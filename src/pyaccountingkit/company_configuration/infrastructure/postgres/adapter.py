"""PostgreSQL L02 proof: tenant-scoped repository and one durable local UoW.

This adapter assumes a separately authenticated principal and a non-BYPASSRLS
runtime role. It is not an IAM provider, outbox dispatcher, or C10 endpoint.
"""

from collections.abc import Callable
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from ...application.organization_membership_evidence import (
    MembershipChangeReceipt,
    MembershipTransactionEvidence,
)
from ...application.ports import AuditRecord, ChangeReceipt, PendingEvent
from ...domain.organization.entities import LegalEntity
from ...domain.organization.model import MembershipKind, OrganizationMembership
from ...domain.shared.accounting_scope import ConfigurationScope
from ...domain.shared.effective_interval import EffectiveInterval
from ...domain.shared.errors import InvalidScope, VersionConflict
from ...domain.shared.identifiers import CompanyId, LegalEntityId, MembershipId
from ...domain.shared.references import CurrencyCode, JurisdictionCode
from .tenant_boundary import require_tenant_connection


class PostgresLegalEntityRepository:
    def __init__(self, uow: "PostgresUnitOfWork") -> None:
        self._uow = uow

    def get(self, *, scope: ConfigurationScope, entity_id: LegalEntityId) -> LegalEntity | None:
        self._uow._bind_scope(scope)
        if entity_id != scope.legal_entity_id:
            raise InvalidScope("Entity identifier and requested scope disagree")
        row = self._uow._connection.execute(
            "SELECT company_id, entity_id, legal_name, jurisdiction, "
            "functional_currency, revision FROM company_configuration.legal_entities "
            "WHERE tenant_id=%s AND company_id=%s AND entity_id=%s",
            (scope.tenant_id, scope.company_id.value, entity_id.value),
        ).fetchone()
        if row is None:
            return None
        return LegalEntity(
            id=LegalEntityId(row["entity_id"]),
            scope=ConfigurationScope(
                scope.tenant_id, CompanyId(row["company_id"]), LegalEntityId(row["entity_id"])
            ),
            legal_name=row["legal_name"],
            jurisdiction=JurisdictionCode(row["jurisdiction"].strip()),
            functional_currency=CurrencyCode(row["functional_currency"].strip()),
            revision=row["revision"],
        )

    def save(self, entity: LegalEntity, *, expected_revision: int) -> None:
        self._uow._bind_scope(entity.scope)
        if expected_revision == 0 and entity.revision == 1:
            result = self._uow._connection.execute(
                "INSERT INTO company_configuration.legal_entities "
                "(tenant_id, company_id, entity_id, legal_name, jurisdiction, "
                "functional_currency, revision) VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (tenant_id, entity_id) DO NOTHING RETURNING entity_id",
                (entity.scope.tenant_id, entity.scope.company_id.value, entity.id.value,
                 entity.legal_name, entity.jurisdiction.value,
                 entity.functional_currency.value, entity.revision),
            )
            if result.fetchone() is None:
                raise VersionConflict("LegalEntity already exists")
        elif expected_revision >= 1 and entity.revision == expected_revision + 1:
            result = self._uow._connection.execute(
                "UPDATE company_configuration.legal_entities SET legal_name=%s, revision=%s "
                "WHERE tenant_id=%s AND company_id=%s AND entity_id=%s AND revision=%s "
                "RETURNING entity_id",
                (entity.legal_name, entity.revision, entity.scope.tenant_id,
                 entity.scope.company_id.value, entity.id.value, expected_revision),
            )
            if result.fetchone() is None:
                raise VersionConflict("Revision mismatch or scope changed")
        else:
            raise VersionConflict("Invalid expected revision transition")


