"""L04-04: reference-framework binding candidates, not normative decisions.

One effective binding per book and purpose at the preview date. This pure
domain model cannot prove IFRS/PCG/SYSCOHADA legality or publish a configuration.
"""

from dataclasses import dataclass
from datetime import date

from ..shared.accounting_scope import ConfigurationScope
from ..shared.effective_interval import EffectiveInterval
from ..shared.errors import DomainError
from ..shared.identifiers import FrameworkBindingId
from ..shared.references import ReferenceFrameworkRef
from .assignments import BookAssignmentPurpose
from .model import AccountingBookDraft


class InvalidFrameworkBinding(DomainError):
    code = "INVALID_FRAMEWORK_BINDING"


class FrameworkBindingMissing(DomainError):
    code = "FRAMEWORK_BINDING_MISSING"


class FrameworkBindingAmbiguous(DomainError):
    code = "FRAMEWORK_BINDING_AMBIGUOUS"


class FrameworkUnavailable(DomainError):
    code = "FRAMEWORK_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class ReferenceFrameworkBindingCandidate:
    """Book-specific dated choice, separate from Normative Layer's own content."""

    id: FrameworkBindingId
    scope: ConfigurationScope
    purpose: BookAssignmentPurpose
    framework: ReferenceFrameworkRef
    effective: EffectiveInterval
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, FrameworkBindingId):
            raise InvalidFrameworkBinding("Typed FrameworkBindingId required")
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is None:
            raise InvalidFrameworkBinding("Explicit book-level scope required")
        if not isinstance(self.purpose, BookAssignmentPurpose):
            raise InvalidFrameworkBinding("Typed purpose required")
        if not isinstance(self.framework, ReferenceFrameworkRef):
            raise InvalidFrameworkBinding("Typed versioned normative reference required")
        if not isinstance(self.effective, EffectiveInterval):
            raise InvalidFrameworkBinding("EffectiveInterval required")
        if (
            not isinstance(self.source_ref, str)
            or not self.source_ref.strip()
            or self.source_ref.strip() != self.source_ref
        ):
            raise InvalidFrameworkBinding("Nonblank trimmed source reference required")

    def require_draft_compatibility(self, book: AccountingBookDraft) -> None:
        """L04-01 stores one reference: do not silently override that pointer.

        Distinct historical frameworks within one published book are deferred
        until book versioning and known_at are modeled and independently approved.
        """
        if not isinstance(book, AccountingBookDraft):
            raise InvalidFrameworkBinding("Typed draft book required")
        if self.scope != book.scope:
            raise InvalidFrameworkBinding("Framework binding crosses book accounting scope")
        if self.framework != book.framework:
            raise InvalidFrameworkBinding("Binding conflicts with book draft reference")
        if self.effective.start < book.effective.start or (
            book.effective.end is not None
            and (self.effective.end is None or self.effective.end > book.effective.end)
        ):
            raise InvalidFrameworkBinding("Binding extends beyond book validity")


@dataclass(frozen=True, slots=True)
class BookFrameworkPreview:
    """Explicitly non-authoritative R&D preview, never a published C10 result."""

    book_scope: ConfigurationScope
    binding_id: FrameworkBindingId
    framework: ReferenceFrameworkRef
    purpose: BookAssignmentPurpose
    as_of: date


def preview_reference_framework_binding(
    *,
    book: AccountingBookDraft,
    scope: ConfigurationScope,
    purpose: BookAssignmentPurpose,
    as_of: date,
    bindings: tuple[ReferenceFrameworkBindingCandidate, ...],
) -> BookFrameworkPreview:
    """Pure fail-closed selection; no hidden defaults or latest-version fallback."""
    if not isinstance(book, AccountingBookDraft):
        raise InvalidFrameworkBinding("Typed draft book required")
    if not isinstance(scope, ConfigurationScope) or scope.book_id is None:
        raise InvalidFrameworkBinding("Book-level query scope required")
    if book.scope != scope:
        raise InvalidFrameworkBinding("Queried book does not match requested scope")
    if not isinstance(purpose, BookAssignmentPurpose):
        raise InvalidFrameworkBinding("Typed purpose required")
    if type(as_of) is not date:
        raise InvalidFrameworkBinding("as_of must be a date, not datetime")
    if not isinstance(bindings, tuple):
        raise InvalidFrameworkBinding("Bindings must be an immutable tuple")

    chosen: ReferenceFrameworkBindingCandidate | None = None
    seen = set()
    for binding in bindings:
        if not isinstance(binding, ReferenceFrameworkBindingCandidate):
            raise InvalidFrameworkBinding("Catalog contains a non-binding")
        if binding.id in seen:
            raise FrameworkBindingAmbiguous("Duplicate framework binding identity")
        seen.add(binding.id)
        # Fail closed even if an out-of-scope binding is for a different purpose.
        binding.require_draft_compatibility(book)
        if binding.purpose == purpose and binding.effective.contains(as_of):
            if chosen is not None:
                raise FrameworkBindingAmbiguous(
                    "Multiple framework bindings apply to the same book/purpose/date"
                )
            chosen = binding

    if chosen is None:
        raise FrameworkBindingMissing(
            "No explicitly bound reference framework for this book/purpose/date"
        )
    if not book.effective.contains(as_of):
        raise InvalidFrameworkBinding("Book is not effective at the requested date")
    return BookFrameworkPreview(
        book_scope=scope,
        binding_id=chosen.id,
        framework=chosen.framework,
        purpose=purpose,
        as_of=as_of,
    )
