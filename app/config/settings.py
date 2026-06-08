import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


def _normalize_supabase_url(url: str) -> str:
    return url.rstrip("/").removesuffix("/rest/v1")


class Settings:
    SUPABASE_URL: str = _normalize_supabase_url(os.getenv("SUPABASE_URL", ""))
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    @classmethod
    def validate_supabase(cls) -> None:
        if not cls.SUPABASE_URL:
            raise ValueError("SUPABASE_URL is not set in .env")
        if not cls.SUPABASE_KEY:
            raise ValueError("SUPABASE_KEY is not set in .env")


settings = Settings()
