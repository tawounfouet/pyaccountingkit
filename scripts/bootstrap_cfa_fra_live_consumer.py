#!/usr/bin/env python3
"""Plan or materialize a standalone CFA FRA consumer from the frozen Sprint-7 oracle."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from pyaccountingkit.integrations.cfa_fra import (
    DEFAULT_FRAMEWORK_REQUIREMENT,
    ConsumerBootstrapError,
    apply_live_consumer_bootstrap,
    consumer_bootstrap_manifest,
    plan_live_consumer_bootstrap,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "resources" / "cfa_fra_django_mvp_sprint_7"


def _oracle_tree_sha() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD:resources/cfa_fra_django_mvp_sprint_7"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ConsumerBootstrapError(
            "cannot verify frozen oracle tree SHA from the current Git checkout"
        )
    return completed.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument(
        "--framework-requirement",
        default=DEFAULT_FRAMEWORK_REQUIREMENT,
    )
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    plan = plan_live_consumer_bootstrap(
        SOURCE,
        source_tree_sha=_oracle_tree_sha(),
        framework_requirement=args.framework_requirement,
    )
    preview = {
        "mode": "WRITE" if args.write else "DRY_RUN",
        "destination": str(args.destination),
        "source_file_count": plan.source_file_count,
        **consumer_bootstrap_manifest(plan),
    }
    print(json.dumps(preview, indent=2, sort_keys=True))

    if not args.write:
        print("CFA FRA standalone consumer bootstrap: DRY_RUN")
        return 0

    result = apply_live_consumer_bootstrap(
        SOURCE,
        args.destination,
        plan,
        overwrite=args.overwrite,
    )
    print(f"Consumer seed materialized: {result.destination}")
    print(f"Bootstrap manifest: {result.manifest_path}")
    print("Canonical live consumer binding remains UNBOUND until this seed is published.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
