"""LOT-26 integration contract for MIG-13 retirement readiness evidence."""

from __future__ import annotations

import json
from pathlib import Path

from pyaccountingkit.integrations.cfa_fra import (
    LegacyRetirementEvidence,
    LegacyRetirementGate,
    MigrationRouting,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tests" / "consumer" / "cfa_fra" / "RETIREMENT_EVIDENCE.json"


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_retirement_manifest_requires_target_only_routing() -> None:
    payload = _manifest()

    assert payload["schema_version"] == "1"
    assert payload["routing_profile"] == "target_only"
    assert MigrationRouting.target_only().is_target_only() is True


def test_current_retirement_manifest_records_only_real_external_blockers() -> None:
    payload = _manifest()
    external = payload["external_evidence"]

    assert isinstance(external, dict)
    assert external["legacy_identities"]["green"] is False
    assert external["regulatory_authority"]["green"] is False
    assert tuple(payload["expected_blockers"]) == (
        "evidence:consumer-e2e",
        "evidence:legacy-identities",
        "evidence:regulatory-authority",
    )


def test_current_mig13_decision_stays_blocked_with_target_only_routing() -> None:
    decision = LegacyRetirementGate().evaluate(
        MigrationRouting.target_only(),
        LegacyRetirementEvidence(
            golden_parity_green=True,
            production_adapters_green=True,
            consumer_e2e_green=False,
            identities_traceable=False,
            regulatory_authority_replaced=False,
        ),
    )

    assert decision.ready is False
    assert decision.blockers == (
        "evidence:consumer-e2e",
        "evidence:legacy-identities",
        "evidence:regulatory-authority",
    )


def test_mig13_flips_ready_only_when_external_cutover_evidence_is_green() -> None:
    decision = LegacyRetirementGate().evaluate(
        MigrationRouting.target_only(),
        LegacyRetirementEvidence(
            golden_parity_green=True,
            production_adapters_green=True,
            consumer_e2e_green=True,
            identities_traceable=True,
            regulatory_authority_replaced=True,
        ),
    )

    assert decision.ready is True
    assert decision.blockers == ()
