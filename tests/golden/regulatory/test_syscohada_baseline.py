"""Golden baseline: SYSCOHADA 2017 structure vs the upstream dataset (LOT-10)."""

from __future__ import annotations

from pathlib import Path

from pyaccountingkit.adapters.regulatory.filesystem import LocalFilesystemReferenceAdapter
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.domain.references.relations import (
    ConstraintKind,
    NegativeConstraint,
)
from pyaccountingkit.domain.references.standards import ReferenceNodeType, StandardType

STRUCTURED = (
    Path(__file__).resolve().parents[3] / "docs" / "referentiels" / "datasets" / "structured"
)

CONSTRAINTS = {
    StandardType.SYSCOHADA: (
        NegativeConstraint(
            node_id="account:ohada-syscohada:2017:101",
            kind=ConstraintKind.CREDIT_ONLY,
            reason="Capital social: solde créditeur permanent.",
            standard_id="syscohada",
        ),
        NegativeConstraint(
            node_id="account:ohada-syscohada:2017:401",
            kind=ConstraintKind.CREDIT_ONLY,
            reason="Fournisseurs: solde créditeur.",
            standard_id="syscohada",
        ),
        NegativeConstraint(
            node_id="account:ohada-syscohada:2017:411",
            kind=ConstraintKind.DEBIT_ONLY,
            reason="Clients: solde débiteur.",
            standard_id="syscohada",
        ),
    ),
}


def _provider() -> LocalFilesystemReferenceAdapter:
    return LocalFilesystemReferenceAdapter(
        STRUCTURED,
        clock=FrozenClock(),
        extra_constraints=CONSTRAINTS,
    )


def test_syscohada_2017_classes_one_to_nine_grounded() -> None:
    provider = _provider()
    hierarchy = provider.get_hierarchy(StandardType.SYSCOHADA)
    assert [node.ref_code for node in hierarchy.classes()] == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
    ]


def test_syscohada_2017_node_count_no_orphans() -> None:
    provider = _provider()
    hierarchy = provider.get_hierarchy(StandardType.SYSCOHADA)
    assert hierarchy.node_count == 1412
    assert hierarchy.standard_id == "ohada-syscohada"


def test_syscohada_2017_known_accounts_present() -> None:
    provider = _provider()
    assert provider.get_node(StandardType.SYSCOHADA, "101").label == "Capital social"
    suppliers = provider.get_node(StandardType.SYSCOHADA, "401")
    assert suppliers.label == "Fournisseurs, dettes en compte"
    assert provider.get_node(StandardType.SYSCOHADA, "411").label == "Clients"
    assert provider.get_node(StandardType.SYSCOHADA, "411").node_type is ReferenceNodeType.ACCOUNT


def test_syscohada_2017_snapshot_replayable() -> None:
    provider = _provider()
    snapshot = provider.get_snapshot(StandardType.SYSCOHADA, "2017.1")
    assert snapshot.verify()
    replayed = snapshot.replay()
    assert replayed.node_count == snapshot.nodes.__len__()
    again = provider.get_snapshot(StandardType.SYSCOHADA, "2017.1")
    assert again.checksum == snapshot.checksum


def test_syscohada_2017_negative_constraints_first_class() -> None:
    provider = _provider()
    register = provider.constraints(StandardType.SYSCOHADA)
    assert register.balance_kind("account:ohada-syscohada:2017:101") is ConstraintKind.CREDIT_ONLY
    assert register.balance_kind("account:ohada-syscohada:2017:411") is ConstraintKind.DEBIT_ONLY
