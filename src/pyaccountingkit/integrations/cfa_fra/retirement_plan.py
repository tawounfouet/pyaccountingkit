"""Deterministic CFA FRA legacy-retirement planning for LOT-26."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import cast


class LegacyRetirementPlanError(RuntimeError):
    """Raised when MIG-13 evidence cannot support a retirement plan."""


class LegacyRetirementDisposition(StrEnum):
    """Inventory disposition assigned to one live-consumer equivalent."""

    RETIRE_ENGINE = "RETIRE_ENGINE"
    REWIRE_CONSUMER = "REWIRE_CONSUMER"
    MIGRATE_PERSISTENCE = "MIGRATE_PERSISTENCE"
    KEEP_CONSUMER = "KEEP_CONSUMER"
    FROZEN_ORACLE = "FROZEN_ORACLE"


class LegacyRetirementAction(StrEnum):
    """Non-executing action described by the retirement plan."""

    RETIRE_DUPLICATE_ENGINE = "RETIRE_DUPLICATE_ENGINE"
    VERIFY_CONSUMER_REWIRED = "VERIFY_CONSUMER_REWIRED"
    PRESERVE_OR_MIGRATE_PERSISTENCE = "PRESERVE_OR_MIGRATE_PERSISTENCE"
    KEEP_CONSUMER_CONCERN = "KEEP_CONSUMER_CONCERN"
    PRESERVE_FROZEN_ORACLE = "PRESERVE_FROZEN_ORACLE"


_ACTIONS: dict[LegacyRetirementDisposition, LegacyRetirementAction] = {
    LegacyRetirementDisposition.RETIRE_ENGINE: LegacyRetirementAction.RETIRE_DUPLICATE_ENGINE,
    LegacyRetirementDisposition.REWIRE_CONSUMER: LegacyRetirementAction.VERIFY_CONSUMER_REWIRED,
    LegacyRetirementDisposition.MIGRATE_PERSISTENCE: (
        LegacyRetirementAction.PRESERVE_OR_MIGRATE_PERSISTENCE
    ),
    LegacyRetirementDisposition.KEEP_CONSUMER: LegacyRetirementAction.KEEP_CONSUMER_CONCERN,
    LegacyRetirementDisposition.FROZEN_ORACLE: LegacyRetirementAction.PRESERVE_FROZEN_ORACLE,
}


@dataclass(frozen=True, slots=True)
class LegacyRetirementPlanItem:
    """One deterministic live-consumer retirement action."""

    path: str
    disposition: LegacyRetirementDisposition
    action: LegacyRetirementAction
    reason: str


@dataclass(frozen=True, slots=True)
class LegacyRetirementPlan:
    """Reviewed, non-executing legacy-retirement plan."""

    oracle_tree_sha: str
    inventory_sha256: str
    readiness_sha256: str
    items: tuple[LegacyRetirementPlanItem, ...]
    plan_sha256: str

    def by_action(
        self,
        action: LegacyRetirementAction,
    ) -> tuple[LegacyRetirementPlanItem, ...]:
        return tuple(item for item in self.items if item.action is action)


def _canonical_bytes(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _require_ready(readiness: Mapping[str, object]) -> None:
    if readiness.get("routing_target_only") is not True:
        raise LegacyRetirementPlanError("retirement planning requires target-only routing")
    if readiness.get("ready") is not True:
        raise LegacyRetirementPlanError("retirement planning requires MIG-13 ready=true")

    blockers = readiness.get("blockers")
    expected = readiness.get("expected_blockers")
    if blockers != [] or expected != []:
        raise LegacyRetirementPlanError(
            "retirement planning requires empty calculated and expected blocker sets"
        )

    raw_evidence = readiness.get("evidence")
    if not isinstance(raw_evidence, dict):
        raise LegacyRetirementPlanError("retirement readiness evidence is missing")
    evidence = cast(Mapping[str, object], raw_evidence)
    required = (
        "golden_parity_green",
        "production_adapters_green",
        "consumer_e2e_green",
        "identities_traceable",
        "regulatory_authority_replaced",
    )
    missing = tuple(name for name in required if evidence.get(name) is not True)
    if missing:
        raise LegacyRetirementPlanError(
            "retirement planning requires every evidence gate green: "
            + ", ".join(missing)
        )


def build_legacy_retirement_plan(
    inventory: Mapping[str, object],
    readiness: Mapping[str, object],
) -> LegacyRetirementPlan:
    """Build a deterministic, non-mutating plan only after MIG-13 is ready."""
    _require_ready(readiness)

    if inventory.get("schema_version") != "1":
        raise LegacyRetirementPlanError("retirement inventory must use schema_version='1'")

    raw_oracle = inventory.get("oracle")
    raw_policy = inventory.get("policy")
    raw_components = inventory.get("components")
    if not isinstance(raw_oracle, dict):
        raise LegacyRetirementPlanError("retirement inventory oracle is missing")
    if not isinstance(raw_policy, dict):
        raise LegacyRetirementPlanError("retirement inventory policy is missing")
    if not isinstance(raw_components, list) or not raw_components:
        raise LegacyRetirementPlanError("retirement inventory components are missing")

    oracle = cast(Mapping[str, object], raw_oracle)
    policy = cast(Mapping[str, object], raw_policy)
    tree_sha = oracle.get("tree_sha")
    if not isinstance(tree_sha, str) or not tree_sha:
        raise LegacyRetirementPlanError("retirement inventory oracle tree_sha is missing")
    if policy.get("snapshot_is_immutable") is not True:
        raise LegacyRetirementPlanError("retirement plan requires immutable frozen oracle")
    if policy.get("applies_to") != "live-consumer-equivalents":
        raise LegacyRetirementPlanError(
            "retirement plan may target live-consumer-equivalents only"
        )
    if policy.get("retirement_requires_mig13_ready") is not True:
        raise LegacyRetirementPlanError("retirement inventory must require MIG-13 readiness")

    items: list[LegacyRetirementPlanItem] = []
    seen_paths: set[str] = set()
    for index, raw in enumerate(raw_components):
        if not isinstance(raw, dict):
            raise LegacyRetirementPlanError(
                f"retirement inventory component {index} must be a JSON object"
            )
        component = cast(Mapping[str, object], raw)
        path = component.get("path")
        reason = component.get("reason")
        raw_disposition = component.get("disposition")
        if not isinstance(path, str) or not path:
            raise LegacyRetirementPlanError(f"component {index} path must be non-empty")
        if path in seen_paths:
            raise LegacyRetirementPlanError(f"duplicate retirement path: {path}")
        seen_paths.add(path)
        if not isinstance(reason, str) or not reason.strip():
            raise LegacyRetirementPlanError(f"{path}: retirement reason must be non-empty")
        if not isinstance(raw_disposition, str):
            raise LegacyRetirementPlanError(f"{path}: retirement disposition is missing")
        try:
            disposition = LegacyRetirementDisposition(raw_disposition)
        except ValueError as exc:
            raise LegacyRetirementPlanError(
                f"{path}: unsupported retirement disposition {raw_disposition!r}"
            ) from exc

        action = _ACTIONS[disposition]
        if disposition is LegacyRetirementDisposition.FROZEN_ORACLE:
            if action is not LegacyRetirementAction.PRESERVE_FROZEN_ORACLE:
                raise LegacyRetirementPlanError("frozen oracle may never receive a destructive action")

        items.append(
            LegacyRetirementPlanItem(
                path=path,
                disposition=disposition,
                action=action,
                reason=reason,
            )
        )

    ordered = tuple(sorted(items, key=lambda item: (item.action.value, item.path)))
    inventory_sha256 = _sha256(inventory)
    readiness_sha256 = _sha256(readiness)
    plan_payload: dict[str, object] = {
        "oracle_tree_sha": tree_sha,
        "inventory_sha256": inventory_sha256,
        "readiness_sha256": readiness_sha256,
        "items": [
            {
                "path": item.path,
                "disposition": item.disposition.value,
                "action": item.action.value,
                "reason": item.reason,
            }
            for item in ordered
        ],
    }
    return LegacyRetirementPlan(
        oracle_tree_sha=tree_sha,
        inventory_sha256=inventory_sha256,
        readiness_sha256=readiness_sha256,
        items=ordered,
        plan_sha256=hashlib.sha256(_canonical_bytes(plan_payload)).hexdigest(),
    )


def retirement_plan_payload(plan: LegacyRetirementPlan) -> dict[str, object]:
    """Serialize a retirement plan without adding executable side effects."""
    return {
        "schema_version": "1",
        "oracle_tree_sha": plan.oracle_tree_sha,
        "inventory_sha256": plan.inventory_sha256,
        "readiness_sha256": plan.readiness_sha256,
        "plan_sha256": plan.plan_sha256,
        "items": [
            {
                "path": item.path,
                "disposition": item.disposition.value,
                "action": item.action.value,
                "reason": item.reason,
            }
            for item in plan.items
        ],
    }


__all__ = [
    "LegacyRetirementAction",
    "LegacyRetirementDisposition",
    "LegacyRetirementPlan",
    "LegacyRetirementPlanError",
    "LegacyRetirementPlanItem",
    "build_legacy_retirement_plan",
    "retirement_plan_payload",
]
