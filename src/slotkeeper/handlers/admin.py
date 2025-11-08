from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery
from slotkeeper.config import Settings
from slotkeeper.core.booking.shared import REPO
from slotkeeper.core.booking.models import BookingStatus

router = Router()

def _is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_ids

@router.callback_query(F.data.startswith("adm:confirm:"))
async def admin_config(cb: CallbackQuery) -> None:
    settings = Settings()
    if not _is_admin(cb.from_user.id, settings):
        await cb.answer("Недостаточно прав.", show_alert=True)
        return

    booking_id = int(cb.data.split(":")[-1])
    b = REPO.get(booking_id)
    if not b:
        await cb.answer("Заявка не найдена.", show_alert=True)
        return

    if b.status not in {BookingStatus.pending_review}:
        await cb.answer(f"Статус уже {b.status}.", show_alert=True)
        return

    b.status = BookingStatus.confirmed
    REPO.update(b)

    try:
        await cb.message.edit_text(cb.message.text + "\n\nСтатус: ✅ подтверждено.")
    except Exception:
        pass

    if b.client_chat_id:
        try:
            await cb.bot.send_message(b.client_chat_id, f"Заявка #{b.id} подтверждена. Ждем вас!")
        except Exception:
            pass

    await cb.answer("Подтверждено.")


@router.callback_query(F.data.startswith("adm:reject:"))
async def admin_reject(cb: CallbackQuery) -> None:
    settings = Settings()
    if not _is_admin(cb.from_user.id, settings):
        await cb.answer("Ндостаточно прав.", show_alert=True)
        return

    booking_id = int(cb.data.split(":")[-1])
    b = REPO.get(booking_id)
    if not b:
        await cb.answer("Заявка не найдена.", show_alert=True)
        return
    if b.status != BookingStatus.pending_review:
        await cb.answer(f"Статус уже {b.status}.", show_alert=True)
        return

    b.status = BookingStatus.cancelled_by_admin
    REPO.update(b)

    try:
        await cb.message.edit_text(cb.message.text + "\n\nСтатус: 🛑 отклонено админом.")
    except Exception:
        pass

    if b.client_chat_id:
        try:
            await cb.bot.send_message(b.client_chat_id, f"Заявка #{b.id} отклонина администратором.")
        except Exception:
            pass

    await cb.answer("Отклонено.")

