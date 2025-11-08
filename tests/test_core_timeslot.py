from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from slotkeeper.core.models import TimeSlot, overlaps, with_buffers


def test_overlaps_and_buffers_basic():
    tz = ZoneInfo("Europe/Riga")
    a = TimeSlot(datetime(2025, 1, 1, 10, 0, tzinfo=tz), datetime(2025, 1, 1, 12, 0, tzinfo=tz))
    b = TimeSlot(datetime(2025, 1, 1, 11, 30, tzinfo=tz), datetime(2025, 1, 1, 13, 0, tzinfo=tz))
    assert overlaps(a, b)

    buffered = with_buffers(a, timedelta(minutes=30), timedelta(minutes=60))
    assert buffered.start == datetime(2025, 1, 1, 9, 30, tzinfo=tz)
    assert buffered.end == datetime(2025, 1, 1, 13, 0, tzinfo=tz)
