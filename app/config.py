import os
from pathlib import Path
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    database_path: str = "./data/eyes_up.db"
    birdnet_confidence_threshold: float = 0.50
    birdnet_latitude: Optional[float] = None
    birdnet_longitude: Optional[float] = None
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "gemma2:2b"
    tts_engine: str = "browser"  # "browser", "local_cli", or "elevenlabs"
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None

    @field_validator("birdnet_latitude", "birdnet_longitude", mode="before")
    @classmethod
    def parse_optional_float(cls, v):
        if v == "" or v is None:
            return None
        return float(v)

    @field_validator("elevenlabs_api_key", "elevenlabs_voice_id", mode="before")
    @classmethod
    def parse_optional_str(cls, v):
        if v == "" or v is None:
            return None
        return str(v)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Ensure data directory exists
data_dir = Path(settings.database_path).parent
data_dir.mkdir(parents=True, exist_ok=True)
