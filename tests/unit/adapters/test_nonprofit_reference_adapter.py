"""Unit tests for the France Non-Profit effective-plan provider."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyaccountingkit.adapters.regulatory.nonprofit import (
    NonProfitFilesystemReferenceAdapter,
    parse_effective_plan,
    parse_reference_overlay,
)
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.domain.references.capabilities import ReferenceCapability
from pyaccountingkit.domain.references.effective_plan import EffectiveAccountOrigin


def test_effective_plan_parser_preserves_provider_resolution() -> None:
    document = {
        "standard_id": "fr-nonprofit",
        "edition": "2026",
        "base_standard": "fr-pcg:2026",
        "inheritance_rule": "official rule",
        "statistics": {
            "effective_accounts_or_groups": 2,
            "extension_additions": 1,
            "extension_overrides": 0,
            "inherited": 1,
        },
        "accounts": [
            {
                "account_id": "account:fr-nonprofit:2026:101",
                "base_account_id": "account:fr-pcg:2026:101",
                "base_label": "Capital",
                "extension_source_ref": None,
                "label": "Capital",
                "origin": "inherited_from_base_standard",
                "provenance_type": "derived",
                "ref_code": "101",
            },
            {
                "account_id": "account:fr-nonprofit:2026:19",
                "base_account_id": None,
                "base_label": None,
                "extension_source_ref": {
                    "document_id": "source",
                    "page_pdf": 37,
                    "section": "Art. 320-2",
                    "snippet": "19 - Fonds dédiés",
                    "source_line_md": 1722,
                },
                "label": "Fonds dédiés",
                "origin": "extension_addition",
                "provenance_type": "official_source",
                "ref_code": "19",
            },
        ],
    }
    plan = parse_effective_plan(document)
    assert plan.account("101").origin is EffectiveAccountOrigin.INHERITED_FROM_BASE_STANDARD
    assert plan.account("19").extension_source_ref.document_id == "source"


def test_overlay_parser_preserves_source_reference() -> None:
    document = {
        "base_standard": "fr-pcg:2026",
        "edition": "2026",
        "extension_codes": ["19"],
        "overlay_entries": [
            {
                "base_label_source": None,
                "base_standard": "fr-pcg:2026",
                "canonical_effect": "replace_or_add",
                "edition": "2026",
                "extension_label_source": "Fonds dédiés",
                "overlay_id": "overlay:fr-nonprofit:2026:19",
                "overlay_type": "specific_addition",
                "ref_code": "19",
                "regulatory_status": "official_extension",
                "source_ref": {
                    "document_id": "source",
                    "page_pdf": 37,
                    "section": "Art. 320-2",
                    "snippet": "19 - Fonds dédiés",
                    "source_line_md": 1722,
                },
                "standard_id": "fr-nonprofit",
            }
        ],
        "regulatory_basis": {
            "inheritance_article": "320-1",
            "source_document_id": "source",
            "specific_accounts_article": "320-2",
        },
        "standard_id": "fr-nonprofit",
        "statistics": {"specific_addition": 1},
    }
    overlay = parse_reference_overlay(document)
    assert overlay.entry("19").source_ref.page_pdf == 37


def test_provider_loads_effective_plan_without_requiring_overlay(tmp_path: Path) -> None:
    plan = {
        "standard_id": "fr-nonprofit",
        "edition": "2026",
        "base_standard": "fr-pcg:2026",
        "statistics": {
            "effective_accounts_or_groups": 1,
            "extension_additions": 0,
            "extension_overrides": 0,
            "inherited": 1,
        },
        "accounts": [
            {
                "account_id": "account:fr-nonprofit:2026:101",
                "base_account_id": "account:fr-pcg:2026:101",
                "base_label": "Capital",
                "extension_source_ref": None,
                "label": "Capital",
                "origin": "inherited_from_base_standard",
                "provenance_type": "derived",
                "ref_code": "101",
            }
        ],
    }
    (tmp_path / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    provider = NonProfitFilesystemReferenceAdapter(
        tmp_path,
        clock=FrozenClock(),
        effective_plan_filename="plan.json",
        overlay_filename="missing-overlay.json",
    )
    assert provider.get_effective_plan("fr-nonprofit", "2026").account("101") is not None
    assert provider.capabilities("fr-nonprofit", "2026").supports(
        ReferenceCapability.EFFECTIVE_PLAN
    )


def test_provider_fails_closed_on_wrong_coordinates(tmp_path: Path) -> None:
    provider = NonProfitFilesystemReferenceAdapter(tmp_path)
    with pytest.raises(KeyError, match="unsupported effective plan"):
        provider.get_effective_plan("fr-pcg", "2026")
