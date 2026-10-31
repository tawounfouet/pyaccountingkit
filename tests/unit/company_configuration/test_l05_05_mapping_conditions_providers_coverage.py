"""L05-05 adversarial R&D conditional mapping/provider/coverage contracts."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from pyaccountingkit.company_configuration.application.chart_mapping_diagnostics import (
    MappingDiagnosticsCandidateQuery,
    MappingDiagnosticsCandidateService,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal
from pyaccountingkit.company_configuration.domain.chart_of_accounts import (
    AccountClassificationCode,
    AccountCode,
    AccountMappingCandidate,
    ChartCode,
    CompanyAccountDraft,
    CompanyChartDraft,
    CompanyChartVersionCandidate,
    ConditionalMappingCandidateResolution,
    CoverageDisposition,
    InvalidMappingCondition,
    MappingCandidateAmbiguous,
    MappingCandidateDigestMismatch,
    MappingCandidateMissing,
    MappingConditionProfileCandidate,
    MappingCoverageExceptionCandidate,
    MappingFact,
    MappingFactKey,
    MappingKind,
    MappingPrecedencePolicy,
    MappingPredicate,
    MappingProviderRequired,
    MappingProviderRequirementCandidate,
    MappingRuleCondition,
    MappingSetVersionCandidate,
    MissingMappingFact,
    PredicateOperator,
    ProviderCapability,
    SpecializedMappingProviderContract,
    preview_mapping_coverage_candidate,
    require_specialized_provider_candidate,
    resolve_conditional_mapping_candidate,
)
from pyaccountingkit.company_configuration.domain.chart_of_accounts.mapping import (
    InvalidMappingCandidate,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
    KnowledgeInterval,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountMappingCandidateId,
    CompanyAccountId,
    CompanyChartCandidateVersionId,
    CompanyChartId,
    CompanyId,
    LegalEntityId,
    MappingSetCandidateVersionId,
)
from pyaccountingkit.company_configuration.domain.shared.references import (
    ReferenceFrameworkRef,
)
from pyaccountingkit.company_configuration.infrastructure.chart_mapping_diagnostics_memory import (
    MemoryMappingDiagnosticsCandidates,
)

JAN = datetime(2026, 1, 1, tzinfo=UTC)
MAR = datetime(2026, 3, 1, tzinfo=UTC)
FEB = datetime(2026, 2, 1, tzinfo=UTC)
DAY = date(2026, 2, 15)
START = date(2026, 1, 1)
VALID = EffectiveInterval(START)
PERIOD = KnowledgeInterval(JAN)


def sample(*, policy=MappingPrecedencePolicy.REQUIRE_UNIQUE, pair_count=2):
    scope = ConfigurationScope(
        tenant_id="tenant-a", company_id=CompanyId.new(),
        legal_entity_id=LegalEntityId.new(),
    )
    source = CompanyChartDraft(
        CompanyChartId.new(), scope, ChartCode("LOCAL"), "Local",
        VALID, "rnd:source",
    )
    target = CompanyChartDraft(
        CompanyChartId.new(), scope, ChartCode("GROUP"), "Group",
        VALID, "rnd:target",
    )

    def account(chart, code):
        return CompanyAccountDraft(
            CompanyAccountId.new(), chart.id, scope, AccountCode(code),
            "Account " + code, AccountClassificationCode("LOCAL"),
            True, VALID, "rnd:account",
        )

    a, b = account(source, "001"), account(source, "002")
    x, y = account(target, "901"), account(target, "902")
    normative = ReferenceFrameworkRef("PCG", "TEST_2026")
    sv = CompanyChartVersionCandidate(
        CompanyChartCandidateVersionId.new(), source, (a, b), (), (),
        normative, VALID, PERIOD, "rnd:source-version",
    )
    tv = CompanyChartVersionCandidate(
        CompanyChartCandidateVersionId.new(), target, (x, y), (), (),
        normative, VALID, PERIOD, "rnd:target-version",
    )
    sid = MappingSetCandidateVersionId.new()
    pairs = ((a, x), (a, y))[:pair_count]
    mappings = tuple(
        AccountMappingCandidate(
            id=AccountMappingCandidateId.new(),
            mapping_set_version_id=sid, scope=scope,
            source_chart_version_id=sv.id, source_account_id=s.id,
            target_chart_version_id=tv.id, target_account_id=t.id,
            kind=MappingKind.DIRECT_ONE_TO_ONE, effective=VALID,
            source_ref="rnd:map",
            priority=(n + 1) if policy is MappingPrecedencePolicy.EXPLICIT_PRIORITY_RND else None,
        )
        for n, (s, t) in enumerate(pairs)
    )
    mapping_set = MappingSetVersionCandidate(
        sid, scope, sv, tv, mappings, policy, VALID, PERIOD, "rnd:mapping-set",
    )
    return mapping_set, a, b, x, y


def predicate(value="RETAIL", *, key=MappingFactKey.SEGMENT):
    return MappingPredicate(key, PredicateOperator.EQUALS, (value,))


def profile(ms, *predicates, knowledge=None):
    rules = tuple(
        MappingRuleCondition(
            m.id, predicates[i] if i < len(predicates) else (),
            "rnd:condition",
        )
        for i, m in enumerate(ms.mappings)
    )
    return MappingConditionProfileCandidate(
        ms, rules, ms.effective, knowledge or ms.knowledge, "rnd:conditions",
    )


def run(p, source, facts=(), known_at=FEB, day=DAY):
    return resolve_conditional_mapping_candidate(
        profile=p, source_account_id=source.id,
        facts=tuple(facts), as_of=day, known_at=known_at,
    )


def provider(ms, source, x, y):
    return MappingProviderRequirementCandidate(
        ms, source.id, (x.id, y.id),
        SpecializedMappingProviderContract(
            "EXTERNAL_ALLOCATION", "1.0", ProviderCapability.ONE_TO_MANY_ALLOCATION,
            "SOURCE_FACTS_V1", "ALLOCATION_PROPOSAL_V1",
        ),
        VALID, PERIOD, "rnd:provider-intent",
    )


def test_equals_predicate_selects_only_matching_target_and_pins_digest():
    ms, a, _, x, y = sample()
    p = profile(ms, (predicate("RETAIL"),), (predicate("INDUSTRIAL"),))
    receipt = run(p, a, (MappingFact(MappingFactKey.SEGMENT, "RETAIL"),))
    assert isinstance(receipt, ConditionalMappingCandidateResolution)
    assert receipt.target_account_id == x.id
    assert receipt.target_account_id != y.id
    assert receipt.canonical_manifest()["status"] == "UNPUBLISHED_CONDITIONAL_MAPPING_PREVIEW"
    assert receipt.content_digest.startswith("sha256:")
    assert len(receipt.content_digest) == 71
    receipt.verify_integrity()


def test_one_of_condition_and_two_fact_and_expression_are_declarative_only():
    ms, a, _, _, y = sample()
    cond_a = (
        MappingPredicate(
            MappingFactKey.SEGMENT, PredicateOperator.ONE_OF, ("INDUSTRIAL", "RETAIL")
        ),
        MappingPredicate(
            MappingFactKey.ACTIVITY, PredicateOperator.EQUALS, ("SALE",)
        ),
    )
    p = profile(ms, cond_a, (predicate("GOVERNMENT"),))
    result = run(p, a, (
        MappingFact(MappingFactKey.ACTIVITY, "SALE"),
        MappingFact(MappingFactKey.SEGMENT, "RETAIL"),
    ))
    assert result.target_account_id == ms.mappings[0].target_account_id
    with pytest.raises(MappingCandidateMissing):
        run(p, a, (
            MappingFact(MappingFactKey.ACTIVITY, "PURCHASE"),
            MappingFact(MappingFactKey.SEGMENT, "RETAIL"),
        ))
    assert y.id not in [result.target_account_id]


def test_false_predicates_refuse_no_default_to_last_or_generic_account():
    ms, a, *_ = sample()
    p = profile(ms, (predicate("A"),), (predicate("B"),))
    with pytest.raises(MappingCandidateMissing, match="condition"):
        run(p, a, (MappingFact(MappingFactKey.SEGMENT, "C"),))


def test_missing_context_is_not_false_and_never_falls_back_to_unconditional():
    ms, a, *_ = sample()
    p = profile(ms, (predicate("A"),), ())
    with pytest.raises(MissingMappingFact, match="required"):
        run(p, a)
    with pytest.raises(MissingMappingFact):
        run(p, a, (MappingFact(MappingFactKey.ACTIVITY, "SALE"),))


def test_two_matching_conditions_fail_under_unique_policy():
    ms, a, *_ = sample()
    p = profile(ms, (predicate("A"),), (predicate("A"),))
    with pytest.raises(MappingCandidateAmbiguous, match="Multiple"):
        run(p, a, (MappingFact(MappingFactKey.SEGMENT, "A"),))


def test_explicit_unique_priority_selects_highest_condition_candidate():
    ms, a, _, _, y = sample(policy=MappingPrecedencePolicy.EXPLICIT_PRIORITY_RND)
    p = profile(ms, (predicate("A"),), (predicate("A"),))
    result = run(p, a, (MappingFact(MappingFactKey.SEGMENT, "A"),))
    assert result.target_account_id == y.id


def test_tied_priority_matching_fails_even_when_conditions_equal():
    ms, a, *_ = sample(policy=MappingPrecedencePolicy.EXPLICIT_PRIORITY_RND)
    revised = replace(ms.mappings[1], priority=1)
    ms = replace(ms, mappings=(ms.mappings[0], revised))
    p = profile(ms, (predicate("A"),), (predicate("A"),))
    with pytest.raises(MappingCandidateAmbiguous, match="Equal-priority"):
        run(p, a, (MappingFact(MappingFactKey.SEGMENT, "A"),))


@pytest.mark.parametrize(
    "bad", ["", " ", "retail", "A B", "ÉTRANGER", "a", "A" * 65]
)
def test_noncanonical_fact_value_rejected(bad):
    with pytest.raises(InvalidMappingCondition):
        MappingFact(MappingFactKey.SEGMENT, bad)


@pytest.mark.parametrize("op,expected", [
    (PredicateOperator.EQUALS, ()),
    (PredicateOperator.EQUALS, ("A", "B")),
    (PredicateOperator.ONE_OF, ()),
    (PredicateOperator.ONE_OF, ("A", "A")),
    (PredicateOperator.ONE_OF, ("invalid",)),
])
def test_invalid_predicate_cardinality_values_refused(op, expected):
    with pytest.raises(InvalidMappingCondition):
        MappingPredicate(MappingFactKey.SEGMENT, op, expected)


def test_condition_rules_reject_duplicate_fact_keys():
    ms, *_ = sample()
    with pytest.raises(InvalidMappingCondition, match="Duplicate"):
        MappingRuleCondition(
            ms.mappings[0].id, (predicate("A"), predicate("B")), "rnd:duplicate"
        )


def test_profile_requires_exactly_one_declaration_for_every_mapping():
    ms, *_ = sample()
    with pytest.raises(InvalidMappingCondition, match="exactly one"):
        replace(profile(ms), rules=())
    first = profile(ms).rules[0]
    with pytest.raises(InvalidMappingCondition, match="exactly one"):
        replace(profile(ms), rules=(first, first))
    with pytest.raises(InvalidMappingCondition, match="exactly one"):
        replace(profile(ms), rules=(
            first, MappingRuleCondition(AccountMappingCandidateId.new(), (), "rnd:foreign")
        ))


def test_duplicate_context_keys_are_refused():
    ms, a, *_ = sample()
    with pytest.raises(InvalidMappingCondition, match="Duplicate"):
        run(profile(ms), a, (
            MappingFact(MappingFactKey.SEGMENT, "A"),
            MappingFact(MappingFactKey.SEGMENT, "B"),
        ))


def test_canonical_conditions_and_receipt_ignore_input_order_and_timezone():
    ms, a, *_ = sample()
    p = profile(ms, (predicate("A"), predicate("B", key=MappingFactKey.ACTIVITY)), ())
    reordered = replace(
        p, rules=tuple(reversed(p.rules))
    )
    assert reordered.content_digest == p.content_digest
    facts = (MappingFact(MappingFactKey.ACTIVITY, "B"),
             MappingFact(MappingFactKey.SEGMENT, "A"))
    one = run(p, a, facts)
    two = run(reordered, a, tuple(reversed(facts)),
              known_at=FEB.astimezone(timezone(timedelta(hours=1))))
    assert one.content_digest == two.content_digest


def test_future_knowledge_profile_rejected_without_backfilling():
    ms, a, *_ = sample()
    p = profile(ms, knowledge=KnowledgeInterval(MAR))
    with pytest.raises(MappingCandidateMissing, match="profile"):
        run(p, a, known_at=FEB)


def test_tampered_profile_or_nested_mapping_digest_refused():
    ms, a, *_ = sample()
    p = profile(ms)
    receipt = run(p, a)
    object.__setattr__(p.rules[0], "source_ref", "tampered")
    with pytest.raises(MappingCandidateDigestMismatch):
        receipt.verify_integrity()
    ms2, a2, *_ = sample()
    p2 = profile(ms2)
    receipt2 = run(p2, a2)
    object.__setattr__(ms2.mappings[0], "source_ref", "tampered")
    with pytest.raises(MappingCandidateDigestMismatch):
        receipt2.verify_integrity()


def test_original_known_vs_restated_conditional_proposals_do_not_rewrite_history():
    ms, a, *_ = sample()
    old_set = replace(ms, knowledge=KnowledgeInterval(JAN, MAR))
    new_set = replace(ms, knowledge=KnowledgeInterval(MAR))
    old = profile(old_set, (predicate("RETAIL"),), ())
    new = profile(new_set, (), (predicate("RETAIL"),))
    ctx = (MappingFact(MappingFactKey.SEGMENT, "RETAIL"),)
    before = run(old, a, ctx, known_at=FEB)
    after = run(new, a, ctx, known_at=MAR)
    assert before.target_account_id != after.target_account_id
    assert before.content_digest != after.content_digest


def test_explicit_provider_requirement_never_returns_allocation_or_posting():
    ms, _, b, x, y = sample(pair_count=1)
    request = provider(ms, b, x, y)
    request.verify_integrity()
    assert len(request.target_account_ids) == 2
    assert request.canonical_manifest()["status"] == "MAPPING_REQUIRES_PROVIDER_UNFULFILLED"
    for name in ("execute", "allocate", "post", "run", "amount", "publish"):
        assert not hasattr(request, name)
        assert not hasattr(request.provider, name)
    with pytest.raises(MappingProviderRequired):
        require_specialized_provider_candidate(
            requirement=request, source_account_id=b.id, as_of=DAY, known_at=FEB
        )


def test_provider_requirement_rejects_one_target_duplicates_and_unknown_accounts():
    ms, _, b, x, y = sample(pair_count=1)
    req = provider(ms, b, x, y)
    for targets in ((x.id,), (x.id, x.id), (x.id, CompanyAccountId.new())):
        with pytest.raises(InvalidMappingCandidate):
            replace(req, target_account_ids=targets)


def test_provider_requirement_does_not_override_direct_mapping():
    ms, a, _, x, y = sample(pair_count=1)
    with pytest.raises(InvalidMappingCandidate, match="conflicts"):
        provider(ms, a, x, y)


def test_provider_capability_is_explicit_and_versioned():
    ms, _, b, x, y = sample(pair_count=1)
    req = provider(ms, b, x, y)
    with pytest.raises(InvalidMappingCandidate):
        replace(
            req, provider=replace(
                req.provider, capability=ProviderCapability.RECLASSIFICATION
            )
        )
    with pytest.raises(InvalidMappingCandidate):
        replace(req, provider=replace(req.provider, provider_version=" "))
    with pytest.raises(InvalidMappingCandidate):
        replace(req, provider=replace(req.provider, input_schema="bad"))


def test_provider_intent_outside_active_cutoff_is_never_executed():
    ms, _, b, x, y = sample(pair_count=1)
    req = provider(ms, b, x, y)
    with pytest.raises(InvalidMappingCandidate, match="No matching"):
        require_specialized_provider_candidate(
            requirement=req, source_account_id=b.id, as_of=DAY,
            known_at=datetime(2025, 12, 1, tzinfo=UTC)
        )


def test_coverage_explicitly_lists_unmapped_accounts_and_never_claims_approval():
    ms, a, b, *_ = sample(pair_count=1)
    result = preview_mapping_coverage_candidate(
        mapping_set=ms, as_of=DAY, known_at=FEB
    )
    rows = {r.source_account_id: r for r in result.rows}
    assert rows[a.id].disposition is CoverageDisposition.DIRECT_CANDIDATE
    assert rows[b.id].disposition is CoverageDisposition.UNMAPPED
    assert result.has_unresolved
    assert result.canonical_manifest()["status"] == "DIAGNOSTIC_ONLY_NOT_PUBLICATION"
    result.verify_integrity()


def test_coverage_conditions_are_unresolved_without_actual_context():
    ms, a, b, *_ = sample(pair_count=1)
    p = profile(ms, (predicate("RETAIL"),))
    result = preview_mapping_coverage_candidate(
        mapping_set=ms, as_of=DAY, known_at=FEB, conditions=p
    )
    dispositions = {r.source_account_id: r.disposition for r in result.rows}
    assert dispositions[a.id] is CoverageDisposition.CONDITIONAL_NEEDS_FACTS
    assert dispositions[b.id] is CoverageDisposition.UNMAPPED


def test_coverage_reports_provider_requirement_and_proposed_exception_separately():
    ms, a, b, x, y = sample(pair_count=1)
    req = provider(ms, b, x, y)
    report = preview_mapping_coverage_candidate(
        mapping_set=ms, as_of=DAY, known_at=FEB, providers=(req,),
    )
    assert {r.source_account_id: r.disposition for r in report.rows}[b.id] is (
        CoverageDisposition.PROVIDER_REQUIRED
    )
    exception = MappingCoverageExceptionCandidate(
        ms.id, b.id, "Proposed manual gap", VALID, PERIOD, "rnd:exception",
    )
    other = preview_mapping_coverage_candidate(
        mapping_set=ms, as_of=DAY, known_at=FEB, exceptions=(exception,),
    )
    assert {r.source_account_id: r.disposition for r in other.rows}[b.id] is (
        CoverageDisposition.EXCEPTION_DECLARED
    )
    assert other.has_unresolved
    assert report.content_digest != other.content_digest


def test_exception_cannot_silently_override_an_existing_mapping():
    ms, a, *_ = sample(pair_count=1)
    exc = MappingCoverageExceptionCandidate(
        ms.id, a.id, "No longer needed", VALID, PERIOD, "rnd:exc"
    )
    with pytest.raises(MappingCandidateAmbiguous, match="Exception cannot override"):
        preview_mapping_coverage_candidate(
            mapping_set=ms, as_of=DAY, known_at=FEB, exceptions=(exc,)
        )


def test_two_active_provider_requirements_are_ambiguous():
    ms, _, b, x, y = sample(pair_count=1)
    req = provider(ms, b, x, y)
    with pytest.raises(MappingCandidateAmbiguous, match="Overlapping provider"):
        preview_mapping_coverage_candidate(
            mapping_set=ms, as_of=DAY, known_at=FEB, providers=(req, req)
        )


def test_two_active_coverage_exceptions_are_ambiguous():
    ms, _, b, *_ = sample(pair_count=1)
    exc = MappingCoverageExceptionCandidate(
        ms.id, b.id, "A", VALID, PERIOD, "rnd:exc"
    )
    with pytest.raises(MappingCandidateAmbiguous, match="Overlapping coverage"):
        preview_mapping_coverage_candidate(
            mapping_set=ms, as_of=DAY, known_at=FEB, exceptions=(exc, exc)
        )


def test_coverage_conflicts_and_priority_are_only_structural():
    ms, a, b, *_ = sample()
    report = preview_mapping_coverage_candidate(mapping_set=ms, as_of=DAY, known_at=FEB)
    st = {r.source_account_id: r.disposition for r in report.rows}
    assert st[a.id] is CoverageDisposition.AMBIGUOUS
    assert st[b.id] is CoverageDisposition.UNMAPPED
    ms2, a2, *_ = sample(policy=MappingPrecedencePolicy.EXPLICIT_PRIORITY_RND)
    report2 = preview_mapping_coverage_candidate(
        mapping_set=ms2, as_of=DAY, known_at=FEB
    )
    assert {r.source_account_id: r.disposition for r in report2.rows}[a2.id] is (
        CoverageDisposition.DIRECT_CANDIDATE
    )


def test_coverage_digest_is_deterministic_independent_of_rule_order():
    ms, *_ = sample(pair_count=2)
    original = preview_mapping_coverage_candidate(
        mapping_set=ms, as_of=DAY, known_at=FEB
    )
    swapped = replace(ms, mappings=tuple(reversed(ms.mappings)))
    other = preview_mapping_coverage_candidate(
        mapping_set=swapped, as_of=DAY, known_at=FEB
    )
    assert original.content_digest == other.content_digest


def test_foreign_coverage_exception_or_provider_catalog_is_rejected():
    ms, _, b, x, y = sample(pair_count=1)
    foreign = MappingCoverageExceptionCandidate(
        MappingSetCandidateVersionId.new(), b.id, "Wrong set", VALID, PERIOD, "rnd:exc"
    )
    with pytest.raises(InvalidMappingCandidate, match="Foreign"):
        preview_mapping_coverage_candidate(
            mapping_set=ms, as_of=DAY, known_at=FEB, exceptions=(foreign,)
        )
    req = provider(ms, b, x, y)
    another, *_ = sample(pair_count=1)
    with pytest.raises(InvalidMappingCandidate, match="Foreign provider"):
        preview_mapping_coverage_candidate(
            mapping_set=another, as_of=DAY, known_at=FEB, providers=(req,)
        )


def test_coverage_fails_out_of_period_not_latest_fallback():
    ms, *_ = sample(pair_count=1)
    with pytest.raises(InvalidMappingCandidate, match="not effective/known"):
        preview_mapping_coverage_candidate(
            mapping_set=ms, as_of=DAY, known_at=MAR.replace(year=2025)
        )


def test_coverage_report_checksum_tamper_detected():
    ms, *_ = sample(pair_count=1)
    report = preview_mapping_coverage_candidate(
        mapping_set=ms, as_of=DAY, known_at=FEB
    )
    object.__setattr__(report, "content_digest", "sha256:" + "0" * 64)
    with pytest.raises(MappingCandidateDigestMismatch):
        report.verify_integrity()


def test_frozen_declarative_objects_have_no_amount_or_callable_code():
    ms, *_ = sample(pair_count=1)
    p = profile(ms)
    with pytest.raises(FrozenInstanceError):
        p.source_ref = "tampered"
    with pytest.raises(FrozenInstanceError):
        p.rules[0].source_ref = "tampered"
    for value in (p, p.rules[0]):
        for forbidden in ("eval", "execute", "allocate", "post", "publish", "amount"):
            assert not hasattr(value, forbidden)


def test_read_only_service_uses_distinct_fake_action_grants():
    ms, a, *_ = sample(pair_count=1)
    p = profile(ms)

    class Grants:
        allowed = set()

        def require(self, *, principal, action, scope):
            if action not in self.allowed:
                raise PermissionError("Candidate diagnostics grant denied")

    auth = Grants()
    svc = MappingDiagnosticsCandidateService(
        reader=MemoryMappingDiagnosticsCandidates(profiles=(p,)), authorization=auth
    )
    actor = TrustedPrincipal("rnd", "tenant-a")
    q = MappingDiagnosticsCandidateQuery(ms.scope, ms.id, DAY, FEB)
    with pytest.raises(PermissionError):
        svc.resolve(q, principal=actor, source_account_id=a.id, facts=())
    auth.allowed = {"chart.mapping.condition.candidate.preview"}
    assert svc.resolve(
        q, principal=actor, source_account_id=a.id, facts=()
    ).mapping_id == ms.mappings[0].id
    with pytest.raises(PermissionError):
        svc.coverage(q, principal=actor)
    auth.allowed.add("chart.mapping.coverage.candidate.preview")
    assert svc.coverage(q, principal=actor).has_unresolved
    with pytest.raises(PermissionError, match="Cross-tenant"):
        svc.coverage(q, principal=TrustedPrincipal("rnd", "tenant-b"))
    with pytest.raises(PermissionError, match="Unverified"):
        svc.coverage(q, principal="raw-user")


def test_malicious_reader_cannot_leak_unscoped_profile():
    ms, a, *_ = sample(pair_count=1)
    p = profile(ms)
    wrong_scope = replace(ms.scope, legal_entity_id=LegalEntityId.new())
    object.__setattr__(ms, "scope", wrong_scope)

    class BadReader:
        def profiles_for_scope(self, scope):
            return (p,)

    class Allow:
        def require(self, *, principal, action, scope):
            return None

    svc = MappingDiagnosticsCandidateService(reader=BadReader(), authorization=Allow())
    q = MappingDiagnosticsCandidateQuery(
        replace(wrong_scope, legal_entity_id=LegalEntityId.new()), ms.id, DAY, FEB
    )
    with pytest.raises(InvalidMappingCandidate, match="Leaked"):
        svc.resolve(
            q, principal=TrustedPrincipal("rnd", "tenant-a"),
            source_account_id=a.id, facts=(),
        )


def test_no_sql_posting_or_network_import_in_new_rnd_modules():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.application import chart_mapping_diagnostics
    from pyaccountingkit.company_configuration.domain.chart_of_accounts import (
        mapping_conditions,
        mapping_coverage,
        mapping_provider,
    )
    from pyaccountingkit.company_configuration.infrastructure import (
        chart_mapping_diagnostics_memory,
    )

    for module in (
        chart_mapping_diagnostics, chart_mapping_diagnostics_memory,
        mapping_conditions, mapping_coverage, mapping_provider,
    ):
        source = Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0] for node in ast.walk(tree)
            if isinstance(node, ast.Import) for alias in node.names
        }
        assert not {"psycopg", "sqlalchemy", "httpx", "requests"} & imports
        for word in ("organization_issuer_gateway", "Ledger.post", "eval(", "exec("):
            assert word not in source
