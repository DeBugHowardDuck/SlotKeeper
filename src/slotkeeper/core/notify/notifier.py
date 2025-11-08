from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

from aiogram import Bot

from slotkeeper.config import Settings
from slotkeeper.core.booking.shared import REPO

@dataclass
class _Runtime:
    bot: Optional[Bot] = None
    settings: Optional[Settings] = None

class Notifier:
    def __init__(self) -> None:
        self.bot: Optional[Bot] = None
        self.settings: Optional[Settings] = None
        self._tasks: set[asyncio.Task] = set()

    def set_runtime(self, bot: Bot, settings: Settings) -> None:
        self.bot = bot
        self.settings = settings

    def schedule_hold_warning(self, booking_id: int) -> None:
        if not self.bot or not self.settings:
            return
        task = asyncio.create_task(self._hold_warning_runner(booking_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _hold_warning_runner(self, booking_id: int) -> None:
        bot = self.bot
        settings = self.settings
        if not bot or not settings:
            return

        b = REPO.get(booking_id)
        if not b or not b.hold_deadline:
            return

        tz = ZoneInfo(settings.APP_TIMEZONE)
        warn_before = timedelta(minutes=max(0, settings.HOLD_WARN_BEFORE_MIN))
        now = datetime.now(tz)
        fire_at = b.hold_deadline - warn_before
        delay = (fire_at - now).total_seconds()

        if delay > 0:
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return

        # обновим состояние
        b2 = REPO.get(booking_id)
        if not b2 or b2.status != "pending_review" or not b2.hold_deadline:
            return

        text = (
            f"⏳ Холд заявки #{b2.id} истекает в {b2.hold_deadline.astimezone(tz).strftime('%H:%M')}.\n"
            f"{b2.customer.fullname}, гостей: {b2.customer.guests}, тел: {b2.customer.phone}\n"
            f"{b2.starts_at.strftime('%Y-%m-%d %H:%M')}–{b2.ends_at.strftime('%H:%M')}"
        )
        for admin_id in settings.admin_ids:
            try:
                await bot.send_message(chat_id=admin_id, text=text)
            except Exception:
                pass


NOTIFY = Notifier()
