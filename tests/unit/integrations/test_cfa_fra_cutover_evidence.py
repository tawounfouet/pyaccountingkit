"""LOT-26 tests for attestable live-cutover evidence."""

from __future__ import annotations

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    CutoverEvidenceStatus,
    ExternalCutoverEvidence,
    LiveCutoverEvidence,
)


def test_blocked_evidence_requires_reason_and_is_not_green() -> None:
    evidence = ExternalCutoverEvidence(
        status=CutoverEvidenceStatus.BLOCKED,
        source="live-consumer-cutover",
        reason="identity migration has not been executed yet",
    )

    assert evidence.green is False


def test_passing_evidence_requires_attestation_metadata() -> None:
    with pytest.raises(ValueError):
        ExternalCutoverEvidence(
            status=CutoverEvidenceStatus.PASS,
            source="live-consumer-cutover",
        )

    evidence = ExternalCutoverEvidence(
        status=CutoverEvidenceStatus.PASS,
        source="live-consumer-cutover",
        artifact="s3://evidence/cfa-fra/identity-migration.json",
        sha256="a" * 64,
        observed_at="2026-09-30T11:00:00Z",
        producer="cfa-fra-cutover-pipeline",
    )

    assert evidence.green is True


@pytest.mark.parametrize(
    ("sha256", "observed_at"),
    [
        ("A" * 64, "2026-09-30T11:00:00Z"),
        ("abc", "2026-09-30T11:00:00Z"),
        ("a" * 64, "2026-09-30T11:00:00"),
        ("a" * 64, "not-a-dateZ"),
    ],
)
def test_passing_evidence_rejects_invalid_attestation(
    sha256: str,
    observed_at: str,
) -> None:
    with pytest.raises(ValueError):
        ExternalCutoverEvidence(
            status=CutoverEvidenceStatus.PASS,
            source="live-consumer-cutover",
            artifact="evidence.json",
            sha256=sha256,
            observed_at=observed_at,
            producer="cutover-pipeline",
        )


def test_live_cutover_aggregate_exposes_retirement_booleans() -> None:
    blocked = ExternalCutoverEvidence(
        status=CutoverEvidenceStatus.BLOCKED,
        source="live-consumer-cutover",
        reason="not yet attested",
    )
    passed = ExternalCutoverEvidence(
        status=CutoverEvidenceStatus.PASS,
        source="live-consumer-cutover",
        artifact="regulatory-authority.json",
        sha256="b" * 64,
        observed_at="2026-09-30T11:00:00Z",
        producer="cutover-pipeline",
    )

    evidence = LiveCutoverEvidence(
        consumer_e2e=blocked,
        legacy_identities=blocked,
        regulatory_authority=passed,
    )

    assert evidence.consumer_e2e_green is False
    assert evidence.identities_traceable is False
    assert evidence.regulatory_authority_replaced is True
