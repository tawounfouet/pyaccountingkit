#!/usr/bin/env python3
"""Run PyAccountingKit release qualification gates with explicit controls."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

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
    required_evidence = _VERSIONED_RC_EVIDENCE.get(version, ())
    missing_evidence = [
        relative_path
        for relative_path in required_evidence
        if not (ROOT / relative_path).is_file()
    ]
    if missing_evidence:
        joined = ", ".join(missing_evidence)
        raise QualificationError(
            f"release-candidate {version} is missing required evidence: {joined}"
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
    results.append(
        run_command(
            [sys.executable, "scripts/validate_ci.py"],
            label="CI workflow contract",
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
