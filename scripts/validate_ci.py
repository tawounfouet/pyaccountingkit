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
            "consumer-binding:\n",
            "consumer-evidence:\n",
            "retirement-inventory:\n",
            "cutover-evidence:\n",
            "cutover-pipeline:\n",
            "retirement-plan:\n",
            "retirement-execution:\n",
            "retirement-completion:\n",
            "retirement-readiness:\n",
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
            "python scripts/qualify_cfa_fra_consumer.py",
            "consumer_e2e_green: ${{ steps.consumer-state.outputs.consumer_e2e_green }}",
            "consumer_e2e_green: ${{ steps.cutover-state.outputs.consumer_e2e_green }}",
            "python scripts/validate_cfa_fra_retirement_inventory.py",
            "python scripts/validate_cfa_fra_cutover_evidence.py",
            "python scripts/run_cfa_fra_cutover_evidence_pipeline.py",
            "python scripts/plan_cfa_fra_legacy_retirement.py",
            "python scripts/verify_cfa_fra_legacy_retirement_execution.py",
            "python scripts/qualify_cfa_fra_legacy_retirement_completion.py",
            "identities_traceable: ${{ steps.cutover-state.outputs.identities_traceable }}",
            (
                "regulatory_authority_replaced: "
                "${{ steps.cutover-state.outputs.regulatory_authority_replaced }}"
            ),
            '--consumer-e2e-green "${{ needs.cutover-evidence.outputs.consumer_e2e_green }}"',
            '--identities-traceable "${{ needs.cutover-evidence.outputs.identities_traceable }}"',
            (
                "--regulatory-authority-replaced "
                '"${{ needs.cutover-evidence.outputs.regulatory_authority_replaced }}"'
            ),
            "python scripts/qualify_cfa_fra_retirement.py",
            "resources/cfa_fra_django_mvp_sprint_7/pyproject.toml",
            "python scripts/qualify_release.py --release-candidate",
            "python scripts/validate_cfa_fra_consumer_binding.py",
            "--require-bound",
            "consumer_repository_bound",
            "tests/consumer/cfa_fra/CONSUMER_BINDING.json",
            "startsWith(github.head_ref, 'release/')",
            "needs: [test, postgresql, sqlalchemy-postgresql, cutover-evidence]",
            "build/cfa_fra_live_retirement_readiness.json",
            "tests/consumer/cfa_fra/live_evidence/legacy-retirement-plan.json",
            "tests/consumer/cfa_fra/live_evidence/legacy-retirement-execution.json",
            "tests/consumer/cfa_fra/live_evidence/legacy-retirement-completion.json",
            "assert r['ready'] is True",
            "assert generated == committed",
            (
                "[quality, test, package, postgresql, sqlalchemy-postgresql, "
                "consumer-binding, consumer-evidence, retirement-inventory, cutover-evidence, "
                "cutover-pipeline, retirement-plan, retirement-execution, retirement-completion, "
                "retirement-readiness, release-qualification]"
            ),
            "if: ${{ always() }}",
            "QUALITY_RESULT: ${{ needs.quality.result }}",
            "TEST_RESULT: ${{ needs.test.result }}",
            "PACKAGE_RESULT: ${{ needs.package.result }}",
            "POSTGRESQL_RESULT: ${{ needs.postgresql.result }}",
            "SQLALCHEMY_POSTGRESQL_RESULT: ${{ needs.sqlalchemy-postgresql.result }}",
            "CONSUMER_BINDING_RESULT: ${{ needs.consumer-binding.result }}",
            'test "$CONSUMER_BINDING_RESULT" = "success"',
            "CONSUMER_EVIDENCE_RESULT: ${{ needs.consumer-evidence.result }}",
            "RETIREMENT_INVENTORY_RESULT: ${{ needs.retirement-inventory.result }}",
            "CUTOVER_EVIDENCE_RESULT: ${{ needs.cutover-evidence.result }}",
            "CUTOVER_PIPELINE_RESULT: ${{ needs.cutover-pipeline.result }}",
            'test "$CUTOVER_PIPELINE_RESULT" = "success"',
            "RETIREMENT_PLAN_RESULT: ${{ needs.retirement-plan.result }}",
            'test "$RETIREMENT_PLAN_RESULT" = "success"',
            "RETIREMENT_EXECUTION_RESULT: ${{ needs.retirement-execution.result }}",
            'test "$RETIREMENT_EXECUTION_RESULT" = "success"',
            "RETIREMENT_COMPLETION_RESULT: ${{ needs.retirement-completion.result }}",
            'test "$RETIREMENT_COMPLETION_RESULT" = "success"',
            "RETIREMENT_READINESS_RESULT: ${{ needs.retirement-readiness.result }}",
            "RELEASE_QUALIFICATION_RESULT: ${{ needs.release-qualification.result }}",
        ),
        label="CI",
    )

    if text.count("actions/checkout@v7") != 15:
        violations.append("CI: expected exactly fifteen actions/checkout@v7 uses")
    if text.count("actions/setup-python@v7") != 15:
        violations.append("CI: expected exactly fifteen actions/setup-python@v7 uses")
    if text.count("cache: pip") != 15:
        violations.append("CI: every Python execution job must enable pip cache")
    if text.count("cache-dependency-path:") != 15:
        violations.append("CI: every Python execution job must define a pip cache key")
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
        '--consumer-e2e-green "${{ needs.consumer-evidence.outputs.consumer_e2e_green }}"',
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
        "consumer-evidence, retirement-inventory, cutover-evidence, "
        "cutover-pipeline, retirement-plan, retirement-execution, retirement-completion, "
        "retirement-readiness, release-qualification, ci-gate"
    )
    print("Supported Python matrix: 3.11, 3.12, 3.13")
    print("Qualified suites: unit, property, contract, integration, golden, replay, concurrency")
    print("Production adapter gates: Django/PostgreSQL 16, SQLAlchemy/PostgreSQL 16")
    print("Consumer binding: explicit live repository identity, UNBOUND allowed outside RC")
    print("Consumer gate: bundled CFA FRA Sprint-7 executable evidence")
    print("Retirement inventory: live-consumer deletion/rewire/migration classification")
    print("Cutover evidence: cryptographically verified consumer/identity/reference artifacts")
    print("Cutover pipeline: reviewed plan/apply execution on isolated fixture evidence")
    print("Retirement plan: deterministic non-executing L26-C actions after MIG-13 READY")
    print("Retirement execution: exact-plan post-cutover verification with immutable oracle guard")
    print("Retirement completion: sealed L26-C proof eligible for 0.6.0rc1 qualification")
    print("RC1 live gate: release/* requires bound consumer repository plus live readiness/completion")
    print("Retirement gate: MIG-13 readiness with explicit blocker evidence")
    print("Security jobs: audit, sast")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
