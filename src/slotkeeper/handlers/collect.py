from __future__ import annotations

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from slotkeeper.fsm.states import ClientFlow
from slotkeeper.utils.validators import is_phone, parse_guests

router = Router()

@router.message(StateFilter(ClientFlow.ContactCollect))
async def got_fullname_ask_phone(message: Message, state: FSMContext) -> None:
    fullname = " ".join(message.text.split())
    if len(fullname) < 3 or " " not in fullname:
        await message.answer("Нужно ввести имя и фамилию через пробел. Пример: Иван Петров")
        return

    await state.update_data(fullname=fullname)
    await state.set_state(ClientFlow.ContactPhone)
    await message.answer("Введи номер телефона в формате +79001234567.")

@router.message(StateFilter(ClientFlow.ContactPhone))
async def got_phone_ask_guests(message: Message, state: FSMContext) -> None:
    phone = message.text.strip()
    if not is_phone(phone):
        await message.answer("Номер не похож на реальный. Пример: +79001234567. Попробуй ещё раз.")
        return

    await state.update_data(phone=phone)
    await state.set_state(ClientFlow.GuestsCount)
    await message.answer("Сколько гостей придёт? Введи число от 1 до 12.")

@router.message(StateFilter(ClientFlow.GuestsCount))
async def got_guests_show_summary(message: Message, state: FSMContext) -> None:
    guests = parse_guests(message.text)
    if guests is None:
        await message.answer("Мне нужно целое число от 1 до 12. Попробуй ещё.")
        return

    await state.update_data(guests=guests)
    data = await state.get_data()

    summary = (
        "Сводка заявки:\n"
        f"• Имя: {data.get('fullname')}\n"
        f"• Телефон: {data.get('phone')}\n"
        f"• Гостей: {data.get('guests')}\n"
        "\nСтатус: draft. Дальше добавим выбор времени и холд."
    )

    await message.answer(summary)
    await state.set_state(ClientFlow.Summary)
