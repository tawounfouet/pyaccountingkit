"""Cryptographic verification for CFA FRA live cutover artifacts."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pyaccountingkit.integrations.cfa_fra.cutover_evidence import (
    CutoverEvidenceStatus,
    ExternalCutoverEvidence,
    LiveCutoverEvidence,
)


class CutoverArtifactVerificationError(RuntimeError):
    """Raised when an attested cutover artifact cannot be verified safely."""


@dataclass(frozen=True, slots=True)
class VerifiedExternalCutoverEvidence:
    """One cutover proof after local artifact verification."""

    evidence: ExternalCutoverEvidence
    verified: bool
    actual_sha256: str | None = None

    @property
    def green(self) -> bool:
        """Return whether this proof is both PASS and cryptographically verified."""
        return self.evidence.status is CutoverEvidenceStatus.PASS and self.verified


@dataclass(frozen=True, slots=True)
class VerifiedLiveCutoverEvidence:
    """Verified external proof set consumed by MIG-13 readiness."""

    legacy_identities: VerifiedExternalCutoverEvidence
    regulatory_authority: VerifiedExternalCutoverEvidence

    @property
    def identities_traceable(self) -> bool:
        return self.legacy_identities.green

    @property
    def regulatory_authority_replaced(self) -> bool:
        return self.regulatory_authority.green


def _safe_artifact_path(root: Path, artifact: str) -> Path:
    candidate = PurePosixPath(artifact)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise CutoverArtifactVerificationError(
            "cutover evidence artifact must be a safe relative path"
        )
    if not candidate.parts:
        raise CutoverArtifactVerificationError("cutover evidence artifact path is empty")

    resolved_root = root.resolve()
    resolved = (resolved_root / Path(*candidate.parts)).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise CutoverArtifactVerificationError(
            "cutover evidence artifact escapes the configured evidence root"
        ) from exc
    return resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def attest_external_cutover_artifact(
    *,
    artifact: str,
    artifact_root: Path,
    source: str,
    observed_at: str,
    producer: str,
) -> ExternalCutoverEvidence:
    """Create a PASS attestation from real artifact bytes, never from a supplied digest."""
    path = _safe_artifact_path(artifact_root, artifact)
    if not path.is_file():
        raise CutoverArtifactVerificationError(
            f"cutover evidence artifact does not exist: {artifact}"
        )

    evidence = ExternalCutoverEvidence(
        status=CutoverEvidenceStatus.PASS,
        source=source,
        artifact=artifact,
        sha256=_sha256_file(path),
        observed_at=observed_at,
        producer=producer,
    )
    verified = verify_external_cutover_evidence(evidence, artifact_root=artifact_root)
    if not verified.green:
        raise CutoverArtifactVerificationError(
            "freshly attested cutover artifact did not verify"
        )
    return evidence


def verify_external_cutover_evidence(
    evidence: ExternalCutoverEvidence,
    *,
    artifact_root: Path,
) -> VerifiedExternalCutoverEvidence:
    """Verify one PASS artifact or preserve an explicit BLOCKED record."""
    if evidence.status is CutoverEvidenceStatus.BLOCKED:
        return VerifiedExternalCutoverEvidence(evidence=evidence, verified=False)

    artifact = evidence.artifact
    expected_sha256 = evidence.sha256
    if artifact is None or expected_sha256 is None:
        raise CutoverArtifactVerificationError(
            "passing cutover evidence is missing artifact coordinates"
        )

    path = _safe_artifact_path(artifact_root, artifact)
    if not path.is_file():
        raise CutoverArtifactVerificationError(
            f"cutover evidence artifact does not exist: {artifact}"
        )

    actual_sha256 = _sha256_file(path)
    if not hmac.compare_digest(actual_sha256, expected_sha256):
        raise CutoverArtifactVerificationError(f"cutover evidence SHA-256 mismatch for {artifact}")

    return VerifiedExternalCutoverEvidence(
        evidence=evidence,
        verified=True,
        actual_sha256=actual_sha256,
    )


def verify_live_cutover_evidence(
    evidence: LiveCutoverEvidence,
    *,
    artifact_root: Path,
) -> VerifiedLiveCutoverEvidence:
    """Verify every live-cutover proof before exposing retirement booleans."""
    return VerifiedLiveCutoverEvidence(
        legacy_identities=verify_external_cutover_evidence(
            evidence.legacy_identities,
            artifact_root=artifact_root,
        ),
        regulatory_authority=verify_external_cutover_evidence(
            evidence.regulatory_authority,
            artifact_root=artifact_root,
        ),
    )


__all__ = [
    "CutoverArtifactVerificationError",
    "attest_external_cutover_artifact",
    "VerifiedExternalCutoverEvidence",
    "VerifiedLiveCutoverEvidence",
    "verify_external_cutover_evidence",
    "verify_live_cutover_evidence",
]
