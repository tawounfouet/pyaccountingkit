"""LOT-26 integration contract for CFA FRA live cutover evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    CutoverArtifactVerificationError,
    CutoverEvidenceStatus,
    ExternalCutoverEvidence,
    LiveCutoverEvidence,
    verify_live_cutover_evidence,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tests" / "consumer" / "cfa_fra" / "RETIREMENT_EVIDENCE.json"


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_live_cutover_manifest_uses_verified_schema_v4() -> None:
    payload = _manifest()

    assert payload["schema_version"] == "4"
    assert payload["routing_profile"] == "target_only"
    external = payload["external_evidence"]
    assert isinstance(external, dict)

    evidence = LiveCutoverEvidence.from_mapping(external)
    artifact_policy = payload["artifact_policy"]
    assert artifact_policy == {
        "root": "tests/consumer/cfa_fra/live_evidence",
        "require_local_materialization": True,
        "sha256_verified": True,
        "content_schema_verified": True,
        "schemas": {
            "legacy_identities": "cfa_fra_legacy_identity_migration/v1",
            "regulatory_authority": "cfa_fra_regulatory_authority_cutover/v1",
        },
    }
    verified = verify_live_cutover_evidence(
        evidence,
        artifact_root=ROOT / artifact_policy["root"],
    )

    assert verified.identities_traceable is False
    assert verified.regulatory_authority_replaced is False


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

    with pytest.raises(CutoverArtifactVerificationError):
        verify_live_cutover_evidence(
            LiveCutoverEvidence(
                legacy_identities=evidence,
                regulatory_authority=evidence,
            ),
            artifact_root=ROOT / "tests" / "consumer" / "cfa_fra" / "live_evidence",
        )


def test_expected_blockers_match_current_external_evidence_state() -> None:
    payload = _manifest()
    external = payload["external_evidence"]
    assert isinstance(external, dict)
    evidence = LiveCutoverEvidence.from_mapping(external)
    artifact_policy = payload["artifact_policy"]
    verified = verify_live_cutover_evidence(
        evidence,
        artifact_root=ROOT / artifact_policy["root"],
    )
    blockers = set(payload["expected_blockers"])

    assert ("evidence:legacy-identities" in blockers) is (not verified.identities_traceable)
    assert ("evidence:regulatory-authority" in blockers) is (
        not verified.regulatory_authority_replaced
    )
