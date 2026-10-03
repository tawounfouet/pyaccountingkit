#!/usr/bin/env python3
"""Run PyAccountingKit release qualification gates with explicit controls."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pyaccountingkit.integrations.cfa_fra import (
    LiveConsumerBindingError,
    parse_live_consumer_binding_state,
)

ROOT = Path(__file__).resolve().parents[1]

_RC_TEST_SUITES: tuple[tuple[str, str], ...] = (
    ("tests/integration", "Integration test suite"),
    ("tests/golden", "Golden test suite"),
    ("tests/replay", "Replay test suite"),
    ("tests/concurrency", "Concurrency test suite"),
)

_VERSIONED_RC_EVIDENCE: dict[str, tuple[str, ...]] = {
    "0.4.0rc1": (
        "tests/integration/test_0_4_subledger_financial_analysis_pipeline.py",
        "tests/property/test_subledger_settlement_properties.py",
        "tests/concurrency/test_subledger_allocation_concurrency.py",
        "tests/golden/test_subledger_settlement_golden.py",
        "tests/golden/test_financial_analysis_golden.py",
        "tests/replay/test_0_4_release_pipeline_replay.py",
        "tests/contract/test_corporate_finance_boundary.py",
        "tests/integration/test_0_3_import_reporting_pipeline.py",
        "tests/replay/test_0_3_release_pipeline_replay.py",
    ),
    "0.5.0rc1": (
        "tests/integration/test_0_5_public_production_adapter_pipeline.py",
        "tests/contract/test_public_api_boundary.py",
        "tests/contract/test_extension_api_contracts.py",
        "tests/integration/test_django_postgresql_adapter.py",
        "tests/concurrency/test_django_postgresql_concurrency.py",
        "tests/integration/test_sqlalchemy_postgresql_adapter.py",
        "tests/concurrency/test_sqlalchemy_postgresql_concurrency.py",
        "tests/integration/test_0_4_subledger_financial_analysis_pipeline.py",
        "tests/replay/test_0_4_release_pipeline_replay.py",
        "tests/contract/test_corporate_finance_boundary.py",
        "tests/integration/test_0_3_import_reporting_pipeline.py",
        "tests/replay/test_0_3_release_pipeline_replay.py",
    ),
    "0.6.0rc1": (
        "tests/integration/test_0_6_cfa_fra_consumer_conversion.py",
        "tests/integration/test_0_6_cfa_fra_live_cutover_evidence.py",
        "tests/integration/test_0_6_cfa_fra_retirement_readiness.py",
        "tests/integration/test_0_6_cfa_fra_retirement_plan.py",
        "tests/integration/test_0_6_cfa_fra_retirement_execution.py",
        "tests/integration/test_0_6_cfa_fra_retirement_completion.py",
        "tests/golden/cfa_fra/BASELINE.json",
        "tests/consumer/cfa_fra/RETIREMENT_EVIDENCE.json",
        "tests/consumer/cfa_fra/CONSUMER_BINDING.json",
        "tests/consumer/cfa_fra/CONSUMER_BOOTSTRAP.json",
        "tests/consumer/cfa_fra/live_evidence/consumer-e2e.json",
        "tests/consumer/cfa_fra/live_evidence/legacy-identities.json",
        "tests/consumer/cfa_fra/live_evidence/regulatory-authority.json",
        "tests/consumer/cfa_fra/live_evidence/legacy-retirement-plan.json",
        "tests/consumer/cfa_fra/live_evidence/legacy-retirement-execution.json",
        "tests/consumer/cfa_fra/live_evidence/legacy-retirement-completion.json",
    ),
    "0.7.0rc1": (
        "tests/integration/test_0_7_regulatory_compatibility_matrix.py",
        "tests/golden/regulatory/test_lot27_capability_profiles.py",
        "tests/golden/regulatory/test_nonprofit_effective_plan.py",
        "tests/golden/regulatory/test_ebnl_structure_provider.py",
        "tests/golden/regulatory/test_ohada_standard_relations.py",
        "tests/golden/regulatory/test_reporting_structure_provider.py",
        "REGULATORY_COMPATIBILITY_MATRIX.json",
        "SNAPSHOT_SCHEMA_MANIFEST.json",
    ),
}


@dataclass(frozen=True)
class GateResult:
    """Result of one qualification gate."""

    name: str
    duration_seconds: float


class QualificationError(RuntimeError):
    """Raised when a release qualification gate fails."""


def project_version() -> str:
    """Return the canonical version from pyproject.toml."""
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def run_command(command: list[str], *, label: str) -> GateResult:
    """Run a command as a named qualification gate."""
    started = time.monotonic()
    print(f"\n== {label} ==")
    print("+", " ".join(command))
    completed = subprocess.run(command, cwd=ROOT, check=False)
    duration = time.monotonic() - started
    if completed.returncode != 0:
        if completed.returncode == 5 and "pytest" in command:
            raise QualificationError(f"{label} failed: pytest collected no tests (exit code 5)")
        raise QualificationError(f"{label} failed with exit code {completed.returncode}")
    print(f"{label}: PASS ({duration:.2f}s)")
    return GateResult(label, duration)


def validate_manifests() -> GateResult:
    """Validate root manifest schema shape and version coherence."""
    started = time.monotonic()
    version = project_version()
    specifications: tuple[tuple[str, str, type[dict] | type[list]], ...] = (
        ("PUBLIC_API_MANIFEST.json", "public_api", dict),
        ("PUBLIC_ERROR_CODES.json", "error_codes", dict),
        ("ADAPTER_CONTRACT_MANIFEST.json", "adapter_contracts", dict),
        ("REGULATORY_COMPATIBILITY_MATRIX.json", "regulatory_frameworks", list),
        ("SNAPSHOT_SCHEMA_MANIFEST.json", "snapshots", dict),
    )

    for filename, payload_key, payload_type in specifications:
        path = ROOT / filename
        if not path.is_file():
            raise QualificationError(f"manifest missing: {filename}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise QualificationError(f"invalid JSON in {filename}: {exc}") from exc
        if data.get("version") != version:
            raise QualificationError(
                f"{filename} version {data.get('version')} does not match {version}"
            )
        payload = data.get(payload_key)
        if not isinstance(payload, payload_type):
            expected = payload_type.__name__
            raise QualificationError(f"{filename}.{payload_key} must be {expected}")
        if version == "0.0.1" and payload:
            raise QualificationError(
                f"bootstrap manifest {filename}.{payload_key} must remain empty"
            )

    duration = time.monotonic() - started
    print("\n== Manifest coherence ==")
    print(f"Manifest coherence: PASS ({duration:.2f}s)")
    return GateResult("Manifest coherence", duration)


def run_callable(name: str, function: Callable[[], GateResult]) -> GateResult:
    """Run a Python gate and normalize unexpected failures."""
    try:
        return function()
    except QualificationError:
        raise
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        raise QualificationError(f"{name} failed unexpectedly: {exc}") from exc


def _pytest_gate(paths: list[str], *, label: str) -> GateResult:
    return run_command(
        [sys.executable, "-m", "pytest", *paths, "-v", "--tb=short"],
        label=label,
    )


def _has_tests(relative_path: str) -> bool:
    path = ROOT / relative_path
    return path.is_dir() and any(path.rglob("test_*.py"))


def validate_release_candidate_contract(
    *,
    skip_tests: bool,
    skip_package: bool,
) -> None:
    """Fail closed when a release candidate omits mandatory qualification evidence."""
    if skip_tests:
        raise QualificationError("release-candidate qualification cannot skip tests")
    if skip_package:
        raise QualificationError("release-candidate qualification cannot skip package verification")
    missing = [path for path, _ in _RC_TEST_SUITES if not _has_tests(path)]
    if missing:
        joined = ", ".join(missing)
        raise QualificationError(
            f"release-candidate qualification requires non-empty test suites: {joined}"
        )

    version = project_version()
    if re.search(r"rc\\d+$", version) and version not in _VERSIONED_RC_EVIDENCE:
        raise QualificationError(
            f"release-candidate {version} has no registered evidence contract"
        )
    required_evidence = _VERSIONED_RC_EVIDENCE.get(version, ())
    missing_evidence = [
        relative_path for relative_path in required_evidence if not (ROOT / relative_path).is_file()
    ]
    if missing_evidence:
        joined = ", ".join(missing_evidence)
        raise QualificationError(
            f"release-candidate {version} is missing required evidence: {joined}"
        )

    if version == "0.6.0rc1":
        _validate_cfa_fra_0_6_rc1_completion()


def _validate_cfa_fra_0_6_rc1_completion() -> None:
    """Require a semantically complete canonical L26-C proof for 0.6.0rc1."""
    completion_path = (
        ROOT
        / "tests"
        / "consumer"
        / "cfa_fra"
        / "live_evidence"
        / "legacy-retirement-completion.json"
    )
    inventory_path = ROOT / "tests" / "consumer" / "cfa_fra" / "LEGACY_RETIREMENT_INVENTORY.json"
    binding_path = ROOT / "tests" / "consumer" / "cfa_fra" / "CONSUMER_BINDING.json"
    bootstrap_path = ROOT / "tests" / "consumer" / "cfa_fra" / "CONSUMER_BOOTSTRAP.json"

    try:
        completion = json.loads(completion_path.read_text(encoding="utf-8"))
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        binding_state = json.loads(binding_path.read_text(encoding="utf-8"))
        bootstrap_contract = json.loads(bootstrap_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise QualificationError(f"invalid CFA FRA RC1 JSON evidence: {exc}") from exc

    if not isinstance(completion, dict):
        raise QualificationError("CFA FRA RC1 completion evidence must be a JSON object")
    if not isinstance(inventory, dict):
        raise QualificationError("CFA FRA retirement inventory must be a JSON object")
    if not isinstance(bootstrap_contract, dict):
        raise QualificationError("CFA FRA consumer bootstrap contract must be a JSON object")
    if bootstrap_contract.get("schema_version") != "1":
        raise QualificationError("CFA FRA consumer bootstrap contract requires schema_version='1'")
    bootstrap_source = bootstrap_contract.get("source")
    bootstrap_target = bootstrap_contract.get("target")
    bootstrap_safety = bootstrap_contract.get("safety")
    if not isinstance(bootstrap_source, dict) or not isinstance(bootstrap_target, dict):
        raise QualificationError("CFA FRA consumer bootstrap source/target contract is invalid")
    if not isinstance(bootstrap_safety, dict):
        raise QualificationError("CFA FRA consumer bootstrap safety contract is invalid")
    if bootstrap_source.get("oracle_tree_sha") != "07d4880534d2e2239e19fd4ef4139de70b56773a":
        raise QualificationError("CFA FRA consumer bootstrap must target the frozen oracle tree")
    if bootstrap_source.get("oracle_manifest_version") != "0.8.0":
        raise QualificationError("CFA FRA consumer bootstrap must target oracle manifest 0.8.0")
    framework_requirement = bootstrap_target.get("framework_requirement")
    if framework_requirement != "pyaccountingkit>=0.6.0b26,<0.7":
        raise QualificationError("CFA FRA consumer bootstrap framework requirement drifted")
    if bootstrap_target.get("binding_after_bootstrap") != "UNBOUND_UNTIL_PUBLISHED":
        raise QualificationError("CFA FRA consumer bootstrap may not auto-bind a repository")
    if bootstrap_target.get("cutover_state_after_bootstrap") != "NOT_STARTED":
        raise QualificationError("CFA FRA consumer bootstrap may not auto-promote cutover state")
    for field in (
        "source_snapshot_mutation_allowed",
        "automatic_github_publication",
        "automatic_consumer_binding",
        "automatic_cutover_evidence_promotion",
    ):
        if bootstrap_safety.get(field) is not False:
            raise QualificationError(f"CFA FRA consumer bootstrap safety requires {field}=false")

    if not isinstance(binding_state, dict):
        raise QualificationError("CFA FRA consumer binding must be a JSON object")
    try:
        consumer_binding_state = parse_live_consumer_binding_state(binding_state)
    except LiveConsumerBindingError as exc:
        raise QualificationError(f"invalid CFA FRA consumer binding: {exc}") from exc
    if consumer_binding_state.binding is None:
        raise QualificationError("CFA FRA 0.6.0rc1 requires a BOUND live consumer repository")
    live_binding = consumer_binding_state.binding
    if live_binding.environment != "production":
        raise QualificationError("CFA FRA 0.6.0rc1 consumer binding must target production")

    required_values = {
        "schema_version": "1",
        "status": "COMPLETE",
        "ready_for_0_6_rc1": True,
        "routing_target_only": True,
    }
    for key, expected in required_values.items():
        if completion.get(key) != expected:
            raise QualificationError(f"CFA FRA RC1 completion evidence requires {key}={expected!r}")

    raw_oracle = inventory.get("oracle")
    if not isinstance(raw_oracle, dict):
        raise QualificationError("CFA FRA retirement inventory oracle is missing")
    oracle_tree_sha = raw_oracle.get("tree_sha")
    if not isinstance(oracle_tree_sha, str) or not oracle_tree_sha:
        raise QualificationError("CFA FRA retirement inventory oracle tree_sha is missing")
    if completion.get("oracle_tree_sha") != oracle_tree_sha:
        raise QualificationError("CFA FRA RC1 completion oracle tree does not match inventory")

    consumer_revision = completion.get("consumer_revision")
    if not isinstance(consumer_revision, str) or not consumer_revision.strip():
        raise QualificationError("CFA FRA RC1 completion requires a live consumer revision")
    if consumer_revision == oracle_tree_sha:
        raise QualificationError("CFA FRA RC1 completion may not target the frozen oracle revision")

    binding_revision = live_binding.revision_sha
    if binding_revision != consumer_revision:
        raise QualificationError(
            "CFA FRA consumer binding revision must match retirement completion revision"
        )

    sha256_pattern = re.compile(r"^[0-9a-f]{64}$")
    for key in (
        "plan_sha256",
        "execution_receipt_sha256",
        "inventory_sha256",
        "readiness_sha256",
        "completion_sha256",
    ):
        value = completion.get(key)
        if not isinstance(value, str) or sha256_pattern.fullmatch(value) is None:
            raise QualificationError(
                f"CFA FRA RC1 completion requires lowercase SHA-256 field {key}"
            )

    expected_counts = {
        "RETIRE_DUPLICATE_ENGINE": 10,
        "VERIFY_CONSUMER_REWIRED": 8,
        "PRESERVE_OR_MIGRATE_PERSISTENCE": 7,
        "KEEP_CONSUMER_CONCERN": 8,
        "PRESERVE_FROZEN_ORACLE": 6,
    }
    if completion.get("action_counts") != expected_counts:
        raise QualificationError(
            "CFA FRA RC1 completion action counts do not match the reviewed retirement inventory"
        )


def qualify(
    *,
    skip_tests: bool,
    skip_package: bool,
    full: bool,
    release_candidate: bool = False,
) -> list[GateResult]:
    """Execute the deterministic qualification sequence."""
    if release_candidate:
        validate_release_candidate_contract(
            skip_tests=skip_tests,
            skip_package=skip_package,
        )

    results: list[GateResult] = []
    results.append(run_command(["bash", "scripts/check_hygiene.sh"], label="Repository hygiene"))
    results.append(
        run_command(
            [sys.executable, "scripts/validate_architecture.py"],
            label="Architecture safety",
        )
    )
    results.append(run_callable("Manifest coherence", validate_manifests))
    for script, label in (
        ("scripts/generate_public_api_manifest.py", "Public API manifest generation"),
        ("scripts/generate_error_codes_manifest.py", "Public error manifest generation"),
        ("scripts/generate_adapter_contract_manifest.py", "Adapter contract manifest generation"),
        (
            "scripts/generate_regulatory_compatibility_matrix.py",
            "Regulatory compatibility matrix generation",
        ),
        (
            "scripts/generate_snapshot_schema_manifest.py",
            "Snapshot schema manifest generation",
        ),
    ):
        results.append(
            run_command(
                [sys.executable, script, "--check"],
                label=label,
            )
        )
    results.append(
        run_command(
            [sys.executable, "scripts/validate_ci.py"],
            label="CI workflow contract",
        )
    )
    results.append(
        run_command(
            [sys.executable, "scripts/validate_documentation.py"],
            label="Documentation contract",
        )
    )
    results.append(
        run_command(
            [sys.executable, "scripts/validate_regulatory_gate.py"],
            label="Regulatory gate",
        )
    )
    results.append(
        run_command(
            [sys.executable, "scripts/validate_resource_governance.py"],
            label="Resource governance",
        )
    )
    results.append(
        run_command(
            [sys.executable, "scripts/validate_lot00_remediation_status.py"],
            label="LOT-00 remediation status",
        )
    )
    results.append(
        run_command(
            [sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"],
            label="Ruff lint",
        )
    )
    results.append(
        run_command(
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                "src",
                "tests",
                "scripts",
            ],
            label="Ruff format",
        )
    )
    results.append(
        run_command(
            [sys.executable, "-m", "mypy", "src/"],
            label="Strict type checking",
        )
    )

    if not skip_package:
        results.append(
            run_command(
                [sys.executable, "scripts/verify_package.py"],
                label="Package verification",
            )
        )

    if not skip_tests:
        results.append(
            _pytest_gate(
                ["tests/unit", "tests/property", "tests/contract"],
                label="Core deterministic test suite",
            )
        )
        if full or release_candidate:
            for path, label in _RC_TEST_SUITES:
                if _has_tests(path):
                    results.append(_pytest_gate([path], label=label))
                elif release_candidate:
                    raise QualificationError(
                        f"{label} is mandatory for a release candidate but {path} is empty"
                    )
                else:
                    print(f"\n== {label} ==")
                    print(f"{label}: NOT APPLICABLE (no tests collected in {path})")

    return results


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip pytest for focused diagnostics; this never qualifies a full release.",
    )
    parser.add_argument(
        "--skip-package",
        action="store_true",
        help="Skip wheel/sdist qualification for focused local diagnostics.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Add integration/golden/replay/concurrency suites when present.",
    )
    parser.add_argument(
        "--release-candidate",
        action="store_true",
        help=(
            "Require package verification plus non-empty integration, golden, replay and "
            "concurrency suites; no qualification evidence may be skipped."
        ),
    )
    args = parser.parse_args()

    try:
        results = qualify(
            skip_tests=args.skip_tests,
            skip_package=args.skip_package,
            full=args.full,
            release_candidate=args.release_candidate,
        )
    except QualificationError as exc:
        print(f"\nRelease qualification: FAIL: {exc}", file=sys.stderr)
        return 1

    total = sum(result.duration_seconds for result in results)
    if args.release_candidate:
        mode = "RELEASE_CANDIDATE"
    elif args.full:
        mode = "FULL"
    else:
        mode = "CORE"
    print("\nRelease qualification: PASS")
    print(f"Project version: {project_version()}")
    print(f"Mode: {mode}")
    print(f"Gates passed: {len(results)}")
    print(f"Aggregate gate time: {total:.2f}s")
    if args.skip_tests:
        print("Tests: SKIPPED explicitly; full release qualification is not satisfied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
