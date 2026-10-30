"""L04-02 local, process-only book draft ports adapter: NOT a database or IAM.

The store offers a locked, copy-on-enter transaction for deterministic R&D.
It does not provide distributed locking, durable audit, SQL grants or legal
company/ownership attestation. No connection to the L03 HOLD SQL path.
"""

from collections.abc import Callable
from threading import RLock

from ..application.accounting_books import (
    BookDraftPermissionDenied,
    BookDraftUnitOfWork,
)
from ..application.ports import TrustedPrincipal
from ..domain.accounting_books import (
    AccountingBookDraft,
    InvalidAccountingBook,
    require_unique_book_code,
)
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.errors import VersionConflict
from ..domain.shared.identifiers import AccountingBookId, CompanyId, LegalEntityId


class MemoryBookAuthorization:
    """Explicit action-level test allowlist; not a real identity provider."""

    def __init__(self) -> None:
        self._grants: set[tuple[str, str, ConfigurationScope]] = set()

    def grant(
        self, *, principal: TrustedPrincipal, action: str, scope: ConfigurationScope
    ) -> None:
        if not isinstance(principal, TrustedPrincipal) or (
            principal.tenant_id != scope.tenant_id
        ):
            raise BookDraftPermissionDenied("Tenant-bound principal required")
        self._grants.add((principal.actor_id, action, scope))

    def require(
        self, *, principal: TrustedPrincipal, action: str, scope: ConfigurationScope
    ) -> None:
        if not isinstance(principal, TrustedPrincipal) or (
            principal.tenant_id != scope.tenant_id
        ) or (principal.actor_id, action, scope) not in self._grants:
            raise BookDraftPermissionDenied("Action not explicitly granted")

    def revoke(
        self, *, principal: TrustedPrincipal, action: str, scope: ConfigurationScope
    ) -> None:
        self._grants.discard((principal.actor_id, action, scope))


class MemoryCompanyEntityMembership:
    """Test fixture only; an allowlisted pair does NOT prove legal membership."""

    def __init__(self) -> None:
        self._pairs: set[tuple[str, CompanyId, LegalEntityId]] = set()

    def allow(self, scope: ConfigurationScope) -> None:
        if not isinstance(scope, ConfigurationScope):
            raise InvalidAccountingBook("ConfigurationScope required")
        self._pairs.add((scope.tenant_id, scope.company_id, scope.legal_entity_id))

    def require(self, *, scope: ConfigurationScope) -> None:
        if not isinstance(scope, ConfigurationScope) or (
            scope.tenant_id, scope.company_id, scope.legal_entity_id
        ) not in self._pairs:
            raise BookDraftPermissionDenied("Company/entity relationship unverified")

    def revoke(self, scope: ConfigurationScope) -> None:
        self._pairs.discard((scope.tenant_id, scope.company_id, scope.legal_entity_id))


class MemoryBookStore:
    """Private state; no external writes beyond a committed unit of work."""

    def __init__(self) -> None:
        self._books: dict[tuple[str, AccountingBookId], AccountingBookDraft] = {}
        self.lock = RLock()

    def snapshot(self) -> tuple[AccountingBookDraft, ...]:
        with self.lock:
            return tuple(self._books.values())


class MemoryBookRepository:
    """Optimistic revision and uniqueness policy under the UoW's store lock."""

    def __init__(
        self, data: dict[tuple[str, AccountingBookId], AccountingBookDraft]
    ) -> None:
        self._data = data

    def get(self, scope: ConfigurationScope) -> AccountingBookDraft | None:
        if not isinstance(scope, ConfigurationScope) or scope.book_id is None:
            raise InvalidAccountingBook("Book scope required")
        found = self._data.get((scope.tenant_id, scope.book_id))
        return found if found is not None and found.scope == scope else None

    def list_for_entity(
        self, scope: ConfigurationScope
    ) -> tuple[AccountingBookDraft, ...]:
        if not isinstance(scope, ConfigurationScope) or scope.book_id is not None:
            raise InvalidAccountingBook("Entity-level query scope required")
        results = [
            draft for draft in self._data.values()
            if draft.scope.tenant_id == scope.tenant_id
            and draft.scope.company_id == scope.company_id
            and draft.scope.legal_entity_id == scope.legal_entity_id
        ]
        return tuple(sorted(results, key=lambda x: (x.code.value, str(x.id))))

    def save(self, draft: AccountingBookDraft, *, expected_revision: int) -> None:
        if not isinstance(draft, AccountingBookDraft):
            raise InvalidAccountingBook("Typed book draft required")
        if type(expected_revision) is not int or expected_revision < 0:
            raise VersionConflict("Invalid optimistic revision")
        key = (draft.scope.tenant_id, draft.id)
        previous = self._data.get(key)
        if previous is None:
            if expected_revision != 0 or draft.revision != 1:
                raise VersionConflict("New draft requires expected revision 0 and revision 1")
        elif (
            previous.scope != draft.scope
            or previous.revision != expected_revision
            or draft.revision != expected_revision + 1
        ):
            raise VersionConflict("Book draft revision or accounting scope conflict")
        require_unique_book_code(draft, tuple(self._data.values()))
        self._data[key] = draft


class MemoryBookUnitOfWork:
    """One-process serializable fake with explicit commit and rollback."""

    def __init__(
        self, store: MemoryBookStore, *, before_commit: Callable[[], None] | None = None
    ) -> None:
        self._store = store
        self._before_commit = before_commit
        self._active = False
        self._committed = False

    def __enter__(self) -> "MemoryBookUnitOfWork":
        self._store.lock.acquire()
        try:
            self._working = self._store._books.copy()
            self.books = MemoryBookRepository(self._working)
            self._active = True
            return self
        except BaseException:
            self._store.lock.release()
            raise

    def commit(self) -> None:
        if not self._active or self._committed:
            raise RuntimeError("A live, uncommitted unit of work is required")
        if self._before_commit is not None:
            self._before_commit()
        self._store._books = self._working.copy()
        self._committed = True

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._active:
            self._active = False
            self._store.lock.release()


def memory_book_uow_factory(store: MemoryBookStore) -> Callable[[], BookDraftUnitOfWork]:
    """Construct a local-only factory; never use as a production UoW."""
    return lambda: MemoryBookUnitOfWork(store)
