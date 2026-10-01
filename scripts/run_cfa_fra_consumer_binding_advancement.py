#!/usr/bin/env python3
"""Plan/apply a verified CFA FRA live-consumer binding revision advancement."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from pyaccountingkit.integrations.cfa_fra import (
    ConsumerBindingAdvancementError,
    ConsumerBindingRevisionObservation,
    ConsumerRepositoryObservation,
    apply_consumer_binding_advancement_plan,
    binding_advancement_plan_payload,
    parse_live_consumer_binding_state,
    plan_consumer_binding_advancement,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "resources" / "cfa_fra_django_mvp_sprint_7"
DEFAULT_BINDING = ROOT / "tests" / "consumer" / "cfa_fra" / "CONSUMER_BINDING.json"


def _load(path: Path) -> dict[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConsumerBindingAdvancementError(f"{path} must contain a JSON object")
    return raw


def _git(root: Path, *args: str, allow_ancestor_false: bool = False) -> tuple[int, str]:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0 and not (allow_ancestor_false and completed.returncode == 1):
        detail = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
        raise ConsumerBindingAdvancementError(detail)
    return completed.returncode, completed.stdout.strip()


def _observe(
    root: Path,
    previous_revision: str,
) -> ConsumerBindingRevisionObservation:
    resolved = root.resolve()
    if not resolved.is_dir():
        raise ConsumerBindingAdvancementError("bound consumer root does not exist")

    _, top_level = _git(resolved, "rev-parse", "--show-toplevel")
    _, status = _git(resolved, "status", "--porcelain")
    _, revision = _git(resolved, "rev-parse", "HEAD")
    _, branch = _git(resolved, "branch", "--show-current")
    _, origin = _git(resolved, "remote", "get-url", "origin")
    ancestor_code, _ = _git(
        resolved,
        "merge-base",
        "--is-ancestor",
        previous_revision,
        revision,
        allow_ancestor_false=True,
    )
    manifest = _load(resolved / "PYACCOUNTINGKIT_CONSUMER_BOOTSTRAP.json")
    repository = ConsumerRepositoryObservation(
        repository_is_top_level=Path(top_level).resolve() == resolved,
        worktree_clean=not bool(status),
        revision_sha=revision,
        current_branch=branch,
        origin=origin,
        bootstrap_manifest=manifest,
    )
    return ConsumerBindingRevisionObservation(
        repository=repository,
        previous_revision_is_ancestor=ancestor_code == 0,
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
    state = parse_live_consumer_binding_state(current)
    if state.binding is None:
        raise ConsumerBindingAdvancementError("canonical consumer binding remains UNBOUND")

    observation = _observe(args.consumer_root, state.binding.revision_sha)

    if args.command == "plan":
        plan = plan_consumer_binding_advancement(
            observation,
            SOURCE,
            current,
            observed_at=args.observed_at,
            producer=args.producer,
        )
        payload = binding_advancement_plan_payload(plan)
        _atomic_write(args.plan_output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        print("CFA FRA consumer binding advancement: PLAN READY")
        return 0

    plan_payload = _load(args.plan)
    candidate = apply_consumer_binding_advancement_plan(
        plan_payload,
        observation,
        SOURCE,
        current,
    )
    print(json.dumps(candidate, indent=2, sort_keys=True))
    if not args.write:
        print("CFA FRA consumer binding advancement: APPLY DRY_RUN")
        return 0

    _atomic_write(args.binding, candidate)
    print(f"CFA FRA consumer binding advancement: BOUND REVISION ADVANCED -> {args.binding}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
