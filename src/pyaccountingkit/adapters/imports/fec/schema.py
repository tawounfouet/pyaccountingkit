"""Versioned French FEC source schema and adapter descriptor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


FEC_FIELD_NAMES: tuple[str, ...] = (
    "JournalCode",
    "JournalLib",
    "EcritureNum",
    "EcritureDate",
    "CompteNum",
    "CompteLib",
    "CompAuxNum",
    "CompAuxLib",
    "PieceRef",
    "PieceDate",
    "EcritureLib",
    "Debit",
    "Credit",
    "EcritureLet",
    "DateLet",
    "ValidDate",
    "Montantdevise",
    "Idevise",
)


@dataclass(frozen=True, slots=True)
class FECFieldDefinition:
    field_name: str
    required_column: bool
    semantic_target: str


FEC_FIELDS: tuple[FECFieldDefinition, ...] = tuple(
    FECFieldDefinition(name, True, name) for name in FEC_FIELD_NAMES
)


@dataclass(frozen=True, slots=True)
class FECSourceDescriptor:
    """Parsing/normalization coordinates for one FEC source."""

    filename: str | None = None
    encoding: str = "utf-8-sig"
    delimiter: str | None = None
    fiscal_year_start: date | None = None
    fiscal_year_end: date | None = None
    default_currency: str = "EUR"
    source_system: str = "FEC"

    def __post_init__(self) -> None:
        if self.delimiter is not None and len(self.delimiter) != 1:
            raise ValueError("FEC delimiter must contain exactly one character")
        if (
            self.fiscal_year_start is not None
            and self.fiscal_year_end is not None
            and self.fiscal_year_start > self.fiscal_year_end
        ):
            raise ValueError("fiscal_year_start must be <= fiscal_year_end")
        if len(self.default_currency) != 3:
            raise ValueError("default_currency must be an ISO 4217 code")


def validate_fec_header(fieldnames: tuple[str, ...]) -> None:
    """Require the canonical 18-column FEC header in its regulatory order."""
    if fieldnames != FEC_FIELD_NAMES:
        missing = tuple(name for name in FEC_FIELD_NAMES if name not in fieldnames)
        extra = tuple(name for name in fieldnames if name not in FEC_FIELD_NAMES)
        raise ValueError(
            "invalid FEC header: expected canonical 18 fields; "
            f"missing={missing!r}, extra={extra!r}, actual={fieldnames!r}"
        )


__all__ = [
    "FEC_FIELDS",
    "FEC_FIELD_NAMES",
    "FECFieldDefinition",
    "FECSourceDescriptor",
    "validate_fec_header",
]
