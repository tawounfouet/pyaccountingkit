"""Unit qualification for the CFA FRA golden parity primitives."""

from __future__ import annotations

from decimal import Decimal

import pytest

from pyaccountingkit.integrations.cfa_fra.golden import (
    DivergenceCategory,
    GoldenCategory,
    GoldenFixture,
    IntentionalDivergence,
    ORACLE_MANIFEST_VERSION,
    ORACLE_TREE_SHA,
)


def _fixture(**overrides: object) -> GoldenFixture:
    values: dict[str, object] = {
        "scenario_id": "CFA-TEST-001",
        "category": GoldenCategory.POSTING,
        "inputs": {"amount": Decimal("1000"), "currency": "XAF"},
        "expected": {
            "status": "POSTED",
            "lines": [
                {"account": "57110000", "debit": Decimal("1000"), "credit": Decimal("0")},
                {"account": "10110000", "debit": Decimal("0"), "credit": Decimal("1000")},
            ],
        },
    }
    values.update(overrides)
    return GoldenFixture(**values)  # type: ignore[arg-type]


def test_fixture_checksum_is_deterministic_across_mapping_order() -> None:
    left = _fixture(inputs={"currency": "XAF", "amount": Decimal("1000")})
    right = _fixture(inputs={"amount": Decimal("1000"), "currency": "XAF"})
    assert left.checksum == right.checksum


def test_fixture_normalizes_decimal_to_exact_string() -> None:
    fixture = _fixture()
    assert fixture.inputs["amount"] == "1000"
    lines = fixture.expected["lines"]
    assert isinstance(lines, tuple)
    first = lines[0]
    assert isinstance(first, dict) is False
    assert first["debit"] == "1000"  # type: ignore[index]


def test_fixture_rejects_binary_float_even_when_nested() -> None:
    with pytest.raises(TypeError, match="binary float forbidden"):
        _fixture(expected={"nested": {"amount": 0.1}})


def test_exact_parity_is_qualified() -> None:
    fixture = _fixture(expected={"status": "POSTED", "total": Decimal("1000")})
    result = fixture.compare({"status": "POSTED", "total": Decimal("1000")})
    assert result.exact is True
    assert result.qualified is True
    assert result.mismatches == ()


def test_unregistered_mismatch_fails_closed() -> None:
    fixture = _fixture(expected={"status": "POSTED"})
    result = fixture.compare({"status": "DRAFT"})
    assert result.exact is False
    assert result.qualified is False
    assert result.unregistered_mismatches[0].path == "$.status"


def test_registered_intentional_divergence_is_qualified_but_not_exact() -> None:
    divergence = IntentionalDivergence(
        divergence_id="CFA-DIV-001",
        category=DivergenceCategory.GENERALIZATION,
        paths=("$.entry_number",),
        oracle_behavior="REV- prefix is mandatory",
        pyaccountingkit_behavior="numbering is policy-driven",
        rationale="Legacy numbering is not a universal accounting invariant.",
        migration_impact="Consumer compatibility mapping may preserve the legacy display number.",
        reference="ADR-CFA-010",
    )
    fixture = _fixture(
        expected={"entry_number": "REV-S3-003"},
        divergences=(divergence,),
    )
    result = fixture.compare({"entry_number": "reversal:1"})
    assert result.exact is False
    assert result.qualified is True
    assert result.unregistered_mismatches == ()
    assert result.accepted_divergence_ids == ("CFA-DIV-001",)


def test_extra_actual_field_is_a_mismatch() -> None:
    fixture = _fixture(expected={"status": "POSTED"})
    result = fixture.compare({"status": "POSTED", "orm_object": "forbidden"})
    assert result.qualified is False
    assert result.mismatches[0].path == "$.orm_object"


def test_oracle_identity_is_pinned() -> None:
    fixture = _fixture()
    assert fixture.oracle_tree_sha == ORACLE_TREE_SHA
    assert fixture.oracle_manifest_version == ORACLE_MANIFEST_VERSION
    assert ORACLE_TREE_SHA == "07d4880534d2e2239e19fd4ef4139de70b56773a"
