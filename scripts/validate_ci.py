#!/usr/bin/env python3
"""Validate canonical CI and Security workflow contracts for PyAccountingKit."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
SECURITY_WORKFLOW = ROOT / ".github" / "workflows" / "security.yml"
TEST_COMMAND = (
    "python -m pytest tests/unit tests/property tests/contract tests/integration "
    "tests/golden tests/replay tests/concurrency -v --tb=short"
)


def _missing_snippets(text: str, snippets: tuple[str, ...], *, label: str) -> list[str]:
    return [
        f"{label}: missing required workflow contract: {snippet}"
        for snippet in snippets
        if snippet not in text
    ]


def validate_ci_text(text: str) -> list[str]:
    """Return contract violations for the canonical CI workflow text."""
    violations = _missing_snippets(
        text,
        (
            "permissions:\n  contents: read",
            "concurrency:",
            "cancel-in-progress: true",
            "quality:\n",
            "test:\n",
            "package:\n",
            "postgresql:\n",
            "sqlalchemy-postgresql:\n",
            "release-qualification:\n",
            "ci-gate:\n",
            "fail-fast: false",
            'python-version: ["3.11", "3.12", "3.13"]',
            "python scripts/qualify_release.py --skip-tests --skip-package",
            "python scripts/verify_package.py",
            TEST_COMMAND,
            "image: postgres:16",
            "python -m django migrate --noinput",
            "python -m django makemigrations pyaccountingkit_django --check --dry-run",
            "tests/integration/test_django_postgresql_adapter.py",
            "tests/concurrency/test_django_postgresql_concurrency.py",
            'PYAK_SQLALCHEMY_POSTGRES_TEST: "1"',
            "tests/integration/test_sqlalchemy_postgresql_adapter.py",
            "tests/concurrency/test_sqlalchemy_postgresql_concurrency.py",
            "python scripts/check_sqlalchemy_metadata.py",
            "python scripts/qualify_release.py --release-candidate",
            "startsWith(github.head_ref, 'release/')",
            (
                "needs: [quality, test, package, postgresql, sqlalchemy-postgresql, "
                "release-qualification]"
            ),
            "if: ${{ always() }}",
            "QUALITY_RESULT: ${{ needs.quality.result }}",
            "TEST_RESULT: ${{ needs.test.result }}",
            "PACKAGE_RESULT: ${{ needs.package.result }}",
            "POSTGRESQL_RESULT: ${{ needs.postgresql.result }}",
            "SQLALCHEMY_POSTGRESQL_RESULT: ${{ needs.sqlalchemy-postgresql.result }}",
            "RELEASE_QUALIFICATION_RESULT: ${{ needs.release-qualification.result }}",
        ),
        label="CI",
    )

    if text.count("actions/checkout@v7") != 6:
        violations.append("CI: expected exactly six actions/checkout@v7 uses")
    if text.count("actions/setup-python@v7") != 6:
        violations.append("CI: expected exactly six actions/setup-python@v7 uses")
    if text.count("cache: pip") != 6:
        violations.append("CI: every Python execution job must enable pip cache")
    if text.count("cache-dependency-path: pyproject.toml") != 6:
        violations.append("CI: every pip cache must be keyed from pyproject.toml")
    if text.count("python scripts/verify_package.py") != 1:
        violations.append("CI: package verification must execute exactly once")
    if text.count(TEST_COMMAND) != 1:
        violations.append("CI: accounting qualification test command must appear exactly once")

    forbidden = (
        "\n  lint:\n",
        "\n  typecheck:\n",
        "\n  engineering-safety:\n",
        "run: python scripts/qualify_release.py\n",
        "actions/checkout@v4",
        "actions/setup-python@v5",
    )
    message = "CI: forbidden legacy or redundant workflow construct"
    for snippet in forbidden:
        if snippet in text:
            violations.append(f"{message}: {snippet.strip()}")

    return violations


def validate_security_text(text: str) -> list[str]:
    """Return contract violations for the Security workflow text."""
    violations = _missing_snippets(
        text,
        (
            "permissions:\n  contents: read",
            "concurrency:",
            "cancel-in-progress: true",
            "audit:\n",
            "sast:\n",
            "python -m pip_audit",
            "python -m bandit -r src/ -c pyproject.toml",
        ),
        label="Security",
    )

    if text.count("actions/checkout@v7") != 2:
        violations.append("Security: expected exactly two actions/checkout@v7 uses")
    if text.count("actions/setup-python@v7") != 2:
        violations.append("Security: expected exactly two actions/setup-python@v7 uses")
    if text.count("cache: pip") != 2:
        violations.append("Security: every Python execution job must enable pip cache")
    if "actions/checkout@v4" in text or "actions/setup-python@v5" in text:
        violations.append("Security: legacy Node-20 action generations are forbidden")

    return violations


def workflow_violations() -> list[str]:
    """Validate workflow files from the repository root."""
    violations: list[str] = []
    for path, validator in (
        (CI_WORKFLOW, validate_ci_text),
        (SECURITY_WORKFLOW, validate_security_text),
    ):
        if not path.is_file():
            violations.append(f"workflow missing: {path.relative_to(ROOT)}")
            continue
        violations.extend(validator(path.read_text(encoding="utf-8")))
    return violations


def main() -> int:
    """CLI entry point for workflow contract validation."""
    violations = workflow_violations()
    if violations:
        print("CI workflow validation: FAIL", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    print("CI workflow validation: PASS")
    print(
        "Canonical jobs: quality, test, package, postgresql, sqlalchemy-postgresql, "
        "release-qualification, ci-gate"
    )
    print("Supported Python matrix: 3.11, 3.12, 3.13")
    print("Qualified suites: unit, property, contract, integration, golden, replay, concurrency")
    print("Production adapter gates: Django/PostgreSQL 16, SQLAlchemy/PostgreSQL 16")
    print("Security jobs: audit, sast")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
