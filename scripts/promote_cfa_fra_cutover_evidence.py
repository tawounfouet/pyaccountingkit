#!/usr/bin/env python3
"""Promote one CFA FRA live cutover proof from BLOCKED to verified PASS."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from pyaccountingkit.integrations.cfa_fra import promote_cutover_evidence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "tests" / "consumer" / "cfa_fra" / "RETIREMENT_EVIDENCE.json"


def _load(path: Path) -> Mapping[str, object]:
    return cast(Mapping[str, object], json.loads(path.read_text(encoding="utf-8")))


def _artifact_root(manifest: Mapping[str, object]) -> Path:
    raw_policy = manifest.get("artifact_policy")
    if not isinstance(raw_policy, dict):
        raise ValueError("retirement manifest must define artifact_policy")
    raw_root = raw_policy.get("root")
    if not isinstance(raw_root, str) or not raw_root.strip():
        raise ValueError("artifact_policy.root must be a non-empty string")

    root = (ROOT / raw_root).resolve()
    try:
        root.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("artifact_policy.root must remain inside the repository") from exc
    if not root.is_dir():
        raise ValueError("artifact_policy.root must exist")
    return root


def _write_atomic(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "key",
        choices=("consumer_e2e", "legacy_identities", "regulatory_authority"),
    )
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--producer", required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Persist the promoted manifest. Without this flag the command is a dry-run.",
    )
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = _load(manifest_path)
    artifact_root = _artifact_root(manifest)
    result = promote_cutover_evidence(
        manifest,
        key=args.key,
        artifact_root=artifact_root,
        artifact=args.artifact,
        source=args.source,
        observed_at=args.observed_at,
        producer=args.producer,
    )

    payload = json.dumps(result.manifest, indent=2, sort_keys=False) + "\n"
    print(payload, end="")
    print(f"Promoted evidence: {result.key}")
    print(f"Computed SHA-256: {result.evidence.sha256}")
    print(f"Removed blocker: {result.removed_blocker}")

    if args.write:
        _write_atomic(manifest_path, payload)
        print(f"Manifest updated atomically: {manifest_path}")
    else:
        print("Dry-run only: manifest was not modified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
