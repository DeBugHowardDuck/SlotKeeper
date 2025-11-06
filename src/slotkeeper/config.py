from __future__ import annotations

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    APP_TIMEZONE: str = 'Europe/Moscow'

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }
