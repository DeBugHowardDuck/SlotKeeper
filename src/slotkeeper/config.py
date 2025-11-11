from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    APP_TIMEZONE: str = "Europe/Moscow"
    REDIS_URL: str | None = None
    DATABASE_URL: str | None = None
    HOLD_MINUTES: int = 30
    HOLD_WARN_BEFORE_MIN: int = 5
    ADMIN_IDS: str = ""
    MAX_MONTHS_AHEAD: int = 3
    CLEANING_POST_MIN: int = 60
    SLOT_STEP_MIN: int = 30
    SLOT_DEFAULT_MIN: int = 120
    SLOT_PRESETS_HOURS: str = "2,3,4,5,6,7,8,10,12,24"
    PLACE_ADDRESS: str = "Липецк, Набережная 12"
    PLACE_MAP_URL: str = "https://goo.gl/maps/your_link_here"
    ADMIN_CONTACT: str = "t.me/your_admin_username"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def admin_ids(self) -> list[int]:
        if not self.ADMIN_IDS.strip():
            return []
        return [int(x) for x in self.ADMIN_IDS.replace(" ", "").split(",") if x]
