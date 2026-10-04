"""Tests for G5 external-control orchestration."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "close_g5_external_controls.py"


def _load_module() -> ModuleType:
    name = "pyaccountingkit_g5_external_closure_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_missing_token_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    monkeypatch.delenv(module.TOKEN_ENV, raising=False)

    assert module.main(["check"]) == 2


def test_check_verifies_both_controls(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    calls: list[tuple[str, str]] = []

    def fake_run(script: Path, action: str) -> None:
        calls.append((script.name, action))

    monkeypatch.setattr(module, "_run", fake_run)

    module.check_controls()

    assert calls == [
        ("configure_main_branch_protection.py", "check"),
        ("configure_release_immutability.py", "check"),
    ]


def test_apply_verifies_again_after_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    calls: list[tuple[str, str]] = []

    def fake_run(script: Path, action: str) -> None:
        calls.append((script.name, action))

    monkeypatch.setattr(module, "_run", fake_run)

    module.apply_controls()

    assert calls == [
        ("configure_main_branch_protection.py", "apply"),
        ("configure_release_immutability.py", "apply"),
        ("configure_main_branch_protection.py", "check"),
        ("configure_release_immutability.py", "check"),
    ]


def test_promote_checks_both_before_any_status_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    calls: list[tuple[str, str]] = []

    def fake_run(script: Path, action: str) -> None:
        calls.append((script.name, action))

    monkeypatch.setattr(module, "_run", fake_run)

    module.promote_statuses()

    assert calls == [
        ("configure_main_branch_protection.py", "check"),
        ("configure_release_immutability.py", "check"),
        ("configure_main_branch_protection.py", "promote-status"),
        ("configure_release_immutability.py", "promote-status"),
    ]


def test_close_orders_apply_verify_then_promote(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    calls: list[tuple[str, str]] = []

    def fake_run(script: Path, action: str) -> None:
        calls.append((script.name, action))

    monkeypatch.setattr(module, "_run", fake_run)

    module.close_controls()

    assert calls == [
        ("configure_main_branch_protection.py", "apply"),
        ("configure_release_immutability.py", "apply"),
        ("configure_main_branch_protection.py", "check"),
        ("configure_release_immutability.py", "check"),
        ("configure_main_branch_protection.py", "check"),
        ("configure_release_immutability.py", "check"),
        ("configure_main_branch_protection.py", "promote-status"),
        ("configure_release_immutability.py", "promote-status"),
    ]


def test_subprocess_failure_aborts_immediately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()

    class Result:
        returncode = 1

    def fake_subprocess_run(*args, **kwargs):
        del args, kwargs
        return Result()

    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)

    with pytest.raises(module.G5ClosureError, match="failed with exit code 1"):
        module._run(module.BRANCH_SCRIPT, "check")


def test_main_close_has_no_release_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    monkeypatch.setenv(module.TOKEN_ENV, "test-token")
    called: list[str] = []
    monkeypatch.setattr(module, "close_controls", lambda: called.append("close"))

    assert module.main(["close"]) == 0
    assert called == ["close"]
    assert os.environ[module.TOKEN_ENV] == "test-token"
