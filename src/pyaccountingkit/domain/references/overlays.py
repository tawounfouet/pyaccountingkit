"""Read-only regulatory overlay provenance (LOT-27)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from pyaccountingkit.domain.references.effective_plan import RegulatorySourceReference


@dataclass(frozen=True, slots=True)
class ReferenceOverlayEntry:
    """One source-backed extension delta; never an implicit runtime mutation rule."""

    overlay_id: str
    standard_id: str
    edition: str
    base_standard: str
    ref_code: str
    overlay_type: str
    canonical_effect: str
    regulatory_status: str
    extension_label: str
    source_ref: RegulatorySourceReference
    base_label: str | None = None

    def __post_init__(self) -> None:
        required = (
            self.overlay_id,
            self.standard_id,
            self.edition,
            self.base_standard,
            self.ref_code,
            self.overlay_type,
            self.canonical_effect,
            self.regulatory_status,
            self.extension_label,
        )
        if any(not value.strip() for value in required):
            raise ValueError("overlay identity and provenance fields must be non-empty")


@dataclass(frozen=True, slots=True)
class ReferenceOverlay:
    """Audit/explanation view of one regulatory extension overlay."""

    standard_id: str
    edition: str
    base_standard: str
    entries: tuple[ReferenceOverlayEntry, ...]
    extension_codes: tuple[str, ...]
    regulatory_basis: Mapping[str, str] = field(default_factory=dict)
    statistics: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.standard_id.strip() or not self.edition.strip() or not self.base_standard.strip():
            raise ValueError("overlay coordinates must be non-empty")
        if not self.entries:
            raise ValueError("overlay must contain entries")

        ids = [entry.overlay_id for entry in self.entries]
        codes = [entry.ref_code for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("overlay contains duplicate overlay_id")
        if len(codes) != len(set(codes)):
            raise ValueError("overlay contains duplicate ref_code")
        if set(codes) != set(self.extension_codes):
            raise ValueError("overlay extension_codes must match entry ref_codes")

        for entry in self.entries:
            if (
                entry.standard_id != self.standard_id
                or entry.edition != self.edition
                or entry.base_standard != self.base_standard
            ):
                raise ValueError("overlay entry coordinates must match overlay coordinates")

        if sum(self.statistics.values()) not in {0, len(self.entries)}:
            raise ValueError("overlay statistics must account for every entry")

    def entry(self, code_or_id: str) -> ReferenceOverlayEntry | None:
        for entry in self.entries:
            if entry.overlay_id == code_or_id or entry.ref_code == code_or_id:
                return entry
        return None


__all__ = ["ReferenceOverlay", "ReferenceOverlayEntry"]
