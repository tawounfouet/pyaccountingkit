"""Unit tests for the reference adapters (LOT-10)."""

from __future__ import annotations

import json
from pathlib import Path

from pyaccountingkit.adapters.regulatory.filesystem import LocalFilesystemReferenceAdapter
from pyaccountingkit.adapters.regulatory.in_memory import InMemoryReferenceAdapter
from pyaccountingkit.adapters.regulatory.package import PackageReferenceAdapter
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.domain.references.hierarchy import ReferenceHierarchy
from pyaccountingkit.domain.references.relations import (
    ConstraintKind,
    NegativeConstraint,
)
from pyaccountingkit.domain.references.standards import ReferenceNodeType, StandardType
from pyaccountingkit.ports.references import AccountingReferenceProviderProtocol

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "regulatory"
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


def _checked(adapter: AccountingReferenceProviderProtocol) -> AccountingReferenceProviderProtocol:
    return adapter


def test_filesystem_adapter_serves_port_contract() -> None:
    adapter = _checked(
        LocalFilesystemReferenceAdapter(
            FIXTURES,
            clock=FrozenClock(),
            resource_names=CANONICAL_PCG,
            extra_constraints=CONSTRAINTS,
        )
    )
    _assert_standard(adapter)


def test_package_adapter_serves_port_contract(tmp_path: Path) -> None:
    import sys

    pkg = tmp_path / "pkgdata"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "mini.json").write_text(
        (FIXTURES / "mini_canonical_structure.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    sys.path.insert(0, str(tmp_path))
    try:
        adapter = _checked(
            PackageReferenceAdapter(
                "pkgdata",
                clock=FrozenClock(),
                resource_names={StandardType.PCG_FRANCE: "mini.json"},
                extra_constraints=CONSTRAINTS,
            )
        )
        _assert_standard(adapter)
    finally:
        sys.path.remove(str(tmp_path))


def test_in_memory_adapter_serves_port_contract() -> None:
    hierarchy = _fixture_hierarchy()
    adapter = _checked(
        InMemoryReferenceAdapter(
            {StandardType.PCG_FRANCE: hierarchy},
            clock=FrozenClock(),
            extra_constraints=CONSTRAINTS,
        )
    )
    _assert_standard(adapter)


def test_missing_standard_capabilities_empty() -> None:
    hierarchy = _fixture_hierarchy()
    adapter = _checked(
        InMemoryReferenceAdapter({StandardType.PCG_FRANCE: hierarchy}, clock=FrozenClock())
    )
    from pyaccountingkit.domain.references.capabilities import ReferenceCapability

    assert not adapter.capabilities(StandardType.SYSCOHADA).supports(
        ReferenceCapability.NODE_LOOKUP
    )


def _fixture_hierarchy() -> ReferenceHierarchy:
    raw = json.loads((FIXTURES / "mini_canonical_structure.json").read_text(encoding="utf-8"))
    from pyaccountingkit.adapters.regulatory._base import parse_structure

    return parse_structure(raw)


def _assert_standard(adapter: AccountingReferenceProviderProtocol) -> None:
    from pyaccountingkit.domain.references.capabilities import ReferenceCapability

    hierarchy = adapter.get_hierarchy(StandardType.PCG_FRANCE)
    assert hierarchy.node_count == 11
    assert len(adapter.list_nodes_by_standard(StandardType.PCG_FRANCE)) == 11

    by_id = adapter.get_node(StandardType.PCG_FRANCE, "account:fr-pcg:2026:411")
    assert by_id is not None
    assert by_id.node_type is ReferenceNodeType.ACCOUNT
    assert by_id.label == "Clients"

    by_code = adapter.get_node(StandardType.PCG_FRANCE, "411")
    assert by_code is not None
    assert by_code.node_id == "account:fr-pcg:2026:411"

    snapshot = adapter.get_snapshot(StandardType.PCG_FRANCE, "2026.1")
    assert snapshot.verify()
    assert snapshot.replay().all_nodes() == hierarchy.all_nodes()

    capabilities = adapter.capabilities(StandardType.PCG_FRANCE)
    assert capabilities.supports(ReferenceCapability.SNAPSHOTS)

    register = adapter.constraints(StandardType.PCG_FRANCE)
    assert register.balance_kind("account:fr-pcg:2026:401") is ConstraintKind.CREDIT_ONLY
    concepts = adapter.concept_registry()
    assert concepts.get("CASH") is not None
