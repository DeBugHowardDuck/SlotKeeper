from __future__ import annotations

import asyncio
from pydantic_settings import BaseSettings
from aiogram import Bot, Dispatcher

from aiogram.types import Message

class Settings(BaseSettings):
    BOT_TOKEN: str
    APP_TIMEZONE: str = 'Europe/Moscow'

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

async def ping_handler(message: Message) -> None:
    await message.answer('SlotKeeper is now online!')

def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.message.register(ping_handler, lambda m: m.text == "/ping")
    return dp

async def run() -> None:
    settings = Settings()
    bot = Bot(token=settings.BOT_TOKEN)
    dp = build_dispatcher()

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(run())