"""LOT-26 tests for deterministic CFA FRA legacy-retirement planning."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    LegacyRetirementAction,
    LegacyRetirementPlanError,
    build_legacy_retirement_plan,
    retirement_plan_payload,
)

ROOT = Path(__file__).resolve().parents[3]
INVENTORY = ROOT / "tests" / "consumer" / "cfa_fra" / "LEGACY_RETIREMENT_INVENTORY.json"
READY = ROOT / "tests" / "fixtures" / "cfa_fra_retirement_plan" / "RETIREMENT_READINESS_READY.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_retirement_plan_is_deterministic_and_preserves_frozen_oracle() -> None:
    plan = build_legacy_retirement_plan(_load(INVENTORY), _load(READY))
    repeated = build_legacy_retirement_plan(_load(INVENTORY), _load(READY))

    assert plan == repeated
    assert len(plan.plan_sha256) == 64
    assert len(plan.by_action(LegacyRetirementAction.RETIRE_DUPLICATE_ENGINE)) == 10
    assert len(plan.by_action(LegacyRetirementAction.VERIFY_CONSUMER_REWIRED)) == 8
    assert len(plan.by_action(LegacyRetirementAction.PRESERVE_OR_MIGRATE_PERSISTENCE)) == 7
    assert len(plan.by_action(LegacyRetirementAction.KEEP_CONSUMER_CONCERN)) == 8
    frozen = plan.by_action(LegacyRetirementAction.PRESERVE_FROZEN_ORACLE)
    assert len(frozen) == 6
    assert all("/tests/" in item.path for item in frozen)


def test_retirement_plan_rejects_mig13_not_ready() -> None:
    readiness = _load(READY)
    readiness["ready"] = False
    readiness["blockers"] = ["evidence:consumer-e2e"]
    readiness["expected_blockers"] = ["evidence:consumer-e2e"]
    readiness["evidence"]["consumer_e2e_green"] = False

    with pytest.raises(LegacyRetirementPlanError, match="ready=true"):
        build_legacy_retirement_plan(_load(INVENTORY), readiness)


def test_retirement_plan_rejects_hidden_non_green_evidence() -> None:
    readiness = _load(READY)
    readiness["evidence"]["identities_traceable"] = False

    with pytest.raises(LegacyRetirementPlanError, match="every evidence gate green"):
        build_legacy_retirement_plan(_load(INVENTORY), readiness)


def test_retirement_plan_rejects_mutable_oracle_policy() -> None:
    inventory = _load(INVENTORY)
    inventory["policy"]["snapshot_is_immutable"] = False

    with pytest.raises(LegacyRetirementPlanError, match="immutable frozen oracle"):
        build_legacy_retirement_plan(inventory, _load(READY))


def test_retirement_plan_payload_never_contains_execute_instruction() -> None:
    payload = retirement_plan_payload(build_legacy_retirement_plan(_load(INVENTORY), _load(READY)))
    rendered = json.dumps(payload)

    assert payload["schema_version"] == "1"
    assert "DELETE_FILE" not in rendered
    assert "EXECUTE" not in rendered
    assert "PRESERVE_FROZEN_ORACLE" in rendered
