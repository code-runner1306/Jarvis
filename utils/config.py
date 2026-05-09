import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # LLM Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "llama3.2:8b"
    
    # Voice Settings
    WAKE_WORD: str = "hey jarvis"
    STT_MODEL: str = "base"  # tiny, base, small, medium, large-v3
    
    # UI Settings
    WINDOW_WIDTH: int = 800
    WINDOW_HEIGHT: int = 800
    
    # Persistence
    DATABASE_URL: str = "sqlite:///jarvis.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
