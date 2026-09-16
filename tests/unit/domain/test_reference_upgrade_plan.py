"""LOT-17 qualification for regulatory reference upgrade planning."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.reporting.reference_reporting_model import (
    ReferenceReportingModel,
    ReferenceReportingNode,
    ReferenceReportingNodeType,
)
from pyaccountingkit.domain.reporting.reference_upgrade import (
    ReferenceNodeChangeType,
    ReferenceUpgradePlan,
    ReferenceUpgradeStatus,
)
from pyaccountingkit.domain.reporting.regulatory_mapping import (
    RegulatoryMappingProvenance,
    RegulatoryMappingSet,
    RegulatoryMappingSetStatus,
    RegulatoryMappingStatus,
    RegulatoryStatementMapping,
)

ENTITY = EntityId("entity-a")


def _node(
    *,
    required: bool = False,
    human_validation_required: bool = False,
) -> ReferenceReportingNode:
    return ReferenceReportingNode(
        node_id="assets",
        code="ASSETS",
        label="Assets",
        node_type=ReferenceReportingNodeType.TOTAL,
        order=1,
        required=required,
        human_validation_required=human_validation_required,
    )


def _model(
    snapshot: str,
    node: ReferenceReportingNode,
    *extra: ReferenceReportingNode,
) -> ReferenceReportingModel:
    return ReferenceReportingModel(
        model_id="pcg-bs-model",
        model_code="BALANCE_SHEET",
        framework="PCG",
        edition="2026",
        reference_snapshot_id=snapshot,
        reference_snapshot_checksum=("a" if snapshot == "old" else "b") * 64,
        nodes=(node, *extra),
    )


def _mapping_set() -> RegulatoryMappingSet:
    return RegulatoryMappingSet(
        mapping_set_id="reg-map-1",
        accounting_entity_id=ENTITY,
        profile_id="pcg-profile",
        reference_model_id="pcg-bs-model",
        version="1",
        status=RegulatoryMappingSetStatus.ACTIVE,
        mappings=(
            RegulatoryStatementMapping(
                mapping_id="m1",
                statement_line_code="FS_ASSETS",
                reference_node_id="assets",
                allocation=Decimal("1"),
                status=RegulatoryMappingStatus.VALIDATED,
                provenance=RegulatoryMappingProvenance.MANUAL,
                effective_from=date(2026, 1, 1),
            ),
        ),
        effective_from=date(2026, 1, 1),
    )


def test_changed_mapped_node_requires_human_review_and_preserves_impact() -> None:
    plan = ReferenceUpgradePlan.build(
        plan_id="upgrade-1",
        profile_id="pcg-profile",
        from_model=_model("old", _node(required=False)),
        to_model=_model("new", _node(required=True)),
        mapping_set=_mapping_set(),
    )

    assert plan.requires_human_review is True
    assert plan.status is ReferenceUpgradeStatus.REVIEW_REQUIRED
    assert plan.impacted_mapping_ids == ("m1",)
    assert plan.node_changes[0].change_type is ReferenceNodeChangeType.CHANGED
    assert "required flag changed" in plan.node_changes[0].reasons


def test_optional_additive_node_can_be_ready_without_mapping_review() -> None:
    optional = ReferenceReportingNode(
        node_id="memo",
        code="MEMO",
        label="Memo",
        node_type=ReferenceReportingNodeType.DISCLOSURE,
        order=2,
        required=False,
    )
    plan = ReferenceUpgradePlan.build(
        plan_id="upgrade-2",
        profile_id="pcg-profile",
        from_model=_model("old", _node()),
        to_model=_model("new", _node(), optional),
        mapping_set=_mapping_set(),
    )

    assert plan.requires_human_review is False
    assert plan.status is ReferenceUpgradeStatus.READY
    assert plan.impacted_mapping_ids == ()
    assert plan.node_changes[0].change_type is ReferenceNodeChangeType.ADDED


def test_upgrade_checksum_is_deterministic() -> None:
    kwargs = {
        "profile_id": "pcg-profile",
        "from_model": _model("old", _node()),
        "to_model": _model("new", _node(required=True)),
        "mapping_set": _mapping_set(),
    }

    first = ReferenceUpgradePlan.build(plan_id="upgrade-a", **kwargs)
    second = ReferenceUpgradePlan.build(plan_id="upgrade-b", **kwargs)

    assert first.checksum == second.checksum
