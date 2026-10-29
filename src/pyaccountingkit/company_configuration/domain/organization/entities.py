"""Pure LegalEntity aggregate slice for L01.

This is deliberately not the L03 organization module: membership validity,
legal identifiers, statuses, permission checks and audit persistence are not
implemented here. Creating the record does not activate an accounting book.
"""

from dataclasses import dataclass, replace

from ..shared.accounting_scope import ConfigurationScope
from ..shared.errors import InvalidLegalEntity, VersionConflict
from ..shared.identifiers import LegalEntityId
from ..shared.references import CurrencyCode, JurisdictionCode


def _nonblank(value: str, field: str) -> None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value.strip() != value
    ):
        raise InvalidLegalEntity(f"{field} must be a non-empty, trimmed string")


@dataclass(frozen=True, slots=True, eq=False)
class LegalEntity:
    """Identity-stable, immutable legal-entity record for an explicit scope.

    The scope describes the **configuration tenant and company perimeter**;
    it is not proof of organizational membership or authorization. A new
    version is produced on a proposed name change; external use cases own
    authorization, durable audit, and publication in later lots.
    """

    id: LegalEntityId
    scope: ConfigurationScope
    legal_name: str
    jurisdiction: JurisdictionCode
    functional_currency: CurrencyCode
    revision: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, LegalEntityId):
            raise InvalidLegalEntity("LegalEntity.id must be a typed LegalEntityId")
        if not isinstance(self.scope, ConfigurationScope):
            raise InvalidLegalEntity("LegalEntity requires a ConfigurationScope")
        if self.scope.legal_entity_id != self.id or self.scope.book_id is not None:
            raise InvalidLegalEntity("Entity-level scope must match id and have no book")
        _nonblank(self.legal_name, "legal_name")
        if not isinstance(self.jurisdiction, JurisdictionCode):
            raise InvalidLegalEntity("jurisdiction must be a typed JurisdictionCode")
        if not isinstance(self.functional_currency, CurrencyCode):
            raise InvalidLegalEntity("functional_currency must be a typed CurrencyCode")
        if type(self.revision) is not int or self.revision < 1:
            raise InvalidLegalEntity("revision must be a positive integer")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LegalEntity):
            return NotImplemented
        return (self.scope.tenant_id, self.id) == (other.scope.tenant_id, other.id)

    def __hash__(self) -> int:
        return hash((self.scope.tenant_id, self.id))

    def with_legal_name(
        self, new_name: str, *, expected_revision: int, reason: str
    ) -> "LegalEntity":
        """Produce a reviewed *candidate* revision; no write/audit occurs.

        Authorization and audit are mandatory at the application boundary
        in L02; this method alone cannot authorize a company configuration.
        """
        if type(expected_revision) is not int or expected_revision != self.revision:
            raise VersionConflict("LegalEntity revision does not match")
        _nonblank(new_name, "new_name")
        _nonblank(reason, "reason")
        if new_name == self.legal_name:
            raise InvalidLegalEntity("A name amendment must change the legal name")
        return replace(self, legal_name=new_name, revision=self.revision + 1)
