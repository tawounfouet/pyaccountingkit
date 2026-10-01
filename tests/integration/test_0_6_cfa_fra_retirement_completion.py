"""Integration tests for the L26-C retirement completion CLI."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from pyaccountingkit.integrations.cfa_fra import (
    LegacyRetirementAction,
    LegacyRetirementObservedState,
    build_legacy_retirement_plan,
    retirement_plan_payload,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "qualify_cfa_fra_legacy_retirement_completion.py"
INVENTORY = ROOT / "tests" / "consumer" / "cfa_fra" / "LEGACY_RETIREMENT_INVENTORY.json"
READY = ROOT / "tests" / "fixtures" / "cfa_fra_retirement_plan" / "RETIREMENT_READINESS_READY.json"

_EXPECTED_STATE = {
    LegacyRetirementAction.RETIRE_DUPLICATE_ENGINE: LegacyRetirementObservedState.RETIRED,
    LegacyRetirementAction.VERIFY_CONSUMER_REWIRED: LegacyRetirementObservedState.REWIRED,
    LegacyRetirementAction.PRESERVE_OR_MIGRATE_PERSISTENCE: LegacyRetirementObservedState.PRESERVED,
    LegacyRetirementAction.KEEP_CONSUMER_CONCERN: LegacyRetirementObservedState.PRESENT,
    LegacyRetirementAction.PRESERVE_FROZEN_ORACLE: LegacyRetirementObservedState.PRESERVED,
}


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_retirement_completion_cli_emits_rc1_eligible_proof(tmp_path) -> None:
    inventory = _load(INVENTORY)
    readiness = _load(READY)
    plan = build_legacy_retirement_plan(inventory, readiness)

    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(retirement_plan_payload(plan)), encoding="utf-8")

    observations: list[dict[str, str]] = []
    for item in plan.items:
        state = _EXPECTED_STATE[item.action]
        digest = hashlib.sha256(f"{item.path}:{state.value}".encode()).hexdigest()
        observations.append(
            {
                "path": item.path,
                "state": state.value,
                "source": "isolated-completion-integration",
                "evidence_checksum": f"sha256:{digest}",
            }
        )
    evidence_path = tmp_path / "execution-evidence.json"
    evidence_path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "plan_sha256": plan.plan_sha256,
                "consumer_revision": "integration-completed-revision",
                "observations": observations,
            }
        ),
        encoding="utf-8",
    )

    output = tmp_path / "completion.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--readiness",
            str(READY),
            "--inventory",
            str(INVENTORY),
            "--plan",
            str(plan_path),
            "--execution-evidence",
            str(evidence_path),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "L26-C legacy retirement: COMPLETE" in result.stdout
    assert "0.6.0rc1 qualification: ELIGIBLE" in result.stdout
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "COMPLETE"
    assert payload["ready_for_0_6_rc1"] is True
