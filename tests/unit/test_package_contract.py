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


def _write_wheel(path: Path, version: str, *, leaked_file: str | None = None) -> None:
    metadata = f"Metadata-Version: 2.1\nName: pyaccountingkit\nVersion: {version}\n"
    with zipfile.ZipFile(path, mode="w") as archive:
        archive.writestr("pyaccountingkit/__init__.py", f"__version__ = '{version}'\n")
        archive.writestr("pyaccountingkit/py.typed", "")
        archive.writestr(f"pyaccountingkit-{version}.dist-info/METADATA", metadata)
        if leaked_file is not None:
            archive.writestr(leaked_file, "unexpected")


def _add_tar_text(archive: tarfile.TarFile, name: str, content: str = "") -> None:
    data = content.encode("utf-8")
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def _write_sdist(path: Path, version: str) -> None:
    prefix = f"pyaccountingkit-{version}/"
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
    """Package metadata must stay aligned with the declared release version."""
    module = _load_package_verifier()
    assert module.project_metadata()[0] == "pyaccountingkit"
    assert module.project_metadata()[2] == []


@pytest.fixture
def project_version() -> str:
    """The canonical version declared by the current pyproject.toml."""
    module = _load_package_verifier()
    return module.project_metadata()[1]


def test_artifact_selection_requires_exactly_one_wheel_and_sdist(
    tmp_path: Path, project_version: str
) -> None:
    """Artifact selection must be deterministic for the expected version."""
    module = _load_package_verifier()
    wheel = tmp_path / f"pyaccountingkit-{project_version}-py3-none-any.whl"
    sdist = tmp_path / f"pyaccountingkit-{project_version}.tar.gz"
    wheel.touch()
    sdist.touch()
    assert module.select_artifacts(tmp_path, project_version) == (wheel, sdist)


def test_artifact_selection_rejects_missing_distribution(
    tmp_path: Path, project_version: str
) -> None:
    """Missing package artifacts must fail qualification."""
    module = _load_package_verifier()
    with pytest.raises(module.VerificationError, match="expected exactly one wheel"):
        module.select_artifacts(tmp_path, project_version)


def test_wheel_contract_accepts_minimal_wheel(tmp_path: Path, project_version: str) -> None:
    """The package gate accepts a correctly shaped minimal wheel."""
    module = _load_package_verifier()
    wheel = tmp_path / f"pyaccountingkit-{project_version}-py3-none-any.whl"
    _write_wheel(wheel, project_version)
    module.verify_wheel(wheel, "pyaccountingkit", project_version)


def test_wheel_contract_rejects_repository_content_leak(
    tmp_path: Path, project_version: str
) -> None:
    """Repository-only documentation must never leak into the wheel."""
    module = _load_package_verifier()
    wheel = tmp_path / f"pyaccountingkit-{project_version}-py3-none-any.whl"
    _write_wheel(wheel, project_version, leaked_file="docs/internal.md")
    with pytest.raises(module.VerificationError, match="repository-only content"):
        module.verify_wheel(wheel, "pyaccountingkit", project_version)


def test_sdist_contract_accepts_reproducibility_files(tmp_path: Path, project_version: str) -> None:
    """The sdist gate requires the repository files needed to rebuild the package."""
    module = _load_package_verifier()
    sdist = tmp_path / f"pyaccountingkit-{project_version}.tar.gz"
    _write_sdist(sdist, project_version)
    module.verify_sdist(sdist, project_version)