class PostgresUnitOfWork:
    """One connection per UoW, transaction-bound scope and rollback on failure.

    Tenant advisory locking makes the idempotency lookup/write atomic for these
    application commands within a database. It is deliberately coarse-grained;
    operational throughput and locking order need benchmarks before production.
    """

    def __init__(
        self, dsn: str, *, before_commit: Callable[[], None] | None = None
    ) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("A PostgreSQL DSN is required")
        self._dsn = dsn
        self._before_commit = before_commit
        self._connection: psycopg.Connection | None = None
        self._scope: ConfigurationScope | None = None
        self._committed = False

    def __enter__(self) -> "PostgresUnitOfWork":
        if self._connection is not None:
            raise RuntimeError("UnitOfWork cannot be entered twice")
        self._connection = psycopg.connect(self._dsn, row_factory=dict_row)
        self.entities = PostgresLegalEntityRepository(self)
        self.org_memberships = PostgresOrganizationMembershipRepository(self)
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._connection is not None:
            try:
                if not self._committed:
                    self._connection.rollback()
            finally:
                self._connection.close()
                self._connection = None
                self._scope = None

    def _bind_scope(self, scope: ConfigurationScope) -> None:
        if self._connection is None or self._committed:
            raise RuntimeError("UnitOfWork is not active")
        if not isinstance(scope, ConfigurationScope):
            raise InvalidScope("Typed accounting scope is required")
        if self._scope is None:
            require_tenant_connection(self._connection, scope.tenant_id)
            self._connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                ("cc:tenant:" + scope.tenant_id,),
            )
            self._scope = scope
        elif scope != self._scope:
            raise InvalidScope("One UnitOfWork cannot cross accounting scopes")

    def lookup_request(
        self, *, actor_id: str, scope: ConfigurationScope, action: str, key: str
    ) -> tuple[str, ChangeReceipt] | None:
        self._bind_scope(scope)
        row = self._connection.execute(
            "SELECT request_digest, receipt_revision, receipt_correlation_id, "
            "receipt_audit_id, receipt_event_id FROM "
            "company_configuration.idempotency_requests WHERE tenant_id=%s "
            "AND actor_id=%s AND company_id=%s AND entity_id=%s "
            "AND action=%s AND request_key=%s",
            (scope.tenant_id, actor_id, scope.company_id.value,
             scope.legal_entity_id.value, action, key),
        ).fetchone()
        if row is None:
            return None
        return row["request_digest"], ChangeReceipt(
            entity_id=scope.legal_entity_id, revision=row["receipt_revision"],
            correlation_id=row["receipt_correlation_id"],
            audit_id=str(row["receipt_audit_id"]), event_id=str(row["receipt_event_id"]),
        )

    def save_request(
        self, *, actor_id: str, scope: ConfigurationScope, action: str,
        key: str, digest: str, receipt: ChangeReceipt,
    ) -> None:
        self._bind_scope(scope)
        self._connection.execute(
            "INSERT INTO company_configuration.idempotency_requests "
            "(tenant_id, actor_id, company_id, entity_id, action, request_key, "
            "request_digest, receipt_revision, receipt_correlation_id, "
            "receipt_audit_id, receipt_event_id) VALUES "
            "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (scope.tenant_id, actor_id, scope.company_id.value,
             scope.legal_entity_id.value, action, key, digest, receipt.revision,
             receipt.correlation_id, UUID(receipt.audit_id), UUID(receipt.event_id)),
        )

    def append_audit(self, record: AuditRecord) -> None:
        self._bind_scope(record.scope)
        self._connection.execute(
            "INSERT INTO company_configuration.audit_records "
            "(record_id, tenant_id, company_id, entity_id, actor_id, action, "
            "before_revision, after_revision, reason, correlation_id, recorded_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (UUID(record.record_id), record.scope.tenant_id, record.scope.company_id.value,
             record.entity_id.value, record.actor_id, record.action,
             record.before_revision, record.after_revision, record.reason,
             record.correlation_id, record.recorded_at),
        )

    def append_outbox(self, event: PendingEvent) -> None:
        self._bind_scope(event.scope)
        self._connection.execute(
            "INSERT INTO company_configuration.outbox_events "
            "(event_id, tenant_id, company_id, entity_id, event_type, schema_version, "
            "revision, correlation_id, recorded_at) VALUES "
            "(%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (UUID(event.event_id), event.scope.tenant_id, event.scope.company_id.value,
             event.entity_id.value, event.event_type, event.schema_version,
             event.revision, event.correlation_id, event.recorded_at),
        )

    def lookup_membership_request(
        self, *, actor_id: str, scope: ConfigurationScope, action: str, key: str,
    ) -> tuple[str, MembershipChangeReceipt] | None:
        """MembershipId-based request; never return L02 LegalEntity receipts."""
        self._bind_scope(scope)
        row = self._connection.execute(
            "SELECT request_digest,membership_id,company_id,legal_entity_id,"
            "revision,correlation_id,audit_id,event_id "
            "FROM company_configuration.organization_membership_requests "
            "WHERE tenant_id=%s AND actor_id=%s AND action=%s AND request_key=%s",
            (scope.tenant_id, actor_id, action, key),
        ).fetchone()
        if row is None:
            return None
        return row["request_digest"].strip(), MembershipChangeReceipt(
            membership_id=MembershipId(row["membership_id"]),
            company_id=CompanyId(row["company_id"]),
            legal_entity_id=LegalEntityId(row["legal_entity_id"]),
            revision=row["revision"],
            correlation_id=row["correlation_id"],
            audit_id=str(row["audit_id"]), event_id=str(row["event_id"]),
        )

    def append_membership_evidence(
        self, *, scope: ConfigurationScope, evidence: MembershipTransactionEvidence,
    ) -> None:
        """Evidence and affiliation must commit together in the bound transaction."""
        self._bind_scope(scope)
        if not isinstance(evidence, MembershipTransactionEvidence):
            raise InvalidScope("Typed membership transaction evidence required")
        m, r = evidence.membership, evidence.receipt
        if (
            m.tenant_id != scope.tenant_id
            or m.company_id != scope.company_id
            or m.legal_entity_id != scope.legal_entity_id
            or r.company_id != scope.company_id
            or r.legal_entity_id != scope.legal_entity_id
        ):
            raise InvalidScope("Membership evidence is outside the transaction scope")
        self._connection.execute(
            "INSERT INTO company_configuration.organization_membership_audit "
            "(record_id,tenant_id,actor_id,action,membership_id,company_id,"
            "legal_entity_id,before_revision,after_revision,valid_from,valid_to,"
            "source_ref,reason,correlation_id,recorded_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                UUID(r.audit_id), m.tenant_id, evidence.actor_id, evidence.action,
                m.id.value, m.company_id.value, m.legal_entity_id.value,
                m.revision-1, m.revision, m.valid.start, m.valid.end,
                m.source_ref, evidence.reason, r.correlation_id, m.recorded_at,
            ),
        )
        self._connection.execute(
            "INSERT INTO company_configuration.organization_membership_outbox "
            "(event_id,tenant_id,event_type,schema_version,membership_id,company_id,"
            "legal_entity_id,revision,kind,exclusive,valid_from,valid_to,"
            "source_ref,correlation_id,recorded_at) "
            "VALUES (%s,%s,%s,1,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                UUID(r.event_id), m.tenant_id, evidence.action, m.id.value,
                m.company_id.value, m.legal_entity_id.value, m.revision,
                m.kind.value, m.exclusive, m.valid.start, m.valid.end,
                m.source_ref, r.correlation_id, m.recorded_at,
            ),
        )
        self._connection.execute(
            "INSERT INTO company_configuration.organization_membership_requests "
            "(tenant_id,actor_id,action,request_key,request_digest,membership_id,"
            "company_id,legal_entity_id,revision,correlation_id,audit_id,event_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                m.tenant_id, evidence.actor_id, evidence.action,
                evidence.request_key, evidence.request_digest,
                m.id.value, m.company_id.value, m.legal_entity_id.value,
                m.revision, r.correlation_id, UUID(r.audit_id), UUID(r.event_id),
            ),
        )

    def commit(self) -> None:
        if self._connection is None or self._committed or self._scope is None:
            raise RuntimeError("Cannot commit an empty or closed UnitOfWork")
        if self._before_commit is not None:
            self._before_commit()
        self._connection.commit()
        self._committed = True


