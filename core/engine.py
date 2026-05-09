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
            print("[ENGINE] Wake word detected, generating greeting via Ollama...")
            asyncio.run_coroutine_threadsafe(self._respond_to_wakeword(), self.loop)
            
        elif event == "SPEECH_COMPLETE":
            print("[ENGINE] Speech captured, starting transcription...")
            asyncio.run_coroutine_threadsafe(self._process_voice_command(data), self.loop)

    async def _respond_to_wakeword(self):
        """Generate a dynamic greeting and THEN open the mic for commands."""
        try:
            response = await self.agent.process_query("Hey Jarvis")
            print(f"[JARVIS] {response}")
            await self.tts.speak(response)
        except Exception as e:
            print(f"[ENGINE ERROR] Failed to respond to wake word: {e}")
        finally:
            # NOW open the microphone for the user's command
            self.listener.enter_command_mode()

    async def _process_voice_command(self, audio_data):
        """Transcribe, think, speak, then determine next state."""
        try:
            # 1. Transcribe
            print("[ENGINE] Transcribing audio with Faster-Whisper...")
            text = self.stt.transcribe(audio_data)
            if not text or text.strip() in (".", ". . . .", "..."):
                print("[ENGINE] Transcription empty or noise, ignoring.")
                self.listener.enter_wake_word_mode()
                return
                
            print(f"[USER] {text}")
            
            # Check for exit phrase in user input
            text_lower = text.lower()
            exit_phrases = ["thank you", "thanks", "that's all", "goodbye", "bye", "go to sleep", "stop listening"]
            is_exit = any(phrase in text_lower for phrase in exit_phrases)
            
            # Callback for real-time narration during tool calls
            async def narrate(msg):
                print(f"[JARVIS NARRATION] {msg}")
                await self.tts.speak(msg)
                
            # 2. Process with Brain
            model_name = getattr(self.agent.llm, "model", "Unknown")
            print(f"[ENGINE] Consulting Brain (model: {model_name})...")
            response = await self.agent.process_query(text, narration_callback=narrate)
            print(f"[JARVIS] {response}")
            
            # 3. Speak response
            print("[ENGINE] Generating speech...")
            await self.tts.speak(response)
            print("[ENGINE] Speech complete.")
            
            # 4. Decide next state
            if is_exit:
                print("[ENGINE] Exit phrase detected. Returning to sleep.")
                self.listener.enter_wake_word_mode()
            else:
                self.listener.enter_command_mode()
                
        except Exception as e:
            print(f"[ENGINE ERROR] Failed to process voice command: {e}")
            self.listener.enter_wake_word_mode()

    def start(self):
        self.listener.start()
        activity_monitor.start()

    def stop(self):
        print("[ENGINE] Shutting down... cleaning up memory.")
        asyncio.run_coroutine_threadsafe(self.agent.heal_memory(), self.loop)
        self.listener.stop()
        activity_monitor.stop()
        self.loop.call_soon_threadsafe(self.loop.stop)
