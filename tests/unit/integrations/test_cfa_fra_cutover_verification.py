"""LOT-26 tests for cryptographic cutover artifact verification."""

from __future__ import annotations

import hashlib
import json

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


def test_live_evidence_is_green_only_after_all_artifacts_verify(tmp_path) -> None:
    consumer_payload = (
        json.dumps(
            {
                "schema": "cfa_fra_consumer_e2e_cutover/v1",
                "kind": "consumer_e2e_cutover",
                "consumer": "CFA FRA",
                "observed_at": "2026-09-30T12:00:00Z",
                "environment": "production",
                "producer": "cfa-fra-live-e2e",
                "routing_profile": "target_only",
                "scenarios": [
                    {
                        "scenario": scenario,
                        "status": "PASS",
                        "source": f"live:{scenario}",
                        "evidence_checksum": "sha256:" + ("a" * 64),
                    }
                    for scenario in [
                        "login",
                        "organization_context",
                        "fec_import",
                        "journal",
                        "ledger",
                        "balance",
                        "financial_statements",
                        "controls",
                        "closing",
                        "exports",
                    ]
                ],
            },
            sort_keys=True,
        )
        + "\n"
    ).encode()
    identity_payload = (
        json.dumps(
            {
                "schema": "cfa_fra_legacy_identity_migration/v1",
                "kind": "legacy_identity_migration",
                "consumer": "CFA FRA",
                "generated_at": "2026-09-30T12:00:00Z",
                "source_system": "CFA_FRA_LEGACY",
                "target_system": "PYACCOUNTINGKIT",
                "summary": {
                    "total_legacy_records": 1,
                    "mapped_records": 1,
                    "unresolved_records": 0,
                },
                "mappings": [
                    {
                        "legacy_type": "JournalEntry",
                        "legacy_id": "legacy-1",
                        "target_type": "JournalEntry",
                        "target_id": "target-1",
                        "source": "CFA_FRA_LEGACY",
                    }
                ],
            },
            sort_keys=True,
        )
        + "\n"
    ).encode()
    authority_payload = (
        json.dumps(
            {
                "schema": "cfa_fra_regulatory_authority_cutover/v1",
                "kind": "regulatory_authority_cutover",
                "consumer": "CFA FRA",
                "observed_at": "2026-09-30T12:00:00Z",
                "provider": {"name": "PyAccountingKit", "version": "0.6.0b16"},
                "routing_profile": "target_only",
                "local_framework_account_authority": False,
                "local_seed_commands_authoritative": False,
                "effective_plan_delegated": True,
                "sample_resolutions": [
                    {
                        "standard_id": "SYSCOHADA",
                        "edition": "2017",
                        "reference_key": "101000",
                        "target_reference_id": "reference-101000",
                    }
                ],
            },
            sort_keys=True,
        )
        + "\n"
    ).encode()
    (tmp_path / "consumer-e2e.json").write_bytes(consumer_payload)
    (tmp_path / "identities.json").write_bytes(identity_payload)
    (tmp_path / "authority.json").write_bytes(authority_payload)

    verified = verify_live_cutover_evidence(
        LiveCutoverEvidence(
            consumer_e2e=_passing(
                artifact="consumer-e2e.json",
                payload=consumer_payload,
            ),
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

    assert verified.consumer_e2e_green is True
    assert verified.identities_traceable is True
    assert verified.regulatory_authority_replaced is True


def test_live_verification_rejects_checksum_valid_but_semantically_wrong_artifact(
    tmp_path,
) -> None:
    payload = b'{"kind":"arbitrary-but-hashed"}\n'
    (tmp_path / "identities.json").write_bytes(payload)

    with pytest.raises(CutoverArtifactVerificationError):
        verify_live_cutover_evidence(
            LiveCutoverEvidence(
                consumer_e2e=_blocked(),
                legacy_identities=_passing(
                    artifact="identities.json",
                    payload=payload,
                ),
                regulatory_authority=_blocked(),
            ),
            artifact_root=tmp_path,
        )
