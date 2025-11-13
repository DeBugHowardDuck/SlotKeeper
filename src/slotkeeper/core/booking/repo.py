from __future__ import annotations
import itertools
from collections.abc import Iterable
from datetime import datetime
from typing import Dict, List

from .models import Booking, BookingStatus


class InMemoryBookingRepo:
    def __init__(self) -> None:
        self._seq = itertools.count(1)
        self._items: Dict[int, Booking] = {}

    def add(self, b: Booking) -> Booking:
        b.id = next(self._seq)
        self._items[b.id] = b
        return b

    def get(self, booking_id: int) -> Booking | None:
        return self._items.get(booking_id)

    def all(self) -> List[Booking]:
        return list(self._items.values())

    def update(self, b: Booking) -> None:
        self._items[b.id] = b

    def mark_expired_if_held_and_due(self, now: datetime) -> list[int]:
        expired: list[int] = []
        for b in self._items.values():
            if (
                b.status == BookingStatus.pending_review
                and b.hold_deadline
                and now >= b.hold_deadline
            ):
                b.status = BookingStatus.expired
                expired.append(b.id)
        return expired

    def conflicts(self, start: datetime, end: datetime) -> Iterable[Booking]:
        for b in self._items.values():
            if (
                    b.status in {BookingStatus.confirmed, BookingStatus.pending_review}
                    and not (b.ends_at <= start or end <= b.starts_at)
            ):
                yield b
