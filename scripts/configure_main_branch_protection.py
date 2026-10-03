#!/usr/bin/env python3
"""Configure and verify the canonical GitHub protection policy for main."""

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
STATUS_FILE = ROOT / "docs" / "audits" / "LOT_00_REMEDIATION_STATUS.json"

OWNER = "tawounfouet"
REPOSITORY = "pyaccountingkit"
BRANCH = "main"
API_VERSION = "2026-03-10"
TOKEN_ENV = "PYAK_GITHUB_ADMIN_TOKEN"

REQUIRED_CHECKS = (
    "Canonical CI gate",
    "Dependency audit",
    "Static security analysis",
)


class BranchProtectionError(RuntimeError):
    """Raised when branch-protection administration cannot complete safely."""


def protection_payload() -> dict[str, Any]:
    """Return the canonical branch-protection configuration."""
    return {
        "required_status_checks": {
            "strict": True,
            "contexts": list(REQUIRED_CHECKS),
        },
        "enforce_admins": True,
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": False,
            "require_code_owner_reviews": False,
            "required_approving_review_count": 0,
            "require_last_push_approval": False,
        },
        "restrictions": None,
        "required_linear_history": True,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "block_creations": False,
        "required_conversation_resolution": True,
        "lock_branch": False,
        "allow_fork_syncing": True,
    }


def _api_url() -> str:
    return f"https://api.github.com/repos/{OWNER}/{REPOSITORY}/branches/{BRANCH}/protection"


def api_request(
    method: str,
    *,
    token: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call the GitHub branch-protection REST endpoint."""
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        _api_url(),
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "pyaccountingkit-lot00-closure",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise BranchProtectionError(
            f"GitHub API {method} failed with HTTP {exc.code}: {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise BranchProtectionError(f"GitHub API {method} failed: {exc.reason}") from exc

    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise BranchProtectionError("GitHub API returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise BranchProtectionError("GitHub API returned a non-object protection payload")
    return result


def protection_violations(data: object) -> list[str]:
    """Return deviations from the canonical protection policy."""
    if not isinstance(data, dict):
        return ["branch protection response must be an object"]

    violations: list[str] = []

    checks = data.get("required_status_checks")
    if not isinstance(checks, dict):
        violations.append("required_status_checks must be enabled")
    else:
        if checks.get("strict") is not True:
            violations.append("required_status_checks.strict must be true")
        contexts = checks.get("contexts")
        if not isinstance(contexts, list):
            violations.append("required_status_checks.contexts must be a list")
        else:
            missing = sorted(set(REQUIRED_CHECKS) - set(contexts))
            if missing:
                violations.append(f"missing required status checks: {missing}")

    admins = data.get("enforce_admins")
    if not isinstance(admins, dict) or admins.get("enabled") is not True:
        violations.append("admin enforcement must be enabled")

    reviews = data.get("required_pull_request_reviews")
    if not isinstance(reviews, dict):
        violations.append("pull requests must be required before merge")
    elif reviews.get("required_approving_review_count") != 0:
        violations.append("required approving review count must remain 0 for solo maintenance")

    force_pushes = data.get("allow_force_pushes")
    if not isinstance(force_pushes, dict) or force_pushes.get("enabled") is not False:
        violations.append("force pushes must be disabled")

    deletions = data.get("allow_deletions")
    if not isinstance(deletions, dict) or deletions.get("enabled") is not False:
        violations.append("branch deletion must be disabled")

    conversations = data.get("required_conversation_resolution")
    if not isinstance(conversations, dict) or conversations.get("enabled") is not True:
        violations.append("conversation resolution must be required")

    linear = data.get("required_linear_history")
    if not isinstance(linear, dict) or linear.get("enabled") is not True:
        violations.append("linear history must be required")

    return violations


def print_check(data: dict[str, Any]) -> int:
    """Print branch-protection verification result."""
    violations = protection_violations(data)
    if violations:
        print("Main branch protection: FAIL", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    print("Main branch protection: PASS")
    print(f"Repository: {OWNER}/{REPOSITORY}")
    print(f"Branch: {BRANCH}")
    print("Required checks:")
    for check in REQUIRED_CHECKS:
        print(f"- {check}")
    print("Pull request required: yes")
    print("Admin enforcement: yes")
    print("Force pushes: blocked")
    print("Branch deletion: blocked")
    print("Linear history: required")
    return 0


def _load_status() -> dict[str, Any]:
    try:
        data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BranchProtectionError(f"invalid LOT-00 status JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise BranchProtectionError("LOT-00 status file must contain an object")
    return data


def promote_lot00_status(protection: dict[str, Any]) -> None:
    """Promote LOT-00 only after a successful live protection observation."""
    violations = protection_violations(protection)
    if violations:
        raise BranchProtectionError(
            "cannot promote LOT-00 while branch protection is non-compliant: "
            + "; ".join(violations)
        )

    data = _load_status()
    external = data.get("external_controls")
    if not isinstance(external, dict):
        raise BranchProtectionError("LOT-00 status is missing external_controls")
    main_branch = external.get("main_branch")
    if not isinstance(main_branch, dict):
        raise BranchProtectionError("LOT-00 status is missing external_controls.main_branch")

    main_branch["observed_protected"] = True
    main_branch["observation"] = (
        "GitHub branch protection verified through the authenticated Administration API."
    )
    main_branch["verified_policy"] = {
        "required_status_checks": list(REQUIRED_CHECKS),
        "strict_status_checks": True,
        "pull_request_required": True,
        "admin_enforcement": True,
        "force_pushes_blocked": True,
        "deletion_blocked": True,
        "conversation_resolution_required": True,
        "linear_history_required": True,
    }

    blockers = data.get("blockers")
    if not isinstance(blockers, list):
        raise BranchProtectionError("LOT-00 status blockers must be a list")
    for blocker in blockers:
        if isinstance(blocker, dict) and blocker.get("id") == "MAIN_BRANCH_PROTECTION_UNENFORCED":
            blocker["status"] = "CLOSED"
            blocker["resolution"] = (
                "GitHub main branch protection verified with required PR, CI, security, "
                "admin, force-push and deletion controls."
            )

    sublots = data.get("sublots")
    if not isinstance(sublots, list):
        raise BranchProtectionError("LOT-00 status sublots must be a list")
    final = next(
        (item for item in sublots if isinstance(item, dict) and item.get("id") == "LOT-00.9"),
        None,
    )
    if final is None:
        raise BranchProtectionError("LOT-00.9 status entry is missing")
    final["status"] = "COMPLETE"
    data["overall_status"] = "COMPLETE"

    STATUS_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _token() -> str:
    token = os.environ.get(TOKEN_ENV, "").strip()
    if not token:
        raise BranchProtectionError(
            f"{TOKEN_ENV} is required; use a GitHub token with repository Administration: write"
        )
    return token


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("check", "apply", "promote-status"),
        help="Verify, apply, or verify-and-promote the LOT-00 external control.",
    )
    args = parser.parse_args(argv)

    try:
        token = _token()
        if args.action == "apply":
            protection = api_request("PUT", token=token, payload=protection_payload())
            result = print_check(protection)
            if result != 0:
                return result
            print("Main branch protection applied and verified.")
            return 0

        protection = api_request("GET", token=token)
        result = print_check(protection)
        if result != 0:
            return result

        if args.action == "promote-status":
            promote_lot00_status(protection)
            print(f"LOT-00 status promoted to COMPLETE in {STATUS_FILE.relative_to(ROOT)}")
        return 0
    except BranchProtectionError as exc:
        print(f"Main branch protection administration: FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
