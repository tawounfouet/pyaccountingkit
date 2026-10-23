"""PostingOrchestrator — transactional, entity-safe and version-aware posting."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.errors import (
    EntryNotFoundError,
    IdempotencyReplayError,
    InactiveAccountError,
    InactiveJournalError,
    InvalidEntryStateError,
    NonPostableAccountError,
    PeriodClosedError,
    RevisionConflictError,
    UnknownAccountError,
)
from pyaccountingkit.core.identifiers import EntityId, EntryId
from pyaccountingkit.core.revisions import Revision
from pyaccountingkit.domain.audit.events import AuditEvent
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.ledger.posting import PostingService
from pyaccountingkit.domain.traceability.accounting_execution import AccountingExecutionTrace
from pyaccountingkit.domain.traceability.trace import CanonicalHasher
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
    """Transactional use-case for posting one or several journal entries."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactoryProtocol,
        chart_resolver: CompanyChartResolverProtocol,
        posting_service: PostingService,
    ) -> None:
        self._uow_factory = uow_factory
        self._chart_resolver = chart_resolver
        self._posting_service = posting_service

    def post(
        self,
        entry: JournalEntry,
        actor_id: str,
        *,
        expected_entity_id: EntityId | None = None,
        execution_trace: AccountingExecutionTrace | None = None,
    ) -> PostingResult:
        """Post *entry* exactly once in one transaction.

        expected_entity_id binds caller-owned business intent to the
        journal/period scope selected for persistence.
        """
        with self._uow_factory.open() as uow:
            result = self._post_in_uow(
                uow,
                entry,
                actor_id,
                expected_entity_id=expected_entity_id,
                execution_trace=execution_trace,
            )
            uow.commit()
        return result

    def post_in_uow(
        self,
        uow: UnitOfWorkProtocol,
        entry: JournalEntry,
        actor_id: str,
        *,
        expected_entity_id: EntityId | None = None,
        execution_trace: AccountingExecutionTrace | None = None,
    ) -> PostingResult:
        """Post through the canonical engine inside an already-open transaction."""

        return self._post_in_uow(
            uow,
            entry,
            actor_id,
            expected_entity_id=expected_entity_id,
            execution_trace=execution_trace,
        )

    def post_many(
        self,
        entries: tuple[JournalEntry, ...],
        actor_id: str,
        *,
        expected_entity_id: EntityId | None = None,
    ) -> tuple[PostingResult, ...]:
        """Post several entries atomically through the same canonical engine."""
        if not entries:
            return ()
        with self._uow_factory.open() as uow:
            results = tuple(
                self._post_in_uow(
                    uow,
                    entry,
                    actor_id,
                    expected_entity_id=expected_entity_id,
                )
                for entry in entries
            )
            uow.commit()
        return results

    def _post_in_uow(
        self,
        uow: UnitOfWorkProtocol,
        entry: JournalEntry,
        actor_id: str,
        *,
        expected_entity_id: EntityId | None = None,
        execution_trace: AccountingExecutionTrace | None = None,
    ) -> PostingResult:
        period = uow.periods.get(entry.period_id)
        journal = uow.journals.get(entry.journal_id)
        if expected_entity_id is not None:
            require_same_entity(
                expected_entity_id,
                journal.entity_id,
                resource=f"journal {journal.id}",
            )
        require_same_entity(
            journal.entity_id,
            period.entity_id,
            resource=f"period {period.id}",
        )

        if entry.status is not EntryStatus.VALIDATED:
            raise InvalidEntryStateError(
                f"Écriture {entry.id} doit être VALIDATED avant comptabilisation"
            )

        idempotency_key = f"post:{entry.id}"
        payload_fingerprint = self._posting_fingerprint(
            entry,
            journal.entity_id,
            execution_trace,
        )
        if not uow.idempotency.claim(idempotency_key, payload_fingerprint):
            return self._replay(
                uow,
                entry.id,
                idempotency_key,
                execution_trace=execution_trace,
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

        try:
            persisted = uow.entries.get(entry.id)
        except EntryNotFoundError:
            uow.entries.add(entry)
            posting_entry = entry
            expected_revision = Revision()
        else:
            if persisted != entry:
                raise RevisionConflictError(
                    f"Entry {entry.id}: persisted VALIDATED content differs from posting request"
                )
            posting_entry = persisted
            expected_revision = uow.entries.get_revision(entry.id)

        posted = self._posting_service.post(posting_entry, period, actor_id)
        uow.entries.save(posted, expected_revision)
        if execution_trace is not None:
            require_same_entity(
                journal.entity_id,
                execution_trace.entity_id,
                resource=f"accounting execution trace {execution_trace.trace_id}",
            )
            if execution_trace.journal_entry_id != posted.id:
                raise RevisionConflictError(
                    f"Execution trace {execution_trace.trace_id}: entry "
                    f"{execution_trace.journal_entry_id} does not match {posted.id}"
                )
            uow.execution_traces.append(execution_trace)

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
        return PostingResult(posted_entry=posted, idempotency_key=idempotency_key)

    @staticmethod
    def _posting_fingerprint(
        entry: JournalEntry,
        entity_id: EntityId,
        execution_trace: AccountingExecutionTrace | None = None,
    ) -> str:
        return CanonicalHasher.digest(
            {
                "operation": "POST_ENTRY",
                "entity_id": str(entity_id),
                "entry_id": str(entry.id),
                "journal_id": str(entry.journal_id),
                "period_id": str(entry.period_id),
                "entry_date": entry.entry_date.isoformat(),
                "description": entry.description,
                "entry_type": entry.entry_type.value,
                "reversal_of_id": (
                    str(entry.reversal_of_id) if entry.reversal_of_id is not None else None
                ),
                "execution_trace": (
                    execution_trace.canonical_payload() if execution_trace is not None else None
                ),
                "lines": [
                    {
                        "account_id": str(line.account_id),
                        "debit_amount": str(line.debit.amount),
                        "debit_currency": line.debit.currency.code,
                        "debit_exponent": line.debit.currency.exponent,
                        "credit_amount": str(line.credit.amount),
                        "credit_currency": line.credit.currency.code,
                        "credit_exponent": line.credit.currency.exponent,
                        "label": line.label,
                    }
                    for line in entry.lines
                ],
            }
        )

    def _replay(
        self,
        uow: UnitOfWorkProtocol,
        entry_id: EntryId,
        key: str,
        *,
        execution_trace: AccountingExecutionTrace | None = None,
    ) -> PostingResult:
        stored = uow.entries.get(entry_id)
        if stored.status is not EntryStatus.POSTED:
            raise IdempotencyReplayError(
                f"Clé {key} déjà consommée mais {entry_id} n'est pas POSTED"
            )
        if execution_trace is not None:
            persisted_trace = uow.execution_traces.get_by_entry_id(entry_id)
            if persisted_trace is None:
                raise IdempotencyReplayError(
                    f"Clé {key} déjà consommée mais aucune trace d'exécution n'existe"
                )
            if persisted_trace != execution_trace:
                raise IdempotencyReplayError(
                    f"Clé {key} déjà consommée avec une trace d'exécution différente"
                )
        return PostingResult(posted_entry=stored, idempotency_key=key, was_replayed=True)

    @staticmethod
    def _validate_accounts(entry: JournalEntry, chart: CompanyChartOfAccounts) -> None:
        for line in entry.lines:
            account = chart.get_by_id(line.account_id)
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
