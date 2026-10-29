"""Deployment configuration must reject unintended privileged SQL credentials."""

import base64

import pytest

from pyaccountingkit.company_configuration.infrastructure.postgres.signed_control_plane import (
    SignedControlPlaneSettings,
    UnsafeControlPlaneDeployment,
)


def settings():
    pub1 = base64.b64encode(bytes(range(32))).decode()
    pub2 = base64.b64encode(bytes(range(1, 33))).decode()
    return {
        "CC_PG_CONTROL_PLANE_DSN": (
            "postgresql://cc_control_plane:password@control.example.test/cc"
            "?sslmode=verify-full"
        ),
        "CC_PG_PRIVILEGED_AUDIT_DSN": (
            "postgresql://cc_privileged_audit:password@audit.example.test/cc"
            "?sslmode=verify-full"
        ),
        "CC_IAM_OPERATOR_ISSUER": "https://identity.example.test",
        "CC_IAM_APPROVAL_ISSUER": "https://approvals.example.test",
        "CC_IAM_AUDIENCE": "cc-privileged",
        "CC_IAM_OPERATOR_KID": "operator-v1",
        "CC_IAM_APPROVAL_KID": "checker-v1",
        "CC_IAM_OPERATOR_ED25519_PUBLIC_B64": pub1,
        "CC_IAM_APPROVAL_ED25519_PUBLIC_B64": pub2,
    }


def test_hardened_settings_keep_sql_secrets_out_of_representation():
    config = SignedControlPlaneSettings.from_environment(settings())
    assert config.operator_trust.issuer == "https://identity.example.test"
    assert config.approval_trust.kind == "approval"
    assert "password" not in repr(config)
    assert "postgresql" not in repr(config)


@pytest.mark.parametrize("extra", [
    {"CC_PG_ADMIN_DSN": "postgresql://postgres:secret@db/cc"},
    {"PGPASSWORD": "owner-secret"},
    {"DATABASE_URL": "postgresql://postgres:secret@db/cc"},
    {"CC_PG_DSN": "postgresql://cc_runtime_a:secret@db/cc"},
])
def test_inherited_owner_or_runtime_environment_is_refused(extra):
    with pytest.raises(UnsafeControlPlaneDeployment):
        SignedControlPlaneSettings.from_environment(settings() | extra)


@pytest.mark.parametrize("dsnpiece", [
    "sslmode=disable", "sslmode=require", "sslmode=prefer", "",
    "sslmode=verify-full&options=-c%20session_replication_role=replica",
])
def test_insufficient_tls_or_unsafe_pg_options_refused(dsnpiece):
    config = settings()
    config["CC_PG_CONTROL_PLANE_DSN"] = (
        "postgresql://cc_control_plane:password@control.example.test/cc?" + dsnpiece
    )
    with pytest.raises(UnsafeControlPlaneDeployment):
        SignedControlPlaneSettings.from_environment(config)


def test_owner_account_and_localhost_refused():
    config = settings()
    config["CC_PG_CONTROL_PLANE_DSN"] = (
        "postgresql://postgres:password@localhost/cc?sslmode=verify-full"
    )
    with pytest.raises(UnsafeControlPlaneDeployment):
        SignedControlPlaneSettings.from_environment(config)


def test_swapped_sql_identities_refused():
    config = settings()
    config["CC_PG_CONTROL_PLANE_DSN"], config["CC_PG_PRIVILEGED_AUDIT_DSN"] = (
        config["CC_PG_PRIVILEGED_AUDIT_DSN"], config["CC_PG_CONTROL_PLANE_DSN"]
    )
    with pytest.raises(UnsafeControlPlaneDeployment):
        SignedControlPlaneSettings.from_environment(config)


def test_missing_trusted_key_or_shared_trust_domains_refused():
    config = settings()
    del config["CC_IAM_APPROVAL_ED25519_PUBLIC_B64"]
    with pytest.raises(UnsafeControlPlaneDeployment):
        SignedControlPlaneSettings.from_environment(config)
    config = settings()
    config["CC_IAM_APPROVAL_ISSUER"] = config["CC_IAM_OPERATOR_ISSUER"]
    with pytest.raises(UnsafeControlPlaneDeployment):
        SignedControlPlaneSettings.from_environment(config)


def test_invalid_public_key_bytes_refused():
    config = settings()
    config["CC_IAM_OPERATOR_ED25519_PUBLIC_B64"] = "invalid!"
    with pytest.raises(UnsafeControlPlaneDeployment):
        SignedControlPlaneSettings.from_environment(config)
