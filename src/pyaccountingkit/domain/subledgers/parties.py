"""Accounting-local parties and references for subledgers."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.subledgers.auxiliary import AuxiliaryReference
from pyaccountingkit.domain.subledgers.errors import InvalidSubledgerConfigurationError
from pyaccountingkit.domain.subledgers.primitives import (
    SubledgerPartyStatus,
    SubledgerPartyType,
)


@dataclass(frozen=True, slots=True)
class PartyRef:
    """Reference to a party mastered by an external or upstream system."""

    system: str
    value: str

    def __post_init__(self) -> None:
        if not self.system.strip():
            raise InvalidSubledgerConfigurationError("party reference system must not be empty")
        if not self.value.strip():
            raise InvalidSubledgerConfigurationError("party reference value must not be empty")


@dataclass(frozen=True, slots=True)
class SubledgerParty:
    """Accounting-local party identity; deliberately not a CompanyAccount."""

    party_id: str
    entity_id: EntityId
    party_type: SubledgerPartyType
    display_name: str
    external_ref: PartyRef | None = None
    auxiliary_reference: AuxiliaryReference | None = None
    status: SubledgerPartyStatus = SubledgerPartyStatus.ACTIVE

    def __post_init__(self) -> None:
        if not self.party_id.strip():
            raise InvalidSubledgerConfigurationError("party_id must not be empty")
        if not self.display_name.strip():
            raise InvalidSubledgerConfigurationError("display_name must not be empty")

    def is_active(self) -> bool:
        return self.status is SubledgerPartyStatus.ACTIVE


__all__ = ["PartyRef", "SubledgerParty"]
