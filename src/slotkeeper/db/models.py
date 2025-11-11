from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, BigInteger, String, Date, DateTime, Enum, Boolean,
    ForeignKey, CheckConstraint, UniqueConstraint, func
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()

class BookingStatusEnum(str, enum.Enum):
    draft = "draft"
    pending_review = "pending_review"
    confirmed = "confirmed"
    cancelled_by_admin = "cancelled_by_admin"
    cancelled_by_client = "cancelled_by_client"
    expired = "expired"

class Customer(Base):
    __tablename__ = "customers"
    id = Column(BigInteger, primary_key=True)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    guests = Column(Integer, nullable=False)
    birth_date = Column(Date, nullable=True)
    age = Column(Integer, nullable=True)
    __table_args__ = (
        CheckConstraint("guests BETWEEN 1 AND 12", name="ck_customers_guests"),
    )
    bookings = relationship("Booking", back_populates="customer")

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(BigInteger, primary_key=True)
    customer_id = Column(BigInteger, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at   = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(BookingStatusEnum, name="booking_status"), nullable=False, default=BookingStatusEnum.draft)
    hold_deadline = Column(DateTime(timezone=True), nullable=True)
    client_chat_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="ck_bookings_time"),
    )
    customer = relationship("Customer", back_populates="bookings")
    services = relationship("BookingService", back_populates="booking", cascade="all, delete-orphan")

class Service(Base):
    __tablename__ = "services"
    id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    adult_only = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=100)

class BookingService(Base):
    __tablename__ = "booking_services"
    booking_id = Column(BigInteger, ForeignKey("bookings.id", ondelete="CASCADE"), primary_key=True)
    service_id = Column(BigInteger, ForeignKey("services.id"), primary_key=True)

    booking = relationship("Booking", back_populates="services")
    service = relationship("Service")