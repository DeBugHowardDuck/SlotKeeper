from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo


class BookingStatus(StrEnum):
    draft = "draft"
    pending_review = "pending_review"
    confirmed = "confirmed"
    cancelled_by_client = "cancelled_by_client"
    cancelled_by_admin = "cancelled_by_admin"
    expired = "expired"
    no_show = "no_show"


@dataclass(slots=True, frozen=True)
class Customer:
    full_name: str
    phone: str
    guests: int


@dataclass(slots=True)
class Booking:
    id: int
    customer: Customer
    starts_at: datetime
    ends_at: datetime
    status: BookingStatus
    hold_deadline: datetime | None = None
    client_chat_id: int | None = None

    @property
    def is_on_hold(self) -> bool:
        return (
            self.status == BookingStatus.pending_review
            and self.hold_deadline is not None
        )

    def set_hold(self, minutes: int, tz: str) -> None:
        self.status = BookingStatus.pending_review
        tzinfo = ZoneInfo(tz)
        now = datetime.now(tzinfo)
        self.hold_deadline = now + timedelta(minutes=minutes)
