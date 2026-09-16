"""LOT-17 qualification for canonical reference reporting models."""

from __future__ import annotations

import pytest

from pyaccountingkit.domain.reporting.errors import RegulatoryReportingError
from pyaccountingkit.domain.reporting.reference_reporting_model import (
    ReferenceReportingModel,
    ReferenceReportingNode,
    ReferenceReportingNodeType,
)


def _node(
    node_id: str,
    code: str,
    order: int,
    *,
    parent_node_id: str | None = None,
    required: bool = False,
    human_validation_required: bool = False,
    account_hints_executable: bool = False,
    account_hints: tuple[str, ...] = (),
) -> ReferenceReportingNode:
    return ReferenceReportingNode(
        node_id=node_id,
        code=code,
        label=f"Node {code}",
        node_type=ReferenceReportingNodeType.DETAIL,
        order=order,
        parent_node_id=parent_node_id,
        required=required,
        human_validation_required=human_validation_required,
        account_hints_executable=account_hints_executable,
        account_hints=account_hints,
        provenance="official-dataset",
    )


def _model(nodes: tuple[ReferenceReportingNode, ...]) -> ReferenceReportingModel:
    return ReferenceReportingModel(
        model_id="pcg-balance-sheet",
        model_code="PCG_BS",
        framework="PCG",
        edition="2026",
        reference_snapshot_id="ref-pcg-2026",
        reference_snapshot_checksum="a" * 64,
        nodes=nodes,
    )


def test_model_orders_nodes_deterministically_and_resolves_by_id_or_code() -> None:
    child = _node("child", "A1", 20, parent_node_id="root")
    root = _node("root", "A", 10)
    model = _model((child, root))

    assert [node.code for node in model.ordered_nodes] == ["A", "A1"]
    assert model.node_by_id("child") is child
    assert model.node_by_code("A") is root


def test_model_rejects_duplicate_ids_and_codes() -> None:
    with pytest.raises(RegulatoryReportingError, match="ids must be unique"):
        _model((_node("same", "A", 1), _node("same", "B", 2)))

    with pytest.raises(RegulatoryReportingError, match="codes must be unique"):
        _model((_node("a", "SAME", 1), _node("b", "SAME", 2)))


def test_model_rejects_unknown_parent_and_hierarchy_cycle() -> None:
    with pytest.raises(RegulatoryReportingError, match="unknown parent"):
        _model((_node("a", "A", 1, parent_node_id="missing"),))

    with pytest.raises(RegulatoryReportingError, match="hierarchy cycle"):
        _model(
            (
                _node("a", "A", 1, parent_node_id="b"),
                _node("b", "B", 2, parent_node_id="a"),
            )
        )


def test_human_validation_required_hint_cannot_be_executable() -> None:
    with pytest.raises(RegulatoryReportingError, match="cannot be executable"):
        _node(
            "a",
            "A",
            1,
            human_validation_required=True,
            account_hints_executable=True,
            account_hints=("101000",),
        )


def test_non_executable_candidate_hints_remain_reference_metadata() -> None:
    node = _node(
        "a",
        "A",
        1,
        human_validation_required=True,
        account_hints_executable=False,
        account_hints=("101000", "102000"),
    )

    assert node.account_hints == ("101000", "102000")
    assert node.account_hints_executable is False
    assert node.human_validation_required is True


def test_model_checksum_is_independent_from_input_node_order() -> None:
    root = _node("root", "A", 10)
    child = _node("child", "A1", 20, parent_node_id="root")

    assert _model((root, child)).checksum == _model((child, root)).checksum
