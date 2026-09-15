"""PostingOrchestrator — the transactional, idempotent PostEntry use-case.

Encapsulates the atomic mutation (*rollback leaves no partial state*),
chart/journal/period validation, exact-once posting under duplicate
requests, audit and outbox hooks.  The pure DRAFT → POSTED transition is
delegated to the domain ``PostingService``.
"""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.errors import (
    IdempotencyReplayError,
    InactiveAccountError,
    InactiveJournalError,
    NonPostableAccountError,
    PeriodClosedError,
    UnknownAccountError,
)
from pyaccountingkit.core.identifiers import EntryId
from pyaccountingkit.core.revisions import Revision
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.ledger.posting import PostingService
from pyaccountingkit.ports.outbox import OutboxRecord
from pyaccountingkit.ports.unit_of_work import UnitOfWorkFactoryProtocol, UnitOfWorkProtocol


@dataclass(frozen=True, slots=True)
class PostingResult:
    """Outcome of a posting request, idempotent by key."""

    posted_entry: JournalEntry
    idempotency_key: str
    was_replayed: bool = False


class PostingOrchestrator:
    """Transactional use-case for posting one journal entry."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactoryProtocol,
        chart: CompanyChartOfAccounts,
        posting_service: PostingService,
    ) -> None:
        self._uow_factory = uow_factory
        self._chart = chart
        self._posting_service = posting_service

    def post(self, entry: JournalEntry, actor_id: str) -> PostingResult:
        """Post *entry* exactly once; a duplicate request replays cleanly."""
        idempotency_key = f"post:{entry.id}"
        with self._uow_factory.open() as uow:
            if not uow.idempotency.claim(idempotency_key):
                return self._replay(uow, entry.id, idempotency_key)

            period = uow.periods.get(entry.period_id)
            journal = uow.journals.get(entry.journal_id)
            if not journal.is_active():
                raise InactiveJournalError(f"Journal {journal.id} inactif")
            if not period.is_open_for_posting():
                raise PeriodClosedError(f"Période {period.id} fermée ou verrouillée")
            self._validate_accounts(entry)

            uow.entries.add(entry)
            posted = self._posting_service.post(entry, period, actor_id)
            uow.entries.save(posted, Revision())
            uow.outbox.publish(
                OutboxRecord(
                    event_type="ENTRY_POSTED",
                    entity_id=str(posted.id),
                    payload={
                        "entry_id": str(posted.id),
                        "period_id": str(posted.period_id),
                    },
                )
            )
            uow.idempotency.complete(idempotency_key)
            uow.commit()
        return PostingResult(posted_entry=posted, idempotency_key=idempotency_key)

    def _replay(
        self,
        uow: UnitOfWorkProtocol,
        entry_id: EntryId,
        key: str,
    ) -> PostingResult:
        stored = uow.entries.get(entry_id)
        if stored.status is not EntryStatus.POSTED:
            raise IdempotencyReplayError(
                f"Clé {key} déjà consommée mais {entry_id} n'est pas POSTED"
            )
        return PostingResult(posted_entry=stored, idempotency_key=key, was_replayed=True)

    def _validate_accounts(self, entry: JournalEntry) -> None:
        for line in entry.lines:
            account = self._chart.get_by_code(str(line.account_id))
            if account is None:
                raise UnknownAccountError(f"Compte {line.account_id} inconnu au plan")
            if not account.is_active():
                raise InactiveAccountError(f"Compte {line.account_id} inactif")
            if not account.postable:
                raise NonPostableAccountError(f"Compte {line.account_id} non comptabilisable")


__all__ = ["PostingResult", "PostingOrchestrator"]
