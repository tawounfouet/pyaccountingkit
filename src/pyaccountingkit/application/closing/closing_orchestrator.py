"""Closing use-case — seal a period, preserve evidence, carry opening balances."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date

from pyaccountingkit.core.clock import ClockProtocol
from pyaccountingkit.core.errors import PeriodClosedError
from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.domain.closing.closing_run import (
    CloseGate,
    ClosingEvidenceBundle,
    ClosingPhase,
    ClosingRun,
    ClosingRunBook,
)
from pyaccountingkit.domain.closing.opening import (
    OpeningEntryBuilder,
    build_opening_balances,
)
from pyaccountingkit.domain.controls.control import ControlOutcome, ControlRun
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.periods.closing_status import ClosingStatus
from pyaccountingkit.domain.reporting.trial_balance import TrialBalance
from pyaccountingkit.domain.traceability.trace import CanonicalHasher
from pyaccountingkit.ports.unit_of_work import UnitOfWorkFactoryProtocol

RunIdFactory = Callable[[], str]


class ClosingOrchestrator:
    """Runs the full close: gate -> REVIEW -> CLOSING -> CLOSED -> evidence.

    Posting against a period that has reached CLOSING or CLOSED is rejected
    through ``is_open_for_posting`` (close vs posting race).  The sealed
    evidence bundle is append-only, so a later open of the next period can
    never erase the previous closing evidence.  The opening entry built from
    the POST_CLOSING trial balance is POSTED and explicitly references the
    originating closing run (traceable opening generation).
    """

    def __init__(
        self,
        uow_factory: UnitOfWorkFactoryProtocol,
        run_book: ClosingRunBook,
        close_gate: CloseGate,
        run_id_factory: RunIdFactory,
        clock: ClockProtocol,
    ) -> None:
        self._uow_factory = uow_factory
        self._run_book = run_book
        self._close_gate = close_gate
        self._run_id_factory = run_id_factory
        self._clock = clock

    def close_period(
        self,
        period_id: PeriodId,
        control_runs: Sequence[ControlRun],
        trial_balance: TrialBalance,
        *,
        next_period_id: PeriodId | None = None,
        opening_journal_id: JournalId | None = None,
        opening_entry_id: EntryId | None = None,
        opening_date: date | None = None,
    ) -> ClosingRun:
        """Close one period after the blocking controls passed.

        ``trial_balance`` must be the POST_CLOSING snapshot read *before* the
        transition; it is sealed into the evidence so the bundle documents
        the exact state under close.
        """
        failed_codes = [
            run.definition_code for run in control_runs if run.result.outcome is ControlOutcome.FAIL
        ]
        self._close_gate.assert_passes(failed_codes)

        run_id = self._run_id_factory()
        controls_hash = CanonicalHasher.digest(
            {
                "controls": [
                    {"code": run.definition_code, "outcome": run.result.outcome.value}
                    for run in sorted(control_runs, key=lambda run: run.definition_code)
                ]
            }
        )
        evidence = ClosingEvidenceBundle(
            run_id=run_id,
            period_id=str(period_id),
            trial_balance_checksum=trial_balance.checksum,
            control_runs_hash=controls_hash,
            total_debit=str(trial_balance.total_debit.amount),
            total_credit=str(trial_balance.total_credit.amount),
            sealed_at=self._clock.now(),
        )
        run = ClosingRun(
            id=run_id,
            period_id=str(period_id),
            phase=ClosingPhase.RUNNING,
        ).with_evidence(evidence)

        with self._uow_factory.open() as uow:
            period = uow.periods.get(period_id)
            if period.status.is_closed():
                raise PeriodClosedError(f"Période {period_id} déjà close")
            closed = self._advance_to_closed(period)
            uow.periods.save(closed)
            self._carry_opening_balances(
                uow,
                trial_balance=trial_balance,
                next_period_id=next_period_id,
                opening_journal_id=opening_journal_id,
                opening_entry_id=opening_entry_id,
                opening_date=opening_date,
                run_id=run_id,
            )
            uow.commit()
        self._run_book.record(run)
        return run

    def _advance_to_closed(self, period: AccountingPeriod) -> AccountingPeriod:
        current = period
        for target in (ClosingStatus.REVIEW, ClosingStatus.CLOSING, ClosingStatus.CLOSED):
            if current.status.can_transition_to(target):
                current = current.with_status(target)
        if not current.status.is_closed():
            raise PeriodClosedError(
                f"Impossible de clôturer la période {period.id} "
                f"depuis l'état {current.status.value}"
            )
        return current

    def _carry_opening_balances(
        self,
        uow: object,
        *,
        trial_balance: TrialBalance,
        next_period_id: PeriodId | None,
        opening_journal_id: JournalId | None,
        opening_entry_id: EntryId | None,
        opening_date: date | None,
        run_id: str,
    ) -> None:
        if next_period_id is None:
            return
        if opening_journal_id is None or opening_entry_id is None or opening_date is None:
            raise ValueError("Ouverture demandée : journal, écriture et date requis")
        openings = build_opening_balances(trial_balance.lines)
        if not openings:
            return
        entry = OpeningEntryBuilder(opening_date, run_id).build(
            openings,
            journal_id=opening_journal_id,
            period_id=next_period_id,
            entry_id=opening_entry_id,
        )
        uow.entries.add(entry)  # type: ignore[attr-defined]


__all__ = ["ClosingOrchestrator"]
