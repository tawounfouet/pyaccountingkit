"""L04-06 immutable candidate versions and deterministic bitemporal snapshots.

Pure R&D: sealed DIGEST != signature, approval, publication, or C10 authority.
All components are local unapproved drafts; nothing here can authorize posting.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from ..shared.accounting_scope import ConfigurationScope
from ..shared.effective_interval import EffectiveInterval, KnowledgeInterval
from ..shared.errors import DomainError
from ..shared.identifiers import BookCandidateVersionId
from .assignments import BookAssignmentCandidate, BookAssignmentPurpose
from .framework_bindings import ReferenceFrameworkBindingCandidate
from .model import AccountingBookDraft
from .normative_history import NormativeReferenceHistoricalPreview


class InvalidBookCandidateVersion(DomainError):
    code = "INVALID_BOOK_CANDIDATE_VERSION"


class BookCandidateVersionMissing(DomainError):
    code = "BOOK_CANDIDATE_VERSION_MISSING"


class BookCandidateVersionAmbiguous(DomainError):
    code = "BOOK_CANDIDATE_VERSION_AMBIGUOUS"


class CandidateSnapshotDigestMismatch(DomainError):
    code = "CANDIDATE_SNAPSHOT_DIGEST_MISMATCH"


CANONICALIZATION_VERSION = "l04-rnd-1"


def _instant(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _period(period: EffectiveInterval) -> dict[str, str | None]:
    return {
        "from": period.start.isoformat(),
        "to": period.end.isoformat() if period.end is not None else None,
    }


def _knowledge(interval: KnowledgeInterval) -> dict[str, str | None]:
    return {
        "from": _instant(interval.start),
        "to": _instant(interval.end) if interval.end is not None else None,
    }


def _digest(payload: dict[str, object]) -> str:
    """Versioned canonical JSON profile: UTF-8, sorted keys, fixed separators."""
    raw = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _covers(outer: EffectiveInterval, inner: EffectiveInterval) -> bool:
    return outer.start <= inner.start and (
        outer.end is None or (
            inner.end is not None and inner.end <= outer.end
        )
    )


@dataclass(frozen=True, slots=True, eq=False)
class BookConfigurationCandidateVersion:
    """Bitemporal copy of a complete *candidate* Book/Assignment/Binding triple.

    The independent version ID does not imply that an approved
    ConfigurationVersion or PublicationRecord exists.
    """

    id: BookCandidateVersionId
    book: AccountingBookDraft
    assignment: BookAssignmentCandidate
    binding: ReferenceFrameworkBindingCandidate
    purpose: BookAssignmentPurpose
    effective: EffectiveInterval
    knowledge: KnowledgeInterval
    source_ref: str
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.id, BookCandidateVersionId):
            raise InvalidBookCandidateVersion("Typed candidate version ID required")
        if not isinstance(self.book, AccountingBookDraft):
            raise InvalidBookCandidateVersion("Typed book draft required")
        if not isinstance(self.assignment, BookAssignmentCandidate):
            raise InvalidBookCandidateVersion("Typed book assignment required")
        if not isinstance(self.binding, ReferenceFrameworkBindingCandidate):
            raise InvalidBookCandidateVersion("Typed reference binding required")
        if not isinstance(self.purpose, BookAssignmentPurpose):
            raise InvalidBookCandidateVersion("Typed purpose required")
        if not isinstance(self.effective, EffectiveInterval):
            raise InvalidBookCandidateVersion("Explicit business interval required")
        if not isinstance(self.knowledge, KnowledgeInterval):
            raise InvalidBookCandidateVersion("Explicit knowledge interval required")
        if (
            not isinstance(self.source_ref, str)
            or not self.source_ref.strip()
            or self.source_ref != self.source_ref.strip()
        ):
            raise InvalidBookCandidateVersion("Trimmed candidate provenance required")
        self.assignment.require_candidate_compatibility(self.book)
        self.binding.require_draft_compatibility(self.book)
        if self.assignment.purpose != self.purpose or self.binding.purpose != self.purpose:
            raise InvalidBookCandidateVersion("Book assignment/binding purpose mismatch")
        for component in (self.book, self.assignment, self.binding):
            if not _covers(component.effective, self.effective):
                raise InvalidBookCandidateVersion(
                    "Version effective interval escapes a component's validity"
                )
        object.__setattr__(self, "content_digest", _digest(self.canonical_payload()))

    @property
    def scope(self) -> ConfigurationScope:
        return self.book.scope

    def canonical_payload(self) -> dict[str, object]:
        """No Python hashes, float amounts, implicit local dates, or 'latest'."""
        book = self.book
        return {
            "schema": CANONICALIZATION_VERSION,
            "candidate_version_id": str(self.id),
            "scope": {
                "tenant": book.scope.tenant_id,
                "company": str(book.scope.company_id),
                "legal_entity": str(book.scope.legal_entity_id),
                "book": str(book.id),
            },
            "book": {
                "code": book.code.value,
                "label": book.label,
                "currency": book.currency.value,
                "framework_code": book.framework.framework_code,
                "framework_version": book.framework.version,
                "effective": _period(book.effective),
                "source_ref": book.source_ref,
                "revision": book.revision,
            },
            "assignment": {
                "id": str(self.assignment.id),
                "effective": _period(self.assignment.effective),
                "purpose": self.assignment.purpose.value,
                "source_ref": self.assignment.source_ref,
            },
            "framework_binding": {
                "id": str(self.binding.id),
                "framework_code": self.binding.framework.framework_code,
                "framework_version": self.binding.framework.version,
                "effective": _period(self.binding.effective),
                "purpose": self.binding.purpose.value,
                "source_ref": self.binding.source_ref,
            },
            "candidate_effective": _period(self.effective),
            "candidate_knowledge": _knowledge(self.knowledge),
            "purpose": self.purpose.value,
            "source_ref": self.source_ref,
        }

    def verify_integrity(self) -> None:
        if _digest(self.canonical_payload()) != self.content_digest:
            raise CandidateSnapshotDigestMismatch("Candidate version content was altered")


@dataclass(frozen=True, slots=True, eq=False)
class BookConfigurationCandidateSnapshot:
    """A deterministic *preview receipt*, not an approved/published snapshot."""

    version: BookConfigurationCandidateVersion
    normative_claim: NormativeReferenceHistoricalPreview
    as_of: date
    known_at: datetime
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.version, BookConfigurationCandidateVersion):
            raise InvalidBookCandidateVersion("Typed candidate version required")
        if not isinstance(self.normative_claim, NormativeReferenceHistoricalPreview):
            raise InvalidBookCandidateVersion("Typed normative declaration preview required")
        if type(self.as_of) is not date:
            raise InvalidBookCandidateVersion("Business date required")
        if (
            type(self.known_at) is not datetime
            or self.known_at.tzinfo is None
            or self.known_at.utcoffset() is None
        ):
            raise InvalidBookCandidateVersion("Timezone-aware known_at required")
        if (
            self.normative_claim.framework != self.version.binding.framework
            or self.normative_claim.as_of != self.as_of
            or _instant(self.normative_claim.known_at) != _instant(self.known_at)
            or not self.version.effective.contains(self.as_of)
            or not self.version.knowledge.contains(self.known_at)
        ):
            raise InvalidBookCandidateVersion("Historical components do not match query")
        self.version.verify_integrity()
        object.__setattr__(self, "content_digest", _digest(self.canonical_payload()))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema": CANONICALIZATION_VERSION,
            "candidate_version_id": str(self.version.id),
            "candidate_version_digest": self.version.content_digest,
            "normative_statement_id": str(self.normative_claim.statement_id),
            "normative_source": self.normative_claim.source.value,
            "normative_source_ref": self.normative_claim.source_ref,
            "normative_framework_code": self.normative_claim.framework.framework_code,
            "normative_framework_version": self.normative_claim.framework.version,
            "as_of": self.as_of.isoformat(),
            "known_at": _instant(self.known_at),
            "status": "NON_AUTHORITATIVE_RND_CANDIDATE",
        }

    def verify_integrity(self) -> None:
        self.version.verify_integrity()
        if _digest(self.canonical_payload()) != self.content_digest:
            raise CandidateSnapshotDigestMismatch("Candidate snapshot content was altered")


def select_book_candidate_version(
    *,
    scope: ConfigurationScope,
    purpose: BookAssignmentPurpose,
    as_of: date,
    known_at: datetime,
    versions: tuple[BookConfigurationCandidateVersion, ...],
) -> BookConfigurationCandidateVersion:
    """Select exactly one candidate with two time axes; never a published query."""
    if not isinstance(scope, ConfigurationScope) or scope.book_id is None:
        raise InvalidBookCandidateVersion("Explicit book-level scope required")
    if not isinstance(purpose, BookAssignmentPurpose):
        raise InvalidBookCandidateVersion("Typed purpose required")
    if type(as_of) is not date:
        raise InvalidBookCandidateVersion("Business date required")
    if (
        type(known_at) is not datetime
        or known_at.tzinfo is None
        or known_at.utcoffset() is None
    ):
        raise InvalidBookCandidateVersion("Timezone-aware known_at required")
    if not isinstance(versions, tuple):
        raise InvalidBookCandidateVersion("Versions must be an immutable tuple")

    seen: set[BookCandidateVersionId] = set()
    selected: BookConfigurationCandidateVersion | None = None
    for version in versions:
        if not isinstance(version, BookConfigurationCandidateVersion):
            raise InvalidBookCandidateVersion("Catalog contains a non-version")
        if version.scope != scope:
            raise InvalidBookCandidateVersion("Candidate catalog leaked foreign scope")
        if version.id in seen:
            raise BookCandidateVersionAmbiguous("Duplicate candidate version identity")
        seen.add(version.id)
        version.verify_integrity()
        if (
            version.purpose == purpose
            and version.effective.contains(as_of)
            and version.knowledge.contains(known_at)
        ):
            if selected is not None:
                raise BookCandidateVersionAmbiguous("Concurrent versions at as_of/known_at")
            selected = version
    if selected is None:
        raise BookCandidateVersionMissing("No candidate at business and knowledge date")
    return selected
