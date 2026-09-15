"""Unit tests for sealed, replayable reference snapshots (LOT-10)."""

from __future__ import annotations

from datetime import UTC, datetime

from pyaccountingkit.domain.references.hierarchy import ReferenceHierarchy, ReferenceNode
from pyaccountingkit.domain.references.snapshots import ReferenceSnapshot
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
