from __future__ import annotations

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from slotkeeper.utils.validators import is_phone, parse_guests, normalize_phone

from slotkeeper.fsm.states import ClientFlow
from slotkeeper.utils.validators import is_phone, parse_guests

from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, date
from slotkeeper.ui.keyboards import month_kb, services_kb
from slotkeeper.config import Settings

router = Router()


@router.message(StateFilter(ClientFlow.ContactCollect))
async def got_fullname_ask_phone(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    fullname = " ".join(text.split())

    if len(fullname) < 2 or fullname.isdigit():
        await message.answer(
            "✍️ Напишите, пожалуйста, ваше имя.\n"
            "Например: <b>Анна</b>."
        )
        return

    await state.update_data(fullname=fullname)
    await state.set_state(ClientFlow.ContactPhone)
    await message.answer(
        "Укажи номер телефона. 📱\n"
        "В формате: <b>8 904 555 01 23</b>."
    )

@router.message(StateFilter(ClientFlow.ContactPhone))
async def got_phone_ask_birth(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()

    phone_normalized = normalize_phone(raw)
    if phone_normalized is None:
        await message.answer(
            "Номер не похож на реальный.\n"
            "Примеры: <b>+7 999 123 45 67</b> или <b>8 999 123 45 67</b>."
        )
        return

    await state.update_data(phone=phone_normalized)
    await state.set_state(ClientFlow.BirthDate)
    await message.answer("📅 Укажи дату рождения в формате ДД.ММ.ГГГГ.")


@router.message(StateFilter(ClientFlow.BirthDate))
async def got_birth_ask_guests(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    try:
        birth = datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer("Пожалуйста, введи дату в формате ДД.ММ.ГГГГ.")
        return

    today = datetime.now().date()
    age = (today - birth).days // 365
    await state.update_data(birth_date=birth.isoformat(), age=age)

    await state.set_state(ClientFlow.GuestsCount)
    await message.answer("👥 Сколько вас будет? Введи число от 1 до 12.")


@router.message(StateFilter(ClientFlow.GuestsCount))
async def got_guests_show_services(message: Message, state: FSMContext) -> None:
    guests = parse_guests(message.text)
    if guests is None:
        await message.answer("Мне нужно целое число от 1 до 12. Попробуй ещё.")
        return

    await state.update_data(guests=guests)
    data = await state.get_data()
    age = data.get("age", 0)

    available_services = [
        "Просмотр фильмов (экран + проектор)",
        "Sony PlayStation 5",
        "караоке (колонка + 3 микрофона)",
        "Настольные игры",
        "Попкорн",
        "Чай/Кофе",
    ]
    if age >= 18:
        available_services.append("Кальян, табак, уголь (18+)")

    await state.update_data(available_services=available_services, selected_services=[])
    await state.set_state(ClientFlow.Services)
    await message.answer(
        "🎬 Выберите услуги, которые хотите включить (можно несколько):",
        reply_markup=services_kb(available_services, [])
    )


@router.callback_query(StateFilter(ClientFlow.Services))
async def got_services(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    available = data.get("available_services", [])
    selected = data.get("selected_services", [])

    code = cb.data.split(":")[1]

    if code == "done":
        if not selected:
            await cb.answer("Выберите хотя бы одну услугу.")
            return

        await state.update_data(services=selected)
        settings = Settings()
        tz = ZoneInfo(settings.APP_TIMEZONE)
        today = datetime.now(tz).date()
        y, m = today.year, today.month
        total_months = y * 12 + (m - 1) + settings.MAX_MONTHS_AHEAD
        max_year = total_months // 12
        max_month = total_months % 12 + 1
        max_day = date(max_year, max_month, 1) - timedelta(days=1)

        await cb.message.edit_text(
            "📆 Теперь выбери день на календаре или введи дату ДД.ММ.ГГГГ:",
            reply_markup=month_kb(
                y, m, settings.APP_TIMEZONE, min_date=today, max_date=max_day
            ),
        )
        await state.set_state(ClientFlow.Summary)
        await cb.answer()
        return

    idx = int(code)
    service = available[idx]

    if service in selected:
        selected.remove(service)
    else:
        selected.append(service)

    await state.update_data(selected_services=selected)

    await cb.message.edit_reply_markup(reply_markup=services_kb(available, selected))
    await cb.answer(f"Выбрано: {len(selected)}")
