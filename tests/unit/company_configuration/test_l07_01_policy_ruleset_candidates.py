"""R&D-only L07-01: candidate contracts and negative boundary tests."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta

import pytest

from pyaccountingkit.company_configuration.domain.policies import (
    CandidatePolicyConflict,
    CandidatePolicyMissing,
    InvalidPolicyCandidate,
    PolicyAssignmentCandidate,
    PolicyAssignmentCandidateId,
    PolicyCandidateDraft,
    PolicyCandidateId,
    PolicyCode,
    PolicyTopic,
    RulesetCandidateDraft,
    RulesetCandidateId,
    RulesetCode,
    preview_policy_candidate,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import ConfigurationScope
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
    KnowledgeInterval,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountingBookId,
    CompanyId,
    LegalEntityId,
)

START = date(2027, 1, 1)
END = date(2028, 1, 1)
KNOWN = datetime(2026, 10, 31, tzinfo=UTC)


def fixture():
    entity = ConfigurationScope("tenant-a", CompanyId.new(), LegalEntityId.new())
    book = replace(entity, book_id=AccountingBookId.new())
    policy = PolicyCandidateDraft(
        PolicyCandidateId.new(), entity, PolicyCode("REVENUE_POLICY"),
        PolicyTopic("REVENUE"), EffectiveInterval(START, END),
        "unverified:PCG-2027", "rnd:policy",
    )
    ruleset = RulesetCandidateDraft(
        RulesetCandidateId.new(), entity, RulesetCode("REVENUE_RULES"),
        EffectiveInterval(START, END), "unverified:PCG-2027", "rnd:rules",
    )
    assignment = PolicyAssignmentCandidate(
        PolicyAssignmentCandidateId.new(), book, PolicyTopic("REVENUE"),
        policy.id, ruleset.id, EffectiveInterval(START, END),
        KnowledgeInterval(KNOWN), "rnd:assignment",
    )
    return book, policy, ruleset, assignment


def preview(book, policy, ruleset, assignment, *, day=START, known=KNOWN):
    return preview_policy_candidate(
        scope=book, topic=PolicyTopic("REVENUE"), as_of=day, known_at=known,
        policies=(policy,), rulesets=(ruleset,), assignments=(assignment,),
    )


def test_explicit_candidate_and_never_posting_authority():
    book, policy, ruleset, assignment = fixture()
    result = preview(book, policy, ruleset, assignment)
    assert result.policy_id == policy.id
    assert result.ruleset_id == ruleset.id
    assert result.assignment_id == assignment.id
    assert result.book_id == book.book_id
    assert result.eligible_for_posting is False
    with pytest.raises(FrozenInstanceError):
        result.eligible_for_posting = True


@pytest.mark.parametrize("bad", ["", " ", "bad", "A B", " A", "ÉX", "A" * 49, 5])
def test_invalid_literal_codes_fail_closed(bad):
    for cls in (PolicyCode, RulesetCode, PolicyTopic):
        with pytest.raises(InvalidPolicyCandidate):
            cls(bad)


def test_identifier_types_are_not_interchangeable():
    book, policy, ruleset, assignment = fixture()
    with pytest.raises(InvalidPolicyCandidate):
        replace(policy, id=ruleset.id)
    with pytest.raises(InvalidPolicyCandidate):
        replace(assignment, policy_id=ruleset.id)
    with pytest.raises(InvalidPolicyCandidate):
        replace(ruleset, code=policy.code)


def test_candidate_draft_immutable_and_positive_revisions():
    _, policy, ruleset, _ = fixture()
    with pytest.raises(FrozenInstanceError):
        policy.revision = 3
    with pytest.raises(InvalidPolicyCandidate):
        replace(policy, revision=0)
    with pytest.raises(InvalidPolicyCandidate):
        replace(ruleset, revision=True)


def test_bitemporal_missing_and_known_at_cannot_fallback():
    book, policy, ruleset, assignment = fixture()
    for day, known in ((END, KNOWN), (START, KNOWN - timedelta(seconds=1))):
        with pytest.raises(CandidatePolicyMissing):
            preview(book, policy, ruleset, assignment, day=day, known=known)


def test_non_aware_timestamp_and_bad_catalog_fail():
    book, policy, ruleset, assignment = fixture()
    with pytest.raises(InvalidPolicyCandidate):
        preview(book, policy, ruleset, assignment, known=datetime(2026, 10, 31))
    with pytest.raises(InvalidPolicyCandidate):
        preview_policy_candidate(
            scope=book, topic=PolicyTopic("REVENUE"), as_of=START, known_at=KNOWN,
            policies=[policy], rulesets=(ruleset,), assignments=(assignment,),
        )


def test_duplicate_and_ambiguous_assignments_denied():
    book, policy, ruleset, assignment = fixture()
    for duplicate in (assignment, replace(assignment, id=PolicyAssignmentCandidateId.new())):
        with pytest.raises(CandidatePolicyConflict):
            preview_policy_candidate(
                scope=book, topic=assignment.topic, as_of=START, known_at=KNOWN,
                policies=(policy,), rulesets=(ruleset,), assignments=(assignment, duplicate),
            )


def test_invalid_foreign_inactive_candidates_rejected_too():
    book, policy, ruleset, assignment = fixture()
    foreign = replace(policy, scope=replace(policy.scope, tenant_id="tenant-x"))
    with pytest.raises(CandidatePolicyConflict):
        preview_policy_candidate(
            scope=book, topic=assignment.topic, as_of=START, known_at=KNOWN,
            policies=(policy, foreign), rulesets=(ruleset,), assignments=(assignment,),
        )


def test_orphans_inactive_assignments_and_wrong_claim_fail():
    book, policy, ruleset, assignment = fixture()
    inactive = replace(assignment, topic=PolicyTopic("OTHER"), id=PolicyAssignmentCandidateId.new())
    with pytest.raises(CandidatePolicyConflict):
        preview_policy_candidate(
            scope=book, topic=assignment.topic, as_of=START, known_at=KNOWN,
            policies=(policy,), rulesets=(ruleset,), assignments=(assignment, inactive),
        )
    with pytest.raises(CandidatePolicyConflict):
        preview(book, policy, replace(ruleset, framework_claim="unverified:IFRS"), assignment)
    with pytest.raises(CandidatePolicyConflict):
        preview(book, policy, ruleset, replace(assignment, ruleset_id=RulesetCandidateId.new()))


def test_assignment_must_be_contained_and_book_scope_explicit():
    book, policy, ruleset, assignment = fixture()
    with pytest.raises(CandidatePolicyConflict):
        preview(book, policy, ruleset, replace(assignment, effective=EffectiveInterval(START)))
    with pytest.raises(InvalidPolicyCandidate):
        replace(assignment, scope=replace(book, book_id=None))
    with pytest.raises(InvalidPolicyCandidate):
        replace(policy, scope=book)


def test_topic_is_required_no_implicit_group_inheritance():
    book, policy, ruleset, assignment = fixture()
    with pytest.raises(CandidatePolicyMissing):
        preview_policy_candidate(
            scope=book, topic=PolicyTopic("INVENTORY"), as_of=START, known_at=KNOWN,
            policies=(policy,), rulesets=(ruleset,), assignments=(assignment,),
        )


def test_order_of_catalogs_does_not_override_explicit_selection():
    book, policy, ruleset, assignment = fixture()
    other_policy = replace(
        policy, id=PolicyCandidateId.new(), code=PolicyCode("INVENTORY_POLICY"),
        topic=PolicyTopic("INVENTORY"),
    )
    other_assignment = replace(
        assignment, id=PolicyAssignmentCandidateId.new(), policy_id=other_policy.id,
        topic=other_policy.topic,
    )
    selected = []
    for ps, ass in (
        ((policy, other_policy), (assignment, other_assignment)),
        ((other_policy, policy), (other_assignment, assignment)),
    ):
        selected.append(preview_policy_candidate(
            scope=book, topic=assignment.topic, as_of=START, known_at=KNOWN,
            policies=ps, rulesets=(ruleset,), assignments=ass,
        ))
    assert selected[0] == selected[1]


def test_future_ambiguity_is_refused_before_current_preview():
    book, policy, ruleset, assignment = fixture()
    second = replace(
        assignment, id=PolicyAssignmentCandidateId.new(),
        effective=EffectiveInterval(date(2027, 7, 1), END),
    )
    with pytest.raises(CandidatePolicyConflict, match="future dates"):
        preview_policy_candidate(
            scope=book, topic=assignment.topic, as_of=START, known_at=KNOWN,
            policies=(policy,), rulesets=(ruleset,), assignments=(assignment, second),
        )


def test_overlapping_definition_codes_are_refused_even_inactive():
    book, policy, ruleset, assignment = fixture()
    duplicate_policy = replace(policy, id=PolicyCandidateId.new())
    duplicate_ruleset = replace(ruleset, id=RulesetCandidateId.new())
    for policies, rulesets in (
        ((policy, duplicate_policy), (ruleset,)),
        ((policy,), (ruleset, duplicate_ruleset)),
    ):
        with pytest.raises(CandidatePolicyConflict, match="Overlapping candidate"):
            preview_policy_candidate(
                scope=book, topic=assignment.topic, as_of=START, known_at=KNOWN,
                policies=policies, rulesets=rulesets, assignments=(assignment,),
            )
