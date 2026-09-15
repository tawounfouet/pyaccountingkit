"""ReversalOrchestrator — the transactional, idempotent ReverseEntry use-case.

Creates a posted reversal entry and marks the original entry accordingly,
then persists both atomically.  A duplicate request replays cleanly.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from pyaccountingkit.core.errors import (
    AlreadyReversedError,
    EntryNotFoundError,
    IdempotencyReplayError,
    PeriodClosedError,
)
from pyaccountingkit.core.identifiers import EntryId, PeriodId
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.ledger.reversal import create_reversal
from pyaccountingkit.ports.unit_of_work import (
    UnitOfWorkFactoryProtocol,
    UnitOfWorkProtocol,
)


@dataclass(frozen=True, slots=True)
class ReversalResult:
    """Outcome of a reversal request, idempotent by key."""

    marked_original: JournalEntry
    reversal_entry: JournalEntry
    idempotency_key: str
    was_replayed: bool = False


class ReversalOrchestrator:
    """Transactional use-case for reversal of one posted entry."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactoryProtocol,
        reversal_id_factory: Callable[[], EntryId],
    ) -> None:
        self._uow_factory = uow_factory
        self._reversal_id_factory = reversal_id_factory

    def reverse(
        self,
        entry_id: EntryId,
        target_period_id: PeriodId,
        reversal_date: date,
        actor_id: str,
    ) -> ReversalResult:
        """Produce a posted reversal and mark the original entry reversed."""
        idempotency_key = f"reversal:{entry_id}:{target_period_id}:{reversal_date.isoformat()}"
        with self._uow_factory.open() as uow:
            if not uow.idempotency.claim(idempotency_key):
                return self._replay(uow, entry_id, idempotency_key)

            original = uow.entries.get(entry_id)
            target_period = uow.periods.get(target_period_id)
            if not target_period.is_open_for_posting():
                raise PeriodClosedError(
                    f"Période {target_period.id} fermée ou verrouillée pour la contrepassation"
                )
            if original.status is not EntryStatus.POSTED:
                raise EntryNotFoundError(
                    f"Écriture {entry_id} non postée ({original.status.value})"
                )
            if original.reversed_by_id is not None:
                raise AlreadyReversedError(
                    f"Écriture {entry_id} déjà contrepassée ({original.reversed_by_id})"
                )

            reversal_id = self._reversal_id_factory()
            marked, reversal = create_reversal(
                original,
                reversal_date,
                reversal_id,
                target_period,
                uow.audit,
                uow.clock,
                actor_id,
            )
            expected = uow.entries.get_revision(original.id)
            uow.entries.save(marked, expected)
            uow.entries.add(reversal)
            uow.idempotency.complete(idempotency_key)
            uow.commit()
        return ReversalResult(
            marked_original=marked,
            reversal_entry=reversal,
            idempotency_key=idempotency_key,
        )

    def _replay(
        self,
        uow: UnitOfWorkProtocol,
        entry_id: EntryId,
        key: str,
    ) -> ReversalResult:
        reversal_entries = uow.entries.find_by_reversal_of(entry_id)
        if not reversal_entries:
            raise IdempotencyReplayError(
                f"Clé {key} déjà consommée mais aucune contrepassation trouvée"
            )
        reversal = reversal_entries[0]
        original = uow.entries.get(entry_id)
        return ReversalResult(
            marked_original=original,
            reversal_entry=reversal,
            idempotency_key=key,
            was_replayed=True,
        )


__all__ = ["ReversalResult", "ReversalOrchestrator"]
