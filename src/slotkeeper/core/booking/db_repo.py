from sqlalchemy import select, and_
from sqlalchemy.orm import Session, joinedload, selectinload

from slotkeeper.db.models import (
    Booking as DBBooking,
    Customer as DBCustomer,
    BookingService,
    Service,
)
from slotkeeper.core.booking.models import Booking, Customer, BookingStatus

def _to_domain(db: DBBooking) -> Booking:
    raw = db.status
    if hasattr(raw, "value"):
        raw = raw.value
    status = BookingStatus(raw)

    cust = Customer(
        full_name=db.customer.full_name,
        phone=db.customer.phone,
        guests=db.customer.guests,
    )

    return Booking(
        id=db.id,
        customer=cust,
        starts_at=db.starts_at,
        ends_at=db.ends_at,
        status=status,
        hold_deadline=db.hold_deadline,
        client_chat_id=db.client_chat_id,
    )


class DBRepo:
    def __init__(self, session: Session):
        self.s = session

    def get(self, booking_id: int) -> Booking | None:
        stmt = (
            select(DBBooking)
            .where(DBBooking.id == booking_id)
            .options(
                joinedload(DBBooking.customer),
                selectinload(DBBooking.services).joinedload(BookingService.service),
            )
        )
        row = self.s.execute(stmt).unique().scalar_one_or_none()
        return _to_domain(row) if row else None

    def all(self) -> list[Booking]:
        stmt = (
            select(DBBooking)
            .options(
                joinedload(DBBooking.customer),
                selectinload(DBBooking.services).joinedload(BookingService.service),
            )
            .order_by(DBBooking.id.desc())
        )
        rows = self.s.execute(stmt).unique().scalars().all()
        return [_to_domain(r) for r in rows]

    def conflicts(self, start_dt, end_dt) -> list[Booking]:
        stmt = select(DBBooking).where(
            and_(DBBooking.starts_at < end_dt, DBBooking.ends_at > start_dt)
        )
        rows = self.s.execute(stmt).scalars().all()
        return [_to_domain(r) for r in rows]

    def add(self, booking: Booking, services: list[str] | None = None) -> Booking:
        db_cust = DBCustomer(
            full_name=booking.customer.full_name,
            phone=booking.customer.phone,
            guests=booking.customer.guests,
        )
        self.s.add(db_cust)
        self.s.flush()

        status_val = booking.status.value if hasattr(booking.status, "value") else str(booking.status)
        db_booking = DBBooking(
            customer_id=db_cust.id,
            starts_at=booking.starts_at,
            ends_at=booking.ends_at,
            status=status_val,
            hold_deadline=booking.hold_deadline,
            client_chat_id=booking.client_chat_id,
        )
        self.s.add(db_booking)
        self.s.flush()

        if services:
            srv_rows = (
                self.s.execute(select(Service).where(Service.name.in_(services)))
                .scalars()
                .all()
            )
            for srv in srv_rows:
                self.s.add(BookingService(booking_id=db_booking.id, service_id=srv.id))

        self.s.flush()
        return _to_domain(db_booking)

    def update(self, booking: Booking, services: list[str] | None = None) -> Booking:
        db = self.s.get(DBBooking, booking.id)
        if not db:
            raise ValueError(f"Booking #{booking.id} not found")

        db.starts_at = booking.starts_at
        db.ends_at = booking.ends_at
        db.hold_deadline = booking.hold_deadline
        db.client_chat_id = booking.client_chat_id
        db.status = booking.status.value if hasattr(booking.status, "value") else str(booking.status)

        if db.customer:
            db.customer.full_name = booking.customer.full_name
            db.customer.phone = booking.customer.phone
            db.customer.guests = booking.customer.guests

        if services is not None:
            db.services.clear()
            if services:
                srv_rows = (
                    self.s.execute(select(Service).where(Service.name.in_(services)))
                    .scalars()
                    .all()
                )
                for srv in srv_rows:
                    db.services.append(BookingService(booking_id=db.id, service_id=srv.id))

        self.s.flush()
        return _to_domain(db)
