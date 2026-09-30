"""Plan and apply CFA FRA cutover evidence as one controlled pipeline."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from pyaccountingkit.integrations.cfa_fra.cutover_artifact_schema import (
    CutoverArtifactKey,
    parse_cutover_artifact,
)
from pyaccountingkit.integrations.cfa_fra.cutover_evidence import (
    CutoverEvidenceStatus,
    ExternalCutoverEvidence,
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
    evidence_source: str
    observed_at: str
    producer: str
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


def _stage_existing_pass_artifacts(
    manifest: Mapping[str, object],
    *,
    source_root: Path,
    staging_root: Path,
) -> None:
    raw_external = manifest.get("external_evidence")
    if not isinstance(raw_external, dict):
        raise CutoverEvidencePipelineError("retirement manifest must define external_evidence")

    for raw in raw_external.values():
        if not isinstance(raw, dict):
            raise CutoverEvidencePipelineError("retirement evidence records must be JSON objects")
        evidence = ExternalCutoverEvidence.from_mapping(raw)
        if evidence.status is not CutoverEvidenceStatus.PASS:
            continue
        if evidence.artifact is None:
            raise CutoverEvidencePipelineError("existing PASS evidence must declare an artifact")

        source = resolve_cutover_artifact_path(source_root, evidence.artifact)
        if not source.is_file():
            raise CutoverEvidencePipelineError(
                f"existing PASS artifact is missing: {evidence.artifact}"
            )
        target = resolve_cutover_artifact_path(staging_root, evidence.artifact)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _simulate_promotion(
    manifest: Mapping[str, object],
    *,
    key: CutoverArtifactKey,
    artifact: str,
    payload: str,
    source: str,
    observed_at: str,
    producer: str,
    existing_artifact_root: Path | None,
) -> CutoverEvidencePromotion:
    with TemporaryDirectory(prefix="pyaccountingkit-cutover-plan-") as directory:
        root = Path(directory)
        if existing_artifact_root is not None:
            _stage_existing_pass_artifacts(
                manifest,
                source_root=existing_artifact_root,
                staging_root=root,
            )
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
    existing_artifact_root: Path | None = None,
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
        existing_artifact_root=existing_artifact_root,
    )
    return CutoverEvidencePipelinePlan(
        key=key,
        artifact=artifact,
        artifact_payload=payload,
        artifact_sha256=promotion.evidence.sha256 or "",
        source_manifest_sha256=manifest_sha256(manifest),
        removed_blocker=promotion.removed_blocker,
        evidence_source=evidence_source,
        observed_at=observed_at,
        producer=producer,
        candidate_manifest=promotion.manifest,
    )


def pipeline_plan_payload(plan: CutoverEvidencePipelinePlan) -> dict[str, object]:
    """Serialize one reviewed plan for a separate apply step."""
    return {
        "schema_version": "1",
        "key": plan.key,
        "artifact": plan.artifact,
        "artifact_payload": plan.artifact_payload,
        "artifact_sha256": plan.artifact_sha256,
        "source_manifest_sha256": plan.source_manifest_sha256,
        "removed_blocker": plan.removed_blocker,
        "evidence_source": plan.evidence_source,
        "observed_at": plan.observed_at,
        "producer": plan.producer,
        "candidate_manifest": plan.candidate_manifest,
    }


def pipeline_plan_from_mapping(payload: Mapping[str, object]) -> CutoverEvidencePipelinePlan:
    """Load and validate a serialized pipeline plan."""
    if payload.get("schema_version") != "1":
        raise CutoverEvidencePipelineError("cutover pipeline plan must use schema_version='1'")

    key = payload.get("key")
    if key not in {"legacy_identities", "regulatory_authority"}:
        raise CutoverEvidencePipelineError("cutover pipeline plan has an invalid evidence key")

    string_fields = (
        "artifact",
        "artifact_payload",
        "artifact_sha256",
        "source_manifest_sha256",
        "removed_blocker",
        "evidence_source",
        "observed_at",
        "producer",
    )
    values: dict[str, str] = {}
    for field in string_fields:
        value = payload.get(field)
        if not isinstance(value, str) or not value:
            raise CutoverEvidencePipelineError(
                f"cutover pipeline plan field {field!r} must be a non-empty string"
            )
        values[field] = value

    for field in ("artifact_sha256", "source_manifest_sha256"):
        value = values[field]
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise CutoverEvidencePipelineError(
                f"cutover pipeline plan field {field!r} must be lowercase SHA-256"
            )

    candidate = payload.get("candidate_manifest")
    if not isinstance(candidate, dict):
        raise CutoverEvidencePipelineError(
            "cutover pipeline plan candidate_manifest must be a JSON object"
        )

    return CutoverEvidencePipelinePlan(
        key=key,
        artifact=values["artifact"],
        artifact_payload=values["artifact_payload"],
        artifact_sha256=values["artifact_sha256"],
        source_manifest_sha256=values["source_manifest_sha256"],
        removed_blocker=values["removed_blocker"],
        evidence_source=values["evidence_source"],
        observed_at=values["observed_at"],
        producer=values["producer"],
        candidate_manifest=cast(dict[str, object], candidate),
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
            f"cutover artifact already exists: {plan.artifact}; explicit overwrite is required"
        )

    with TemporaryDirectory(prefix="pyaccountingkit-cutover-apply-") as directory:
        staging_root = Path(directory)
        _stage_existing_pass_artifacts(
            current_manifest,
            source_root=artifact_root,
            staging_root=staging_root,
        )
        staged = resolve_cutover_artifact_path(staging_root, plan.artifact)
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_text(plan.artifact_payload, encoding="utf-8")
        parse_cutover_artifact(plan.key, staged)

        promotion = promote_cutover_evidence(
            current_manifest,
            key=plan.key,
            artifact_root=staging_root,
            artifact=plan.artifact,
            source=plan.evidence_source,
            observed_at=plan.observed_at,
            producer=plan.producer,
        )

    if promotion.manifest != plan.candidate_manifest:
        raise CutoverEvidencePipelineError("promotion result differs from reviewed dry-run plan")
    if promotion.removed_blocker != plan.removed_blocker:
        raise CutoverEvidencePipelineError("removed blocker differs from reviewed dry-run plan")
    if promotion.evidence.sha256 != plan.artifact_sha256:
        raise CutoverEvidencePipelineError(
            "generated artifact digest differs from reviewed dry-run plan"
        )

    _write_atomic(target, plan.artifact_payload)
    parse_cutover_artifact(plan.key, target)

    manifest_payload = (
        json.dumps(
            promotion.manifest,
            indent=2,
            sort_keys=False,
        )
        + "\n"
    )
    _write_atomic(manifest_path, manifest_payload)
    return promotion


__all__ = [
    "CutoverEvidencePipelineError",
    "CutoverEvidencePipelinePlan",
    "apply_cutover_evidence_pipeline",
    "manifest_sha256",
    "pipeline_plan_from_mapping",
    "pipeline_plan_payload",
    "plan_cutover_evidence_pipeline",
]
