"""L05-03: bitemporal chart *candidates* and version-pinned book binding previews.

No published CompanyChartVersion, verified Normative Layer, live L04 book,
signed C10 receipt, IAM proof, SQL transaction or permission to post.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from ..shared.accounting_scope import ConfigurationScope
from ..shared.effective_interval import EffectiveInterval, KnowledgeInterval
from ..shared.errors import DomainError
from ..shared.identifiers import (
    BookChartBindingCandidateId,
    CompanyChartCandidateVersionId,
)
from ..shared.references import ReferenceFrameworkRef
from .bookability import AccountStatusCandidate
from .hierarchy import (
    AccountHierarchyEdgeCandidate,
    validate_candidate_account_hierarchy,
)
from .model import CompanyAccountDraft, CompanyChartDraft


class InvalidChartCandidateVersion(DomainError):
    code = "INVALID_CHART_CANDIDATE_VERSION"


class InvalidBookChartBinding(DomainError):
    code = "INVALID_BOOK_CHART_BINDING"


class BookChartCandidateMissing(DomainError):
    code = "BOOK_CHART_CANDIDATE_MISSING"


class BookChartCandidateAmbiguous(DomainError):
    code = "BOOK_CHART_CANDIDATE_AMBIGUOUS"


class ChartCandidateDigestMismatch(DomainError):
    code = "CHART_CANDIDATE_DIGEST_MISMATCH"


class ChartFrameworkClaimMismatch(DomainError):
    code = "CHART_FRAMEWORK_CLAIM_MISMATCH"


SCHEMA = "l05-rnd-candidate-v1"


def _timestamp(instant: datetime) -> str:
    return instant.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _validity(value: EffectiveInterval) -> dict[str, str | None]:
    return {"start": value.start.isoformat(),
            "end": value.end.isoformat() if value.end else None}


def _knowledge(value: KnowledgeInterval) -> dict[str, str | None]:
    return {"start": _timestamp(value.start),
            "end": _timestamp(value.end) if value.end else None}


def _covers(outer: EffectiveInterval, inner: EffectiveInterval) -> bool:
    return outer.start <= inner.start and (
        outer.end is None or (inner.end is not None and inner.end <= outer.end)
    )


def _hash(data: dict[str, object]) -> str:
    payload = json.dumps(
        data, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _scope(scope: ConfigurationScope) -> dict[str, str]:
    return {
        "tenant": scope.tenant_id,
        "company": str(scope.company_id),
        "legal_entity": str(scope.legal_entity_id),
        "book": str(scope.book_id) if scope.book_id is not None else "",
    }


def _ref(value: ReferenceFrameworkRef) -> dict[str, str]:
    return {"code": value.framework_code, "version": value.version}


def _code(value: str) -> None:
    if not isinstance(value, str) or re.fullmatch(
        r"[A-Z][A-Z0-9_-]{0,31}", value
    ) is None:
        raise InvalidBookChartBinding("Canonical uppercase chart-use code required")


@dataclass(frozen=True, slots=True)
class BookChartPurpose:
    """Provisional book usage key, distinct from absent unmerged L04 types."""

    value: str

    def __post_init__(self) -> None:
        _code(self.value)


@dataclass(frozen=True, slots=True, eq=False)
class CompanyChartVersionCandidate:
    """Unpublished, immutable-in-Python bundle of chart/account/graph candidates."""

    id: CompanyChartCandidateVersionId
    chart: CompanyChartDraft
    accounts: tuple[CompanyAccountDraft, ...]
    edges: tuple[AccountHierarchyEdgeCandidate, ...]
    statuses: tuple[AccountStatusCandidate, ...]
    declared_framework: ReferenceFrameworkRef
    effective: EffectiveInterval
    knowledge: KnowledgeInterval
    source_ref: str
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.id, CompanyChartCandidateVersionId):
            raise InvalidChartCandidateVersion("Typed candidate version ID required")
        if not isinstance(self.chart, CompanyChartDraft):
            raise InvalidChartCandidateVersion("Typed chart draft required")
        if not isinstance(self.declared_framework, ReferenceFrameworkRef):
            raise InvalidChartCandidateVersion("Explicit versioned framework claim required")
        if not isinstance(self.effective, EffectiveInterval) or not isinstance(
            self.knowledge, KnowledgeInterval
        ):
            raise InvalidChartCandidateVersion("Business and knowledge windows required")
        if not isinstance(self.source_ref, str) or not self.source_ref.strip() or (
            self.source_ref != self.source_ref.strip()
        ):
            raise InvalidChartCandidateVersion("Trimmed candidate provenance required")
        if not _covers(self.chart.effective, self.effective):
            raise InvalidChartCandidateVersion("Version validity escapes draft chart")
        validate_candidate_account_hierarchy(
            chart=self.chart, accounts=self.accounts, edges=self.edges
        )
        if not isinstance(self.statuses, tuple):
            raise InvalidChartCandidateVersion("Immutable status tuple required")
        ids = set()
        by_id = {account.id: account for account in self.accounts}
        by_account: dict[object, list[AccountStatusCandidate]] = {}
        for status in self.statuses:
            if not isinstance(status, AccountStatusCandidate):
                raise InvalidChartCandidateVersion("Non-status in version manifest")
            if status.id in ids:
                raise InvalidChartCandidateVersion("Duplicate status candidate ID")
            ids.add(status.id)
            account = by_id.get(status.account_id)
            if (
                account is None
                or status.chart_id != self.chart.id
                or status.scope != self.chart.scope
                or not _covers(account.effective, status.effective)
            ):
                raise InvalidChartCandidateVersion("Foreign/orphan/out-of-range account status")
            previous = by_account.setdefault(status.account_id, [])
            if any(old.effective.overlaps(status.effective) for old in previous):
                raise InvalidChartCandidateVersion("Overlapping statuses in chart version")
            previous.append(status)
        object.__setattr__(self, "content_digest", _hash(self.canonical_manifest()))

    def canonical_manifest(self) -> dict[str, object]:
        """Canonical sorted full content; a checksum, never a signature."""
        chart = self.chart
        return {
            "schema": SCHEMA,
            "id": str(self.id),
            "chart": {
                "id": str(chart.id), "scope": _scope(chart.scope),
                "code": chart.code.value, "label": chart.label,
                "effective": _validity(chart.effective),
                "revision": chart.revision, "source_ref": chart.source_ref,
            },
            "declared_framework": _ref(self.declared_framework),
            "effective": _validity(self.effective),
            "knowledge": _knowledge(self.knowledge),
            "source_ref": self.source_ref,
            "accounts": [
                {
                    "id": str(a.id), "chart_id": str(a.chart_id),
                    "scope": _scope(a.scope), "code": a.code.value,
                    "label": a.label, "class": a.classification.value,
                    "postable": a.postable, "effective": _validity(a.effective),
                    "revision": a.revision, "source_ref": a.source_ref,
                }
                for a in sorted(self.accounts, key=lambda x: str(x.id))
            ],
            "edges": [
                {
                    "id": str(e.id), "scope": _scope(e.scope),
                    "chart_id": str(e.chart_id), "view": e.view.value,
                    "child": str(e.child_id), "parent": str(e.parent_id),
                    "effective": _validity(e.effective), "source_ref": e.source_ref,
                }
                for e in sorted(self.edges, key=lambda x: str(x.id))
            ],
            "statuses": [
                {
                    "id": str(s.id), "scope": _scope(s.scope),
                    "chart_id": str(s.chart_id), "account_id": str(s.account_id),
                    "status": s.status.value, "effective": _validity(s.effective),
                    "source_ref": s.source_ref,
                }
                for s in sorted(self.statuses, key=lambda x: str(x.id))
            ],
        }

    def verify_integrity(self) -> None:
        if _hash(self.canonical_manifest()) != self.content_digest:
            raise ChartCandidateDigestMismatch("Chart candidate manifest was altered")


@dataclass(frozen=True, slots=True)
class BookChartBindingCandidate:
    """Dated claimed book → exact chart-version link, NOT legal book ownership."""

    id: BookChartBindingCandidateId
    book_scope: ConfigurationScope
    purpose: BookChartPurpose
    chart_id: object
    chart_version_id: CompanyChartCandidateVersionId
    declared_book_framework: ReferenceFrameworkRef
    effective: EffectiveInterval
    knowledge: KnowledgeInterval
    source_ref: str

    def __post_init__(self) -> None:
        from ..shared.identifiers import CompanyChartId

        if not isinstance(self.id, BookChartBindingCandidateId):
            raise InvalidBookChartBinding("Typed binding candidate ID required")
        if not isinstance(self.book_scope, ConfigurationScope) or (
            self.book_scope.book_id is None
        ):
            raise InvalidBookChartBinding("Explicit book-level scope required")
        if not isinstance(self.purpose, BookChartPurpose):
            raise InvalidBookChartBinding("Typed book-chart purpose required")
        if not isinstance(self.chart_id, CompanyChartId):
            raise InvalidBookChartBinding("Typed chart ID required")
        if not isinstance(self.chart_version_id, CompanyChartCandidateVersionId):
            raise InvalidBookChartBinding("Typed exact chart version ID required")
        if not isinstance(self.declared_book_framework, ReferenceFrameworkRef):
            raise InvalidBookChartBinding("Typed versioned book framework claim required")
        if not isinstance(self.effective, EffectiveInterval) or not isinstance(
            self.knowledge, KnowledgeInterval
        ):
            raise InvalidBookChartBinding("Effective and knowledge intervals required")
        if not isinstance(self.source_ref, str) or not self.source_ref.strip() or (
            self.source_ref != self.source_ref.strip()
        ):
            raise InvalidBookChartBinding("Canonical source_ref required")


@dataclass(frozen=True, slots=True, eq=False)
class BookChartCandidateReadReceipt:
    """Deterministic SHA-256 preview binding, never a signed C10 receipt."""

    binding: BookChartBindingCandidate
    chart_version: CompanyChartVersionCandidate
    as_of: date
    known_at: datetime
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.binding, BookChartBindingCandidate) or not isinstance(
            self.chart_version, CompanyChartVersionCandidate
        ):
            raise InvalidBookChartBinding("Typed candidate binding and chart version required")
        if type(self.as_of) is not date or (
            type(self.known_at) is not datetime
            or self.known_at.tzinfo is None
            or self.known_at.utcoffset() is None
        ):
            raise InvalidBookChartBinding("Business date and aware knowledge instant required")
        self.chart_version.verify_integrity()
        self._validate_relation()
        object.__setattr__(self, "content_digest", _hash(self.canonical_manifest()))

    def _validate_relation(self) -> None:
        b, v = self.binding, self.chart_version
        scope = v.chart.scope
        if (
            b.chart_id != v.chart.id or b.chart_version_id != v.id
            or b.book_scope.tenant_id != scope.tenant_id
            or b.book_scope.company_id != scope.company_id
            or b.book_scope.legal_entity_id != scope.legal_entity_id
            or not _covers(v.effective, b.effective)
            or not b.effective.contains(self.as_of)
            or not b.knowledge.contains(self.known_at)
            or not v.knowledge.contains(self.known_at)
        ):
            raise InvalidBookChartBinding("Binding and chart version temporal/scope mismatch")
        if b.declared_book_framework != v.declared_framework:
            raise ChartFrameworkClaimMismatch(
                "Declared chart and book framework editions differ"
            )

    def canonical_manifest(self) -> dict[str, object]:
        b = self.binding
        return {
            "schema": SCHEMA, "status": "UNPUBLISHED_RND_PREVIEW",
            "binding_id": str(b.id), "book_scope": _scope(b.book_scope),
            "purpose": b.purpose.value,
            "chart_id": str(b.chart_id), "chart_version_id": str(b.chart_version_id),
            "book_framework_claim": _ref(b.declared_book_framework),
            "binding_effective": _validity(b.effective),
            "binding_knowledge": _knowledge(b.knowledge),
            "binding_source_ref": b.source_ref,
            "chart_digest": self.chart_version.content_digest,
            "as_of": self.as_of.isoformat(), "known_at": _timestamp(self.known_at),
        }

    def verify_integrity(self) -> None:
        self.chart_version.verify_integrity()
        self._validate_relation()
        if _hash(self.canonical_manifest()) != self.content_digest:
            raise ChartCandidateDigestMismatch("Book-chart preview receipt altered")


def preview_book_chart_candidate(
    *, book_scope: ConfigurationScope, purpose: BookChartPurpose,
    as_of: date, known_at: datetime,
    bindings: tuple[BookChartBindingCandidate, ...],
    chart_versions: tuple[CompanyChartVersionCandidate, ...],
) -> BookChartCandidateReadReceipt:
    """Fail closed: exact book, purpose, time, chart version and framework claim."""
    if not isinstance(book_scope, ConfigurationScope) or book_scope.book_id is None:
        raise InvalidBookChartBinding("Typed book scope required")
    if not isinstance(purpose, BookChartPurpose) or type(as_of) is not date:
        raise InvalidBookChartBinding("Typed purpose and business date required")
    if (
        type(known_at) is not datetime or known_at.tzinfo is None
        or known_at.utcoffset() is None
    ):
        raise InvalidBookChartBinding("Aware known_at required")
    if not isinstance(bindings, tuple) or not isinstance(chart_versions, tuple):
        raise InvalidBookChartBinding("Immutable catalog tuples required")

    seen_bindings: set[BookChartBindingCandidateId] = set()
    active: list[BookChartBindingCandidate] = []
    for b in bindings:
        if not isinstance(b, BookChartBindingCandidate):
            raise InvalidBookChartBinding("Catalog contains non-binding")
        if b.id in seen_bindings:
            raise BookChartCandidateAmbiguous("Repeated binding identity")
        seen_bindings.add(b.id)
        if b.book_scope != book_scope:
            raise InvalidBookChartBinding("Foreign book scope in binding catalog")
        if b.purpose == purpose and b.effective.contains(as_of) and (
            b.knowledge.contains(known_at)
        ):
            active.append(b)
    if not active:
        raise BookChartCandidateMissing("No dated book chart binding for request")
    if len(active) != 1:
        raise BookChartCandidateAmbiguous("Concurrent active book chart bindings")
    binding = active[0]
    versions: dict[CompanyChartCandidateVersionId, CompanyChartVersionCandidate] = {}
    for v in chart_versions:
        if not isinstance(v, CompanyChartVersionCandidate):
            raise InvalidChartCandidateVersion("Catalog contains non-version")
        if (
            v.chart.scope.tenant_id != book_scope.tenant_id
            or v.chart.scope.company_id != book_scope.company_id
            or v.chart.scope.legal_entity_id != book_scope.legal_entity_id
        ):
            raise InvalidChartCandidateVersion("Foreign chart version scope in catalog")
        if v.id in versions:
            raise BookChartCandidateAmbiguous("Repeated chart version identity")
        v.verify_integrity()
        versions[v.id] = v
    candidate = versions.get(binding.chart_version_id)
    if candidate is None:
        raise BookChartCandidateMissing("Bound exact chart version is not available")
    return BookChartCandidateReadReceipt(
        binding=binding, chart_version=candidate, as_of=as_of, known_at=known_at
    )
