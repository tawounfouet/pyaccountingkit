#!/usr/bin/env python3
"""Validate the canonical CFA FRA live-consumer repository binding."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyaccountingkit.integrations.cfa_fra import (
    LiveConsumerBindingError,
    parse_live_consumer_binding_state,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BINDING = ROOT / "tests" / "consumer" / "cfa_fra" / "CONSUMER_BINDING.json"
RETIREMENT_MANIFEST = ROOT / "tests" / "consumer" / "cfa_fra" / "RETIREMENT_EVIDENCE.json"
RETIREMENT_INVENTORY = ROOT / "tests" / "consumer" / "cfa_fra" / "LEGACY_RETIREMENT_INVENTORY.json"


def _load(path: Path) -> dict[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise LiveConsumerBindingError(f"{path} must contain a JSON object")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binding", type=Path, default=DEFAULT_BINDING)
    parser.add_argument("--require-bound", action="store_true")
    parser.add_argument("--expected-revision")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    state = parse_live_consumer_binding_state(_load(args.binding))
    retirement_manifest = _load(RETIREMENT_MANIFEST)
    inventory = _load(RETIREMENT_INVENTORY)

    if state.consumer != retirement_manifest.get("consumer"):
        raise LiveConsumerBindingError(
            "canonical consumer binding identity must match retirement manifest consumer"
        )

    bound = state.bound
    report: dict[str, object] = {
        "consumer": state.consumer,
        "bound": bound,
        "status": state.status,
    }

    if state.binding is not None:
        oracle = inventory.get("oracle")
        if not isinstance(oracle, dict):
            raise LiveConsumerBindingError("retirement inventory oracle is missing")
        oracle_tree_sha = oracle.get("tree_sha")
        if state.binding.revision_sha == oracle_tree_sha:
            raise LiveConsumerBindingError(
                "live consumer revision may not equal the frozen oracle tree SHA"
            )
        if (
            args.expected_revision is not None
            and state.binding.revision_sha != args.expected_revision
        ):
            raise LiveConsumerBindingError(
                "live consumer binding revision does not match expected retirement revision"
            )
        report.update(
            {
                "repository": state.binding.repository,
                "repository_url": state.binding.repository_url,
                "default_branch": state.binding.default_branch,
                "revision_sha": state.binding.revision_sha,
                "environment": state.binding.environment,
                "observed_at": state.binding.observed_at,
                "producer": state.binding.producer,
                "binding_sha256": state.binding.binding_sha256,
            }
        )
    else:
        report["reason"] = state.reason

    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")

    print(payload, end="")
    if args.require_bound and not bound:
        raise LiveConsumerBindingError("live CFA FRA consumer repository remains UNBOUND")
    print(f"CFA FRA live consumer repository binding: {'BOUND' if bound else 'UNBOUND'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
