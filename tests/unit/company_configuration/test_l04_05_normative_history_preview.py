"""L04-05 bitemporal normative *claims*, not certified Normative Layer truth."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from pyaccountingkit.company_configuration.application.accounting_book_normative_history import (
    BookNormativeHistoryPreviewService,
    PreviewNormativeHistoryForBookDraft,
)
from pyaccountingkit.company_configuration.application.accounting_books import (
    BookDraftPermissionDenied,
    BookDraftService,
    ProposeBookDraft,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal
from pyaccountingkit.company_configuration.domain.accounting_books import (
    AccountingBookDraft,
    BookAssignmentCandidate,
    BookAssignmentMissing,
    BookAssignmentPurpose,
    BookCode,
    NormativeDeclaration,
    NormativeReferenceStatement,
    NormativeSourceCode,
    NormativeStatementAmbiguous,
    NormativeStatementMissing,
    NormativeStatementUnavailable,
    InvalidNormativeStatement,
    ReferenceFrameworkBindingCandidate,
    preview_normative_reference_history,
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
    BookAssignmentId,
    CompanyId,
    FrameworkBindingId,
    LegalEntityId,
    NormativeStatementId,
)
from pyaccountingkit.company_configuration.domain.shared.references import (
    CurrencyCode,
    ReferenceFrameworkRef,
)
from pyaccountingkit.company_configuration.infrastructure import (
    accounting_book_normative_history_memory,
)
from pyaccountingkit.company_configuration.infrastructure.accounting_book_assignments_memory import (
    MemoryBookAssignmentCandidates,
)
from pyaccountingkit.company_configuration.infrastructure.accounting_book_frameworks_memory import (
    MemoryBookFrameworkCandidates,
)
from pyaccountingkit.company_configuration.infrastructure.accounting_books_memory import (
    MemoryBookAuthorization,
    MemoryBookStore,
    MemoryCompanyEntityMembership,
    memory_book_uow_factory,
)

ClaimsMemory = accounting_book_normative_history_memory.MemoryNormativeReferenceClaims
SOURCE = NormativeSourceCode("TEST_SOURCE")
DAY = date(2026, 2, 15)
JAN = datetime(2026, 1, 1, tzinfo=UTC)
FEB = datetime(2026, 2, 1, tzinfo=UTC)
MAR = datetime(2026, 3, 1, tzinfo=UTC)


def make_book():
    book_id = AccountingBookId.new()
    return AccountingBookDraft(
        id=book_id,
        scope=ConfigurationScope(
            tenant_id="tenant-a",
            company_id=CompanyId.new(),
            legal_entity_id=LegalEntityId.new(),
            book_id=book_id,
        ),
        code=BookCode("MAIN"),
        label="Draft book",
        currency=CurrencyCode("EUR"),
        framework=ReferenceFrameworkRef("FR-PCG", "2026"),
        effective=EffectiveInterval(date(2026, 1, 1)),
        source_ref="rnd:book",
    )


def make_assignment(book):
    return BookAssignmentCandidate(
        id=BookAssignmentId.new(),
        scope=book.scope,
        purpose=BookAssignmentPurpose("STATUTORY"),
        effective=book.effective,
        source_ref="rnd:assignment",
    )


def make_binding(book):
    return ReferenceFrameworkBindingCandidate(
        id=FrameworkBindingId.new(),
        scope=book.scope,
        purpose=BookAssignmentPurpose("STATUTORY"),
        framework=book.framework,
        effective=book.effective,
        source_ref="rnd:binding",
    )


def statement(
    book, *, start=JAN, end=None, status=NormativeDeclaration.DECLARED_AVAILABLE,
    source=SOURCE, framework=None, effective=None, statement_id=None,
):
    return NormativeReferenceStatement(
        id=statement_id or NormativeStatementId.new(),
        framework=framework or book.framework,
        source=source,
        effective=effective or book.effective,
        knowledge=KnowledgeInterval(start, end),
        declaration=status,
        source_ref="rnd:unverified-external-declaration",
    )


def pure(book, statements, *, as_of=DAY, known_at=FEB, source=SOURCE):
    return preview_normative_reference_history(
        framework=book.framework, source=source, as_of=as_of,
        known_at=known_at, statements=statements,
    )


def create_service(
    book, claims, *, grant=True, membership=True, assignments=None, bindings=None
):
    store = MemoryBookStore()
    auth = MemoryBookAuthorization()
    members = MemoryCompanyEntityMembership()
    principal = TrustedPrincipal("rnd-test-actor", book.scope.tenant_id)
    members.allow(book.scope)
    auth.grant(
        principal=principal, action="book.draft.propose", scope=book.scope
    )
    uow = memory_book_uow_factory(store)
    BookDraftService(uow, auth, members).propose(
        ProposeBookDraft(book, "In-memory demo"), principal=principal
    )
    if not membership:
        members.revoke(book.scope)
    if grant:
        auth.grant(
            principal=principal,
            action="book.normative_history.preview",
            scope=book.scope,
        )
    service = BookNormativeHistoryPreviewService(
        uow_factory=uow,
        assignments=MemoryBookAssignmentCandidates(
            (make_assignment(book),) if assignments is None else assignments
        ),
        frameworks=MemoryBookFrameworkCandidates(
            (make_binding(book),) if bindings is None else bindings
        ),
        statements=ClaimsMemory(claims),
        authorization=auth,
        membership=members,
    )
    return service, principal, store, auth, members


def query(book, *, source=SOURCE, as_of=DAY, known_at=FEB):
    return PreviewNormativeHistoryForBookDraft(
        book.scope, BookAssignmentPurpose("STATUTORY"), source, as_of, known_at
    )


def test_positive_reference_statement_returns_explicit_unverified_source():
    book = make_book()
    s = statement(book)
    result = pure(book, (s,))
    assert result.statement_id == s.id
    assert result.framework == book.framework
    assert result.source == SOURCE
    assert result.as_of == DAY and result.known_at == FEB
    assert "unverified" in result.source_ref


def test_known_at_before_source_statement_is_not_a_default_to_latest():
    book = make_book()
    with pytest.raises(NormativeStatementMissing):
        pure(book, (statement(book, start=FEB),), known_at=JAN)


def test_backdated_restatement_preserves_prior_knowledge():
    book = make_book()
    old = statement(
        book, start=JAN, end=MAR,
        status=NormativeDeclaration.DECLARED_UNAVAILABLE,
    )
    corrected = statement(book, start=MAR)
    with pytest.raises(NormativeStatementUnavailable):
        pure(book, (old, corrected), known_at=FEB)
    assert pure(book, (old, corrected), known_at=MAR).statement_id == corrected.id


def test_two_known_claims_for_same_reference_are_ambiguous_not_last_wins():
    book = make_book()
    with pytest.raises(NormativeStatementAmbiguous):
        pure(book, (statement(book), statement(book, start=FEB)))


def test_duplicate_ids_rejected_even_if_knowledge_intervals_disjoint():
    book = make_book()
    first = statement(book, start=JAN, end=MAR)
    second = statement(book, start=MAR, statement_id=first.id)
    with pytest.raises(NormativeStatementAmbiguous):
        pure(book, (first, second))


def test_half_open_effective_dates_fail_when_end_is_excluded():
    book = make_book()
    s = statement(
        book,
        effective=EffectiveInterval(date(2026, 1, 1), date(2026, 2, 15)),
    )
    with pytest.raises(NormativeStatementMissing):
        pure(book, (s,), as_of=date(2026, 2, 15))
    assert pure(book, (s,), as_of=date(2026, 2, 14)).statement_id == s.id


def test_knowledge_interval_timezone_offset_is_normalized_by_inherited_vo():
    book = make_book()
    later = datetime(2026, 3, 1, 1, tzinfo=timezone(timedelta(hours=1)))
    record = statement(book, start=JAN, end=MAR)
    with pytest.raises(NormativeStatementMissing):
        pure(book, (record,), known_at=later)


def test_reference_source_and_version_must_match_without_fallback():
    book = make_book()
    variants = (
        statement(book, source=NormativeSourceCode("OTHER_SOURCE")),
        statement(book, framework=ReferenceFrameworkRef("FR-PCG", "2025")),
    )
    for record in variants:
        with pytest.raises(InvalidNormativeStatement, match="foreign"):
            pure(book, (record,))


@pytest.mark.parametrize("bad", ["", "lowercase", "A/B", " WITH_SPACE", "A" * 33])
def test_invalid_source_codes_rejected(bad):
    with pytest.raises(InvalidNormativeStatement):
        NormativeSourceCode(bad)


def test_invalid_statement_fields_are_rejected():
    book = make_book()
    record = statement(book)
    with pytest.raises(InvalidNormativeStatement):
        replace(record, id=book.id)
    with pytest.raises(InvalidNormativeStatement):
        replace(record, framework="IFRS")
    with pytest.raises(InvalidNormativeStatement):
        replace(record, declaration="DECLARED_AVAILABLE")
    with pytest.raises(InvalidNormativeStatement):
        replace(record, source_ref=" non-canonical ")
    with pytest.raises(InvalidNormativeStatement):
        replace(record, knowledge="2026-02-01")


def test_reject_naive_datetime_or_datetime_used_instead_of_business_date():
    book = make_book()
    for bad in (datetime(2026, 2, 1), "2026-02-01"):
        with pytest.raises(InvalidNormativeStatement, match="known_at"):
            pure(book, (statement(book),), known_at=bad)
    with pytest.raises(InvalidNormativeStatement):
        pure(book, (statement(book),), as_of=datetime(2026, 2, 15))


def test_reject_non_tuple_or_non_statement():
    book = make_book()
    with pytest.raises(InvalidNormativeStatement):
        pure(book, [statement(book)])
    with pytest.raises(InvalidNormativeStatement):
        pure(book, ("fake",))


def test_readonly_service_requires_all_current_draft_links_and_knowntime_claim():
    book = make_book()
    s = statement(book)
    svc, actor, store, _, _ = create_service(book, (s,))
    result = svc.preview(query(book), principal=actor)
    assert result.book_binding.framework == book.framework
    assert result.normative_claim.statement_id == s.id
    assert store.snapshot() == (book,)
    assert not hasattr(svc, "publish")
    assert not hasattr(svc, "post")


def test_missing_book_assignment_blocks_source_history_preview():
    book = make_book()
    svc, actor, _, _, _ = create_service(book, (statement(book),), assignments=())
    with pytest.raises(BookAssignmentMissing):
        svc.preview(query(book), principal=actor)


def test_unavailable_historical_claim_does_not_become_available_through_binding():
    book = make_book()
    s = statement(book, status=NormativeDeclaration.DECLARED_UNAVAILABLE)
    svc, actor, _, _, _ = create_service(book, (s,))
    with pytest.raises(NormativeStatementUnavailable):
        svc.preview(query(book), principal=actor)


def test_zero_claims_stays_unavailable_even_with_reference_in_book():
    book = make_book()
    svc, actor, _, _, _ = create_service(book, ())
    with pytest.raises(NormativeStatementMissing):
        svc.preview(query(book), principal=actor)


def test_default_deny_no_grant_or_membership():
    book = make_book()
    s = statement(book)
    svc, actor, store, _, _ = create_service(book, (s,), grant=False)
    with pytest.raises(BookDraftPermissionDenied):
        svc.preview(query(book), principal=actor)
    svc, actor, store, _, _ = create_service(book, (s,), membership=False)
    with pytest.raises(BookDraftPermissionDenied):
        svc.preview(query(book), principal=actor)
    assert store.snapshot() == (book,)


def test_cross_tenant_or_unverified_actor_is_denied():
    book = make_book()
    svc, _, _, _, _ = create_service(book, (statement(book),))
    with pytest.raises(BookDraftPermissionDenied, match="Cross-tenant"):
        svc.preview(
            query(book), principal=TrustedPrincipal("rnd-test-actor", "tenant-b")
        )
    with pytest.raises(BookDraftPermissionDenied, match="Verified"):
        svc.preview(query(book), principal="unsafe")


def test_revoke_grant_revokes_next_read():
    book = make_book()
    svc, actor, _, auth, _ = create_service(book, (statement(book),))
    auth.revoke(
        principal=actor, action="book.normative_history.preview", scope=book.scope
    )
    with pytest.raises(BookDraftPermissionDenied):
        svc.preview(query(book), principal=actor)


def test_memory_reader_uses_exact_reference_source_and_never_saves():
    book = make_book()
    s = statement(book)
    registry = ClaimsMemory((s,))
    assert registry.list_for_reference(book.framework, SOURCE) == (s,)
    assert registry.list_for_reference(
        ReferenceFrameworkRef("FR-PCG", "2025"), SOURCE
    ) == ()
    assert registry.list_for_reference(
        book.framework, NormativeSourceCode("OTHER_SOURCE")
    ) == ()
    assert not hasattr(registry, "save")
    assert not hasattr(registry, "publish")


def test_malicious_reader_leaking_another_source_fails_closed():
    book = make_book()
    svc, actor, store, access, members = create_service(
        book, (statement(book),)
    )

    class ForeignSource:
        def list_for_reference(self, framework, source):
            return (statement(book, source=NormativeSourceCode("FOREIGN")),)

    malicious = BookNormativeHistoryPreviewService(
        uow_factory=memory_book_uow_factory(store),
        assignments=MemoryBookAssignmentCandidates((make_assignment(book),)),
        frameworks=MemoryBookFrameworkCandidates((make_binding(book),)),
        statements=ForeignSource(),
        authorization=access,
        membership=members,
    )
    with pytest.raises(InvalidNormativeStatement, match="foreign"):
        malicious.preview(query(book), principal=actor)


def test_query_requires_book_scope_and_aware_known_at():
    book = make_book()
    with pytest.raises(InvalidNormativeStatement):
        query(book, known_at=datetime(2026, 2, 1))
    with pytest.raises(InvalidNormativeStatement):
        PreviewNormativeHistoryForBookDraft(
            replace(book.scope, book_id=None),
            BookAssignmentPurpose("STATUTORY"), SOURCE, DAY, FEB
        )
    with pytest.raises(InvalidNormativeStatement):
        PreviewNormativeHistoryForBookDraft(
            book.scope, BookAssignmentPurpose("STATUTORY"), "TEST_SOURCE", DAY, FEB
        )


def test_import_graph_is_free_of_sql_and_live_iam_clients():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.application import (
        accounting_book_normative_history,
    )
    from pyaccountingkit.company_configuration.infrastructure import (
        accounting_book_normative_history_memory,
    )

    for module in (accounting_book_normative_history, accounting_book_normative_history_memory):
        source = Path(module.__file__).read_text(encoding="utf-8")
        imported = {
            n.name for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Import) for n in node.names
        }
        assert not ({"psycopg", "sqlalchemy", "httpx", "requests"} & imported)
        assert "organization_issuer_gateway" not in source
