import asyncio
import numpy as np
import soundfile as sf
import pygame
import os
import tempfile
import urllib.request
from utils.config import settings

class TTSEngine:
    def __init__(self):
        self.engine_type = getattr(settings, "TTS_ENGINE", "piper").lower()
        self.voice = settings.TTS_VOICE
        self.speed = settings.TTS_SPEED
        self.lang = settings.TTS_LANG
        
        # Piper specific
        self.piper_voice_name = getattr(settings, "PIPER_VOICE", "en_GB-alan-medium")
        self.piper_model = None
        self.kokoro_pipeline = None
        
        # Piper generally uses 22050Hz, Kokoro uses 24000Hz
        self.sample_rate = 22050 if self.engine_type == "piper" else 24000
        pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=1)
        
        if self.engine_type == "piper":
            self._init_piper()
        elif self.engine_type == "kokoro":
            self._init_kokoro()
        else:
            print(f"[TTS] Using fallback edge-tts engine.")

    def _init_piper(self):
        try:
            from piper import PiperVoice
            model_dir = os.path.join(os.path.dirname(__file__), "..", "models", "piper")
            os.makedirs(model_dir, exist_ok=True)
            
            onnx_path = os.path.join(model_dir, f"{self.piper_voice_name}.onnx")
            json_path = os.path.join(model_dir, f"{self.piper_voice_name}.onnx.json")
            
            # Download model if not exists
            if not os.path.exists(onnx_path) or not os.path.exists(json_path):
                print(f"[TTS] Downloading Piper voice '{self.piper_voice_name}'...")
                base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium"
                if "alan" not in self.piper_voice_name:
                    # Generic fallback URL logic for other voices would go here, 
                    # but we are sticking to alan-medium for JARVIS
                    pass
                urllib.request.urlretrieve(f"{base_url}/{self.piper_voice_name}.onnx", onnx_path)
                urllib.request.urlretrieve(f"{base_url}/{self.piper_voice_name}.onnx.json", json_path)
                print("[TTS] Download complete.")
            
            self.piper_model = PiperVoice.load(onnx_path, config_path=json_path)
            print(f"[TTS] Piper initialized (voice={self.piper_voice_name})")
        except Exception as e:
            print(f"[TTS WARNING] Piper failed to init: {e}. Falling back to edge-tts.")
            self.engine_type = "edge"

    def _init_kokoro(self):
        try:
            from kokoro import KPipeline
            self.kokoro_pipeline = KPipeline(lang_code=self.lang)
            print(f"[TTS] Kokoro initialized (voice={self.voice})")
        except Exception as e:
            print(f"[TTS WARNING] Kokoro failed to init: {e}. Falling back to edge-tts.")
            self.engine_type = "edge"

    async def speak(self, text: str):
        if not text:
            return

        if self.engine_type == "piper" and self.piper_model:
            await self._speak_piper(text)
        elif self.engine_type == "kokoro" and self.kokoro_pipeline:
            await self._speak_kokoro(text)
        else:
            await self._speak_edge_tts(text)

    async def _speak_piper(self, text: str):
        loop = asyncio.get_running_loop()
        tmp_path = await loop.run_in_executor(None, self._generate_piper_audio, text)
        
        if tmp_path and os.path.exists(tmp_path):
            self._play_audio(tmp_path)

    def _generate_piper_audio(self, text: str) -> str:
        try:
            import wave
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            tmp_path = tmp_file.name
            tmp_file.close()
            
            with wave.open(tmp_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.piper_model.config.sample_rate)
                
                for chunk in self.piper_model.synthesize(text):
                    wav_file.writeframes(chunk.audio_int16_bytes)
                    
            return tmp_path
        except Exception as e:
            print(f"[TTS ERROR] Piper generation failed: {e}")
            return None

    async def _speak_kokoro(self, text: str):
        loop = asyncio.get_running_loop()
        tmp_path = await loop.run_in_executor(None, self._generate_kokoro_audio, text)
        if tmp_path and os.path.exists(tmp_path):
            self._play_audio(tmp_path)

    def _generate_kokoro_audio(self, text: str) -> str:
        try:
            generator = self.kokoro_pipeline(text, voice=self.voice, speed=self.speed)
            all_audio = []
            for _, _, audio in generator:
                all_audio.append(audio)
            
            if not all_audio:
                return None
            
            full_audio = np.concatenate(all_audio)
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            tmp_path = tmp_file.name
            tmp_file.close()
            sf.write(tmp_path, full_audio, 24000)
            return tmp_path
        except Exception as e:
            print(f"[TTS ERROR] Kokoro generation failed: {e}")
            return None

    async def _speak_edge_tts(self, text: str):
        try:
            import edge_tts
        except ImportError:
            return
            
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_path = tmp_file.name
            
        communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
        await communicate.save(tmp_path)
        self._play_audio(tmp_path)

    def _play_audio(self, file_path: str):
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
        try:
            os.remove(file_path)
        except:
            pass

if __name__ == "__main__":
    engine = TTSEngine()
    asyncio.run(engine.speak("Hello sir, I am JARVIS. How can I help you today?"))
