#!/usr/bin/env python3
"""Execute the bundled CFA FRA Sprint-7 consumer evidence matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from pyaccountingkit.integrations.cfa_fra import (
    ConsumerQualification,
    ConsumerScenario,
    ConsumerScenarioEvidence,
    ConsumerScenarioStatus,
)

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "tests" / "consumer" / "cfa_fra" / "CONSUMER_EVIDENCE_MATRIX.json"


def _load_matrix() -> Mapping[str, object]:
    return cast(Mapping[str, object], json.loads(MATRIX_PATH.read_text(encoding="utf-8")))


def _required_str(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key!r} must be a non-empty string")
    return value


def _target_checksum(resource: Path, targets: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for target in sorted(targets):
        path = resource / target
        if not path.is_file():
            raise FileNotFoundError(f"consumer evidence target missing: {target}")
        digest.update(target.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _run_pytest(resource: Path, targets: Sequence[str]) -> tuple[bool, str]:
    command = [sys.executable, "-m", "pytest", *targets, "-q", "--tb=short"]
    print("+", " ".join(command), flush=True)
    result = subprocess.run(
        command,
        cwd=resource,
        check=False,
        text=True,
    )
    if result.returncode == 0:
        return True, "bundled CFA FRA pytest evidence passed"
    return False, f"bundled CFA FRA pytest exited with {result.returncode}"


def build_evidence() -> tuple[ConsumerScenarioEvidence, ...]:
    matrix = _load_matrix()
    oracle = cast(Mapping[str, object], matrix["oracle"])
    resource = ROOT / _required_str(oracle, "resource_path")
    tree_sha = _required_str(oracle, "tree_sha")

    raw_scenarios = matrix.get("scenarios")
    if not isinstance(raw_scenarios, list):
        raise ValueError("consumer evidence matrix must contain a scenario list")

    cached_runs: dict[tuple[str, ...], tuple[bool, str]] = {}
    evidence: list[ConsumerScenarioEvidence] = []

    for raw in raw_scenarios:
        if not isinstance(raw, dict):
            raise ValueError("consumer scenario entries must be JSON objects")
        item = cast(Mapping[str, object], raw)
        scenario = ConsumerScenario(_required_str(item, "scenario"))
        mode = _required_str(item, "mode")

        if mode == "blocked":
            reason = _required_str(item, "reason")
            evidence.append(
                ConsumerScenarioEvidence(
                    scenario=scenario,
                    status=ConsumerScenarioStatus.BLOCKED,
                    source=f"cfa-fra-sprint7:{tree_sha}",
                    detail=reason,
                )
            )
            continue

        if mode != "pytest":
            raise ValueError(f"unsupported consumer evidence mode {mode!r}")

        raw_targets = item.get("pytest_targets")
        if not isinstance(raw_targets, list) or not raw_targets:
            raise ValueError(f"{scenario.value}: pytest mode requires targets")
        targets = tuple(str(target) for target in raw_targets)
        result = cached_runs.get(targets)
        if result is None:
            result = _run_pytest(resource, targets)
            cached_runs[targets] = result
        passed, detail = result

        evidence.append(
            ConsumerScenarioEvidence(
                scenario=scenario,
                status=(
                    ConsumerScenarioStatus.PASS
                    if passed
                    else ConsumerScenarioStatus.FAIL
                ),
                source=f"cfa-fra-sprint7:{','.join(targets)}",
                detail=None if passed else detail,
                evidence_checksum=_target_checksum(resource, targets),
            )
        )

    return tuple(evidence)


def _report(evidence: tuple[ConsumerScenarioEvidence, ...]) -> dict[str, object]:
    qualification = ConsumerQualification(evidence)
    decision = qualification.evaluate()
    return {
        "consumer_e2e_green": decision.green,
        "blockers": list(decision.blockers),
        "passed": [item.value for item in decision.passed],
        "failed": [item.value for item in decision.failed],
        "blocked": [item.value for item in decision.blocked],
        "missing": [item.value for item in decision.missing],
        "evidence": [
            {
                "scenario": item.scenario.value,
                "status": item.status.value,
                "source": item.source,
                "detail": item.detail,
                "evidence_checksum": item.evidence_checksum,
            }
            for item in qualification.evidence()
        ],
    }


def qualify(output: Path | None = None) -> int:
    evidence = build_evidence()
    report = _report(evidence)

    expected_blocked = ["closing", "controls", "login"]
    if report["failed"] or report["missing"]:
        print(json.dumps(report, indent=2, sort_keys=True), file=sys.stderr)
        return 1
    if report["blocked"] != expected_blocked:
        print(
            "CFA FRA consumer evidence gap set changed; review the cutover contract.",
            file=sys.stderr,
        )
        print(json.dumps(report, indent=2, sort_keys=True), file=sys.stderr)
        return 1
    if report["consumer_e2e_green"] is not False:
        print("consumer E2E must remain false while known Sprint-7 gaps exist", file=sys.stderr)
        return 1

    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    print("CFA FRA consumer evidence: QUALIFIED WITH EXPLICIT BLOCKERS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    return qualify(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
