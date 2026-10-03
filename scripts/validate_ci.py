#!/usr/bin/env python3
"""Validate canonical CI and Security workflow contracts for PyAccountingKit."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
SECURITY_WORKFLOW = ROOT / ".github" / "workflows" / "security.yml"
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
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
            "regulatory-qualification:\n",
            "consumer-bootstrap:\n",
            "consumer-publication:\n",
            "consumer-binding-advancement:\n",
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
            "regulatory-release-qualification:\n",
            "stable-release-qualification:\n",
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
            "python scripts/generate_regulatory_compatibility_matrix.py --check",
            "python scripts/generate_snapshot_schema_manifest.py --check",
            "python scripts/validate_documentation.py",
            "python scripts/validate_regulatory_gate.py",
            "Regulatory capability qualification",
            "tests/golden/regulatory/test_lot27_capability_profiles.py",
            "tests/golden/regulatory/test_nonprofit_effective_plan.py",
            "tests/unit/adapters/test_nonprofit_reference_adapter.py",
            "tests/unit/domain/test_effective_reference_plan.py",
            "tests/unit/domain/test_standard_relations.py",
            "tests/unit/adapters/test_ohada_relation_adapter.py",
            "tests/golden/regulatory/test_ebnl_structure_provider.py",
            "tests/golden/regulatory/test_ohada_standard_relations.py",
            "tests/integration/test_0_7_regulatory_compatibility_matrix.py",
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
            "python scripts/bootstrap_cfa_fra_live_consumer.py",
            "PYACCOUNTINGKIT_CONSUMER_BOOTSTRAP.json",
            "UNBOUND_UNTIL_PUBLISHED",
            "python scripts/run_cfa_fra_consumer_publication.py",
            "python scripts/run_cfa_fra_consumer_binding_advancement.py",
            "CFA FRA consumer publication handoff",
            "CFA FRA consumer binding revision advancement",
            "publication_sha256",
            "bootstrap_sha256",
            "python scripts/validate_cfa_fra_consumer_binding.py",
            "--require-bound",
            "consumer_repository_bound",
            "tests/consumer/cfa_fra/CONSUMER_BINDING.json",
            "startsWith(github.head_ref, 'release/0.6')",
            "startsWith(github.head_ref, 'release/0.7.0rc')",
            "github.head_ref == 'release/0.7.0'",
            "python scripts/validate_stable_gate.py",
            "needs: [test, postgresql, sqlalchemy-postgresql, cutover-evidence,",
            "consumer-bootstrap, consumer-binding]",
            "build/cfa_fra_live_retirement_readiness.json",
            "tests/consumer/cfa_fra/live_evidence/legacy-retirement-plan.json",
            "tests/consumer/cfa_fra/live_evidence/legacy-retirement-execution.json",
            "tests/consumer/cfa_fra/live_evidence/legacy-retirement-completion.json",
            "assert r['ready'] is True",
            "assert generated == committed",
            (
                "[quality, test, package, postgresql, sqlalchemy-postgresql, "
                "regulatory-qualification, consumer-bootstrap, consumer-publication, "
                "consumer-binding-advancement, "
                "consumer-binding, consumer-evidence, retirement-inventory, cutover-evidence, "
                "cutover-pipeline, retirement-plan, retirement-execution, retirement-completion, "
                "retirement-readiness, release-qualification, "
                "regulatory-release-qualification, stable-release-qualification]"
            ),
            "if: ${{ always() }}",
            "QUALITY_RESULT: ${{ needs.quality.result }}",
            "TEST_RESULT: ${{ needs.test.result }}",
            "PACKAGE_RESULT: ${{ needs.package.result }}",
            "POSTGRESQL_RESULT: ${{ needs.postgresql.result }}",
            "SQLALCHEMY_POSTGRESQL_RESULT: ${{ needs.sqlalchemy-postgresql.result }}",
            "REGULATORY_QUALIFICATION_RESULT: ${{ needs.regulatory-qualification.result }}",
            'test "$REGULATORY_QUALIFICATION_RESULT" = "success"',
            "CONSUMER_BOOTSTRAP_RESULT: ${{ needs.consumer-bootstrap.result }}",
            'test "$CONSUMER_BOOTSTRAP_RESULT" = "success"',
            "CONSUMER_PUBLICATION_RESULT: ${{ needs.consumer-publication.result }}",
            'test "$CONSUMER_PUBLICATION_RESULT" = "success"',
            "CONSUMER_BINDING_ADVANCEMENT_RESULT: ${{ needs.consumer-binding-advancement.result }}",
            'test "$CONSUMER_BINDING_ADVANCEMENT_RESULT" = "success"',
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
            (
                "REGULATORY_RELEASE_QUALIFICATION_RESULT: "
                "${{ needs.regulatory-release-qualification.result }}"
            ),
            (
                "STABLE_RELEASE_QUALIFICATION_RESULT: "
                "${{ needs.stable-release-qualification.result }}"
            ),
            "HEAD_REF: ${{ github.head_ref }}",
            'test "$REGULATORY_RELEASE_QUALIFICATION_RESULT" = "success"',
            'test "$REGULATORY_RELEASE_QUALIFICATION_RESULT" = "skipped"',
            'test "$STABLE_RELEASE_QUALIFICATION_RESULT" = "success"',
            'test "$STABLE_RELEASE_QUALIFICATION_RESULT" = "skipped"',
        ),
        label="CI",
    )

    if text.count("actions/checkout@v7") != 21:
        violations.append("CI: expected exactly twenty-one actions/checkout@v7 uses")
    if text.count("actions/setup-python@v7") != 21:
        violations.append("CI: expected exactly twenty-one actions/setup-python@v7 uses")
    if text.count("cache: pip") != 21:
        violations.append("CI: every Python execution job must enable pip cache")
    if text.count("cache-dependency-path:") != 21:
        violations.append("CI: every Python execution job must define a pip cache key")
    if text.count("if: ${{ !startsWith(github.head_ref, 'release/0.7') }}") != 12:
        violations.append("CI: every CFA FRA qualification job must skip release/0.7")
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


def validate_release_text(text: str) -> list[str]:
    """Return contract violations for the publication workflow."""
    violations = _missing_snippets(
        text,
        (
            'tags:\n      - "v*"',
            "permissions:\n  contents: read",
            "concurrency:",
            "cancel-in-progress: false",
            "preflight:\n",
            "build:\n",
            "publish-pypi:\n",
            "publication-smoke:\n",
            "github-release:\n",
            "release-integrity:\n",
            "fetch-depth: 0",
            "persist-credentials: false",
            "git fetch origin main --no-tags",
            "python scripts/prepare_release.py preflight",
            '--github-output "$GITHUB_OUTPUT"',
            "python scripts/qualify_release.py --release-candidate",
            "python scripts/prepare_release.py build",
            "Build, verify and seal distributions exactly once",
            "actions/upload-artifact@v7.0.1",
            "actions/download-artifact@v8.0.1",
            "environment:\n      name: pypi",
            "id-token: write",
            "pypa/gh-action-pypi-publish@v1.14.2",
            "packages-dir: release-bundle/dist/",
            "Verify exact PyPI publication",
            "pyaccountingkit==${RELEASE_VERSION}",
            "needs: [preflight, build, publish-pypi, publication-smoke]",
            "softprops/action-gh-release@v3.0.3",
            "draft: true",
            'gh release edit "$GITHUB_REF_NAME" --draft=false -R "$GITHUB_REPOSITORY"',
            'gh release verify "$GITHUB_REF_NAME" -R "$GITHUB_REPOSITORY"',
            "RELEASE_QUALIFICATION_MANIFEST.json",
            "SHA256SUMS",
        ),
        label="Release",
    )

    expected_counts = (
        ("actions/checkout@v7.0.1", 4),
        ("actions/setup-python@v7.0.0", 5),
        ("actions/upload-artifact@v7.0.1", 1),
        ("actions/download-artifact@v8.0.1", 2),
        ("python scripts/qualify_release.py --release-candidate", 1),
        ("python scripts/prepare_release.py build", 1),
        ("python scripts/prepare_release.py verify", 2),
        ("pypa/gh-action-pypi-publish@v1.14.2", 1),
        ("softprops/action-gh-release@v3.0.3", 1),
    )
    for snippet, expected in expected_counts:
        actual = text.count(snippet)
        if actual != expected:
            violations.append(
                f"Release: expected {expected} occurrence(s) of {snippet!r}, found {actual}"
            )

    forbidden = (
        "actions/checkout@v4",
        "actions/setup-python@v5",
        "pypa/gh-action-pypi-publish@release/v1",
        "softprops/action-gh-release@v2",
        "python -m build",
        "twine upload",
        "skip-existing:",
        "password:",
        "repository-url:",
        "cancel-in-progress: true",
    )
    for snippet in forbidden:
        if snippet in text:
            violations.append(f"Release: forbidden publication construct: {snippet}")

    return violations


def workflow_violations() -> list[str]:
    """Validate workflow files from the repository root."""
    violations: list[str] = []
    for path, validator in (
        (CI_WORKFLOW, validate_ci_text),
        (SECURITY_WORKFLOW, validate_security_text),
        (RELEASE_WORKFLOW, validate_release_text),
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
        "regulatory-qualification, consumer-evidence, retirement-inventory, cutover-evidence, "
        "cutover-pipeline, retirement-plan, retirement-execution, retirement-completion, "
        "retirement-readiness, release-qualification, regulatory-release-qualification, ci-gate"
    )
    print("Supported Python matrix: 3.11, 3.12, 3.13")
    print("Qualified suites: unit, property, contract, integration, golden, replay, concurrency")
    print("Production adapter gates: Django/PostgreSQL 16, SQLAlchemy/PostgreSQL 16")
    print(
        "Regulatory qualification: capability-scoped LOT-27 profiles, "
        "Non-Profit effective plan, EBNL structure, OHADA relation guards and golden safety"
    )
    print("Consumer bootstrap: deterministic standalone seed from immutable Sprint-7 oracle")
    print("Consumer publication: reviewed Git provenance handoff before BOUND")
    print("Consumer binding advancement: monotonic descendant revision re-attestation")
    print("Consumer binding: explicit live repository identity, UNBOUND allowed outside RC")
    print("Consumer gate: bundled CFA FRA Sprint-7 executable evidence")
    print("Retirement inventory: live-consumer deletion/rewire/migration classification")
    print("Cutover evidence: cryptographically verified consumer/identity/reference artifacts")
    print("Cutover pipeline: reviewed plan/apply execution on isolated fixture evidence")
    print("Retirement plan: deterministic non-executing L26-C actions after MIG-13 READY")
    print("Retirement execution: exact-plan post-cutover verification with immutable oracle guard")
    print("Retirement completion: sealed L26-C proof eligible for 0.6.0rc1 qualification")
    print(
        "RC1 live gate:",
        "release/0.6 requires bound consumer repository plus live readiness/completion",
    )
    print("LOT-27 RC gate: release/0.7.0rc uses regulatory GR/G4 evidence without CFA FRA jobs")
    print("LOT-27 stable gate: release/0.7.0 requires fail-closed G5 with 0 BLOCKER")
    print("Retirement gate: MIG-13 readiness with explicit blocker evidence")
    print("Security jobs: audit, sast")
    print(
        "Release pipeline: preflight, build-once, Trusted Publishing, PyPI smoke, "
        "draft-to-published GitHub Release, immutable verification"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
