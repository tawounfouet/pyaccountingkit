"""L03 organization domain: scope identity and historical affiliations, no ledger."""

from .entities import LegalEntity
from .model import (
    Company,
    CompanyKind,
    CompanyStatus,
    Establishment,
    EstablishmentStatus,
    LegalIdentifier,
    MembershipKind,
    OrganizationMembership,
    require_establishment_parent,
    require_membership_parents,
)
from .policies import (
    active_memberships_at,
    require_no_exclusive_membership_conflicts,
    require_unique_legal_identifier,
)

__all__ = [
    "Company",
    "CompanyKind",
    "CompanyStatus",
    "Establishment",
    "EstablishmentStatus",
    "LegalEntity",
    "LegalIdentifier",
    "MembershipKind",
    "OrganizationMembership",
    "active_memberships_at",
    "require_establishment_parent",
    "require_membership_parents",
    "require_no_exclusive_membership_conflicts",
    "require_unique_legal_identifier",
]
