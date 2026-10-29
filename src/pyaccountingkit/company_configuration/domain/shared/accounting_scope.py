"""Explicit multi-tenant accounting scope; no implicit current tenant."""

from dataclasses import dataclass

from .errors import InvalidScope
from .identifiers import AccountingBookId, CompanyId, LegalEntityId


@dataclass(frozen=True, slots=True)
class ConfigurationScope:
    tenant_id: str
    company_id: CompanyId
    legal_entity_id: LegalEntityId
    book_id: AccountingBookId | None = None

    def __post_init__(self) -> None:
        if (not isinstance(self.tenant_id, str) or not self.tenant_id
                or self.tenant_id.strip() != self.tenant_id):
            raise InvalidScope("A non-empty explicit tenant_id is required")
        if not isinstance(self.company_id, CompanyId):
            raise InvalidScope("A typed company_id is required")
        if not isinstance(self.legal_entity_id, LegalEntityId):
            raise InvalidScope("A typed legal_entity_id is required")
        if self.book_id is not None and not isinstance(self.book_id, AccountingBookId):
            raise InvalidScope("book_id must be an AccountingBookId when provided")

    def require_same_scope(self, other: "ConfigurationScope") -> None:
        if not isinstance(other, ConfigurationScope) or self != other:
            raise InvalidScope("Cross-scope use is forbidden")
