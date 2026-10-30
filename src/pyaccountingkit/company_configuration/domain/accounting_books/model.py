"""L04 (R&D): pure, immutable *draft* accounting-book model.

DDD Aggregate / Value Object: a draft defines an intended configuration,
not an activated ledger. This module cannot authorize Company membership,
certify a reference framework, publish a version or record journal entries.

Security boundary: G3 #71 HOLD; no infrastructure, SQL or IAM dependency.
"""

import re
from dataclasses import dataclass, replace

from ..shared.accounting_scope import ConfigurationScope
from ..shared.effective_interval import EffectiveInterval
from ..shared.errors import DomainError, VersionConflict
from ..shared.identifiers import AccountingBookId
from ..shared.references import CurrencyCode, ReferenceFrameworkRef


class InvalidAccountingBook(DomainError):
    """A proposed accounting-book configuration violates local invariants."""

    code = "INVALID_ACCOUNTING_BOOK"


class AccountingBookConflict(DomainError):
    """Two proposed books conflict within the explicitly scoped catalog."""

    code = "ACCOUNTING_BOOK_CONFLICT"


def _nonblank(value: str, field: str) -> None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
    ):
        raise InvalidAccountingBook(f"{field} must be a non-empty, trimmed string")


@dataclass(frozen=True, slots=True)
class BookCode:
    """Human-facing code, not a stable identity or normative account number.

    The conservative R&D syntax is intentionally provisional: migration to an
    approved business naming policy requires a later ADR.
    """

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not re.fullmatch(
            r"[A-Z][A-Z0-9_-]{0,31}", self.value
        ):
            raise InvalidAccountingBook(
                "BookCode must be 1–32 uppercase ASCII letters/digits/_/-; "
                "begin with a letter"
            )


@dataclass(frozen=True, slots=True, eq=False)
class AccountingBookDraft:
    """Immutable L04 proposal with explicit tenant, company and legal entity.

    The scope is *claimed intent*, never evidence that the legal entity belongs
    to the company. No status transition to ACTIVE is possible in this slice.
    A draft revision is not a durable audit event or a published accounting book.
    """

    id: AccountingBookId
    scope: ConfigurationScope
    code: BookCode
    label: str
    currency: CurrencyCode
    framework: ReferenceFrameworkRef
    effective: EffectiveInterval
    source_ref: str
    revision: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, AccountingBookId):
            raise InvalidAccountingBook("A typed AccountingBookId is required")
        if not isinstance(self.scope, ConfigurationScope):
            raise InvalidAccountingBook("A typed ConfigurationScope is required")
        if self.scope.book_id != self.id:
            raise InvalidAccountingBook("Book scope must bind to the matching book id")
        if not isinstance(self.code, BookCode):
            raise InvalidAccountingBook("Book code must be a typed BookCode")
        _nonblank(self.label, "label")
        if not isinstance(self.currency, CurrencyCode):
            raise InvalidAccountingBook("Book currency must be a CurrencyCode")
        if not isinstance(self.framework, ReferenceFrameworkRef):
            raise InvalidAccountingBook("An explicit versioned framework is required")
        if not isinstance(self.effective, EffectiveInterval):
            raise InvalidAccountingBook("Effective date interval is required")
        _nonblank(self.source_ref, "source_ref")
        if type(self.revision) is not int or self.revision < 1:
            raise InvalidAccountingBook("revision must be a positive integer")

    def __eq__(self, other: object) -> bool:
        """DDD Entity identity is tenant + BookId, not code or revision."""
        if not isinstance(other, AccountingBookDraft):
            return NotImplemented
        return (self.scope.tenant_id, self.id) == (other.scope.tenant_id, other.id)

    def __hash__(self) -> int:
        return hash((self.scope.tenant_id, self.id))

    def rename(
        self, label: str, *, expected_revision: int, reason: str
    ) -> "AccountingBookDraft":
        """Build another *candidate*, without granting authorization or writing."""
        self._check_revision(expected_revision, reason)
        _nonblank(label, "label")
        if label == self.label:
            raise InvalidAccountingBook("A rename must change the label")
        return replace(self, label=label, revision=self.revision + 1)

    def reframe(
        self, framework: ReferenceFrameworkRef, *, expected_revision: int, reason: str
    ) -> "AccountingBookDraft":
        """Propose a new reference; never assert that it is legally applicable."""
        self._check_revision(expected_revision, reason)
        if not isinstance(framework, ReferenceFrameworkRef):
            raise InvalidAccountingBook("Expected a versioned framework reference")
        if framework == self.framework:
            raise InvalidAccountingBook("A framework amendment must change the reference")
        return replace(self, framework=framework, revision=self.revision + 1)

    def _check_revision(self, expected_revision: int, reason: str) -> None:
        if type(expected_revision) is not int or expected_revision != self.revision:
            raise VersionConflict("AccountingBookDraft revision mismatch")
        _nonblank(reason, "reason")


def require_unique_book_code(
    candidate: AccountingBookDraft, existing: tuple[AccountingBookDraft, ...]
) -> None:
    """Pure policy: reject overlapping codes within one entity's draft perimeter.

    This is not a database uniqueness guarantee; concurrent persistence must
    enforce the policy independently. Same BookId denotes a revision of itself.
    Cross-entity book sharing and primary-vs-secondary ownership remain ADRs.
    """
    if not isinstance(candidate, AccountingBookDraft):
        raise InvalidAccountingBook("Expected an AccountingBookDraft")
    if not isinstance(existing, tuple):
        raise InvalidAccountingBook("Existing catalog must be an immutable tuple")
    for book in existing:
        if not isinstance(book, AccountingBookDraft):
            raise InvalidAccountingBook("Catalog contains a non-book value")
        if (book.scope.tenant_id, book.id) == (candidate.scope.tenant_id, candidate.id):
            continue
        if (
            book.scope.tenant_id == candidate.scope.tenant_id
            and book.scope.company_id == candidate.scope.company_id
            and book.scope.legal_entity_id == candidate.scope.legal_entity_id
            and book.code == candidate.code
            and book.effective.overlaps(candidate.effective)
        ):
            raise AccountingBookConflict(
                "Overlapping book codes in the same tenant/company/entity perimeter"
            )
