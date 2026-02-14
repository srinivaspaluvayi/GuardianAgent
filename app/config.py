"""Guardian Supervisor configuration."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

# Project root (parent of app/)
_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT / ".env"


class Settings(BaseSettings):
    """Application settings from env and .env file."""

    # API
    app_name: str = "Guardian Supervisor"
    debug: bool = False

    # Database (default SQLite for local run; use Postgres in production)
    database_url: str = "sqlite:///./guardian.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Stream names
    stream_action_intent: str = "action.intent"
    stream_action_decision: str = "action.decision"
    stream_approval_request: str = "approval.request"
    stream_approval_decision: str = "approval.decision"

    # Consumer
    consumer_group: str = "guardian"
    consumer_name: str = "guardian-1"

    # LLM risk scoring (optional; if not set, score is policy-only)
    # For Ollama: set GUARDIAN_LLM_BASE_URL=http://localhost:11434/v1 and GUARDIAN_LLM_MODEL=<your-model>. No API key needed.
    llm_api_key: str = ""
    llm_model: str = "llama3.2:3b"  # Ollama: good at JSON/instructions, small (~2GB). Or llama3.1:8b / mistral:7b
    llm_base_url: str = ""  # set to http://localhost:11434/v1 for Ollama

    model_config = {
        "env_prefix": "GUARDIAN_",
        "env_file": _ENV_FILE,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
