"""Contract tests — every reference adapter must satisfy the same behaviour."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from pyaccountingkit.adapters.regulatory.filesystem import LocalFilesystemReferenceAdapter
from pyaccountingkit.adapters.regulatory.in_memory import InMemoryReferenceAdapter
from pyaccountingkit.adapters.regulatory.package import PackageReferenceAdapter
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.domain.references.capabilities import ReferenceCapability
from pyaccountingkit.domain.references.relations import ConstraintKind, NegativeConstraint
from pyaccountingkit.domain.references.standards import ReferenceNodeType, StandardType
from pyaccountingkit.ports.references import AccountingReferenceProviderProtocol

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "regulatory"
CANONICAL_PCG = {StandardType.PCG_FRANCE: "mini_canonical_structure.json"}

CONSTRAINTS = {
    StandardType.PCG_FRANCE: (
        NegativeConstraint(
            node_id="account:fr-pcg:2026:401",
            kind=ConstraintKind.CREDIT_ONLY,
            reason="Fournisseurs: solde créditeur.",
            standard_id="fr-pcg",
        ),
    ),
}


def _filesystem() -> AccountingReferenceProviderProtocol:
    return LocalFilesystemReferenceAdapter(
        FIXTURES,
        clock=FrozenClock(),
        resource_names=CANONICAL_PCG,
        extra_constraints=CONSTRAINTS,
    )


def _in_memory() -> AccountingReferenceProviderProtocol:
    raw = json.loads((FIXTURES / "mini_canonical_structure.json").read_text(encoding="utf-8"))
    from pyaccountingkit.adapters.regulatory._base import parse_structure

    hierarchy = parse_structure(raw)
    return InMemoryReferenceAdapter(
        {StandardType.PCG_FRANCE: hierarchy},
        clock=FrozenClock(),
        extra_constraints=CONSTRAINTS,
    )


def _package(tmp_path: Path) -> AccountingReferenceProviderProtocol:
    pkg = tmp_path / "pkgdata"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "mini.json").write_text(
        (FIXTURES / "mini_canonical_structure.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    sys.path.insert(0, str(tmp_path))
    return PackageReferenceAdapter(
        "pkgdata",
        clock=FrozenClock(),
        resource_names={StandardType.PCG_FRANCE: "mini.json"},
        extra_constraints=CONSTRAINTS,
    )


@pytest.mark.parametrize(
    "builder",
    [_filesystem, _in_memory],
    ids=["filesystem", "in_memory"],
)
def test_reference_provider_contract(
    builder: Callable[[], AccountingReferenceProviderProtocol],
) -> None:
    _assert_contract(builder())


def test_reference_provider_contract_package(tmp_path: Path) -> None:
    _assert_contract(_package(tmp_path))


def _assert_contract(adapter: AccountingReferenceProviderProtocol) -> None:
    hierarchy = adapter.get_hierarchy(StandardType.PCG_FRANCE)
    assert hierarchy.standard_id == "fr-pcg"
    assert hierarchy.node_count == 11

    nodes = adapter.list_nodes_by_standard(StandardType.PCG_FRANCE)
    assert len(nodes) == 11

    assert adapter.get_node(StandardType.PCG_FRANCE, "account:fr-pcg:2026:101").label == "Capital"
    assert adapter.get_node(StandardType.PCG_FRANCE, "401").ref_code == "401"
    assert adapter.get_node(StandardType.PCG_FRANCE, "missing") is None

    snapshot = adapter.get_snapshot(StandardType.PCG_FRANCE, "2026.1")
    assert snapshot.verify()
    assert snapshot.checksum == adapter.get_snapshot(StandardType.PCG_FRANCE, "2026.1").checksum

    capabilities = adapter.capabilities(StandardType.PCG_FRANCE)
    assert capabilities.supports(ReferenceCapability.HIERARCHY)
    assert capabilities.supports(ReferenceCapability.NEGATIVE_CONSTRAINTS)

    register = adapter.constraints(StandardType.PCG_FRANCE)
    assert register.balance_kind("account:fr-pcg:2026:401") is ConstraintKind.CREDIT_ONLY

    assert adapter.get_node(StandardType.PCG_FRANCE, "account:fr-pcg:2026:411").node_type is (
        ReferenceNodeType.ACCOUNT
    )
