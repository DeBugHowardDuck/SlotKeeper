from __future__ import annotations
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from redis.asyncio import from_url as redis_from_url

from slotkeeper.config import Settings
from slotkeeper.core.booking.hold import HoldManager
from slotkeeper.core.booking.repo import InMemoryBookingRepo
from slotkeeper.handlers.start import router as start_router
from slotkeeper.handlers.search import router as search_router
from slotkeeper.handlers.collect import router as collect_router


_REPO = InMemoryBookingRepo
_HOLDS = HoldManager(repo=_REPO, tz="Europe/Moscow")


async def run() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    settings = Settings()
    bot = Bot(token=settings.BOT_TOKEN)

    if settings.REDIS_URL:
        redis = redis_from_url(settings.REDIS_URL, decode_responses=True)
        storage = RedisStorage(
            redis=redis, key_builder=DefaultKeyBuilder(with_bot_id=True)
        )
        logging.info("FSM storage: Redis")
    else:
        storage = MemoryStorage()
        logging.info("FSM storage: Memory (no REDIS_URL)")

    _HOLDS.tz = settings.APP_TIMEZONE
    _HOLDS.start(interval_seconds=5)

    dp = Dispatcher(storage=storage)
    dp.include_router(start_router)
    dp.include_router(collect_router)
    dp.include_router(search_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run())
