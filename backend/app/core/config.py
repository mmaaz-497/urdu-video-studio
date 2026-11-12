from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # Video pipeline provider
    VIDEO_PROVIDER: Literal["mock", "runpod"] = "mock"

    # Storage provider
    STORAGE_PROVIDER: Literal["local", "r2"] = "local"
    LOCAL_STORAGE_PATH: str = "./.data/storage"

    # Cloudflare R2
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Daily usage limits
    DAILY_VIDEO_LIMIT: int = 5
    DAILY_SCRIPT_LIMIT: int = 20

    # Stale-job sweeper
    MAX_PROCESSING_SECONDS: int = 600

    # ffmpeg CPU budget (encoder/filter threads per ffmpeg process)
    FFMPEG_THREADS: int = 2

    # Email (Resend)
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "no-reply@example.com"
    # Public origin of the frontend; used to build password-reset links.
    FRONTEND_BASE_URL: str = "http://localhost:3000"

    # Session / CSRF
    SESSION_COOKIE_SECRET: str
    # Secure cookies are only sent over HTTPS (and http://localhost in Chrome/Firefox).
    # Keep true in production; set false only for a plain-http LAN test.
    COOKIE_SECURE: bool = True
    SESSION_TTL_SECONDS: int = 604800
    CSRF_COOKIE_NAME: str = "csrf_token"

    # RunPod
    RUNPOD_API_KEY: str = ""
    RUNPOD_ENDPOINT_ID: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
