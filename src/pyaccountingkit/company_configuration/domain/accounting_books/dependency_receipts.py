"""L04-07: fail-closed dependency claims and non-authoritative read receipts.

Only declares candidate reference coverage. No content verification, fiscal
period locking, chart eligibility, policy evaluation, publication, or posting.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from ..shared.accounting_scope import ConfigurationScope
from ..shared.effective_interval import EffectiveInterval, KnowledgeInterval
from ..shared.errors import DomainError
from ..shared.identifiers import BookCandidateVersionId, BookDependencyClaimId
from .candidate_snapshots import BookConfigurationCandidateSnapshot


class InvalidBookDependency(DomainError):
    code = "INVALID_BOOK_DEPENDENCY"


class BookDependencyMissing(DomainError):
    code = "BOOK_DEPENDENCY_MISSING"


class BookDependencyAmbiguous(DomainError):
    code = "BOOK_DEPENDENCY_AMBIGUOUS"


class BookDependencyUnavailable(DomainError):
    code = "BOOK_DEPENDENCY_UNAVAILABLE"


class BookDependencyDigestMismatch(DomainError):
    code = "BOOK_DEPENDENCY_DIGEST_MISMATCH"


class BookDependencyKind(Enum):
    """Strict R&D five-slot profile, NOT the final multi-policy/cardinality ADR."""

    CHART = "CHART"
    CALENDAR = "CALENDAR"
    POLICY = "POLICY"
    RULESET = "RULESET"
    DIMENSION = "DIMENSION"


REQUIRED_DEPENDENCIES: tuple[BookDependencyKind, ...] = tuple(BookDependencyKind)
RECEIPT_SCHEMA = "l04-dependency-rnd-1"


class BookDependencyDeclaration(Enum):
    DECLARED_AVAILABLE = "DECLARED_AVAILABLE"
    DECLARED_UNAVAILABLE = "DECLARED_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class BookDependencyRef:
    """Opaque catalog code + version, not a verified external object."""

    code: str
    version: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.code, str)
            or re.fullmatch(r"[A-Z][A-Z0-9_-]{0,63}", self.code) is None
            or not isinstance(self.version, str)
            or not self.version
            or self.version != self.version.strip()
        ):
            raise InvalidBookDependency("Canonical code and explicit version required")


@dataclass(frozen=True, slots=True)
class BookDependencyClaim:
    """A source's dated claim pinned to an *unpublished* book candidate version."""

    id: BookDependencyClaimId
    candidate_version_id: BookCandidateVersionId
    scope: ConfigurationScope
    kind: BookDependencyKind
    reference: BookDependencyRef
    effective: EffectiveInterval
    knowledge: KnowledgeInterval
    declaration: BookDependencyDeclaration
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, BookDependencyClaimId):
            raise InvalidBookDependency("Typed claim ID required")
        if not isinstance(self.candidate_version_id, BookCandidateVersionId):
            raise InvalidBookDependency("Typed candidate version ID required")
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is None:
            raise InvalidBookDependency("Explicit book-level scope required")
        if not isinstance(self.kind, BookDependencyKind):
            raise InvalidBookDependency("Typed dependency kind required")
        if not isinstance(self.reference, BookDependencyRef):
            raise InvalidBookDependency("Typed dependency code/version required")
        if not isinstance(self.effective, EffectiveInterval):
            raise InvalidBookDependency("Business interval required")
        if not isinstance(self.knowledge, KnowledgeInterval):
            raise InvalidBookDependency("Knowledge interval required")
        if not isinstance(self.declaration, BookDependencyDeclaration):
            raise InvalidBookDependency("Typed claim declaration required")
        if (
            not isinstance(self.source_ref, str)
            or not self.source_ref.strip()
            or self.source_ref != self.source_ref.strip()
        ):
            raise InvalidBookDependency("Nonblank trimmed source pointer required")


