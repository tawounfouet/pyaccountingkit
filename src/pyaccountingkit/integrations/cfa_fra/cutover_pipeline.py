"""Plan and apply CFA FRA cutover evidence as one controlled pipeline."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from pyaccountingkit.integrations.cfa_fra.cutover_artifact_schema import (
    CutoverArtifactKey,
    parse_cutover_artifact,
)
from pyaccountingkit.integrations.cfa_fra.cutover_generation import (
    GeneratedCutoverArtifact,
    generate_cutover_artifact_from_mapping,
    generation_payload,
)
from pyaccountingkit.integrations.cfa_fra.cutover_promotion import (
    CutoverEvidencePromotion,
    promote_cutover_evidence,
)
from pyaccountingkit.integrations.cfa_fra.cutover_verification import (
    resolve_cutover_artifact_path,
)


class CutoverEvidencePipelineError(RuntimeError):
    """Raised when a planned cutover evidence transition cannot be applied safely."""


@dataclass(frozen=True, slots=True)
class CutoverEvidencePipelinePlan:
    """Immutable dry-run plan for one evidence transition."""

    key: CutoverArtifactKey
    artifact: str
    artifact_payload: str
    artifact_sha256: str
    source_manifest_sha256: str
    removed_blocker: str
    candidate_manifest: dict[str, object]


def _canonical_json(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def manifest_sha256(payload: Mapping[str, object]) -> str:
    """Fingerprint a manifest semantically, independent of pretty-print formatting."""
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _artifact_payload(generated: GeneratedCutoverArtifact) -> str:
    return json.dumps(generation_payload(generated), indent=2, sort_keys=True) + "\n"


def _simulate_promotion(
    manifest: Mapping[str, object],
    *,
    key: CutoverArtifactKey,
    artifact: str,
    payload: str,
    source: str,
    observed_at: str,
    producer: str,
) -> CutoverEvidencePromotion:
    with TemporaryDirectory(prefix="pyaccountingkit-cutover-plan-") as directory:
        root = Path(directory)
        candidate = resolve_cutover_artifact_path(root, artifact)
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text(payload, encoding="utf-8")
        parse_cutover_artifact(key, candidate)
        return promote_cutover_evidence(
            manifest,
            key=key,
            artifact_root=root,
            artifact=artifact,
            source=source,
            observed_at=observed_at,
            producer=producer,
        )


def plan_cutover_evidence_pipeline(
    manifest: Mapping[str, object],
    *,
    key: CutoverArtifactKey,
    source_observation: Mapping[str, object],
    artifact: str,
    evidence_source: str,
    observed_at: str,
    producer: str,
) -> CutoverEvidencePipelinePlan:
    """Generate, validate and simulate promotion without mutating durable state."""
    generated = generate_cutover_artifact_from_mapping(key, source_observation)
    payload = _artifact_payload(generated)
    promotion = _simulate_promotion(
        manifest,
        key=key,
        artifact=artifact,
        payload=payload,
        source=evidence_source,
        observed_at=observed_at,
        producer=producer,
    )
    return CutoverEvidencePipelinePlan(
        key=key,
        artifact=artifact,
        artifact_payload=payload,
        artifact_sha256=promotion.evidence.sha256 or "",
        source_manifest_sha256=manifest_sha256(manifest),
        removed_blocker=promotion.removed_blocker,
        candidate_manifest=promotion.manifest,
    )


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


def apply_cutover_evidence_pipeline(
    plan: CutoverEvidencePipelinePlan,
    *,
    current_manifest: Mapping[str, object],
    manifest_path: Path,
    artifact_root: Path,
    evidence_source: str,
    observed_at: str,
    producer: str,
    overwrite_artifact: bool = False,
) -> CutoverEvidencePromotion:
    """Apply a previously reviewed plan with stale-plan and overwrite protection."""
    if manifest_sha256(current_manifest) != plan.source_manifest_sha256:
        raise CutoverEvidencePipelineError(
            "retirement manifest changed after planning; regenerate the cutover plan"
        )

    target = resolve_cutover_artifact_path(artifact_root, plan.artifact)
    if target.exists() and not overwrite_artifact:
        raise CutoverEvidencePipelineError(
            f"cutover artifact already exists: {plan.artifact}; "
            "explicit overwrite is required"
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    parse_payload = json.loads(plan.artifact_payload)
    if not isinstance(parse_payload, dict):
        raise CutoverEvidencePipelineError("planned artifact payload must be a JSON object")

    descriptor, temporary = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(plan.artifact_payload)
            handle.flush()
            os.fsync(handle.fileno())
        parse_cutover_artifact(plan.key, temporary_path)

        promotion = promote_cutover_evidence(
            current_manifest,
            key=plan.key,
            artifact_root=temporary_path.parent,
            artifact=temporary_path.name,
            source=evidence_source,
            observed_at=observed_at,
            producer=producer,
        )

        planned_record = plan.candidate_manifest["external_evidence"]
        applied_record = promotion.manifest["external_evidence"]
        if planned_record != applied_record:
            raise CutoverEvidencePipelineError(
                "promotion result differs from reviewed dry-run plan"
            )
        if promotion.evidence.sha256 != plan.artifact_sha256:
            raise CutoverEvidencePipelineError(
                "generated artifact digest differs from reviewed dry-run plan"
            )

        temporary_path.replace(target)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    manifest_payload = json.dumps(
        promotion.manifest,
        indent=2,
        sort_keys=False,
    ) + "\n"
    _write_atomic(manifest_path, manifest_payload)
    return promotion


__all__ = [
    "CutoverEvidencePipelineError",
    "CutoverEvidencePipelinePlan",
    "apply_cutover_evidence_pipeline",
    "manifest_sha256",
    "plan_cutover_evidence_pipeline",
]
