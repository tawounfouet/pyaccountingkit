"""Typed application commands; roles never appear in payloads."""

from dataclasses import dataclass

from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.identifiers import LegalEntityId
from ..domain.shared.references import CurrencyCode, JurisdictionCode


def _required(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip() or value.strip() != value:
        raise ValueError(f"{label} must be non-empty and trimmed")


@dataclass(frozen=True, slots=True)
class CreateLegalEntity:
    scope: ConfigurationScope
    legal_name: str
    jurisdiction: JurisdictionCode
    functional_currency: CurrencyCode
    request_id: str
    correlation_id: str
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is not None:
            raise ValueError("CreateLegalEntity requires an entity-level scope")
        for value, label in ((self.request_id, "request_id"),
                             (self.correlation_id, "correlation_id"),
                             (self.reason, "reason")):
            _required(value, label)
        _required(self.legal_name, "legal_name")
        if not isinstance(self.jurisdiction, JurisdictionCode):
            raise ValueError("Typed jurisdiction required")
        if not isinstance(self.functional_currency, CurrencyCode):
            raise ValueError("Typed functional currency required")


@dataclass(frozen=True, slots=True)
class RenameLegalEntity:
    scope: ConfigurationScope
    entity_id: LegalEntityId
    new_name: str
    expected_revision: int
    request_id: str
    correlation_id: str
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is not None:
            raise ValueError("RenameLegalEntity requires an entity-level scope")
        if not isinstance(self.entity_id, LegalEntityId):
            raise ValueError("Typed legal entity id required")
        if self.entity_id != self.scope.legal_entity_id:
            raise ValueError("Entity id must match scope")
        if type(self.expected_revision) is not int or self.expected_revision < 1:
            raise ValueError("A positive expected revision is required")
        for value, label in ((self.request_id, "request_id"),
                             (self.correlation_id, "correlation_id"),
                             (self.reason, "reason"), (self.new_name, "new_name")):
            _required(value, label)
