"""L05-04: typed mapping-set candidate snapshots and pure account resolution.

Only 1:1 and N:1 declarative correspondences. A mapping NEVER allocates
money, journals entries, certifies accounts or posts to a Ledger.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import Enum

from ..shared.accounting_scope import ConfigurationScope
from ..shared.effective_interval import EffectiveInterval, KnowledgeInterval
from ..shared.errors import DomainError
from ..shared.identifiers import (
    AccountMappingCandidateId,
    CompanyAccountId,
    CompanyChartCandidateVersionId,
    MappingSetCandidateVersionId,
)
from .versions_bindings import CompanyChartVersionCandidate


class InvalidMappingCandidate(DomainError):
    code = "INVALID_ACCOUNT_MAPPING_CANDIDATE"


class MappingCandidateMissing(DomainError):
    code = "ACCOUNT_MAPPING_CANDIDATE_MISSING"


class MappingCandidateAmbiguous(DomainError):
    code = "ACCOUNT_MAPPING_CANDIDATE_AMBIGUOUS"


class MappingCandidateDigestMismatch(DomainError):
    code = "ACCOUNT_MAPPING_CANDIDATE_DIGEST_MISMATCH"


class MappingKind(Enum):
    DIRECT_ONE_TO_ONE = "DIRECT_ONE_TO_ONE"
    AGGREGATE_MANY_TO_ONE = "AGGREGATE_MANY_TO_ONE"


class MappingPrecedencePolicy(Enum):
    """Provisional R&D policy, not approved ADR-COA-06 or published priority."""

    REQUIRE_UNIQUE = "REQUIRE_UNIQUE"
    EXPLICIT_PRIORITY_RND = "EXPLICIT_PRIORITY_RND"


SCHEMA = "l05-rnd-mapping-v1"


def _effective(value: EffectiveInterval) -> dict[str, str | None]:
    return {
        "start": value.start.isoformat(),
        "end": value.end.isoformat() if value.end is not None else None,
    }


def _aware(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _knowledge(value: KnowledgeInterval) -> dict[str, str | None]:
    return {
        "start": _aware(value.start),
        "end": _aware(value.end) if value.end is not None else None,
    }


def _scope(value: ConfigurationScope) -> dict[str, str]:
    return {
        "tenant": value.tenant_id,
        "company": str(value.company_id),
        "entity": str(value.legal_entity_id),
    }


def _contains_period(outer: EffectiveInterval, inner: EffectiveInterval) -> bool:
    return outer.start <= inner.start and (
        outer.end is None or (inner.end is not None and inner.end <= outer.end)
    )


def _contains_knowledge(outer: KnowledgeInterval, inner: KnowledgeInterval) -> bool:
    return outer.start <= inner.start and (
        outer.end is None or (inner.end is not None and inner.end <= outer.end)
    )


def _digest(manifest: dict[str, object]) -> str:
    raw = json.dumps(
        manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class AccountMappingCandidate:
    """One source account → exactly ONE target account (no 1:N allocations)."""

    id: AccountMappingCandidateId
    mapping_set_version_id: MappingSetCandidateVersionId
    scope: ConfigurationScope
    source_chart_version_id: CompanyChartCandidateVersionId
    source_account_id: CompanyAccountId
    target_chart_version_id: CompanyChartCandidateVersionId
    target_account_id: CompanyAccountId
    kind: MappingKind
    effective: EffectiveInterval
    source_ref: str
    priority: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, AccountMappingCandidateId):
            raise InvalidMappingCandidate("Typed mapping identity required")
        if not isinstance(self.mapping_set_version_id, MappingSetCandidateVersionId):
            raise InvalidMappingCandidate("Typed mapping set version ID required")
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is not None:
            raise InvalidMappingCandidate("Entity-level mapping scope required")
        if not isinstance(self.source_chart_version_id, CompanyChartCandidateVersionId):
            raise InvalidMappingCandidate("Typed source chart version required")
        if not isinstance(self.target_chart_version_id, CompanyChartCandidateVersionId):
            raise InvalidMappingCandidate("Typed target chart version required")
        if (
            not isinstance(self.source_account_id, CompanyAccountId)
            or not isinstance(self.target_account_id, CompanyAccountId)
        ):
            raise InvalidMappingCandidate("Typed source/target account IDs required")
        if not isinstance(self.kind, MappingKind):
            raise InvalidMappingCandidate("Typed mapping kind required; 1:N unsupported")
        if not isinstance(self.effective, EffectiveInterval):
            raise InvalidMappingCandidate("Business validity interval required")
        if not isinstance(self.source_ref, str) or not self.source_ref.strip() or (
            self.source_ref != self.source_ref.strip()
        ):
            raise InvalidMappingCandidate("Trimmed mapping provenance required")
        if self.priority is not None and (
            type(self.priority) is not int or self.priority < 0
        ):
            raise InvalidMappingCandidate("Explicit nonnegative integer priority required")


def _mapping_manifest(item: AccountMappingCandidate) -> dict[str, object]:
    return {
        "id": str(item.id),
        "set_version_id": str(item.mapping_set_version_id),
        "scope": _scope(item.scope),
        "source_chart_version_id": str(item.source_chart_version_id),
        "source_account_id": str(item.source_account_id),
        "target_chart_version_id": str(item.target_chart_version_id),
        "target_account_id": str(item.target_account_id),
        "kind": item.kind.value,
        "effective": _effective(item.effective),
        "source_ref": item.source_ref,
        "priority": item.priority,
    }


@dataclass(frozen=True, slots=True, eq=False)
class MappingSetVersionCandidate:
    """Coherent mapping catalog pinned to two exact *candidate* chart versions."""

    id: MappingSetCandidateVersionId
    scope: ConfigurationScope
    source_chart: CompanyChartVersionCandidate
    target_chart: CompanyChartVersionCandidate
    mappings: tuple[AccountMappingCandidate, ...]
    precedence: MappingPrecedencePolicy
    effective: EffectiveInterval
    knowledge: KnowledgeInterval
    source_ref: str
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.id, MappingSetCandidateVersionId):
            raise InvalidMappingCandidate("Typed mapping-set version ID required")
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is not None:
            raise InvalidMappingCandidate("Explicit entity-level mapping scope required")
        if not isinstance(self.source_chart, CompanyChartVersionCandidate) or not isinstance(
            self.target_chart, CompanyChartVersionCandidate
        ):
            raise InvalidMappingCandidate("Two exact chart candidate versions required")
        if not isinstance(self.mappings, tuple) or any(
            not isinstance(m, AccountMappingCandidate) for m in self.mappings
        ):
            raise InvalidMappingCandidate("Immutable typed mapping tuple required")
        if not isinstance(self.precedence, MappingPrecedencePolicy):
            raise InvalidMappingCandidate("Explicit precedence policy required")
        if not isinstance(self.effective, EffectiveInterval) or not isinstance(
            self.knowledge, KnowledgeInterval
        ):
            raise InvalidMappingCandidate("Business and knowledge windows required")
        if not isinstance(self.source_ref, str) or not self.source_ref.strip() or (
            self.source_ref != self.source_ref.strip()
        ):
            raise InvalidMappingCandidate("Trimmed mapping-set source required")
        self.source_chart.verify_integrity()
        self.target_chart.verify_integrity()
        for version in (self.source_chart, self.target_chart):
            if version.chart.scope != self.scope:
                raise InvalidMappingCandidate("Cross-tenant/entity chart candidate")
            if not _contains_period(version.effective, self.effective):
                raise InvalidMappingCandidate("Mapping set exceeds chart validity")
            if not _contains_knowledge(version.knowledge, self.knowledge):
                raise InvalidMappingCandidate("Mapping set exceeds chart knowledge window")

        source_accounts = {a.id: a for a in self.source_chart.accounts}
        target_accounts = {a.id: a for a in self.target_chart.accounts}
        seen: set[AccountMappingCandidateId] = set()
        for m in self.mappings:
            if m.id in seen:
                raise MappingCandidateAmbiguous("Duplicate mapping identity")
            seen.add(m.id)
            if (
                m.mapping_set_version_id != self.id or m.scope != self.scope
                or m.source_chart_version_id != self.source_chart.id
                or m.target_chart_version_id != self.target_chart.id
            ):
                raise InvalidMappingCandidate("Mapping version or accounting scope mismatch")
            sa = source_accounts.get(m.source_account_id)
            ta = target_accounts.get(m.target_account_id)
            if sa is None or ta is None:
                raise InvalidMappingCandidate("Mapping source/target account absent in version")
            if not all(
                _contains_period(period, m.effective)
                for period in (self.effective, sa.effective, ta.effective)
            ):
                raise InvalidMappingCandidate("Mapping validity exceeds account/set period")
            if self.precedence is MappingPrecedencePolicy.REQUIRE_UNIQUE:
                if m.priority is not None:
                    raise InvalidMappingCandidate("Priority without explicit policy forbidden")
            elif m.priority is None:
                raise InvalidMappingCandidate("Explicit-priority policy requires every rank")

        # A DIRECT rule is a claim of 1:1 semantics, not a permitted N:1
        # aggregation. Overlapping different sources to one target must all
        # explicitly be AGGREGATE_MANY_TO_ONE.
        for i, left in enumerate(self.mappings):
            for right in self.mappings[i + 1:]:
                if (
                    left.target_account_id == right.target_account_id
                    and left.source_account_id != right.source_account_id
                    and left.effective.overlaps(right.effective)
                    and (left.kind is not MappingKind.AGGREGATE_MANY_TO_ONE
                         or right.kind is not MappingKind.AGGREGATE_MANY_TO_ONE)
                ):
                    raise InvalidMappingCandidate(
                        "N:1 correspondence requires explicit AGGREGATE_MANY_TO_ONE"
                    )
        object.__setattr__(self, "content_digest", _digest(self.canonical_manifest()))

    def canonical_manifest(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "status": "UNPUBLISHED_RND_MAPPING_CANDIDATE",
            "id": str(self.id), "scope": _scope(self.scope),
            "source_chart_version_id": str(self.source_chart.id),
            "source_chart_digest": self.source_chart.content_digest,
            "target_chart_version_id": str(self.target_chart.id),
            "target_chart_digest": self.target_chart.content_digest,
            "precedence": self.precedence.value,
            "effective": _effective(self.effective),
            "knowledge": _knowledge(self.knowledge),
            "source_ref": self.source_ref,
            "mappings": [
                _mapping_manifest(m) for m in sorted(self.mappings, key=lambda x: str(x.id))
            ],
        }

    def verify_integrity(self) -> None:
        self.source_chart.verify_integrity()
        self.target_chart.verify_integrity()
        if _digest(self.canonical_manifest()) != self.content_digest:
            raise MappingCandidateDigestMismatch("Mapping set content or lineage mutated")


@dataclass(frozen=True, slots=True, eq=False)
class AccountMappingCandidateResolution:
    """One chosen mapping, NO amount or accounting instruction."""

    mapping_set: MappingSetVersionCandidate
    mapping: AccountMappingCandidate
    as_of: date
    known_at: datetime
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.mapping_set, MappingSetVersionCandidate) or not isinstance(
            self.mapping, AccountMappingCandidate
        ):
            raise InvalidMappingCandidate("Typed set and mapping required")
        if type(self.as_of) is not date or type(self.known_at) is not datetime or (
            self.known_at.tzinfo is None or self.known_at.utcoffset() is None
        ):
            raise InvalidMappingCandidate("Business date and aware instant required")
        self.mapping_set.verify_integrity()
        if (
            not any(m is self.mapping for m in self.mapping_set.mappings)
            or not self.mapping_set.effective.contains(self.as_of)
            or not self.mapping_set.knowledge.contains(self.known_at)
            or not self.mapping.effective.contains(self.as_of)
        ):
            raise InvalidMappingCandidate("Resolution references non-applicable rule")
        object.__setattr__(self, "content_digest", _digest(self.canonical_manifest()))

    def canonical_manifest(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "status": "UNPUBLISHED_RND_MAPPING_RESOLUTION",
            "mapping_set_version_id": str(self.mapping_set.id),
            "mapping_set_digest": self.mapping_set.content_digest,
            "mapping_id": str(self.mapping.id),
            "mapping_source_ref": self.mapping.source_ref,
            "source_account_id": str(self.mapping.source_account_id),
            "target_account_id": str(self.mapping.target_account_id),
            "kind": self.mapping.kind.value,
            "as_of": self.as_of.isoformat(), "known_at": _aware(self.known_at),
        }

    def verify_integrity(self) -> None:
        self.mapping_set.verify_integrity()
        if _digest(self.canonical_manifest()) != self.content_digest:
            raise MappingCandidateDigestMismatch("Resolution content modified")


def resolve_account_mapping_candidate(
    *,
    scope: ConfigurationScope,
    source_account_id: CompanyAccountId,
    as_of: date,
    known_at: datetime,
    mapping_sets: tuple[MappingSetVersionCandidate, ...],
) -> AccountMappingCandidateResolution:
    """One date/knowledge-specific source→target; never 1:N monetary splitting."""
    if not isinstance(scope, ConfigurationScope) or scope.book_id is not None:
        raise InvalidMappingCandidate("Entity-level typed scope required")
    if not isinstance(source_account_id, CompanyAccountId) or type(as_of) is not date:
        raise InvalidMappingCandidate("Typed source account and business date required")
    if type(known_at) is not datetime or known_at.tzinfo is None or (
        known_at.utcoffset() is None
    ):
        raise InvalidMappingCandidate("Aware knowledge cutoff required")
    if not isinstance(mapping_sets, tuple):
        raise InvalidMappingCandidate("Immutable mapping-set catalog required")
    seen: set[MappingSetCandidateVersionId] = set()
    active: list[MappingSetVersionCandidate] = []
    for candidate in mapping_sets:
        if not isinstance(candidate, MappingSetVersionCandidate):
            raise InvalidMappingCandidate("Catalog contains non-mapping set")
        if candidate.id in seen:
            raise MappingCandidateAmbiguous("Duplicate mapping-set version identity")
        seen.add(candidate.id)
        if candidate.scope != scope:
            raise InvalidMappingCandidate("Foreign mapping-set scope")
        candidate.verify_integrity()
        if candidate.effective.contains(as_of) and candidate.knowledge.contains(known_at):
            active.append(candidate)
    if not active:
        raise MappingCandidateMissing("No applicable mapping-set candidate")
    if len(active) != 1:
        raise MappingCandidateAmbiguous("Concurrent active mapping-set versions")
    chosen = active[0]
    matches = [
        m for m in chosen.mappings
        if m.source_account_id == source_account_id and m.effective.contains(as_of)
    ]
    if not matches:
        raise MappingCandidateMissing("No explicit candidate mapping for source account")
    if len(matches) > 1:
        if chosen.precedence is MappingPrecedencePolicy.REQUIRE_UNIQUE:
            raise MappingCandidateAmbiguous("Multiple source mappings, no precedence policy")
        highest = max(m.priority for m in matches if m.priority is not None)
        matches = [m for m in matches if m.priority == highest]
        if len(matches) != 1:
            raise MappingCandidateAmbiguous("Equal-priority candidate mappings")
    return AccountMappingCandidateResolution(
        mapping_set=chosen, mapping=matches[0], as_of=as_of, known_at=known_at
    )
