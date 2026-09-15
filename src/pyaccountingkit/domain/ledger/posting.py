"""Posting service — pure domain transition from DRAFT to POSTED.

Idempotency, entity isolation, account validation, audit, outbox publication
and transactional commit belong to the application orchestrator.  This
service only validates the accounting transition and returns an immutable
POSTED copy.
"""

from __future__ import annotations

from pyaccountingkit.core.clock import ClockProtocol
from pyaccountingkit.core.errors import EntryAlreadyPostedError, PeriodClosedError
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod


class PostingService:
    """Apply the irreversible DRAFT/VALIDATED → POSTED domain transition."""

    def __init__(self, clock: ClockProtocol) -> None:
        self._clock = clock

    def post(
        self,
        entry: JournalEntry,
        period: AccountingPeriod,
        user_id: str,
    ) -> JournalEntry:
        """Validate and post *entry*, returning a new POSTED copy.

        ``user_id`` remains part of the stable service signature because the
        application layer uses it for the transactional audit record.  The
        pure domain transition itself does not persist or emit that record.
        """
        del user_id
        entry.validate_balance()
        if entry.status is not EntryStatus.DRAFT and entry.status is not EntryStatus.VALIDATED:
            raise EntryAlreadyPostedError(
                f"Écriture {entry.id} ({entry.status.value}) ne peut être comptabilisée"
            )
        if not period.is_open_for_posting():
            raise PeriodClosedError(f"La période {period.id} est verrouillée ou clôturée")
        period.assert_date_within(entry.entry_date)
        return entry.freeze(self._clock.now())


__all__ = ["PostingService"]
