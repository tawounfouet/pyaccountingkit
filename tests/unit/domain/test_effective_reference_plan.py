"""Domain tests for provider-resolved effective plans and overlays."""

from __future__ import annotations

import pytest

from pyaccountingkit.domain.references.effective_plan import (
    EffectiveAccountOrigin,
    EffectiveAccountPlan,
    EffectiveReferenceAccount,
    RegulatorySourceReference,
)
from pyaccountingkit.domain.references.overlays import ReferenceOverlay, ReferenceOverlayEntry


def _source() -> RegulatorySourceReference:
    return RegulatorySourceReference(
        document_id="official-source",
        page_pdf=10,
        section="Art. 320-2",
        snippet="19 - Fonds dédiés",
        source_line_md=42,
    )


def test_effective_plan_rejects_duplicate_reference_codes() -> None:
    account = EffectiveReferenceAccount(
        account_id="account:fr-nonprofit:2026:19",
        ref_code="19",
        label="Fonds dédiés",
        origin=EffectiveAccountOrigin.EXTENSION_ADDITION,
        provenance_type="official_source",
        extension_source_ref=_source(),
    )
    with pytest.raises(ValueError, match="duplicate ref_code"):
        EffectiveAccountPlan(
            standard_id="fr-nonprofit",
            edition="2026",
            base_standard="fr-pcg:2026",
            accounts=(
                account,
                EffectiveReferenceAccount(
                    account_id="account:fr-nonprofit:2026:019",
                    ref_code="19",
                    label="Duplicate",
                    origin=EffectiveAccountOrigin.EXTENSION_ADDITION,
                    provenance_type="official_source",
                    extension_source_ref=_source(),
                ),
            ),
        )


def test_extension_addition_requires_source_and_no_base_account() -> None:
    with pytest.raises(ValueError, match="requires source and no base account"):
        EffectiveReferenceAccount(
            account_id="account:fr-nonprofit:2026:19",
            ref_code="19",
            label="Fonds dédiés",
            origin=EffectiveAccountOrigin.EXTENSION_ADDITION,
            provenance_type="official_source",
            base_account_id="account:fr-pcg:2026:19",
            extension_source_ref=_source(),
        )


def test_overlay_is_read_only_provenance_with_exact_codes() -> None:
    entry = ReferenceOverlayEntry(
        overlay_id="overlay:fr-nonprofit:2026:19",
        standard_id="fr-nonprofit",
        edition="2026",
        base_standard="fr-pcg:2026",
        ref_code="19",
        overlay_type="specific_addition",
        canonical_effect="replace_or_add",
        regulatory_status="official_extension",
        extension_label="Fonds dédiés",
        source_ref=_source(),
    )
    overlay = ReferenceOverlay(
        standard_id="fr-nonprofit",
        edition="2026",
        base_standard="fr-pcg:2026",
        entries=(entry,),
        extension_codes=("19",),
        statistics={"specific_addition": 1},
    )
    assert overlay.entry("19") == entry
    assert not hasattr(overlay, "apply")
