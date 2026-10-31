"""L07-01: pure candidate policy/ruleset model and fail-closed R&D preview.

No normative rule interpreter, priority/inheritance, approved policy, IAM, C10,
SQL, publication, audit, PostingPlan or Ledger effect is implemented here.
"""

from dataclasses import dataclass
from datetime import date, datetime
from re import fullmatch

from ..shared.accounting_scope import ConfigurationScope
from ..shared.effective_interval import EffectiveInterval, KnowledgeInterval
from ..shared.identifiers import AccountingBookId
from .identifiers import PolicyAssignmentCandidateId, PolicyCandidateId, RulesetCandidateId


class InvalidPolicyCandidate(ValueError):
    """Malformed or cross-scope untrusted candidate data."""


class CandidatePolicyMissing(ValueError):
    """No matching explicitly declared candidate; no fallback."""


class CandidatePolicyConflict(ValueError):
    """Ambiguous identity, assignment or candidate catalog; deny first."""


def _code(value: str) -> str:
    if type(value) is not str or fullmatch(r"[A-Z][A-Z0-9_\-]{0,47}", value) is None:
        raise InvalidPolicyCandidate("Code must be literal uppercase ASCII (1..48 chars)")
    return value


def _claim(value: str) -> str:
    if type(value) is not str or not value or value.strip() != value or len(value) > 256:
        raise InvalidPolicyCandidate("Explicit nonempty bounded source claim required")
    return value


@dataclass(frozen=True, slots=True)
class PolicyCode:
    value: str

    def __post_init__(self) -> None:
        _code(self.value)


@dataclass(frozen=True, slots=True)
class RulesetCode:
    value: str

    def __post_init__(self) -> None:
        _code(self.value)


@dataclass(frozen=True, slots=True)
class PolicyTopic:
    """Explicit resolution dimension; a book may have several independent topics."""

    value: str

    def __post_init__(self) -> None:
        _code(self.value)


def _entity_scope(scope: ConfigurationScope) -> None:
    if not isinstance(scope, ConfigurationScope) or scope.book_id is not None:
        raise InvalidPolicyCandidate("Draft must use explicit entity scope, never book authority")


def _book_scope(scope: ConfigurationScope) -> None:
    if not isinstance(scope, ConfigurationScope) or not isinstance(scope.book_id, AccountingBookId):
        raise InvalidPolicyCandidate("Assignment requires an explicit typed book scope")


@dataclass(frozen=True, slots=True)
class PolicyCandidateDraft:
    """Unpublished and unapproved company policy candidate (not normative truth)."""

    id: PolicyCandidateId
    scope: ConfigurationScope
    code: PolicyCode
    topic: PolicyTopic
    effective: EffectiveInterval
    framework_claim: str
    source_ref: str
    revision: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, PolicyCandidateId) or not isinstance(self.code, PolicyCode):
            raise InvalidPolicyCandidate("Typed policy ID and PolicyCode required")
        if not isinstance(self.topic, PolicyTopic) or not isinstance(self.effective, EffectiveInterval):
            raise InvalidPolicyCandidate("Typed policy topic and valid interval required")
        _entity_scope(self.scope)
        _claim(self.framework_claim)
        _claim(self.source_ref)
        if type(self.revision) is not int or self.revision < 1:
            raise InvalidPolicyCandidate("Positive integer candidate revision required")


@dataclass(frozen=True, slots=True)
class RulesetCandidateDraft:
    """Opaque ruleset reference; never interprets a rule expression or executes code."""

    id: RulesetCandidateId
    scope: ConfigurationScope
    code: RulesetCode
    effective: EffectiveInterval
    framework_claim: str
    rules_source_ref: str
    revision: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, RulesetCandidateId) or not isinstance(self.code, RulesetCode):
            raise InvalidPolicyCandidate("Typed ruleset ID and RulesetCode required")
        if not isinstance(self.effective, EffectiveInterval):
            raise InvalidPolicyCandidate("Typed effective interval required")
        _entity_scope(self.scope)
        _claim(self.framework_claim)
        _claim(self.rules_source_ref)
        if type(self.revision) is not int or self.revision < 1:
            raise InvalidPolicyCandidate("Positive integer candidate revision required")


@dataclass(frozen=True, slots=True)
class PolicyAssignmentCandidate:
    """Unpublished, book-scoped, bitemporal policy-to-ruleset claim."""

    id: PolicyAssignmentCandidateId
    scope: ConfigurationScope
    topic: PolicyTopic
    policy_id: PolicyCandidateId
    ruleset_id: RulesetCandidateId
    effective: EffectiveInterval
    knowledge: KnowledgeInterval
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, PolicyAssignmentCandidateId):
            raise InvalidPolicyCandidate("Typed assignment ID required")
        _book_scope(self.scope)
        if (not isinstance(self.topic, PolicyTopic)
                or not isinstance(self.policy_id, PolicyCandidateId)
                or not isinstance(self.ruleset_id, RulesetCandidateId)):
            raise InvalidPolicyCandidate("Typed topic, policy and ruleset references required")
        if not isinstance(self.effective, EffectiveInterval) or not isinstance(
            self.knowledge, KnowledgeInterval
        ):
            raise InvalidPolicyCandidate("Business and knowledge intervals required")
        _claim(self.source_ref)


