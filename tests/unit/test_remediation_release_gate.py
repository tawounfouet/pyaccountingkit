"""Tests for the REM-10 remediation release gate."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def _load_module() -> ModuleType:
    name = "pyaccountingkit_remediation_release_gate_test"
    path = ROOT / "scripts" / "validate_remediation_release_gate.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _materialize_fixture(tmp_path: Path) -> dict[str, object]:
    registry = json.loads(
        (ROOT / "docs" / "audits" / "REMEDIATION_2026_10_STATUS.json").read_text(
            encoding="utf-8"
        )
    )
    version = str(registry["package_version"])
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "pyaccountingkit"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    registry_path = tmp_path / "docs" / "audits" / "REMEDIATION_2026_10_STATUS.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    for finding in registry["findings"]:
        for test_ref in finding["corrective_tests"]:
            test_path = tmp_path / str(test_ref).split("::", 1)[0]
            test_path.parent.mkdir(parents=True, exist_ok=True)
            test_path.touch()

    return registry


def test_actual_repository_passes_remediation_release_gate() -> None:
    module = _load_module()
    assert module.remediation_release_violations(root=ROOT) == []


def test_gate_rejects_open_finding(tmp_path: Path) -> None:
    module = _load_module()
    registry = _materialize_fixture(tmp_path)
    registry["findings"][0]["status"] = "OPEN"
    registry_path = tmp_path / "docs" / "audits" / "REMEDIATION_2026_10_STATUS.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    violations = module.remediation_release_violations(root=tmp_path)

    assert any("F01" in item and "FIXED_UNVERIFIED or VERIFIED" in item for item in violations)


def test_gate_rejects_conditional_release_scope(tmp_path: Path) -> None:
    module = _load_module()
    registry = _materialize_fixture(tmp_path)
    a01 = next(item for item in registry["findings"] if item["id"] == "A01")
    a01["release_scope"] = "CONDITIONAL"
    registry_path = tmp_path / "docs" / "audits" / "REMEDIATION_2026_10_STATUS.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    violations = module.remediation_release_violations(root=tmp_path)

    assert any("A01" in item and "release_scope" in item for item in violations)


def test_gate_rejects_package_version_drift(tmp_path: Path) -> None:
    module = _load_module()
    _materialize_fixture(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "pyaccountingkit"\nversion = "9.9.9"\n',
        encoding="utf-8",
    )

    violations = module.remediation_release_violations(root=tmp_path)

    assert any("package_version must match" in item for item in violations)


def test_gate_rejects_missing_corrective_test_path(tmp_path: Path) -> None:
    module = _load_module()
    registry = _materialize_fixture(tmp_path)
    first_ref = registry["findings"][0]["corrective_tests"][0]
    (tmp_path / str(first_ref).split("::", 1)[0]).unlink()

    violations = module.remediation_release_violations(root=tmp_path)

    assert any("corrective test path does not exist" in item for item in violations)
