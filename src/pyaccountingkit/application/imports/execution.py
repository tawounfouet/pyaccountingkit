"""Execution of a reviewed ImportPlan through the canonical posting engine."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pyaccountingkit.application.ledger.posting_orchestrator import PostingOrchestrator
from pyaccountingkit.core.currency import Currency
from pyaccountingkit.core.identifiers import EntryId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.imports.batch import ImportTransactionMode
from pyaccountingkit.domain.imports.import_plan import ImportEntryPlan, ImportPlan
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine


@dataclass(frozen=True, slots=True)
class ImportExecutionResult:
    batch_id: str
    plan_checksum: str
    created_entry_ids: tuple[EntryId, ...]
    dry_run: bool
    transaction_mode: ImportTransactionMode = ImportTransactionMode.ALL_OR_NOTHING


class ImportExecutionService:
    """Execute a fresh plan without introducing a second posting engine."""

    def __init__(self, posting: PostingOrchestrator) -> None:
        self._posting = posting

    def dry_run(self, plan: ImportPlan) -> ImportExecutionResult:
        """Return a deterministic preview result and perform no accounting mutation."""
        return ImportExecutionResult(
            batch_id=plan.batch_id,
            plan_checksum=plan.checksum,
            created_entry_ids=(),
            dry_run=True,
        )

    def execute(
        self,
        plan: ImportPlan,
        *,
        currency: Currency,
        actor_id: str,
        source_checksum: str,
        adapter_version: str,
        mapping_version: str,
        chart_version: str,
        transaction_mode: ImportTransactionMode = ImportTransactionMode.ALL_OR_NOTHING,
        chunk_size: int | None = None,
    ) -> ImportExecutionResult:
        """Reject stale plans then delegate every mutation to ``PostingOrchestrator``."""
        plan.assert_fresh(
            source_checksum=source_checksum,
            adapter_version=adapter_version,
            mapping_version=mapping_version,
            chart_version=chart_version,
        )
        entries = tuple(
            self._journal_entry(plan, entry_plan, currency) for entry_plan in plan.entry_plans
        )
        if transaction_mode is ImportTransactionMode.ALL_OR_NOTHING:
            results = self._posting.post_many(entries, actor_id=actor_id)
        elif transaction_mode is ImportTransactionMode.PER_ITEM:
            results = tuple(self._posting.post(entry, actor_id=actor_id) for entry in entries)
        else:
            if chunk_size is None or chunk_size <= 0:
                raise ValueError("CHUNKED_ATOMIC import requires chunk_size > 0")
            results = tuple(
                result
                for start in range(0, len(entries), chunk_size)
                for result in self._posting.post_many(
                    entries[start : start + chunk_size],
                    actor_id=actor_id,
                )
            )
        return ImportExecutionResult(
            batch_id=plan.batch_id,
            plan_checksum=plan.checksum,
            created_entry_ids=tuple(result.posted_entry.id for result in results),
            dry_run=False,
            transaction_mode=transaction_mode,
        )

    @staticmethod
    def _journal_entry(
        plan: ImportPlan,
        entry_plan: ImportEntryPlan,
        currency: Currency,
    ) -> JournalEntry:
        entry_id = ImportExecutionService._entry_id(plan, entry_plan)
        lines = tuple(
            JournalLine(
                account_id=line.account_id,
                debit=Money(line.debit, currency),
                credit=Money(line.credit, currency),
                label=line.source_record_ref,
            )
            for line in entry_plan.lines
        )
        return JournalEntry(
            id=entry_id,
            journal_id=entry_plan.journal_id,
            period_id=entry_plan.period_id,
            entry_date=entry_plan.accounting_date,
            description=entry_plan.description or f"Import {entry_plan.source_entry_key.value}",
            lines=lines,
        )

    @staticmethod
    def _entry_id(plan: ImportPlan, entry_plan: ImportEntryPlan) -> EntryId:
        """Stable source identity prevents duplicate ledger effects across import batches."""
        identity = "|".join(
            (
                str(plan.entity_id),
                plan.source_checksum,
                plan.adapter_id,
                entry_plan.source_entry_key.value,
            )
        )
        digest = hashlib.sha256(identity.encode()).hexdigest()[:32]
        return EntryId(f"imp_{digest}")


__all__ = ["ImportExecutionResult", "ImportExecutionService"]
