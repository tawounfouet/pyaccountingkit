"""Golden qualification for France Non-Profit 2026 effective-plan consumption."""

from __future__ import annotations

from pathlib import Path

from pyaccountingkit import AccountingApplication
from pyaccountingkit.adapters.regulatory.nonprofit import NonProfitFilesystemReferenceAdapter
from pyaccountingkit.application.references.effective_plan_service import (
    EffectivePlanReferenceService,
)
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.domain.references.capabilities import ReferenceCapability
from pyaccountingkit.domain.references.effective_plan import EffectiveAccountOrigin

STRUCTURED = (
    Path(__file__).resolve().parents[3]
    / "resources"
    / "regulatory-accounting-data-framework"
    / "datasets"
    / "structured"
)


def _provider() -> NonProfitFilesystemReferenceAdapter:
    return NonProfitFilesystemReferenceAdapter(STRUCTURED, clock=FrozenClock())


def test_nonprofit_effective_plan_is_consumed_directly_with_901_accounts() -> None:
    plan = _provider().get_effective_plan("fr-nonprofit", "2026")
    assert plan.standard_id == "fr-nonprofit"
    assert plan.edition == "2026"
    assert plan.base_standard == "fr-pcg:2026"
    assert len(plan.accounts) == 901
    assert dict(plan.statistics) == {
        "effective_accounts_or_groups": 901,
        "extension_additions": 73,
        "extension_overrides": 43,
        "inherited": 785,
    }


def test_nonprofit_effective_plan_preserves_origin_and_source_provenance() -> None:
    plan = _provider().get_effective_plan("fr-nonprofit", "2026")

    inherited = plan.account("101")
    assert inherited is not None
    assert inherited.origin is EffectiveAccountOrigin.INHERITED_FROM_BASE_STANDARD
    assert inherited.base_account_id == "account:fr-pcg:2026:101"
    assert inherited.extension_source_ref is None

    addition = plan.account("19")
    assert addition is not None
    assert addition.origin is EffectiveAccountOrigin.EXTENSION_ADDITION
    assert addition.base_account_id is None
    assert addition.extension_source_ref is not None
    assert addition.extension_source_ref.document_id == "fr-nonprofit-recueil-2026-md"
    assert addition.extension_source_ref.section == "Art. 320-2"

    override = plan.account("10")
    assert override is not None
    assert override.origin is EffectiveAccountOrigin.EXTENSION_OVERRIDE
    assert override.label == "Fonds propres et réserves"
    assert override.base_account_id == "account:fr-pcg:2026:10"


def test_nonprofit_overlay_is_audit_only_and_preserves_116_source_deltas() -> None:
    overlay = _provider().get_overlay("fr-nonprofit", "2026")
    assert len(overlay.entries) == 116
    assert len(overlay.extension_codes) == 116
    assert dict(overlay.statistics) == {
        "label_or_semantic_override": 26,
        "same_semantics_label": 17,
        "specific_addition": 73,
    }
    addition = overlay.entry("19")
    assert addition is not None
    assert addition.source_ref.document_id == "fr-nonprofit-recueil-2026-md"
    assert addition.canonical_effect == "replace_or_add"
    assert not hasattr(overlay, "apply")


def test_nonprofit_effective_plan_snapshot_is_deterministic_and_replayable() -> None:
    provider = _provider()
    first = provider.get_effective_plan_snapshot("fr-nonprofit", "2026", "2026.1")
    second = provider.get_effective_plan_snapshot("fr-nonprofit", "2026", "2026.1")
    assert first.verify()
    assert second.verify()
    assert first.checksum == second.checksum
    assert first.replay().accounts == provider.get_effective_plan("fr-nonprofit", "2026").accounts


def test_nonprofit_provider_declares_only_real_capabilities() -> None:
    capabilities = _provider().capabilities("fr-nonprofit", "2026")
    assert capabilities.supports(ReferenceCapability.EFFECTIVE_PLAN)
    assert capabilities.supports(ReferenceCapability.OVERLAYS)
    assert capabilities.supports(ReferenceCapability.SNAPSHOTS)
    assert not capabilities.supports(ReferenceCapability.HIERARCHY)


def test_public_references_facade_delegates_effective_plan_and_snapshot() -> None:
    provider = _provider()
    application = AccountingApplication(references=EffectivePlanReferenceService(provider))

    plan = application.references.get_effective_plan(
        standard_id="fr-nonprofit",
        edition="2026",
    )
    snapshot = application.references.create_snapshot(
        standard_id="fr-nonprofit",
        edition="2026",
        version="2026.1",
    )

    assert plan.account("19") is not None
    assert snapshot.verify()
    assert snapshot.standard_id == "fr-nonprofit"
