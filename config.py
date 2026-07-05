import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API Keys
    GEMINI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    PEXELS_API_KEY: Optional[str] = None
    PIXABAY_API_KEY: Optional[str] = None

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # LLM Settings
    LLM_BACKEND: str = "gemini"  # gemini | anthropic | openai
    GEMINI_MODEL: str = "gemini-2.5-flash"
    ANTHROPIC_MODEL: str = "claude-haiku-4-5"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Project Paths
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR: str = os.path.join(BASE_DIR, "output")
    TEMP_DIR: str = os.path.join(BASE_DIR, "temp")
    LIBRARY_DIR: str = os.path.join(BASE_DIR, "library")
    FONTS_DIR: str = os.path.join(BASE_DIR, "fonts")

    # Rendering
    DEFAULT_FPS: int = 30
    DEFAULT_RESOLUTION: tuple = (1080, 1920)

    # Curation
    CANDIDATES_PER_BEAT: int = 16
    CLIP_MATCH_WEIGHT: float = 0.4
    VISUAL_QA_WEIGHT: float = 0.3
    PALETTE_MATCH_WEIGHT: float = 0.15
    MOTION_STABILITY_WEIGHT: float = 0.15
    MIN_ACCEPT_SCORE: float = 0.45
    WEAK_MATCH_THRESHOLD: float = 0.55  # below this clip_score, trigger a fallback query retry

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

for directory in [settings.OUTPUT_DIR, settings.TEMP_DIR, settings.LIBRARY_DIR, settings.FONTS_DIR]:
    os.makedirs(directory, exist_ok=True)
