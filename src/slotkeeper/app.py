from __future__ import annotations
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from redis.asyncio import from_url as redis_from_url

from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from slotkeeper.config import Settings
from slotkeeper.core.booking.hold import HoldManager
from slotkeeper.core.booking.repo import InMemoryBookingRepo
from slotkeeper.handlers.start import router as start_router
from slotkeeper.handlers.search import router as search_router
from slotkeeper.handlers.collect import router as collect_router
from slotkeeper.handlers.admin import router as admin_router

from slotkeeper.core.booking.shared import HOLDS
from slotkeeper.core.notify.notifier import NOTIFY


_REPO = InMemoryBookingRepo
_HOLDS = HoldManager(repo=_REPO, tz="Europe/Riga")


async def run() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    settings = Settings()
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    if settings.REDIS_URL:
        redis = redis_from_url(settings.REDIS_URL, decode_responses=True)
        storage = RedisStorage(
            redis=redis, key_builder=DefaultKeyBuilder(with_bot_id=True)
        )
        logging.info("FSM storage: Redis")
    else:
        storage = MemoryStorage()
        logging.info("FSM storage: Memory (no REDIS_URL)")

    NOTIFY.set_runtime(bot=bot, settings=settings)

    HOLDS.tz = settings.APP_TIMEZONE
    HOLDS.start(interval_seconds=30)

    dp = Dispatcher(storage=storage)
    dp.include_router(start_router)
    dp.include_router(collect_router)
    dp.include_router(search_router)
    dp.include_router(admin_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run())
