"""L05-05: descriptive specialized-provider requirement; NEVER invoke a provider.

Provider capabilities are opaque versioned declarations: there is no Callable,
amount, allocation function, journal line, remote port or execution gateway.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum

from ..shared.effective_interval import EffectiveInterval, KnowledgeInterval
from ..shared.identifiers import CompanyAccountId, CompanyChartCandidateVersionId
from .mapping import (
    InvalidMappingCandidate,
    MappingCandidateDigestMismatch,
    MappingSetVersionCandidate,
    _contains_knowledge,
    _contains_period,
    _digest,
    _effective,
    _knowledge,
)


class MappingProviderRequired(InvalidMappingCandidate):
    code = "MAPPING_REQUIRES_PROVIDER"


class ProviderCapability(Enum):
    ONE_TO_MANY_ALLOCATION = "ONE_TO_MANY_ALLOCATION"
    RECLASSIFICATION = "RECLASSIFICATION"


def _key(s: str) -> bool:
    return isinstance(s, str) and bool(re.fullmatch(r"[A-Z][A-Z0-9_-]{0,63}", s))


@dataclass(frozen=True, slots=True)
class SpecializedMappingProviderContract:
    """Typed *descriptor* with no money or execution behavior."""

    provider_code: str
    provider_version: str
    capability: ProviderCapability
    input_schema: str
    output_schema: str

    def __post_init__(self) -> None:
        if (
            not _key(self.provider_code)
            or not isinstance(self.provider_version, str)
            or not self.provider_version.strip()
            or self.provider_version != self.provider_version.strip()
            or not isinstance(self.capability, ProviderCapability)
            or not _key(self.input_schema)
            or not _key(self.output_schema)
        ):
            raise InvalidMappingCandidate("Typed versioned provider contract required")


@dataclass(frozen=True, slots=True, eq=False)
class MappingProviderRequirementCandidate:
    """Unfulfilled requirement pinned to one mapping-set version and its accounts."""

    mapping_set: MappingSetVersionCandidate
    source_account_id: CompanyAccountId
    target_account_ids: tuple[CompanyAccountId, ...]
    provider: SpecializedMappingProviderContract
    effective: EffectiveInterval
    knowledge: KnowledgeInterval
    source_ref: str
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.mapping_set, MappingSetVersionCandidate):
            raise InvalidMappingCandidate("Typed mapping-set candidate required")
        if not isinstance(self.source_account_id, CompanyAccountId):
            raise InvalidMappingCandidate("Typed source account required")
        if (
            not isinstance(self.target_account_ids, tuple)
            or len(self.target_account_ids) < 2
            or any(not isinstance(v, CompanyAccountId) for v in self.target_account_ids)
            or len(set(self.target_account_ids)) != len(self.target_account_ids)
        ):
            raise InvalidMappingCandidate("1:N requires at least two distinct typed targets")
        if not isinstance(self.provider, SpecializedMappingProviderContract):
            raise InvalidMappingCandidate("Explicit provider descriptor required")
        if self.provider.capability is not ProviderCapability.ONE_TO_MANY_ALLOCATION:
            raise InvalidMappingCandidate("1:N requirement needs allocation provider descriptor")
        if not isinstance(self.effective, EffectiveInterval) or not isinstance(
            self.knowledge, KnowledgeInterval
        ):
            raise InvalidMappingCandidate("Explicit provider time windows required")
        if not isinstance(self.source_ref, str) or not self.source_ref.strip() or (
            self.source_ref != self.source_ref.strip()
        ):
            raise InvalidMappingCandidate("Nonempty trimmed requirement provenance required")
        self.mapping_set.verify_integrity()
        if not _contains_period(self.mapping_set.effective, self.effective) or not (
            _contains_knowledge(self.mapping_set.knowledge, self.knowledge)
        ):
            raise InvalidMappingCandidate("Provider requirement exceeds mapping-set windows")
        sources = {a.id: a for a in self.mapping_set.source_chart.accounts}
        targets = {a.id: a for a in self.mapping_set.target_chart.accounts}
        if (
            self.source_account_id not in sources
            or not set(self.target_account_ids) <= targets.keys()
        ):
            raise InvalidMappingCandidate("Provider requirement account absent in pinned charts")
        for account in (sources[self.source_account_id], *(
            targets[account_id] for account_id in self.target_account_ids
        )):
            if not _contains_period(account.effective, self.effective):
                raise InvalidMappingCandidate(
                    "Provider requirement extends beyond referenced account validity"
                )
        if any(
            m.source_account_id == self.source_account_id
            and m.effective.overlaps(self.effective)
            for m in self.mapping_set.mappings
        ):
            raise InvalidMappingCandidate("1:N provider intent conflicts with direct mappings")
        object.__setattr__(self, "content_digest", _digest(self.canonical_manifest()))

    @property
    def source_chart_version_id(self) -> CompanyChartCandidateVersionId:
        return self.mapping_set.source_chart.id

    @property
    def target_chart_version_id(self) -> CompanyChartCandidateVersionId:
        return self.mapping_set.target_chart.id

    def canonical_manifest(self) -> dict[str, object]:
        return {
            "schema": "l05-provider-intent-rnd-v1",
            "status": "MAPPING_REQUIRES_PROVIDER_UNFULFILLED",
            "mapping_set_id": str(self.mapping_set.id),
            "mapping_set_digest": self.mapping_set.content_digest,
            "source_chart_version_id": str(self.source_chart_version_id),
            "target_chart_version_id": str(self.target_chart_version_id),
            "source_account_id": str(self.source_account_id),
            "target_account_ids": sorted(str(x) for x in self.target_account_ids),
            "provider_code": self.provider.provider_code,
            "provider_version": self.provider.provider_version,
            "provider_capability": self.provider.capability.value,
            "input_schema": self.provider.input_schema,
            "output_schema": self.provider.output_schema,
            "effective": _effective(self.effective),
            "knowledge": _knowledge(self.knowledge),
            "source_ref": self.source_ref,
        }

    def verify_integrity(self) -> None:
        self.mapping_set.verify_integrity()
        if _digest(self.canonical_manifest()) != self.content_digest:
            raise MappingCandidateDigestMismatch("Provider requirement intent changed")


def require_specialized_provider_candidate(
    *, requirement: MappingProviderRequirementCandidate,
    source_account_id: CompanyAccountId,
    as_of: date,
    known_at: datetime,
) -> None:
    """Always fail with a typed, nonexecuting marker for matching 1:N intent."""
    if not isinstance(requirement, MappingProviderRequirementCandidate) or not isinstance(
        source_account_id, CompanyAccountId
    ):
        raise InvalidMappingCandidate("Typed requirement and source account required")
    if type(as_of) is not date or type(known_at) is not datetime or (
        known_at.tzinfo is None or known_at.utcoffset() is None
    ):
        raise InvalidMappingCandidate("Typed as_of and aware known_at required")
    requirement.verify_integrity()
    if (
        requirement.source_account_id != source_account_id
        or not requirement.effective.contains(as_of)
        or not requirement.knowledge.contains(known_at)
    ):
        raise InvalidMappingCandidate("No matching active provider requirement")
    raise MappingProviderRequired(
        "Specialized provider is explicitly required; no allocation is executed"
    )
