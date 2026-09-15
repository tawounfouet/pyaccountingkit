"""PostingOrchestrator — transactional, entity-safe and version-aware posting."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.entity_scope import require_same_entity
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
from pyaccountingkit.domain.audit.events import AuditEvent
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.ledger.posting import PostingService
from pyaccountingkit.ports.company_chart_resolution import CompanyChartResolverProtocol
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
        chart_resolver: CompanyChartResolverProtocol,
        posting_service: PostingService,
    ) -> None:
        self._uow_factory = uow_factory
        self._chart_resolver = chart_resolver
        self._posting_service = posting_service

    def post(self, entry: JournalEntry, actor_id: str) -> PostingResult:
        """Post *entry* exactly once; a duplicate request replays cleanly."""
        idempotency_key = f"post:{entry.id}"
        with self._uow_factory.open() as uow:
            if not uow.idempotency.claim(idempotency_key):
                return self._replay(uow, entry.id, idempotency_key)

            period = uow.periods.get(entry.period_id)
            journal = uow.journals.get(entry.journal_id)
            require_same_entity(
                journal.entity_id,
                period.entity_id,
                resource=f"period {period.id}",
            )
            resolved_chart = self._chart_resolver.resolve(
                entity_id=journal.entity_id,
                accounting_date=entry.entry_date,
            )
            if not journal.is_active():
                raise InactiveJournalError(f"Journal {journal.id} inactif")
            if not period.is_open_for_posting():
                raise PeriodClosedError(f"Période {period.id} fermée ou verrouillée")
            self._validate_accounts(entry, resolved_chart.chart)

            uow.entries.add(entry)
            posted = self._posting_service.post(entry, period, actor_id)
            uow.entries.save(posted, Revision())

            trace_payload = {
                "entry_id": str(posted.id),
                "period_id": str(posted.period_id),
                "journal_id": str(posted.journal_id),
                "chart_id": resolved_chart.chart_id,
                "chart_version": resolved_chart.chart_version,
                "reference_snapshot_id": resolved_chart.reference_snapshot_id,
            }
            uow.audit.record(
                AuditEvent(
                    event_type="ENTRY_POSTED",
                    entity_id=str(journal.entity_id),
                    actor_id=actor_id,
                    occurred_at=posted.posted_at or uow.clock.now(),
                    payload={
                        **trace_payload,
                        "total_debit": str(posted.total_debit().amount),
                        "total_credit": str(posted.total_credit().amount),
                    },
                )
            )
            uow.outbox.publish(
                OutboxRecord(
                    event_type="ENTRY_POSTED",
                    entity_id=str(journal.entity_id),
                    payload=trace_payload,
                    idempotency_key=idempotency_key,
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

    @staticmethod
    def _validate_accounts(entry: JournalEntry, chart: CompanyChartOfAccounts) -> None:
        for line in entry.lines:
            account = chart.get_by_code(str(line.account_id))
            if account is None:
                raise UnknownAccountError(f"Compte {line.account_id} inconnu au plan")
            require_same_entity(
                chart.entity_id,
                account.entity_id,
                resource=f"company account {account.id}",
            )
            if not account.is_active():
                raise InactiveAccountError(f"Compte {line.account_id} inactif")
            if not account.postable:
                raise NonPostableAccountError(f"Compte {line.account_id} non comptabilisable")


__all__ = ["PostingResult", "PostingOrchestrator"]
