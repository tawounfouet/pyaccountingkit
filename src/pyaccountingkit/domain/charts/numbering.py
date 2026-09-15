"""Account code policies — charset, length, segments and generation (LOT-11).

The domain never assumes a universal numeric length or prefix semantics: every
format rule lives in an explicit policy (ADR COA-002/003/010/016).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from pyaccountingkit.core.errors import InvalidAccountCodeError

_DEFAULT_MAX_LENGTH = 50


class AccountCharset(StrEnum):
    """Character families admitted by an account code policy."""

    NUMERIC = "NUMERIC"
    ALPHABETIC = "ALPHABETIC"
    ALPHANUMERIC = "ALPHANUMERIC"
    CUSTOM_REGEX = "CUSTOM_REGEX"


_CHARSET_REGEX = {
    AccountCharset.NUMERIC: r"[0-9]",
    AccountCharset.ALPHABETIC: r"[A-Za-z]",
    AccountCharset.ALPHANUMERIC: r"[0-9A-Za-z]",
}


@dataclass(frozen=True, slots=True)
class AccountCodeSegment:
    """One positional part of a segmented account code."""

    name: str
    length: int | None = None
    charset: AccountCharset = AccountCharset.NUMERIC
    required: bool = True
    allowed_values: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Segment name must be non-empty")
        if self.length is not None and self.length <= 0:
            raise ValueError(f"Segment {self.name!r} length must be positive")
        if self.length is None and not self.required:
            raise ValueError(f"Segment {self.name!r} must be fixed-length to be optional")


@dataclass(frozen=True, slots=True)
class AccountCodeContext:
    """Extra business context carried into a code validation."""

    chart_id: str | None = None
    parent_code: str | None = None
    reference_code: str | None = None
    account_kind: str | None = None
    account_role: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AccountCodeValidationResult:
    """Deterministic outcome of a policy validation."""

    ok: bool
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NormalizedAccountCode:
    """Raw and canonical forms of a code, after deterministic normalization."""

    raw_value: str
    canonical_value: str


@dataclass(frozen=True, slots=True)
class AccountCodeGenerationRequest:
    """Inputs a policy may consume to build or expand a company code."""

    reference_code: str | None = None
    parent_code: str | None = None
    segments: Mapping[str, str] = field(default_factory=dict)
    sequence: str | None = None
    target_length: int | None = None


class AccountCodePolicy(ABC):
    """Strategy that validates and generates company account codes."""

    charset: AccountCharset
    max_length: int = _DEFAULT_MAX_LENGTH

    @property
    @abstractmethod
    def policy_id(self) -> str:
        """Stable policy identifier, e.g. ``numeric-fixed-8``."""

    @abstractmethod
    def generate(self, request: AccountCodeGenerationRequest) -> str:
        """Build a code from the request; raises on non-generatable input."""

    def normalize(self, code: str) -> str:
        """Deterministic canonical form (trim + case for alpha policies)."""
        return code.strip()

    def normalized(self, code: str) -> NormalizedAccountCode:
        return NormalizedAccountCode(
            raw_value=code,
            canonical_value=self.normalize(code),
        )

    def validate(
        self,
        code: str,
        context: AccountCodeContext | None = None,
    ) -> AccountCodeValidationResult:
        """Return validation errors without raising; safe for suggestion flows."""
        canonical = self.normalize(code)
        errors: list[str] = []
        if not canonical:
            errors.append("empty code")
        if len(canonical) > self.max_length:
            errors.append(f"longer than {self.max_length} chars")
        for kind, message in self._specific_checks(canonical, context):
            if kind == "length":
                errors.append(message)
            elif kind == "format":
                errors.append(message)
            else:
                errors.append(message)
        return AccountCodeValidationResult(ok=not errors, errors=tuple(errors))

    def require_valid(self, code: str, context: AccountCodeContext | None = None) -> str:
        """Raise ``InvalidAccountCodeError`` when the code violates the policy."""
        result = self.validate(code, context)
        if not result.ok:
            raise InvalidAccountCodeError("; ".join(result.errors))
        return self.normalize(code)

    def _specific_checks(
        self,
        canonical: str,
        context: AccountCodeContext | None,
    ) -> tuple[tuple[str, str], ...]:
        raise NotImplementedError

    def _charset_pattern(self, charset: AccountCharset, custom: str | None = None) -> str:
        if charset is AccountCharset.CUSTOM_REGEX:
            if custom is None:
                raise ValueError("CUSTOM_REGEX requires an explicit pattern")
            return f"(?:{custom})"
        return _CHARSET_REGEX[charset]


class NumericFixedLengthPolicy(AccountCodePolicy):
    """Exactly ``length`` numeric digits; padding only when explicitly configured."""

    charset: AccountCharset = AccountCharset.NUMERIC

    def __init__(
        self,
        *,
        length: int,
        policy_id: str | None = None,
        padding_char: str = "",
    ) -> None:
        if length <= 0:
            raise ValueError("length must be positive")
        if len(padding_char) > 1:
            raise ValueError("padding_char must be a single character")
        self.length = length
        self.max_length = length
        self._policy_id = policy_id or f"numeric-fixed-{length}"
        self._padding_char = padding_char or ""

    @property
    def policy_id(self) -> str:
        return self._policy_id

    def generate(self, request: AccountCodeGenerationRequest) -> str:
        base = request.reference_code or request.parent_code
        if base is None:
            raise InvalidAccountCodeError(
                f"Policy {self.policy_id}: a reference or parent code is required"
            )
        code = base
        if self._padding_char and len(code) < self.length:
            code = code + self._padding_char * (self.length - len(code))
        if len(code) != self.length or not code.isdigit():
            raise InvalidAccountCodeError(
                f"Policy {self.policy_id}: cannot generate a {self.length}-digit code from {base!r}"
            )
        return code

    def _specific_checks(
        self,
        canonical: str,
        context: AccountCodeContext | None,
    ) -> tuple[tuple[str, str], ...]:
        errors: list[tuple[str, str]] = []
        if not canonical.isdigit():
            errors.append(("format", "must contain only digits"))
        if len(canonical) != self.length:
            errors.append(("length", f"must be exactly {self.length} chars"))
        return tuple(errors)


class NumericVariableLengthPolicy(AccountCodePolicy):
    """Digits between ``min_length`` and ``max_length`` (length is not an invariant)."""

    charset: AccountCharset = AccountCharset.NUMERIC

    def __init__(
        self,
        *,
        min_length: int = 3,
        max_length: int = 12,
        policy_id: str | None = None,
    ) -> None:
        if not (1 <= min_length <= max_length):
            raise ValueError("min_length must be within 1..max_length")
        self.min_length = min_length
        self.max_length = max_length
        self._policy_id = policy_id or f"numeric-variable-{min_length}-{max_length}"

    @property
    def policy_id(self) -> str:
        return self._policy_id

    def generate(self, request: AccountCodeGenerationRequest) -> str:
        base = request.reference_code or request.parent_code
        if base is None or not base.isdigit():
            raise InvalidAccountCodeError(
                f"Policy {self.policy_id}: a numeric reference code is required"
            )
        return self.require_valid(base)

    def _specific_checks(
        self,
        canonical: str,
        context: AccountCodeContext | None,
    ) -> tuple[tuple[str, str], ...]:
        errors: list[tuple[str, str]] = []
        if not canonical.isdigit():
            errors.append(("format", "must contain only digits"))
        if not (self.min_length <= len(canonical) <= self.max_length):
            errors.append(("length", f"must be {self.min_length}-{self.max_length} chars"))
        return tuple(errors)


class SegmentedNumericPolicy(AccountCodePolicy):
    """Fixed-length digits segments, concatenated as the canonical storage form."""

    charset: AccountCharset = AccountCharset.NUMERIC

    def __init__(
        self,
        segments: tuple[AccountCodeSegment, ...],
        policy_id: str | None = None,
    ) -> None:
        if not segments:
            raise ValueError("at least one segment is required")
        for segment in segments:
            if segment.length is None:
                raise ValueError(f"Segment {segment.name!r} must declare a fixed length")
        self.segments = segments
        self.max_length = sum(segment.length or 0 for segment in segments)
        self._policy_id = policy_id or "segmented-numeric"

    @property
    def policy_id(self) -> str:
        return self._policy_id

    def split(self, canonical: str) -> dict[str, str]:
        """Split a canonical code into its segment values."""
        offset = 0
        parts: dict[str, str] = {}
        for segment in self.segments:
            end = offset + (segment.length or 0)
            parts[segment.name] = canonical[offset:end]
            offset = end
        return parts

    def generate(self, request: AccountCodeGenerationRequest) -> str:
        values = []
        for segment in self.segments:
            value = request.segments.get(segment.name, "")
            if not segment.required and not value:
                values.append("")
                continue
            if not value:
                raise InvalidAccountCodeError(
                    f"Segment {segment.name!r} is required for generation"
                )
            if segment.length is not None and len(value) != segment.length:
                raise InvalidAccountCodeError(
                    f"Segment {segment.name!r} must be {segment.length} chars"
                )
            pattern = self._charset_pattern(segment.charset)
            if not re.fullmatch(f"{pattern}+", value):
                raise InvalidAccountCodeError(
                    f"Segment {segment.name!r} violates charset {segment.charset.value}"
                )
            if segment.allowed_values and value not in segment.allowed_values:
                raise InvalidAccountCodeError(
                    f"Segment {segment.name!r} value {value!r} not allowed"
                )
            values.append(value)
        return "".join(values)

    def _specific_checks(
        self,
        canonical: str,
        context: AccountCodeContext | None,
    ) -> tuple[tuple[str, str], ...]:
        expected = sum(segment.length or 0 for segment in self.segments)
        if len(canonical) != expected:
            return (("length", f"must be exactly {expected} chars"),)
        if not canonical.isdigit():
            return (("format", "must contain only digits"),)
        return ()


class AlphanumericPolicy(AccountCodePolicy):
    """Alphanumeric codes constrained by an explicit regex pattern."""

    charset: AccountCharset = AccountCharset.ALPHANUMERIC

    def __init__(
        self,
        *,
        pattern: str,
        min_length: int = 1,
        max_length: int = _DEFAULT_MAX_LENGTH,
        policy_id: str | None = None,
    ) -> None:
        self._pattern = re.compile(f"^{pattern}$")
        self.min_length = min_length
        self.max_length = max_length
        self._policy_id = policy_id or "alphanumeric"

    @property
    def policy_id(self) -> str:
        return self._policy_id

    def normalize(self, code: str) -> str:
        return code.strip().upper()

    def generate(self, request: AccountCodeGenerationRequest) -> str:
        reference = request.reference_code
        sequence = request.sequence
        candidate: str | None = None
        if reference and sequence:
            candidate = f"{reference}-{sequence}"
        elif reference:
            candidate = reference
        elif sequence:
            candidate = sequence
        if candidate is None:
            raise InvalidAccountCodeError(
                f"Policy {self.policy_id}: reference or sequence is required"
            )
        return self.require_valid(candidate)

    def _specific_checks(
        self,
        canonical: str,
        context: AccountCodeContext | None,
    ) -> tuple[tuple[str, str], ...]:
        errors: list[tuple[str, str]] = []
        if len(canonical) < self.min_length:
            errors.append(("length", f"must be at least {self.min_length} chars"))
        if not self._pattern.fullmatch(canonical):
            errors.append(("format", f"must match {self._pattern.pattern}"))
        return tuple(errors)


class CustomAccountCodePolicy(AccountCodePolicy):
    """Bespoke policy: an explicit regex plus an optional generation template."""

    charset: AccountCharset = AccountCharset.CUSTOM_REGEX

    def __init__(
        self,
        *,
        pattern: str,
        policy_id: str,
        generation_template: Callable[[AccountCodeGenerationRequest], str] | None = None,
        max_length: int = _DEFAULT_MAX_LENGTH,
    ) -> None:
        self._pattern = re.compile(f"^{pattern}$")
        self._policy_id = policy_id
        self._template = generation_template
        self.max_length = max_length

    @property
    def policy_id(self) -> str:
        return self._policy_id

    def generate(self, request: AccountCodeGenerationRequest) -> str:
        if self._template is None:
            raise InvalidAccountCodeError(f"Policy {self._policy_id}: generation is not supported")
        candidate = self._template(request)
        self.require_valid(candidate)
        return self.normalize(candidate)

    def _specific_checks(
        self,
        canonical: str,
        context: AccountCodeContext | None,
    ) -> tuple[tuple[str, str], ...]:
        if not self._pattern.fullmatch(canonical):
            return (("format", f"must match {self._pattern.pattern}"),)
        return ()


__all__ = [
    "AccountCharset",
    "AccountCodeContext",
    "AccountCodeGenerationRequest",
    "AccountCodePolicy",
    "AccountCodeSegment",
    "AccountCodeValidationResult",
    "NormalizedAccountCode",
    "NumericFixedLengthPolicy",
    "NumericVariableLengthPolicy",
    "SegmentedNumericPolicy",
    "AlphanumericPolicy",
    "CustomAccountCodePolicy",
]
