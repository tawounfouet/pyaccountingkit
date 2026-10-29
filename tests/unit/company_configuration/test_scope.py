import pytest

from pyaccountingkit.company_configuration.domain.shared.accounting_scope import ConfigurationScope
from pyaccountingkit.company_configuration.domain.shared.errors import InvalidScope
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountingBookId, CompanyId, LegalEntityId,
)


def scope(tenant="tenant-a", book=None):
    return ConfigurationScope(tenant, CompanyId.new(), LegalEntityId.new(), book)


def test_explicit_scope_accepted():
    s = scope(book=AccountingBookId.new())
    s.require_same_scope(s)


def test_cross_scope_rejected_even_same_ids_other_tenant():
    s = scope()
    other = ConfigurationScope("tenant-b", s.company_id, s.legal_entity_id)
    with pytest.raises(InvalidScope):
        s.require_same_scope(other)


@pytest.mark.parametrize("tenant", [None, "", " other ", 123])
def test_invalid_tenant_rejected(tenant):
    with pytest.raises(InvalidScope):
        scope(tenant)


def test_book_id_must_be_typed():
    with pytest.raises(InvalidScope):
        scope(book=CompanyId.new())
