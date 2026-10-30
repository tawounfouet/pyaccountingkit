"""Opaque, runtime-distinguishable UUID identifiers.

Do not confuse a company, legal entity, book, or draft just because their
underlying UUID happens to match. Parsing strings is explicit at boundaries.
"""

from dataclasses import dataclass
from typing import Self
from uuid import UUID, uuid4

from .errors import InvalidIdentifier


@dataclass(frozen=True, slots=True)
class _UUIDIdentifier:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise InvalidIdentifier(f"{type(self).__name__} requires a UUID")

    @classmethod
    def new(cls) -> Self:
        return cls(uuid4())

    @classmethod
    def parse(cls, value: str) -> Self:
        if not isinstance(value, str) or not value or value.strip() != value:
            raise InvalidIdentifier(f"{cls.__name__} requires a canonical UUID string")
        try:
            parsed = UUID(value)
        except (ValueError, AttributeError) as exc:
            raise InvalidIdentifier(f"Invalid {cls.__name__}") from exc
        if str(parsed) != value:
            raise InvalidIdentifier(f"{cls.__name__} must use lower-case canonical UUID format")
        return cls(parsed)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class CompanyId(_UUIDIdentifier):
    """Stable identity of an organizational configuration perimeter."""


@dataclass(frozen=True, slots=True)
class LegalEntityId(_UUIDIdentifier):
    """Stable identity of a legal entity."""


@dataclass(frozen=True, slots=True)
class AccountingBookId(_UUIDIdentifier):
    """Stable identity of a book, separate from its code or framework."""


@dataclass(frozen=True, slots=True)
class BookAssignmentId(_UUIDIdentifier):
    """Stable identity of a proposed book/entity assignment, separate from the book."""


@dataclass(frozen=True, slots=True)
class FrameworkBindingId(_UUIDIdentifier):
    """Candidate framework binding identity, distinct from book and normative ref."""


@dataclass(frozen=True, slots=True)
class NormativeStatementId(_UUIDIdentifier):
    """Identity of an external-source declaration (not of a normative rule)."""


@dataclass(frozen=True, slots=True)
class BookCandidateVersionId(_UUIDIdentifier):
    """Unpublished L04 R&D component version, not an approved publication."""


@dataclass(frozen=True, slots=True)
class BookDependencyClaimId(_UUIDIdentifier):
    """Local R&D dependency claim ID, not a certified external registry ID."""


@dataclass(frozen=True, slots=True)
class ConfigurationDraftId(_UUIDIdentifier):
    """Stable identity of an unpublished configuration draft."""


@dataclass(frozen=True, slots=True)
class ConfigurationVersionId(_UUIDIdentifier):
    """Stable identity of a configuration version."""
