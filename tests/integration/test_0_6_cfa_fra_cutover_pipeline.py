"""Integration tests for the CFA FRA cutover evidence pipeline CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "run_cfa_fra_cutover_evidence_pipeline.py"
SOURCE = ROOT / "tests" / "fixtures" / "cfa_fra_cutover_generation" / "identity-source.json"


def _manifest() -> dict[str, object]:
    return {
        "schema_version": "4",
        "consumer": "CFA FRA generation test consumer",
        "routing_profile": "target_only",
        "external_evidence": {
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
            "root": "tests/consumer/cfa_fra/live_evidence",
            "require_local_materialization": True,
            "sha256_verified": True,
            "content_schema_verified": True,
            "schemas": {
                "legacy_identities": "cfa_fra_legacy_identity_migration/v1",
                "regulatory_authority": "cfa_fra_regulatory_authority_cutover/v1",
            },
        },
    }


def test_pipeline_cli_requires_reviewed_plan_before_apply(tmp_path) -> None:
    manifest_path = tmp_path / "RETIREMENT_EVIDENCE.json"
    artifact_root = tmp_path / "live_evidence"
    plan_path = tmp_path / "cutover-plan.json"
    original = _manifest()
    manifest_path.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")

    plan = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--manifest",
            str(manifest_path),
            "--artifact-root",
            str(artifact_root),
            "plan",
            "legacy_identities",
            "--source",
            str(SOURCE),
            "--artifact",
            "legacy-identities.json",
            "--evidence-source",
            "live-consumer-cutover",
            "--observed-at",
            "2026-09-30T15:00:00Z",
            "--producer",
            "pytest",
            "--plan-output",
            str(plan_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert plan.returncode == 0, plan.stdout + plan.stderr
    assert plan_path.is_file()
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == original
    assert not (artifact_root / "legacy-identities.json").exists()

    apply = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--manifest",
            str(manifest_path),
            "--artifact-root",
            str(artifact_root),
            "apply",
            "--plan",
            str(plan_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert apply.returncode == 0, apply.stdout + apply.stderr
    assert (artifact_root / "legacy-identities.json").is_file()
    promoted = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert promoted["external_evidence"]["legacy_identities"]["status"] == "PASS"
    assert promoted["expected_blockers"] == [
        "evidence:consumer-e2e",
        "evidence:regulatory-authority",
    ]


def test_pipeline_cli_rejects_stale_reviewed_plan(tmp_path) -> None:
    manifest_path = tmp_path / "RETIREMENT_EVIDENCE.json"
    artifact_root = tmp_path / "live_evidence"
    plan_path = tmp_path / "cutover-plan.json"
    manifest = _manifest()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    plan = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--manifest",
            str(manifest_path),
            "plan",
            "legacy_identities",
            "--source",
            str(SOURCE),
            "--artifact",
            "legacy-identities.json",
            "--evidence-source",
            "live-consumer-cutover",
            "--observed-at",
            "2026-09-30T15:00:00Z",
            "--producer",
            "pytest",
            "--plan-output",
            str(plan_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert plan.returncode == 0, plan.stdout + plan.stderr

    manifest["external_evidence"]["legacy_identities"]["reason"] = "state changed"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    apply = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--manifest",
            str(manifest_path),
            "--artifact-root",
            str(artifact_root),
            "apply",
            "--plan",
            str(plan_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert apply.returncode != 0
    assert "changed after planning" in apply.stderr
    assert not (artifact_root / "legacy-identities.json").exists()
