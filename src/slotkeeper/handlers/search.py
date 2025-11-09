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
from slotkeeper.fsm.states import ClientFlow

from slotkeeper.core.booking.shared import REPO
from slotkeeper.core.notify.notifier import NOTIFY
from slotkeeper.ui.keyboards import times_kb, admin_booking_actions_kb, duration_kb
import re
from datetime import date
from dataclasses import dataclass

from slotkeeper.ui.keyboards import month_kb

DISPLAY_START_HOUR = 9
DISPLAY_END_HOUR   = 22

router = Router()

_DATE_RE = re.compile(r"^\s*(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})\s*$")

@dataclass
class Span:
    start: datetime
    end: datetime


def merge_spans(spans: list[Span]) -> list[Span]:
    if not spans:
        return []
    spans = sorted(spans, key=lambda s: s.start)
    merged: list[Span] = [spans[0]]
    for s in spans[1:]:
        last = merged[-1]
        if s.start <= last.end:
            last.end = max(last.end, s.end)
        else:
            merged.append(s)
    return merged

def calc_free_starts(
    day_start: datetime,
    day_end: datetime,
    busy: list[Span],
    step: timedelta,
    min_duration: timedelta,
) -> list[datetime]:
    busy = merge_spans(busy)
    t = day_start
    out: list[datetime] = []
    while t + min_duration <= day_end:
        conflict = False
        for b in busy:
            if not ((t + min_duration) <= b.start or t >= b.end):
                conflict = True
                break
        if not conflict:
            out.append(t)
        t += step
    return out

def _visible_starts(starts: list[datetime]) -> list[datetime]:
    return [dt for dt in starts if DISPLAY_START_HOUR <= dt.hour < DISPLAY_END_HOUR]



@router.message(StateFilter(ClientFlow.Summary))
async def manual_date_input(message: Message, state: FSMContext) -> None:
    m = _DATE_RE.match(message.text or "")
    if not m:
        return
    d, mo, y = map(int, m.groups())
    try:
        picked = date(y, mo, d)
    except ValueError:
        await message.answer("Некорректная дата. Формат: ДД.ММ.ГГГГ")
        return

    settings = Settings()
    tz = ZoneInfo(settings.APP_TIMEZONE)

    day_start = datetime.combine(picked, datetime.min.time()).replace(tzinfo=tz)
    day_end = day_start + timedelta(days=1)

    post_buf = timedelta(minutes=settings.CLEANING_POST_MIN)

    busy = []
    for b in REPO.all():
        if b.status not in {BookingStatus.confirmed, BookingStatus.pending_review}:
            continue
        if b.starts_at < day_end and (b.ends_at + post_buf) > day_start:
            start = max(b.starts_at, day_start)
            end = min(b.ends_at + post_buf, day_end)
            busy.append(type("TS", (), {"start": start, "end": end})())

    step = timedelta(hours=1)
    min_duration = timedelta(minutes=settings.SLOT_DEFAULT_MIN)

    free_starts = calc_free_starts(day_start, day_end, busy, step, min_duration)
    free_starts = _visible_starts(free_starts)
    if not free_starts:
        await message.answer("На этот день нет стартов в окне 09:00–22:00. Попробуй другой день.")
        return

    iso_list = [dt.isoformat() for dt in free_starts]
    await message.answer(
        f"Доступные старты на {picked.isoformat()} (по часу):",
        reply_markup=times_kb(iso_list),
    )

@router.message(StateFilter(ClientFlow.Summary))
async def after_summary_show_calendar(message: Message, state: FSMContext) -> None:
    settings = Settings()
    tz = ZoneInfo(settings.APP_TIMEZONE)
    now = datetime.now(tz).date()
    max_day = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
    y, m = now.year, now.month
    total_months = y * 12 + (m - 1) + settings.MAX_MONTHS_AHEAD
    max_year = total_months // 12
    max_month = total_months % 12 + 1
    max_day = date(max_year, max_month, 1) - timedelta(days=1)

    await message.answer(
        "Выбери день на календаре или введи дату текстом в формате ДД.ММ.ГГГГ.",
        reply_markup=month_kb(
            y, m, settings.APP_TIMEZONE, min_date=now, max_date=max_day
        ),
    )


def _month_bounds(now: date, months_ahead: int) -> tuple[date, date]:
    y, m = now.year, now.month
    total_months = y * 12 + (m - 1) + months_ahead
    max_year = total_months // 12
    max_month = total_months % 12 + 1
    max_day = date(max_year, max_month, 1) - timedelta(days=1)
    return now, max_day


@router.callback_query(StateFilter(ClientFlow.Summary), F.data.startswith("cal:"))
async def calendar_navigate(cb: CallbackQuery) -> None:
    settings = Settings()
    tz = ZoneInfo(settings.APP_TIMEZONE)
    now = datetime.now(tz).date()
    min_day, max_day = _month_bounds(now, settings.MAX_MONTHS_AHEAD)

    _, ym, step = cb.data.split(":")
    year, month = map(int, ym.split("-"))
    step_int = int(step)

    month = month + step_int
    year += (month - 1) // 12
    month = (month - 1) % 12 + 1

    await cb.message.edit_reply_markup(
        reply_markup=month_kb(
            year, month, settings.APP_TIMEZONE, min_date=min_day, max_date=max_day
        )
    )
    await cb.answer()


