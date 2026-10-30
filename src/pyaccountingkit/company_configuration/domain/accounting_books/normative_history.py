"""L04-05: pure, bitemporal declarations about normative references.

Company Configuration does not own Normative Layer truth. A statement from a
test catalog is NOT proof of legal validity, availability or certified content.
This module is exclusively for isolated, non-postable historical R&D preview.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum

from ..shared.effective_interval import EffectiveInterval, KnowledgeInterval
from ..shared.errors import DomainError
from ..shared.identifiers import NormativeStatementId
from ..shared.references import ReferenceFrameworkRef


class InvalidNormativeStatement(DomainError):
    code = "INVALID_NORMATIVE_STATEMENT"


class NormativeStatementMissing(DomainError):
    code = "NORMATIVE_STATEMENT_MISSING"


class NormativeStatementAmbiguous(DomainError):
    code = "NORMATIVE_STATEMENT_AMBIGUOUS"


class NormativeStatementUnavailable(DomainError):
    code = "NORMATIVE_STATEMENT_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class NormativeSourceCode:
    """Provisional source identifier; not an authority validation."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not re.fullmatch(
            r"[A-Z][A-Z0-9_-]{0,31}", self.value
        ):
            raise InvalidNormativeStatement("Canonical uppercase source code required")


class NormativeDeclaration(Enum):
    """Claimed state of a reference, never independently verified by this code."""

    DECLARED_AVAILABLE = "DECLARED_AVAILABLE"
    DECLARED_UNAVAILABLE = "DECLARED_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class NormativeReferenceStatement:
    """Source-scoped declaration with independent business and knowledge windows."""

    id: NormativeStatementId
    source: NormativeSourceCode
    framework: ReferenceFrameworkRef
    effective: EffectiveInterval
    knowledge: KnowledgeInterval
    declaration: NormativeDeclaration
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, NormativeStatementId):
            raise InvalidNormativeStatement("Typed NormativeStatementId required")
        if not isinstance(self.source, NormativeSourceCode):
            raise InvalidNormativeStatement("Typed NormativeSourceCode required")
        if not isinstance(self.framework, ReferenceFrameworkRef):
            raise InvalidNormativeStatement("Typed versioned framework required")
        if not isinstance(self.effective, EffectiveInterval):
            raise InvalidNormativeStatement("EffectiveInterval required")
        if not isinstance(self.knowledge, KnowledgeInterval):
            raise InvalidNormativeStatement("KnowledgeInterval required")
        if not isinstance(self.declaration, NormativeDeclaration):
            raise InvalidNormativeStatement("Typed declaration required")
        if (
            not isinstance(self.source_ref, str)
            or not self.source_ref.strip()
            or self.source_ref != self.source_ref.strip()
        ):
            raise InvalidNormativeStatement("Nonblank trimmed provenance pointer required")


@dataclass(frozen=True, slots=True)
class NormativeReferenceHistoricalPreview:
    """An as-of/known-at claim selection, NOT a signed normative attestation."""

    statement_id: NormativeStatementId
    source: NormativeSourceCode
    framework: ReferenceFrameworkRef
    as_of: date
    known_at: datetime
    source_ref: str


def preview_normative_reference_history(
    *,
    framework: ReferenceFrameworkRef,
    source: NormativeSourceCode,
    as_of: date,
    known_at: datetime,
    statements: tuple[NormativeReferenceStatement, ...],
) -> NormativeReferenceHistoricalPreview:
    """Select exactly one externally *declared* state at business/knowledge time.

    No 'latest' fallback. Multiple concurrent claims are explicitly ambiguous;
    a declared-unavailable claim blocks selection even when a prior positive
    statement is known. No official source content is retrieved or certified.
    """
    if not isinstance(framework, ReferenceFrameworkRef):
        raise InvalidNormativeStatement("Typed versioned framework required")
    if not isinstance(source, NormativeSourceCode):
        raise InvalidNormativeStatement("Typed normative source required")
    if type(as_of) is not date:
        raise InvalidNormativeStatement("Business date required, not datetime")
    if (
        type(known_at) is not datetime
        or known_at.tzinfo is None
        or known_at.utcoffset() is None
    ):
        raise InvalidNormativeStatement("Timezone-aware known_at required")
    if not isinstance(statements, tuple):
        raise InvalidNormativeStatement("Statements must be an immutable tuple")

    seen: set[NormativeStatementId] = set()
    eligible: NormativeReferenceStatement | None = None
    for record in statements:
        if not isinstance(record, NormativeReferenceStatement):
            raise InvalidNormativeStatement("Catalog contains non-statement")
        if record.id in seen:
            raise NormativeStatementAmbiguous("Duplicate normative statement identity")
        seen.add(record.id)
        if record.framework != framework or record.source != source:
            raise InvalidNormativeStatement("Catalog leaked a foreign reference/source")
        if record.effective.contains(as_of) and record.knowledge.contains(known_at):
            if eligible is not None:
                raise NormativeStatementAmbiguous(
                    "Concurrent declarations for same reference, source and time"
                )
            eligible = record

    if eligible is None:
        raise NormativeStatementMissing("No declared state at effective_at and known_at")
    if eligible.declaration is NormativeDeclaration.DECLARED_UNAVAILABLE:
        raise NormativeStatementUnavailable(
            "Source declared this reference unavailable at the historical cutoff"
        )
    return NormativeReferenceHistoricalPreview(
        statement_id=eligible.id,
        source=source,
        framework=framework,
        as_of=as_of,
        known_at=known_at,
        source_ref=eligible.source_ref,
    )
