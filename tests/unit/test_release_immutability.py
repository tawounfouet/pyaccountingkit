"""Tests for GitHub release-immutability G5 administration."""

from __future__ import annotations

import importlib.util
import json
import sys
import urllib.error
from io import BytesIO
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "configure_release_immutability.py"


def _load_module() -> ModuleType:
    name = "pyaccountingkit_release_immutability_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _enabled_state(*, enforced_by_owner: bool = False) -> dict[str, object]:
    return {
        "enabled": True,
        "enforced_by_owner": enforced_by_owner,
    }


def test_enabled_immutability_is_accepted() -> None:
    module = _load_module()

    assert module.immutability_violations(_enabled_state()) == []


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"enabled": False},
        {"enabled": None},
        [],
    ],
)
def test_non_enabled_immutability_is_rejected(payload: object) -> None:
    module = _load_module()

    violations = module.immutability_violations(payload)

    assert violations


def test_status_promotion_requires_positive_live_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    status_file = tmp_path / "g5.json"
    source = ROOT / "docs" / "audits" / "G5_EXTERNAL_CONTROLS.json"
    status_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(module, "STATUS_FILE", status_file)

    with pytest.raises(module.ReleaseImmutabilityError, match="cannot promote G5"):
        module.promote_g5_status({"enabled": False})


def test_status_promotion_closes_only_immutability_blocker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    status_file = tmp_path / "g5.json"
    source = ROOT / "docs" / "audits" / "G5_EXTERNAL_CONTROLS.json"
    status_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(module, "STATUS_FILE", status_file)

    module.promote_g5_status(_enabled_state(enforced_by_owner=True))

    promoted = json.loads(status_file.read_text(encoding="utf-8"))
    immutable = promoted["controls"]["immutable_releases"]
    assert immutable["required"] is True
    assert immutable["observed_enabled"] is True
    assert immutable["status"] == "COMPLETE"
    assert immutable["enforced_by_owner"] is True
    blocker = next(
        item for item in promoted["blockers"] if item["id"] == "IMMUTABLE_RELEASES_UNVERIFIED"
    )
    assert blocker["status"] == "CLOSED"
    assert all(value is False for value in promoted["release_claims"].values())


def test_missing_release_claims_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    status_file = tmp_path / "g5.json"
    source = ROOT / "docs" / "audits" / "G5_EXTERNAL_CONTROLS.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload.pop("release_claims")
    status_file.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(module, "STATUS_FILE", status_file)

    with pytest.raises(module.ReleaseImmutabilityError, match="release_claims"):
        module.promote_g5_status(_enabled_state())


def test_get_404_is_normalized_to_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()

    def fake_urlopen(request, timeout):
        del request, timeout
        raise urllib.error.HTTPError(
            module._api_url(),
            404,
            "Not Found",
            hdrs=None,
            fp=BytesIO(b"{}"),
        )

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    assert module.api_request("GET", token="test-token") == {
        "enabled": False,
        "enforced_by_owner": False,
    }


def test_apply_is_idempotent_when_already_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    calls: list[str] = []

    def fake_request(method: str, *, token: str) -> dict[str, object]:
        assert token == "test-token"
        calls.append(method)
        return _enabled_state(enforced_by_owner=True)

    monkeypatch.setattr(module, "api_request", fake_request)
    monkeypatch.setattr(module, "_token", lambda: "test-token")

    assert module.main(["apply"]) == 0
    assert calls == ["GET"]
