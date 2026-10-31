"""L05-04: deterministic 1:1 / N:1 mapping R&D and negative contracts."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from pyaccountingkit.company_configuration.application.chart_mapping_candidate_resolution import (
    AccountMappingCandidateResolutionService,
    ResolveAccountMappingCandidate,
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
    InvalidMappingCandidate,
    MappingCandidateAmbiguous,
    MappingCandidateDigestMismatch,
    MappingCandidateMissing,
    MappingKind,
    MappingPrecedencePolicy,
    MappingSetVersionCandidate,
    resolve_account_mapping_candidate,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
    KnowledgeInterval,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountingBookId,
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
from pyaccountingkit.company_configuration.infrastructure.chart_mapping_candidates_memory import (
    MemoryMappingSetCandidates,
)

JAN = datetime(2026, 1, 1, tzinfo=UTC)
MAR = datetime(2026, 3, 1, tzinfo=UTC)
FEB = datetime(2026, 2, 1, tzinfo=UTC)
DAY = date(2026, 2, 15)
JUL = date(2026, 7, 1)


def fixture():
    scope = ConfigurationScope(
        tenant_id="tenant-a", company_id=CompanyId.new(),
        legal_entity_id=LegalEntityId.new(),
    )
    local = CompanyChartDraft(
        CompanyChartId.new(), scope, ChartCode("LOCAL"), "Local chart",
        EffectiveInterval(date(2026, 1, 1)), "rnd:local"
    )
    group = CompanyChartDraft(
        CompanyChartId.new(), scope, ChartCode("GROUP"), "Group chart",
        EffectiveInterval(date(2026, 1, 1)), "rnd:group"
    )

    def acct(chart, code):
        return CompanyAccountDraft(
            CompanyAccountId.new(), chart.id, chart.scope, AccountCode(code),
            "Account " + code, AccountClassificationCode("LOCAL"), True,
            chart.effective, "rnd:account"
        )

    a = acct(local, "00123")
    b = acct(local, "00234")
    x = acct(group, "901")
    y = acct(group, "902")
    framework = ReferenceFrameworkRef("PCG", "TEST_2026")
    lv = CompanyChartVersionCandidate(
        CompanyChartCandidateVersionId.new(), local, (a, b), (), (),
        framework, local.effective, KnowledgeInterval(JAN), "rnd:source-version"
    )
    gv = CompanyChartVersionCandidate(
        CompanyChartCandidateVersionId.new(), group, (x, y), (), (),
        framework, group.effective, KnowledgeInterval(JAN), "rnd:target-version"
    )
    return scope, lv, gv, a, b, x, y


def rule(
    context, source, target, *,
    set_id, identity=None, kind=MappingKind.DIRECT_ONE_TO_ONE,
    effective=None, priority=None, scope=None, source_version=None, target_version=None,
):
    s, lv, gv, _, _, _, _ = context
    return AccountMappingCandidate(
        id=identity or AccountMappingCandidateId.new(),
        mapping_set_version_id=set_id,
        scope=scope or s,
        source_chart_version_id=source_version or lv.id,
        source_account_id=source.id,
        target_chart_version_id=target_version or gv.id,
        target_account_id=target.id,
        kind=kind,
        effective=effective or EffectiveInterval(date(2026, 1, 1)),
        source_ref="rnd:rule",
        priority=priority,
    )


def mapping_set(
    context, definitions, *, set_id=None,
    precedence=MappingPrecedencePolicy.REQUIRE_UNIQUE,
    effective=None, knowledge=None, scope=None, local=None, group=None
):
    s, lv, gv, *_ = context
    identity = set_id or MappingSetCandidateVersionId.new()
    rules = tuple(
        rule(context, src, dst, set_id=identity, **options)
        for src, dst, options in definitions
    )
    return MappingSetVersionCandidate(
        identity, scope or s, local or lv, group or gv, rules, precedence,
        effective or EffectiveInterval(date(2026, 1, 1)),
        knowledge or KnowledgeInterval(JAN), "rnd:mapping-set",
    )


def definitions(ctx, *, kind=MappingKind.DIRECT_ONE_TO_ONE):
    _, _, _, a, _, x, _ = ctx
    return ((a, x, {"kind": kind}),)


def resolve(ctx, catalogs, source, *, day=DAY, known_at=FEB, scope=None):
    s = scope or ctx[0]
    return resolve_account_mapping_candidate(
        scope=s, source_account_id=source.id, as_of=day,
        known_at=known_at, mapping_sets=tuple(catalogs)
    )


def test_direct_one_to_one_is_exactly_one_account_not_financial_operation():
    ctx = fixture()
    mset = mapping_set(ctx, definitions(ctx))
    res = resolve(ctx, (mset,), ctx[3])
    assert res.mapping.kind is MappingKind.DIRECT_ONE_TO_ONE
    assert res.mapping.source_account_id == ctx[3].id
    assert res.mapping.target_account_id == ctx[5].id
    assert res.mapping_set.id == mset.id
    assert ctx[3].code.value == "00123"
    assert res.content_digest.startswith("sha256:")
    assert len(res.content_digest) == 71
    assert "amount" not in str(res.canonical_manifest()).lower()
    for forbidden in ("amount", "journal", "post", "publish", "allocate", "execute"):
        assert not hasattr(res, forbidden)
    res.verify_integrity()


def test_mapping_set_digest_is_independent_of_input_order():
    ctx = fixture()
    _, _, _, a, b, x, y = ctx
    mset = mapping_set(ctx, ((a, x, {}), (b, y, {})))
    reversed_catalog = replace(mset, mappings=tuple(reversed(mset.mappings)))
    assert reversed_catalog.content_digest == mset.content_digest
    assert reversed_catalog.canonical_manifest() == mset.canonical_manifest()


def test_n_to_one_uses_explicit_semantics_without_posting_or_aggregation_amounts():
    ctx = fixture()
    _, _, _, a, b, x, _ = ctx
    mset = mapping_set(
        ctx, (
            (a, x, {"kind": MappingKind.AGGREGATE_MANY_TO_ONE}),
            (b, x, {"kind": MappingKind.AGGREGATE_MANY_TO_ONE}),
        ),
    )
    ra = resolve(ctx, (mset,), a)
    rb = resolve(ctx, (mset,), b)
    assert ra.mapping.target_account_id == rb.mapping.target_account_id == x.id
    assert ra.mapping.id != rb.mapping.id
    assert "amount" not in str(ra.canonical_manifest()).lower()


def test_direct_rules_cannot_implicitly_converge_to_same_target():
    ctx = fixture()
    _, _, _, a, b, x, _ = ctx
    with pytest.raises(InvalidMappingCandidate, match="N:1"):
        mapping_set(ctx, (
            (a, x, {}),
            (b, x, {}),
        ))


def test_mixed_direct_and_aggregate_to_same_target_is_rejected():
    ctx = fixture()
    _, _, _, a, b, x, _ = ctx
    with pytest.raises(InvalidMappingCandidate, match="N:1"):
        mapping_set(ctx, (
            (a, x, {"kind": MappingKind.AGGREGATE_MANY_TO_ONE}),
            (b, x, {"kind": MappingKind.DIRECT_ONE_TO_ONE}),
        ))


def test_one_to_many_kind_is_not_in_prototype_enum():
    assert {kind.value for kind in MappingKind} == {
        "DIRECT_ONE_TO_ONE", "AGGREGATE_MANY_TO_ONE"
    }
    ctx = fixture()
    with pytest.raises(InvalidMappingCandidate, match="kind"):
        mapping_set(ctx, ((ctx[3], ctx[5], {"kind": "ONE_TO_MANY"}),))


def test_missing_required_mapping_refuses_generic_or_latest_fallback():
    ctx = fixture()
    mset = mapping_set(ctx, definitions(ctx))
    with pytest.raises(MappingCandidateMissing, match="explicit"):
        resolve(ctx, (mset,), ctx[4])
    with pytest.raises(MappingCandidateMissing, match="mapping-set"):
        resolve(ctx, (), ctx[3])


def test_two_same_source_different_targets_without_policy_are_ambiguous():
    ctx = fixture()
    _, _, _, a, _, x, y = ctx
    mset = mapping_set(ctx, ((a, x, {}), (a, y, {})))
    with pytest.raises(MappingCandidateAmbiguous, match="precedence"):
        resolve(ctx, (mset,), a)


def test_explicit_rnd_priority_selects_one_target_never_allocates():
    ctx = fixture()
    _, _, _, a, _, x, y = ctx
    mset = mapping_set(
        ctx,
        ((a, x, {"priority": 2}), (a, y, {"priority": 7})),
        precedence=MappingPrecedencePolicy.EXPLICIT_PRIORITY_RND,
    )
    result = resolve(ctx, (mset,), a)
    assert result.mapping.target_account_id == y.id
    assert result.mapping.priority == 7
    assert result.canonical_manifest()["status"] == "UNPUBLISHED_RND_MAPPING_RESOLUTION"


def test_tied_highest_priority_fails_instead_of_uuid_order():
    ctx = fixture()
    _, _, _, a, _, x, y = ctx
    mset = mapping_set(
        ctx,
        ((a, x, {"priority": 7}), (a, y, {"priority": 7})),
        precedence=MappingPrecedencePolicy.EXPLICIT_PRIORITY_RND,
    )
    with pytest.raises(MappingCandidateAmbiguous, match="Equal-priority"):
        resolve(ctx, (mset,), a)


def test_priority_without_policy_or_rank_missing_with_policy_fails():
    ctx = fixture()
    _, _, _, a, _, x, _ = ctx
    with pytest.raises(InvalidMappingCandidate, match="without explicit"):
        mapping_set(ctx, ((a, x, {"priority": 5}),))
    with pytest.raises(InvalidMappingCandidate, match="every rank"):
        mapping_set(
            ctx, ((a, x, {}),),
            precedence=MappingPrecedencePolicy.EXPLICIT_PRIORITY_RND,
        )


@pytest.mark.parametrize("priority", [-1, True, 1.5, "2"])
def test_priority_must_be_canonical_nonnegative_integer(priority):
    ctx = fixture()
    with pytest.raises(InvalidMappingCandidate, match="integer priority"):
        mapping_set(ctx, ((ctx[3], ctx[5], {"priority": priority}),))


def test_business_date_filter_and_half_open_change_are_deterministic():
    ctx = fixture()
    _, _, _, a, _, x, y = ctx
    mset = mapping_set(
        ctx, (
            (a, x, {"effective": EffectiveInterval(date(2026, 1, 1), JUL)}),
            (a, y, {"effective": EffectiveInterval(JUL)}),
        ),
    )
    before = resolve(ctx, (mset,), a)
    after = resolve(ctx, (mset,), a, day=JUL)
    assert before.mapping.target_account_id == x.id
    assert after.mapping.target_account_id == y.id


def test_future_effective_mapping_is_never_defaulted_to_current():
    ctx = fixture()
    mset = mapping_set(
        ctx, ((ctx[3], ctx[5], {"effective": EffectiveInterval(JUL)}),)
    )
    with pytest.raises(MappingCandidateMissing, match="explicit"):
        resolve(ctx, (mset,), ctx[3])


def test_future_mapping_set_is_unavailable_for_earlier_business_day():
    ctx = fixture()
    mset = mapping_set(
        ctx, ((ctx[3], ctx[5], {"effective": EffectiveInterval(JUL)}),),
        effective=EffectiveInterval(JUL),
    )
    with pytest.raises(MappingCandidateMissing, match="mapping-set"):
        resolve(ctx, (mset,), ctx[3])


def test_future_knowledge_is_not_replayed_at_old_known_at():
    ctx = fixture()
    mset = mapping_set(
        ctx, definitions(ctx), knowledge=KnowledgeInterval(MAR),
    )
    with pytest.raises(MappingCandidateMissing, match="mapping-set"):
        resolve(ctx, (mset,), ctx[3], known_at=FEB)


def test_original_known_mapping_and_later_restated_mapping_are_distinct():
    ctx = fixture()
    _, _, _, a, _, x, y = ctx
    old = mapping_set(
        ctx, ((a, x, {}),), knowledge=KnowledgeInterval(JAN, MAR)
    )
    new = mapping_set(ctx, ((a, y, {}),), knowledge=KnowledgeInterval(MAR))
    originally_known = resolve(ctx, (old, new), a, known_at=FEB)
    restated = resolve(ctx, (old, new), a, known_at=MAR)
    assert originally_known.mapping.target_account_id == x.id
    assert restated.mapping.target_account_id == y.id
    assert originally_known.content_digest != restated.content_digest
    originally_known.verify_integrity()
    restated.verify_integrity()


def test_overlapping_mapping_sets_are_ambiguous_not_latest_wins():
    ctx = fixture()
    first = mapping_set(ctx, definitions(ctx))
    second = mapping_set(ctx, definitions(ctx))
    with pytest.raises(MappingCandidateAmbiguous, match="Concurrent"):
        resolve(ctx, (first, second), ctx[3])


def test_duplicate_set_id_even_in_disjoint_knowledge_is_denied():
    ctx = fixture()
    identity = MappingSetCandidateVersionId.new()
    first = mapping_set(ctx, definitions(ctx), set_id=identity,
                        knowledge=KnowledgeInterval(JAN, MAR))
    second = mapping_set(ctx, definitions(ctx), set_id=identity,
                         knowledge=KnowledgeInterval(MAR))
    with pytest.raises(MappingCandidateAmbiguous, match="Duplicate mapping-set"):
        resolve(ctx, (first, second), ctx[3])


def test_duplicate_rule_identity_inside_set_rejected():
    ctx = fixture()
    mset = mapping_set(ctx, definitions(ctx))
    # dataclasses.replace recreates and validates, it cannot seal duplicate IDs
    with pytest.raises(MappingCandidateAmbiguous, match="Duplicate mapping"):
        replace(mset, mappings=(mset.mappings[0], mset.mappings[0]))


def test_mapping_rejects_target_account_absent_from_declared_target_chart():
    ctx = fixture()
    with pytest.raises(InvalidMappingCandidate, match="absent"):
        mapping_set(
            ctx, ((ctx[3], ctx[4], {}),)
        )


def test_mapping_rejects_source_account_absent_from_declared_source_chart():
    ctx = fixture()
    with pytest.raises(InvalidMappingCandidate, match="absent"):
        mapping_set(
            ctx, ((ctx[5], ctx[6], {}),)
        )


def test_mapping_rejects_wrong_chart_version_ids_or_mapping_set_identity():
    ctx = fixture()
    mset = mapping_set(ctx, definitions(ctx))
    rule_one = mset.mappings[0]
    for change in (
        {"mapping_set_version_id": MappingSetCandidateVersionId.new()},
        {"source_chart_version_id": CompanyChartCandidateVersionId.new()},
        {"target_chart_version_id": CompanyChartCandidateVersionId.new()},
    ):
        with pytest.raises(InvalidMappingCandidate, match="version"):
            replace(mset, mappings=(replace(rule_one, **change),))


def test_mapping_scope_and_version_cross_tenant_fail_closed():
    ctx = fixture()
    bad_scope = replace(ctx[0], legal_entity_id=LegalEntityId.new())
    with pytest.raises(InvalidMappingCandidate, match="Cross-tenant/entity"):
        mapping_set(ctx, definitions(ctx), scope=bad_scope)
    mset = mapping_set(ctx, definitions(ctx))
    with pytest.raises(InvalidMappingCandidate, match="scope"):
        replace(
            mset, mappings=(replace(mset.mappings[0], scope=bad_scope),)
        )


def test_foreign_mapping_set_even_if_not_applicable_is_refused():
    ctx = fixture()
    mset = mapping_set(ctx, definitions(ctx))
    mutated = replace(mset.scope, tenant_id="tenant-b")
    object.__setattr__(mset, "scope", mutated)
    with pytest.raises(InvalidMappingCandidate, match="Foreign"):
        resolve(ctx, (mset,), ctx[3])


def test_mapping_period_cannot_extend_beyond_set_or_account():
    ctx = fixture()
    with pytest.raises(InvalidMappingCandidate, match="validity"):
        mapping_set(
            ctx, definitions(ctx),
            effective=EffectiveInterval(date(2026, 1, 1), JUL),
        )


def test_mapping_set_cannot_outlive_source_chart_version_or_knowledge():
    ctx = fixture()
    v = ctx[1]
    expired = replace(v, knowledge=KnowledgeInterval(JAN, MAR))
    with pytest.raises(InvalidMappingCandidate, match="knowledge"):
        mapping_set(
            ctx, definitions(ctx), local=expired,
            knowledge=KnowledgeInterval(JAN),
        )


def test_untyped_scope_dates_and_catalog_are_rejected():
    ctx = fixture()
    mset = mapping_set(ctx, definitions(ctx))
    with pytest.raises(InvalidMappingCandidate):
        resolve_account_mapping_candidate(
            scope=replace(ctx[0], book_id=AccountingBookId.new()),
            source_account_id=ctx[3].id, as_of=DAY, known_at=FEB,
            mapping_sets=(mset,),
        )
    with pytest.raises(InvalidMappingCandidate):
        resolve_account_mapping_candidate(
            scope=ctx[0], source_account_id=ctx[3].id,
            as_of=datetime(2026, 2, 15), known_at=FEB, mapping_sets=(mset,),
        )
    with pytest.raises(InvalidMappingCandidate):
        resolve_account_mapping_candidate(
            scope=ctx[0], source_account_id=ctx[3].id, as_of=DAY,
            known_at=datetime(2026, 2, 1), mapping_sets=(mset,),
        )
    with pytest.raises(InvalidMappingCandidate):
        resolve_account_mapping_candidate(
            scope=ctx[0], source_account_id=ctx[3].id, as_of=DAY,
            known_at=FEB, mapping_sets=[mset],
        )


def test_duplicate_or_non_typed_catalog_is_rejected():
    ctx = fixture()
    with pytest.raises(InvalidMappingCandidate, match="non-mapping set"):
        resolve(ctx, ("bad",), ctx[3])


def test_integrity_mutated_rule_is_detected():
    ctx = fixture()
    mset = mapping_set(ctx, definitions(ctx))
    result = resolve(ctx, (mset,), ctx[3])
    object.__setattr__(mset.mappings[0], "source_ref", "tampered")
    with pytest.raises(MappingCandidateDigestMismatch):
        result.verify_integrity()


def test_integrity_mutated_source_chart_account_detected():
    ctx = fixture()
    mset = mapping_set(ctx, definitions(ctx))
    result = resolve(ctx, (mset,), ctx[3])
    object.__setattr__(ctx[3], "label", "changed")
    with pytest.raises(Exception, match="altered"):
        result.verify_integrity()


def test_integrity_mutated_resolution_receipt_is_detected():
    ctx = fixture()
    mset = mapping_set(ctx, definitions(ctx))
    result = resolve(ctx, (mset,), ctx[3])
    object.__setattr__(result, "content_digest", "sha256:" + "0" * 64)
    with pytest.raises(MappingCandidateDigestMismatch):
        result.verify_integrity()


def test_mapping_and_set_are_frozen_values():
    ctx = fixture()
    mset = mapping_set(ctx, definitions(ctx))
    with pytest.raises(FrozenInstanceError):
        mset.source_ref = "tampered"
    with pytest.raises(FrozenInstanceError):
        mset.mappings[0].priority = 1


def test_known_at_timezone_is_canonicalized_to_utc():
    ctx = fixture()
    mset = mapping_set(ctx, definitions(ctx))
    a = resolve(ctx, (mset,), ctx[3], known_at=FEB)
    offset = FEB.astimezone(timezone(timedelta(hours=2)))
    b = resolve(ctx, (mset,), ctx[3], known_at=offset)
    assert a.content_digest == b.content_digest


def test_memory_adapter_is_read_only_and_scope_specific():
    ctx = fixture()
    mset = mapping_set(ctx, definitions(ctx))
    reader = MemoryMappingSetCandidates((mset,))
    assert reader.list_for_scope(ctx[0]) == (mset,)
    assert reader.list_for_scope(
        replace(ctx[0], company_id=CompanyId.new())
    ) == ()
    assert not hasattr(reader, "publish")
    assert not hasattr(reader, "save")


def test_application_service_requires_scoped_fake_grant():
    ctx = fixture()
    mset = mapping_set(ctx, definitions(ctx))
    actor = TrustedPrincipal("rnd-reviewer", "tenant-a")

    class Access:
        allowed = False

        def require(self, *, principal, action, scope):
            assert action == "chart.mapping.candidate.resolve"
            if not self.allowed:
                raise PermissionError("No preview action grant")

    auth = Access()
    svc = AccountMappingCandidateResolutionService(
        sets=MemoryMappingSetCandidates((mset,)), authorization=auth
    )
    query = ResolveAccountMappingCandidate(ctx[0], ctx[3].id, DAY, FEB)
    with pytest.raises(PermissionError, match="grant"):
        svc.resolve(query, principal=actor)
    auth.allowed = True
    assert svc.resolve(query, principal=actor).mapping.target_account_id == ctx[5].id
    with pytest.raises(PermissionError, match="Cross-tenant"):
        svc.resolve(query, principal=TrustedPrincipal("rnd-reviewer", "tenant-b"))
    with pytest.raises(PermissionError, match="Unverified"):
        svc.resolve(query, principal="untrusted:actor")


def test_malicious_reader_leak_is_denied_by_pure_domain():
    ctx = fixture()
    mset = mapping_set(ctx, definitions(ctx))
    fake_scope = replace(ctx[0], tenant_id="tenant-b")
    object.__setattr__(mset, "scope", fake_scope)

    class MaliciousReader:
        def list_for_scope(self, ignored):
            return (mset,)

    class Allow:
        def require(self, *, principal, action, scope):
            return None

    svc = AccountMappingCandidateResolutionService(
        sets=MaliciousReader(), authorization=Allow()
    )
    with pytest.raises(InvalidMappingCandidate, match="Foreign"):
        svc.resolve(
            ResolveAccountMappingCandidate(ctx[0], ctx[3].id, DAY, FEB),
            principal=TrustedPrincipal("rnd-reviewer", "tenant-a")
        )


def test_architecture_has_no_sql_ledger_or_implicit_allocation_operations():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.application import (
        chart_mapping_candidate_resolution,
    )
    from pyaccountingkit.company_configuration.domain.chart_of_accounts import mapping
    from pyaccountingkit.company_configuration.infrastructure import (
        chart_mapping_candidates_memory,
    )

    for module in (
        chart_mapping_candidate_resolution, chart_mapping_candidates_memory, mapping,
    ):
        text = Path(module.__file__).read_text(encoding="utf-8")
        imports = {
            alias.name.split(".")[0] for node in ast.walk(ast.parse(text))
            if isinstance(node, ast.Import) for alias in node.names
        }
        assert not ({"psycopg", "sqlalchemy", "requests", "httpx"} & imports)
        assert "organization_issuer_gateway" not in text
        assert not hasattr(module, "post")
        assert not hasattr(module, "allocate")
        assert not hasattr(module, "publish")
