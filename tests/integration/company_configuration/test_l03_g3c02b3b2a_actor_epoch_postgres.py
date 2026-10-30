"""G3-C02b3b2a owner-projected actor epoch, live SQL row locks, SQL ACLs.

Independent IAM verification & business UoW wiring are not part of this slice.
"""

import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from pyaccountingkit.company_configuration.infrastructure.postgres import (  # noqa: E402
    tenant_boundary,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.organization_actor_grant_epoch import (  # noqa: E402
    ActorGrantEpochReference,
    PostgresActorGrantEpochFence,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
COMPANY = os.getenv("CC_PG_ORG_COMPANY_WRITER_DSN")
OTHER_COMPANY = os.getenv("CC_PG_ORG_COMPANY_WRITER_DSN_B")
REGISTRY = os.getenv("CC_PG_ORG_REGISTRY_WRITER_DSN")
LIFECYCLE = os.getenv("CC_PG_ORG_LIFECYCLE_WRITER_DSN")
MEMBERSHIP = os.getenv("CC_PG_ORG_MEMBERSHIP_WRITER_DSN")
RUNTIME = os.getenv("CC_PG_DSN")
NONCE = os.getenv("CC_PG_ORG_NONCE_CONSUMER_DSN")
pytestmark = pytest.mark.skipif(
    not all((ADMIN, COMPANY, OTHER_COMPANY, REGISTRY, LIFECYCLE,
             MEMBERSHIP, RUNTIME, NONCE)),
    reason="G3-C02b3b2a requires isolated PostgreSQL issuer CI credentials",
)

TABLE = "company_configuration.organization_actor_grant_epochs"
FUNC = (
    "company_configuration.require_org_actor_grant_epoch("
    "text,uuid,bigint,text,text,uuid,text,text)"
)


@pytest.fixture(autouse=True)
def clear_projected_grants():
    if ADMIN:
        with psycopg.connect(ADMIN) as conn:
            conn.execute("DELETE FROM " + TABLE)
    yield
    if ADMIN:
        with psycopg.connect(ADMIN) as conn:
            conn.execute("DELETE FROM " + TABLE)


def reference():
    return ActorGrantEpochReference(
        tenant_id="tenant-a", grant_id=uuid4(), grant_version=1,
        actor_id="signed-actor", action="organization.company.register",
        target_id=uuid4(), authority_issuer="test-iam-decision",
        decision_sha256="a" * 64,
    )


def provision(ref, *, enabled=True, expires_in=timedelta(minutes=2)):
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "INSERT INTO " + TABLE + " (grant_id,tenant_id,actor_id,action,"
            "target_id,authority_issuer,grant_version,enabled,valid_until,"
            "decision_sha256,source_event_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (ref.grant_id, ref.tenant_id, ref.actor_id, ref.action,
             ref.target_id, ref.authority_issuer, ref.grant_version, enabled,
             datetime.now(UTC) + expires_in, ref.decision_sha256, uuid4()),
        )


def bump_epoch(ref, *, enabled=False):
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "UPDATE " + TABLE + " SET enabled=%s,grant_version=%s,"
            "source_event_id=%s,observed_at=clock_timestamp() "
            "WHERE grant_id=%s",
            (enabled, ref.grant_version + 1, uuid4(), ref.grant_id),
        )


def test_owner_projected_exact_scope_authorizes_all_four_issuer_families():
    fence = PostgresActorGrantEpochFence()
    for dsn, action in (
        (COMPANY, "organization.company.register"),
        (REGISTRY, "organization.establishment.register"),
        (LIFECYCLE, "organization.company.transition"),
        (MEMBERSHIP, "organization.membership.assign"),
    ):
        ref = replace(reference(), action=action)
        provision(ref)
        with psycopg.connect(dsn) as conn:
            assert fence.require(connection=conn, reference=ref) is None
        # Even if the current grant is valid, wrong SQL issuer family fails.
        other_dsn = REGISTRY if dsn == COMPANY else COMPANY
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with psycopg.connect(other_dsn) as conn:
                fence.require(connection=conn, reference=ref)


@pytest.mark.parametrize("mismatch", [
    {"actor_id": "forged-actor"}, {"tenant_id": "tenant-b"},
    {"action": "organization.membership.assign"},
    {"target_id": uuid4()}, {"authority_issuer": "self-issued"},
    {"decision_sha256": "b" * 64}, {"grant_version": 2},
    {"grant_id": uuid4()},
])
def test_actor_scope_version_decision_and_tenant_mismatch_denied(mismatch):
    ref = reference()
    provision(ref)
    error = (
        tenant_boundary.TenantConnectionMismatch
        if "tenant_id" in mismatch else psycopg.errors.InsufficientPrivilege
    )
    with pytest.raises(error):
        with psycopg.connect(COMPANY) as conn:
            PostgresActorGrantEpochFence().require(
                connection=conn, reference=replace(ref, **mismatch),
            )


