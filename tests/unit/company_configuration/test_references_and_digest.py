import pytest

from pyaccountingkit.company_configuration.domain.shared.digest import ContentDigest
from pyaccountingkit.company_configuration.domain.shared.errors import InvalidDigest, InvalidReference
from pyaccountingkit.company_configuration.domain.shared.references import (
    CurrencyCode, ReferenceFrameworkRef,
)


def test_references_are_versioned_and_opaque():
    assert CurrencyCode("EUR").value == "EUR"
    assert ReferenceFrameworkRef("PCG", "2026").version == "2026"


@pytest.mark.parametrize("value", ["eUr", "EÚR", "EURO", "", None])
def test_invalid_currency_ref(value):
    with pytest.raises(InvalidReference):
        CurrencyCode(value)


@pytest.mark.parametrize("code,version", [("", "2026"), ("PCG", ""),
                                            (" PCG", "2026"), ("PCG", "2026 ")])
def test_missing_or_ambiguous_framework_ref(code, version):
    with pytest.raises(InvalidReference):
        ReferenceFrameworkRef(code, version)


def test_digest_is_deterministic_for_key_order():
    a = ContentDigest.from_canonical_json({"book": "A", "enabled": True})
    b = ContentDigest.from_canonical_json({"enabled": True, "book": "A"})
    assert a == b
    assert len(a.hex_sha256) == 64


def test_digest_rejects_invalid_json_and_hash():
    with pytest.raises(InvalidDigest):
        ContentDigest.from_canonical_json({"bad": {2, 3}})
    with pytest.raises(InvalidDigest):
        ContentDigest.from_canonical_json({"nan": float("nan")})
    with pytest.raises(InvalidDigest):
        ContentDigest("ABC")
