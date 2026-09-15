"""Unit tests for chart generation from reference plans (LOT-11)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pyaccountingkit.adapters.regulatory._base import parse_structure
from pyaccountingkit.adapters.regulatory.in_memory import InMemoryReferenceAdapter
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.charts.generation import (
    CompanyChartGenerationRequest,
    CompanyChartGenerator,
    GenerationMode,
    ReferenceNodeInclusionPolicy,
)
from pyaccountingkit.domain.charts.numbering import (
    NumericFixedLengthPolicy,
)
from pyaccountingkit.domain.references.relations import (
    ConstraintKind,
    NegativeConstraint,
)
from pyaccountingkit.domain.references.standards import StandardType

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "regulatory"
CONSTRAINTS = {
    StandardType.PCG_FRANCE: (
        NegativeConstraint(
            node_id="account:fr-pcg:2026:401",
            kind=ConstraintKind.CREDIT_ONLY,
            reason="Fournisseurs.",
            standard_id="fr-pcg",
        ),
    ),
}


def _provider() -> InMemoryReferenceAdapter:
    raw = json.loads((FIXTURES / "mini_canonical_structure.json").read_text(encoding="utf-8"))
    hierarchy = parse_structure(raw)
    return InMemoryReferenceAdapter(
        {StandardType.PCG_FRANCE: hierarchy},
        clock=FrozenClock(),
        extra_constraints=CONSTRAINTS,
    )


def _request(**kwargs: object) -> CompanyChartGenerationRequest:
    defaults: dict[str, object] = {
        "entity_id": EntityId("ent_1"),
        "standard": StandardType.PCG_FRANCE,
        "reference_snapshot_id": "snap1",
        "edition": "2026",
        "effective_date": date(2026, 1, 1),
    }
    defaults.update(kwargs)
    return CompanyChartGenerationRequest(**defaults)  # type: ignore[arg-type]


def test_reference_only_minimum_plan() -> None:
    provider = _provider()
    generator = CompanyChartGenerator(provider)
    result = generator.generate(_request())
    codes = {account.code for account in result.accounts}
    assert "101" in codes
    assert "401" in codes
    assert "105" not in codes
    assert len(result.candidates) == len(result.accounts)


def test_include_all_accounts() -> None:
    provider = _provider()
    generator = CompanyChartGenerator(provider)
    result = generator.generate(
        _request(inclusion=ReferenceNodeInclusionPolicy.INCLUDE_ALL_ACCOUNTS)
    )
    codes = {account.code for account in result.accounts}
    assert "105" in codes
    assert "101" in codes


def test_pad_to_length_generates_padded_codes() -> None:
    provider = _provider()
    policy = NumericFixedLengthPolicy(length=8, padding_char="0")
    generator = CompanyChartGenerator(provider)
    result = generator.generate(
        _request(
            mode=GenerationMode.PAD_TO_LENGTH,
            code_policy=policy,
        )
    )
    codes = {account.code for account in result.accounts}
    assert "51200000" in codes or "40100000" in codes
    for code in codes:
        assert len(code) == 8
        assert code.isdigit()


def test_multi_format_512_binds_correctly() -> None:
    """DoD: PCG 512 can map to multiple company code formats; binding is explicit."""
    provider = _provider()
    generator = CompanyChartGenerator(provider)
    ref_id = "account:fr-pcg:2026:512"
    cases = [
        (
            GenerationMode.PAD_TO_LENGTH,
            NumericFixedLengthPolicy(length=8, padding_char="0"),
            "51200000",
        ),
        (GenerationMode.REFERENCE_ONLY, None, "512"),
    ]
    for mode, policy, expected_code in cases:
        result = generator.generate(
            _request(
                mode=mode,
                code_policy=policy,
                inclusion=ReferenceNodeInclusionPolicy.INCLUDE_ALL_ACCOUNTS,
                auto_promote=True,
            )
        )
        bindings = result.registry.bindings_for_reference(ref_id)
        assert len(bindings) == 1, f"expected 1 binding for {ref_id}"
        binding = bindings[0]
        assert binding.company_account_code == expected_code
        assert binding.reference_node_id == ref_id


def test_company_code_is_not_a_reference_id() -> None:
    """DoD: company code != regulatory ID — links are explicit, not inferred."""
    provider = _provider()
    generator = CompanyChartGenerator(provider)
    result = generator.generate(
        _request(
            mode=GenerationMode.PAD_TO_LENGTH,
            code_policy=NumericFixedLengthPolicy(length=8, padding_char="0"),
            inclusion=ReferenceNodeInclusionPolicy.INCLUDE_ALL_ACCOUNTS,
            auto_promote=True,
        )
    )
    for binding in result.bindings:
        assert binding.company_account_code != binding.reference_node_id


def test_template_expansion() -> None:
    provider = _provider()
    generator = CompanyChartGenerator(provider)
    result = generator.generate(
        _request(
            mode=GenerationMode.TEMPLATE_EXPANSION,
            template="{reference}-BNP",
            inclusion=ReferenceNodeInclusionPolicy.MINIMUM_PLAN_ONLY,
        )
    )
    codes = {account.code for account in result.accounts}
    assert any(code.endswith("-BNP") for code in codes)


def test_auto_promote_creates_bindings() -> None:
    provider = _provider()
    generator = CompanyChartGenerator(provider)
    result = generator.generate(_request(auto_promote=True))
    assert len(result.bindings) == len(result.accounts)
    assert len(result.candidates) == 0


def test_candidates_separated_from_bindings() -> None:
    provider = _provider()
    generator = CompanyChartGenerator(provider)
    result = generator.generate(_request())
    assert len(result.candidates) > 0
    assert len(result.bindings) == 0


def test_non_postable_account_codes_are_company_codes_not_regulatory_ids() -> None:
    provider = _provider()
    generator = CompanyChartGenerator(provider)
    policy = NumericFixedLengthPolicy(length=8, padding_char="0")
    result = generator.generate(
        _request(
            mode=GenerationMode.PAD_TO_LENGTH,
            code_policy=policy,
            inclusion=ReferenceNodeInclusionPolicy.MINIMUM_PLAN_ONLY,
            auto_promote=True,
        )
    )
    for account in result.accounts:
        assert len(account.code) == 8
    for binding in result.bindings:
        assert binding.reference_node_id.startswith("account:")
