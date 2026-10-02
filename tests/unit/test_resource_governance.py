"""Tests for resource provenance, rights status and packaging governance."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_resource_governance.py"
REGISTRY = ROOT / "RESOURCE_GOVERNANCE.json"


def _load_validator() -> ModuleType:
    name = "pyaccountingkit_resource_governance_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _registry() -> dict[str, object]:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _stored_tree_lookup(data: dict[str, object]):
    bundles = data["bundles"]
    assert isinstance(bundles, list)
    mapping = {
        bundle["path"]: bundle["tree_sha"]
        for bundle in bundles
        if isinstance(bundle, dict)
    }
    return lambda path: str(mapping[path])


def _resource_paths(data: dict[str, object]) -> set[str]:
    bundles = data["bundles"]
    assert isinstance(bundles, list)
    return {
        str(bundle["path"])
        for bundle in bundles
        if isinstance(bundle, dict)
    }


def test_current_resource_governance_is_valid() -> None:
    """The checked-out repository must satisfy its pinned resource contract."""
    module = _load_validator()
    assert module.resource_governance_violations() == []
    assert module.main() == 0


def test_unregistered_resource_directory_is_rejected() -> None:
    """Adding a new resource subtree requires an explicit governance entry."""
    module = _load_validator()
    data = _registry()
    resource_paths = _resource_paths(data)
    resource_paths.add("resources/unreviewed-bundle")

    violations = module.validate_registry_data(
        data,
        resource_directories=resource_paths,
        tree_lookup=_stored_tree_lookup(data),
    )

    assert any("missing governance entries" in item for item in violations)


def test_resource_tree_drift_is_rejected() -> None:
    """A resource snapshot cannot change without refreshing its pinned Git tree."""
    module = _load_validator()
    data = _registry()
    resource_paths = _resource_paths(data)

    def drifted_tree(path: str) -> str:
        if path == "resources/cfa_fra_django_mvp_sprint_7":
            return "f" * 40
        return _stored_tree_lookup(data)(path)

    violations = module.validate_registry_data(
        data,
        resource_directories=resource_paths,
        tree_lookup=drifted_tree,
    )

    assert any("tree SHA drifted" in item for item in violations)


def test_third_party_bundle_cannot_claim_project_mit_status() -> None:
    """Third-party source bundles must remain explicitly rights-review-required."""
    module = _load_validator()
    data = copy.deepcopy(_registry())
    bundles = data["bundles"]
    assert isinstance(bundles, list)
    regulatory = next(
        bundle
        for bundle in bundles
        if isinstance(bundle, dict)
        and bundle.get("id") == "regulatory-accounting-data-framework"
    )
    regulatory["rights_status"] = "MIT"

    violations = module.validate_registry_data(
        data,
        resource_directories=_resource_paths(data),
        tree_lookup=_stored_tree_lookup(data),
    )

    assert any("unsupported rights_status" in item for item in violations)
    assert any("third-party source bundle" in item for item in violations)


def test_resource_package_or_runtime_dependency_is_rejected() -> None:
    """Repository evidence cannot silently become shipped runtime content."""
    module = _load_validator()
    data = copy.deepcopy(_registry())
    bundles = data["bundles"]
    assert isinstance(bundles, list)
    first = bundles[0]
    assert isinstance(first, dict)
    first["package_inclusion"] = True
    first["runtime_dependency"] = True

    violations = module.validate_registry_data(
        data,
        resource_directories=_resource_paths(data),
        tree_lookup=_stored_tree_lookup(data),
    )

    assert any("package_inclusion must be false" in item for item in violations)
    assert any("runtime_dependency must be false" in item for item in violations)


def test_resource_manifest_version_drift_is_rejected() -> None:
    """Registry identity must follow each embedded bundle's own manifest."""
    module = _load_validator()
    data = copy.deepcopy(_registry())
    bundles = data["bundles"]
    assert isinstance(bundles, list)
    first = bundles[0]
    assert isinstance(first, dict)
    first["manifest_version"] = "999.0"

    violations = module.validate_registry_data(
        data,
        resource_directories=_resource_paths(data),
        tree_lookup=_stored_tree_lookup(data),
    )

    assert any("version" in item and "999.0" in item for item in violations)
