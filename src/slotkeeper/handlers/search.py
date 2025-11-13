from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from slotkeeper.config import Settings
from slotkeeper.core.booking.models import BookingStatus, Booking, Customer
from slotkeeper.fsm.states import ClientFlow

from slotkeeper.core.booking.shared import repo_scope

import re
from datetime import date
from dataclasses import dataclass
from slotkeeper.ui.keyboards import (
    times_kb,
    admin_booking_actions_kb,
    duration_kb,
    month_kb,
    start_kb,
)



from typing import Optional

DISPLAY_START_HOUR = 9
DISPLAY_END_HOUR = 22

router = Router()

_DATE_RE = re.compile(r"^\s*(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})\s*$")


@dataclass
class Span:
    start: datetime
    end: datetime


def _safe_bd_this_year(bd: date, year: int) -> date:
    try:
        return date(year, bd.month, bd.day)
    except ValueError:
        return date(year, 2, 28)


def in_birthday_window(picked: date, birth_iso: Optional[str], window_days: int = 7) -> tuple[bool, date, date]:
    if not birth_iso:
        return (False, picked, picked)
    bd = datetime.fromisoformat(birth_iso).date()
    anchor = _safe_bd_this_year(bd, picked.year)
    start = anchor - timedelta(days=window_days)
    end = anchor + timedelta(days=window_days)
    return (start <= picked <= end, start, end)


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

    data = await state.get_data()
    eligible, win_start, win_end = in_birthday_window(picked, data.get("birth_date"), window_days=7)

    badge = ""
    if eligible:
        badge = (
            "🎉 <b>Вы попадаете в окно скидки по ДР!</b>\n"
            f"Действует: {win_start.strftime('%d.%m.%Y')} — {win_end.strftime('%d.%m.%Y')}\n\n"
        )

    busy = []
    with repo_scope() as REPO:
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
        badge + "⌚ Выберите время:",
        reply_markup=times_kb(iso_list),
        parse_mode="HTML",
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
    day_end = day_start + timedelta(days=1)
    post_buf = timedelta(minutes=settings.CLEANING_POST_MIN)

    data = await state.get_data()
    eligible, win_start, win_end = in_birthday_window(picked_date, data.get("birth_date"), window_days=7)

    badge = ""
    if eligible:
        badge = (
            "🎉 <b>Вы попадаете в окно скидки по ДР!</b>\n"
            f"Действует: {win_start.strftime('%d.%m.%Y')} — {win_end.strftime('%d.%m.%Y')}\n\n"
        )

    busy: list[Span] = []
    with repo_scope() as REPO:
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
        badge + "⌚ Выберите время:",
        reply_markup=times_kb(iso_list),
        parse_mode="HTML",
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
        "⌛ Выбери <b>длительность брони</b>:", reply_markup=duration_kb(hours)
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
    with repo_scope() as REPO:
        for b in REPO.conflicts(start_dt, end_dt + post_buf):
            await cb.message.answer(
                "Этот интервал конфликтует с существующей бронью/клинингом. Выбери другое время."
            )
            await cb.answer()
            return

    data = await state.get_data()
    selected_services = data.get("services", [])
    services_text = ", ".join(selected_services) if selected_services else "—"

    data = await state.get_data()
    eligible, win_start, win_end = in_birthday_window(start_dt.date(), data.get("birth_date"), window_days=7)
    bd_line = "да" if eligible else "нет"

    booking = Booking(
        id=0,
        customer=Customer(full_name=fullname, phone=phone, guests=guests),
        starts_at=start_dt,
        ends_at=end_dt,
        status=BookingStatus.draft,
        client_chat_id=(cb.message.chat.id if cb.message else cb.from_user.id),
    )

    with repo_scope() as repo:

        booking = repo.add(booking, services=selected_services)
        booking.set_hold(minutes=settings.HOLD_MINUTES, tz=settings.APP_TIMEZONE)
        repo.update(booking)
        booking_id = booking.id

        admin_text = (
            f"🎟️ <b>Новая заявка! # {booking.id}</b>\n\n"
            f"🕓 Интервал: {start_dt:%Y-%m-%d %H:%M} – {end_dt:%H:%M}\n\n"
            f"👤 Имя: {fullname}\n"
            f"📞 Телефон: {phone}\n\n"
            f"👥 Гостей: {guests}\n"
            f"🧾 Услуги: {services_text}\n\n"
            f"🎂 Скидка по ДР: {bd_line}\n"
        )

        for admin_id in settings.admin_ids:
            try:
                await cb.bot.send_message(
                    admin_id,
                    admin_text,
                    reply_markup=admin_booking_actions_kb(booking_id),
                )
            except Exception:
                pass

        await cb.message.answer(
            f"⏳📝 Заявка # {booking.id} в обработке:\n\n"
            f"🕓 {start_dt:%Y-%m-%d %H:%M} – {end_dt:%H:%M}.\n\n"
            f"💬 Я напишу, как только администратор подтвердит бронирование."
        )

        await state.set_state(ClientFlow.WaitAdmin)
        await cb.answer()


@router.callback_query(F.data == "contact_admin")
async def contact_admin_callback(cb: CallbackQuery, state: FSMContext):
    settings = Settings()
    data = await state.get_data()
    fullname = data.get("fullname", cb.from_user.full_name or "—")
    phone = data.get("phone", "не указан")
    guests = data.get("guests", "—")

    await cb.message.answer(
        "✅ Мы уведомили администратора — он скоро с тобой свяжется."
    )

    for admin_id in settings.admin_ids:
        try:
            await cb.bot.send_message(
                admin_id,
                (
                    "📞 <b>Запрос связи от клиента</b>\n\n"
                    f"👤 Имя: {fullname}\n"
                    f"📱 Телефон: {phone}\n"
                    f"👥 Гостей: {guests}\n"
                    f"💬 Telegram: @{cb.from_user.username or '—'}\n"
                    f"🆔 ID: <code>{cb.from_user.id}</code>"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass
    await cb.answer()
