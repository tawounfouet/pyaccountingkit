"""Contract tests for the executable CFA FRA consumer evidence matrix."""

from __future__ import annotations

import json
from pathlib import Path

from pyaccountingkit.integrations.cfa_fra import (
    ConsumerQualification,
    ConsumerScenario,
    ConsumerScenarioEvidence,
    ConsumerScenarioStatus,
)

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "tests" / "consumer" / "cfa_fra" / "CONSUMER_EVIDENCE_MATRIX.json"


def test_consumer_evidence_matrix_covers_gate_consumer_exactly_once() -> None:
    payload = json.loads(MATRIX.read_text(encoding="utf-8"))
    scenarios = [item["scenario"] for item in payload["scenarios"]]

    assert len(scenarios) == len(set(scenarios))
    assert set(scenarios) == {item.value for item in ConsumerScenario}


def test_sprint7_known_gaps_remain_explicit_and_retirement_blocking() -> None:
    payload = json.loads(MATRIX.read_text(encoding="utf-8"))
    evidence = []
    for item in payload["scenarios"]:
        scenario = ConsumerScenario(item["scenario"])
        if item["mode"] == "blocked":
            evidence.append(
                ConsumerScenarioEvidence(
                    scenario=scenario,
                    status=ConsumerScenarioStatus.BLOCKED,
                    source="matrix-contract",
                    detail=item["reason"],
                )
            )
        else:
            evidence.append(
                ConsumerScenarioEvidence(
                    scenario=scenario,
                    status=ConsumerScenarioStatus.PASS,
                    source="matrix-contract",
                )
            )

    decision = ConsumerQualification(tuple(evidence)).evaluate()

    assert decision.green is False
    assert decision.failed == ()
    assert decision.missing == ()
    assert decision.blocked == (
        ConsumerScenario.CLOSING,
        ConsumerScenario.CONTROLS,
        ConsumerScenario.LOGIN,
    )


def test_every_pytest_evidence_target_exists_in_frozen_resource() -> None:
    payload = json.loads(MATRIX.read_text(encoding="utf-8"))
    resource = ROOT / payload["oracle"]["resource_path"]

    targets = [
        target
        for item in payload["scenarios"]
        if item["mode"] == "pytest"
        for target in item["pytest_targets"]
    ]

    assert targets
    assert all((resource / target).is_file() for target in targets)
