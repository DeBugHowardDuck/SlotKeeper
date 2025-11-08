from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    APP_TIMEZONE: str = "Europe/Moscow"
    REDIS_URL: str | None = None
    HOLD_MINUTES: int = 30
    HOLD_WARN_BEFORE_MIN: int = 5
    ADMIN_IDS: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def admin_ids(self) -> list[int]:
        if not self.ADMIN_IDS.strip():
            return []
        return [int(x) for x in self.ADMIN_IDS.replace(" ", "").split(",") if x]
