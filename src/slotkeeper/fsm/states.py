from __future__ import annotations
from aiogram.fsm.state import State, StatesGroup

class ClientFlow(StatesGroup):
    Start = State()
    ConsentRules = State()
    ContactCollect = State()
    SlotSearch = State()
    SlotPick = State()
    Summary = State()
    Submit = State()
    WaitAdmin = State()

    MyBookings = State()
    BookingDetails = State()
    CancelOrChange = State()
