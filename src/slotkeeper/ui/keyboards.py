from __future__ import annotations
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Найти слот", callback_data="find_slot")],
            [InlineKeyboardButton(text="Мои брони", callback_data="my_bookings")],
        ]
    )


def weekdays_kb(today: datetime) -> InlineKeyboardMarkup:
    names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    rows = []
    for i in range(7):
        d = today.date().toordinal() + i
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{names[(today.weekday() + i) % 7]}", callback_data=f"wk:{d}"
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def times_kb(iso_list: list[str]) -> InlineKeyboardMarkup:
    rows = []
    row: list[InlineKeyboardButton] = []
    for iso in iso_list:
        t_label = iso[11:16]
        row.append(InlineKeyboardButton(text=t_label, callback_data=f"tm:{iso}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def messenger_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Telegram", callback_data="msgr:tg")],
            [InlineKeyboardButton(text="WhatsApp", callback_data="msgr:wa")],
            [InlineKeyboardButton(text="Звонок", callback_data="msgr:call")],
        ]
    )


def admin_booking_actions_kb(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить", callback_data=f"adm:confirm:{booking_id}"
                ),
                InlineKeyboardButton(
                    text="🛑 Отклонить", callback_data=f"adm:reject:{booking_id}"
                ),
            ],
        ]
    )
