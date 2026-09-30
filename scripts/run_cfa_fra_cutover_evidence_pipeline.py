#!/usr/bin/env python3
"""Plan or apply the CFA FRA cutover evidence pipeline."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from pyaccountingkit.integrations.cfa_fra import (
    CutoverArtifactKey,
    apply_cutover_evidence_pipeline,
    pipeline_plan_from_mapping,
    pipeline_plan_payload,
    plan_cutover_evidence_pipeline,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "tests" / "consumer" / "cfa_fra" / "RETIREMENT_EVIDENCE.json"


def _load_mapping(path: Path) -> Mapping[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(Mapping[str, object], raw)


def _artifact_root(manifest: Mapping[str, object]) -> Path:
    raw_policy = manifest.get("artifact_policy")
    if not isinstance(raw_policy, dict):
        raise ValueError("retirement manifest must define artifact_policy")
    raw_root = raw_policy.get("root")
    if not isinstance(raw_root, str) or not raw_root.strip():
        raise ValueError("artifact_policy.root must be a non-empty string")
    root = (ROOT / raw_root).resolve()
    root.relative_to(ROOT.resolve())
    return root


def _plan(args: argparse.Namespace) -> int:
    manifest = _load_mapping(args.manifest)
    source = _load_mapping(args.source)
    artifact_root = (
        args.artifact_root.resolve() if args.artifact_root is not None else _artifact_root(manifest)
    )
    plan = plan_cutover_evidence_pipeline(
        manifest,
        key=cast(CutoverArtifactKey, args.key),
        source_observation=source,
        artifact=args.artifact,
        evidence_source=args.evidence_source,
        observed_at=args.observed_at,
        producer=args.producer,
        existing_artifact_root=artifact_root,
    )
    payload = json.dumps(pipeline_plan_payload(plan), indent=2, sort_keys=False) + "\n"
    print(payload, end="")
    if args.plan_output is not None:
        args.plan_output.write_text(payload, encoding="utf-8")
        print(f"Plan written: {args.plan_output}")
    else:
        print("Dry-run only: no durable state was modified")
    return 0


def _apply(args: argparse.Namespace) -> int:
    manifest_path = args.manifest.resolve()
    manifest = _load_mapping(manifest_path)
    plan = pipeline_plan_from_mapping(_load_mapping(args.plan))
    artifact_root = (
        args.artifact_root.resolve() if args.artifact_root is not None else _artifact_root(manifest)
    )
    promotion = apply_cutover_evidence_pipeline(
        plan,
        current_manifest=manifest,
        manifest_path=manifest_path,
        artifact_root=artifact_root,
        overwrite_artifact=args.overwrite_artifact,
    )
    print(f"Applied evidence plan: {plan.key}")
    print(f"Artifact: {plan.artifact}")
    print(f"SHA-256: {promotion.evidence.sha256}")
    print(f"Removed blocker: {promotion.removed_blocker}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--artifact-root", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan")
    plan.add_argument("key", choices=("consumer_e2e", "legacy_identities", "regulatory_authority"))
    plan.add_argument("--source", type=Path, required=True)
    plan.add_argument("--artifact", required=True)
    plan.add_argument("--evidence-source", required=True)
    plan.add_argument("--observed-at", required=True)
    plan.add_argument("--producer", required=True)
    plan.add_argument("--plan-output", type=Path)
    plan.set_defaults(handler=_plan)

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--plan", type=Path, required=True)
    apply_parser.add_argument("--overwrite-artifact", action="store_true")
    apply_parser.set_defaults(handler=_apply)

    args = parser.parse_args()
    return cast(int, args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
