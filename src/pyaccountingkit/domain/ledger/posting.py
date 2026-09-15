"""Posting service — the pure domain transition from DRAFT to POSTED.

This is the innermost domain service.  Idempotency, account validation and
transactional commit live in the orchestrator layer that calls this one.
"""

from __future__ import annotations

from pyaccountingkit.core.clock import ClockProtocol
from pyaccountingkit.domain.audit.events import AuditEvent
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.ports.audit import AuditLogSinkProtocol


class PostingService:
    """Apply the irreversible DRAFT → POSTED transition of a journal entry."""

    def __init__(self, clock: ClockProtocol, audit_sink: AuditLogSinkProtocol) -> None:
        self._clock = clock
        self._audit_sink = audit_sink

    def post(
        self,
        entry: JournalEntry,
        period: AccountingPeriod,
        user_id: str,
    ) -> JournalEntry:
        """Validate and post *entry*, returning a new POSTED copy.

        Raises
        ------
        EntryAlreadyPostedError
            If the entry is neither DRAFT nor VALIDATED.
        PeriodClosedError
            If the period is closed/locked or the date falls outside.
        UnbalancedEntryError
            If debits and credits do not balance exactly.
        """
        entry.validate_balance()
        if entry.status is not EntryStatus.DRAFT and entry.status is not EntryStatus.VALIDATED:
            from pyaccountingkit.core.errors import EntryAlreadyPostedError

            raise EntryAlreadyPostedError(
                f"Écriture {entry.id} ({entry.status.value}) ne peut être comptabilisée"
            )

        if not period.is_open_for_posting():
            from pyaccountingkit.core.errors import PeriodClosedError

            raise PeriodClosedError(f"La période {period.id} est verrouillée ou clôturée")

        period.assert_date_within(entry.entry_date)

        now = self._clock.now()
        posted = entry.freeze(now)

        self._audit_sink.record(
            AuditEvent(
                event_type="ENTRY_POSTED",
                entity_id=str(entry.id),
                actor_id=user_id,
                occurred_at=now,
                payload={
                    "entry_id": str(entry.id),
                    "period_id": str(entry.period_id),
                    "total_debit": str(posted.total_debit().amount),
                    "total_credit": str(posted.total_credit().amount),
                },
            )
        )
        return posted


__all__ = ["PostingService"]
