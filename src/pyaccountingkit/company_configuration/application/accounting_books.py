"""L04-02 R&D: typed application commands, queries, and hexagonal ports.

All writes are *in-memory draft proposals* only. No legal membership proof,
production principal authentication, SQL operations, audit, outbox or posting.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, Self

from ..domain.accounting_books import AccountingBookDraft, InvalidAccountingBook
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.errors import DomainError
from ..domain.shared.identifiers import AccountingBookId
from ..domain.shared.references import ReferenceFrameworkRef
from .ports import TrustedPrincipal


class BookDraftNotFound(DomainError):
    code = "BOOK_DRAFT_NOT_FOUND"


class BookDraftPermissionDenied(DomainError):
    code = "BOOK_DRAFT_PERMISSION_DENIED"


def _reason(value: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise InvalidAccountingBook("A non-empty trimmed amendment reason is required")


def _book_scope(scope: ConfigurationScope) -> None:
    if not isinstance(scope, ConfigurationScope) or not isinstance(
        scope.book_id, AccountingBookId
    ):
        raise InvalidAccountingBook("A typed book-level scope is required")


def _entity_scope(scope: ConfigurationScope) -> None:
    if not isinstance(scope, ConfigurationScope) or scope.book_id is not None:
        raise InvalidAccountingBook("A typed entity-level scope without book_id is required")


@dataclass(frozen=True, slots=True)
class ProposeBookDraft:
    draft: AccountingBookDraft
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.draft, AccountingBookDraft):
            raise InvalidAccountingBook("Expected a typed AccountingBookDraft")
        _reason(self.reason)


@dataclass(frozen=True, slots=True)
class RenameBookDraft:
    scope: ConfigurationScope
    label: str
    expected_revision: int
    reason: str

    def __post_init__(self) -> None:
        _book_scope(self.scope)
        _reason(self.reason)
        if not isinstance(self.label, str) or not self.label.strip():
            raise InvalidAccountingBook("New label required")
        if type(self.expected_revision) is not int or self.expected_revision < 1:
            raise InvalidAccountingBook("Expected positive revision")


@dataclass(frozen=True, slots=True)
class ReframeBookDraft:
    scope: ConfigurationScope
    framework: ReferenceFrameworkRef
    expected_revision: int
    reason: str

    def __post_init__(self) -> None:
        _book_scope(self.scope)
        _reason(self.reason)
        if not isinstance(self.framework, ReferenceFrameworkRef):
            raise InvalidAccountingBook("Typed versioned framework required")
        if type(self.expected_revision) is not int or self.expected_revision < 1:
            raise InvalidAccountingBook("Expected positive revision")


@dataclass(frozen=True, slots=True)
class GetBookDraft:
    scope: ConfigurationScope

    def __post_init__(self) -> None:
        _book_scope(self.scope)


@dataclass(frozen=True, slots=True)
class ListBookDrafts:
    scope: ConfigurationScope

    def __post_init__(self) -> None:
        _entity_scope(self.scope)


class BookDraftRepository(Protocol):
    """Scoped repository port; concrete adapter must enforce optimistic concurrency."""

    def get(self, scope: ConfigurationScope) -> AccountingBookDraft | None: ...

    def list_for_entity(
        self, scope: ConfigurationScope
    ) -> tuple[AccountingBookDraft, ...]: ...

    def save(self, draft: AccountingBookDraft, *, expected_revision: int) -> None: ...


class BookDraftUnitOfWork(Protocol):
    books: BookDraftRepository

    def __enter__(self) -> Self: ...

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None: ...

    def commit(self) -> None: ...


class BookDraftAuthorization(Protocol):
    """External identity/authorization still required. Fake allowlist is NOT an IAM."""

    def require(
        self, *, principal: TrustedPrincipal, action: str, scope: ConfigurationScope
    ) -> None: ...


class CompanyEntityMembership(Protocol):
    """Independent authoritative membership check; test fake is NOT legal proof."""

    def require(self, *, scope: ConfigurationScope) -> None: ...


class BookDraftService:
    """Application use cases; authorization and company/entity membership first.

    No transport may build TrustedPrincipal from caller-supplied JSON. The
    actual production signature-to-IAM check remains G3 issue #71.
    """

    def __init__(
        self,
        uow_factory: Callable[[], BookDraftUnitOfWork],
        authorization: BookDraftAuthorization,
        membership: CompanyEntityMembership,
    ) -> None:
        self._uow_factory = uow_factory
        self._authorization = authorization
        self._membership = membership

    def _check(
        self, *, principal: TrustedPrincipal, action: str, scope: ConfigurationScope
    ) -> None:
        if not isinstance(principal, TrustedPrincipal):
            raise BookDraftPermissionDenied("Verified principal required")
        if principal.tenant_id != scope.tenant_id:
            raise BookDraftPermissionDenied("Cross-tenant access denied")
        self._authorization.require(principal=principal, action=action, scope=scope)
        self._membership.require(scope=scope)

    def propose(
        self, command: ProposeBookDraft, *, principal: TrustedPrincipal
    ) -> AccountingBookDraft:
        if not isinstance(command, ProposeBookDraft):
            raise TypeError("Expected ProposeBookDraft")
        draft = command.draft
        self._check(principal=principal, action="book.draft.propose", scope=draft.scope)
        with self._uow_factory() as uow:
            uow.books.save(draft, expected_revision=0)
            uow.commit()
        return draft

    def rename(
        self, command: RenameBookDraft, *, principal: TrustedPrincipal
    ) -> AccountingBookDraft:
        if not isinstance(command, RenameBookDraft):
            raise TypeError("Expected RenameBookDraft")
        self._check(principal=principal, action="book.draft.rename", scope=command.scope)
        with self._uow_factory() as uow:
            current = uow.books.get(command.scope)
            if current is None:
                raise BookDraftNotFound("Draft not found in this book scope")
            updated = current.rename(
                command.label, expected_revision=command.expected_revision,
                reason=command.reason,
            )
            uow.books.save(updated, expected_revision=command.expected_revision)
            uow.commit()
        return updated

    def reframe(
        self, command: ReframeBookDraft, *, principal: TrustedPrincipal
    ) -> AccountingBookDraft:
        if not isinstance(command, ReframeBookDraft):
            raise TypeError("Expected ReframeBookDraft")
        self._check(principal=principal, action="book.draft.reframe", scope=command.scope)
        with self._uow_factory() as uow:
            current = uow.books.get(command.scope)
            if current is None:
                raise BookDraftNotFound("Draft not found in this book scope")
            updated = current.reframe(
                command.framework, expected_revision=command.expected_revision,
                reason=command.reason,
            )
            uow.books.save(updated, expected_revision=command.expected_revision)
            uow.commit()
        return updated

    def get(
        self, query: GetBookDraft, *, principal: TrustedPrincipal
    ) -> AccountingBookDraft:
        if not isinstance(query, GetBookDraft):
            raise TypeError("Expected GetBookDraft")
        self._check(principal=principal, action="book.draft.read", scope=query.scope)
        with self._uow_factory() as uow:
            current = uow.books.get(query.scope)
            if current is None:
                raise BookDraftNotFound("Draft not found in this book scope")
            return current

    def list(
        self, query: ListBookDrafts, *, principal: TrustedPrincipal
    ) -> tuple[AccountingBookDraft, ...]:
        if not isinstance(query, ListBookDrafts):
            raise TypeError("Expected ListBookDrafts")
        self._check(principal=principal, action="book.draft.list", scope=query.scope)
        with self._uow_factory() as uow:
            return uow.books.list_for_entity(query.scope)
