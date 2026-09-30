"""Integration tests for the CFA FRA live-evidence promotion CLI."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "promote_cfa_fra_cutover_evidence.py"
FIXTURE = ROOT / "tests" / "fixtures" / "cfa_fra_cutover_promotion" / "sample-evidence.json"


def _manifest() -> dict[str, object]:
    return {
        "schema_version": "5",
        "consumer": "CFA FRA test consumer",
        "routing_profile": "target_only",
        "artifact_policy": {
            "root": "tests/fixtures/cfa_fra_cutover_promotion",
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
                "reason": "not promoted yet",
            },
            "regulatory_authority": {
                "status": "BLOCKED",
                "source": "live-consumer-cutover",
                "reason": "not promoted yet",
            },
        },
        "expected_blockers": [
            "evidence:consumer-e2e",
            "evidence:legacy-identities",
            "evidence:regulatory-authority",
        ],
    }


def _command(manifest: Path, *, write: bool = False) -> list[str]:
    command = [
        sys.executable,
        str(SCRIPT),
        "legacy_identities",
        "--artifact",
        FIXTURE.name,
        "--source",
        "test-promotion",
        "--observed-at",
        "2026-09-30T12:30:00Z",
        "--producer",
        "pytest",
        "--manifest",
        str(manifest),
    ]
    if write:
        command.append("--write")
    return command


def test_promotion_cli_is_dry_run_by_default(tmp_path) -> None:
    manifest = tmp_path / "retirement.json"
    original = _manifest()
    manifest.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")

    result = subprocess.run(
        _command(manifest),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Dry-run only" in result.stdout
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() in result.stdout
    assert json.loads(manifest.read_text(encoding="utf-8")) == original


def test_promotion_cli_writes_atomically_only_when_explicit(tmp_path) -> None:
    manifest = tmp_path / "retirement.json"
    manifest.write_text(json.dumps(_manifest(), indent=2) + "\n", encoding="utf-8")

    result = subprocess.run(
        _command(manifest, write=True),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    record = payload["external_evidence"]["legacy_identities"]

    assert record["status"] == "PASS"
    assert record["sha256"] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert "evidence:legacy-identities" not in payload["expected_blockers"]
    assert "evidence:regulatory-authority" in payload["expected_blockers"]
