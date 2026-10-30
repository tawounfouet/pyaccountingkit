"""L04-03: provisional ownership boundary and dated assignment read preview.

All test allowlists and assignments are local fakes. No published C10, posting
rights, verified IAM credentials or authoritative Company membership exists.
"""

from dataclasses import replace
from datetime import date, datetime

import pytest

from pyaccountingkit.company_configuration.application.accounting_book_assignments import (
    BookAssignmentPreviewService,
    ListBookAssignmentCandidates,
    PreviewAssignedBookDrafts,
)
from pyaccountingkit.company_configuration.application.accounting_books import (
    BookDraftPermissionDenied,
    BookDraftService,
    ProposeBookDraft,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal
from pyaccountingkit.company_configuration.domain.accounting_books import (
    AccountingBookDraft,
    BookAssignmentAmbiguous,
    BookAssignmentCandidate,
    BookAssignmentMissing,
    BookAssignmentPurpose,
    BookCode,
    InvalidBookAssignment,
    preview_applicable_book_drafts,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountingBookId,
    BookAssignmentId,
    CompanyId,
    LegalEntityId,
)
from pyaccountingkit.company_configuration.domain.shared.references import (
    CurrencyCode,
    ReferenceFrameworkRef,
)
from pyaccountingkit.company_configuration.infrastructure.accounting_book_assignments_memory import (
    MemoryBookAssignmentCandidates,
)
from pyaccountingkit.company_configuration.infrastructure.accounting_books_memory import (
    MemoryBookAuthorization,
    MemoryBookStore,
    MemoryCompanyEntityMembership,
    memory_book_uow_factory,
)


def make_book(
    *,
    company=None,
    entity=None,
    tenant="tenant-a",
    code="MAIN",
    start=date(2026, 1, 1),
    end=None,
):
    book_id = AccountingBookId.new()
    scope = ConfigurationScope(
        tenant_id=tenant,
        company_id=company or CompanyId.new(),
        legal_entity_id=entity or LegalEntityId.new(),
        book_id=book_id,
    )
    return AccountingBookDraft(
        id=book_id,
        scope=scope,
        code=BookCode(code),
        label="Demo",
        currency=CurrencyCode("EUR"),
        framework=ReferenceFrameworkRef("FR-PCG", "2026"),
        effective=EffectiveInterval(start, end),
        source_ref="demo:spec",
    )


def make_assignment(
    book, *,
    scope=None,
    purpose="STATUTORY",
    start=date(2026, 1, 1),
    end=None,
    assignment_id=None,
):
    return BookAssignmentCandidate(
        id=assignment_id or BookAssignmentId.new(),
        scope=scope or book.scope,
        purpose=BookAssignmentPurpose(purpose),
        effective=EffectiveInterval(start, end),
        source_ref="demo:assignment",
    )


def build_service(books, assignments, *, allow=True):
    store = MemoryBookStore()
    auth = MemoryBookAuthorization()
    membership = MemoryCompanyEntityMembership()
    principal = TrustedPrincipal("rnd-actor", "tenant-a")
    uow = memory_book_uow_factory(store)
    book_service = BookDraftService(uow, auth, membership)
    for book in books:
        membership.allow(book.scope)
        auth.grant(
            principal=principal, action="book.draft.propose", scope=book.scope
        )
        book_service.propose(ProposeBookDraft(book, "R&D proposal"), principal=principal)
    entity_scope = replace(books[0].scope, book_id=None)
    if allow:
        auth.grant(
            principal=principal, action="book.assignment.preview", scope=entity_scope
        )
    service = BookAssignmentPreviewService(
        uow, MemoryBookAssignmentCandidates(tuple(assignments)), auth, membership
    )
    return service, principal, auth, membership, store, entity_scope


def test_typed_assignment_id_is_stable_and_not_equal_book_id():
    book = make_book()
    assignment = make_assignment(book)
    assert isinstance(assignment.id, BookAssignmentId)
    assert isinstance(assignment.scope.book_id, AccountingBookId)
    assert type(assignment.id) is not type(book.id)
    assert BookAssignmentId.parse(str(assignment.id)) == assignment.id


@pytest.mark.parametrize("purpose", ["", "statutory", " GROUP", "A/B", "ÉTAT", "A" * 33])
def test_invalid_purpose_is_rejected(purpose):
    with pytest.raises(InvalidBookAssignment):
        BookAssignmentPurpose(purpose)


def test_purpose_is_not_a_frozen_normative_book_kind_enum():
    assert BookAssignmentPurpose("GROUP_REPORTING").value == "GROUP_REPORTING"


def test_valid_assignment_and_preview_return_only_explicit_book():
    book = make_book()
    assignment = make_assignment(book)
    service, principal, _, _, _, scope = build_service((book,), (assignment,))
    result = service.preview(
        PreviewAssignedBookDrafts(scope, BookAssignmentPurpose("STATUTORY"), date(2026, 5, 1)),
        principal=principal,
    )
    assert result == (book,)
    assert service.list_candidates(
        ListBookAssignmentCandidates(scope), principal=principal
    ) == (assignment,)


def test_no_assignment_is_fail_closed_not_implicit_primary_book():
    book = make_book()
    service, principal, _, _, _, scope = build_service((book,), ())
    with pytest.raises(BookAssignmentMissing):
        service.preview(
            PreviewAssignedBookDrafts(scope, BookAssignmentPurpose("STATUTORY"), date(2026, 5, 1)),
            principal=principal,
        )


def test_purpose_and_date_must_match_no_fallback():
    book = make_book()
    assignment = make_assignment(book, start=date(2026, 3, 1))
    service, principal, _, _, _, scope = build_service((book,), (assignment,))
    for purpose, day in (
        ("GROUP_REPORTING", date(2026, 5, 1)),
        ("STATUTORY", date(2026, 2, 1)),
    ):
        with pytest.raises(BookAssignmentMissing):
            service.preview(
                PreviewAssignedBookDrafts(scope, BookAssignmentPurpose(purpose), day),
                principal=principal,
            )


def test_two_parallel_books_are_explicitly_returned_in_deterministic_order():
    company, entity = CompanyId.new(), LegalEntityId.new()
    b = make_book(company=company, entity=entity, code="B")
    a = make_book(company=company, entity=entity, code="A")
    service, principal, _, _, _, scope = build_service(
        (b, a), (make_assignment(b), make_assignment(a))
    )
    assert service.preview(
        PreviewAssignedBookDrafts(scope, BookAssignmentPurpose("STATUTORY"), date(2026, 5, 1)),
        principal=principal,
    ) == (a, b)


def test_overlapping_assignments_same_book_and_purpose_are_ambiguous():
    book = make_book()
    assignments = (
        make_assignment(book),
        make_assignment(book, start=date(2026, 2, 1)),
    )
    service, principal, _, _, _, scope = build_service((book,), assignments)
    with pytest.raises(BookAssignmentAmbiguous):
        service.preview(
            PreviewAssignedBookDrafts(scope, BookAssignmentPurpose("STATUTORY"), date(2026, 5, 1)),
            principal=principal,
        )


def test_nonoverlapping_same_book_assignment_succeeds_in_each_window():
    book = make_book()
    assignments = (
        make_assignment(book, end=date(2026, 7, 1)),
        make_assignment(book, start=date(2026, 7, 1)),
    )
    service, principal, _, _, _, scope = build_service((book,), assignments)
    for day in (date(2026, 6, 30), date(2026, 7, 1)):
        assert service.preview(
            PreviewAssignedBookDrafts(scope, BookAssignmentPurpose("STATUTORY"), day),
            principal=principal,
        ) == (book,)


def test_duplicate_assignment_ids_are_ambiguous_even_when_periods_disjoint():
    book = make_book()
    assignment = make_assignment(book, end=date(2026, 7, 1))
    reused = make_assignment(
        book, assignment_id=assignment.id, start=date(2026, 7, 1)
    )
    with pytest.raises(BookAssignmentAmbiguous):
        preview_applicable_book_drafts(
            scope=replace(book.scope, book_id=None),
            purpose=BookAssignmentPurpose("STATUTORY"),
            as_of=date(2026, 6, 1),
            books=(book,),
            assignments=(assignment, reused),
        )


def test_assignment_to_unknown_book_is_rejected_not_silently_dropped():
    book = make_book()
    unknown = replace(book.scope, book_id=AccountingBookId.new())
    service, principal, _, _, _, scope = build_service(
        (book,), (make_assignment(book, scope=unknown),)
    )
    with pytest.raises(InvalidBookAssignment, match="unavailable"):
        service.preview(
            PreviewAssignedBookDrafts(scope, BookAssignmentPurpose("STATUTORY"), date(2026, 3, 1)),
            principal=principal,
        )


def test_assignment_cannot_cross_company_or_legal_entity_for_preview():
    book = make_book()
    foreign = replace(book.scope, legal_entity_id=LegalEntityId.new())
    with pytest.raises(InvalidBookAssignment, match="Cross-entity"):
        make_assignment(book, scope=foreign).require_candidate_compatibility(book)


def test_assignment_interval_cannot_escape_book_validity():
    book = make_book(start=date(2026, 2, 1), end=date(2026, 9, 1))
    for first, last in (
        (date(2026, 1, 1), date(2026, 8, 1)),
        (date(2026, 2, 1), None),
        (date(2026, 2, 1), date(2026, 10, 1)),
    ):
        assignment = make_assignment(book, start=first, end=last)
        with pytest.raises(InvalidBookAssignment, match="beyond"):
            assignment.require_candidate_compatibility(book)


def test_scoped_authorization_is_default_deny_for_reads():
    book = make_book()
    service, principal, _, _, store, scope = build_service(
        (book,), (make_assignment(book),), allow=False
    )
    with pytest.raises(BookDraftPermissionDenied):
        service.preview(
            PreviewAssignedBookDrafts(scope, BookAssignmentPurpose("STATUTORY"), date(2026, 4, 1)),
            principal=principal,
        )
    assert store.snapshot() == (book,)


def test_cross_tenant_and_raw_principal_cannot_preview():
    book = make_book()
    service, _, _, _, _, scope = build_service((book,), (make_assignment(book),))
    query = PreviewAssignedBookDrafts(scope, BookAssignmentPurpose("STATUTORY"), date(2026, 4, 1))
    with pytest.raises(BookDraftPermissionDenied, match="Cross-tenant"):
        service.preview(query, principal=TrustedPrincipal("rnd-actor", "tenant-b"))
    with pytest.raises(BookDraftPermissionDenied, match="Verified"):
        service.preview(query, principal="raw:actor")


def test_revoked_membership_blocks_preview_even_with_action_grant():
    book = make_book()
    service, principal, _, membership, _, scope = build_service(
        (book,), (make_assignment(book),)
    )
    membership.revoke(scope)
    with pytest.raises(BookDraftPermissionDenied, match="relationship"):
        service.preview(
            PreviewAssignedBookDrafts(scope, BookAssignmentPurpose("STATUTORY"), date(2026, 4, 1)),
            principal=principal,
        )


def test_reader_that_leaks_cross_tenant_assignment_must_fail_closed():
    book = make_book()
    service, principal, auth, membership, store, scope = build_service(
        (book,), (make_assignment(book),)
    )

    class MaliciousReader:
        def list_for_entity(self, unused_scope):
            return (make_assignment(book, scope=replace(book.scope, tenant_id="tenant-b")),)

    hardened = BookAssignmentPreviewService(
        memory_book_uow_factory(store), MaliciousReader(), auth, membership
    )
    with pytest.raises(InvalidBookAssignment, match="Out-of-scope"):
        hardened.preview(
            PreviewAssignedBookDrafts(scope, BookAssignmentPurpose("STATUTORY"), date(2026, 5, 1)),
            principal=principal,
        )
    with pytest.raises(InvalidBookAssignment, match="out-of-scope"):
        hardened.list_candidates(ListBookAssignmentCandidates(scope), principal=principal)


def test_datetime_and_book_scope_cannot_be_used_as_preview_temporality():
    book = make_book()
    with pytest.raises(InvalidBookAssignment):
        PreviewAssignedBookDrafts(
            book.scope, BookAssignmentPurpose("STATUTORY"), date(2026, 1, 1)
        )
    with pytest.raises(InvalidBookAssignment):
        PreviewAssignedBookDrafts(
            replace(book.scope, book_id=None),
            BookAssignmentPurpose("STATUTORY"),
            datetime(2026, 1, 1),
        )


def test_fixture_is_read_only_and_cannot_expose_another_entity():
    book = make_book()
    assignment = make_assignment(book)
    reader = MemoryBookAssignmentCandidates((assignment,))
    foreign = replace(book.scope, book_id=None, legal_entity_id=LegalEntityId.new())
    assert reader.list_for_entity(foreign) == ()
    assert not hasattr(reader, "save")
    assert not hasattr(reader, "publish")
    assert not hasattr(BookAssignmentPreviewService, "activate")
    assert not hasattr(BookAssignmentPreviewService, "post")


def test_no_sql_or_live_iam_dependency_imported():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.application import accounting_book_assignments
    from pyaccountingkit.company_configuration.infrastructure import (
        accounting_book_assignments_memory,
    )

    for module in (accounting_book_assignments, accounting_book_assignments_memory):
        source = Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {
            item.name for node in ast.walk(tree)
            if isinstance(node, ast.Import) for item in node.names
        }
        assert not imported.intersection({"psycopg", "sqlalchemy", "requests", "httpx"})
        assert "organization_issuer_gateway" not in source
