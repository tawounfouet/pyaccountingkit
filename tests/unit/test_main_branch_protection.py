"""Tests for canonical main-branch protection administration."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "configure_main_branch_protection.py"


def _load_module() -> ModuleType:
    name = "pyaccountingkit_main_protection_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _compliant_response(module: ModuleType) -> dict[str, object]:
    return {
        "required_status_checks": {
            "strict": True,
            "contexts": list(module.REQUIRED_CHECKS),
        },
        "enforce_admins": {"enabled": True},
        "required_pull_request_reviews": {
            "required_approving_review_count": 0,
        },
        "allow_force_pushes": {"enabled": False},
        "allow_deletions": {"enabled": False},
        "required_conversation_resolution": {"enabled": True},
        "required_linear_history": {"enabled": True},
    }


def test_protection_payload_is_fail_closed() -> None:
    """The desired server-side policy must remain explicit and restrictive."""
    module = _load_module()
    payload = module.protection_payload()

    assert payload["required_status_checks"] == {
        "strict": True,
        "contexts": list(module.REQUIRED_CHECKS),
    }
    assert payload["enforce_admins"] is True
    assert payload["required_pull_request_reviews"]["required_approving_review_count"] == 0
    assert payload["allow_force_pushes"] is False
    assert payload["allow_deletions"] is False
    assert payload["required_conversation_resolution"] is True
    assert payload["required_linear_history"] is True


def test_compliant_protection_is_accepted() -> None:
    """Exact required checks and branch safety controls close the external blocker."""
    module = _load_module()
    assert module.protection_violations(_compliant_response(module)) == []


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (
            lambda data: data["required_status_checks"]["contexts"].remove("Canonical CI gate"),
            "missing required status checks",
        ),
        (
            lambda data: data["allow_force_pushes"].update({"enabled": True}),
            "force pushes must be disabled",
        ),
        (
            lambda data: data["allow_deletions"].update({"enabled": True}),
            "branch deletion must be disabled",
        ),
        (
            lambda data: data["enforce_admins"].update({"enabled": False}),
            "admin enforcement must be enabled",
        ),
        (
            lambda data: data.pop("required_pull_request_reviews"),
            "pull requests must be required",
        ),
    ],
)
def test_noncompliant_protection_is_rejected(mutation, expected: str) -> None:
    """Every mandatory GitHub server-side control is independently fail-closed."""
    module = _load_module()
    data = _compliant_response(module)
    mutation(data)

    violations = module.protection_violations(data)
    assert any(expected in violation for violation in violations)


def test_status_promotion_requires_compliant_protection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LOT-00 cannot move to COMPLETE from a non-compliant server observation."""
    module = _load_module()
    status_file = tmp_path / "status.json"
    source = ROOT / "docs" / "audits" / "LOT_00_REMEDIATION_STATUS.json"
    status_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(module, "STATUS_FILE", status_file)

    data = _compliant_response(module)
    data["allow_force_pushes"] = {"enabled": True}

    with pytest.raises(module.BranchProtectionError, match="cannot promote LOT-00"):
        module.promote_lot00_status(data)


def test_status_promotion_closes_only_the_external_blocker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A verified server policy promotes LOT-00 without inventing release claims."""
    module = _load_module()
    status_file = tmp_path / "status.json"
    source = ROOT / "docs" / "audits" / "LOT_00_REMEDIATION_STATUS.json"
    status_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(module, "STATUS_FILE", status_file)

    module.promote_lot00_status(_compliant_response(module))

    promoted = json.loads(status_file.read_text(encoding="utf-8"))
    assert promoted["overall_status"] == "COMPLETE"
    assert promoted["external_controls"]["main_branch"]["observed_protected"] is True
    final = next(item for item in promoted["sublots"] if item["id"] == "LOT-00.9")
    assert final["status"] == "COMPLETE"
    blocker = next(
        item
        for item in promoted["blockers"]
        if item["id"] == "MAIN_BRANCH_PROTECTION_UNENFORCED"
    )
    assert blocker["status"] == "CLOSED"
    assert all(value is False for value in promoted["release_claims"].values())
