"""Final L26-C completion gate for CFA FRA legacy retirement."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from pyaccountingkit.integrations.cfa_fra.retirement_execution import (
    verify_legacy_retirement_execution,
)
from pyaccountingkit.integrations.cfa_fra.retirement_plan import (
    LegacyRetirementAction,
    LegacyRetirementPlan,
    build_legacy_retirement_plan,
)


class LegacyRetirementCompletionError(RuntimeError):
    """Raised when L26-C cannot be sealed as complete."""


@dataclass(frozen=True, slots=True)
class LegacyRetirementCompletion:
    """Deterministic proof that L26-C is complete and eligible for RC qualification."""

    oracle_tree_sha: str
    consumer_revision: str
    plan_sha256: str
    execution_receipt_sha256: str
    inventory_sha256: str
    readiness_sha256: str
    action_counts: tuple[tuple[LegacyRetirementAction, int], ...]
    completion_sha256: str


def _canonical_bytes(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def complete_legacy_retirement(
    plan: LegacyRetirementPlan,
    inventory: Mapping[str, object],
    readiness: Mapping[str, object],
    execution_evidence: Mapping[str, object],
) -> LegacyRetirementCompletion:
    """Seal L26-C only when current readiness and verified execution still match exactly."""
    current_plan = build_legacy_retirement_plan(inventory, readiness)
    if current_plan != plan:
        raise LegacyRetirementCompletionError(
            "retirement completion requires the current reviewed retirement plan"
        )
    if readiness.get("routing_target_only") is not True:
        raise LegacyRetirementCompletionError(
            "retirement completion requires target-only routing"
        )
    if readiness.get("ready") is not True:
        raise LegacyRetirementCompletionError(
            "retirement completion requires MIG-13 ready=true"
        )
    if readiness.get("blockers") != [] or readiness.get("expected_blockers") != []:
        raise LegacyRetirementCompletionError(
            "retirement completion requires empty blocker sets"
        )

    receipt = verify_legacy_retirement_execution(
        plan,
        inventory,
        readiness,
        execution_evidence,
    )
    if receipt.inventory_sha256 != plan.inventory_sha256:
        raise LegacyRetirementCompletionError(
            "retirement execution receipt inventory fingerprint drifted"
        )
    if receipt.readiness_sha256 != plan.readiness_sha256:
        raise LegacyRetirementCompletionError(
            "retirement execution receipt readiness fingerprint drifted"
        )
    if receipt.consumer_revision == plan.oracle_tree_sha:
        raise LegacyRetirementCompletionError(
            "retirement completion may not target the frozen oracle revision"
        )

    counts = tuple(
        (action, len(plan.by_action(action)))
        for action in LegacyRetirementAction
    )
    body: dict[str, object] = {
        "oracle_tree_sha": plan.oracle_tree_sha,
        "consumer_revision": receipt.consumer_revision,
        "plan_sha256": plan.plan_sha256,
        "execution_receipt_sha256": receipt.receipt_sha256,
        "inventory_sha256": plan.inventory_sha256,
        "readiness_sha256": plan.readiness_sha256,
        "routing_target_only": True,
        "ready_for_0_6_rc1": True,
        "action_counts": {
            action.value: count
            for action, count in counts
        },
    }
    return LegacyRetirementCompletion(
        oracle_tree_sha=plan.oracle_tree_sha,
        consumer_revision=receipt.consumer_revision,
        plan_sha256=plan.plan_sha256,
        execution_receipt_sha256=receipt.receipt_sha256,
        inventory_sha256=plan.inventory_sha256,
        readiness_sha256=plan.readiness_sha256,
        action_counts=counts,
        completion_sha256=hashlib.sha256(_canonical_bytes(body)).hexdigest(),
    )


def retirement_completion_payload(
    completion: LegacyRetirementCompletion,
) -> dict[str, object]:
    """Serialize the final L26-C completion proof."""
    return {
        "schema_version": "1",
        "status": "COMPLETE",
        "ready_for_0_6_rc1": True,
        "routing_target_only": True,
        "oracle_tree_sha": completion.oracle_tree_sha,
        "consumer_revision": completion.consumer_revision,
        "plan_sha256": completion.plan_sha256,
        "execution_receipt_sha256": completion.execution_receipt_sha256,
        "inventory_sha256": completion.inventory_sha256,
        "readiness_sha256": completion.readiness_sha256,
        "completion_sha256": completion.completion_sha256,
        "action_counts": {
            action.value: count
            for action, count in completion.action_counts
        },
    }


__all__ = [
    "LegacyRetirementCompletion",
    "LegacyRetirementCompletionError",
    "complete_legacy_retirement",
    "retirement_completion_payload",
]
