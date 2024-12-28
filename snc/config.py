from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    openai_api_key: str = ""
    groq_api_key: str = ""
    anthropic_api_key: str = ""
    database_url: str = "sqlite:///./snc.db"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    """
    return Settings()
