from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from ..fsm.states import ClientFlow
from ..ui.keyboards import start_kb

router = Router()

WELCOME = (
    "👋 Привет!\n"
    "Здесь можно <b>забронировать помещение</b> без звонков и бюрократии.\n\n"
    "Нажми кнопку ниже, и я за минуту соберу нужные данные и покажу свободное время.👇"
)


@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME, reply_markup=start_kb())

@router.callback_query(F.data == "start_booking")
async def start_booking(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(ClientFlow.ContactCollect)
    await cb.message.answer(
        "💬 Как к тебе обращаться?\n"
        "Напиши имя и фамилию через пробел. Пример: <b>Иван Петров</b>."
    )
    await cb.answer()


@router.message(StateFilter(None))
async def fallback(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    await message.answer(
        f"Сейчас состояние: {current or '—'}. "
        f"Я не знаю, что делать с этим сообщением."
    )
