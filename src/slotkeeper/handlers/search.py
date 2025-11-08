from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from slotkeeper.config import Settings
from slotkeeper.core.availability import generate_slots_for_day
from slotkeeper.core.booking.models import BookingStatus, Booking, Customer
from slotkeeper.core.booking.repo import InMemoryBookingRepo
from slotkeeper.fsm.states import ClientFlow

from slotkeeper.core.booking.shared import REPO
from slotkeeper.core.notify.notifier import NOTIFY
from slotkeeper.ui.keyboards import weekdays_kb, times_kb, admin_booking_actions_kb


router = Router()

_REPO = InMemoryBookingRepo()


@router.message(StateFilter(ClientFlow.Summary))
async def after_summary_show_days(message: Message, state: FSMContext) -> None:
    settings = Settings()
    tz = ZoneInfo(settings.APP_TIMEZONE)
    now = datetime.now(tz)
    await message.answer("Выберите день для брони: ", reply_markup=weekdays_kb(now))


@router.callback_query(F.data.startswith("wk:"))
async def pick_day(cb: CallbackQuery, state: FSMContext) -> None:
    settings = Settings()
    tz = ZoneInfo(settings.APP_TIMEZONE)
    ordinal = int(cb.data.split(":", 1)[1])
    picked_date = datetime.fromordinal(ordinal).replace(tzinfo=tz)

    busy = []
    for b in _REPO.all():
        if (
            b.status in {BookingStatus.confirmed, BookingStatus.pending_review}
            and b.starts_at.date() == picked_date.date()
        ):
            busy.append(type("TS", (), {"start": b.starts_at, "end": b.ends_at})())

    free = generate_slots_for_day(
        picked_date,
        tz_name=settings.APP_TIMEZONE,
        slot_duration=timedelta(hours=2),
        step=timedelta(minutes=30),
        pre_buffer=timedelta(minutes=30),
        post_buffer=timedelta(minutes=60),
        busy=busy,
    )

    if not free:
        await cb.message.answer("На этот день свободных слотов нет. Попробуй другой.")
        await cb.answer()
        return

    iso_list = [s.start.isoformat() for s in free]
    await cb.message.answer(
        f"Доступные слоты на {picked_date.date().isoformat()}:",
        reply_markup=times_kb(iso_list),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("tm:"))
async def pick_time_and_hold(cb: CallbackQuery, state: FSMContext) -> None:
    settings = Settings()
    tz = ZoneInfo(settings.APP_TIMEZONE)

    data = await state.get_data()
    try:
        fullname = data["fullname"]
        phone = data["phone"]
        guests = int(data["guests"])
    except KeyError:
        await cb.message.answer("Сначала заполни анкету (/start → ok).")
        await cb.answer()
        return

    start_dt = datetime.fromisoformat(cb.data.split(":", 1)[1]).astimezone(tz)
    end_dt = start_dt + timedelta(hours=2)

    for b in _REPO.conflicts(start_dt, end_dt):
        await cb.message.answer("Этот интервал только что заняли. Выбери другой.")
        await cb.answer()
        return

    booking = Booking(
        id=0,
        customer=Customer(full_name=fullname, phone=phone, guests=guests),
        starts_at=start_dt,
        ends_at=end_dt,
        status=BookingStatus.draft,
        client_chat_id=(cb.message.chat.id if cb.message else cb.message.from_user.id),
    )

    booking = REPO.add(booking)
    booking.set_hold(minutes=settings.HOLD_MINUTES, tz=settings.APP_TIMEZONE)
    REPO.update(booking)

    NOTIFY.schedule_hold_warning(booking.id)

    admin_text = (
        f"Новая заявка #{booking.id}\n"
        f"Интервал: {start_dt.strftime('%Y-%m-%d %H:%M')}–{end_dt.strftime('%H:%M')}\n"
        f"Клиент: {fullname}\nТелефон: {phone}\nГостей: {guests}\n"
        f"Статус: {booking.status}\n"
        f"Холд до: {booking.hold_deadline.strftime('%H:%M') if booking.hold_deadline else '—'}"
    )
    for admin_id in settings.admin_ids:
        try:
            await cb.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=admin_booking_actions_kb(booking.id),
            )
        except Exception:
            pass

    await cb.message.answer(
        f"Заявка #{booking.id}: {start_dt.strftime('%Y-%m-%d %H:%M')}–{end_dt.strftime('%H:%M')} на холде "
        f"{settings.HOLD_MINUTES} мин. Статус: {booking.status}. "
    )
    await cb.answer()

    await state.set_state(ClientFlow.WaitAdmin)
