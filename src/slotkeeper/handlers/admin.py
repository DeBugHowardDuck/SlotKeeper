from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram.enums import ParseMode
from aiogram.filters import Command as CommandFilter

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from slotkeeper.config import Settings
from slotkeeper.core.booking.shared import REPO
from slotkeeper.core.booking.models import BookingStatus
from slotkeeper.ui.keyboards import contact_kb

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
            await cb.bot.send_message(
                b.client_chat_id,
                (
                    f"✅ Ваша бронь подтверждена!\n"
                    f"📝 Заявка #{b.id}\n"
                    f"🕓 {b.starts_at:%Y-%m-%d %H:%M} – {b.ends_at:%H:%M}\n\n"
                    f"ℹ️ Информация о месте:\n"
                    f"📍 Адрес: {settings.PLACE_ADDRESS}\n"
                    f"🗺 <a href='{settings.PLACE_MAP_URL}'>Открыть в карте</a>\n\n"
                    f"💬 Если возникнут вопросы — нажмите кнопку ниже."
                ),
                reply_markup=contact_kb(),
                parse_mode="HTML",
            )
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
        await cb.message.edit_text(
            cb.message.text + "\n\nСтатус: 🛑 отклонено админом."
        )
    except Exception:
        pass

    if b.client_chat_id:
        try:
            await cb.bot.send_message(
                b.client_chat_id, f"Заявка #{b.id} отклонина администратором."
            )
        except Exception:
            pass

    await cb.answer("Отклонено.")


@router.message(CommandFilter("report"))
async def admin_report(message: Message) -> None:
    settings = Settings()

    if message.from_user.id not in settings.admin_ids:
        await message.answer("❌ Недостаточно прав.")
        return

    tz = ZoneInfo(settings.APP_TIMEZONE)
    now = datetime.now(tz)

    text = ["📊 *Отчёт по бронированиям*"]
    periods = {
        "Сегодня": now.replace(hour=0, minute=0, second=0, microsecond=0),
        "Неделя": now - timedelta(days=7),
        "Месяц": now - timedelta(days=30),
    }

    for label, start in periods.items():
        bookings = [b for b in REPO.all() if b.starts_at >= start]
        total = len(bookings)
        if total == 0:
            text.append(f"\n*{label}:* — нет заявок")
            continue

        stats: dict[str, int] = {}
        for b in bookings:
            stats[b.status] = stats.get(b.status, 0) + 1

        confirmed = stats.get(BookingStatus.confirmed, 0)
        load = confirmed / total * 100

        text.append(
            f"\n*{label}:* {total} заявок\n"
            f"✅ Подтверждено: {confirmed}\n"
            f"🕒 На рассмотрении: {stats.get(BookingStatus.pending_review, 0)}\n"
            f"❌ Отменено: {stats.get(BookingStatus.cancelled_by_admin, 0)}\n"
            f"⌛ Истекло: {stats.get(BookingStatus.expired, 0)}\n"
            f"📈 Загрузка: {load:.1f}%"
        )

    await message.answer("\n".join(text), parse_mode=ParseMode.MARKDOWN)
