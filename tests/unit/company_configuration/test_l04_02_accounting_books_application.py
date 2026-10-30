"""L04-02: book-draft application use cases and local adapter adversarial tests.

All granted identities and membership pairs in these tests are test doubles.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date

import pytest

from pyaccountingkit.company_configuration.application.accounting_books import (
    BookDraftNotFound,
    BookDraftPermissionDenied,
    BookDraftService,
    GetBookDraft,
    ListBookDrafts,
    ProposeBookDraft,
    ReframeBookDraft,
    RenameBookDraft,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal
from pyaccountingkit.company_configuration.domain.accounting_books import (
    AccountingBookConflict,
    AccountingBookDraft,
    BookCode,
    InvalidAccountingBook,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
)
from pyaccountingkit.company_configuration.domain.shared.errors import VersionConflict
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountingBookId,
    CompanyId,
    LegalEntityId,
)
from pyaccountingkit.company_configuration.domain.shared.references import (
    CurrencyCode,
    ReferenceFrameworkRef,
)
from pyaccountingkit.company_configuration.infrastructure.accounting_books_memory import (
    MemoryBookAuthorization,
    MemoryBookRepository,
    MemoryBookStore,
    MemoryBookUnitOfWork,
    MemoryCompanyEntityMembership,
    memory_book_uow_factory,
)


def make_book(
    *,
    book_id: AccountingBookId | None = None,
    tenant: str = "tenant-a",
    company: CompanyId | None = None,
    entity: LegalEntityId | None = None,
    code: str = "MAIN",
    start: date = date(2026, 1, 1),
    end: date | None = None,
) -> AccountingBookDraft:
    book_id = book_id or AccountingBookId.new()
    return AccountingBookDraft(
        id=book_id,
        scope=ConfigurationScope(
            tenant_id=tenant,
            company_id=company or CompanyId.new(),
            legal_entity_id=entity or LegalEntityId.new(),
            book_id=book_id,
        ),
        code=BookCode(code),
        label="General",
        currency=CurrencyCode("EUR"),
        framework=ReferenceFrameworkRef("FR-PCG", "2026"),
        effective=EffectiveInterval(start, end),
        source_ref="rnd:book-demo",
    )


def scenario():
    store = MemoryBookStore()
    access = MemoryBookAuthorization()
    membership = MemoryCompanyEntityMembership()
    service = BookDraftService(memory_book_uow_factory(store), access, membership)
    principal = TrustedPrincipal(actor_id="test-reviewer", tenant_id="tenant-a")
    return store, access, membership, service, principal


def authorize(access, membership, principal, scope, *actions):
    membership.allow(scope)
    for action in actions:
        access.grant(principal=principal, action=f"book.draft.{action}", scope=scope)


def test_by_default_missing_action_grant_or_membership_denies_without_write():
    store, access, membership, service, principal = scenario()
    book = make_book()
    with pytest.raises(BookDraftPermissionDenied):
        service.propose(ProposeBookDraft(book, "Proposal"), principal=principal)
    authorize(access, membership, principal, book.scope, "read")
    with pytest.raises(BookDraftPermissionDenied):
        service.propose(ProposeBookDraft(book, "Proposal"), principal=principal)
    assert store.snapshot() == ()


def test_membership_is_checked_independently_of_action_allowlist():
    store, access, membership, service, principal = scenario()
    book = make_book()
    access.grant(principal=principal, action="book.draft.propose", scope=book.scope)
    with pytest.raises(BookDraftPermissionDenied, match="relationship"):
        service.propose(ProposeBookDraft(book, "Proposal"), principal=principal)
    assert not store.snapshot()


def test_tenant_mismatch_or_unverified_principal_is_denied():
    store, access, membership, service, principal = scenario()
    book = make_book()
    authorize(access, membership, principal, book.scope, "propose")
    with pytest.raises(BookDraftPermissionDenied, match="Cross-tenant"):
        service.propose(
            ProposeBookDraft(book, "Proposal"),
            principal=TrustedPrincipal("test-reviewer", "tenant-b"),
        )
    with pytest.raises(BookDraftPermissionDenied, match="Verified principal"):
        service.propose(ProposeBookDraft(book, "Proposal"), principal="raw-caller")
    assert store.snapshot() == ()


def test_propose_get_list_rename_reframe_are_only_memory_draft_commands():
    store, access, membership, service, principal = scenario()
    book = make_book()
    entity_scope = replace(book.scope, book_id=None)
    authorize(access, membership, principal, book.scope,
              "propose", "read", "rename", "reframe")
    authorize(access, membership, principal, entity_scope, "list")

    assert service.propose(ProposeBookDraft(book, "Initial proposal"), principal=principal) == book
    assert service.get(GetBookDraft(book.scope), principal=principal).revision == 1
    assert service.list(ListBookDrafts(entity_scope), principal=principal) == (book,)

    changed = service.rename(
        RenameBookDraft(book.scope, "Management", 1, "Approval candidate"),
        principal=principal,
    )
    assert changed.label == "Management" and changed.revision == 2
    assert book.label == "General" and book.revision == 1

    reframed = service.reframe(
        ReframeBookDraft(
            book.scope, ReferenceFrameworkRef("IFRS", "2026"),
            2, "Explicit proposed reframe",
        ),
        principal=principal,
    )
    assert reframed.revision == 3
    assert reframed.framework.framework_code == "IFRS"
    assert store.snapshot() == (reframed,)
    assert not hasattr(service, "activate")
    assert not hasattr(service, "post")


def test_list_never_leaks_books_from_other_entity_tenant_or_company():
    store, access, membership, service, principal = scenario()
    a = make_book()
    b = make_book(company=a.scope.company_id, entity=a.scope.legal_entity_id, code="ALT")
    c = make_book(company=a.scope.company_id, entity=LegalEntityId.new())
    for book in (a, b, c):
        authorize(access, membership, principal, book.scope, "propose")
        service.propose(ProposeBookDraft(book, "Proposal"), principal=principal)
    entity_scope = replace(a.scope, book_id=None)
    authorize(access, membership, principal, entity_scope, "list")
    results = service.list(ListBookDrafts(entity_scope), principal=principal)
    assert tuple(book.code.value for book in results) == ("ALT", "MAIN")
    assert c not in results


def test_competing_code_is_rejected_and_transaction_rolls_back():
    store, access, membership, service, principal = scenario()
    original = make_book()
    candidate = make_book(
        company=original.scope.company_id, entity=original.scope.legal_entity_id
    )
    for book in (original, candidate):
        authorize(access, membership, principal, book.scope, "propose")
    service.propose(ProposeBookDraft(original, "First"), principal=principal)
    with pytest.raises(AccountingBookConflict):
        service.propose(ProposeBookDraft(candidate, "Second"), principal=principal)
    assert len(store.snapshot()) == 1


def test_adjacent_periods_are_not_collisions():
    store, access, membership, service, principal = scenario()
    a = make_book(end=date(2027, 1, 1))
    b = make_book(
        company=a.scope.company_id, entity=a.scope.legal_entity_id,
        start=date(2027, 1, 1),
    )
    for book in (a, b):
        authorize(access, membership, principal, book.scope, "propose")
        service.propose(ProposeBookDraft(book, "Proposal"), principal=principal)
    assert len(store.snapshot()) == 2


def test_missing_scope_cannot_expose_another_company_book():
    store, access, membership, service, principal = scenario()
    book = make_book()
    authorize(access, membership, principal, book.scope, "propose")
    service.propose(ProposeBookDraft(book, "Proposal"), principal=principal)
    wrong_scope = replace(book.scope, company_id=CompanyId.new())
    authorize(access, membership, principal, wrong_scope, "read")
    with pytest.raises(BookDraftNotFound):
        service.get(GetBookDraft(wrong_scope), principal=principal)
    assert len(store.snapshot()) == 1


def test_reusing_book_id_in_different_entity_is_not_a_new_draft():
    store, access, membership, service, principal = scenario()
    first = make_book()
    second = make_book(
        book_id=first.id,
        company=first.scope.company_id,
        entity=LegalEntityId.new(),
    )
    for book in (first, second):
        authorize(access, membership, principal, book.scope, "propose")
    service.propose(ProposeBookDraft(first, "Initial"), principal=principal)
    with pytest.raises(VersionConflict):
        service.propose(ProposeBookDraft(second, "Conflicting identity"), principal=principal)
    assert store.snapshot() == (first,)


def test_stale_rename_rejected_with_current_value_preserved():
    store, access, membership, service, principal = scenario()
    book = make_book()
    authorize(access, membership, principal, book.scope, "propose", "rename")
    service.propose(ProposeBookDraft(book, "New"), principal=principal)
    service.rename(RenameBookDraft(book.scope, "First", 1, "Change"), principal=principal)
    with pytest.raises(VersionConflict):
        service.rename(RenameBookDraft(book.scope, "Second", 1, "Stale"), principal=principal)
    assert store.snapshot()[0].label == "First"


def test_two_parallel_stale_revisions_allow_exactly_one_local_commit():
    store, access, membership, service, principal = scenario()
    book = make_book()
    authorize(access, membership, principal, book.scope, "propose", "rename")
    service.propose(ProposeBookDraft(book, "New"), principal=principal)

    def attempt(label):
        try:
            result = service.rename(
                RenameBookDraft(book.scope, label, 1, "Test race"), principal=principal
            )
            return ("ok", result.revision)
        except VersionConflict:
            return ("conflict", 1)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ("A", "B")))
    assert sorted(result[0] for result in results) == ["conflict", "ok"]
    assert store.snapshot()[0].revision == 2


def test_commit_failure_does_not_publish_staged_book():
    store = MemoryBookStore()
    book = make_book()

    def fail():
        raise RuntimeError("injected commit failure")

    with pytest.raises(RuntimeError, match="injected"):
        with MemoryBookUnitOfWork(store, before_commit=fail) as uow:
            uow.books.save(book, expected_revision=0)
            uow.commit()
    assert store.snapshot() == ()


def test_no_explicit_commit_discards_staged_book():
    store = MemoryBookStore()
    book = make_book()
    with MemoryBookUnitOfWork(store) as uow:
        uow.books.save(book, expected_revision=0)
    assert store.snapshot() == ()


@pytest.mark.parametrize(
    "bad",
    [True, -1, 1.1, "0"],
)
def test_repository_rejects_invalid_expected_revision(bad):
    store = MemoryBookStore()
    with MemoryBookUnitOfWork(store) as uow:
        with pytest.raises(VersionConflict):
            uow.books.save(make_book(), expected_revision=bad)


def test_revoke_action_or_membership_blocks_subsequent_reads():
    store, access, membership, service, principal = scenario()
    book = make_book()
    authorize(access, membership, principal, book.scope, "propose", "read")
    service.propose(ProposeBookDraft(book, "Proposal"), principal=principal)
    access.revoke(principal=principal, action="book.draft.read", scope=book.scope)
    with pytest.raises(BookDraftPermissionDenied):
        service.get(GetBookDraft(book.scope), principal=principal)
    access.grant(principal=principal, action="book.draft.read", scope=book.scope)
    membership.revoke(book.scope)
    with pytest.raises(BookDraftPermissionDenied):
        service.get(GetBookDraft(book.scope), principal=principal)


def test_commands_reject_bare_scope_bad_reason_and_untyped_framework():
    book = make_book()
    with pytest.raises(InvalidAccountingBook):
        RenameBookDraft(replace(book.scope, book_id=None), "Name", 1, "Reason")
    with pytest.raises(InvalidAccountingBook):
        ReframeBookDraft(book.scope, "IFRS", 1, "Reason")
    with pytest.raises(InvalidAccountingBook):
        ProposeBookDraft(book, " ")
    with pytest.raises(InvalidAccountingBook):
        ListBookDrafts(book.scope)
    with pytest.raises(InvalidAccountingBook):
        GetBookDraft(replace(book.scope, book_id=None))


def test_no_sql_iam_or_http_import_in_l04_modules():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.application import accounting_books
    from pyaccountingkit.company_configuration.infrastructure import (
        accounting_books_memory,
    )

    for module in (accounting_books, accounting_books_memory):
        source = Path(module.__file__).read_text(encoding="utf-8")
        symbols = {
            alias.name for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Import) for alias in node.names
        }
        assert not {"psycopg", "sqlalchemy", "requests", "httpx", "django"} & symbols
        assert "organization_issuer_gateway" not in source


def test_repository_protocol_is_implemented_by_memory_adapter():
    assert all(
        hasattr(MemoryBookRepository, member)
        for member in ("get", "list_for_entity", "save")
    )
