"""L05-03: exact-version and bitemporal Chart/Book binding R&D proof."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from pyaccountingkit.company_configuration.application.chart_candidate_preview import (
    BookChartCandidatePreviewService,
    PreviewBookChartCandidate,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal
from pyaccountingkit.company_configuration.domain.chart_of_accounts import (
    AccountClassificationCode,
    AccountCode,
    AccountHierarchyEdgeCandidate,
    AccountStatusCandidate,
    AccountStatusProposal,
    BookChartBindingCandidate,
    BookChartCandidateAmbiguous,
    BookChartCandidateMissing,
    BookChartPurpose,
    ChartCandidateDigestMismatch,
    ChartCode,
    ChartFrameworkClaimMismatch,
    CompanyAccountDraft,
    CompanyChartDraft,
    CompanyChartVersionCandidate,
    HierarchyCycle,
    HierarchyViewCode,
    InvalidBookChartBinding,
    InvalidChartCandidateVersion,
    preview_book_chart_candidate,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
    KnowledgeInterval,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountHierarchyEdgeId,
    AccountingBookId,
    AccountStatusCandidateId,
    BookChartBindingCandidateId,
    CompanyAccountId,
    CompanyChartCandidateVersionId,
    CompanyChartId,
    CompanyId,
    LegalEntityId,
)
from pyaccountingkit.company_configuration.domain.shared.references import (
    ReferenceFrameworkRef,
)
from pyaccountingkit.company_configuration.infrastructure.chart_candidate_preview_memory import (
    MemoryBookChartBindings,
    MemoryChartCandidateVersions,
)


JAN = datetime(2026, 1, 1, tzinfo=UTC)
MAR = datetime(2026, 3, 1, tzinfo=UTC)
FEB = datetime(2026, 2, 1, tzinfo=UTC)
BUSINESS = date(2026, 2, 15)
PURPOSE = BookChartPurpose("STATUTORY")
FRAMEWORK = ReferenceFrameworkRef("PCG", "TEST_2026")


def chart():
    return CompanyChartDraft(
        id=CompanyChartId.new(),
        scope=ConfigurationScope("tenant-a", CompanyId.new(), LegalEntityId.new()),
        code=ChartCode("COA"), label="Test draft chart",
        effective=EffectiveInterval(date(2026, 1, 1)), source_ref="rnd:chart",
    )


def account(c, *, code="00123", label="Draft account"):
    return CompanyAccountDraft(
        id=CompanyAccountId.new(), chart_id=c.id, scope=c.scope,
        code=AccountCode(code), label=label,
        classification=AccountClassificationCode("LOCAL"),
        postable=True, effective=c.effective, source_ref="rnd:account",
    )


def edge(c, child, parent):
    return AccountHierarchyEdgeCandidate(
        id=AccountHierarchyEdgeId.new(), scope=c.scope, chart_id=c.id,
        view=HierarchyViewCode("TREE"), child_id=child.id, parent_id=parent.id,
        effective=c.effective, source_ref="rnd:edge",
    )


def status(c, a, *, active=True):
    return AccountStatusCandidate(
        id=AccountStatusCandidateId.new(), scope=c.scope,
        chart_id=c.id, account_id=a.id,
        status=(
            AccountStatusProposal.PROPOSED_ENABLED
            if active else AccountStatusProposal.PROPOSED_SUSPENDED
        ),
        effective=c.effective, source_ref="rnd:status",
    )


def version(
    c, accounts=(), edges=(), statuses=(), *,
    identity=None, knowledge=None, framework=FRAMEWORK, effective=None
):
    return CompanyChartVersionCandidate(
        id=identity or CompanyChartCandidateVersionId.new(),
        chart=c,
        accounts=accounts,
        edges=edges,
        statuses=statuses,
        declared_framework=framework,
        effective=effective or c.effective,
        knowledge=knowledge or KnowledgeInterval(JAN),
        source_ref="rnd:chart-version",
    )


def binding(c, v, *, identity=None, scope=None, knowledge=None, effective=None,
            framework=FRAMEWORK, purpose=PURPOSE):
    return BookChartBindingCandidate(
        id=identity or BookChartBindingCandidateId.new(),
        book_scope=scope or replace(c.scope, book_id=AccountingBookId.new()),
        purpose=purpose,
        chart_id=c.id, chart_version_id=v.id,
        declared_book_framework=framework,
        effective=effective or c.effective,
        knowledge=knowledge or KnowledgeInterval(JAN),
        source_ref="rnd:binding",
    )


def run(b, versions, bindings=None, *, day=BUSINESS, known_at=FEB):
    return preview_book_chart_candidate(
        book_scope=b.book_scope,
        purpose=b.purpose,
        as_of=day,
        known_at=known_at,
        chart_versions=tuple(versions),
        bindings=tuple(bindings if bindings is not None else (b,)),
    )


def test_version_digest_includes_complete_chart_accounts_edges_and_statuses():
    c = chart()
    parent, leaf = account(c, code="60"), account(c, code="0061")
    link = edge(c, leaf, parent)
    state = status(c, leaf)
    v = version(c, (parent, leaf), (link,), (state,))
    assert v.content_digest.startswith("sha256:") and len(v.content_digest) == 71
    v.verify_integrity()
    assert "0061" in str(v.canonical_manifest())
    assert v.chart.id == c.id
    assert "UNPUBLISHED" not in type(v).__name__
    assert not hasattr(v, "publish")
    assert not hasattr(v, "post")


def test_canonical_version_digest_is_independent_of_input_catalog_order():
    c = chart()
    a, d = account(c, code="01"), account(c, code="02")
    e = edge(c, a, d)
    sa, sd = status(c, a), status(c, d)
    vid = CompanyChartCandidateVersionId.new()
    first = version(c, (a, d), (e,), (sa, sd), identity=vid)
    second = version(c, (d, a), (e,), (sd, sa), identity=vid)
    assert first.content_digest == second.content_digest
    assert first.canonical_manifest() == second.canonical_manifest()


def test_positive_exact_book_chart_version_receipt_and_integrity():
    c = chart()
    leaf = account(c, code="00123")
    v = version(c, (leaf,), statuses=(status(c, leaf),))
    b = binding(c, v)
    receipt = run(b, (v,))
    receipt.verify_integrity()
    assert receipt.chart_version.id == v.id
    assert receipt.chart_version.content_digest == v.content_digest
    assert receipt.binding.id == b.id
    assert receipt.content_digest.startswith("sha256:")
    assert receipt.canonical_manifest()["status"] == "UNPUBLISHED_RND_PREVIEW"
    assert not hasattr(receipt, "post")
    assert not hasattr(receipt, "publish")


def test_historical_restatement_keeps_original_version_and_binding():
    c = chart()
    a = account(c)
    first = version(c, (a,), knowledge=KnowledgeInterval(JAN, MAR))
    revised = replace(a, label="New account", revision=2)
    second = version(c, (revised,), knowledge=KnowledgeInterval(MAR))
    scope = replace(c.scope, book_id=AccountingBookId.new())
    old_binding = binding(
        c, first, scope=scope, knowledge=KnowledgeInterval(JAN, MAR)
    )
    new_binding = binding(c, second, scope=scope, knowledge=KnowledgeInterval(MAR))
    originals = (old_binding, new_binding)
    originally_known = run(
        old_binding, (first, second), originals, known_at=FEB
    )
    restated = run(old_binding, (first, second), originals, known_at=MAR)
    assert originally_known.chart_version.id == first.id
    assert restated.chart_version.id == second.id
    assert originally_known.content_digest != restated.content_digest
    assert originally_known.chart_version.accounts[0].label == "Draft account"
    assert restated.chart_version.accounts[0].label == "New account"
    originally_known.verify_integrity()
    restated.verify_integrity()


def test_future_recorded_binding_does_not_become_visible_in_old_replay():
    c = chart()
    v = version(c)
    b = binding(c, v, knowledge=KnowledgeInterval(MAR))
    with pytest.raises(BookChartCandidateMissing):
        run(b, (v,), known_at=FEB)


def test_future_recorded_version_is_not_available_for_old_known_at():
    c = chart()
    v = version(c, knowledge=KnowledgeInterval(MAR))
    b = binding(c, v)
    with pytest.raises(InvalidBookChartBinding, match="temporal"):
        run(b, (v,), known_at=FEB)


def test_no_fallback_to_unbound_latest_chart_version():
    c = chart()
    old = version(c, knowledge=KnowledgeInterval(JAN, MAR))
    latest = version(c, knowledge=KnowledgeInterval(MAR))
    b = binding(c, old, knowledge=KnowledgeInterval(MAR))
    with pytest.raises(InvalidBookChartBinding, match="temporal"):
        run(b, (old, latest), known_at=MAR)


def test_binding_references_unknown_version_fails_without_latest_fallback():
    c = chart()
    v = version(c)
    another = version(c)
    b = binding(c, v)
    with pytest.raises(BookChartCandidateMissing, match="exact"):
        run(b, (another,))


def test_two_book_bindings_same_date_purpose_are_explicit_conflict():
    c = chart()
    v = version(c)
    b = binding(c, v)
    other = binding(c, v, scope=b.book_scope)
    with pytest.raises(BookChartCandidateAmbiguous, match="Concurrent"):
        run(b, (v,), (b, other))


def test_adjacent_half_open_business_bindings_have_no_overlap():
    c = chart()
    v = version(c)
    scope = replace(c.scope, book_id=AccountingBookId.new())
    first = binding(
        c, v, scope=scope,
        effective=EffectiveInterval(date(2026, 1, 1), date(2026, 7, 1)),
    )
    second = binding(
        c, v, scope=scope, effective=EffectiveInterval(date(2026, 7, 1))
    )
    assert run(first, (v,), (first, second)).binding.id == first.id
    assert run(first, (v,), (first, second), day=date(2026, 7, 1)
               ).binding.id == second.id


def test_duplicate_binding_identity_rejected_even_when_intervals_disjoint():
    c = chart()
    v = version(c)
    first = binding(
        c, v, effective=EffectiveInterval(date(2026, 1, 1), date(2026, 7, 1))
    )
    second = replace(
        first, effective=EffectiveInterval(date(2026, 7, 1))
    )
    with pytest.raises(BookChartCandidateAmbiguous, match="Repeated binding"):
        run(first, (v,), (first, second))


def test_duplicate_chart_version_identity_fails_even_for_out_of_time_record():
    c = chart()
    identity = CompanyChartCandidateVersionId.new()
    first = version(c, identity=identity)
    second = version(c, identity=identity, knowledge=KnowledgeInterval(MAR))
    b = binding(c, first)
    with pytest.raises(BookChartCandidateAmbiguous, match="Repeated chart version"):
        run(b, (first, second))


def test_framework_claim_edition_mismatch_is_not_silent_compatibility():
    c = chart()
    v = version(c)
    b = binding(c, v, framework=ReferenceFrameworkRef("PCG", "TEST_2025"))
    with pytest.raises(ChartFrameworkClaimMismatch):
        run(b, (v,))


def test_matching_framework_pointers_are_not_evidence_of_normative_compliance():
    c = chart()
    v = version(c, framework=ReferenceFrameworkRef("IFRS", "FAKE_TEST"))
    b = binding(c, v, framework=ReferenceFrameworkRef("IFRS", "FAKE_TEST"))
    result = run(b, (v,))
    assert result.chart_version.declared_framework == b.declared_book_framework
    assert "compliance" not in result.canonical_manifest()
    assert not hasattr(result, "verify_normative_authority")


def test_wrong_tenant_company_legal_entity_book_scope_denied():
    c = chart()
    v = version(c)
    b = binding(c, v)
    for altered in (
        replace(b, book_scope=replace(b.book_scope, tenant_id="tenant-b")),
        replace(b, book_scope=replace(b.book_scope, company_id=CompanyId.new())),
        replace(b, book_scope=replace(b.book_scope, legal_entity_id=LegalEntityId.new())),
        replace(b, book_scope=replace(b.book_scope, book_id=AccountingBookId.new())),
    ):
        with pytest.raises(InvalidBookChartBinding, match="Foreign book"):
            run(b, (v,), (altered,))


def test_cross_scope_version_reader_fails_closed_not_filtered():
    c = chart()
    v = version(c)
    b = binding(c, v)
    foreign = version(chart())
    with pytest.raises(InvalidChartCandidateVersion, match="Foreign chart"):
        run(b, (v, foreign))


def test_binding_cannot_escape_chart_version_effective_window():
    c = chart()
    v = version(c, effective=EffectiveInterval(date(2026, 1, 1),
                                             date(2026, 4, 1)))
    b = binding(c, v, effective=EffectiveInterval(date(2026, 1, 1)))
    with pytest.raises(InvalidBookChartBinding, match="temporal"):
        run(b, (v,))


def test_chart_version_effective_must_fit_chart_draft():
    c = chart()
    with pytest.raises(InvalidChartCandidateVersion, match="escapes"):
        version(c, effective=EffectiveInterval(date(2025, 1, 1)))


def test_version_rejects_duplicate_account_codes_and_hierarchy_cycle():
    c = chart()
    a, d = account(c, code="01"), account(c, code="01")
    with pytest.raises(Exception, match="Overlapping account codes"):
        version(c, (a, d))
    a, d = account(c, code="01"), account(c, code="02")
    with pytest.raises(HierarchyCycle):
        version(c, (a, d), (edge(c, a, d), edge(c, d, a)))


def test_version_rejects_overlapping_status_proposals_before_any_query():
    c = chart()
    a = account(c)
    with pytest.raises(InvalidChartCandidateVersion, match="Overlapping"):
        version(c, (a,), statuses=(status(c, a), status(c, a)))


def test_version_rejects_orphan_and_cross_scope_status():
    c = chart()
    a, orphan = account(c), account(c)
    with pytest.raises(InvalidChartCandidateVersion, match="Foreign/orphan"):
        version(c, (a,), statuses=(status(c, orphan),))


def test_mutated_nested_account_after_seal_fails_digest_verification():
    c = chart()
    a = account(c)
    v = version(c, (a,))
    object.__setattr__(a, "label", "Tampered")
    with pytest.raises(ChartCandidateDigestMismatch):
        v.verify_integrity()


def test_mutated_binding_after_receipt_fails_integrity_check():
    c = chart()
    v = version(c)
    b = binding(c, v)
    receipt = run(b, (v,))
    object.__setattr__(b, "source_ref", "tampered-binding")
    with pytest.raises(ChartCandidateDigestMismatch):
        receipt.verify_integrity()


def test_mutated_nested_version_after_receipt_is_refused():
    c = chart()
    v = version(c)
    b = binding(c, v)
    receipt = run(b, (v,))
    object.__setattr__(v, "content_digest", "sha256:" + "0" * 64)
    with pytest.raises(ChartCandidateDigestMismatch):
        receipt.verify_integrity()


def test_candidate_version_and_binding_are_frozen_values():
    c = chart()
    v = version(c)
    b = binding(c, v)
    with pytest.raises(FrozenInstanceError):
        v.source_ref = "changed"
    with pytest.raises(FrozenInstanceError):
        b.source_ref = "changed"


def test_duplicate_or_non_tuple_catalog_fail_closed():
    c = chart()
    v = version(c)
    b = binding(c, v)
    with pytest.raises(InvalidBookChartBinding, match="tuples"):
        preview_book_chart_candidate(
            book_scope=b.book_scope, purpose=PURPOSE,
            as_of=BUSINESS, known_at=FEB,
            bindings=[b], chart_versions=(v,),
        )
    with pytest.raises(InvalidBookChartBinding, match="non-binding"):
        run(b, (v,), ("fake",))
    with pytest.raises(InvalidChartCandidateVersion, match="non-version"):
        run(b, ("fake",))


def test_canonical_known_at_normalizes_offsets_and_detects_naive_values():
    c = chart()
    v = version(c)
    b = binding(c, v)
    at_utc = run(b, (v,), known_at=FEB)
    offset = FEB.astimezone(timezone(timedelta(hours=1)))
    at_paris = run(b, (v,), known_at=offset)
    assert at_utc.content_digest == at_paris.content_digest
    with pytest.raises(InvalidBookChartBinding, match="Aware known_at"):
        run(b, (v,), known_at=datetime(2026, 2, 1))
    with pytest.raises(InvalidBookChartBinding, match="business date"):
        run(b, (v,), day=datetime(2026, 2, 15))


def test_strict_type_validation_on_version_and_binding():
    c = chart()
    v = version(c)
    b = binding(c, v)
    with pytest.raises(InvalidChartCandidateVersion):
        replace(v, id=CompanyChartId.new())
    with pytest.raises(InvalidChartCandidateVersion):
        replace(v, declared_framework="PCG")
    with pytest.raises(InvalidBookChartBinding):
        replace(b, chart_version_id=CompanyChartId.new())
    with pytest.raises(InvalidBookChartBinding):
        replace(b, declared_book_framework="PCG")
    with pytest.raises(InvalidBookChartBinding):
        replace(b, book_scope=c.scope)
    with pytest.raises(InvalidBookChartBinding):
        replace(b, purpose="STATUTORY")


def test_application_service_fails_closed_without_test_grant_or_on_cross_tenant():
    c = chart()
    v = version(c)
    b = binding(c, v)

    class FakeGrants:
        allow = False

        def require(self, *, principal, action, scope):
            assert action == "chart.binding.candidate.preview"
            if not self.allow:
                raise PermissionError("Unapproved candidate preview grant")

    grants = FakeGrants()
    svc = BookChartCandidatePreviewService(
        versions=MemoryChartCandidateVersions((v,)),
        bindings=MemoryBookChartBindings((b,)),
        authorization=grants,
    )
    actor = TrustedPrincipal("rnd-actor", "tenant-a")
    q = PreviewBookChartCandidate(b.book_scope, PURPOSE, BUSINESS, FEB)
    with pytest.raises(PermissionError, match="grant"):
        svc.preview(q, principal=actor)
    grants.allow = True
    result = svc.preview(q, principal=actor)
    assert result.binding.id == b.id
    with pytest.raises(PermissionError, match="Cross-tenant"):
        svc.preview(q, principal=TrustedPrincipal("rnd-actor", "tenant-b"))
    with pytest.raises(PermissionError, match="Unverified"):
        svc.preview(q, principal="user-submitted")
    assert not hasattr(svc, "post")
    assert not hasattr(svc, "publish")


def test_malicious_reader_leaking_foreign_book_is_refused_by_domain():
    c = chart()
    v = version(c)
    b = binding(c, v)

    class Allow:
        def require(self, *, principal, action, scope):
            return None

    class BadBindings:
        def list_for_book(self, scope):
            return (replace(b, book_scope=replace(scope, tenant_id="other")),)

    svc = BookChartCandidatePreviewService(
        versions=MemoryChartCandidateVersions((v,)),
        bindings=BadBindings(),
        authorization=Allow(),
    )
    with pytest.raises(InvalidBookChartBinding, match="Foreign book"):
        svc.preview(
            PreviewBookChartCandidate(b.book_scope, PURPOSE, BUSINESS, FEB),
            principal=TrustedPrincipal("rnd-actor", "tenant-a"),
        )


def test_memory_readers_are_exact_scope_and_have_no_mutators():
    c = chart()
    v = version(c)
    b = binding(c, v)
    chart_reader = MemoryChartCandidateVersions((v,))
    book_reader = MemoryBookChartBindings((b,))
    assert chart_reader.list_for_book_scope(b.book_scope) == (v,)
    assert book_reader.list_for_book(b.book_scope) == (b,)
    assert book_reader.list_for_book(
        replace(b.book_scope, book_id=AccountingBookId.new())
    ) == ()
    assert not hasattr(chart_reader, "save")
    assert not hasattr(book_reader, "publish")


def test_architecture_no_live_book_l04_sql_or_ledger_imports():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.application import chart_candidate_preview
    from pyaccountingkit.company_configuration.domain.chart_of_accounts import (
        versions_bindings,
    )
    from pyaccountingkit.company_configuration.infrastructure import (
        chart_candidate_preview_memory,
    )

    for module in (
        chart_candidate_preview, chart_candidate_preview_memory, versions_bindings,
    ):
        source = Path(module.__file__).read_text(encoding="utf-8")
        imports = {
            item.name.split(".")[0] for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Import) for item in node.names
        }
        assert not ({"psycopg", "sqlalchemy", "requests", "httpx"} & imports)
        assert "organization_issuer_gateway" not in source
        assert "accounting_books" not in source
