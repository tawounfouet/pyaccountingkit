"""Tests for the executable CI workflow contract."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_ci.py"


def _load_validator() -> ModuleType:
    name = "pyaccountingkit_validate_ci_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_current_workflows_satisfy_canonical_contract() -> None:
    """The repository workflows must pass the hardened CI contract."""
    module = _load_validator()
    assert module.workflow_violations() == []
    assert module.main() == 0


def test_ci_contract_rejects_redundant_full_qualifier() -> None:
    """CI must not duplicate the complete release qualifier after dedicated jobs."""
    module = _load_validator()
    text = module.CI_WORKFLOW.read_text(encoding="utf-8")
    hardened = "python scripts/qualify_release.py --skip-tests --skip-package"
    invalid = text.replace(hardened, "python scripts/qualify_release.py")

    violations = module.validate_ci_text(invalid)
    assert any("full qualifier" in item or "redundant" in item for item in violations)


def test_ci_contract_requires_complete_python_matrix() -> None:
    """All supported Bootstrap Python versions must remain explicitly exercised."""
    module = _load_validator()
    text = module.CI_WORKFLOW.read_text(encoding="utf-8")
    invalid = text.replace(
        'python-version: ["3.11", "3.12", "3.13"]',
        'python-version: ["3.11", "3.12"]',
    )

    violations = module.validate_ci_text(invalid)
    assert any("3.13" in item for item in violations)


def test_ci_contract_requires_integration_suite() -> None:
    """Cross-lot integration must remain part of every supported Python test matrix run."""
    module = _load_validator()
    text = module.CI_WORKFLOW.read_text(encoding="utf-8")
    invalid = text.replace(" tests/integration", "")

    violations = module.validate_ci_text(invalid)
    assert any("accounting qualification test command" in item for item in violations)


def test_security_contract_rejects_legacy_action_generations() -> None:
    """Security must not regress to the Node-20 action generations."""
    module = _load_validator()
    text = module.SECURITY_WORKFLOW.read_text(encoding="utf-8")
    invalid = text.replace("actions/checkout@v7", "actions/checkout@v4", 1)

    violations = module.validate_security_text(invalid)
    assert any("legacy Node-20" in item for item in violations)


def test_release_contract_requires_fail_closed_qualification() -> None:
    """Tag publication must remain behind the strongest repository qualifier."""
    module = _load_validator()
    text = module.RELEASE_WORKFLOW.read_text(encoding="utf-8")
    invalid = text.replace(
        "python scripts/qualify_release.py --release-candidate",
        "echo qualification-skipped",
    )

    violations = module.validate_release_text(invalid)
    assert any("release-candidate" in item for item in violations)


def test_release_contract_rejects_secret_based_pypi_authentication() -> None:
    """PyPI publication must remain OIDC-only with no stored password/token input."""
    module = _load_validator()
    text = module.RELEASE_WORKFLOW.read_text(encoding="utf-8")
    invalid = text.replace(
        "packages-dir: release-bundle/dist/",
        "packages-dir: release-bundle/dist/\n          password: SECRET_TOKEN",
    )

    violations = module.validate_release_text(invalid)
    assert any("password:" in item for item in violations)


def test_release_contract_rejects_rebuild_after_bundle_sealing() -> None:
    """Publication jobs must consume the sealed build rather than rebuild distributions."""
    module = _load_validator()
    text = module.RELEASE_WORKFLOW.read_text(encoding="utf-8")
    invalid = text + "\n# regression\n# python -m build\n"

    violations = module.validate_release_text(invalid)
    assert any("python -m build" in item for item in violations)
