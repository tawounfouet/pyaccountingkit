"""L05-05: read-only structural coverage diagnostics for mapping candidates.

No claim of published mapping coverage, postable accounts or user authorization.
No arbitrary exceptions, financial amounts or allocation execution.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum

from ..shared.effective_interval import EffectiveInterval, KnowledgeInterval
from ..shared.identifiers import CompanyAccountId, MappingSetCandidateVersionId
from .mapping import (
    InvalidMappingCandidate,
    MappingCandidateAmbiguous,
    MappingCandidateDigestMismatch,
    MappingPrecedencePolicy,
    MappingSetVersionCandidate,
    _aware,
    _digest,
    _effective,
    _knowledge,
)
from .mapping_conditions import MappingConditionProfileCandidate
from .mapping_provider import MappingProviderRequirementCandidate


class CoverageDisposition(Enum):
    DIRECT_CANDIDATE = "DIRECT_CANDIDATE"
    CONDITIONAL_NEEDS_FACTS = "CONDITIONAL_NEEDS_FACTS"
    PROVIDER_REQUIRED = "PROVIDER_REQUIRED"
    AMBIGUOUS = "AMBIGUOUS"
    UNMAPPED = "UNMAPPED"
    EXCEPTION_DECLARED = "EXCEPTION_DECLARED"


@dataclass(frozen=True, slots=True)
class MappingCoverageExceptionCandidate:
    """Unapproved intent to document an unmapped account; never an allowlist."""

    mapping_set_version_id: MappingSetCandidateVersionId
    source_account_id: CompanyAccountId
    reason: str
    effective: EffectiveInterval
    knowledge: KnowledgeInterval
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.mapping_set_version_id, MappingSetCandidateVersionId):
            raise InvalidMappingCandidate("Typed mapping set version required for exception")
        if not isinstance(self.source_account_id, CompanyAccountId):
            raise InvalidMappingCandidate("Typed exception account required")
        for value in (self.reason, self.source_ref):
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise InvalidMappingCandidate("Nonblank trimmed exception reason/source required")
        if not isinstance(self.effective, EffectiveInterval) or not isinstance(
            self.knowledge, KnowledgeInterval
        ):
            raise InvalidMappingCandidate("Typed dated exception intent required")


@dataclass(frozen=True, slots=True)
class AccountMappingCoverageRow:
    source_account_id: CompanyAccountId
    disposition: CoverageDisposition
    mapping_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True, eq=False)
class MappingCoverageCandidateReport:
    """Candidate-only deterministic report; no approval/compliance status."""

    mapping_set: MappingSetVersionCandidate
    rows: tuple[AccountMappingCoverageRow, ...]
    as_of: date
    known_at: datetime
    evidence_digest: str
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.mapping_set, MappingSetVersionCandidate):
            raise InvalidMappingCandidate("Typed report mapping set required")
        if not isinstance(self.rows, tuple) or any(
            not isinstance(r, AccountMappingCoverageRow) for r in self.rows
        ):
            raise InvalidMappingCandidate("Immutable coverage rows required")
        if len({r.source_account_id for r in self.rows}) != len(self.rows):
            raise InvalidMappingCandidate("Duplicate account coverage row")
        if type(self.as_of) is not date or type(self.known_at) is not datetime or (
            self.known_at.tzinfo is None or self.known_at.utcoffset() is None
        ):
            raise InvalidMappingCandidate("Date and aware knowledge instant required")
        if not isinstance(self.evidence_digest, str) or not self.evidence_digest.startswith(
            "sha256:"
        ):
            raise InvalidMappingCandidate("Pinned evidence digest required")
        self.mapping_set.verify_integrity()
        object.__setattr__(self, "content_digest", _digest(self.canonical_manifest()))

    @property
    def has_unresolved(self) -> bool:
        return any(
            r.disposition is not CoverageDisposition.DIRECT_CANDIDATE
            for r in self.rows
        )

    def canonical_manifest(self) -> dict[str, object]:
        return {
            "schema": "l05-coverage-rnd-v1",
            "status": "DIAGNOSTIC_ONLY_NOT_PUBLICATION",
            "mapping_set_id": str(self.mapping_set.id),
            "mapping_set_digest": self.mapping_set.content_digest,
            "evidence_digest": self.evidence_digest,
            "as_of": self.as_of.isoformat(),
            "known_at": _aware(self.known_at),
            "rows": [
                {
                    "source_account_id": str(row.source_account_id),
                    "disposition": row.disposition.value,
                    "mapping_ids": list(row.mapping_ids),
                }
                for row in sorted(self.rows, key=lambda row: str(row.source_account_id))
            ],
        }

    def verify_integrity(self) -> None:
        self.mapping_set.verify_integrity()
        if _digest(self.canonical_manifest()) != self.content_digest:
            raise MappingCandidateDigestMismatch("Coverage report changed")


def preview_mapping_coverage_candidate(
    *,
    mapping_set: MappingSetVersionCandidate,
    as_of: date,
    known_at: datetime,
    conditions: MappingConditionProfileCandidate | None = None,
    providers: tuple[MappingProviderRequirementCandidate, ...] = (),
    exceptions: tuple[MappingCoverageExceptionCandidate, ...] = (),
) -> MappingCoverageCandidateReport:
    """Classify EVERY effective source account, not just currently mapped ones.

    No context is evaluated here, so a conditional rule is NOT counted as
    resolved. Proposed exceptions are unresolved and never authorize posting.
    """
    if not isinstance(mapping_set, MappingSetVersionCandidate):
        raise InvalidMappingCandidate("Typed mapping set required")
    if type(as_of) is not date or type(known_at) is not datetime or (
        known_at.tzinfo is None or known_at.utcoffset() is None
    ):
        raise InvalidMappingCandidate("Typed business/knowledge cutoff required")
    if not isinstance(providers, tuple) or not isinstance(exceptions, tuple):
        raise InvalidMappingCandidate("Immutable provider/exception catalogs required")
    mapping_set.verify_integrity()
    if not mapping_set.effective.contains(as_of) or not mapping_set.knowledge.contains(
        known_at
    ):
        raise InvalidMappingCandidate("Mapping set not effective/known at requested cutoff")
    if conditions is not None:
        if not isinstance(conditions, MappingConditionProfileCandidate):
            raise InvalidMappingCandidate("Typed condition profile required")
        conditions.verify_integrity()
        if conditions.mapping_set is not mapping_set or not (
            conditions.effective.contains(as_of) and conditions.knowledge.contains(known_at)
        ):
            raise InvalidMappingCandidate("Condition profile is not exact active mapping set")
    source_ids = {a.id for a in mapping_set.source_chart.accounts}
    active_providers: dict[CompanyAccountId, MappingProviderRequirementCandidate] = {}
    for item in providers:
        if not isinstance(item, MappingProviderRequirementCandidate):
            raise InvalidMappingCandidate("Non-provider intent in catalog")
        item.verify_integrity()
        if item.mapping_set is not mapping_set or item.source_account_id not in source_ids:
            raise InvalidMappingCandidate("Foreign provider mapping set/source")
        if item.effective.contains(as_of) and item.knowledge.contains(known_at):
            if item.source_account_id in active_providers:
                raise MappingCandidateAmbiguous("Overlapping provider requirements")
            active_providers[item.source_account_id] = item

    active_exceptions: dict[CompanyAccountId, MappingCoverageExceptionCandidate] = {}
    source_accounts = {a.id: a for a in mapping_set.source_chart.accounts}
    exception_manifest = []
    for item in exceptions:
        if not isinstance(item, MappingCoverageExceptionCandidate):
            raise InvalidMappingCandidate("Non-exception in coverage catalog")
        if (
            item.mapping_set_version_id != mapping_set.id
            or item.source_account_id not in source_ids
        ):
            raise InvalidMappingCandidate("Foreign exception or unknown source")
        if not (
            mapping_set.effective.start <= item.effective.start
            and (
                mapping_set.effective.end is None
                or (
                    item.effective.end is not None
                    and item.effective.end <= mapping_set.effective.end
                )
            )
            and source_accounts[item.source_account_id].effective.start
            <= item.effective.start
            and (
                source_accounts[item.source_account_id].effective.end is None
                or (
                    item.effective.end is not None
                    and item.effective.end
                    <= source_accounts[item.source_account_id].effective.end
                )
            )
            and mapping_set.knowledge.start <= item.knowledge.start
            and (
                mapping_set.knowledge.end is None
                or (
                    item.knowledge.end is not None
                    and item.knowledge.end <= mapping_set.knowledge.end
                )
            )
        ):
            raise InvalidMappingCandidate("Coverage exception exceeds scope time windows")
        exception_manifest.append({
            "set_id": str(item.mapping_set_version_id),
            "account_id": str(item.source_account_id),
            "reason": item.reason,
            "effective": _effective(item.effective),
            "knowledge": _knowledge(item.knowledge),
            "source_ref": item.source_ref,
        })
        if item.effective.contains(as_of) and item.knowledge.contains(known_at):
            if item.source_account_id in active_exceptions:
                raise MappingCandidateAmbiguous("Overlapping coverage exceptions")
            active_exceptions[item.source_account_id] = item

    rules_by_id = {rule.mapping_id: rule for rule in conditions.rules} if conditions else {}
    rows = []
    for account in mapping_set.source_chart.accounts:
        if not account.effective.contains(as_of):
            continue
        matches = [
            item for item in mapping_set.mappings
            if item.source_account_id == account.id and item.effective.contains(as_of)
        ]
        provider = active_providers.get(account.id)
        exception = active_exceptions.get(account.id)
        if provider is not None and (matches or exception is not None):
            raise MappingCandidateAmbiguous("Provider intent overlaps mapping or exception")
        if exception is not None and matches:
            raise MappingCandidateAmbiguous("Exception cannot override an active mapping")
        if provider is not None:
            state = CoverageDisposition.PROVIDER_REQUIRED
        elif exception is not None:
            state = CoverageDisposition.EXCEPTION_DECLARED
        elif not matches:
            state = CoverageDisposition.UNMAPPED
        elif conditions and any(rules_by_id[m.id].predicates for m in matches):
            state = CoverageDisposition.CONDITIONAL_NEEDS_FACTS
        elif len(matches) > 1:
            if mapping_set.precedence is MappingPrecedencePolicy.EXPLICIT_PRIORITY_RND:
                best = max(m.priority for m in matches if m.priority is not None)
                highest = [m for m in matches if m.priority == best]
                state = (
                    CoverageDisposition.DIRECT_CANDIDATE if len(highest) == 1
                    else CoverageDisposition.AMBIGUOUS
                )
            else:
                state = CoverageDisposition.AMBIGUOUS
        else:
            state = CoverageDisposition.DIRECT_CANDIDATE
        rows.append(AccountMappingCoverageRow(
            account.id, state, tuple(sorted(str(m.id) for m in matches))
        ))

    evidence_digest = _digest({
        "schema": "l05-coverage-evidence-rnd-v1",
        "condition_digest": conditions.content_digest if conditions else None,
        "provider_digests": sorted(v.content_digest for v in providers),
        "exceptions": sorted(
            exception_manifest, key=lambda x: (
                x["account_id"], x["effective"]["start"], x["source_ref"]
            )
        ),
    })
    return MappingCoverageCandidateReport(
        mapping_set=mapping_set,
        rows=tuple(rows),
        as_of=as_of,
        known_at=known_at,
        evidence_digest=evidence_digest,
    )
