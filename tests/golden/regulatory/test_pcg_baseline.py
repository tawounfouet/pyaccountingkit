"""Golden baseline: PCG France 2026 structure vs the upstream dataset (LOT-10)."""

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
    StandardType.PCG_FRANCE: (
        NegativeConstraint(
            node_id="account:fr-pcg:2026:101",
            kind=ConstraintKind.CREDIT_ONLY,
            reason="Capital: solde créditeur permanent.",
            standard_id="fr-pcg",
        ),
        NegativeConstraint(
            node_id="account:fr-pcg:2026:401",
            kind=ConstraintKind.CREDIT_ONLY,
            reason="Fournisseurs: solde créditeur.",
            standard_id="fr-pcg",
        ),
        NegativeConstraint(
            node_id="account:fr-pcg:2026:411",
            kind=ConstraintKind.DEBIT_ONLY,
            reason="Clients: solde débiteur.",
            standard_id="fr-pcg",
        ),
        NegativeConstraint(
            node_id="account:fr-pcg:2026:106",
            kind=ConstraintKind.CREDIT_ONLY,
            reason="Réserves: solde créditeur.",
            standard_id="fr-pcg",
        ),
    ),
}


def _provider() -> LocalFilesystemReferenceAdapter:
    return LocalFilesystemReferenceAdapter(
        STRUCTURED,
        clock=FrozenClock(),
        extra_constraints=CONSTRAINTS,
    )


def test_pcg_2026_classes_one_to_seven_grounded() -> None:
    provider = _provider()
    hierarchy = provider.get_hierarchy(StandardType.PCG_FRANCE)
    classes = hierarchy.classes()
    assert [node.ref_code for node in classes] == ["1", "2", "3", "4", "5", "6", "7"]


def test_pcg_2026_no_orphans_and_node_count() -> None:
    provider = _provider()
    hierarchy = provider.get_hierarchy(StandardType.PCG_FRANCE)
    assert hierarchy.node_count == 837


def test_pcg_2026_known_accounts_present() -> None:
    provider = _provider()
    assert provider.get_node(StandardType.PCG_FRANCE, "411").label == "Clients"
    assert provider.get_node(StandardType.PCG_FRANCE, "401").label == "Fournisseurs"
    assert provider.get_node(StandardType.PCG_FRANCE, "101").label == "Capital"
    assert provider.get_node(StandardType.PCG_FRANCE, "512").label == "Banques"
    capital = provider.get_node(StandardType.PCG_FRANCE, "101")
    assert capital.node_type is ReferenceNodeType.ACCOUNT
    waiting = provider.get_node(StandardType.PCG_FRANCE, "471à473")
    assert waiting.node_type is ReferenceNodeType.ACCOUNT_RANGE
    assert waiting.parent_node_id == "account:fr-pcg:2026:47"
    bundle = provider.get_node(StandardType.PCG_FRANCE, "61/62")
    assert bundle.node_type is ReferenceNodeType.GROUP_BUNDLE


def test_pcg_2026_snapshot_replayable_stable() -> None:
    provider = _provider()
    first = provider.get_snapshot(StandardType.PCG_FRANCE, "2026.1")
    second = provider.get_snapshot(StandardType.PCG_FRANCE, "2026.1")
    assert first.checksum == second.checksum
    assert first.verify()
    replayed = first.replay()
    assert replayed.node_count == first.nodes.__len__()


def test_pcg_2026_negative_constraints_first_class() -> None:
    provider = _provider()
    register = provider.constraints(StandardType.PCG_FRANCE)
    assert register.balance_kind("account:fr-pcg:2026:101") is ConstraintKind.CREDIT_ONLY
    assert register.balance_kind("account:fr-pcg:2026:401") is ConstraintKind.CREDIT_ONLY
    assert register.balance_kind("account:fr-pcg:2026:411") is ConstraintKind.DEBIT_ONLY


def test_pcg_512_maps_to_multiple_company_code_formats() -> None:
    """DoD LOT-11: PCG 512 maps to multiple company code formats (1:N binding)."""
    from pyaccountingkit.core.identifiers import EntityId
    from pyaccountingkit.domain.charts.generation import (
        CompanyChartGenerationRequest,
        CompanyChartGenerator,
        GenerationMode,
        ReferenceNodeInclusionPolicy,
    )
    from pyaccountingkit.domain.charts.numbering import NumericFixedLengthPolicy

    generator = CompanyChartGenerator(_provider())
    ref_id = "account:fr-pcg:2026:512"
    cases = [
        (
            GenerationMode.REFERENCE_ONLY,
            None,
            None,
            "512",
        ),
        (
            GenerationMode.PAD_TO_LENGTH,
            NumericFixedLengthPolicy(length=8, padding_char="0"),
            None,
            "51200000",
        ),
        (
            GenerationMode.TEMPLATE_EXPANSION,
            None,
            "{reference}-BNP",
            "512-BNP",
        ),
    ]
    for mode, policy, template, expected_code in cases:
        result = generator.generate(
            CompanyChartGenerationRequest(
                entity_id=EntityId("ent_1"),
                standard=StandardType.PCG_FRANCE,
                reference_snapshot_id="golden-pcg-2026-1",
                edition="2026",
                mode=mode,
                code_policy=policy,
                template=template,
                inclusion=ReferenceNodeInclusionPolicy.INCLUDE_ALL_ACCOUNTS,
                auto_promote=True,
            )
        )
        bindings = result.registry.bindings_for_reference(ref_id)
        assert len(bindings) == 1
        binding = bindings[0]
        assert binding.company_account_code == expected_code
        assert binding.reference_node_id == ref_id
        assert binding.company_account_code != "account:fr-pcg:2026:512"
