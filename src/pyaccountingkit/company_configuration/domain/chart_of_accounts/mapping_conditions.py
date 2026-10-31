"""L05-05: declarative, version-pinned conditional mapping *candidate*.

No arbitrary expression execution, implicit account fallback, financial amount,
1:N allocation, signed C10 record, publishing or Ledger posting.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum

from ..shared.effective_interval import EffectiveInterval, KnowledgeInterval
from ..shared.identifiers import AccountMappingCandidateId, CompanyAccountId
from .mapping import (
    MappingCandidateAmbiguous,
    MappingCandidateDigestMismatch,
    MappingCandidateMissing,
    MappingPrecedencePolicy,
    MappingSetVersionCandidate,
    _aware,
    _contains_knowledge,
    _contains_period,
    _digest,
    _effective,
    _knowledge,
)


class InvalidMappingCondition(ValueError):
    """Invalid or incomplete typed conditional candidate context."""


class MissingMappingFact(InvalidMappingCondition):
    """Refuse to treat missing condition data as a false/default match."""


class MappingFactKey(Enum):
    ACTIVITY = "ACTIVITY"
    BUSINESS_UNIT = "BUSINESS_UNIT"
    COST_CENTER = "COST_CENTER"
    SEGMENT = "SEGMENT"


class PredicateOperator(Enum):
    EQUALS = "EQUALS"
    ONE_OF = "ONE_OF"


def _code(value: str) -> bool:
    if not isinstance(value, str) or not (1 <= len(value) <= 64):
        return False
    return value[0].isupper() and value[0].isascii() and all(
        char.isascii() and (char.isupper() or char.isdigit() or char in "_-")
        for char in value
    )


@dataclass(frozen=True, slots=True)
class MappingFact:
    key: MappingFactKey
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.key, MappingFactKey) or not _code(self.value):
            raise InvalidMappingCondition("Typed fact key and canonical value required")


@dataclass(frozen=True, slots=True)
class MappingPredicate:
    key: MappingFactKey
    operator: PredicateOperator
    expected: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.key, MappingFactKey) or not isinstance(
            self.operator, PredicateOperator
        ):
            raise InvalidMappingCondition("Typed fact operator required")
        if (
            not isinstance(self.expected, tuple)
            or not self.expected
            or any(not _code(v) for v in self.expected)
            or len(set(self.expected)) != len(self.expected)
        ):
            raise InvalidMappingCondition("Nonempty canonical unique predicate values required")
        if self.operator is PredicateOperator.EQUALS and len(self.expected) != 1:
            raise InvalidMappingCondition("EQUALS requires exactly one expected value")

    def matches(self, value: str) -> bool:
        return value in self.expected


@dataclass(frozen=True, slots=True)
class MappingRuleCondition:
    """Explicit AND-only rule. Empty tuple means explicitly unconditional."""

    mapping_id: AccountMappingCandidateId
    predicates: tuple[MappingPredicate, ...]
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.mapping_id, AccountMappingCandidateId):
            raise InvalidMappingCondition("Typed mapping ID required")
        if not isinstance(self.predicates, tuple) or any(
            not isinstance(p, MappingPredicate) for p in self.predicates
        ):
            raise InvalidMappingCondition("Immutable typed predicates required")
        if len({p.key for p in self.predicates}) != len(self.predicates):
            raise InvalidMappingCondition("Duplicate fact key within AND rule")
        if not isinstance(self.source_ref, str) or not self.source_ref.strip() or (
            self.source_ref != self.source_ref.strip()
        ):
            raise InvalidMappingCondition("Trimmed source pointer required")


def _rule_manifest(rule: MappingRuleCondition) -> dict[str, object]:
    return {
        "mapping_id": str(rule.mapping_id),
        "source_ref": rule.source_ref,
        "and": [
            {
                "key": p.key.value,
                "operator": p.operator.value,
                "values": sorted(p.expected),
            }
            for p in sorted(rule.predicates, key=lambda p: p.key.value)
        ],
    }


@dataclass(frozen=True, slots=True, eq=False)
class MappingConditionProfileCandidate:
    """Complete declarative overlay pinned to one L05-04 candidate mapping set."""

    mapping_set: MappingSetVersionCandidate
    rules: tuple[MappingRuleCondition, ...]
    effective: EffectiveInterval
    knowledge: KnowledgeInterval
    source_ref: str
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.mapping_set, MappingSetVersionCandidate):
            raise InvalidMappingCondition("Typed mapping set candidate required")
        if not isinstance(self.rules, tuple) or any(
            not isinstance(rule, MappingRuleCondition) for rule in self.rules
        ):
            raise InvalidMappingCondition("Immutable rule condition catalog required")
        if not isinstance(self.effective, EffectiveInterval) or not isinstance(
            self.knowledge, KnowledgeInterval
        ):
            raise InvalidMappingCondition("Typed business and knowledge intervals required")
        if not isinstance(self.source_ref, str) or not self.source_ref.strip() or (
            self.source_ref != self.source_ref.strip()
        ):
            raise InvalidMappingCondition("Canonical source required")
        self.mapping_set.verify_integrity()
        if not _contains_period(self.mapping_set.effective, self.effective) or not (
            _contains_knowledge(self.mapping_set.knowledge, self.knowledge)
        ):
            raise InvalidMappingCondition("Condition profile escapes mapping set time windows")
        required = {m.id for m in self.mapping_set.mappings}
        supplied = [r.mapping_id for r in self.rules]
        if len(supplied) != len(required) or set(supplied) != required:
            raise InvalidMappingCondition(
                "Every mapping requires exactly one explicit condition declaration"
            )
        object.__setattr__(self, "content_digest", _digest(self.canonical_manifest()))

    def canonical_manifest(self) -> dict[str, object]:
        return {
            "schema": "l05-conditional-rnd-v1",
            "status": "UNPUBLISHED_CONDITION_PROFILE",
            "mapping_set_id": str(self.mapping_set.id),
            "mapping_set_digest": self.mapping_set.content_digest,
            "effective": _effective(self.effective),
            "knowledge": _knowledge(self.knowledge),
            "source_ref": self.source_ref,
            "rules": [
                _rule_manifest(rule) for rule in sorted(
                    self.rules, key=lambda rule: str(rule.mapping_id)
                )
            ],
        }

    def verify_integrity(self) -> None:
        self.mapping_set.verify_integrity()
        if _digest(self.canonical_manifest()) != self.content_digest:
            raise MappingCandidateDigestMismatch("Condition profile was altered")


@dataclass(frozen=True, slots=True, eq=False)
class ConditionalMappingCandidateResolution:
    """One selected target and a pinned context digest, never a posting command."""

    profile: MappingConditionProfileCandidate
    mapping_id: AccountMappingCandidateId
    facts: tuple[MappingFact, ...]
    as_of: date
    known_at: datetime
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.profile, MappingConditionProfileCandidate):
            raise InvalidMappingCondition("Condition profile required")
        if not isinstance(self.mapping_id, AccountMappingCandidateId):
            raise InvalidMappingCondition("Typed mapping ID required")
        _validate_context(self.facts)
        _validate_cutoff(self.as_of, self.known_at)
        self.profile.verify_integrity()
        if (
            not self.profile.effective.contains(self.as_of)
            or not self.profile.knowledge.contains(self.known_at)
            or not any(
                m.id == self.mapping_id and m.effective.contains(self.as_of)
                for m in self.profile.mapping_set.mappings
            )
        ):
            raise InvalidMappingCondition("Resolution does not match profile and date")
        object.__setattr__(self, "content_digest", _digest(self.canonical_manifest()))

    @property
    def target_account_id(self) -> CompanyAccountId:
        for mapping in self.profile.mapping_set.mappings:
            if mapping.id == self.mapping_id:
                return mapping.target_account_id
        raise InvalidMappingCondition("Selected mapping missing from pinned set")

    def canonical_manifest(self) -> dict[str, object]:
        return {
            "schema": "l05-conditional-resolution-rnd-v1",
            "status": "UNPUBLISHED_CONDITIONAL_MAPPING_PREVIEW",
            "profile_digest": self.profile.content_digest,
            "mapping_set_version_id": str(self.profile.mapping_set.id),
            "mapping_id": str(self.mapping_id),
            "target_account_id": str(self.target_account_id),
            "facts": [
                {"key": f.key.value, "value": f.value}
                for f in sorted(self.facts, key=lambda f: f.key.value)
            ],
            "as_of": self.as_of.isoformat(),
            "known_at": _aware(self.known_at),
        }

    def verify_integrity(self) -> None:
        self.profile.verify_integrity()
        if _digest(self.canonical_manifest()) != self.content_digest:
            raise MappingCandidateDigestMismatch("Conditional mapping receipt altered")


def _validate_cutoff(as_of: date, known_at: datetime) -> None:
    if type(as_of) is not date or type(known_at) is not datetime or (
        known_at.tzinfo is None or known_at.utcoffset() is None
    ):
        raise InvalidMappingCondition("Date and timezone-aware knowledge required")


def _validate_context(facts: tuple[MappingFact, ...]) -> dict[MappingFactKey, str]:
    if not isinstance(facts, tuple) or any(
        not isinstance(f, MappingFact) for f in facts
    ):
        raise InvalidMappingCondition("Immutable typed context facts required")
    values = {f.key: f.value for f in facts}
    if len(values) != len(facts):
        raise InvalidMappingCondition("Duplicate contextual fact key")
    return values


def resolve_conditional_mapping_candidate(
    *,
    profile: MappingConditionProfileCandidate,
    source_account_id: CompanyAccountId,
    facts: tuple[MappingFact, ...],
    as_of: date,
    known_at: datetime,
) -> ConditionalMappingCandidateResolution:
    """Explicit typed AND predicates, then L05-04 R&D priority, never Python eval."""
    if not isinstance(profile, MappingConditionProfileCandidate) or not isinstance(
        source_account_id, CompanyAccountId
    ):
        raise InvalidMappingCondition("Typed profile and source account identity required")
    _validate_cutoff(as_of, known_at)
    values = _validate_context(facts)
    profile.verify_integrity()
    if not profile.effective.contains(as_of) or not profile.knowledge.contains(known_at):
        raise MappingCandidateMissing("No active conditional mapping candidate profile")

    declarations = {rule.mapping_id: rule for rule in profile.rules}
    matches = []
    for mapping in profile.mapping_set.mappings:
        if mapping.source_account_id != source_account_id or not mapping.effective.contains(
            as_of
        ):
            continue
        predicates = declarations[mapping.id].predicates
        for predicate in predicates:
            if predicate.key not in values:
                raise MissingMappingFact("Context lacks required typed mapping fact")
        if all(predicate.matches(values[predicate.key]) for predicate in predicates):
            matches.append(mapping)

    if not matches:
        raise MappingCandidateMissing("No matching declared mapping condition")
    if len(matches) > 1:
        if profile.mapping_set.precedence is MappingPrecedencePolicy.REQUIRE_UNIQUE:
            raise MappingCandidateAmbiguous("Multiple matching conditions without priority")
        best = max(m.priority for m in matches if m.priority is not None)
        matches = [m for m in matches if m.priority == best]
        if len(matches) != 1:
            raise MappingCandidateAmbiguous("Equal-priority matching condition candidates")
    return ConditionalMappingCandidateResolution(
        profile=profile, mapping_id=matches[0].id, facts=facts,
        as_of=as_of, known_at=known_at,
    )
