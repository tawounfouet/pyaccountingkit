"""Integration tests for the CFA FRA live-consumer repository binding CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_cfa_fra_consumer_binding.py"
CANONICAL = ROOT / "tests" / "consumer" / "cfa_fra" / "CONSUMER_BINDING.json"


def test_canonical_binding_remains_explicitly_unbound() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--binding", str(CANONICAL)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert '"bound": false' in result.stdout
    assert "repository binding: UNBOUND" in result.stdout


def test_require_bound_fails_for_current_canonical_state() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--binding", str(CANONICAL), "--require-bound"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "remains UNBOUND" in result.stderr


def test_bound_binding_can_be_pinned_to_expected_revision(tmp_path: Path) -> None:
    revision = "b" * 40
    payload = {
        "schema_version": "1",
        "status": "BOUND",
        "consumer": "CFA FRA Django MVP Sprint 7",
        "binding": {
            "schema": "cfa_fra_live_consumer_binding/v1",
            "kind": "live_consumer_repository_binding",
            "consumer": "CFA FRA Django MVP Sprint 7",
            "repository": "tawounfouet/cfa-fra-live",
            "repository_url": "https://github.com/tawounfouet/cfa-fra-live",
            "default_branch": "main",
            "revision_sha": revision,
            "environment": "production",
            "observed_at": "2026-10-01T06:00:00Z",
            "producer": "integration-test",
        },
    }
    path = tmp_path / "binding.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--binding",
            str(path),
            "--require-bound",
            "--expected-revision",
            revision,
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert '"bound": true' in result.stdout
    assert revision in result.stdout
