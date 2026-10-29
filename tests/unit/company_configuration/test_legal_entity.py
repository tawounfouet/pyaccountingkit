"""Pure invariants for minimal L01 LegalEntity aggregate."""

import pytest

from pyaccountingkit.company_configuration.domain.organization import LegalEntity
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.errors import (
    InvalidLegalEntity,
    InvalidReference,
    VersionConflict,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountingBookId,
    CompanyId,
    LegalEntityId,
)
from pyaccountingkit.company_configuration.domain.shared.references import (
    CurrencyCode,
    JurisdictionCode,
)


def entity(*, tenant="t1", legal_name="Example SARL") -> LegalEntity:
    entity_id = LegalEntityId.new()
    scope = ConfigurationScope(tenant, CompanyId.new(), entity_id)
    return LegalEntity(
        id=entity_id,
        scope=scope,
        legal_name=legal_name,
        jurisdiction=JurisdictionCode("FR"),
        functional_currency=CurrencyCode("EUR"),
    )


def test_create_entity_preserves_identity_and_scope():
    value = entity()
    assert value.scope.legal_entity_id == value.id
    assert value.revision == 1
    assert value.jurisdiction.value == "FR"


def test_revision_is_immutable_and_identity_stays_stable():
    original = entity()
    amended = original.with_legal_name(
        "Example France SARL", expected_revision=1, reason="Legal name updated"
    )
    assert amended.id == original.id
    assert amended == original
    assert hash(amended) == hash(original)
    assert amended.legal_name == "Example France SARL"
    assert amended.revision == 2
    assert original.legal_name == "Example SARL"
    assert original.revision == 1


@pytest.mark.parametrize("value", ["", "  ", " Example", "Example ", None, 1])
def test_invalid_names_rejected(value):
    with pytest.raises(InvalidLegalEntity):
        entity(legal_name=value)


def test_book_level_scope_rejected_for_entity():
    legal_id = LegalEntityId.new()
    scope = ConfigurationScope("t1", CompanyId.new(), legal_id, AccountingBookId.new())
    with pytest.raises(InvalidLegalEntity):
        LegalEntity(legal_id, scope, "Example", JurisdictionCode("FR"), CurrencyCode("EUR"))


def test_scope_id_mismatch_rejected():
    legal_id = LegalEntityId.new()
    scope = ConfigurationScope("t1", CompanyId.new(), LegalEntityId.new())
    with pytest.raises(InvalidLegalEntity):
        LegalEntity(legal_id, scope, "Example", JurisdictionCode("FR"), CurrencyCode("EUR"))


@pytest.mark.parametrize("version", [0, -1, True, "1", None])
def test_invalid_revision_rejected(version):
    old = entity()
    with pytest.raises(InvalidLegalEntity):
        LegalEntity(
            old.id, old.scope, old.legal_name, old.jurisdiction, old.functional_currency,
            version,
        )


@pytest.mark.parametrize("version", [0, 2, True, "1", None])
def test_stale_or_invalid_revision_rejected(version):
    with pytest.raises(VersionConflict):
        entity().with_legal_name("Changed", expected_revision=version, reason="Change")


@pytest.mark.parametrize("name, reason", [
    ("Example SARL", "Reason"), ("Changed", ""), ("Changed", "   "),
    ("Changed", " Reason"), ("", "Reason"),
])
def test_invalid_amendment_rejected(name, reason):
    with pytest.raises(InvalidLegalEntity):
        entity().with_legal_name(name, expected_revision=1, reason=reason)


@pytest.mark.parametrize("code", ["fr", "FRA", "F", "F1", " FR", "", None])
def test_invalid_jurisdiction_shape_rejected(code):
    with pytest.raises(InvalidReference):
        JurisdictionCode(code)


def test_equivalent_id_from_another_tenant_is_not_same_entity():
    left = entity(tenant="tenant-A")
    right = LegalEntity(
        left.id,
        ConfigurationScope("tenant-B", left.scope.company_id, left.id),
        left.legal_name,
        left.jurisdiction,
        left.functional_currency,
    )
    assert right != left


def test_wrong_id_type_rejected():
    left = entity()
    with pytest.raises(InvalidLegalEntity):
        LegalEntity(
            CompanyId.new(), left.scope, left.legal_name,
            left.jurisdiction, left.functional_currency,
        )
