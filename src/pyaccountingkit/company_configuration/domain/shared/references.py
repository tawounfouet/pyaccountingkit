"""Typed external references; normative ownership remains external."""

import re
from dataclasses import dataclass

from .errors import InvalidReference


@dataclass(frozen=True, slots=True)
class CurrencyCode:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not re.fullmatch(r"[A-Z]{3}", self.value):
            raise InvalidReference("CurrencyCode must be three uppercase ASCII letters")


@dataclass(frozen=True, slots=True)
class ReferenceFrameworkRef:
    """Versioned pointer; does not certify norm validity or define IFRS accounts."""

    framework_code: str
    version: str

    def __post_init__(self) -> None:
        if not isinstance(self.framework_code, str) or not self.framework_code.strip():
            raise InvalidReference("A framework code is required")
        if self.framework_code.strip() != self.framework_code:
            raise InvalidReference("Framework code cannot have surrounding whitespace")
        if not isinstance(self.version, str) or not self.version.strip():
            raise InvalidReference("An explicit framework version is required")
        if self.version.strip() != self.version:
            raise InvalidReference("Framework version cannot have surrounding whitespace")


@dataclass(frozen=True, slots=True)
class JurisdictionCode:
    """Two-letter code shape only, not validation of legal existence."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not re.fullmatch(r"[A-Z]{2}", self.value):
            raise InvalidReference("JurisdictionCode requires two uppercase ASCII letters")
