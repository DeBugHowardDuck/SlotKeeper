from __future__ import annotations
from slotkeeper.core.booking.repo import InMemoryBookingRepo
from slotkeeper.core.booking.hold import HoldManager
from contextlib import contextmanager
from slotkeeper.db.session import session_scope
from slotkeeper.core.booking.db_repo import DBRepo

REPO = InMemoryBookingRepo()
HOLDS = HoldManager(repo=REPO, tz="Europe/Moscow")

@contextmanager
def repo_scope():
    with session_scope() as s:
        yield DBRepo(s)