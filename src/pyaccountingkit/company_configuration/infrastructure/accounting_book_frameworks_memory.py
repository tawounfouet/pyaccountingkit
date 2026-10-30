"""Process-local read-only reference fixtures; NOT the Normative Layer."""

from datetime import date

from ..domain.accounting_books import (
    FrameworkUnavailable,
    InvalidFrameworkBinding,
    ReferenceFrameworkBindingCandidate,
)
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.effective_interval import EffectiveInterval
from ..domain.shared.references import ReferenceFrameworkRef


class MemoryBookFrameworkCandidates:
    """A typed, immutable test catalog. No save or publish functionality."""

    def __init__(
        self, bindings: tuple[ReferenceFrameworkBindingCandidate, ...]
    ) -> None:
        if not isinstance(bindings, tuple) or any(
            not isinstance(x, ReferenceFrameworkBindingCandidate) for x in bindings
        ):
            raise InvalidFrameworkBinding("Framework fixture must be a typed tuple")
        self._bindings = bindings

    def list_for_book(
        self, scope: ConfigurationScope
    ) -> tuple[ReferenceFrameworkBindingCandidate, ...]:
        if not isinstance(scope, ConfigurationScope) or scope.book_id is None:
            raise InvalidFrameworkBinding("Book-level query scope required")
        return tuple(x for x in self._bindings if x.scope == scope)


class MemoryNormativeFrameworkAvailability:
    """Explicit allowlist of dated references for tests, not legal verification."""

    def __init__(self) -> None:
        self._allow: list[tuple[ReferenceFrameworkRef, EffectiveInterval]] = []

    def allow(
        self, framework: ReferenceFrameworkRef, *, effective: EffectiveInterval
    ) -> None:
        if not isinstance(framework, ReferenceFrameworkRef) or not isinstance(
            effective, EffectiveInterval
        ):
            raise InvalidFrameworkBinding("Typed norm and business interval required")
        self._allow.append((framework, effective))

    def require_available(
        self, framework: ReferenceFrameworkRef, *, as_of: date
    ) -> None:
        if not isinstance(framework, ReferenceFrameworkRef) or type(as_of) is not date:
            raise FrameworkUnavailable("Invalid normative availability check")
        if not any(
            expected == framework and period.contains(as_of)
            for expected, period in self._allow
        ):
            raise FrameworkUnavailable("Framework reference unavailable in test catalog")
