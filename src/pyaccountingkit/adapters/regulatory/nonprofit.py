"""France Non-Profit 2026 effective-plan filesystem provider (LOT-27)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pyaccountingkit.core.clock import ClockProtocol, SystemClock
from pyaccountingkit.domain.references.capabilities import (
    NONPROFIT_EFFECTIVE_CAPABILITIES,
    ReferenceCapabilitySet,
)
from pyaccountingkit.domain.references.effective_plan import (
    EffectiveAccountOrigin,
    EffectiveAccountPlan,
    EffectiveReferenceAccount,
    RegulatorySourceReference,
)
from pyaccountingkit.domain.references.overlays import ReferenceOverlay, ReferenceOverlayEntry
from pyaccountingkit.domain.references.snapshots import EffectivePlanSnapshot

NONPROFIT_STANDARD_ID = "fr-nonprofit"
NONPROFIT_EDITION = "2026"
NONPROFIT_EFFECTIVE_PLAN_FILENAME = "nonprofit_2026_v1_effective_plan.json"
NONPROFIT_OVERLAY_FILENAME = "nonprofit_2026_v1_account_overlay.json"


class NonProfitFilesystemReferenceAdapter:
    """Read the upstream resolved plan directly; overlays remain audit-only evidence."""

    def __init__(
        self,
        base_path: Path,
        *,
        clock: ClockProtocol | None = None,
        effective_plan_filename: str = NONPROFIT_EFFECTIVE_PLAN_FILENAME,
        overlay_filename: str = NONPROFIT_OVERLAY_FILENAME,
    ) -> None:
        self._base_path = base_path
        self._clock = clock or SystemClock()
        self._effective_plan_filename = effective_plan_filename
        self._overlay_filename = overlay_filename
        self._plan: EffectiveAccountPlan | None = None
        self._overlay: ReferenceOverlay | None = None

    def get_effective_plan(self, standard_id: str, edition: str) -> EffectiveAccountPlan:
        self._require_supported_coordinates(standard_id, edition)
        if self._plan is None:
            self._plan = parse_effective_plan(self._load(self._effective_plan_filename))
        return self._plan

    def get_overlay(self, standard_id: str, edition: str) -> ReferenceOverlay:
        self._require_supported_coordinates(standard_id, edition)
        if self._overlay is None:
            self._overlay = parse_reference_overlay(self._load(self._overlay_filename))
        return self._overlay

    def get_effective_plan_snapshot(
        self,
        standard_id: str,
        edition: str,
        version: str,
    ) -> EffectivePlanSnapshot:
        return EffectivePlanSnapshot.seal(
            self.get_effective_plan(standard_id, edition),
            version,
            self._clock.now(),
        )

    def capabilities(self, standard_id: str, edition: str) -> ReferenceCapabilitySet:
        self._require_supported_coordinates(standard_id, edition)
        return NONPROFIT_EFFECTIVE_CAPABILITIES

    def _load(self, filename: str) -> Mapping[str, Any]:
        raw = (self._base_path / filename).read_text(encoding="utf-8")
        document = json.loads(raw)
        if not isinstance(document, dict):
            raise ValueError(f"{filename} must contain a JSON object")
        return document

    @staticmethod
    def _require_supported_coordinates(standard_id: str, edition: str) -> None:
        if standard_id != NONPROFIT_STANDARD_ID or edition != NONPROFIT_EDITION:
            raise KeyError(f"unsupported effective plan {standard_id}:{edition}")


def parse_effective_plan(document: Mapping[str, Any]) -> EffectiveAccountPlan:
    """Parse the canonical upstream effective-plan artifact without replaying overlays."""
    raw_accounts = document.get("accounts")
    if not isinstance(raw_accounts, list):
        raise ValueError("effective plan accounts must be a list")
    accounts = tuple(_parse_effective_account(raw) for raw in raw_accounts)

    statistics = _string_int_mapping(document.get("statistics"), "effective plan statistics")
    return EffectiveAccountPlan(
        standard_id=_required_string(document, "standard_id"),
        edition=_required_string(document, "edition"),
        base_standard=_required_string(document, "base_standard"),
        inheritance_rule=str(document.get("inheritance_rule") or ""),
        accounts=accounts,
        statistics=statistics,
    )


def parse_reference_overlay(document: Mapping[str, Any]) -> ReferenceOverlay:
    """Parse source-backed overlay metadata for audit; never resolve a plan from it."""
    raw_entries = document.get("overlay_entries")
    if not isinstance(raw_entries, list):
        raise ValueError("overlay_entries must be a list")
    entries = tuple(_parse_overlay_entry(raw) for raw in raw_entries)

    raw_codes = document.get("extension_codes")
    if not isinstance(raw_codes, list) or not all(isinstance(item, str) for item in raw_codes):
        raise ValueError("extension_codes must be a string list")

    return ReferenceOverlay(
        standard_id=_required_string(document, "standard_id"),
        edition=_required_string(document, "edition"),
        base_standard=_required_string(document, "base_standard"),
        entries=entries,
        extension_codes=tuple(raw_codes),
        regulatory_basis=_string_mapping(document.get("regulatory_basis"), "regulatory_basis"),
        statistics=_string_int_mapping(document.get("statistics"), "overlay statistics"),
    )


def _parse_effective_account(raw: object) -> EffectiveReferenceAccount:
    if not isinstance(raw, dict):
        raise ValueError("effective account must be a JSON object")
    source = raw.get("extension_source_ref")
    return EffectiveReferenceAccount(
        account_id=_required_string(raw, "account_id"),
        ref_code=_required_string(raw, "ref_code"),
        label=_required_string(raw, "label"),
        base_account_id=_optional_string(raw.get("base_account_id")),
        base_label=_optional_string(raw.get("base_label")),
        origin=EffectiveAccountOrigin(_required_string(raw, "origin")),
        provenance_type=_required_string(raw, "provenance_type"),
        extension_source_ref=None if source is None else _parse_source_reference(source),
    )


def _parse_overlay_entry(raw: object) -> ReferenceOverlayEntry:
    if not isinstance(raw, dict):
        raise ValueError("overlay entry must be a JSON object")
    return ReferenceOverlayEntry(
        overlay_id=_required_string(raw, "overlay_id"),
        standard_id=_required_string(raw, "standard_id"),
        edition=_required_string(raw, "edition"),
        base_standard=_required_string(raw, "base_standard"),
        ref_code=_required_string(raw, "ref_code"),
        overlay_type=_required_string(raw, "overlay_type"),
        canonical_effect=_required_string(raw, "canonical_effect"),
        regulatory_status=_required_string(raw, "regulatory_status"),
        extension_label=_required_string(raw, "extension_label_source"),
        base_label=_optional_string(raw.get("base_label_source")),
        source_ref=_parse_source_reference(raw.get("source_ref")),
    )


def _parse_source_reference(raw: object) -> RegulatorySourceReference:
    if not isinstance(raw, dict):
        raise ValueError("source reference must be a JSON object")
    page = raw.get("page_pdf")
    line = raw.get("source_line_md")
    if page is not None and not isinstance(page, int):
        raise ValueError("page_pdf must be an integer or null")
    if line is not None and not isinstance(line, int):
        raise ValueError("source_line_md must be an integer or null")
    return RegulatorySourceReference(
        document_id=_required_string(raw, "document_id"),
        page_pdf=page,
        section=_required_string(raw, "section"),
        snippet=_required_string(raw, "snippet"),
        source_line_md=line,
    )


def _required_string(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional string field must be string or null")
    return value


def _string_mapping(value: object, label: str) -> Mapping[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    if not all(isinstance(key, str) and isinstance(item, str) for key, item in value.items()):
        raise ValueError(f"{label} must contain string values")
    return dict(value)


def _string_int_mapping(value: object, label: str) -> Mapping[str, int]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    if not all(
        isinstance(key, str) and isinstance(item, int) and not isinstance(item, bool)
        for key, item in value.items()
    ):
        raise ValueError(f"{label} must contain integer values")
    return dict(value)


__all__ = [
    "NONPROFIT_EDITION",
    "NONPROFIT_EFFECTIVE_PLAN_FILENAME",
    "NONPROFIT_OVERLAY_FILENAME",
    "NONPROFIT_STANDARD_ID",
    "NonProfitFilesystemReferenceAdapter",
    "parse_effective_plan",
    "parse_reference_overlay",
]
