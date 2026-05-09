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
            print("Engine: Wake word detected, listening...")
            # Optional: Add a sound effect or UI change
            
        elif event == "SPEECH_COMPLETE":
            print("Engine: Speech captured, transcribing...")
            asyncio.run_coroutine_threadsafe(self.process_voice_command(data), self.loop)

    async def process_voice_command(self, audio_data):
        # 1. Transcribe
        text = self.stt.transcribe(audio_data)
        if not text:
            return
            
        print(f"User said: {text}")
        
        # 2. Process with Brain
        response = await self.agent.process_query(text)
        
        # 3. Speak response
        await self.tts.speak(response)

    def start(self):
        self.listener.start()
        activity_monitor.start()

    def stop(self):
        self.listener.stop()
        activity_monitor.stop()
        self.loop.call_soon_threadsafe(self.loop.stop)
