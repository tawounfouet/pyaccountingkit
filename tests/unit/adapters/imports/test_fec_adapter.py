"""LOT-15 qualification for the specialized French FEC adapter."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from pyaccountingkit.adapters.imports.fec import (
    FECAdapter,
    FECParseError,
    FECSourceDescriptor,
    build_fec_reconciliation_report,
    discover_fec,
)
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.imports.batch import ImportMode
from pyaccountingkit.domain.imports.source_artifact import SourceArtifact

HEADER = "\t".join(
    (
        "JournalCode",
        "JournalLib",
        "EcritureNum",
        "EcritureDate",
        "CompteNum",
        "CompteLib",
        "CompAuxNum",
        "CompAuxLib",
        "PieceRef",
        "PieceDate",
        "EcritureLib",
        "Debit",
        "Credit",
        "EcritureLet",
        "DateLet",
        "ValidDate",
        "Montantdevise",
        "Idevise",
    )
)


def _line(
    *,
    entry: str,
    account: str,
    debit: str,
    credit: str,
    auxiliary: str = "",
    lettering: str = "",
    lettering_date: str = "",
) -> str:
    return "\t".join(
        (
            "AC",
            "Achats",
            entry,
            "20260115",
            account,
            f"Compte {account}",
            auxiliary,
            "Auxiliaire" if auxiliary else "",
            "P-001",
            "20260115",
            "Facture fournisseur",
            debit,
            credit,
            lettering,
            lettering_date,
            "20260116",
            "",
            "",
        )
    )


def _payload() -> bytes:
    return (
        HEADER
        + "\n"
        + _line(
            entry="E1",
            account="401000",
            debit="100.00",
            credit="0",
            auxiliary="SUP-001",
            lettering="LET-1",
            lettering_date="20260201",
        )
        + "\n"
        + _line(entry="E1", account="512000", debit="0", credit="100.00")
        + "\n"
    ).encode()


def _artifact(payload: bytes) -> SourceArtifact:
    return SourceArtifact.from_bytes(
        artifact_ref="fec:2026",
        source_type="FEC",
        payload=payload,
        acquired_at=datetime(2026, 9, 15, tzinfo=UTC),
        filename="123456789FEC20261231.txt",
        media_type="text/plain",
    )


def test_parser_preserves_raw_rows_lineage_and_checksum() -> None:
    payload = _payload()
    adapter = FECAdapter()
    parsed = adapter.parse(_artifact(payload), batch_id="batch-1", payload=payload)

    assert len(parsed.records) == 2
    assert parsed.records[0].source_line_number == 2
    assert parsed.records[0].raw_fields["CompAuxNum"] == "SUP-001"
    assert parsed.records[0].row_checksum is not None
    assert parsed.records[0].provenance["artifact_ref"] == "fec:2026"


def test_parser_rejects_payload_that_does_not_match_source_artifact() -> None:
    payload = _payload()
    adapter = FECAdapter()
    with pytest.raises(FECParseError, match="checksum"):
        adapter.parse(_artifact(payload), batch_id="batch-1", payload=payload + b"x")


def test_parser_rejects_noncanonical_header() -> None:
    payload = _payload().replace(b"CompAuxNum", b"AuxNum", 1)
    artifact = _artifact(payload)
    with pytest.raises(FECParseError, match="header"):
        FECAdapter().parse(artifact, batch_id="batch-1", payload=payload)


def test_normalizer_preserves_auxiliary_and_lettering_without_account_concat() -> None:
    payload = _payload()
    adapter = FECAdapter()
    parsed = adapter.parse(_artifact(payload), batch_id="batch-1", payload=payload)
    records = adapter.normalizer().normalize(parsed, batch_id="batch-1")

    first = records[0]
    assert first.source_account_code == "401000"
    assert first.auxiliary_code == "SUP-001"
    assert first.source_account_code != "401000SUP-001"
    assert first.metadata["fec.EcritureLet"] == "LET-1"
    assert first.metadata["fec.DateLet"] == "20260201"
    assert first.source_entry_key.value == "AC:E1"


def test_fec_grouping_is_deterministic_and_balanced() -> None:
    payload = _payload()
    adapter = FECAdapter()
    parsed = adapter.parse(_artifact(payload), batch_id="batch-1", payload=payload)
    records = adapter.normalizer().normalize(parsed, batch_id="batch-1")

    left = adapter.grouping().group(records)
    right = adapter.grouping().group(tuple(reversed(records)))
    assert left == right
    assert len(left) == 1
    assert left[0].balanced is True


def test_duplicate_candidate_is_warning_only_and_never_deleted() -> None:
    payload = _payload()
    adapter = FECAdapter()
    parsed = adapter.parse(_artifact(payload), batch_id="batch-1", payload=payload)
    duplicated = parsed.records + (parsed.records[0],)

    issues = adapter.validator().validate_raw(duplicated)
    duplicate_issues = [issue for issue in issues if issue.issue_code == "FEC_DUPLICATE_LINE"]
    assert duplicate_issues
    assert all(issue.blocking is False for issue in duplicate_issues)
    assert len(duplicated) == 3


def test_fec_validation_and_reconciliation_totals_match() -> None:
    payload = _payload()
    adapter = FECAdapter(
        FECSourceDescriptor(
            fiscal_year_start=date(2026, 1, 1),
            fiscal_year_end=date(2026, 12, 31),
        )
    )
    parsed = adapter.parse(_artifact(payload), batch_id="batch-1", payload=payload)
    records = adapter.normalizer().normalize(parsed, batch_id="batch-1")
    report = adapter.validator().report(
        batch_id="batch-1",
        raw_records=parsed.records,
        normalized_records=records,
    )
    assert report.valid is True
    assert report.total_debit == Decimal("100.00")
    assert report.total_credit == Decimal("100.00")

    reconciliation = build_fec_reconciliation_report(
        records,
        imported_entry_count=1,
        imported_line_count=2,
        imported_debit=Decimal("100.00"),
        imported_credit=Decimal("100.00"),
    )
    assert reconciliation.reconciled is True


def test_discovery_preserves_accounts_journals_and_auxiliaries() -> None:
    payload = _payload()
    adapter = FECAdapter()
    parsed = adapter.parse(_artifact(payload), batch_id="batch-1", payload=payload)
    records = adapter.normalizer().normalize(parsed, batch_id="batch-1")
    discovery = discover_fec(records)

    assert discovery.source_accounts == (
        ("401000", "Compte 401000"),
        ("512000", "Compte 512000"),
    )
    assert discovery.source_journals == (("AC", "Achats"),)
    assert discovery.auxiliary_codes == ("SUP-001",)
    assert discovery.entry_count == 1
    assert discovery.line_count == 2


def test_same_fec_file_has_stable_scoped_fingerprint() -> None:
    payload = _payload()
    adapter = FECAdapter()
    artifact = _artifact(payload)
    left = adapter.source_fingerprint(
        artifact,
        entity_id=EntityId("entity-1"),
        fiscal_year_id="fy-2026",
    )
    right = adapter.source_fingerprint(
        artifact,
        entity_id=EntityId("entity-1"),
        fiscal_year_id="fy-2026",
    )
    assert left.canonical_key() == right.canonical_key()


def test_trusted_posted_history_requires_explicit_trust() -> None:
    with pytest.raises(ValueError, match="explicitly trusted"):
        FECAdapter.validate_import_mode(
            ImportMode.TRUSTED_POSTED_HISTORY_IMPORT,
            trusted_source=False,
        )
    FECAdapter.validate_import_mode(
        ImportMode.TRUSTED_POSTED_HISTORY_IMPORT,
        trusted_source=True,
    )
