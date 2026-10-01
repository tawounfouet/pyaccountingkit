"""LOT-26 tests for fail-closed external legacy-retirement verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    LegacyRetirementAction,
    LegacyRetirementExecutionError,
    LegacyRetirementObservedState,
    LegacyRetirementPlanError,
    build_legacy_retirement_plan,
    retirement_execution_receipt_payload,
    verify_legacy_retirement_execution,
)

ROOT = Path(__file__).resolve().parents[3]
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


def _evidence() -> tuple[object, dict[str, object], dict[str, object], dict[str, object]]:
    inventory = _load(INVENTORY)
    readiness = _load(READY)
    plan = build_legacy_retirement_plan(inventory, readiness)
    observations: list[dict[str, str]] = []
    for item in plan.items:
        state = _EXPECTED_STATE[item.action]
        digest = hashlib.sha256(f"{item.path}:{state.value}".encode()).hexdigest()
        observations.append(
            {
                "path": item.path,
                "state": state.value,
                "source": "isolated-unit-fixture",
                "evidence_checksum": f"sha256:{digest}",
            }
        )
    evidence: dict[str, object] = {
        "schema_version": "1",
        "plan_sha256": plan.plan_sha256,
        "consumer_revision": "live-consumer-after-retirement",
        "observations": observations,
    }
    return plan, inventory, readiness, evidence


def test_retirement_execution_verifies_exact_postconditions() -> None:
    plan, inventory, readiness, evidence = _evidence()
    receipt = verify_legacy_retirement_execution(plan, inventory, readiness, evidence)

    assert len(receipt.observations) == 39
    assert len(receipt.receipt_sha256) == 64
    payload = retirement_execution_receipt_payload(receipt)
    assert payload["verified"] is True
    assert payload["plan_sha256"] == plan.plan_sha256


def test_retirement_execution_rejects_plan_drift() -> None:
    plan, inventory, readiness, evidence = _evidence()
    readiness["evidence"]["consumer_e2e_green"] = False

    with pytest.raises(LegacyRetirementPlanError, match="every evidence gate green"):
        verify_legacy_retirement_execution(plan, inventory, readiness, evidence)


def test_retirement_execution_rejects_missing_observation() -> None:
    plan, inventory, readiness, evidence = _evidence()
    evidence["observations"] = evidence["observations"][:-1]

    with pytest.raises(LegacyRetirementExecutionError, match="exact plan"):
        verify_legacy_retirement_execution(plan, inventory, readiness, evidence)


def test_retirement_execution_rejects_wrong_component_state() -> None:
    plan, inventory, readiness, evidence = _evidence()
    observations = evidence["observations"]
    assert isinstance(observations, list)
    observations[0]["state"] = "PRESENT"

    with pytest.raises(LegacyRetirementExecutionError, match="expected post-retirement state"):
        verify_legacy_retirement_execution(plan, inventory, readiness, evidence)


def test_retirement_execution_rejects_frozen_oracle_revision_as_target() -> None:
    plan, inventory, readiness, evidence = _evidence()
    evidence["consumer_revision"] = plan.oracle_tree_sha

    with pytest.raises(LegacyRetirementExecutionError, match="frozen oracle revision"):
        verify_legacy_retirement_execution(plan, inventory, readiness, evidence)