class PostgresOrganizationMembershipRepository:
    """Same-connection membership writer, never a separate commit or SQL session.

    The parent and overlap guards are enforced by migration 0015. The UoW
    uses the same scope lock for request replay, membership writes and evidence.
    """

    def __init__(self, uow: PostgresUnitOfWork) -> None:
        self._uow = uow

    def latest(
        self, *, scope: ConfigurationScope, membership_id: MembershipId
    ) -> OrganizationMembership | None:
        self._uow._bind_scope(scope)
        if not isinstance(membership_id, MembershipId):
            raise InvalidScope("Typed membership id required")
        row = self._uow._connection.execute(
            "SELECT membership_id,tenant_id,company_id,legal_entity_id,kind,"
            "exclusive,valid_from,valid_to,recorded_at,source_ref,revision "
            "FROM company_configuration.organizational_membership_revisions "
            "WHERE tenant_id=%s AND company_id=%s AND legal_entity_id=%s "
            "AND membership_id=%s ORDER BY revision DESC LIMIT 1",
            (scope.tenant_id, scope.company_id.value,
             scope.legal_entity_id.value, membership_id.value),
        ).fetchone()
        if row is None:
            return None
        return OrganizationMembership(
            MembershipId(row["membership_id"]), row["tenant_id"],
            CompanyId(row["company_id"]), LegalEntityId(row["legal_entity_id"]),
            MembershipKind(row["kind"]), row["exclusive"],
            EffectiveInterval(row["valid_from"], row["valid_to"]),
            row["recorded_at"], row["source_ref"], row["revision"],
        )

    def append(
        self, *, scope: ConfigurationScope, membership: OrganizationMembership
    ) -> None:
        self._uow._bind_scope(scope)
        if (
            not isinstance(membership, OrganizationMembership)
            or membership.tenant_id != scope.tenant_id
            or membership.company_id != scope.company_id
            or membership.legal_entity_id != scope.legal_entity_id
        ):
            raise InvalidScope("Membership must match transaction's exact scope")
        self._uow._connection.execute(
            "INSERT INTO company_configuration.organizational_membership_revisions "
            "(tenant_id,membership_id,revision,company_id,legal_entity_id,"
            "kind,exclusive,valid_from,valid_to,recorded_at,source_ref) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                membership.tenant_id, membership.id.value, membership.revision,
                membership.company_id.value, membership.legal_entity_id.value,
                membership.kind.value, membership.exclusive, membership.valid.start,
                membership.valid.end, membership.recorded_at, membership.source_ref,
            ),
        )
