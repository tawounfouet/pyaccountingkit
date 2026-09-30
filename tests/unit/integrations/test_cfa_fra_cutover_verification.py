"""LOT-26 tests for cryptographic cutover artifact verification."""

from __future__ import annotations

import hashlib

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    CutoverArtifactVerificationError,
    CutoverEvidenceStatus,
    ExternalCutoverEvidence,
    LiveCutoverEvidence,
    verify_external_cutover_evidence,
    verify_live_cutover_evidence,
)


def _passing(*, artifact: str, payload: bytes) -> ExternalCutoverEvidence:
    return ExternalCutoverEvidence(
        status=CutoverEvidenceStatus.PASS,
        source="live-consumer-cutover",
        artifact=artifact,
        sha256=hashlib.sha256(payload).hexdigest(),
        observed_at="2026-09-30T12:00:00Z",
        producer="cfa-fra-cutover-pipeline",
    )


def _blocked() -> ExternalCutoverEvidence:
    return ExternalCutoverEvidence(
        status=CutoverEvidenceStatus.BLOCKED,
        source="live-consumer-cutover",
        reason="live proof not available yet",
    )


def test_blocked_evidence_requires_no_artifact_io(tmp_path) -> None:
    verified = verify_external_cutover_evidence(
        _blocked(),
        artifact_root=tmp_path,
    )

    assert verified.verified is False
    assert verified.actual_sha256 is None
    assert verified.green is False


def test_passing_evidence_requires_real_matching_artifact(tmp_path) -> None:
    payload = b'{"legacy_id":"42","target_id":"entry-42"}\n'
    artifact = tmp_path / "identity-migration.json"
    artifact.write_bytes(payload)

    verified = verify_external_cutover_evidence(
        _passing(artifact=artifact.name, payload=payload),
        artifact_root=tmp_path,
    )

    assert verified.verified is True
    assert verified.actual_sha256 == hashlib.sha256(payload).hexdigest()
    assert verified.green is True


def test_missing_artifact_fails_closed(tmp_path) -> None:
    with pytest.raises(CutoverArtifactVerificationError):
        verify_external_cutover_evidence(
            _passing(artifact="missing.json", payload=b"expected"),
            artifact_root=tmp_path,
        )


def test_checksum_mismatch_fails_closed(tmp_path) -> None:
    artifact = tmp_path / "authority.json"
    artifact.write_bytes(b"unexpected")

    with pytest.raises(CutoverArtifactVerificationError):
        verify_external_cutover_evidence(
            _passing(artifact=artifact.name, payload=b"expected"),
            artifact_root=tmp_path,
        )


@pytest.mark.parametrize(
    "artifact",
    [
        "../outside.json",
        "/tmp/outside.json",
        "nested/../../outside.json",
    ],
)
def test_artifact_path_traversal_is_rejected(tmp_path, artifact: str) -> None:
    with pytest.raises(CutoverArtifactVerificationError):
        verify_external_cutover_evidence(
            _passing(artifact=artifact, payload=b"expected"),
            artifact_root=tmp_path,
        )


def test_live_evidence_is_green_only_after_both_artifacts_verify(tmp_path) -> None:
    identity_payload = b'{"identity":"verified"}\n'
    authority_payload = b'{"authority":"provider"}\n'
    (tmp_path / "identities.json").write_bytes(identity_payload)
    (tmp_path / "authority.json").write_bytes(authority_payload)

    verified = verify_live_cutover_evidence(
        LiveCutoverEvidence(
            legacy_identities=_passing(
                artifact="identities.json",
                payload=identity_payload,
            ),
            regulatory_authority=_passing(
                artifact="authority.json",
                payload=authority_payload,
            ),
        ),
        artifact_root=tmp_path,
    )

    assert verified.identities_traceable is True
    assert verified.regulatory_authority_replaced is True
