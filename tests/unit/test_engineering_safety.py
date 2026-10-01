"""Tests for executable repository engineering-safety tooling."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _run(*command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True)


def _load_qualifier() -> ModuleType:
    name = "pyaccountingkit_qualify_release_test"
    path = ROOT / "scripts" / "qualify_release.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_repository_hygiene_cli_passes() -> None:
    """The actual repository must pass its hygiene script."""
    result = _run("bash", "scripts/check_hygiene.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Repository hygiene: PASS" in result.stdout


def test_architecture_cli_passes() -> None:
    """The actual repository must pass its architecture CLI."""
    result = _run(sys.executable, "scripts/validate_architecture.py")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Architecture validation: PASS" in result.stdout


def test_qualifier_help_is_available() -> None:
    """Release qualification tooling must expose a usable CLI contract."""
    result = _run(sys.executable, "scripts/qualify_release.py", "--help")
    assert result.returncode == 0
    assert "--skip-tests" in result.stdout
    assert "--skip-package" in result.stdout
    assert "--release-candidate" in result.stdout


@pytest.mark.parametrize(
    ("skip_flag", "expected"),
    (
        ("--skip-tests", "cannot skip tests"),
        ("--skip-package", "cannot skip package verification"),
    ),
)
def test_release_candidate_qualifier_rejects_skipped_evidence(
    skip_flag: str,
    expected: str,
) -> None:
    result = _run(
        sys.executable,
        "scripts/qualify_release.py",
        "--release-candidate",
        skip_flag,
    )
    assert result.returncode == 1
    assert expected in result.stderr


def test_release_candidate_contract_requires_every_extended_suite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_qualifier()
    for relative in ("tests/golden", "tests/replay", "tests/concurrency"):
        directory = tmp_path / relative
        directory.mkdir(parents=True)
        (directory / "test_present.py").write_text("def test_present(): pass\n", encoding="utf-8")

    monkeypatch.setattr(module, "ROOT", tmp_path)
    with pytest.raises(module.QualificationError, match="tests/integration"):
        module.validate_release_candidate_contract(skip_tests=False, skip_package=False)


def test_release_candidate_contract_requires_versioned_0_4_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_qualifier()
    for relative in ("tests/integration", "tests/golden", "tests/replay", "tests/concurrency"):
        directory = tmp_path / relative
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "test_present.py").write_text("def test_present(): pass\n", encoding="utf-8")

    required = module._VERSIONED_RC_EVIDENCE["0.4.0rc1"]
    missing = "tests/replay/test_0_4_release_pipeline_replay.py"
    for relative in required:
        if relative == missing:
            continue
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def test_release_evidence(): pass\n", encoding="utf-8")

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "project_version", lambda: "0.4.0rc1")
    with pytest.raises(module.QualificationError, match="0.4.0rc1.*missing required evidence"):
        module.validate_release_candidate_contract(skip_tests=False, skip_package=False)


def test_release_candidate_contract_requires_versioned_0_5_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_qualifier()
    for relative in ("tests/integration", "tests/golden", "tests/replay", "tests/concurrency"):
        directory = tmp_path / relative
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "test_present.py").write_text("def test_present(): pass\n", encoding="utf-8")

    required = module._VERSIONED_RC_EVIDENCE["0.5.0rc1"]
    missing = "tests/integration/test_sqlalchemy_postgresql_adapter.py"
    for relative in required:
        if relative == missing:
            continue
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def test_release_evidence(): pass\n", encoding="utf-8")

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "project_version", lambda: "0.5.0rc1")
    with pytest.raises(module.QualificationError, match="0.5.0rc1.*missing required evidence"):
        module.validate_release_candidate_contract(skip_tests=False, skip_package=False)


def _write_0_6_rc1_required_evidence(
    module: object,
    root: Path,
    *,
    skip: str | None = None,
    completion: dict[str, object] | None = None,
    binding_status: str = "BOUND",
) -> None:
    for relative in ("tests/integration", "tests/golden", "tests/replay", "tests/concurrency"):
        directory = root / relative
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "test_present.py").write_text("def test_present(): pass\n", encoding="utf-8")

    required = module._VERSIONED_RC_EVIDENCE["0.6.0rc1"]
    for relative in required:
        if relative == skip:
            continue
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative == "tests/consumer/cfa_fra/live_evidence/legacy-retirement-completion.json":
            payload = completion if completion is not None else {}
            path.write_text(json.dumps(payload), encoding="utf-8")
        elif relative == "tests/consumer/cfa_fra/CONSUMER_BINDING.json":
            revision = (
                completion.get("consumer_revision") if completion is not None else None
            ) or "b" * 40
            payload: dict[str, object] = {
                "schema_version": "1",
                "status": binding_status,
                "consumer": "CFA FRA Django MVP Sprint 7",
            }
            if binding_status == "BOUND":
                payload["binding"] = {
                    "schema": "cfa_fra_live_consumer_binding/v1",
                    "kind": "live_consumer_repository_binding",
                    "consumer": "CFA FRA Django MVP Sprint 7",
                    "repository": "tawounfouet/cfa-fra-live",
                    "repository_url": "https://github.com/tawounfouet/cfa-fra-live",
                    "default_branch": "main",
                    "revision_sha": revision,
                    "environment": "production",
                    "observed_at": "2026-10-01T06:00:00Z",
                    "producer": "release-test",
                }
            else:
                payload["reason"] = "repository identity not supplied"
            path.write_text(json.dumps(payload), encoding="utf-8")
        elif path.suffix == ".json":
            path.write_text("{}\n", encoding="utf-8")
        else:
            path.write_text("def test_release_evidence(): pass\n", encoding="utf-8")

    inventory = root / "tests" / "consumer" / "cfa_fra" / "LEGACY_RETIREMENT_INVENTORY.json"
    inventory.parent.mkdir(parents=True, exist_ok=True)
    inventory.write_text(
        json.dumps(
            {
                "oracle": {
                    "tree_sha": "07d4880534d2e2239e19fd4ef4139de70b56773a",
                }
            }
        ),
        encoding="utf-8",
    )


def test_release_candidate_contract_requires_versioned_0_6_live_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_qualifier()
    missing = "tests/consumer/cfa_fra/live_evidence/legacy-retirement-completion.json"
    _write_0_6_rc1_required_evidence(module, tmp_path, skip=missing)

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "project_version", lambda: "0.6.0rc1")
    with pytest.raises(module.QualificationError, match="0.6.0rc1.*missing required evidence"):
        module.validate_release_candidate_contract(skip_tests=False, skip_package=False)


def test_release_candidate_contract_rejects_non_complete_0_6_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_qualifier()
    _write_0_6_rc1_required_evidence(
        module,
        tmp_path,
        completion={
            "schema_version": "1",
            "status": "BLOCKED",
            "ready_for_0_6_rc1": False,
            "routing_target_only": True,
        },
    )

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "project_version", lambda: "0.6.0rc1")
    with pytest.raises(module.QualificationError, match="requires status='COMPLETE'"):
        module.validate_release_candidate_contract(skip_tests=False, skip_package=False)


def test_release_candidate_contract_rejects_unbound_0_6_consumer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_qualifier()
    oracle = "07d4880534d2e2239e19fd4ef4139de70b56773a"
    digest = "a" * 64
    _write_0_6_rc1_required_evidence(
        module,
        tmp_path,
        binding_status="UNBOUND",
        completion={
            "schema_version": "1",
            "status": "COMPLETE",
            "ready_for_0_6_rc1": True,
            "routing_target_only": True,
            "oracle_tree_sha": oracle,
            "consumer_revision": "b" * 40,
            "plan_sha256": digest,
            "execution_receipt_sha256": digest,
            "inventory_sha256": digest,
            "readiness_sha256": digest,
            "completion_sha256": digest,
            "action_counts": {
                "RETIRE_DUPLICATE_ENGINE": 10,
                "VERIFY_CONSUMER_REWIRED": 8,
                "PRESERVE_OR_MIGRATE_PERSISTENCE": 7,
                "KEEP_CONSUMER_CONCERN": 8,
                "PRESERVE_FROZEN_ORACLE": 6,
            },
        },
    )

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "project_version", lambda: "0.6.0rc1")
    with pytest.raises(
        module.QualificationError,
        match="requires a BOUND live consumer repository",
    ):
        module.validate_release_candidate_contract(skip_tests=False, skip_package=False)


def test_release_candidate_contract_accepts_complete_0_6_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_qualifier()
    oracle = "07d4880534d2e2239e19fd4ef4139de70b56773a"
    digest = "a" * 64
    _write_0_6_rc1_required_evidence(
        module,
        tmp_path,
        completion={
            "schema_version": "1",
            "status": "COMPLETE",
            "ready_for_0_6_rc1": True,
            "routing_target_only": True,
            "oracle_tree_sha": oracle,
            "consumer_revision": "b" * 40,
            "plan_sha256": digest,
            "execution_receipt_sha256": digest,
            "inventory_sha256": digest,
            "readiness_sha256": digest,
            "completion_sha256": digest,
            "action_counts": {
                "RETIRE_DUPLICATE_ENGINE": 10,
                "VERIFY_CONSUMER_REWIRED": 8,
                "PRESERVE_OR_MIGRATE_PERSISTENCE": 7,
                "KEEP_CONSUMER_CONCERN": 8,
                "PRESERVE_FROZEN_ORACLE": 6,
            },
        },
    )

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "project_version", lambda: "0.6.0rc1")
    module.validate_release_candidate_contract(skip_tests=False, skip_package=False)


def test_manifest_gate_rejects_version_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Manifest qualification must fail when one manifest drifts from the project version."""
    module = _load_qualifier()
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "pyaccountingkit"\nversion = "0.0.1"\n',
        encoding="utf-8",
    )
    manifests = {
        "PUBLIC_API_MANIFEST.json": {"version": "0.0.2", "public_api": {}},
        "PUBLIC_ERROR_CODES.json": {"version": "0.0.1", "error_codes": {}},
        "ADAPTER_CONTRACT_MANIFEST.json": {"version": "0.0.1", "adapter_contracts": {}},
        "REGULATORY_COMPATIBILITY_MATRIX.json": {
            "version": "0.0.1",
            "regulatory_frameworks": [],
        },
    }
    for filename, payload in manifests.items():
        (tmp_path / filename).write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(module, "ROOT", tmp_path)
    with pytest.raises(module.QualificationError, match="does not match 0.0.1"):
        module.validate_manifests()


@pytest.mark.parametrize(
    "script",
    (
        "scripts/generate_public_api_manifest.py",
        "scripts/generate_error_codes_manifest.py",
        "scripts/generate_adapter_contract_manifest.py",
    ),
)
def test_generated_manifests_are_committed_deterministically(script: str) -> None:
    result = _run(sys.executable, script, "--check")
    assert result.returncode == 0, result.stdout + result.stderr
    assert ": OK" in result.stdout


def test_manifest_gate_accepts_current_repository() -> None:
    """The current root manifests must satisfy the release qualifier contract."""
    module = _load_qualifier()
    result = module.validate_manifests()
    assert result.name == "Manifest coherence"
    assert result.duration_seconds >= 0
