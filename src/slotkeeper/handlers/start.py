from __future__ import annotations
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..fsm.states import ClientFlow

router = Router()

@router.message(F.text == "/start")
async def start_cmd(message: Message, state: FSMContext) -> None:
    await state.clear()

    await message.answer(
        "Привет! Я SlotKeeper. Помогаю бронировать слоты без оплаты в боте.\n"
        "Готов пройтись по правилам? Напиши: 'Ок' или нажми /ok"
    )
    await state.set_state(ClientFlow.ConsentRules)

@router.message(F.text.in_({"/ok", "Ок", "ок", "OK", "Ok"}))
async def accept_rules(message: Message, state: FSMContext) -> None:
    await message.answer("Отлично введи пожалуйста свое имя.")
    await state.set_state(ClientFlow.ConsentRules)

@router.message(ClientFlow.ContactCollect)
async def collect_name_them_stop(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    data = await state.get_data()
    await message.answer(f"Записал имя: {data.get('name')}..")
    await state.clear()