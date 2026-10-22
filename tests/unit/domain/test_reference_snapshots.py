"""Unit tests for sealed, replayable reference snapshots (LOT-10)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest

from pyaccountingkit.domain.references.effective_plan import (
    EffectiveAccountOrigin,
    EffectiveAccountPlan,
    EffectiveReferenceAccount,
)
from pyaccountingkit.domain.references.hierarchy import ReferenceHierarchy, ReferenceNode
from pyaccountingkit.domain.references.snapshots import EffectivePlanSnapshot, ReferenceSnapshot
from pyaccountingkit.domain.references.standards import ReferenceNodeType

NOW = datetime(2026, 1, 1, tzinfo=UTC)
LATER = datetime(2026, 6, 30, tzinfo=UTC)


def _node(node_id: str, ref_code: str) -> ReferenceNode:
    return ReferenceNode(
        node_id=node_id,
        node_type=ReferenceNodeType.ACCOUNT,
        standard_id="fr-pcg",
        edition="2026",
        ref_code=ref_code,
        label=node_id,
        account_class=4,
    )


def _hierarchy() -> ReferenceHierarchy:
    return ReferenceHierarchy(
        "fr-pcg",
        "2026",
        (
            _node("a401", "401"),
            _node("a411", "411"),
        ),
    )


def test_snapshot_seal_and_verify() -> None:
    snapshot = ReferenceSnapshot.seal(_hierarchy(), "2026.1", NOW)
    assert snapshot.verify() is True
    assert snapshot.nodes == _hierarchy().all_nodes()


def test_replay_rebuilds_equal_hierarchy() -> None:
    original = _hierarchy()
    snapshot = ReferenceSnapshot.seal(original, "2026.1", NOW)
    replayed = snapshot.replay()
    assert replayed.all_nodes() == original.all_nodes()
    sealed_again = ReferenceSnapshot.seal(replayed, "2026.1", LATER)
    assert sealed_again.checksum == snapshot.checksum


def test_checksum_is_time_independent() -> None:
    first = ReferenceSnapshot.seal(_hierarchy(), "2026.1", NOW)
    second = ReferenceSnapshot.seal(_hierarchy(), "2026.1", LATER)
    assert first.checksum == second.checksum


def test_checksum_changes_with_nodes_or_version() -> None:
    baseline = ReferenceSnapshot.seal(_hierarchy(), "2026.1", NOW).checksum
    tampered = ReferenceHierarchy(
        "fr-pcg",
        "2026",
        (
            _node("a401", "401"),
            _node("a411", "411"),
            _node("a999", "999"),
        ),
    )
    assert ReferenceSnapshot.seal(tampered, "2026.1", NOW).checksum != baseline
    assert ReferenceSnapshot.seal(_hierarchy(), "2026.2", NOW).checksum != baseline


def test_reference_snapshot_is_detached_from_mutable_node_attributes() -> None:
    attributes: dict[str, object] = {
        "scope": {"codes": ["A", "B"]},
    }
    node = ReferenceNode(
        node_id="a401",
        node_type=ReferenceNodeType.ACCOUNT,
        standard_id="fr-pcg",
        edition="2026",
        ref_code="401",
        label="Suppliers",
        account_class=4,
        attributes=attributes,
    )
    snapshot = ReferenceSnapshot.seal(
        ReferenceHierarchy("fr-pcg", "2026", (node,)),
        "2026.1",
        NOW,
    )

    cast(dict[str, object], attributes["scope"])["codes"] = ["tampered"]

    sealed_scope = cast(dict[str, object], snapshot.nodes[0].attributes["scope"])
    assert sealed_scope["codes"] == ["A", "B"]
    assert snapshot.verify() is True

    with pytest.raises(TypeError):
        cast(dict[str, object], snapshot.nodes[0].attributes)["scope"] = {}
    with pytest.raises(TypeError):
        cast(list[object], sealed_scope["codes"]).append("forbidden")
    assert snapshot.verify() is True


def test_reference_snapshot_replay_keeps_attributes_immutable() -> None:
    node = ReferenceNode(
        node_id="a401",
        node_type=ReferenceNodeType.ACCOUNT,
        standard_id="fr-pcg",
        edition="2026",
        ref_code="401",
        label="Suppliers",
        account_class=4,
        attributes={"scope": {"codes": ["A"]}},
    )
    snapshot = ReferenceSnapshot.seal(
        ReferenceHierarchy("fr-pcg", "2026", (node,)),
        "2026.1",
        NOW,
    )
    replayed = snapshot.replay()
    replayed_node = replayed.node("a401")
    replayed_scope = cast(dict[str, object], replayed_node.attributes["scope"])

    with pytest.raises(TypeError):
        cast(list[object], replayed_scope["codes"]).append("forbidden")
    assert snapshot.verify() is True


def test_effective_plan_snapshot_detaches_and_freezes_statistics() -> None:
    statistics = {
        "inherited": 1,
        "extension_overrides": 0,
        "extension_additions": 0,
        "effective_accounts_or_groups": 1,
    }
    plan = EffectiveAccountPlan(
        standard_id="fr-nonprofit",
        edition="2026",
        base_standard="fr-pcg:2026",
        accounts=(
            EffectiveReferenceAccount(
                account_id="account:fr-nonprofit:2026:101",
                ref_code="101",
                label="Capital",
                origin=EffectiveAccountOrigin.INHERITED_FROM_BASE_STANDARD,
                provenance_type="base",
                base_account_id="account:fr-pcg:2026:101",
            ),
        ),
        statistics=statistics,
    )
    snapshot = EffectivePlanSnapshot.seal(plan, "2026.1", NOW)

    statistics["inherited"] = 999

    assert snapshot.plan.statistics["inherited"] == 1
    assert snapshot.verify() is True
    with pytest.raises(TypeError):
        cast(dict[str, int], snapshot.plan.statistics)["inherited"] = 2
    assert snapshot.replay().statistics["inherited"] == 1
    assert snapshot.verify() is True
