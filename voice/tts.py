import asyncio
import edge_tts
import pygame
import os
import tempfile

class TTSEngine:
    def __init__(self, voice="en-US-GuyNeural"):
        self.voice = voice
        pygame.mixer.init()

    async def speak(self, text: str):
        if not text:
            return
            
        print(f"JARVIS: {text}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_path = tmp_file.name
            
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(tmp_path)
        
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
            
        pygame.mixer.music.unload()
        try:
            os.remove(tmp_path)
        except:
            pass

if __name__ == "__main__":
    engine = TTSEngine()
    asyncio.run(engine.speak("Hello, I am JARVIS. How can I help you today?"))
