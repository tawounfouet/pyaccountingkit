"""Transaction-mode and idempotent-ID qualification for generic import execution."""

from datetime import date
from decimal import Decimal

from pyaccountingkit.application.imports.execution import ImportExecutionService
from pyaccountingkit.application.ledger.posting_orchestrator import PostingResult
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import AccountId, EntityId, JournalId, PeriodId
from pyaccountingkit.domain.imports.batch import ImportTransactionMode
from pyaccountingkit.domain.imports.import_plan import ImportEntryPlan, ImportPlan, ImportPlannedLine
from pyaccountingkit.domain.imports.normalized_record import SourceEntryKey


class _FakePosting:
    def __init__(self) -> None:
        self.single_calls = []
        self.batch_calls = []

    def post(self, entry, actor_id: str):
        self.single_calls.append((entry, actor_id))
        return PostingResult(entry, f"post:{entry.id}")

    def post_many(self, entries, actor_id: str):
        self.batch_calls.append((entries, actor_id))
        return tuple(PostingResult(entry, f"post:{entry.id}") for entry in entries)


def _entry(key: str, debit_account: str, credit_account: str) -> ImportEntryPlan:
    return ImportEntryPlan(
        source_entry_key=SourceEntryKey(key),
        accounting_date=date(2026, 1, 15),
        journal_id=JournalId("j-ac"),
        period_id=PeriodId("p-2026-01"),
        lines=(
            ImportPlannedLine(
                f"{key}:1",
                AccountId(debit_account),
                Decimal("10"),
                Decimal("0"),
            ),
            ImportPlannedLine(
                f"{key}:2",
                AccountId(credit_account),
                Decimal("0"),
                Decimal("10"),
            ),
        ),
    )


def _plan() -> ImportPlan:
    return ImportPlan(
        batch_id="batch-1",
        entity_id=EntityId("entity-1"),
        source_checksum="a" * 64,
        adapter_id="fec-fr",
        adapter_version="0.3.0a2",
        mapping_version="m1",
        chart_version="c1",
        entry_plans=(
            _entry("AC:E1", "401000", "512000"),
            _entry("AC:E2", "401000", "512000"),
        ),
        expected_line_count=4,
    )


def _execute(service: ImportExecutionService, plan: ImportPlan, *, mode, chunk_size=None):
    return service.execute(
        plan,
        currency=EUR,
        actor_id="migration",
        source_checksum=plan.source_checksum,
        adapter_version=plan.adapter_version,
        mapping_version=plan.mapping_version,
        chart_version=plan.chart_version,
        transaction_mode=mode,
        chunk_size=chunk_size,
    )


def test_all_or_nothing_uses_one_atomic_posting_batch() -> None:
    posting = _FakePosting()
    service = ImportExecutionService(posting)  # type: ignore[arg-type]
    result = _execute(service, _plan(), mode=ImportTransactionMode.ALL_OR_NOTHING)
    assert len(posting.batch_calls) == 1
    assert len(posting.batch_calls[0][0]) == 2
    assert posting.single_calls == []
    assert len(result.created_entry_ids) == 2


def test_per_item_uses_one_transaction_per_entry() -> None:
    posting = _FakePosting()
    service = ImportExecutionService(posting)  # type: ignore[arg-type]
    _execute(service, _plan(), mode=ImportTransactionMode.PER_ITEM)
    assert len(posting.single_calls) == 2
    assert posting.batch_calls == []


def test_chunked_atomic_groups_entries_by_requested_chunk_size() -> None:
    posting = _FakePosting()
    service = ImportExecutionService(posting)  # type: ignore[arg-type]
    _execute(
        service,
        _plan(),
        mode=ImportTransactionMode.CHUNKED_ATOMIC,
        chunk_size=1,
    )
    assert [len(call[0]) for call in posting.batch_calls] == [1, 1]


def test_same_reviewed_plan_produces_same_entry_ids() -> None:
    posting = _FakePosting()
    service = ImportExecutionService(posting)  # type: ignore[arg-type]
    plan = _plan()
    first = _execute(service, plan, mode=ImportTransactionMode.ALL_OR_NOTHING)
    second = _execute(service, plan, mode=ImportTransactionMode.ALL_OR_NOTHING)
    assert first.created_entry_ids == second.created_entry_ids
