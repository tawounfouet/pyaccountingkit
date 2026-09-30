"""LOT-26 tests for controlled CFA FRA cutover evidence promotion."""

from __future__ import annotations

import hashlib

import pytest

from pyaccountingkit.integrations.cfa_fra import promote_cutover_evidence


def _manifest() -> dict[str, object]:
    return {
        "schema_version": "3",
        "consumer": "CFA FRA test consumer",
        "routing_profile": "target_only",
        "artifact_policy": {
            "root": "unused-in-unit-test",
            "require_local_materialization": True,
            "sha256_verified": True,
        },
        "external_evidence": {
            "legacy_identities": {
                "status": "BLOCKED",
                "source": "live-consumer-cutover",
                "reason": "identity migration not yet proven",
            },
            "regulatory_authority": {
                "status": "BLOCKED",
                "source": "live-consumer-cutover",
                "reason": "provider cutover not yet proven",
            },
        },
        "expected_blockers": [
            "evidence:consumer-e2e",
            "evidence:legacy-identities",
            "evidence:regulatory-authority",
        ],
    }


def test_promotion_computes_digest_and_removes_only_matching_blocker(tmp_path) -> None:
    payload = b'{"identity":"real-bytes"}\n'
    artifact = tmp_path / "identity-evidence.json"
    artifact.write_bytes(payload)
    original = _manifest()

    result = promote_cutover_evidence(
        original,
        key="legacy_identities",
        artifact_root=tmp_path,
        artifact=artifact.name,
        source="live-consumer-cutover",
        observed_at="2026-09-30T12:30:00Z",
        producer="cfa-fra-cutover-pipeline",
    )

    record = result.manifest["external_evidence"]["legacy_identities"]
    assert record["status"] == "PASS"
    assert record["sha256"] == hashlib.sha256(payload).hexdigest()
    assert record["artifact"] == artifact.name
    assert "reason" not in record
    assert result.removed_blocker == "evidence:legacy-identities"
    assert result.manifest["expected_blockers"] == [
        "evidence:consumer-e2e",
        "evidence:regulatory-authority",
    ]

    assert original["external_evidence"]["legacy_identities"]["status"] == "BLOCKED"
    assert "evidence:legacy-identities" in original["expected_blockers"]


def test_promotion_rejects_missing_real_artifact(tmp_path) -> None:
    with pytest.raises(RuntimeError):
        promote_cutover_evidence(
            _manifest(),
            key="legacy_identities",
            artifact_root=tmp_path,
            artifact="missing.json",
            source="live-consumer-cutover",
            observed_at="2026-09-30T12:30:00Z",
            producer="cfa-fra-cutover-pipeline",
        )


def test_promotion_rejects_overwriting_existing_pass(tmp_path) -> None:
    payload = b'{"authority":"provider"}\n'
    artifact = tmp_path / "authority.json"
    artifact.write_bytes(payload)

    first = promote_cutover_evidence(
        _manifest(),
        key="regulatory_authority",
        artifact_root=tmp_path,
        artifact=artifact.name,
        source="live-consumer-cutover",
        observed_at="2026-09-30T12:30:00Z",
        producer="cfa-fra-cutover-pipeline",
    )

    with pytest.raises(ValueError, match="already PASS"):
        promote_cutover_evidence(
            first.manifest,
            key="regulatory_authority",
            artifact_root=tmp_path,
            artifact=artifact.name,
            source="live-consumer-cutover",
            observed_at="2026-09-30T12:31:00Z",
            producer="cfa-fra-cutover-pipeline",
        )


def test_promotion_requires_corresponding_blocker_before_state_change(tmp_path) -> None:
    payload = b'{"identity":"verified"}\n'
    artifact = tmp_path / "identity.json"
    artifact.write_bytes(payload)
    manifest = _manifest()
    manifest["expected_blockers"] = [
        "evidence:consumer-e2e",
        "evidence:regulatory-authority",
    ]

    with pytest.raises(ValueError, match="expected blocker"):
        promote_cutover_evidence(
            manifest,
            key="legacy_identities",
            artifact_root=tmp_path,
            artifact=artifact.name,
            source="live-consumer-cutover",
            observed_at="2026-09-30T12:30:00Z",
            producer="cfa-fra-cutover-pipeline",
        )
