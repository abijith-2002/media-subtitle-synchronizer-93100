import os
from functools import lru_cache
from typing import Set

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    # Storage directories
    UPLOAD_DIR: str = Field(default_factory=lambda: os.getenv("UPLOAD_DIR", "storage/uploads"))
    SUBTITLE_DIR: str = Field(default_factory=lambda: os.getenv("SUBTITLE_DIR", "storage/subtitles"))

    # Allowed media extensions
    ALLOWED_EXTENSIONS: Set[str] = Field(
        default_factory=lambda: set(
            (os.getenv("ALLOWED_EXTENSIONS", ".mp3,.wav,.m4a,.mp4,.mkv,.mov")).lower().split(",")
        )
    )

    # Database configuration (PostgreSQL)
    # Expected env variables:
    # POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    POSTGRES_HOST: str = Field(default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost"))
    POSTGRES_PORT: str = Field(default_factory=lambda: os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = Field(default_factory=lambda: os.getenv("POSTGRES_DB", "subtitle_sync"))
    POSTGRES_USER: str = Field(default_factory=lambda: os.getenv("POSTGRES_USER", "postgres"))
    POSTGRES_PASSWORD: str = Field(default_factory=lambda: os.getenv("POSTGRES_PASSWORD", ""))

    # WhisperX configuration
    WHISPERX_MODEL: str = Field(default_factory=lambda: os.getenv("WHISPERX_MODEL", "medium"))
    WHISPERX_LANGUAGE: str = Field(default_factory=lambda: os.getenv("WHISPERX_LANGUAGE", "en"))

    # Misc
    DEBUG: bool = Field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")


@lru_cache()
def get_settings() -> Settings:
    """Load and cache settings from environment variables."""
    return Settings()
