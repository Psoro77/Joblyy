from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_provider: str = "ollama"
    ollama_model: str = "gemma4:e2b"
    ollama_base_url: str = "http://localhost:11434"
    cloud_api_key: str = ""
    cloud_model: str = "anthropic/claude-sonnet-4-20250514"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def update_settings(**kwargs: str) -> Settings:
    settings = get_settings()
    for key, value in kwargs.items():
        if value is not None and hasattr(settings, key):
            setattr(settings, key, value)
    return settings
