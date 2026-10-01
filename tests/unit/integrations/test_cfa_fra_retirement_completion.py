"""LOT-26 tests for the final L26-C retirement completion gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    LegacyRetirementAction,
    LegacyRetirementCompletionError,
    LegacyRetirementExecutionError,
    LegacyRetirementObservedState,
    build_legacy_retirement_plan,
    complete_legacy_retirement,
    retirement_completion_payload,
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


def _fixture() -> tuple[object, dict[str, object], dict[str, object], dict[str, object]]:
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
                "source": "isolated-completion-fixture",
                "evidence_checksum": f"sha256:{digest}",
            }
        )
    evidence: dict[str, object] = {
        "schema_version": "1",
        "plan_sha256": plan.plan_sha256,
        "consumer_revision": "live-consumer-completed-revision",
        "observations": observations,
    }
    return plan, inventory, readiness, evidence


def test_completion_seals_exact_plan_and_execution_receipt() -> None:
    plan, inventory, readiness, evidence = _fixture()
    completion = complete_legacy_retirement(plan, inventory, readiness, evidence)
    payload = retirement_completion_payload(completion)

    assert payload["status"] == "COMPLETE"
    assert payload["ready_for_0_6_rc1"] is True
    assert payload["routing_target_only"] is True
    assert len(completion.completion_sha256) == 64
    assert payload["action_counts"] == {
        "RETIRE_DUPLICATE_ENGINE": 10,
        "VERIFY_CONSUMER_REWIRED": 8,
        "PRESERVE_OR_MIGRATE_PERSISTENCE": 7,
        "KEEP_CONSUMER_CONCERN": 8,
        "PRESERVE_FROZEN_ORACLE": 6,
    }


def test_completion_rejects_plan_drift() -> None:
    plan, inventory, readiness, evidence = _fixture()
    inventory["components"][0]["reason"] = "drifted"

    with pytest.raises(LegacyRetirementCompletionError, match="current reviewed retirement plan"):
        complete_legacy_retirement(plan, inventory, readiness, evidence)


def test_completion_rejects_non_target_only_readiness() -> None:
    plan, inventory, readiness, evidence = _fixture()
    readiness["routing_target_only"] = False

    with pytest.raises(LegacyRetirementCompletionError, match="target-only routing"):
        complete_legacy_retirement(plan, inventory, readiness, evidence)


def test_completion_rejects_incomplete_execution_evidence() -> None:
    plan, inventory, readiness, evidence = _fixture()
    observations = evidence["observations"]
    assert isinstance(observations, list)
    observations.pop()

    with pytest.raises(LegacyRetirementExecutionError, match="exact plan"):
        complete_legacy_retirement(plan, inventory, readiness, evidence)
