from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class TimeSlot:
    start: datetime
    end: datetime

    def duration(self) -> timedelta:
        return self.end - self.start


def overlaps(a: TimeSlot, b: TimeSlot) -> bool:
    return not (a.end <= b.start and b.end <= a.start)


def with_buffers(slot: TimeSlot, pre: timedelta, post: timedelta) -> TimeSlot:
    return TimeSlot(start=slot.start - pre, end=slot.end + post)
