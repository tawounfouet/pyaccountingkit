"""Fast contract tests for wheel and sdist verification rules."""

from __future__ import annotations

import importlib.util
import io
import tarfile
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "verify_package.py"


def _load_package_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("pyaccountingkit_package_gate_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_wheel(path: Path, *, leaked_file: str | None = None) -> None:
    metadata = "Metadata-Version: 2.1\nName: pyaccountingkit\nVersion: 0.0.1\n"
    with zipfile.ZipFile(path, mode="w") as archive:
        archive.writestr("pyaccountingkit/__init__.py", "__version__ = '0.0.1'\n")
        archive.writestr("pyaccountingkit/py.typed", "")
        archive.writestr("pyaccountingkit-0.0.1.dist-info/METADATA", metadata)
        if leaked_file is not None:
            archive.writestr(leaked_file, "unexpected")


def _add_tar_text(archive: tarfile.TarFile, name: str, content: str = "") -> None:
    data = content.encode("utf-8")
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def _write_sdist(path: Path) -> None:
    prefix = "pyaccountingkit-0.0.1/"
    required = (
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "src/pyaccountingkit/__init__.py",
        "src/pyaccountingkit/py.typed",
    )
    with tarfile.open(path, mode="w:gz") as archive:
        for relative_path in required:
            _add_tar_text(archive, prefix + relative_path)


def test_project_metadata_contract() -> None:
    """Package metadata must remain aligned with the bootstrap release."""
    module = _load_package_verifier()
    assert module.project_metadata() == ("pyaccountingkit", "0.0.1", [])


def test_artifact_selection_requires_exactly_one_wheel_and_sdist(tmp_path: Path) -> None:
    """Artifact selection must be deterministic for the expected version."""
    module = _load_package_verifier()
    wheel = tmp_path / "pyaccountingkit-0.0.1-py3-none-any.whl"
    sdist = tmp_path / "pyaccountingkit-0.0.1.tar.gz"
    wheel.touch()
    sdist.touch()
    assert module.select_artifacts(tmp_path, "0.0.1") == (wheel, sdist)


def test_artifact_selection_rejects_missing_distribution(tmp_path: Path) -> None:
    """Missing package artifacts must fail qualification."""
    module = _load_package_verifier()
    with pytest.raises(module.VerificationError, match="expected exactly one wheel"):
        module.select_artifacts(tmp_path, "0.0.1")


def test_wheel_contract_accepts_minimal_bootstrap_wheel(tmp_path: Path) -> None:
    """The package gate accepts a correctly shaped minimal wheel."""
    module = _load_package_verifier()
    wheel = tmp_path / "pyaccountingkit-0.0.1-py3-none-any.whl"
    _write_wheel(wheel)
    module.verify_wheel(wheel, "pyaccountingkit", "0.0.1")


def test_wheel_contract_rejects_repository_content_leak(tmp_path: Path) -> None:
    """Repository-only documentation must never leak into the wheel."""
    module = _load_package_verifier()
    wheel = tmp_path / "pyaccountingkit-0.0.1-py3-none-any.whl"
    _write_wheel(wheel, leaked_file="docs/internal.md")
    with pytest.raises(module.VerificationError, match="repository-only content"):
        module.verify_wheel(wheel, "pyaccountingkit", "0.0.1")


def test_sdist_contract_accepts_reproducibility_files(tmp_path: Path) -> None:
    """The sdist gate requires the repository files needed to rebuild the package."""
    module = _load_package_verifier()
    sdist = tmp_path / "pyaccountingkit-0.0.1.tar.gz"
    _write_sdist(sdist)
    module.verify_sdist(sdist, "0.0.1")
