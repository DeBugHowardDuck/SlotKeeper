from __future__ import annotations
from slotkeeper.core.booking.repo import InMemoryBookingRepo
from slotkeeper.core.booking.hold import HoldManager

REPO = InMemoryBookingRepo()
HOLDS = HoldManager(repo=REPO, tz="Europe/Moscow")