#!/usr/bin/env python3
"""Run PyAccountingKit release qualification gates with explicit skip controls."""

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


def qualify(*, skip_tests: bool, skip_package: bool) -> list[GateResult]:
    """Execute the deterministic release qualification sequence."""
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
            run_command(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/unit",
                    "tests/property",
                    "tests/contract",
                    "-v",
                    "--tb=short",
                ],
                label="Bootstrap test suite",
            )
        )

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
    args = parser.parse_args()

    try:
        results = qualify(skip_tests=args.skip_tests, skip_package=args.skip_package)
    except QualificationError as exc:
        print(f"\nRelease qualification: FAIL: {exc}", file=sys.stderr)
        return 1

    total = sum(result.duration_seconds for result in results)
    print("\nRelease qualification: PASS")
    print(f"Project version: {project_version()}")
    print(f"Gates passed: {len(results)}")
    print(f"Aggregate gate time: {total:.2f}s")
    if args.skip_tests:
        print("Tests: SKIPPED explicitly; full release qualification is not satisfied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
