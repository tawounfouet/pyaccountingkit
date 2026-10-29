"""Pure tests: denied-decision auditing does not grant access or mutate state."""

import pytest

from pyaccountingkit.company_configuration.application.commands import CreateLegalEntity
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal
from pyaccountingkit.company_configuration.application.service import (
    LegalEntityService,
    PermissionDenied,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
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


class SpyDenials:
    def __init__(self, *, fail=False):
        self.records = []
        self.fail = fail

    def record_denial(self, **kwargs):
        if self.fail:
            raise OSError("durable denial audit unavailable")
        self.records.append(kwargs)


def build(*, fail=False):
    scope = ConfigurationScope("tenant-a", CompanyId.new(), LegalEntityId.new())
    principal = TrustedPrincipal("finance-user", "tenant-a")
    store, grants, spy = MemoryStore(), MemoryAuthorization(), SpyDenials(fail=fail)
    service = LegalEntityService(lambda: MemoryUnitOfWork(store), grants, denial_audit=spy)
    return scope, principal, store, grants, spy, service


def create(scope):
    return CreateLegalEntity(
        scope=scope, legal_name="Example SAS", jurisdiction=JurisdictionCode("FR"),
        functional_currency=CurrencyCode("EUR"), request_id="r-1",
        correlation_id="trace-1", reason="New entity",
    )


def test_denied_create_emits_an_audit_without_mutating_business_state():
    scope, principal, store, _, spy, service = build()
    with pytest.raises(PermissionDenied):
        service.create(create(scope), principal=principal)
    assert spy.records == [{
        "principal": principal, "action": "legal_entity.create",
        "reason_code": "PERMISSION_DENIED", "correlation_id": "trace-1",
    }]
    assert not store.entities and not store.audit and not store.outbox


def test_denied_foreign_tenant_uses_authenticated_actor_only():
    scope, principal, store, _, spy, service = build()
    foreign = ConfigurationScope("tenant-b", scope.company_id, scope.legal_entity_id)
    with pytest.raises(PermissionDenied):
        service.create(create(foreign), principal=principal)
    assert spy.records[0]["principal"].tenant_id == "tenant-a"
    assert spy.records[0]["reason_code"] == "TENANT_MISMATCH"
    assert not store.entities


def test_allowed_create_does_not_emit_denial():
    scope, principal, store, grants, spy, service = build()
    grants.grant(actor_id=principal.actor_id, scope=scope, action="legal_entity.create")
    assert service.create(create(scope), principal=principal).revision == 1
    assert len(store.audit) == 1
    assert spy.records == []


def test_denial_audit_storage_failure_does_not_permit_mutation():
    scope, principal, store, _, spy, service = build(fail=True)
    with pytest.raises(OSError, match="audit unavailable"):
        service.create(create(scope), principal=principal)
    assert spy.records == []
    assert not store.entities and not store.audit and not store.outbox


def test_unauthenticated_call_never_uses_untrusted_identity_to_log():
    scope, _, store, _, spy, service = build()
    with pytest.raises(PermissionDenied):
        service.create(create(scope), principal=None)
    assert spy.records == []
    assert not store.entities
