"""Real PostgreSQL proofs; execute with an unprivileged application role.

The tests are opt-in locally and mandatory in the dedicated CI PostgreSQL job.
"""

import os
from datetime import UTC, datetime
from threading import Barrier, Thread

import pytest

psycopg = pytest.importorskip("psycopg")

from pyaccountingkit.company_configuration.application.commands import (  # noqa: E402
    CreateLegalEntity,
    RenameLegalEntity,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal  # noqa: E402
from pyaccountingkit.company_configuration.application.service import (  # noqa: E402
    EntityNotFound,
    IdempotencyConflict,
    LegalEntityService,
    PermissionDenied,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (  # noqa: E402
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.errors import (  # noqa: E402
    VersionConflict,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (  # noqa: E402
    CompanyId,
    LegalEntityId,
)
from pyaccountingkit.company_configuration.domain.shared.references import (  # noqa: E402
    CurrencyCode,
    JurisdictionCode,
)
from pyaccountingkit.company_configuration.infrastructure.memory import (  # noqa: E402
    MemoryAuthorization,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.adapter import (  # noqa: E402
    PostgresUnitOfWork,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.migrate import (  # noqa: E402
    apply_migrations,
)

APP_DSN = os.getenv("CC_PG_DSN")
ADMIN_DSN = os.getenv("CC_PG_ADMIN_DSN")
pytestmark = pytest.mark.skipif(
    not (APP_DSN and ADMIN_DSN),
    reason="PostgreSQL integration requires CC_PG_DSN and CC_PG_ADMIN_DSN",
)


class FixedClock:
    def now(self):
        return datetime(2026, 10, 29, tzinfo=UTC)


@pytest.fixture(autouse=True)
def clean_database():
    if not (APP_DSN and ADMIN_DSN):
        yield
        return
    with psycopg.connect(ADMIN_DSN) as conn:
        conn.execute(
            "TRUNCATE company_configuration.legal_entities, "
            "company_configuration.idempotency_requests, "
            "company_configuration.audit_records, "
            "company_configuration.outbox_events"
        )
    yield


def build_service(*, fail=None, tenant="tenant-a"):
    scope = ConfigurationScope(tenant, CompanyId.new(), LegalEntityId.new())
    actor = TrustedPrincipal("accountant", tenant)
    auth = MemoryAuthorization()
    for action in ("legal_entity.create", "legal_entity.read", "legal_entity.rename"):
        auth.grant(actor_id=actor.actor_id, action=action, scope=scope)
    service = LegalEntityService(
        lambda: PostgresUnitOfWork(APP_DSN, before_commit=fail), auth, FixedClock()
    )
    return scope, actor, auth, service


def create(scope, *, request_id="req-1", name="Example SARL"):
    return CreateLegalEntity(
        scope=scope, legal_name=name, jurisdiction=JurisdictionCode("FR"),
        functional_currency=CurrencyCode("EUR"), request_id=request_id,
        correlation_id="corr-1", reason="Entity setup",
    )


def rename(scope, *, name="Example SA", request_id="req-2"):
    return RenameLegalEntity(
        scope=scope, entity_id=scope.legal_entity_id, new_name=name,
        expected_revision=1, request_id=request_id, correlation_id="corr-2",
        reason="Legal registry update",
    )


def counts():
    with psycopg.connect(ADMIN_DSN) as conn:
        return [
            conn.execute(f"SELECT count(*) FROM company_configuration.{table}").fetchone()[0]
            for table in (
                "legal_entities", "audit_records", "outbox_events", "idempotency_requests"
            )
        ]


def test_migration_checksum_is_idempotent():
    assert apply_migrations(ADMIN_DSN) == []


def test_persisted_create_rename_with_atomic_evidence():
    scope, actor, _, service = build_service()
    receipt = service.create(create(scope), principal=actor)
    assert receipt.revision == 1
    assert service.read(principal=actor, scope=scope).legal_name == "Example SARL"
    changed = service.rename(rename(scope), principal=actor)
    assert changed.revision == 2
    assert service.read(principal=actor, scope=scope).legal_name == "Example SA"
    assert counts() == [1, 2, 2, 2]
    with psycopg.connect(ADMIN_DSN) as conn:
        audit_ids = {
            str(row[0]) for row in conn.execute(
                "SELECT record_id FROM company_configuration.audit_records"
            ).fetchall()
        }
        assert {receipt.audit_id, changed.audit_id} == audit_ids


def test_replay_survives_new_connections_without_duplicate_side_effects():
    scope, actor, auth, service = build_service()
    receipt = service.create(create(scope), principal=actor)
    fresh = LegalEntityService(lambda: PostgresUnitOfWork(APP_DSN), auth, FixedClock())
    assert fresh.create(create(scope), principal=actor) == receipt
    assert counts() == [1, 1, 1, 1]
    with pytest.raises(IdempotencyConflict):
        fresh.create(create(scope, name="Unexpected company"), principal=actor)
    assert counts() == [1, 1, 1, 1]


def test_injected_precommit_failure_is_fully_rolled_back():
    scope, actor, auth, _ = build_service()

    def crash():
        raise OSError("inject precommit fault")

    service = LegalEntityService(
        lambda: PostgresUnitOfWork(APP_DSN, before_commit=crash), auth, FixedClock()
    )
    with pytest.raises(OSError, match="inject precommit"):
        service.create(create(scope), principal=actor)
    assert counts() == [0, 0, 0, 0]


def test_stale_optimistic_write_preserves_transactional_evidence():
    scope, actor, _, service = build_service()
    service.create(create(scope), principal=actor)
    service.rename(rename(scope), principal=actor)
    with pytest.raises(VersionConflict):
        service.rename(rename(scope, name="Stale", request_id="req-3"), principal=actor)
    assert counts() == [1, 2, 2, 2]


def test_rls_denies_missing_and_other_tenant_context():
    scope, actor, _, service = build_service()
    service.create(create(scope), principal=actor)
    with psycopg.connect(APP_DSN) as conn:
        # With no tenant context, RLS must not expose any records.
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.legal_entities"
        ).fetchone()[0] == 0
        conn.execute("SELECT set_config('app.tenant_id', %s, true)", ("tenant-b",))
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.legal_entities"
        ).fetchone()[0] == 0
        conn.execute("SELECT set_config('app.tenant_id', %s, true)", ("tenant-a",))
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.legal_entities"
        ).fetchone()[0] == 1
    with psycopg.connect(APP_DSN) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("TRUNCATE company_configuration.audit_records")


def test_application_denial_and_mismatched_company_are_rejected():
    scope, actor, auth, service = build_service()
    service.create(create(scope), principal=actor)
    wrong = ConfigurationScope(scope.tenant_id, CompanyId.new(), scope.legal_entity_id)
    auth.grant(actor_id=actor.actor_id, action="legal_entity.read", scope=wrong)
    with pytest.raises(EntityNotFound):
        service.read(principal=actor, scope=wrong)
    auth.revoke(actor_id=actor.actor_id, action="legal_entity.read", scope=scope)
    with pytest.raises(PermissionDenied):
        service.read(principal=actor, scope=scope)
    assert counts() == [1, 1, 1, 1]


def test_cross_scope_uow_and_append_only_audit_fail_closed():
    a, _, _, _ = build_service()
    b = ConfigurationScope(a.tenant_id, CompanyId.new(), LegalEntityId.new())
    with PostgresUnitOfWork(APP_DSN) as uow:
        assert uow.entities.get(scope=a, entity_id=a.legal_entity_id) is None
        with pytest.raises(Exception, match="One UnitOfWork cannot cross"):
            uow.entities.get(scope=b, entity_id=b.legal_entity_id)
    scope, actor, _, service = build_service()
    service.create(create(scope), principal=actor)
    with psycopg.connect(ADMIN_DSN) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("UPDATE company_configuration.audit_records SET reason='changed'")
    assert counts() == [1, 1, 1, 1]


def test_concurrent_stale_writers_only_one_commits():
    scope, actor, _, service = build_service()
    service.create(create(scope), principal=actor)
    barrier = Barrier(3)
    results = []

    def writer(name, key):
        barrier.wait()
        try:
            service.rename(rename(scope, name=name, request_id=key), principal=actor)
            results.append("ok")
        except VersionConflict:
            results.append("conflict")

    threads = [Thread(target=writer, args=(name, key)) for name, key in [
        ("First SAS", "worker-one"), ("Second SAS", "worker-two")
    ]]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=10)
    assert sorted(results) == ["conflict", "ok"]
    assert counts() == [1, 2, 2, 2]
