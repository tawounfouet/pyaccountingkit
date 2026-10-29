"""L02 in-memory vertical proof, not SQL or distributed qualification."""

from datetime import UTC, datetime
from threading import Barrier, Thread

import pytest

from pyaccountingkit.company_configuration.application.commands import (
    CreateLegalEntity,
    RenameLegalEntity,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal
from pyaccountingkit.company_configuration.application.service import (
    EntityNotFound,
    IdempotencyConflict,
    LegalEntityService,
    PermissionDenied,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.errors import VersionConflict
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    CompanyId,
    LegalEntityId,
)
from pyaccountingkit.company_configuration.domain.shared.references import (
    CurrencyCode,
    JurisdictionCode,
)
from pyaccountingkit.company_configuration.infrastructure.memory import (
    MemoryAuthorization,
    MemoryStore,
    MemoryUnitOfWork,
)


class FixedClock:
    def now(self):
        return datetime(2026, 10, 29, tzinfo=UTC)


def setup():
    store = MemoryStore()
    auth = MemoryAuthorization()
    scope = ConfigurationScope("tenant-a", CompanyId.new(), LegalEntityId.new())
    actor = TrustedPrincipal("controller", "tenant-a")
    for action in ("legal_entity.create", "legal_entity.read", "legal_entity.rename"):
        auth.grant(actor_id=actor.actor_id, action=action, scope=scope)
    service = LegalEntityService(lambda: MemoryUnitOfWork(store), auth, FixedClock())
    return store, auth, scope, actor, service


def make_create(scope, *, name="Example SARL", request_id="req-1", reason="Onboarding"):
    return CreateLegalEntity(
        scope=scope, legal_name=name, jurisdiction=JurisdictionCode("FR"),
        functional_currency=CurrencyCode("EUR"), request_id=request_id,
        correlation_id="cor-1", reason=reason,
    )


def make_rename(scope, *, request_id="req-2", name="Example SA", expected=1):
    return RenameLegalEntity(
        scope=scope, entity_id=scope.legal_entity_id, new_name=name,
        expected_revision=expected, request_id=request_id,
        correlation_id="cor-2", reason="Registered legal name update",
    )


def test_create_read_and_rename_atomic_evidence():
    store, _, scope, actor, service = setup()
    a = service.create(make_create(scope), principal=actor)
    assert a.revision == 1
    assert service.read(principal=actor, scope=scope).legal_name == "Example SARL"
    b = service.rename(make_rename(scope), principal=actor)
    assert b.revision == 2
    assert service.read(principal=actor, scope=scope).legal_name == "Example SA"
    assert [x.after_revision for x in store.audit] == [1, 2]
    assert [x.revision for x in store.outbox] == [1, 2]
    assert store.audit[1].correlation_id == b.correlation_id
    assert store.audit[1].record_id == b.audit_id
    assert store.outbox[1].event_id == b.event_id


def test_fail_closed_missing_grant_or_untrusted_identity():
    store, auth, scope, actor, service = setup()
    auth.revoke(actor_id=actor.actor_id, action="legal_entity.create", scope=scope)
    with pytest.raises(PermissionDenied):
        service.create(make_create(scope), principal=actor)
    with pytest.raises(PermissionDenied):
        service.create(make_create(scope), principal=None)
    assert not store.entities and not store.audit and not store.outbox


def test_authz_revocation_precedes_idempotent_replay():
    store, auth, scope, actor, service = setup()
    service.create(make_create(scope), principal=actor)
    auth.revoke(actor_id=actor.actor_id, action="legal_entity.create", scope=scope)
    with pytest.raises(PermissionDenied):
        service.create(make_create(scope), principal=actor)
    assert len(store.audit) == 1


def test_cross_tenant_and_company_id_guess_cannot_read():
    store, auth, scope, actor, service = setup()
    service.create(make_create(scope), principal=actor)
    wrong_scope = ConfigurationScope(
        scope.tenant_id, CompanyId.new(), scope.legal_entity_id
    )
    auth.grant(actor_id=actor.actor_id, action="legal_entity.read", scope=wrong_scope)
    with pytest.raises(EntityNotFound):
        service.read(principal=actor, scope=wrong_scope)
    with pytest.raises(PermissionDenied):
        service.read(principal=TrustedPrincipal("intruder", "tenant-b"), scope=scope)
    assert len(store.audit) == 1


def test_idempotency_replay_has_no_extra_audit_outbox():
    store, _, scope, actor, service = setup()
    first = service.create(make_create(scope), principal=actor)
    second = service.create(make_create(scope), principal=actor)
    assert first == second
    assert len(store.entities) == len(store.audit) == len(store.outbox) == 1
    assert len(store.requests) == 1


def test_idempotency_payload_conflict_fails_closed():
    store, _, scope, actor, service = setup()
    service.create(make_create(scope), principal=actor)
    with pytest.raises(IdempotencyConflict):
        service.create(make_create(scope, name="Different name"), principal=actor)
    assert len(store.audit) == len(store.outbox) == 1


def test_stale_revision_has_no_side_effects():
    store, _, scope, actor, service = setup()
    service.create(make_create(scope), principal=actor)
    service.rename(make_rename(scope), principal=actor)
    with pytest.raises(VersionConflict):
        service.rename(make_rename(scope, request_id="req-3"), principal=actor)
    assert len(store.audit) == len(store.outbox) == 2


def test_commit_failure_does_not_expose_staged_updates():
    store, auth, scope, actor, service = setup()
    def crash():
        raise OSError("Injected storage failure")
    broken_service = LegalEntityService(
        lambda: MemoryUnitOfWork(store, before_commit=crash), auth, FixedClock()
    )
    with pytest.raises(OSError):
        broken_service.create(make_create(scope), principal=actor)
    assert not store.entities and not store.audit and not store.outbox and not store.requests
    assert service.create(make_create(scope), principal=actor).revision == 1


def test_invalid_clock_rolls_back_everything():
    store, auth, scope, actor, _ = setup()
    class BadClock:
        def now(self):
            return datetime(2026, 10, 29)
    bad = LegalEntityService(lambda: MemoryUnitOfWork(store), auth, BadClock())
    with pytest.raises(ValueError, match="timezone-aware"):
        bad.create(make_create(scope), principal=actor)
    assert not store.entities and not store.audit and not store.outbox


def test_concurrent_optimistic_writers_only_one_commits():
    store, _, scope, actor, service = setup()
    service.create(make_create(scope), principal=actor)
    barrier = Barrier(3)
    outcomes = []
    def writer(request_id, name):
        barrier.wait()
        try:
            service.rename(make_rename(scope, request_id=request_id, name=name), principal=actor)
            outcomes.append("ok")
        except VersionConflict:
            outcomes.append("conflict")
    t1 = Thread(target=writer, args=("cmd-1", "Legal Name A"))
    t2 = Thread(target=writer, args=("cmd-2", "Legal Name B"))
    t1.start()
    t2.start()
    barrier.wait()
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert sorted(outcomes) == ["conflict", "ok"]
    assert len(store.audit) == len(store.outbox) == 2


def test_name_read_requires_its_own_permission():
    _, auth, scope, actor, service = setup()
    service.create(make_create(scope), principal=actor)
    auth.revoke(actor_id=actor.actor_id, action="legal_entity.read", scope=scope)
    with pytest.raises(PermissionDenied):
        service.read(principal=actor, scope=scope)


def test_same_request_id_new_actor_keeps_separate_permission_and_collision():
    store, auth, scope, actor, service = setup()
    service.create(make_create(scope), principal=actor)
    secondary = TrustedPrincipal("secondary", "tenant-a")
    auth.grant(actor_id=secondary.actor_id, action="legal_entity.create", scope=scope)
    with pytest.raises(VersionConflict):
        service.create(make_create(scope), principal=secondary)
    assert len(store.requests) == 1
