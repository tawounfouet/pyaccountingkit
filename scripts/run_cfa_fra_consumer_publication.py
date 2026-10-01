#!/usr/bin/env python3
"""Plan/apply the verified publication handoff for the standalone CFA FRA consumer."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from pyaccountingkit.integrations.cfa_fra import (
    ConsumerPublicationError,
    ConsumerRepositoryObservation,
    apply_consumer_publication_plan,
    plan_consumer_publication,
    publication_plan_payload,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "resources" / "cfa_fra_django_mvp_sprint_7"
DEFAULT_BINDING = ROOT / "tests" / "consumer" / "cfa_fra" / "CONSUMER_BINDING.json"


def _load(path: Path) -> dict[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConsumerPublicationError(f"{path} must contain a JSON object")
    return raw


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
        raise ConsumerPublicationError(detail)
    return completed.stdout.strip()


def _observe(root: Path) -> ConsumerRepositoryObservation:
    resolved = root.resolve()
    if not resolved.is_dir():
        raise ConsumerPublicationError("published consumer root does not exist")
    top_level = Path(_git(resolved, "rev-parse", "--show-toplevel")).resolve()
    manifest = _load(resolved / "PYACCOUNTINGKIT_CONSUMER_BOOTSTRAP.json")
    return ConsumerRepositoryObservation(
        repository_is_top_level=top_level == resolved,
        worktree_clean=not bool(_git(resolved, "status", "--porcelain")),
        revision_sha=_git(resolved, "rev-parse", "HEAD"),
        current_branch=_git(resolved, "branch", "--show-current"),
        origin=_git(resolved, "remote", "get-url", "origin"),
        bootstrap_manifest=manifest,
    )


def _atomic_write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", type=Path, default=DEFAULT_BINDING)
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan")
    plan.add_argument("--consumer-root", type=Path, required=True)
    plan.add_argument("--repository", required=True)
    plan.add_argument("--default-branch", default="main")
    plan.add_argument("--environment", default="production")
    plan.add_argument("--observed-at", required=True)
    plan.add_argument("--producer", required=True)
    plan.add_argument("--plan-output", type=Path, required=True)

    apply = sub.add_parser("apply")
    apply.add_argument("--consumer-root", type=Path, required=True)
    apply.add_argument("--plan", type=Path, required=True)
    apply.add_argument("--write", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    current = _load(args.binding)
    observation = _observe(args.consumer_root)

    if args.command == "plan":
        plan = plan_consumer_publication(
            observation,
            SOURCE,
            current,
            repository=args.repository,
            default_branch=args.default_branch,
            environment=args.environment,
            observed_at=args.observed_at,
            producer=args.producer,
        )
        payload = publication_plan_payload(plan)
        _atomic_write(args.plan_output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        print("CFA FRA consumer publication handoff: PLAN READY")
        return 0

    plan_payload = _load(args.plan)
    candidate = apply_consumer_publication_plan(
        plan_payload,
        observation,
        SOURCE,
        current,
    )
    print(json.dumps(candidate, indent=2, sort_keys=True))
    if not args.write:
        print("CFA FRA consumer publication handoff: APPLY DRY_RUN")
        return 0

    _atomic_write(args.binding, candidate)
    print(f"CFA FRA consumer publication handoff: BOUND -> {args.binding}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
