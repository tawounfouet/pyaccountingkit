#!/usr/bin/env python3
"""Orchestrate fail-closed closure of PyAccountingKit G5 GitHub controls."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRANCH_SCRIPT = ROOT / "scripts" / "configure_main_branch_protection.py"
IMMUTABILITY_SCRIPT = ROOT / "scripts" / "configure_release_immutability.py"
TOKEN_ENV = "PYAK_GITHUB_ADMIN_TOKEN"


class G5ClosureError(RuntimeError):
    """Raised when G5 external-control orchestration cannot complete safely."""


def _token_present() -> bool:
    return bool(os.environ.get(TOKEN_ENV, "").strip())


def _run(script: Path, action: str) -> None:
    command = [sys.executable, str(script), action]
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise G5ClosureError(f"{script.name} {action} failed with exit code {result.returncode}")


def check_controls() -> None:
    """Verify both GitHub server-side controls without mutating them."""
    _run(BRANCH_SCRIPT, "check")
    _run(IMMUTABILITY_SCRIPT, "check")


def apply_controls() -> None:
    """Apply and verify both server-side G5 controls."""
    _run(BRANCH_SCRIPT, "apply")
    _run(IMMUTABILITY_SCRIPT, "apply")
    check_controls()


def promote_statuses() -> None:
    """Promote repository evidence only after both live controls already pass."""
    check_controls()
    _run(BRANCH_SCRIPT, "promote-status")
    _run(IMMUTABILITY_SCRIPT, "promote-status")


def close_controls() -> None:
    """Apply, verify and promote both G5 controls without creating a release."""
    apply_controls()
    promote_statuses()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("check", "apply", "promote-status", "close"),
        help=(
            "Verify controls, apply them, promote evidence, or perform the full "
            "apply+verify+promote closure."
        ),
    )
    args = parser.parse_args(argv)

    if not _token_present():
        print(
            f"G5 external closure: FAIL: {TOKEN_ENV} is required; "
            "use a short-lived fine-grained token with repository Administration access",
            file=sys.stderr,
        )
        return 2

    try:
        if args.action == "check":
            check_controls()
        elif args.action == "apply":
            apply_controls()
        elif args.action == "promote-status":
            promote_statuses()
        else:
            close_controls()
    except G5ClosureError as exc:
        print(f"G5 external closure: FAIL: {exc}", file=sys.stderr)
        return 2

    print("G5 external closure: PASS")
    print("Release/tag/publication side effects: none")
    if args.action in {"promote-status", "close"}:
        print("Next: commit the evidence changes through a normal pull request.")
        print("Then rerun the exact release/0.7.0 stable candidate head.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
