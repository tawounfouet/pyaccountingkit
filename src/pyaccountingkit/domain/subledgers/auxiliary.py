"""Auxiliary identifiers remain distinct from company-account codes."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.domain.subledgers.errors import InvalidSubledgerConfigurationError


@dataclass(frozen=True, slots=True)
class AuxiliaryReference:
    system: str
    code: str
    label: str | None = None

    def __post_init__(self) -> None:
        if not self.system.strip():
            raise InvalidSubledgerConfigurationError("auxiliary reference system must not be empty")
        if not self.code.strip():
            raise InvalidSubledgerConfigurationError("auxiliary reference code must not be empty")
        if self.label is not None and not self.label.strip():
            raise InvalidSubledgerConfigurationError(
                "auxiliary reference label must be non-empty when provided"
            )


__all__ = ["AuxiliaryReference"]
