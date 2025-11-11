from __future__ import annotations

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from slotkeeper.fsm.states import ClientFlow
from slotkeeper.utils.validators import is_phone, parse_guests

from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, date
from slotkeeper.ui.keyboards import month_kb
from slotkeeper.config import Settings

router = Router()


@router.message(StateFilter(ClientFlow.ContactCollect))
async def got_fullname_ask_phone(message: Message, state: FSMContext) -> None:
    fullname = " ".join(message.text.split())
    if len(fullname) < 3 or " " not in fullname:
        await message.answer(
            "✍️ Нужно указать **имя и фамилию** через пробел.\n"
            "Например: <b>Анна Смирнова</b>."
        )
        return

    await state.update_data(fullname=message.text.strip())
    await state.set_state(ClientFlow.ContactPhone)
    await message.answer(
        "📱 Укажи номер телефона в формате <b>+79001234567</b>.\n"
        "Номер нужен для подтверждения брони."
    )

@router.message(StateFilter(ClientFlow.ContactPhone))
async def got_phone_ask_guests(message: Message, state: FSMContext) -> None:
    phone = (message.text or "").strip()
    if not is_phone(phone):
        await message.answer(
            "🤔 Номер не похож на реальный. Пример: <b>+79001234567</b>.\n"
            "Попробуй ещё раз."
        )
        return
    await state.update_data(phone=phone)
    await state.set_state(ClientFlow.GuestsCount)
    await message.answer("👥 Сколько вас будет? Введи число от <b>1 до 12</b>.")


@router.message(StateFilter(ClientFlow.GuestsCount))
async def got_guests_show_summary(message: Message, state: FSMContext) -> None:
    guests = parse_guests(message.text)
    if guests is None:
        await message.answer("Мне нужно целое число от 1 до 12. Попробуй ещё.")
        return

    await state.update_data(guests=guests)
    await state.set_state(ClientFlow.Summary)
    data = await state.get_data()
    await message.answer(
        "Сводка заявки:\n"
        f"👤 Имя: {data.get('fullname')}\n"
        f"📞 Телефон: {data.get('phone')}\n"
        f"👥 Гостей: {data.get('guests')}\n\n"
        "Теперь выберем <b>день</b> и <b>время</b> 🗓️"
    )

    settings = Settings()
    tz = ZoneInfo(settings.APP_TIMEZONE)
    today = datetime.now(tz).date()

    y, m = today.year, today.month
    total_months = y * 12 + (m - 1) + settings.MAX_MONTHS_AHEAD
    max_year = total_months // 12
    max_month = total_months % 12 + 1
    max_day = date(max_year, max_month, 1) - timedelta(days=1)

    await message.answer(
        "📆 Выбери день на календаре или введи дату <b>ДД.ММ.ГГГГ</b>.",
        reply_markup=month_kb(
            y, m, settings.APP_TIMEZONE, min_date=today, max_date=max_day
        ),
    )
