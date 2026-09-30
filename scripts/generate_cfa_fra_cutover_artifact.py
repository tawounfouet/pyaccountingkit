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
    GeneratedCutoverArtifact,
    LegacyIdentityLink,
    LegacyIdentityMap,
    MigrationRouting,
    RegulatoryAuthorityObservation,
    RegulatoryAuthorityResolution,
    generate_legacy_identity_artifact,
    generate_regulatory_authority_artifact,
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


def _string(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise CutoverArtifactGenerationError(f"{field} must be a non-empty string")
    return value


def _integer(payload: Mapping[str, object], field: str) -> int:
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise CutoverArtifactGenerationError(f"{field} must be an integer")
    return value


def _boolean(payload: Mapping[str, object], field: str) -> bool:
    value = payload.get(field)
    if not isinstance(value, bool):
        raise CutoverArtifactGenerationError(f"{field} must be boolean")
    return value


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise CutoverArtifactGenerationError(f"{field} must be a JSON object")
    return cast(Mapping[str, object], value)


def _identity_source(payload: Mapping[str, object]) -> GeneratedCutoverArtifact:
    raw_links = payload.get("links")
    if not isinstance(raw_links, list):
        raise CutoverArtifactGenerationError("links must be a JSON array")

    links: list[LegacyIdentityLink] = []
    for index, raw in enumerate(raw_links):
        item = _mapping(raw, f"links[{index}]")
        checksum = item.get("source_checksum")
        if checksum is not None and not isinstance(checksum, str):
            raise CutoverArtifactGenerationError(
                f"links[{index}].source_checksum must be a string"
            )
        links.append(
            LegacyIdentityLink(
                legacy_type=_string(item, "legacy_type"),
                legacy_id=_string(item, "legacy_id"),
                target_type=_string(item, "target_type"),
                target_id=_string(item, "target_id"),
                source=_string(item, "source"),
                source_checksum=checksum,
            )
        )

    return generate_legacy_identity_artifact(
        consumer=_string(payload, "consumer"),
        generated_at=_string(payload, "generated_at"),
        identities=LegacyIdentityMap(tuple(links)),
        expected_legacy_records=_integer(payload, "expected_legacy_records"),
    )


def _regulatory_source(payload: Mapping[str, object]) -> GeneratedCutoverArtifact:
    provider = _mapping(payload.get("provider"), "provider")
    raw_resolutions = payload.get("sample_resolutions")
    if not isinstance(raw_resolutions, list):
        raise CutoverArtifactGenerationError("sample_resolutions must be a JSON array")

    resolutions = tuple(
        RegulatoryAuthorityResolution(
            standard_id=_string(_mapping(raw, f"sample_resolutions[{index}]"), "standard_id"),
            edition=_string(_mapping(raw, f"sample_resolutions[{index}]"), "edition"),
            reference_key=_string(
                _mapping(raw, f"sample_resolutions[{index}]"),
                "reference_key",
            ),
            target_reference_id=_string(
                _mapping(raw, f"sample_resolutions[{index}]"),
                "target_reference_id",
            ),
        )
        for index, raw in enumerate(raw_resolutions)
    )

    routing_profile = _string(payload, "routing_profile")
    routing = (
        MigrationRouting.target_only()
        if routing_profile == "target_only"
        else MigrationRouting()
    )

    return generate_regulatory_authority_artifact(
        consumer=_string(payload, "consumer"),
        observed_at=_string(payload, "observed_at"),
        observation=RegulatoryAuthorityObservation(
            provider_name=_string(provider, "name"),
            provider_version=_string(provider, "version"),
            routing=routing,
            local_framework_account_authority=_boolean(
                payload,
                "local_framework_account_authority",
            ),
            local_seed_commands_authoritative=_boolean(
                payload,
                "local_seed_commands_authoritative",
            ),
            effective_plan_delegated=_boolean(payload, "effective_plan_delegated"),
            resolutions=resolutions,
        ),
    )


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

    source = _load(args.source)
    generated = (
        _identity_source(source)
        if args.key == "legacy_identities"
        else _regulatory_source(source)
    )
    payload = json.dumps(generation_payload(generated), indent=2, sort_keys=True) + "\n"
    print(payload, end="")

    if not args.write:
        print("Dry-run only: artifact was not materialized")
        return 0

    target = _write_validated(
        key=cast(CutoverArtifactKey, args.key),
        payload=payload,
        artifact_root=args.artifact_root.resolve(),
        artifact=args.artifact,
        overwrite=args.overwrite,
    )
    print(f"Generated and validated: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
