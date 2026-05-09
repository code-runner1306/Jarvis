import asyncio
import threading
from voice.listener import VoiceListener
from voice.stt import STTEngine
from voice.tts import TTSEngine
from agents.supervisor import SupervisorAgent
from utils.monitor import activity_monitor

class JarvisEngine:
    def __init__(self, ui_window=None):
        self.ui = ui_window
        self.stt = STTEngine()
        self.tts = TTSEngine()
        self.agent = SupervisorAgent()
        
        self.listener = VoiceListener(
            callback=self.on_voice_event,
            volume_callback=self.on_volume_update
        )
        
        self.loop = asyncio.new_event_loop()
        self.async_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.async_thread.start()

    def _run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def on_volume_update(self, volume):
        if self.ui:
            self.ui.orb.set_volume(volume)

    def on_voice_event(self, event, data=None):
        if event == "WAKE_WORD_DETECTED":
            print("[ENGINE] Wake word detected, getting dynamic response from Ollama...")
            # Get a dynamic response from the AI for the wake word
            asyncio.run_coroutine_threadsafe(self._respond_to_wakeword(), self.loop)
            
        elif event == "SPEECH_COMPLETE":
            print("[ENGINE] Speech captured, starting transcription...")
            asyncio.run_coroutine_threadsafe(self.process_voice_command(data), self.loop)

    async def _respond_to_wakeword(self):
        # We pass "Hey Jarvis" to the agent so it can respond naturally
        response = await self.agent.process_query("Hey Jarvis")
        print(f"[JARVIS] {response}")
        await self.tts.speak(response)
        # Reset the listener timeout so the user has time to speak after the greeting
        self.listener.reset_timeout()

    async def process_voice_command(self, audio_data):
        # 1. Transcribe
        print("[ENGINE] Transcribing audio with Faster-Whisper...")
        text = self.stt.transcribe(audio_data)
        if not text:
            print("[ENGINE] Transcription empty, ignoring.")
            return
            
        print(f"[USER] {text}")
        
        # 2. Process with Brain
        print(f"[ENGINE] Consulting Brain (model: {self.agent.llm.model})...")
        response = await self.agent.process_query(text)
        print(f"[JARVIS] {response}")
        
        # 3. Speak response
        print("[ENGINE] Generating speech...")
        await self.tts.speak(response)
        print("[ENGINE] Speech complete. Ready for next command.")

    def start(self):
        self.listener.start()
        activity_monitor.start()

    def stop(self):
        self.listener.stop()
        activity_monitor.stop()
        self.loop.call_soon_threadsafe(self.loop.stop)
