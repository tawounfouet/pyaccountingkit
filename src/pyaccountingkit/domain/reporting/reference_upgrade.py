"""Reference-reporting model upgrade plans preserving historical execution coordinates."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

from pyaccountingkit.domain.reporting.errors import RegulatoryReferenceMismatchError
from pyaccountingkit.domain.reporting.reference_reporting_model import ReferenceReportingModel
from pyaccountingkit.domain.reporting.regulatory_mapping import RegulatoryMappingSet


class ReferenceUpgradeStatus(StrEnum):
    READY = "READY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class ReferenceNodeChangeType(StrEnum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    CHANGED = "CHANGED"


@dataclass(frozen=True, slots=True)
class ReferenceNodeChange:
    change_type: ReferenceNodeChangeType
    node_id: str
    code: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReferenceUpgradePlan:
    """Deterministic impact analysis between two sealed reporting models."""

    plan_id: str
    profile_id: str
    from_snapshot_id: str
    from_model_checksum: str
    to_snapshot_id: str
    to_model_checksum: str
    node_changes: tuple[ReferenceNodeChange, ...]
    impacted_mapping_ids: tuple[str, ...]
    requires_human_review: bool
    status: ReferenceUpgradeStatus
    checksum: str

    @classmethod
    def build(
        cls,
        *,
        plan_id: str,
        profile_id: str,
        from_model: ReferenceReportingModel,
        to_model: ReferenceReportingModel,
        mapping_set: RegulatoryMappingSet,
    ) -> ReferenceUpgradePlan:
        if not plan_id.strip() or not profile_id.strip():
            raise ValueError("reference upgrade plan and profile ids must not be empty")
        if from_model.framework != to_model.framework:
            raise RegulatoryReferenceMismatchError(
                "reference upgrade cannot cross regulatory frameworks"
            )
        if mapping_set.profile_id != profile_id:
            raise RegulatoryReferenceMismatchError(
                "reference upgrade mapping set targets a different profile"
            )
        if mapping_set.reference_model_id != from_model.model_id:
            raise RegulatoryReferenceMismatchError(
                "reference upgrade mapping set does not target the source model"
            )

        before = {node.node_id: node for node in from_model.nodes}
        after = {node.node_id: node for node in to_model.nodes}
        changes: list[ReferenceNodeChange] = []

        for node_id in sorted(set(after) - set(before)):
            node = after[node_id]
            added_reasons = ["node added"]
            if node.required:
                added_reasons.append("new node is required")
            if node.human_validation_required:
                added_reasons.append("new node requires human validation")
            changes.append(
                ReferenceNodeChange(
                    change_type=ReferenceNodeChangeType.ADDED,
                    node_id=node.node_id,
                    code=node.code,
                    reasons=tuple(added_reasons),
                )
            )

        for node_id in sorted(set(before) - set(after)):
            node = before[node_id]
            changes.append(
                ReferenceNodeChange(
                    change_type=ReferenceNodeChangeType.REMOVED,
                    node_id=node.node_id,
                    code=node.code,
                    reasons=("node removed",),
                )
            )

        for node_id in sorted(set(before) & set(after)):
            old = before[node_id]
            new = after[node_id]
            reasons: list[str] = []
            if old.code != new.code:
                reasons.append("code changed")
            if old.parent_node_id != new.parent_node_id:
                reasons.append("hierarchy changed")
            if old.required != new.required:
                reasons.append("required flag changed")
            if old.value_type != new.value_type:
                reasons.append("value type changed")
            if old.human_validation_required != new.human_validation_required:
                reasons.append("human-validation flag changed")
            if old.account_hints_executable != new.account_hints_executable:
                reasons.append("account-hint executability changed")
            if old.account_hints != new.account_hints:
                reasons.append("account hints changed")
            if reasons:
                changes.append(
                    ReferenceNodeChange(
                        change_type=ReferenceNodeChangeType.CHANGED,
                        node_id=new.node_id,
                        code=new.code,
                        reasons=tuple(reasons),
                    )
                )

        risky_node_ids = {
            change.node_id
            for change in changes
            if change.change_type is not ReferenceNodeChangeType.ADDED
            or "new node is required" in change.reasons
            or "new node requires human validation" in change.reasons
        }
        impacted_mapping_ids = tuple(
            sorted(
                mapping.mapping_id
                for mapping in mapping_set.mappings
                if mapping.reference_node_id in risky_node_ids
            )
        )
        requires_human_review = bool(risky_node_ids or impacted_mapping_ids)
        status = (
            ReferenceUpgradeStatus.REVIEW_REQUIRED
            if requires_human_review
            else ReferenceUpgradeStatus.READY
        )
        checksum = cls._checksum(
            profile_id=profile_id,
            from_model=from_model,
            to_model=to_model,
            changes=tuple(changes),
            impacted_mapping_ids=impacted_mapping_ids,
            requires_human_review=requires_human_review,
            status=status,
        )
        return cls(
            plan_id=plan_id,
            profile_id=profile_id,
            from_snapshot_id=from_model.reference_snapshot_id,
            from_model_checksum=from_model.checksum,
            to_snapshot_id=to_model.reference_snapshot_id,
            to_model_checksum=to_model.checksum,
            node_changes=tuple(changes),
            impacted_mapping_ids=impacted_mapping_ids,
            requires_human_review=requires_human_review,
            status=status,
            checksum=checksum,
        )

    @staticmethod
    def _checksum(
        *,
        profile_id: str,
        from_model: ReferenceReportingModel,
        to_model: ReferenceReportingModel,
        changes: tuple[ReferenceNodeChange, ...],
        impacted_mapping_ids: tuple[str, ...],
        requires_human_review: bool,
        status: ReferenceUpgradeStatus,
    ) -> str:
        payload = {
            "profile_id": profile_id,
            "from_snapshot_id": from_model.reference_snapshot_id,
            "from_model_checksum": from_model.checksum,
            "to_snapshot_id": to_model.reference_snapshot_id,
            "to_model_checksum": to_model.checksum,
            "node_changes": [
                {
                    "change_type": change.change_type.value,
                    "node_id": change.node_id,
                    "code": change.code,
                    "reasons": list(change.reasons),
                }
                for change in changes
            ],
            "impacted_mapping_ids": list(impacted_mapping_ids),
            "requires_human_review": requires_human_review,
            "status": status.value,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "ReferenceNodeChange",
    "ReferenceNodeChangeType",
    "ReferenceUpgradePlan",
    "ReferenceUpgradeStatus",
]
