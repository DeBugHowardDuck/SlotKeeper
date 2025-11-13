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
    PLACE_ADDRESS: str = "Липецк, проспект имени 60-летия СССР, 2Б."
    PLACE_MAP_URL: str = "https://www.google.com/maps/place/просп.+60+лет+СССР,+2Б,+Липецк,+Липецкая+обл.,+Россия,+398046/@52.5839856,39.5401153,17z/data=!4m6!3m5!1s0x413a6b485fd712cf:0x9cbdc232a213fe2c!8m2!3d52.583927!4d39.5419714!16s%2Fg%2F11bw4chk9m?hl=ru&entry=ttu&g_ep=EgoyMDI1MTExMC4wIKXMDSoASAFQAw%3D%3D"
    ADMIN_CONTACT: str = "t.me/your_admin_username"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def admin_ids(self) -> list[int]:
        if not self.ADMIN_IDS.strip():
            return []
        return [int(x) for x in self.ADMIN_IDS.replace(" ", "").split(",") if x]
