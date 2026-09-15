"""Execution of a reviewed ImportPlan through the canonical posting engine."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.application.ledger.posting_orchestrator import PostingOrchestrator
from pyaccountingkit.core.currency import Currency
from pyaccountingkit.core.identifiers import EntryId, IdFactory
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.imports.import_plan import ImportPlan
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine


@dataclass(frozen=True, slots=True)
class ImportExecutionResult:
    batch_id: str
    plan_checksum: str
    created_entry_ids: tuple[EntryId, ...]
    dry_run: bool


class ImportExecutionService:
    """Execute a fresh plan without introducing a second posting engine."""

    def __init__(
        self,
        posting: PostingOrchestrator,
        *,
        id_factory: IdFactory | None = None,
    ) -> None:
        self._posting = posting
        self._ids = id_factory or IdFactory()

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
    ) -> ImportExecutionResult:
        """Reject stale plans then delegate every entry to ``PostingOrchestrator``."""
        plan.assert_fresh(
            source_checksum=source_checksum,
            adapter_version=adapter_version,
            mapping_version=mapping_version,
            chart_version=chart_version,
        )
        created: list[EntryId] = []
        for entry_plan in plan.entry_plans:
            entry_id = EntryId(self._ids.new("entry"))
            lines = tuple(
                JournalLine(
                    account_id=line.account_id,
                    debit=Money(line.debit, currency),
                    credit=Money(line.credit, currency),
                    label=line.source_record_ref,
                )
                for line in entry_plan.lines
            )
            entry = JournalEntry(
                id=entry_id,
                journal_id=entry_plan.journal_id,
                period_id=entry_plan.period_id,
                entry_date=entry_plan.accounting_date,
                description=entry_plan.description or f"Import {entry_plan.source_entry_key.value}",
                lines=lines,
            )
            self._posting.post(entry, actor_id=actor_id)
            created.append(entry_id)
        return ImportExecutionResult(
            batch_id=plan.batch_id,
            plan_checksum=plan.checksum,
            created_entry_ids=tuple(created),
            dry_run=False,
        )


__all__ = ["ImportExecutionResult", "ImportExecutionService"]
