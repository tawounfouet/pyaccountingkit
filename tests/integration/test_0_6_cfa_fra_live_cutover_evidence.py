"""LOT-26 integration contract for CFA FRA live cutover evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    CutoverEvidenceStatus,
    ExternalCutoverEvidence,
    LiveCutoverEvidence,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tests" / "consumer" / "cfa_fra" / "RETIREMENT_EVIDENCE.json"


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_live_cutover_manifest_uses_attestable_schema_v2() -> None:
    payload = _manifest()

    assert payload["schema_version"] == "2"
    assert payload["routing_profile"] == "target_only"
    external = payload["external_evidence"]
    assert isinstance(external, dict)

    evidence = LiveCutoverEvidence.from_mapping(external)

    assert evidence.identities_traceable is False
    assert evidence.regulatory_authority_replaced is False


def test_current_external_evidence_is_blocked_not_fabricated() -> None:
    payload = _manifest()
    external = payload["external_evidence"]

    assert isinstance(external, dict)
    for key in ("legacy_identities", "regulatory_authority"):
        record = external[key]
        assert record["status"] == "BLOCKED"
        assert record["reason"]
        assert "artifact" not in record
        assert "sha256" not in record


def test_passing_external_evidence_requires_full_attestation() -> None:
    with pytest.raises(ValueError):
        ExternalCutoverEvidence.from_mapping(
            {
                "status": "PASS",
                "source": "live-consumer-cutover",
                "artifact": "identity-migration.json",
            }
        )

    evidence = ExternalCutoverEvidence.from_mapping(
        {
            "status": "PASS",
            "source": "live-consumer-cutover",
            "artifact": "identity-migration.json",
            "sha256": "c" * 64,
            "observed_at": "2026-09-30T11:15:00Z",
            "producer": "cfa-fra-cutover-pipeline",
        }
    )

    assert evidence.status is CutoverEvidenceStatus.PASS
    assert evidence.green is True


def test_expected_blockers_match_current_external_evidence_state() -> None:
    payload = _manifest()
    external = payload["external_evidence"]
    assert isinstance(external, dict)
    evidence = LiveCutoverEvidence.from_mapping(external)
    blockers = set(payload["expected_blockers"])

    assert ("evidence:legacy-identities" in blockers) is (
        not evidence.identities_traceable
    )
    assert ("evidence:regulatory-authority" in blockers) is (
        not evidence.regulatory_authority_replaced
    )
