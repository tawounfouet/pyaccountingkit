"""Tests for the PyAccountingKit 0.0.1 package metadata contract."""

from __future__ import annotations

import importlib.metadata
import importlib.resources
import tomllib
from pathlib import Path

import pyaccountingkit

ROOT = Path(__file__).resolve().parents[2]


def _project_config() -> dict[str, object]:
    """Load pyproject.toml for bootstrap metadata assertions."""
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_runtime_version_matches_project_metadata() -> None:
    """The runtime version must come from the canonical project version."""
    project = _project_config()["project"]
    assert isinstance(project, dict)
    assert pyaccountingkit.__version__ == project["version"] == "0.0.1"


def test_runtime_version_matches_installed_distribution() -> None:
    """Editable and wheel installs must expose the same distribution version."""
    assert pyaccountingkit.__version__ == importlib.metadata.version("pyaccountingkit")


def test_bootstrap_has_zero_runtime_dependencies() -> None:
    """Repository Bootstrap must stay dependency-free at runtime."""
    project = _project_config()["project"]
    assert isinstance(project, dict)
    assert project.get("dependencies", []) == []


def test_pep561_marker_is_packaged() -> None:
    """The installed package must expose its PEP 561 marker."""
    package_files = importlib.resources.files("pyaccountingkit")
    assert package_files.joinpath("py.typed").is_file()


def test_root_public_surface_is_explicit_and_minimal() -> None:
    """The bootstrap root exposes version metadata and no business API."""
    assert pyaccountingkit.__all__ == ["__version__"]
    public_names = {name for name in vars(pyaccountingkit) if not name.startswith("_")}
    assert public_names == set()
