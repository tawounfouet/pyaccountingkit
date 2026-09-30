#!/usr/bin/env python3
"""Generate CFA FRA cutover artifacts from structured source observations."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from pyaccountingkit.integrations.cfa_fra import (
    CutoverArtifactGenerationError,
    CutoverArtifactKey,
    generate_cutover_artifact_from_mapping,
    generation_payload,
    parse_cutover_artifact,
    resolve_cutover_artifact_path,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_ROOT = ROOT / "tests" / "consumer" / "cfa_fra" / "live_evidence"


def _load(path: Path) -> Mapping[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise CutoverArtifactGenerationError("generation source must be a JSON object")
    return cast(Mapping[str, object], raw)


def _write_validated(
    *,
    key: CutoverArtifactKey,
    payload: str,
    artifact_root: Path,
    artifact: str,
    overwrite: bool,
) -> Path:
    target = resolve_cutover_artifact_path(artifact_root, artifact)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        raise CutoverArtifactGenerationError(
            f"cutover artifact already exists: {artifact}; use --overwrite explicitly"
        )

    descriptor, temporary = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        parse_cutover_artifact(key, temporary_path)
        temporary_path.replace(target)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "key",
        choices=("legacy_identities", "regulatory_authority"),
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Materialize the generated artifact. Without this flag the command is a dry-run.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow explicit replacement of an existing generated artifact.",
    )
    args = parser.parse_args()

    key = cast(CutoverArtifactKey, args.key)
    generated = generate_cutover_artifact_from_mapping(key, _load(args.source))
    payload = json.dumps(generation_payload(generated), indent=2, sort_keys=True) + "\n"
    print(payload, end="")

    if not args.write:
        print("Dry-run only: artifact was not materialized")
        return 0

    target = _write_validated(
        key=key,
        payload=payload,
        artifact_root=args.artifact_root.resolve(),
        artifact=args.artifact,
        overwrite=args.overwrite,
    )
    print(f"Generated and validated: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
