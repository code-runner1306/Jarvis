from faster_whisper import WhisperModel
import numpy as np

class STTEngine:
    def __init__(self, model_size="base", device="cpu", compute_type="int8"):
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_data: np.ndarray) -> str:
        # Ensure audio is float32
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
            
        segments, info = self.model.transcribe(audio_data, beam_size=5)
        
        text = ""
        for segment in segments:
            text += segment.text
            
        return text.strip()

if __name__ == "__main__":
    # Test with dummy data
    stt = STTEngine()
    print("STT Engine initialized.")
