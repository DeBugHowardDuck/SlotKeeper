from __future__ import annotations
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from .config import Settings
from .handlers.start import router as start_router


async def run() -> None:
    settings = Settings()
    bot = Bot(token=settings.BOT_TOKEN)

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(start_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run())
