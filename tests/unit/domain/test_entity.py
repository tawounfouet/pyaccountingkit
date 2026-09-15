"""Unit tests for the AccountingEntity identity root."""

from __future__ import annotations

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.identity.entity import AccountingEntity


def _entity() -> AccountingEntity:
    return AccountingEntity(id=EntityId("ent_1"), name="ACME", default_currency=EUR)


def test_entity_declares_identity_and_default_currency() -> None:
    entity = _entity()
    assert entity.id == EntityId("ent_1")
    assert entity.default_currency == EUR
    assert entity.active


def test_entity_is_immutable() -> None:
    entity = _entity()
    with pytest.raises(AttributeError):
        entity.name = "OTHER"  # type: ignore[misc]


def test_inactive_entity_is_supported() -> None:
    entity = AccountingEntity(id=EntityId("ent_2"), name="OLD", default_currency=EUR, active=False)
    assert not entity.active
