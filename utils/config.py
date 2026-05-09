import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Brain Configuration
    LLM_BACKEND: str = "nvidia" # nvidia or ollama
    NVIDIA_API_KEY: str = ""
    NVIDIA_MODEL: str = "nvidia/llama-3.1-nemotron-70b-instruct"

    # Ollama fallback
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3.5:2b"
    
    # Voice Settings
    WAKE_WORD: str = "hey jarvis"
    STT_MODEL: str = "base"  # tiny, base, small, medium, large-v3
    
    # TTS Settings
    TTS_ENGINE: str = "piper" # piper, kokoro, edge
    PIPER_VOICE: str = "en_GB-alan-medium"
    
    # Kokoro options
    TTS_VOICE: str = "bm_george"       # British male (JARVIS-like)
    TTS_SPEED: float = 1.0             # 0.5 = slow, 1.0 = normal, 1.5 = fast
    TTS_LANG: str = "b"                # 'a' = American English, 'b' = British English
    
    # Persistence
    DATABASE_URL: str = "sqlite:///jarvis.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
