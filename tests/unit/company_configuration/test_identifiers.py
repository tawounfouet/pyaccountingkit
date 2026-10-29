from uuid import UUID

import pytest

from pyaccountingkit.company_configuration.domain.shared.errors import InvalidIdentifier
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountingBookId,
    CompanyId,
    ConfigurationDraftId,
    ConfigurationVersionId,
    LegalEntityId,
)


@pytest.mark.parametrize("cls", [CompanyId, LegalEntityId, AccountingBookId,
                                 ConfigurationDraftId, ConfigurationVersionId])
def test_typed_ids_roundtrip(cls):
    value = cls.new()
    assert cls.parse(str(value)) == value
    assert isinstance(value.value, UUID)


def test_id_types_not_interchangeable():
    raw = CompanyId.new().value
    assert CompanyId(raw) != LegalEntityId(raw)
    assert len({CompanyId(raw), LegalEntityId(raw)}) == 2


@pytest.mark.parametrize("invalid", [None, "", "not-a-uuid", " 00000000-0000-0000-0000-000000000000",
                                     "00000000-0000-0000-0000-000000000000 ", 12,
                                     "00000000-0000-0000-0000-00000000000A"])
def test_noncanonical_or_invalid_identifiers_rejected(invalid):
    with pytest.raises(InvalidIdentifier):
        CompanyId.parse(invalid)


def test_constructor_rejects_raw_string():
    with pytest.raises(InvalidIdentifier):
        CompanyId("00000000-0000-0000-0000-000000000000")
