from functools import lru_cache
from pathlib import Path
import os


class Settings:
    def __init__(self) -> None:
        self.app_name = os.getenv("APP_NAME", "LLM Lens")
        self.environment = os.getenv("APP_ENV", "production")
        self.database_path = Path(os.getenv("DATABASE_PATH", "data/llm_lens.db"))
        self.cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()]
        self.api_key = os.getenv("LLM_LENS_API_KEY", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
