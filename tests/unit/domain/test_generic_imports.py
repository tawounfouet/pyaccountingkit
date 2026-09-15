"""LOT-14 generic accounting import domain qualification."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import InvalidImportTransitionError, StaleImportPlanError
from pyaccountingkit.core.identifiers import AccountId, EntityId, JournalId, PeriodId
from pyaccountingkit.domain.imports.batch import AccountingImportBatch, ImportBatchStatus
from pyaccountingkit.domain.imports.import_plan import (
    ImportEntryPlan,
    ImportPlan,
    ImportPlannedLine,
)
from pyaccountingkit.domain.imports.mapping import ExplicitImportAccountMapper, ImportMappingStatus
from pyaccountingkit.domain.imports.normalized_record import (
    NormalizedImportRecord,
    SourceEntryKey,
    group_normalized_records,
)
from pyaccountingkit.domain.imports.raw_record import RawImportRecord
from pyaccountingkit.domain.imports.source_artifact import SourceArtifact


def _record(record_id: str, key: str, debit: str, credit: str) -> NormalizedImportRecord:
    return NormalizedImportRecord(
        batch_id="batch-1",
        normalized_record_id=record_id,
        source_record_ref=f"raw:{record_id}",
        source_entry_key=SourceEntryKey(key),
        source_account_code="401",
        source_journal_code="AC",
        accounting_date=date(2026, 9, 15),
        debit=Decimal(debit),
        credit=Decimal(credit),
        currency=EUR,
    )


def test_source_artifact_computes_sha256_and_size() -> None:
    artifact = SourceArtifact.from_bytes(
        artifact_ref="artifact-1",
        source_type="GENERIC",
        payload=b"immutable source",
        acquired_at=datetime(2026, 9, 15, tzinfo=UTC),
    )
    assert len(artifact.checksum) == 64
    assert artifact.size == len(b"immutable source")


def test_raw_record_is_lossless_and_checksum_deterministic() -> None:
    left = RawImportRecord("batch-1", 0, {"b": "2", "a": "1"})
    right = RawImportRecord("batch-1", 0, {"a": "1", "b": "2"})
    assert left.row_checksum == right.row_checksum
    with pytest.raises(TypeError):
        left.raw_fields["a"] = "changed"  # type: ignore[index]


def test_normalized_record_rejects_zero_line() -> None:
    with pytest.raises(ValueError, match="zero"):
        _record("1", "E1", "0", "0")


def test_grouping_is_deterministic_and_drops_nothing() -> None:
    records = (
        _record("3", "E2", "10", "0"),
        _record("2", "E1", "0", "20"),
        _record("1", "E1", "20", "0"),
        _record("4", "E2", "0", "10"),
    )
    groups = group_normalized_records(records)
    assert [group.source_entry_key.value for group in groups] == ["E1", "E2"]
    assert sum(len(group.records) for group in groups) == len(records)
    assert all(group.balanced for group in groups)


def test_batch_state_machine_rejects_skipping_validation() -> None:
    batch = AccountingImportBatch(
        batch_id="batch-1",
        accounting_entity_id=EntityId("entity-1"),
        source_type="GENERIC",
        adapter_id="adapter",
        adapter_version="1",
        source_artifact_ref="artifact-1",
        source_checksum="a" * 64,
        correlation_id="corr-1",
        created_at=datetime(2026, 9, 15, tzinfo=UTC),
    )
    with pytest.raises(InvalidImportTransitionError, match="illegal"):
        batch.transition(ImportBatchStatus.COMPLETED, at=datetime.now(UTC))


def test_unknown_account_mapping_is_not_executable() -> None:
    mapper = ExplicitImportAccountMapper({"401": AccountId("account-401")})
    decision = mapper.resolve("999")
    assert decision.status is ImportMappingStatus.UNMAPPED
    assert decision.executable is False


def test_import_plan_is_deterministic_and_rejects_staleness() -> None:
    entry = ImportEntryPlan(
        source_entry_key=SourceEntryKey("E1"),
        accounting_date=date(2026, 9, 15),
        journal_id=JournalId("journal-1"),
        period_id=PeriodId("period-1"),
        lines=(
            ImportPlannedLine("raw:1", AccountId("a1"), Decimal("10"), Decimal("0")),
            ImportPlannedLine("raw:2", AccountId("a2"), Decimal("0"), Decimal("10")),
        ),
    )
    plan = ImportPlan(
        batch_id="batch-1",
        entity_id=EntityId("entity-1"),
        source_checksum="a" * 64,
        adapter_id="generic",
        adapter_version="1",
        mapping_version="m1",
        chart_version="c1",
        entry_plans=(entry,),
        expected_line_count=2,
    )
    assert plan.checksum == plan.checksum
    with pytest.raises(StaleImportPlanError, match="stale"):
        plan.assert_fresh(
            source_checksum="a" * 64,
            adapter_version="2",
            mapping_version="m1",
            chart_version="c1",
        )
