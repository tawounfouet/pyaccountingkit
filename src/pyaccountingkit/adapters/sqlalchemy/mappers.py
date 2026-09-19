"""Strict mappings between SQLAlchemy rows and immutable domain objects."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from pyaccountingkit.adapters.sqlalchemy.tables import (
    AccountingPeriodTable,
    JournalEntryTable,
    JournalLineTable,
    JournalTable,
)
from pyaccountingkit.core.currency import Currency, CurrencyCode
from pyaccountingkit.core.identifiers import (
    AccountId,
    EntityId,
    EntryId,
    FiscalYearId,
    JournalId,
    PeriodId,
)
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.periods.closing_status import ClosingStatus


def journal_to_domain(row: JournalTable) -> Journal:
    return Journal(
        id=JournalId(row.id),
        entity_id=EntityId(row.entity_id),
        code=row.code,
        label=row.label,
        active=row.active,
    )


def journal_to_table(journal: Journal) -> JournalTable:
    return JournalTable(
        id=str(journal.id),
        entity_id=str(journal.entity_id),
        code=journal.code,
        label=journal.label,
        active=journal.active,
    )


def period_to_domain(row: AccountingPeriodTable) -> AccountingPeriod:
    return AccountingPeriod(
        id=PeriodId(row.id),
        entity_id=EntityId(row.entity_id),
        fiscal_year_id=FiscalYearId(row.fiscal_year_id),
        start_date=row.start_date,
        end_date=row.end_date,
        status=ClosingStatus(row.status),
    )


def period_to_table(period: AccountingPeriod) -> AccountingPeriodTable:
    return AccountingPeriodTable(
        id=str(period.id),
        entity_id=str(period.entity_id),
        fiscal_year_id=str(period.fiscal_year_id),
        start_date=period.start_date,
        end_date=period.end_date,
        status=period.status.value,
    )


def line_to_domain(row: JournalLineTable) -> JournalLine:
    currency = Currency(
        CurrencyCode(row.currency_code),
        exponent=row.currency_exponent,
    )
    return JournalLine(
        account_id=AccountId(row.account_id),
        debit=Money(row.debit_amount, currency),
        credit=Money(row.credit_amount, currency),
        label=row.label,
    )


def line_to_table(entry_id: str, line_number: int, line: JournalLine) -> JournalLineTable:
    return JournalLineTable(
        entry_id=entry_id,
        line_number=line_number,
        account_id=str(line.account_id),
        debit_amount=line.debit.amount,
        credit_amount=line.credit.amount,
        currency_code=str(line.currency.code),
        currency_exponent=line.currency.exponent,
        label=line.label,
    )


def entry_to_domain(session: Session, row: JournalEntryTable) -> JournalEntry:
    lines = tuple(
        line_to_domain(line)
        for line in session.scalars(
            select(JournalLineTable)
            .where(JournalLineTable.entry_id == row.id)
            .order_by(JournalLineTable.line_number, JournalLineTable.id)
        )
    )
    return JournalEntry(
        id=EntryId(row.id),
        journal_id=JournalId(row.journal_id),
        period_id=PeriodId(row.period_id),
        entry_date=row.entry_date,
        description=row.description,
        lines=lines,
        status=EntryStatus(row.status),
        posted_at=row.posted_at,
        reversal_of_id=EntryId(row.reversal_of_id) if row.reversal_of_id else None,
        reversed_by_id=EntryId(row.reversed_by_id) if row.reversed_by_id else None,
    )


def entry_to_table(entry: JournalEntry, *, revision: int = 0) -> JournalEntryTable:
    return JournalEntryTable(
        id=str(entry.id),
        journal_id=str(entry.journal_id),
        period_id=str(entry.period_id),
        entry_date=entry.entry_date,
        description=entry.description,
        status=entry.status.value,
        posted_at=entry.posted_at,
        reversal_of_id=str(entry.reversal_of_id) if entry.reversal_of_id else None,
        reversed_by_id=str(entry.reversed_by_id) if entry.reversed_by_id else None,
        revision=revision,
    )


__all__ = [
    "entry_to_domain",
    "entry_to_table",
    "journal_to_domain",
    "journal_to_table",
    "line_to_domain",
    "line_to_table",
    "period_to_domain",
    "period_to_table",
]
