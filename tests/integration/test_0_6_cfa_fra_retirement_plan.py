"""Integration tests for the CFA FRA legacy-retirement planner CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "plan_cfa_fra_legacy_retirement.py"
INVENTORY = ROOT / "tests" / "consumer" / "cfa_fra" / "LEGACY_RETIREMENT_INVENTORY.json"
READY = ROOT / "tests" / "fixtures" / "cfa_fra_retirement_plan" / "RETIREMENT_READINESS_READY.json"


def test_retirement_planner_cli_emits_reviewable_non_executing_plan(tmp_path) -> None:
    output = tmp_path / "retirement-plan.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--readiness",
            str(READY),
            "--inventory",
            str(INVENTORY),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Execution: NOT PERFORMED" in result.stdout
    assert "Frozen oracle mutation: FORBIDDEN" in result.stdout
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1"
    assert len(payload["items"]) == 39
    assert any(
        item["action"] == "RETIRE_DUPLICATE_ENGINE"
        for item in payload["items"]
    )
    assert any(
        item["action"] == "PRESERVE_FROZEN_ORACLE"
        for item in payload["items"]
    )


def test_retirement_planner_cli_rejects_blocked_readiness(tmp_path) -> None:
    readiness = json.loads(READY.read_text(encoding="utf-8"))
    readiness["ready"] = False
    readiness["blockers"] = ["evidence:consumer-e2e"]
    readiness["expected_blockers"] = ["evidence:consumer-e2e"]
    readiness["evidence"]["consumer_e2e_green"] = False
    blocked = tmp_path / "blocked.json"
    blocked.write_text(json.dumps(readiness), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--readiness",
            str(blocked),
            "--inventory",
            str(INVENTORY),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "requires MIG-13 ready=true" in result.stderr
