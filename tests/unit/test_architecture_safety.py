"""Executable tests for the bootstrap architecture safety gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_architecture.py"


def _load_architecture_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("pyaccountingkit_architecture_gate_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bootstrap_package(tmp_path: Path) -> Path:
    package_root = tmp_path / "pyaccountingkit"
    package_root.mkdir()
    (package_root / "__init__.py").write_text('"""bootstrap root"""\n', encoding="utf-8")
    for layer in ("core", "domain", "ports"):
        directory = package_root / layer
        directory.mkdir()
        (directory / "__init__.py").write_text('"""scaffold"""\n', encoding="utf-8")
    return package_root


def test_current_repository_has_no_architecture_violations() -> None:
    """The actual repository must satisfy every architecture rule."""
    module = _load_architecture_module()
    assert module.boundary_violations() == []
    assert module.bootstrap_scaffold_violations() == []
    assert module.root_surface_violations() == []
    assert module.main() == 0


def test_boundary_gate_detects_forbidden_framework_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A framework import in core must fail the isolated-layer contract."""
    module = _load_architecture_module()
    package_root = _bootstrap_package(tmp_path)
    (package_root / "core" / "bad.py").write_text("import django\n", encoding="utf-8")
    monkeypatch.setattr(module, "PACKAGE_ROOT", package_root)

    violations = module.boundary_violations()
    assert len(violations) == 1
    assert "core/bad.py: forbidden import django" in violations[0]


def test_bootstrap_gate_detects_executable_business_scaffold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An executable class in a 0.0.1 scaffold must be rejected."""
    module = _load_architecture_module()
    package_root = _bootstrap_package(tmp_path)
    (package_root / "domain" / "money.py").write_text("class Money:\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(module, "PACKAGE_ROOT", package_root)
    monkeypatch.setattr(module, "project_version", lambda: "0.0.1")

    violations = module.bootstrap_scaffold_violations()
    expected = "domain/money.py: executable bootstrap nodes present: ClassDef"
    assert any(expected in item for item in violations)


def test_root_surface_gate_detects_premature_business_symbol(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A business function at package root must be rejected during bootstrap."""
    module = _load_architecture_module()
    package_root = _bootstrap_package(tmp_path)
    root_init = package_root / "__init__.py"
    root_init.write_text("def post_entry():\n    return None\n", encoding="utf-8")
    monkeypatch.setattr(module, "PACKAGE_ROOT", package_root)
    monkeypatch.setattr(module, "project_version", lambda: "0.0.1")

    assert module.root_surface_violations() == ["__init__.py: premature public symbol post_entry"]