def _instant(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _canonical_digest(data: dict[str, object]) -> str:
    raw = json.dumps(
        data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _claim_manifest(claim: BookDependencyClaim) -> dict[str, object]:
    return {
        "claim_id": str(claim.id),
        "candidate_version_id": str(claim.candidate_version_id),
        "scope": {
            "tenant": claim.scope.tenant_id,
            "company": str(claim.scope.company_id),
            "entity": str(claim.scope.legal_entity_id),
            "book": str(claim.scope.book_id),
        },
        "kind": claim.kind.value,
        "code": claim.reference.code,
        "version": claim.reference.version,
        "effective": {
            "start": claim.effective.start.isoformat(),
            "end": (
                claim.effective.end.isoformat() if claim.effective.end is not None else None
            ),
        },
        "knowledge": {
            "start": _instant(claim.knowledge.start),
            "end": _instant(claim.knowledge.end) if claim.knowledge.end is not None else None,
        },
        "declaration": claim.declaration.value,
        "source_ref": claim.source_ref,
    }


@dataclass(frozen=True, slots=True, eq=False)
class BookDependencyCandidateReadReceipt:
    """Digest-bound local preview, NOT a certified C10 read receipt."""

    snapshot: BookConfigurationCandidateSnapshot
    selected: tuple[BookDependencyClaim, ...]
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, BookConfigurationCandidateSnapshot):
            raise InvalidBookDependency("Typed R&D candidate snapshot required")
        if not isinstance(self.selected, tuple):
            raise InvalidBookDependency("Immutable selected claims tuple required")
        self.snapshot.verify_integrity()
        self._verify_claims()
        object.__setattr__(self, "content_digest", _canonical_digest(self.canonical_payload()))

    def _verify_claims(self) -> None:
        if len(self.selected) != len(REQUIRED_DEPENDENCIES):
            raise BookDependencyMissing("R&D dependency profile is incomplete")
        found: set[BookDependencyKind] = set()
        for claim in self.selected:
            if not isinstance(claim, BookDependencyClaim):
                raise InvalidBookDependency("Non-typed dependency claim")
            if claim.kind in found:
                raise BookDependencyAmbiguous("Duplicate dependency kind in receipt")
            found.add(claim.kind)
            if (
                claim.scope != self.snapshot.version.scope
                or claim.candidate_version_id != self.snapshot.version.id
                or not claim.effective.contains(self.snapshot.as_of)
                or not claim.knowledge.contains(self.snapshot.known_at)
            ):
                raise InvalidBookDependency("Receipt claim does not match snapshot context")
            if claim.declaration is not BookDependencyDeclaration.DECLARED_AVAILABLE:
                raise BookDependencyUnavailable("Receipt includes an unavailable claim")
        if found != set(REQUIRED_DEPENDENCIES):
            raise BookDependencyMissing("Required dependency kind is missing")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema": RECEIPT_SCHEMA,
            "candidate_version_id": str(self.snapshot.version.id),
            "candidate_snapshot_digest": self.snapshot.content_digest,
            "as_of": self.snapshot.as_of.isoformat(),
            "known_at": _instant(self.snapshot.known_at),
            "claims": [_claim_manifest(x) for x in self.selected],
            "status": "NON_AUTHORITATIVE_RND_DEPENDENCY_PREVIEW",
        }

    def verify_integrity(self) -> None:
        self.snapshot.verify_integrity()
        self._verify_claims()
        if _canonical_digest(self.canonical_payload()) != self.content_digest:
            raise BookDependencyDigestMismatch("Dependency receipt digest mismatch")


def preview_book_dependency_completeness(
    *,
    snapshot: BookConfigurationCandidateSnapshot,
    claims: tuple[BookDependencyClaim, ...],
) -> BookDependencyCandidateReadReceipt:
    """Require exactly one active, explicit claim per R&D slot on both time axes.

    All supplied records are examined, including out-of-period claims; an
    accidentally mixed tenant/version/scope catalog is rejected, not filtered.
    """
    if not isinstance(snapshot, BookConfigurationCandidateSnapshot):
        raise InvalidBookDependency("Typed candidate snapshot required")
    snapshot.verify_integrity()
    if not isinstance(claims, tuple):
        raise InvalidBookDependency("Immutable claims tuple required")
    seen_ids: set[BookDependencyClaimId] = set()
    selected: dict[BookDependencyKind, BookDependencyClaim] = {}
    for claim in claims:
        if not isinstance(claim, BookDependencyClaim):
            raise InvalidBookDependency("Catalog contains non-claim")
        if claim.id in seen_ids:
            raise BookDependencyAmbiguous("Duplicate dependency claim ID")
        seen_ids.add(claim.id)
        if (
            claim.scope != snapshot.version.scope
            or claim.candidate_version_id != snapshot.version.id
        ):
            raise InvalidBookDependency("Foreign book scope or candidate version")
        if claim.effective.contains(snapshot.as_of) and claim.knowledge.contains(
            snapshot.known_at
        ):
            if claim.kind in selected:
                raise BookDependencyAmbiguous(
                    "Multiple dependency claims active for one required kind"
                )
            selected[claim.kind] = claim

    missing = set(REQUIRED_DEPENDENCIES) - selected.keys()
    if missing:
        raise BookDependencyMissing(
            "Missing active declared dependencies: "
            + ", ".join(sorted(kind.value for kind in missing))
        )
    for claim in selected.values():
        if claim.declaration is BookDependencyDeclaration.DECLARED_UNAVAILABLE:
            raise BookDependencyUnavailable("Required dependency explicitly unavailable")
    return BookDependencyCandidateReadReceipt(
        snapshot=snapshot,
        selected=tuple(selected[kind] for kind in REQUIRED_DEPENDENCIES),
    )
