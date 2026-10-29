"""PostgreSQL L02 proof: tenant-scoped repository and one durable local UoW.

This adapter assumes a separately authenticated principal and a non-BYPASSRLS
runtime role. It is not an IAM provider, outbox dispatcher, or C10 endpoint.
"""

from collections.abc import Callable
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from ...application.ports import AuditRecord, ChangeReceipt, PendingEvent
from ...domain.organization.entities import LegalEntity
from ...domain.shared.accounting_scope import ConfigurationScope
from ...domain.shared.errors import InvalidScope, VersionConflict
from ...domain.shared.identifiers import CompanyId, LegalEntityId
from ...domain.shared.references import CurrencyCode, JurisdictionCode


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
            self._connection.execute(
                "SELECT set_config('app.tenant_id', %s, true)", (scope.tenant_id,)
            )
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

    def commit(self) -> None:
        if self._connection is None or self._committed or self._scope is None:
            raise RuntimeError("Cannot commit an empty or closed UnitOfWork")
        if self._before_commit is not None:
            self._before_commit()
        self._connection.commit()
        self._committed = True
