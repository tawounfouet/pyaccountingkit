"""SQLAlchemy 2.x declarative schema for the canonical PostgreSQL persistence model."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative metadata root for the SQLAlchemy adapter."""


class JournalTable(Base):
    __tablename__ = "pyak_journal"
    __table_args__ = (
        UniqueConstraint("entity_id", "code", name="uq_pyak_journal_entity_code"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    entity_id: Mapped[str] = mapped_column(String(128), index=True)
    code: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AccountingPeriodTable(Base):
    __tablename__ = "pyak_accounting_period"
    __table_args__ = (
        CheckConstraint("start_date <= end_date", name="ck_pyak_period_date_order"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    entity_id: Mapped[str] = mapped_column(String(128), index=True)
    fiscal_year_id: Mapped[str] = mapped_column(String(128), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), index=True)


class JournalEntryTable(Base):
    __tablename__ = "pyak_journal_entry"
    __table_args__ = (
        Index("ix_pyak_entry_period", "period_id", "status", "entry_date"),
        Index("ix_pyak_entry_journal", "journal_id", "status", "entry_date"),
        Index(
            "uq_pyak_entry_full_reversal",
            "reversal_of_id",
            unique=True,
            postgresql_where=text("reversal_of_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    journal_id: Mapped[str] = mapped_column(
        ForeignKey("pyak_journal.id", ondelete="RESTRICT")
    )
    period_id: Mapped[str] = mapped_column(
        ForeignKey("pyak_accounting_period.id", ondelete="RESTRICT")
    )
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), index=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversal_of_id: Mapped[str | None] = mapped_column(
        ForeignKey("pyak_journal_entry.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reversed_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("pyak_journal_entry.id", ondelete="RESTRICT"),
        nullable=True,
    )
    revision: Mapped[int] = mapped_column(BigInteger, default=0)


class JournalLineTable(Base):
    __tablename__ = "pyak_journal_line"
    __table_args__ = (
        UniqueConstraint("entry_id", "line_number", name="uq_pyak_line_entry_number"),
        CheckConstraint(
            "debit_amount >= 0 AND credit_amount >= 0",
            name="ck_pyak_line_nonnegative",
        ),
        CheckConstraint(
            "((debit_amount > 0 AND credit_amount = 0) OR "
            "(credit_amount > 0 AND debit_amount = 0))",
            name="ck_pyak_line_one_sided",
        ),
        CheckConstraint(
            "currency_exponent >= 0 AND currency_exponent <= 4",
            name="ck_pyak_line_currency_exp",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entry_id: Mapped[str] = mapped_column(
        ForeignKey("pyak_journal_entry.id", ondelete="CASCADE"),
        index=True,
    )
    line_number: Mapped[int] = mapped_column(Integer)
    account_id: Mapped[str] = mapped_column(String(128), index=True)
    debit_amount: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    currency_code: Mapped[str] = mapped_column(String(3))
    currency_exponent: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(255), default="")


class AuditEventTable(Base):
    __tablename__ = "pyak_audit_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    entity_id: Mapped[str] = mapped_column(String(128), index=True)
    actor_id: Mapped[str] = mapped_column(String(128))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class IdempotencyRecordTable(Base):
    __tablename__ = "pyak_idempotency"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    status: Mapped[str] = mapped_column(String(16))


class OutboxMessageTable(Base):
    __tablename__ = "pyak_outbox"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    entity_id: Mapped[str] = mapped_column(String(128), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(255), default="", index=True)


__all__ = [
    "AccountingPeriodTable",
    "AuditEventTable",
    "Base",
    "IdempotencyRecordTable",
    "JournalEntryTable",
    "JournalLineTable",
    "JournalTable",
    "OutboxMessageTable",
]