@dataclass(frozen=True, slots=True)
class PolicyCandidatePreview:
    """Read-only candidate evidence; explicitly forbidden as posting permission."""

    assignment_id: PolicyAssignmentCandidateId
    policy_id: PolicyCandidateId
    ruleset_id: RulesetCandidateId
    book_id: AccountingBookId
    topic: PolicyTopic
    as_of: date
    known_at: datetime
    eligible_for_posting: bool = False


def preview_policy_candidate(
    *,
    scope: ConfigurationScope,
    topic: PolicyTopic,
    as_of: date,
    known_at: datetime,
    policies: tuple[PolicyCandidateDraft, ...],
    rulesets: tuple[RulesetCandidateDraft, ...],
    assignments: tuple[PolicyAssignmentCandidate, ...],
) -> PolicyCandidatePreview:
    """Select exactly one self-consistent untrusted candidate in a complete catalog.

    No policy inheritance, ranking, latest-version selection, published-state
    claim or normative framework validation. Reject corrupt unrelated entries.
    """
    _book_scope(scope)
    if not isinstance(topic, PolicyTopic) or type(as_of) is not date:
        raise InvalidPolicyCandidate("Explicit topic and business date required")
    if type(known_at) is not datetime or known_at.tzinfo is None or known_at.utcoffset() is None:
        raise InvalidPolicyCandidate("Timezone-aware known_at required")
    if any(type(items) is not tuple for items in (policies, rulesets, assignments)):
        raise InvalidPolicyCandidate("Immutable candidate tuple catalogs required")

    seen_policy_ids: set[PolicyCandidateId] = set()
    seen_ruleset_ids: set[RulesetCandidateId] = set()
    seen_assignment_ids: set[PolicyAssignmentCandidateId] = set()
    policy_index: dict[PolicyCandidateId, PolicyCandidateDraft] = {}
    ruleset_index: dict[RulesetCandidateId, RulesetCandidateDraft] = {}
    entity_scope = ConfigurationScope(
        tenant_id=scope.tenant_id,
        company_id=scope.company_id,
        legal_entity_id=scope.legal_entity_id,
    )
    for policy in policies:
        if not isinstance(policy, PolicyCandidateDraft) or policy.scope != entity_scope:
            raise CandidatePolicyConflict("Malformed or foreign policy in candidate catalog")
        if policy.id in seen_policy_ids:
            raise CandidatePolicyConflict("Duplicate policy identity")
        for existing in policy_index.values():
            if (existing.code == policy.code and existing.topic == policy.topic
                    and existing.effective.overlaps(policy.effective)):
                raise CandidatePolicyConflict("Overlapping candidate policy code")
        seen_policy_ids.add(policy.id)
        policy_index[policy.id] = policy
    for ruleset in rulesets:
        if not isinstance(ruleset, RulesetCandidateDraft) or ruleset.scope != entity_scope:
            raise CandidatePolicyConflict("Malformed or foreign ruleset in candidate catalog")
        if ruleset.id in seen_ruleset_ids:
            raise CandidatePolicyConflict("Duplicate ruleset identity")
        for existing in ruleset_index.values():
            if (existing.code == ruleset.code
                    and existing.effective.overlaps(ruleset.effective)):
                raise CandidatePolicyConflict("Overlapping candidate ruleset code")
        seen_ruleset_ids.add(ruleset.id)
        ruleset_index[ruleset.id] = ruleset
    for assignment in assignments:
        if not isinstance(assignment, PolicyAssignmentCandidate) or assignment.scope != scope:
            raise CandidatePolicyConflict("Malformed or foreign assignment in candidate catalog")
        if assignment.id in seen_assignment_ids:
            raise CandidatePolicyConflict("Duplicate assignment identity")
        seen_assignment_ids.add(assignment.id)
        policy = policy_index.get(assignment.policy_id)
        ruleset = ruleset_index.get(assignment.ruleset_id)
        if policy is None or ruleset is None:
            raise CandidatePolicyConflict("Unresolved policy/ruleset candidate reference")
        if assignment.topic != policy.topic or policy.framework_claim != ruleset.framework_claim:
            raise CandidatePolicyConflict("Topic or framework claim mismatch")
        for target in (policy.effective, ruleset.effective):
            if (assignment.effective.start < target.start or (
                target.end is not None and (
                    assignment.effective.end is None or assignment.effective.end > target.end
                )
            )):
                raise CandidatePolicyConflict("Assignment outside dependency validity")

    for index, first in enumerate(assignments):
        for second in assignments[index + 1:]:
            if (first.topic == second.topic
                    and first.effective.overlaps(second.effective)
                    and first.knowledge.overlaps(second.knowledge)):
                raise CandidatePolicyConflict("Overlapping assignment candidates at future dates")

    active = [
        a for a in assignments if a.topic == topic
        and a.effective.contains(as_of) and a.knowledge.contains(known_at)
    ]
    if not active:
        raise CandidatePolicyMissing("No explicit policy assignment at as_of / known_at")
    if len(active) != 1:
        raise CandidatePolicyConflict("Ambiguous policy assignments: no priority policy approved")
    chosen = active[0]
    return PolicyCandidatePreview(
        assignment_id=chosen.id,
        policy_id=chosen.policy_id,
        ruleset_id=chosen.ruleset_id,
        book_id=scope.book_id,
        topic=topic,
        as_of=as_of,
        known_at=known_at,
    )