@router.callback_query(StateFilter(ClientFlow.Summary), F.data.startswith("day:"))
async def pick_day(cb: CallbackQuery, state: FSMContext) -> None:
    settings = Settings()
    tz = ZoneInfo(settings.APP_TIMEZONE)
    picked_date = datetime.fromisoformat(cb.data.split(":", 1)[1]).date()

    day_start = datetime.combine(picked_date, datetime.min.time()).replace(tzinfo=tz)
    day_end   = day_start + timedelta(days=1)
    post_buf = timedelta(minutes=settings.CLEANING_POST_MIN)

    busy: list[Span] = []
    for b in REPO.all():
        if b.status not in {BookingStatus.confirmed, BookingStatus.pending_review}:
            continue
        if b.starts_at < day_end and (b.ends_at + post_buf) > day_start:
            start = max(b.starts_at, day_start)
            end = min(b.ends_at + post_buf, day_end)
            busy.append(Span(start=start, end=end))

    step = timedelta(hours=1)
    min_duration = timedelta(minutes=settings.SLOT_DEFAULT_MIN)

    free_starts = calc_free_starts(day_start, day_end, busy, step, min_duration)
    free_starts = _visible_starts(free_starts)
    if not free_starts:
        await cb.message.answer("На этот день нет стартов в окне 09:00–22:00. Попробуй другой день.")
        await cb.answer()
        return

    iso_list = [dt.isoformat() for dt in free_starts]
    await cb.message.answer(
        f"Доступные старты на {picked_date.isoformat()} (по часу):",
        reply_markup=times_kb(iso_list),
    )
    await cb.answer()

@router.callback_query(StateFilter(ClientFlow.Summary), F.data.startswith("tm:"))
async def pick_time(cb: CallbackQuery, state: FSMContext) -> None:
    settings = Settings()
    tz = ZoneInfo(settings.APP_TIMEZONE)

    start_dt = datetime.fromisoformat(cb.data.split(":", 1)[1]).astimezone(tz)
    await state.update_data(start_iso=start_dt.isoformat())

    hours = [int(x) for x in settings.SLOT_PRESETS_HOURS.split(",") if x.strip()]
    await cb.message.answer(
        "Выбери длительность брони:", reply_markup=duration_kb(hours)
    )
    await state.set_state(ClientFlow.PickDuration)
    await cb.answer()


@router.callback_query(StateFilter(ClientFlow.PickDuration), F.data.startswith("dur:"))
async def pick_duration_and_hold(cb: CallbackQuery, state: FSMContext) -> None:
    settings = Settings()
    tz = ZoneInfo(settings.APP_TIMEZONE)

    data = await state.get_data()
    try:
        fullname = data["fullname"]
        phone = data["phone"]
        guests = int(data["guests"])
        start_dt = datetime.fromisoformat(data["start_iso"]).astimezone(tz)
    except KeyError:
        await cb.message.answer("Сначала заполни анкету (/start → ok).")
        await cb.answer()
        return

    hours = int(cb.data.split(":", 1)[1])
    end_dt = start_dt + timedelta(hours=hours)

    post_buf = timedelta(minutes=settings.CLEANING_POST_MIN)
    for b in REPO.conflicts(start_dt, end_dt + post_buf):
        await cb.message.answer(
            "Этот интервал конфликтует с существующей бронью/клинингом. Выбери другое время."
        )
        await cb.answer()
        return

    booking = Booking(
        id=0,
        customer=Customer(full_name=fullname, phone=phone, guests=guests),
        starts_at=start_dt,
        ends_at=end_dt,
        status=BookingStatus.draft,
        client_chat_id=(cb.message.chat.id if cb.message else cb.from_user.id),
    )
    booking = REPO.add(booking)
    booking.set_hold(minutes=settings.HOLD_MINUTES, tz=settings.APP_TIMEZONE)
    REPO.update(booking)

    NOTIFY.schedule_hold_warning(booking.id)

    admin_text = (
        f"Новая заявка #{booking.id}\n"
        f"Интервал: {start_dt.strftime('%Y-%m-%d %H:%M')} – {end_dt.strftime('%Y-%m-%d %H:%M')}\n"
        f"Клиент: {fullname}\nТелефон: {phone}\nГостей: {guests}\n"
        f"Статус: {booking.status}\n"
        f"Клининг: +{settings.CLEANING_POST_MIN} мин после окончания\n"
        f"Холд до: {booking.hold_deadline.strftime('%H:%M') if booking.hold_deadline else '—'}"
    )
    for admin_id in settings.admin_ids:
        try:
            await cb.bot.send_message(
                admin_id, admin_text, reply_markup=admin_booking_actions_kb(booking.id)
            )
        except Exception:
            pass

    await cb.message.answer(
        f"Заявка #{booking.id}: {start_dt:%Y-%m-%d %H:%M} – {end_dt:%Y-%m-%d %H:%M}. "
        f"После брони резервируем {settings.CLEANING_POST_MIN} мин на клининг. "
        f"Холд {settings.HOLD_MINUTES} мин, статус: {booking.status}."
    )
    await state.set_state(ClientFlow.WaitAdmin)
    await cb.answer()


