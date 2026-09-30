"""LOT-26 tests for the reviewable CFA FRA cutover evidence pipeline."""

from __future__ import annotations

import json

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    CutoverEvidencePipelineError,
    apply_cutover_evidence_pipeline,
    pipeline_plan_from_mapping,
    pipeline_plan_payload,
    plan_cutover_evidence_pipeline,
)


def _manifest() -> dict[str, object]:
    return {
        "schema_version": "5",
        "consumer": "CFA FRA generation test consumer",
        "routing_profile": "target_only",
        "external_evidence": {
            "consumer_e2e": {
                "status": "BLOCKED",
                "source": "live-consumer-cutover",
                "reason": "consumer E2E not yet proven",
            },
            "legacy_identities": {
                "status": "BLOCKED",
                "source": "live-consumer-cutover",
                "reason": "identity proof not supplied",
            },
            "regulatory_authority": {
                "status": "BLOCKED",
                "source": "live-consumer-cutover",
                "reason": "authority proof not supplied",
            },
        },
        "expected_blockers": [
            "evidence:consumer-e2e",
            "evidence:legacy-identities",
            "evidence:regulatory-authority",
        ],
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
    }


def _consumer_source() -> dict[str, object]:
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
        "consumer": "CFA FRA generation test consumer",
        "observed_at": "2026-09-30T16:00:00Z",
        "environment": "production",
        "producer": "cfa-fra-live-e2e",
        "scenarios": [
            {
                "scenario": scenario,
                "status": "PASS",
                "source": f"live:{scenario}",
                "evidence_checksum": "sha256:" + ("b" * 64),
            }
            for scenario in scenarios
        ],
    }


def _identity_source() -> dict[str, object]:
    return {
        "consumer": "CFA FRA generation test consumer",
        "generated_at": "2026-09-30T15:00:00Z",
        "expected_legacy_records": 1,
        "links": [
            {
                "legacy_type": "JournalEntry",
                "legacy_id": "legacy-1",
                "target_type": "JournalEntry",
                "target_id": "target-1",
                "source": "CFA_FRA_LEGACY",
            }
        ],
    }


def _plan():
    return plan_cutover_evidence_pipeline(
        _manifest(),
        key="legacy_identities",
        source_observation=_identity_source(),
        artifact="legacy-identities.json",
        evidence_source="live-consumer-cutover",
        observed_at="2026-09-30T15:00:00Z",
        producer="cfa-fra-cutover-pipeline",
    )


def test_pipeline_plans_consumer_e2e_as_first_class_evidence() -> None:
    plan = plan_cutover_evidence_pipeline(
        _manifest(),
        key="consumer_e2e",
        source_observation=_consumer_source(),
        artifact="consumer-e2e.json",
        evidence_source="live-consumer-cutover",
        observed_at="2026-09-30T16:00:00Z",
        producer="cfa-fra-cutover-pipeline",
    )

    assert plan.removed_blocker == "evidence:consumer-e2e"
    assert plan.candidate_manifest["expected_blockers"] == [
        "evidence:legacy-identities",
        "evidence:regulatory-authority",
    ]


def test_pipeline_plan_round_trips_and_removes_only_matching_blocker() -> None:
    plan = _plan()
    restored = pipeline_plan_from_mapping(pipeline_plan_payload(plan))

    assert restored == plan
    assert len(plan.artifact_sha256) == 64
    assert plan.removed_blocker == "evidence:legacy-identities"
    assert plan.candidate_manifest["expected_blockers"] == [
        "evidence:consumer-e2e",
        "evidence:regulatory-authority",
    ]


def test_pipeline_apply_materializes_reviewed_artifact_and_manifest(tmp_path) -> None:
    plan = _plan()
    manifest_path = tmp_path / "RETIREMENT_EVIDENCE.json"
    artifact_root = tmp_path / "live_evidence"
    current = _manifest()
    manifest_path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")

    promotion = apply_cutover_evidence_pipeline(
        plan,
        current_manifest=current,
        manifest_path=manifest_path,
        artifact_root=artifact_root,
    )

    assert promotion.evidence.sha256 == plan.artifact_sha256
    artifact_path = artifact_root / "legacy-identities.json"
    assert artifact_path.is_file()
    applied = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert applied == plan.candidate_manifest
    assert applied["external_evidence"]["legacy_identities"]["status"] == "PASS"


def test_pipeline_rejects_stale_manifest_before_artifact_write(tmp_path) -> None:
    plan = _plan()
    stale = _manifest()
    stale["consumer"] = "Changed Consumer"
    manifest_path = tmp_path / "RETIREMENT_EVIDENCE.json"
    manifest_path.write_text(json.dumps(stale), encoding="utf-8")
    artifact_root = tmp_path / "live_evidence"

    with pytest.raises(CutoverEvidencePipelineError, match="changed after planning"):
        apply_cutover_evidence_pipeline(
            plan,
            current_manifest=stale,
            manifest_path=manifest_path,
            artifact_root=artifact_root,
        )

    assert not (artifact_root / "legacy-identities.json").exists()


def test_pipeline_rejects_existing_artifact_without_explicit_overwrite(tmp_path) -> None:
    plan = _plan()
    current = _manifest()
    manifest_path = tmp_path / "RETIREMENT_EVIDENCE.json"
    manifest_path.write_text(json.dumps(current), encoding="utf-8")
    artifact_root = tmp_path / "live_evidence"
    artifact_root.mkdir()
    target = artifact_root / "legacy-identities.json"
    target.write_text("do-not-overwrite", encoding="utf-8")

    with pytest.raises(CutoverEvidencePipelineError, match="explicit overwrite"):
        apply_cutover_evidence_pipeline(
            plan,
            current_manifest=current,
            manifest_path=manifest_path,
            artifact_root=artifact_root,
        )

    assert target.read_text(encoding="utf-8") == "do-not-overwrite"


def test_pipeline_plan_rejects_tampered_sha256() -> None:
    payload = pipeline_plan_payload(_plan())
    payload["artifact_sha256"] = "0" * 63 + "X"

    with pytest.raises(CutoverEvidencePipelineError, match="lowercase SHA-256"):
        pipeline_plan_from_mapping(payload)
