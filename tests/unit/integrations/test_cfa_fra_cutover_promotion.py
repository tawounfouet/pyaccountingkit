"""LOT-26 tests for controlled CFA FRA cutover evidence promotion."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    CutoverArtifactVerificationError,
    promote_cutover_evidence,
)


def _manifest() -> dict[str, object]:
    return {
        "schema_version": "5",
        "consumer": "CFA FRA test consumer",
        "routing_profile": "target_only",
        "artifact_policy": {
            "root": "unused-in-unit-test",
            "require_local_materialization": True,
            "sha256_verified": True,
            "content_schema_verified": True,
            "schemas": {
                "consumer_e2e": "cfa_fra_consumer_e2e_cutover/v1",
                "legacy_identities": "cfa_fra_legacy_identity_migration/v1",
                "regulatory_authority": "cfa_fra_regulatory_authority_cutover/v1",
            },
        },
        "external_evidence": {
            "consumer_e2e": {
                "status": "BLOCKED",
                "source": "live-consumer-cutover",
                "reason": "consumer E2E not yet proven",
            },
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


def _consumer_payload() -> dict[str, object]:
    scenarios = (
        "login",
        "organization_context",
        "fec_import",
        "journal",
        "ledger",
        "balance",
        "financial_statements",
        "controls",
        "closing",
        "exports",
    )
    return {
        "schema": "cfa_fra_consumer_e2e_cutover/v1",
        "kind": "consumer_e2e_cutover",
        "consumer": "CFA FRA test consumer",
        "observed_at": "2026-09-30T16:00:00Z",
        "environment": "production",
        "producer": "cfa-fra-live-e2e",
        "routing_profile": "target_only",
        "scenarios": [
            {
                "scenario": scenario,
                "status": "PASS",
                "source": f"live:{scenario}",
                "evidence_checksum": "sha256:" + ("a" * 64),
            }
            for scenario in scenarios
        ],
    }


def _identity_payload() -> dict[str, object]:
    return {
        "schema": "cfa_fra_legacy_identity_migration/v1",
        "kind": "legacy_identity_migration",
        "consumer": "CFA FRA test consumer",
        "generated_at": "2026-09-30T12:30:00Z",
        "source_system": "CFA_FRA_LEGACY",
        "target_system": "PYACCOUNTINGKIT",
        "summary": {
            "total_legacy_records": 1,
            "mapped_records": 1,
            "unresolved_records": 0,
        },
        "mappings": [
            {
                "legacy_type": "JournalEntry",
                "legacy_id": "legacy-42",
                "target_type": "JournalEntry",
                "target_id": "target-42",
                "source": "CFA_FRA_LEGACY",
            }
        ],
    }


def _authority_payload() -> dict[str, object]:
    return {
        "schema": "cfa_fra_regulatory_authority_cutover/v1",
        "kind": "regulatory_authority_cutover",
        "consumer": "CFA FRA test consumer",
        "observed_at": "2026-09-30T12:30:00Z",
        "provider": {"name": "PyAccountingKit", "version": "0.6.0b16"},
        "routing_profile": "target_only",
        "local_framework_account_authority": False,
        "local_seed_commands_authoritative": False,
        "effective_plan_delegated": True,
        "sample_resolutions": [
            {
                "standard_id": "SYSCOHADA",
                "edition": "2017",
                "reference_key": "101000",
                "target_reference_id": "reference-101000",
            }
        ],
    }


def _write_json(path: Path, payload: dict[str, object]) -> bytes:
    encoded = (json.dumps(payload, sort_keys=True) + "\n").encode()
    path.write_bytes(encoded)
    return encoded


def test_consumer_e2e_promotion_removes_only_consumer_blocker(tmp_path) -> None:
    artifact = tmp_path / "consumer-e2e.json"
    _write_json(artifact, _consumer_payload())

    result = promote_cutover_evidence(
        _manifest(),
        key="consumer_e2e",
        artifact_root=tmp_path,
        artifact=artifact.name,
        source="live-consumer-cutover",
        observed_at="2026-09-30T16:00:00Z",
        producer="cfa-fra-cutover-pipeline",
    )

    assert result.removed_blocker == "evidence:consumer-e2e"
    assert result.manifest["external_evidence"]["consumer_e2e"]["status"] == "PASS"
    assert result.manifest["expected_blockers"] == [
        "evidence:legacy-identities",
        "evidence:regulatory-authority",
    ]


def test_promotion_computes_digest_and_removes_only_matching_blocker(tmp_path) -> None:
    artifact = tmp_path / "identity-evidence.json"
    payload = _write_json(artifact, _identity_payload())
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
    with pytest.raises(CutoverArtifactVerificationError):
        promote_cutover_evidence(
            _manifest(),
            key="legacy_identities",
            artifact_root=tmp_path,
            artifact="missing.json",
            source="live-consumer-cutover",
            observed_at="2026-09-30T12:30:00Z",
            producer="cfa-fra-cutover-pipeline",
        )


def test_promotion_rejects_semantically_wrong_artifact(tmp_path) -> None:
    artifact = tmp_path / "wrong.json"
    _write_json(artifact, _authority_payload())

    with pytest.raises(CutoverArtifactVerificationError):
        promote_cutover_evidence(
            _manifest(),
            key="legacy_identities",
            artifact_root=tmp_path,
            artifact=artifact.name,
            source="live-consumer-cutover",
            observed_at="2026-09-30T12:30:00Z",
            producer="cfa-fra-cutover-pipeline",
        )


def test_promotion_rejects_overwriting_existing_pass(tmp_path) -> None:
    artifact = tmp_path / "authority.json"
    _write_json(artifact, _authority_payload())

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
    artifact = tmp_path / "identity.json"
    _write_json(artifact, _identity_payload())
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


def test_promotion_rejects_artifact_for_another_consumer(tmp_path) -> None:
    artifact = tmp_path / "identity-other-consumer.json"
    payload = _identity_payload()
    payload["consumer"] = "Another Consumer"
    _write_json(artifact, payload)

    with pytest.raises(ValueError, match="artifact consumer"):
        promote_cutover_evidence(
            _manifest(),
            key="legacy_identities",
            artifact_root=tmp_path,
            artifact=artifact.name,
            source="live-consumer-cutover",
            observed_at="2026-09-30T12:30:00Z",
            producer="cfa-fra-cutover-pipeline",
        )
