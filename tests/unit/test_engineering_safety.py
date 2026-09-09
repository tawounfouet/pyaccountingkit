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


def test_manifest_gate_accepts_current_repository() -> None:
    """The current root manifests must satisfy the release qualifier contract."""
    module = _load_qualifier()
    result = module.validate_manifests()
    assert result.name == "Manifest coherence"
    assert result.duration_seconds >= 0
