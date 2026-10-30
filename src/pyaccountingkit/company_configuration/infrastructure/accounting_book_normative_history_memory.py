"""Read-only in-process historical statement fixture (NOT a Normative Layer).

The caller controls this fake; none of its statements are verified, signed,
officially published or intrinsically trustworthy.
"""

from ..domain.accounting_books import (
    InvalidNormativeStatement,
    NormativeReferenceStatement,
    NormativeSourceCode,
)
from ..domain.shared.references import ReferenceFrameworkRef


class MemoryNormativeReferenceClaims:
    """Immutable test fixture with exact source and version matching."""

    def __init__(self, statements: tuple[NormativeReferenceStatement, ...]) -> None:
        if not isinstance(statements, tuple) or any(
            not isinstance(x, NormativeReferenceStatement) for x in statements
        ):
            raise InvalidNormativeStatement("Typed immutable statement tuple required")
        self._statements = statements

    def list_for_reference(
        self, framework: ReferenceFrameworkRef, source: NormativeSourceCode
    ) -> tuple[NormativeReferenceStatement, ...]:
        if not isinstance(framework, ReferenceFrameworkRef) or not isinstance(
            source, NormativeSourceCode
        ):
            raise InvalidNormativeStatement("Typed framework and source required")
        return tuple(
            x for x in self._statements
            if x.framework == framework and x.source == source
        )
