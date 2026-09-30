"""LOT-26 tests for the live CFA FRA consumer E2E cutover artifact."""

from __future__ import annotations

import pytest

from pyaccountingkit.integrations.cfa_fra.cutover_artifact_schema import (
    CONSUMER_E2E_SCHEMA,
    ConsumerE2ECutoverArtifact,
    CutoverArtifactSchemaError,
)
from pyaccountingkit.integrations.cfa_fra.cutover_generation import (
    CutoverArtifactGenerationError,
    generate_consumer_e2e_artifact,
)

SCENARIOS = (
    "login",
    "organization_context",
    "fec_import",
    "journal",
    "ledger",
    "balance",
    "financial_statements",
    "controls",
    "closing",
    "exports",
)


def _scenarios() -> list[dict[str, object]]:
    return [
        {
            "scenario": scenario,
            "status": "PASS",
            "source": f"live:{scenario}",
            "evidence_checksum": "sha256:" + (str(index % 10) * 64),
        }
        for index, scenario in enumerate(SCENARIOS)
    ]


def _payload() -> dict[str, object]:
    return {
        "schema": CONSUMER_E2E_SCHEMA,
        "kind": "consumer_e2e_cutover",
        "consumer": "CFA FRA",
        "observed_at": "2026-09-30T16:00:00Z",
        "environment": "production",
        "producer": "cfa-fra-live-e2e",
        "routing_profile": "target_only",
        "scenarios": _scenarios(),
    }


def test_consumer_e2e_artifact_requires_all_ten_live_passes() -> None:
    artifact = ConsumerE2ECutoverArtifact.from_mapping(_payload())

    assert len(artifact.evidence) == 10
    assert tuple(item.scenario.value for item in artifact.evidence) == (
        "balance",
        "closing",
        "controls",
        "exports",
        "fec_import",
        "financial_statements",
        "journal",
        "ledger",
        "login",
        "organization_context",
    )


@pytest.mark.parametrize("missing", ["login", "controls", "closing"])
def test_consumer_e2e_artifact_rejects_missing_scenario(missing: str) -> None:
    payload = _payload()
    payload["scenarios"] = [
        item for item in _scenarios() if item["scenario"] != missing
    ]

    with pytest.raises(CutoverArtifactSchemaError, match="exactly one PASS"):
        ConsumerE2ECutoverArtifact.from_mapping(payload)


def test_consumer_e2e_artifact_rejects_duplicate_scenario() -> None:
    payload = _payload()
    scenarios = _scenarios()
    payload["scenarios"] = [*scenarios, dict(scenarios[0])]

    with pytest.raises(CutoverArtifactSchemaError, match="duplicate consumer evidence"):
        ConsumerE2ECutoverArtifact.from_mapping(payload)


def test_consumer_e2e_artifact_rejects_non_passing_scenario() -> None:
    payload = _payload()
    scenarios = _scenarios()
    scenarios[0]["status"] = "BLOCKED"
    payload["scenarios"] = scenarios

    with pytest.raises(CutoverArtifactSchemaError, match="must be PASS"):
        ConsumerE2ECutoverArtifact.from_mapping(payload)


def test_consumer_e2e_artifact_rejects_noncanonical_checksum() -> None:
    payload = _payload()
    scenarios = _scenarios()
    scenarios[0]["evidence_checksum"] = "sha256:ABC"
    payload["scenarios"] = scenarios

    with pytest.raises(CutoverArtifactSchemaError, match="64 lowercase hex"):
        ConsumerE2ECutoverArtifact.from_mapping(payload)


def test_consumer_e2e_generation_self_validates_schema() -> None:
    generated = generate_consumer_e2e_artifact(
        consumer="CFA FRA",
        observed_at="2026-09-30T16:00:00Z",
        environment="production",
        producer="cfa-fra-live-e2e",
        scenarios=_scenarios(),
    )

    assert generated.key == "consumer_e2e"
    assert generated.payload["schema"] == CONSUMER_E2E_SCHEMA


def test_consumer_e2e_generation_rejects_blocked_input() -> None:
    scenarios = _scenarios()
    scenarios[0]["status"] = "BLOCKED"

    with pytest.raises(CutoverArtifactGenerationError):
        generate_consumer_e2e_artifact(
            consumer="CFA FRA",
            observed_at="2026-09-30T16:00:00Z",
            environment="production",
            producer="cfa-fra-live-e2e",
            scenarios=scenarios,
        )
