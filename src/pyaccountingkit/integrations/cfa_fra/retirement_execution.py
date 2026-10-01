"""Fail-closed verification of externally executed CFA FRA legacy retirement."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from pyaccountingkit.integrations.cfa_fra.retirement_plan import (
    LegacyRetirementAction,
    LegacyRetirementPlan,
    build_legacy_retirement_plan,
)

_SHA256_PREFIXED = re.compile(r"^sha256:[0-9a-f]{64}$")


class LegacyRetirementExecutionError(RuntimeError):
    """Raised when external retirement execution evidence cannot be trusted."""


class LegacyRetirementObservedState(StrEnum):
    """Observed post-cutover state for one planned legacy component."""

    RETIRED = "RETIRED"
    REWIRED = "REWIRED"
    PRESERVED = "PRESERVED"
    PRESENT = "PRESENT"


_EXPECTED_STATE: dict[LegacyRetirementAction, LegacyRetirementObservedState] = {
    LegacyRetirementAction.RETIRE_DUPLICATE_ENGINE: LegacyRetirementObservedState.RETIRED,
    LegacyRetirementAction.VERIFY_CONSUMER_REWIRED: LegacyRetirementObservedState.REWIRED,
    LegacyRetirementAction.PRESERVE_OR_MIGRATE_PERSISTENCE: (
        LegacyRetirementObservedState.PRESERVED
    ),
    LegacyRetirementAction.KEEP_CONSUMER_CONCERN: LegacyRetirementObservedState.PRESENT,
    LegacyRetirementAction.PRESERVE_FROZEN_ORACLE: LegacyRetirementObservedState.PRESERVED,
}


@dataclass(frozen=True, slots=True)
class LegacyRetirementExecutionObservation:
    """One externally produced post-retirement observation."""

    path: str
    state: LegacyRetirementObservedState
    source: str
    evidence_checksum: str

    def __post_init__(self) -> None:
        if not self.path.strip():
            raise ValueError("retirement execution observation path must not be empty")
        if not self.source.strip():
            raise ValueError("retirement execution observation source must not be empty")
        if _SHA256_PREFIXED.fullmatch(self.evidence_checksum) is None:
            raise ValueError(
                "retirement execution observation checksum must be sha256:<64 lowercase hex>"
            )


@dataclass(frozen=True, slots=True)
class LegacyRetirementExecutionReceipt:
    """Verified receipt proving that an external live-consumer retirement matches its plan."""

    plan_sha256: str
    inventory_sha256: str
    readiness_sha256: str
    consumer_revision: str
    observations: tuple[LegacyRetirementExecutionObservation, ...]
    receipt_sha256: str


def _canonical_bytes(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _parse_observations(
    payload: Mapping[str, object],
) -> tuple[LegacyRetirementExecutionObservation, ...]:
    if payload.get("schema_version") != "1":
        raise LegacyRetirementExecutionError(
            "retirement execution evidence must use schema_version='1'"
        )

    raw_observations = payload.get("observations")
    if not isinstance(raw_observations, list) or not raw_observations:
        raise LegacyRetirementExecutionError(
            "retirement execution evidence must contain observations"
        )

    observations: list[LegacyRetirementExecutionObservation] = []
    for index, raw in enumerate(raw_observations):
        if not isinstance(raw, dict):
            raise LegacyRetirementExecutionError(
                f"retirement execution observation {index} must be a JSON object"
            )
        item = cast(Mapping[str, object], raw)
        path = item.get("path")
        raw_state = item.get("state")
        source = item.get("source")
        checksum = item.get("evidence_checksum")
        if not isinstance(path, str):
            raise LegacyRetirementExecutionError(f"observation {index} path must be a string")
        if not isinstance(raw_state, str):
            raise LegacyRetirementExecutionError(f"{path}: observed state must be a string")
        if not isinstance(source, str):
            raise LegacyRetirementExecutionError(f"{path}: source must be a string")
        if not isinstance(checksum, str):
            raise LegacyRetirementExecutionError(f"{path}: evidence checksum must be a string")
        try:
            state = LegacyRetirementObservedState(raw_state)
            observations.append(
                LegacyRetirementExecutionObservation(
                    path=path,
                    state=state,
                    source=source,
                    evidence_checksum=checksum,
                )
            )
        except ValueError as exc:
            raise LegacyRetirementExecutionError(
                f"{path}: invalid retirement execution observation"
            ) from exc

    return tuple(observations)


def verify_legacy_retirement_execution(
    plan: LegacyRetirementPlan,
    inventory: Mapping[str, object],
    readiness: Mapping[str, object],
    evidence: Mapping[str, object],
) -> LegacyRetirementExecutionReceipt:
    """Verify external retirement work against the exact still-current MIG-13 plan."""
    current_plan = build_legacy_retirement_plan(inventory, readiness)
    if current_plan != plan:
        raise LegacyRetirementExecutionError(
            "reviewed retirement plan no longer matches current inventory/readiness"
        )

    if evidence.get("plan_sha256") != plan.plan_sha256:
        raise LegacyRetirementExecutionError(
            "retirement execution evidence does not target the reviewed plan"
        )

    consumer_revision = evidence.get("consumer_revision")
    if not isinstance(consumer_revision, str) or not consumer_revision.strip():
        raise LegacyRetirementExecutionError(
            "retirement execution evidence requires a consumer revision"
        )
    if consumer_revision == plan.oracle_tree_sha:
        raise LegacyRetirementExecutionError(
            "retirement execution evidence may not target the frozen oracle revision"
        )

    observations = _parse_observations(evidence)
    by_path: dict[str, LegacyRetirementExecutionObservation] = {}
    for observation in observations:
        if observation.path in by_path:
            raise LegacyRetirementExecutionError(
                f"duplicate retirement execution observation: {observation.path}"
            )
        by_path[observation.path] = observation

    planned_paths = {item.path for item in plan.items}
    observed_paths = set(by_path)
    missing = sorted(planned_paths - observed_paths)
    unexpected = sorted(observed_paths - planned_paths)
    if missing or unexpected:
        detail: list[str] = []
        if missing:
            detail.append("missing=" + ",".join(missing))
        if unexpected:
            detail.append("unexpected=" + ",".join(unexpected))
        raise LegacyRetirementExecutionError(
            "retirement execution observations must cover the exact plan: " + "; ".join(detail)
        )

    ordered: list[LegacyRetirementExecutionObservation] = []
    for item in plan.items:
        observation = by_path[item.path]
        expected = _EXPECTED_STATE[item.action]
        if observation.state is not expected:
            raise LegacyRetirementExecutionError(
                f"{item.path}: expected post-retirement state {expected.value}, "
                f"got {observation.state.value}"
            )
        ordered.append(observation)

    receipt_body: dict[str, object] = {
        "plan_sha256": plan.plan_sha256,
        "inventory_sha256": plan.inventory_sha256,
        "readiness_sha256": plan.readiness_sha256,
        "consumer_revision": consumer_revision,
        "observations": [
            {
                "path": observation.path,
                "state": observation.state.value,
                "source": observation.source,
                "evidence_checksum": observation.evidence_checksum,
            }
            for observation in ordered
        ],
    }
    return LegacyRetirementExecutionReceipt(
        plan_sha256=plan.plan_sha256,
        inventory_sha256=plan.inventory_sha256,
        readiness_sha256=plan.readiness_sha256,
        consumer_revision=consumer_revision,
        observations=tuple(ordered),
        receipt_sha256=hashlib.sha256(_canonical_bytes(receipt_body)).hexdigest(),
    )


def retirement_execution_receipt_payload(
    receipt: LegacyRetirementExecutionReceipt,
) -> dict[str, object]:
    """Serialize a verified retirement receipt."""
    return {
        "schema_version": "1",
        "verified": True,
        "plan_sha256": receipt.plan_sha256,
        "inventory_sha256": receipt.inventory_sha256,
        "readiness_sha256": receipt.readiness_sha256,
        "consumer_revision": receipt.consumer_revision,
        "receipt_sha256": receipt.receipt_sha256,
        "observations": [
            {
                "path": observation.path,
                "state": observation.state.value,
                "source": observation.source,
                "evidence_checksum": observation.evidence_checksum,
            }
            for observation in receipt.observations
        ],
    }


__all__ = [
    "LegacyRetirementExecutionError",
    "LegacyRetirementExecutionObservation",
    "LegacyRetirementExecutionReceipt",
    "LegacyRetirementObservedState",
    "retirement_execution_receipt_payload",
    "verify_legacy_retirement_execution",
]
