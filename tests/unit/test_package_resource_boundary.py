"""Tests for wheel/sdist repository-resource exclusion contracts."""

from __future__ import annotations

import importlib.util
import io
import sys
import tarfile
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "verify_package.py"


def _load_verifier() -> ModuleType:
    name = "pyaccountingkit_package_resource_boundary_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write_tar_member(archive: tarfile.TarFile, name: str, payload: bytes = b"x") -> None:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    archive.addfile(info, io.BytesIO(payload))


def _build_fake_sdist(path: Path, *, include_resource: bool) -> None:
    prefix = "pyaccountingkit-0.7.0b1/"
    required = (
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "src/pyaccountingkit/__init__.py",
        "src/pyaccountingkit/py.typed",
    )
    with tarfile.open(path, mode="w:gz") as archive:
        for suffix in required:
            _write_tar_member(archive, prefix + suffix)
        if include_resource:
            _write_tar_member(
                archive,
                prefix + "resources/regulatory-accounting-data-framework/source.pdf",
            )


def test_sdist_contract_accepts_distribution_without_repository_resources(tmp_path: Path) -> None:
    """A source distribution may ship project files but not governed resource bundles."""
    module = _load_verifier()
    sdist = tmp_path / "pyaccountingkit-0.7.0b1.tar.gz"
    _build_fake_sdist(sdist, include_resource=False)

    module.verify_sdist(sdist, "0.7.0b1")


def test_sdist_contract_rejects_governed_resource_leak(tmp_path: Path) -> None:
    """A resource file inside the sdist is a hard packaging-governance failure."""
    module = _load_verifier()
    sdist = tmp_path / "pyaccountingkit-0.7.0b1.tar.gz"
    _build_fake_sdist(sdist, include_resource=True)

    with pytest.raises(module.VerificationError, match="repository-only content"):
        module.verify_sdist(sdist, "0.7.0b1")


def test_hatch_sdist_configuration_excludes_resources_and_data() -> None:
    """The build backend must explicitly exclude governed repository-only trees."""
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "[tool.hatch.build.targets.sdist]" in pyproject
    assert '"/resources"' in pyproject
    assert '"/data"' in pyproject
