"""Reversal service — creates a mirror entry that cancels a posted one.

The service itself is pure and persistence-free; it returns immutable
domain objects.  The orchestrator layer persists both the reversal and
the marked original.
"""

from __future__ import annotations

from datetime import date

from pyaccountingkit.core.clock import ClockProtocol
from pyaccountingkit.core.errors import (
    AlreadyReversedError,
    EntryNotPostedError,
    InvalidReversalDateError,
    PeriodClosedError,
)
from pyaccountingkit.core.identifiers import EntryId
from pyaccountingkit.domain.audit.events import AuditEvent
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.ports.audit import AuditLogSinkProtocol


def create_reversal(
    original: JournalEntry,
    reversal_date: date,
    reversal_id: EntryId,
    target_period: AccountingPeriod,
    audit_sink: AuditLogSinkProtocol,
    clock: ClockProtocol,
    user_id: str,
) -> tuple[JournalEntry, JournalEntry]:
    """Create a new posted reversal entry and a copy of the original marked as reversed.

    Returns
    -------
    (marked_original, reversal)
        Both are frozen immutable copies ready for persistence.

    Raises
    ------
    EntryNotPostedError
        If *original* is not POSTED.
    AlreadyReversedError
        If *original* already carries ``reversed_by_id``.
    InvalidReversalDateError
        If *reversal_date* is outside the target period.
    """
    if original.status is not EntryStatus.POSTED:
        raise EntryNotPostedError(
            f"Seules les écritures POSTED peuvent être contrepassées, reçu {original.status.value}"
        )
    if original.reversed_by_id is not None:
        raise AlreadyReversedError(
            f"L'écriture {original.id} est déjà contrepassée par {original.reversed_by_id}"
        )
    if not target_period.contains(reversal_date):
        raise InvalidReversalDateError(
            f"Date {reversal_date} hors de la période {target_period.id}"
        )
    if not target_period.is_open_for_posting():
        raise PeriodClosedError(f"La période {target_period.id} est verrouillée ou clôturée")

    now = clock.now()
    reversed_lines = tuple(
        JournalLine(
            account_id=line.account_id,
            debit=line.credit,
            credit=line.debit,
            label=f"Contrepassation {original.id}",
        )
        for line in original.lines
    )
    total = original.total_debit()
    reversal_entry = JournalEntry(
        id=reversal_id,
        journal_id=original.journal_id,
        period_id=target_period.id,
        entry_date=reversal_date,
        description=f"Contrepassation de {original.id}",
        lines=reversed_lines,
        status=EntryStatus.POSTED,
        posted_at=now,
        reversal_of_id=original.id,
    )

    marked_original = JournalEntry(
        id=original.id,
        journal_id=original.journal_id,
        period_id=original.period_id,
        entry_date=original.entry_date,
        description=original.description,
        lines=original.lines,
        status=EntryStatus.POSTED,
        posted_at=original.posted_at,
        reversal_of_id=original.reversal_of_id,
        reversed_by_id=reversal_id,
    )

    audit_sink.record(
        AuditEvent(
            event_type="ENTRY_REVERSED",
            entity_id=str(original.id),
            actor_id=user_id,
            occurred_at=now,
            payload={
                "original_entry_id": str(original.id),
                "reversal_entry_id": str(reversal_id),
                "total": str(total.amount),
            },
        )
    )
    return marked_original, reversal_entry


__all__ = ["create_reversal"]
