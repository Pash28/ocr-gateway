"""
Centralized application configuration.
All settings are read from environment variables (.env),
making it easy to change behavior between local / docker / production
without modifying code.
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- General ---
    app_name: str = "OCRGateway"
    environment: str = Field(default="local")  # local | docker | production
    debug: bool = Field(default=False)

    # --- Security ---
    api_key: str = Field(default="dev-secret-key", description="Key for X-API-Key header")
    api_key_enabled: bool = Field(default=True)

    # --- File limits ---
    max_upload_size_mb: int = Field(default=20)
    allowed_image_types: List[str] = Field(
        default_factory=lambda: ["image/png", "image/jpeg", "image/webp", "image/bmp", "image/tiff"]
    )
    allowed_pdf_type: str = "application/pdf"

    # --- OCR ---
    default_languages: str = Field(default="eng", description="Tesseract language code(s), joined by +, e.g. eng+rus")
    max_pdf_pages_sync: int = Field(default=3, description="Page limit for synchronous PDF OCR")

    # --- Task queue (Celery + Redis) ---
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_task_time_limit_seconds: int = Field(default=300)

    # --- Rate limit ---
    rate_limit_per_minute: int = Field(default=30)


@lru_cache
def get_settings() -> Settings:
    """Cache settings so .env is only read once per process lifetime."""
    return Settings()