def test_owner_grant_epoch_revocation_invalidates_old_version():
    ref = reference()
    provision(ref)
    fence = PostgresActorGrantEpochFence()
    with psycopg.connect(COMPANY) as conn:
        fence.require(connection=conn, reference=ref)
    bump_epoch(ref, enabled=False)
    for variant in (ref, replace(ref, grant_version=2)):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with psycopg.connect(COMPANY) as conn:
                fence.require(connection=conn, reference=variant)
    # Owner may reinstate only with a newer signed/provisioned epoch. An old
    # version cannot be trusted after revocation even if re-enabled.
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "UPDATE " + TABLE + " SET enabled=true,grant_version=3,"
            "source_event_id=%s,observed_at=clock_timestamp() WHERE grant_id=%s",
            (uuid4(), ref.grant_id),
        )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(COMPANY) as conn:
            fence.require(connection=conn, reference=ref)
    with psycopg.connect(COMPANY) as conn:
        fence.require(connection=conn, reference=replace(ref, grant_version=3))


def test_grant_expiration_or_excessive_projection_horizon_denied():
    fence = PostgresActorGrantEpochFence()
    for delta in (timedelta(minutes=-1), timedelta(hours=1)):
        ref = reference()
        provision(ref, expires_in=delta)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with psycopg.connect(COMPANY) as conn:
                fence.require(connection=conn, reference=ref)


def test_owner_cannot_regress_grant_epoch_or_change_identity_scope():
    ref = reference()
    provision(ref)
    for assignment in (
        "grant_version=1", "grant_version=0",
        "actor_id='new-actor',grant_version=2",
        "tenant_id='tenant-b',grant_version=2",
        "source_event_id=source_event_id,grant_version=2",
    ):
        with pytest.raises(psycopg.errors.CheckViolation):
            with psycopg.connect(ADMIN) as conn:
                conn.execute(
                    "UPDATE " + TABLE + " SET " + assignment
                    + " WHERE grant_id=%s", (ref.grant_id,),
                )


def test_sql_issuer_lock_serializes_owner_revocation_against_commit():
    ref = reference()
    provision(ref)
    fence = PostgresActorGrantEpochFence()
    with psycopg.connect(COMPANY) as writer:
        fence.require(connection=writer, reference=ref)
        # An independently authorized owner cannot move grant epoch while
        # this specific SQL issuer's active transaction holds FOR SHARE.
        with psycopg.connect(ADMIN) as owner:
            owner.execute("SET LOCAL lock_timeout='200ms'")
            with pytest.raises(psycopg.errors.LockNotAvailable):
                owner.execute(
                    "UPDATE " + TABLE + " SET grant_version=2,enabled=false,"
                    "source_event_id=%s WHERE grant_id=%s",
                    (uuid4(), ref.grant_id),
                )
            owner.rollback()
    # The write has committed and released its scoped grant row lock.
    bump_epoch(ref)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(COMPANY) as writer:
            fence.require(connection=writer, reference=ref)


def test_owner_revocation_committed_before_epoch_fence_denies_sql_commit():
    ref = reference()
    provision(ref)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(COMPANY) as conn:
            conn.execute("SELECT 1")
            # Simulated transaction already started before owner revocation.
            bump_epoch(ref)
            PostgresActorGrantEpochFence().require(connection=conn, reference=ref)


def test_runtime_nonce_and_other_tenant_issuer_have_no_actor_grant_authority():
    ref = reference()
    provision(ref)
    fence = PostgresActorGrantEpochFence()
    for dsn in (RUNTIME, NONCE):
        with psycopg.connect(dsn) as conn:
            assert conn.execute(
                "SELECT has_function_privilege(current_user,%s,'EXECUTE')", (FUNC,)
            ).fetchone()[0] is False
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with psycopg.connect(dsn) as conn:
                fence.require(connection=conn, reference=ref)
    with pytest.raises(tenant_boundary.TenantConnectionMismatch):
        with psycopg.connect(OTHER_COMPANY) as conn:
            fence.require(connection=conn, reference=ref)


def test_untrusted_sql_principals_cannot_provision_or_mutate_grant_epochs():
    ref = reference()
    provision(ref)
    for dsn in (RUNTIME, NONCE, COMPANY, REGISTRY, LIFECYCLE, MEMBERSHIP):
        with psycopg.connect(dsn) as conn:
            for privilege in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                assert conn.execute(
                    "SELECT has_table_privilege(current_user,%s,%s)",
                    (TABLE, privilege),
                ).fetchone()[0] is False
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with psycopg.connect(dsn) as conn:
                conn.execute(
                    "UPDATE " + TABLE + " SET enabled=false WHERE grant_id=%s",
                    (ref.grant_id,),
                )


def test_invalid_reference_and_autocommit_do_not_pass_epoch_fence():
    ref = reference()
    with pytest.raises(ValueError):
        replace(ref, decision_sha256="not-sha256")
    with psycopg.connect(COMPANY, autocommit=True) as conn:
        with pytest.raises(ValueError):
            PostgresActorGrantEpochFence().require(connection=conn, reference=ref)
