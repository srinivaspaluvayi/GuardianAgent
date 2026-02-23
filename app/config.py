"""Loads env/settings. Single source of truth for configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "Guardian Agent"

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "guardian"

    # LLM (Step 7+)
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"


settings = Settings()
