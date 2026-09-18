"""Strict mappings between Django persistence rows and immutable domain objects."""

from __future__ import annotations

from pyaccountingkit.adapters.django.models import (
    AccountingPeriodModel,
    JournalEntryModel,
    JournalLineModel,
    JournalModel,
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


def journal_to_domain(model: JournalModel) -> Journal:
    return Journal(
        id=JournalId(model.pk),
        entity_id=EntityId(model.entity_id),
        code=model.code,
        label=model.label,
        active=model.active,
    )


def journal_to_model(journal: Journal) -> JournalModel:
    return JournalModel(
        id=str(journal.id),
        entity_id=str(journal.entity_id),
        code=journal.code,
        label=journal.label,
        active=journal.active,
    )


def period_to_domain(model: AccountingPeriodModel) -> AccountingPeriod:
    return AccountingPeriod(
        id=PeriodId(model.pk),
        entity_id=EntityId(model.entity_id),
        fiscal_year_id=FiscalYearId(model.fiscal_year_id),
        start_date=model.start_date,
        end_date=model.end_date,
        status=ClosingStatus(model.status),
    )


def period_to_model(period: AccountingPeriod) -> AccountingPeriodModel:
    return AccountingPeriodModel(
        id=str(period.id),
        entity_id=str(period.entity_id),
        fiscal_year_id=str(period.fiscal_year_id),
        start_date=period.start_date,
        end_date=period.end_date,
        status=period.status.value,
    )


def line_to_domain(model: JournalLineModel) -> JournalLine:
    currency = Currency(
        CurrencyCode(model.currency_code),
        exponent=model.currency_exponent,
    )
    return JournalLine(
        account_id=AccountId(model.account_id),
        debit=Money(model.debit_amount, currency),
        credit=Money(model.credit_amount, currency),
        label=model.label,
    )


def line_to_model(entry_id: str, line_number: int, line: JournalLine) -> JournalLineModel:
    return JournalLineModel(
        entry_id=entry_id,
        line_number=line_number,
        account_id=str(line.account_id),
        debit_amount=line.debit.amount,
        credit_amount=line.credit.amount,
        currency_code=str(line.currency.code),
        currency_exponent=line.currency.exponent,
        label=line.label,
    )


def entry_to_domain(model: JournalEntryModel, *, using: str | None = None) -> JournalEntry:
    database = using or model._state.db or "default"
    lines = tuple(
        line_to_domain(row)
        for row in JournalLineModel.objects.using(database)
        .filter(entry_id=model.pk)
        .order_by("line_number", "id")
    )
    return JournalEntry(
        id=EntryId(model.pk),
        journal_id=JournalId(model.journal_id),
        period_id=PeriodId(model.period_id),
        entry_date=model.entry_date,
        description=model.description,
        lines=lines,
        status=EntryStatus(model.status),
        posted_at=model.posted_at,
        reversal_of_id=EntryId(model.reversal_of_id) if model.reversal_of_id else None,
        reversed_by_id=EntryId(model.reversed_by_id) if model.reversed_by_id else None,
    )


def entry_to_model(entry: JournalEntry, *, revision: int = 0) -> JournalEntryModel:
    return JournalEntryModel(
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
    "entry_to_model",
    "journal_to_domain",
    "journal_to_model",
    "line_to_domain",
    "line_to_model",
    "period_to_domain",
    "period_to_model",
]
