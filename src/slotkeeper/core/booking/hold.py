from __future__ import annotations
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from .repo import InMemoryBookingRepo


class HoldManager:
    def __init__(self, repo: InMemoryBookingRepo, tz: str) -> None:
        self.repo = repo
        self.tz = tz
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def start(self, interval_seconds: int = 5) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._runner(interval_seconds))

    async def _runner(self, interval_seconds: int) -> None:
        tzinfo = ZoneInfo(self.tz)
        while not self._stop.is_set():
            now = datetime.now(tzinfo)
            self.repo.mark_expired_if_held_and_due(now)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval_seconds)
            except asyncio.TimeoutError:
                pass

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await asyncio.shield(self._task)
