from __future__ import annotations
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from calendar import monthrange
from datetime import datetime, date
from zoneinfo import ZoneInfo


def start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Начать бронирование", callback_data="start_booking")]
    ])


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Найти слот", callback_data="find_slot")],
            [InlineKeyboardButton(text="Мои брони", callback_data="my_bookings")],
        ]
    )


#
#
# def weekdays_kb(today: datetime) -> InlineKeyboardMarkup:
#     names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
#     rows = []
#     for i in range(7):
#         d = today.date().toordinal() + i
#         rows.append(
#             [
#                 InlineKeyboardButton(
#                     text=f"{names[(today.weekday() + i) % 7]}", callback_data=f"wk:{d}"
#                 )
#             ]
#         )
#     return InlineKeyboardMarkup(inline_keyboard=rows)


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


# def messenger_kb() -> InlineKeyboardMarkup:
#     return InlineKeyboardMarkup(
#         inline_keyboard=[
#             [InlineKeyboardButton(text="Telegram", callback_data="msgr:tg")],
#             [InlineKeyboardButton(text="WhatsApp", callback_data="msgr:wa")],
#             [InlineKeyboardButton(text="Звонок", callback_data="msgr:call")],
#         ]
#     )
#

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


def month_kb(
        year: int, month: int, tz_name: str, min_date: date, max_date: date
) -> InlineKeyboardMarkup:
    tz = ZoneInfo(tz_name)
    days_in_month = monthrange(year, month)[1]
    first_day = date(year, month, 1)

    rows: list[list[InlineKeyboardButton]] = []
    title = first_day.strftime("%B %Y")
    rows.append([InlineKeyboardButton(text=title.capitalize(), callback_data="noop")])

    rows.append(
        [
            InlineKeyboardButton(text="Пн", callback_data="noop"),
            InlineKeyboardButton(text="Вт", callback_data="noop"),
            InlineKeyboardButton(text="Ср", callback_data="noop"),
            InlineKeyboardButton(text="Чт", callback_data="noop"),
            InlineKeyboardButton(text="Пт", callback_data="noop"),
            InlineKeyboardButton(text="Сб", callback_data="noop"),
            InlineKeyboardButton(text="Вс", callback_data="noop"),
        ]
    )

    offset = first_day.weekday()
    row: list[InlineKeyboardButton] = []
    for _ in range(offset):
        row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

    for d in range(1, days_in_month + 1):
        cur = date(year, month, d)
        if min_date <= cur <= max_date:
            cb = f"day:{cur.isoformat()}"
            row.append(InlineKeyboardButton(text=str(d), callback_data=cb))
        else:
            row.append(InlineKeyboardButton(text="·", callback_data="noop"))
        if len(row) == 7:
            rows.append(row)
            row = []
    if row:
        while len(row) < 7:
            row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
        rows.append(row)

    prev_month = (year if month > 1 else year - 1, 12 if month == 1 else month - 1)
    next_month = (year if month < 12 else year + 1, 1 if month == 12 else month + 1)

    rows.append(
        [
            InlineKeyboardButton(
                text="◀", callback_data=f"cal:{year:04d}-{month:02d}:-1"
            ),
            InlineKeyboardButton(
                text="▶", callback_data=f"cal:{year:04d}-{month:02d}:+1"
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def duration_kb(hours_list: list[int]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for h in hours_list:
        row.append(InlineKeyboardButton(text=f"{h} ч", callback_data=f"dur:{h}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def contact_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Связаться с менеджером", callback_data="contact_admin")]
    ])
