"""Unit tests for account code policies (LOT-11)."""

from __future__ import annotations

import pytest

from pyaccountingkit.core.errors import InvalidAccountCodeError
from pyaccountingkit.domain.charts.numbering import (
    AccountCodeGenerationRequest,
    AccountCodeSegment,
    AlphanumericPolicy,
    CustomAccountCodePolicy,
    NumericFixedLengthPolicy,
    NumericVariableLengthPolicy,
    SegmentedNumericPolicy,
)


class TestNumericFixedLength:
    def test_validates_exact_length(self) -> None:
        policy = NumericFixedLengthPolicy(length=8)
        result = policy.validate("51200001")
        assert result.ok
        assert not result.errors

    def test_rejects_wrong_length(self) -> None:
        policy = NumericFixedLengthPolicy(length=8)
        result = policy.validate("512")
        assert not result.ok
        assert any("exactly 8" in e for e in result.errors)

    def test_require_valid_raises_on_invalid(self) -> None:
        policy = NumericFixedLengthPolicy(length=8)
        with pytest.raises(InvalidAccountCodeError, match="exactly 8"):
            policy.require_valid("512")

    def test_require_valid_returns_normalized(self) -> None:
        policy = NumericFixedLengthPolicy(length=8)
        assert policy.require_valid("51200001") == "51200001"

    def test_generate_pads_right(self) -> None:
        policy = NumericFixedLengthPolicy(length=8, padding_char="0")
        code = policy.generate(AccountCodeGenerationRequest(reference_code="512"))
        assert code == "51200000"

    def test_generate_rejects_long_input(self) -> None:
        policy = NumericFixedLengthPolicy(length=6)
        with pytest.raises(InvalidAccountCodeError):
            policy.generate(AccountCodeGenerationRequest(reference_code="123456789"))

    def test_normalization_is_identity(self) -> None:
        policy = NumericFixedLengthPolicy(length=6)
        assert policy.normalize("512001") == "512001"


class TestNumericVariableLength:
    def test_allows_valid_digits(self) -> None:
        policy = NumericVariableLengthPolicy(min_length=3, max_length=12)
        assert policy.validate("51201").ok
        assert not policy.validate("51").ok
        assert not policy.validate("A123").ok

    def test_generate_returns_ref_if_valid(self) -> None:
        policy = NumericVariableLengthPolicy(min_length=3, max_length=8)
        assert policy.generate(AccountCodeGenerationRequest(reference_code="51201")) == "51201"


class TestSegmentedNumeric:
    def test_fixed_length_split(self) -> None:
        segments = (
            AccountCodeSegment(name="ref", length=3),
            AccountCodeSegment(name="bank", length=2),
            AccountCodeSegment(name="seq", length=4),
        )
        policy = SegmentedNumericPolicy(segments=segments)
        assert policy.validate("512010001").ok
        assert policy.split("512010001") == {"ref": "512", "bank": "01", "seq": "0001"}

    def test_rejects_wrong_total_length(self) -> None:
        segments = (AccountCodeSegment(name="ref", length=3),)
        policy = SegmentedNumericPolicy(segments=segments)
        assert not policy.validate("51200").ok

    def test_generate_from_segments(self) -> None:
        segments = (
            AccountCodeSegment(name="ref", length=3),
            AccountCodeSegment(name="seq", length=2),
        )
        policy = SegmentedNumericPolicy(segments=segments)
        code = policy.generate(AccountCodeGenerationRequest(segments={"ref": "512", "seq": "01"}))
        assert code == "51201"


class TestAlphanumeric:
    def test_pattern_must_match(self) -> None:
        policy = AlphanumericPolicy(pattern=r"[A-Z0-9-]{1,20}")
        assert policy.validate("BANK-BNP-EUR").ok
        assert not policy.validate("bank bnp eur").ok

    def test_normalization_uppercases(self) -> None:
        policy = AlphanumericPolicy(pattern=r"[A-Z0-9-]{1,20}")
        assert policy.normalize("  512-bnp  ") == "512-BNP"

    def test_generate_reference_and_sequence(self) -> None:
        policy = AlphanumericPolicy(pattern=r"[A-Z0-9-]{1,20}")
        code = policy.generate(AccountCodeGenerationRequest(reference_code="BANK", sequence="EUR"))
        assert code == "BANK-EUR"


class TestCustom:
    def test_custom_validate(self) -> None:
        policy = CustomAccountCodePolicy(pattern=r"[A-Z]{3}\d{6}", policy_id="custom")
        assert policy.validate("ABC123456").ok
        assert not policy.validate("AB12345").ok
        assert policy.policy_id == "custom"
