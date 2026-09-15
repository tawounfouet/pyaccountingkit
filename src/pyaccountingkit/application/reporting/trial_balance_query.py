"""Trial balance use-case — aggregates POSTED entries into a verified snapshot."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from pyaccountingkit.core.currency import EUR, Currency
from pyaccountingkit.core.identifiers import PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.reporting.balance_line import AccountBalanceLine
from pyaccountingkit.domain.reporting.trial_balance import (
    TrialBalance,
    TrialBalanceSnapshot,
)
from pyaccountingkit.ports.unit_of_work import UnitOfWorkFactoryProtocol


class TrialBalanceQuery:
    """Computes a trial balance from the reference journal-entry repository.

    Only POSTED entries contribute; draft and validated entries are
    excluded. Ordering is deterministic (account code asc, then checksum
    of the aggregated lines).
    """

    def __init__(
        self,
        uow_factory: UnitOfWorkFactoryProtocol,
        chart: CompanyChartOfAccounts,
    ) -> None:
        self._uow_factory = uow_factory
        self._chart = chart

    def balance_for(
        self,
        period_id: PeriodId,
        snapshot: TrialBalanceSnapshot = TrialBalanceSnapshot.BEFORE_ADJUSTMENTS,
    ) -> TrialBalance:
        """Return the verified trial balance of one period."""
        with self._uow_factory.open() as uow:
            entries = uow.entries.list_by_period(period_id)
            lines = self._aggregate(entries)
        return TrialBalance.build(
            period_id,
            snapshot,
            lines,
            accounting_entity_id=self._chart.entity_id,
        )

    def drill_down(
        self,
        period_id: PeriodId,
        account_code: str,
    ) -> Sequence[tuple[object, JournalLine]]:
        """Return the underlying journal lines of one account for drill-down."""
        with self._uow_factory.open() as uow:
            entries = uow.entries.list_by_period(period_id)
            matching: list[tuple[object, JournalLine]] = []
            for entry in entries:
                for line in entry.lines:
                    if str(line.account_id) == account_code:
                        matching.append((entry.id, line))
            return tuple(matching)

    def _aggregate(
        self,
        entries: Sequence[JournalEntry],
    ) -> tuple[AccountBalanceLine, ...]:
        currency = self._default_currency(entries)
        buckets: dict[str, list[Money]] = defaultdict(
            lambda: [Money.zero(currency), Money.zero(currency)]
        )
        for entry in entries:
            for line in entry.lines:
                bucket = buckets[str(line.account_id)]
                bucket[0] = bucket[0] + line.debit
                bucket[1] = bucket[1] + line.credit
        return tuple(
            AccountBalanceLine(
                account_code=code,
                label=self._label(code),
                sum_debit=bucket[0],
                sum_credit=bucket[1],
            )
            for code, bucket in sorted(buckets.items())
        )

    def _default_currency(self, entries: Sequence[JournalEntry]) -> Currency:
        if not entries:
            return EUR
        return entries[0].lines[0].currency

    def _label(self, code: str) -> str:
        account = self._chart.get_by_code(code)
        return account.label if account is not None else code


__all__ = ["TrialBalanceQuery"]
