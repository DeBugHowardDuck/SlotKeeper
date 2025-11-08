from __future__ import annotations
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from .models import TimeSlot, overlaps, with_buffers

def _day_window(dt: datetime, open_at: time, close_at: time) -> TimeSlot:
    start = dt.replace(hour=open_at.hour, minute=open_at.minute, second=0, microsecond=0)
    end = dt.replace(hour=close_at.hour, minute=close_at.minute, second=0, microsecond=0)
    if end <= start:
        end = end + timedelta(days=1)
    return TimeSlot(start=start, end=end)


def generate_slots_for_day(
    date_local: datetime,
    *,
    tz_name: str,
    open_at: time = time(11, 0),
    close_at: time = time(23, 0),
    slot_duration: timedelta = timedelta(hours=2),
    step: timedelta = timedelta(minutes=30),
    pre_buffer: timedelta = timedelta(minutes=30),
    post_buffer: timedelta = timedelta(minutes=60),
    busy: list[TimeSlot] | None = None,
) -> list[TimeSlot]:

    tz = ZoneInfo(tz_name)
    date_local = date_local.astimezone(tz)

    day_window = _day_window(date_local, open_at, close_at)

    candidates: list[TimeSlot] = []
    cursor = day_window.start
    while cursor + slot_duration < day_window.end:
        candidates.append(TimeSlot(cursor, cursor + slot_duration))
        cursor += step

    if not busy:
        return candidates

    free: list[TimeSlot] = []
    for c in candidates:
        buffered = with_buffers(c, pre_buffer, post_buffer)
        if any(overlaps(buffered, b) for b in busy):
            continue
        free.append(c)
    return free