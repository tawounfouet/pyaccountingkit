"""Controlled promotion of verified CFA FRA live cutover evidence."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from pyaccountingkit.integrations.cfa_fra.cutover_artifact_schema import (
    LEGACY_IDENTITIES_SCHEMA,
    REGULATORY_AUTHORITY_SCHEMA,
    CutoverArtifactKey,
    parse_cutover_artifact,
)
from pyaccountingkit.integrations.cfa_fra.cutover_evidence import (
    CutoverEvidenceStatus,
    ExternalCutoverEvidence,
    LiveCutoverEvidence,
)
from pyaccountingkit.integrations.cfa_fra.cutover_verification import (
    attest_external_cutover_artifact,
    resolve_cutover_artifact_path,
    verify_live_cutover_evidence,
)

CutoverEvidenceKey = CutoverArtifactKey

_BLOCKERS: dict[CutoverEvidenceKey, str] = {
    "legacy_identities": "evidence:legacy-identities",
    "regulatory_authority": "evidence:regulatory-authority",
}


@dataclass(frozen=True, slots=True)
class CutoverEvidencePromotion:
    """Result of one controlled external-evidence promotion."""

    key: CutoverEvidenceKey
    evidence: ExternalCutoverEvidence
    removed_blocker: str
    manifest: dict[str, object]


def _record(evidence: ExternalCutoverEvidence) -> dict[str, object]:
    payload = asdict(evidence)
    payload["status"] = evidence.status.value
    return {key: value for key, value in payload.items() if value is not None}


def promote_cutover_evidence(
    manifest: Mapping[str, object],
    *,
    key: CutoverEvidenceKey,
    artifact_root: Path,
    artifact: str,
    source: str,
    observed_at: str,
    producer: str,
) -> CutoverEvidencePromotion:
    """Promote one blocked proof to PASS using a digest derived from real bytes."""
    if manifest.get("schema_version") != "4":
        raise ValueError("cutover evidence promotion requires schema_version='4'")
    if manifest.get("routing_profile") != "target_only":
        raise ValueError("cutover evidence promotion requires target_only routing")

    raw_policy = manifest.get("artifact_policy")
    if not isinstance(raw_policy, dict):
        raise ValueError("cutover evidence promotion requires artifact_policy")
    policy = cast(Mapping[str, object], raw_policy)
    if policy.get("content_schema_verified") is not True:
        raise ValueError("cutover evidence promotion requires content-schema verification")
    expected_schemas = {
        "legacy_identities": LEGACY_IDENTITIES_SCHEMA,
        "regulatory_authority": REGULATORY_AUTHORITY_SCHEMA,
    }
    if policy.get("schemas") != expected_schemas:
        raise ValueError("cutover evidence promotion requires qualified artifact schemas")

    consumer = manifest.get("consumer")
    if not isinstance(consumer, str) or not consumer.strip():
        raise ValueError("cutover evidence promotion requires a consumer identity")

    raw_external = manifest.get("external_evidence")
    if not isinstance(raw_external, dict):
        raise ValueError("cutover evidence manifest must define external_evidence")
    external = cast(Mapping[str, object], raw_external)

    current = external.get(key)
    if not isinstance(current, dict):
        raise ValueError(f"cutover evidence record {key!r} is missing")
    current_evidence = ExternalCutoverEvidence.from_mapping(cast(Mapping[str, object], current))
    if current_evidence.status is CutoverEvidenceStatus.PASS:
        raise ValueError(f"cutover evidence record {key!r} is already PASS")

    artifact_path = resolve_cutover_artifact_path(artifact_root, artifact)
    parsed_artifact = parse_cutover_artifact(key, artifact_path)
    if parsed_artifact.consumer != consumer:
        raise ValueError(
            "cutover artifact consumer must match the retirement evidence consumer"
        )

    evidence = attest_external_cutover_artifact(
        key=key,
        artifact=artifact,
        artifact_root=artifact_root,
        source=source,
        observed_at=observed_at,
        producer=producer,
    )

    promoted = deepcopy(dict(manifest))
    promoted_external = cast(dict[str, object], promoted["external_evidence"])
    promoted_external[key] = _record(evidence)

    raw_expected = promoted.get("expected_blockers")
    if not isinstance(raw_expected, list) or not all(
        isinstance(item, str) for item in raw_expected
    ):
        raise ValueError("cutover evidence expected_blockers must be a string list")

    blocker = _BLOCKERS[key]
    if blocker not in raw_expected:
        raise ValueError(f"expected blocker {blocker!r} is missing before promotion")
    promoted["expected_blockers"] = [
        item for item in cast(list[str], raw_expected) if item != blocker
    ]

    live = LiveCutoverEvidence.from_mapping(cast(Mapping[str, object], promoted_external))
    verified = verify_live_cutover_evidence(live, artifact_root=artifact_root)
    if key == "legacy_identities" and not verified.identities_traceable:
        raise RuntimeError("promoted identity evidence did not verify")
    if key == "regulatory_authority" and not verified.regulatory_authority_replaced:
        raise RuntimeError("promoted regulatory-authority evidence did not verify")

    return CutoverEvidencePromotion(
        key=key,
        evidence=evidence,
        removed_blocker=blocker,
        manifest=promoted,
    )


__all__ = [
    "CutoverEvidenceKey",
    "CutoverEvidencePromotion",
    "promote_cutover_evidence",
]
