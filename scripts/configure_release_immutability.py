#!/usr/bin/env python3
"""Configure and verify GitHub release immutability for G5."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / "docs" / "audits" / "G5_EXTERNAL_CONTROLS.json"

OWNER = "tawounfouet"
REPOSITORY = "pyaccountingkit"
API_VERSION = "2026-03-10"
TOKEN_ENV = "PYAK_GITHUB_ADMIN_TOKEN"


class ReleaseImmutabilityError(RuntimeError):
    """Raised when release-immutability administration cannot complete safely."""


def _api_url() -> str:
    return f"https://api.github.com/repos/{OWNER}/{REPOSITORY}/immutable-releases"


def api_request(method: str, *, token: str) -> dict[str, Any]:
    """Call the GitHub immutable-releases REST endpoint."""
    request = urllib.request.Request(
        _api_url(),
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "pyaccountingkit-g5-closure",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
            content = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if method == "GET" and exc.code == 404:
            return {
                "enabled": False,
                "enforced_by_owner": False,
            }
        detail = exc.read().decode("utf-8", errors="replace")
        raise ReleaseImmutabilityError(
            f"GitHub API {method} failed with HTTP {exc.code}: {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise ReleaseImmutabilityError(f"GitHub API {method} failed: {exc.reason}") from exc

    if status == 204:
        return {}

    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ReleaseImmutabilityError("GitHub API returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise ReleaseImmutabilityError("GitHub API returned a non-object immutability payload")
    return result


def immutability_violations(data: object) -> list[str]:
    """Return deviations from the required G5 immutable-release state."""
    if not isinstance(data, dict):
        return ["release immutability response must be an object"]
    if data.get("enabled") is not True:
        return ["GitHub release immutability must be enabled"]
    return []


def print_check(data: dict[str, Any]) -> int:
    """Print release-immutability verification result."""
    violations = immutability_violations(data)
    if violations:
        print("GitHub release immutability: FAIL", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    print("GitHub release immutability: PASS")
    print(f"Repository: {OWNER}/{REPOSITORY}")
    print("Enabled: yes")
    print(f"Enforced by owner: {data.get('enforced_by_owner') is True}")
    return 0


def _load_status() -> dict[str, Any]:
    try:
        data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReleaseImmutabilityError(f"invalid G5 external controls JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ReleaseImmutabilityError("G5 external controls file must contain an object")
    return data


def promote_g5_status(state: dict[str, Any]) -> None:
    """Close only the immutable-release G5 blocker after a live positive observation."""
    violations = immutability_violations(state)
    if violations:
        raise ReleaseImmutabilityError(
            "cannot promote G5 while release immutability is non-compliant: "
            + "; ".join(violations)
        )

    data = _load_status()
    if data.get("target_version") != "0.7.0":
        raise ReleaseImmutabilityError("G5 external controls target_version must remain 0.7.0")

    controls = data.get("controls")
    if not isinstance(controls, dict):
        raise ReleaseImmutabilityError("G5 external controls is missing controls")
    immutable = controls.get("immutable_releases")
    if not isinstance(immutable, dict):
        raise ReleaseImmutabilityError("G5 external controls is missing immutable_releases")

    immutable["required"] = True
    immutable["observed_enabled"] = True
    immutable["status"] = "COMPLETE"
    immutable["enforced_by_owner"] = state.get("enforced_by_owner") is True
    immutable["observation"] = (
        "GitHub release immutability verified through the authenticated Administration API."
    )

    blockers = data.get("blockers")
    if not isinstance(blockers, list):
        raise ReleaseImmutabilityError("G5 external blockers must be a list")
    blocker = next(
        (
            item
            for item in blockers
            if isinstance(item, dict) and item.get("id") == "IMMUTABLE_RELEASES_UNVERIFIED"
        ),
        None,
    )
    if blocker is None:
        raise ReleaseImmutabilityError("IMMUTABLE_RELEASES_UNVERIFIED blocker is missing")
    blocker["status"] = "CLOSED"
    blocker["resolution"] = (
        "GitHub release immutability verified enabled through the authenticated "
        "Administration API before v0.7.0 creation."
    )

    claims = data.get("release_claims")
    if not isinstance(claims, dict):
        raise ReleaseImmutabilityError("G5 release_claims must be an object")
    if any(value is not False for value in claims.values()):
        raise ReleaseImmutabilityError(
            "release claims must remain false while only the external control is promoted"
        )

    STATUS_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _token() -> str:
    token = os.environ.get(TOKEN_ENV, "").strip()
    if not token:
        raise ReleaseImmutabilityError(
            f"{TOKEN_ENV} is required; use a GitHub token with repository Administration access"
        )
    return token


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("check", "apply", "promote-status"),
        help="Verify, enable, or verify-and-promote the G5 external control.",
    )
    args = parser.parse_args(argv)

    try:
        token = _token()

        if args.action == "apply":
            state = api_request("GET", token=token)
            if state.get("enabled") is not True:
                api_request("PUT", token=token)
                state = api_request("GET", token=token)
            result = print_check(state)
            if result != 0:
                return result
            print("GitHub release immutability enabled and verified.")
            return 0

        state = api_request("GET", token=token)
        result = print_check(state)
        if result != 0:
            return result

        if args.action == "promote-status":
            promote_g5_status(state)
            print(f"G5 external control promoted in {STATUS_FILE.relative_to(ROOT)}")
        return 0
    except ReleaseImmutabilityError as exc:
        print(f"Release immutability administration: FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
