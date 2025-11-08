from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..fsm.states import ClientFlow

router = Router()


@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Привет! Я SlotKeeper. Помогаю бронировать слоты без оплаты в боте.\n"
        "Готов пройтись по правилам? Напиши «Ок» или нажми /ok"
    )
    await state.set_state(ClientFlow.ConsentRules)


@router.message(Command("ok"))
@router.message(StateFilter(ClientFlow.ConsentRules), F.text.casefold() == "ок")
@router.message(StateFilter(ClientFlow.ConsentRules), F.text.casefold() == "ok")
async def accept_rules(message: Message, state: FSMContext) -> None:
    await state.set_state(ClientFlow.ContactCollect)
    await message.answer("Окей. Введи, пожалуйста, своё имя.")


@router.message(StateFilter(None))
async def fallback(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    await message.answer(
        f"Сейчас состояние: {current or '—'}. "
        f"Я не знаю, что делать с этим сообщением."
    )
