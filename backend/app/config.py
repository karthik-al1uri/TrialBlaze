"""
Application configuration.
Loads settings from environment variables / .env file.
"""

import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env only if not already set (local dev only)
if not os.getenv("MONGO_URI"):
    load_dotenv("ai/.env")


class Settings(BaseSettings):
    APP_NAME: str = "TrailBlaze AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"

    MONGO_URI: str = os.getenv("MONGO_URI", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_CHAT_MODEL: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    OPENAI_EMBEDDING_MODEL: str = os.getenv(
        "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "trailblaze")
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000")


settings = Settings()
