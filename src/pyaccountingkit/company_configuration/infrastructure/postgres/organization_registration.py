"""ORG-4b PostgreSQL UoW: new company/site/registry row and evidence atomically.

A tenant-bound runtime DSN is mandatory, NOT a schema-owner DSN. Uses the
same tenant advisory locking namespace as L02's transactional commands.
"""

from collections.abc import Callable
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from ...application.organization_registration import (
    OrganizationEvidence,
    OrganizationRegistrationReceipt,
    OrganizationTargetKind,
)
from ...domain.organization.model import Company, Establishment, LegalIdentifier
from ...domain.shared.errors import InvalidOrganization
from .tenant_boundary import require_tenant_connection


class PostgresOrganizationRegistrationUnitOfWork:
    def __init__(
        self, dsn: str, *, before_commit: Callable[[], None] | None = None,
    ) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("An explicit tenant-bound DSN is required")
        self._dsn = dsn
        self._before_commit = before_commit
        self._conn: psycopg.Connection | None = None
        self._tenant: str | None = None
        self._committed = False

    def __enter__(self) -> "PostgresOrganizationRegistrationUnitOfWork":
        if self._conn is not None:
            raise RuntimeError("Registration UoW cannot be entered twice")
        self._conn = psycopg.connect(self._dsn, row_factory=dict_row)
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._conn is not None:
            try:
                if not self._committed:
                    self._conn.rollback()
            finally:
                self._conn.close()
                self._conn = None
                self._tenant = None

    def _bind(self, tenant_id: str) -> None:
        if self._conn is None or self._committed:
            raise RuntimeError("Registration UoW is not active")
        if self._tenant is None:
            require_tenant_connection(self._conn, tenant_id)
            self._conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                ("cc:tenant:" + tenant_id,),
            )
            self._tenant = tenant_id
        elif self._tenant != tenant_id:
            raise InvalidOrganization("A transaction cannot cross tenant boundaries")

    def lookup(
        self, *, tenant_id: str, actor_id: str, action: str, request_key: str,
    ) -> tuple[str, OrganizationRegistrationReceipt] | None:
        self._bind(tenant_id)
        row = self._conn.execute(
            "SELECT request_digest,target_kind,target_id,revision,correlation_id,"
            "audit_id,event_id FROM company_configuration.organization_command_requests "
            "WHERE tenant_id=%s AND actor_id=%s AND action=%s AND request_key=%s",
            (tenant_id, actor_id, action, request_key),
        ).fetchone()
        if row is None:
            return None
        receipt = OrganizationRegistrationReceipt(
            tenant_id=tenant_id, target_kind=OrganizationTargetKind(row["target_kind"]),
            target_id=row["target_id"], revision=row["revision"],
            correlation_id=row["correlation_id"], audit_id=row["audit_id"],
            event_id=row["event_id"],
        )
        return row["request_digest"].strip(), receipt

    def insert_company(self, company: Company) -> None:
        if not isinstance(company, Company):
            raise InvalidOrganization("Typed company required")
        self._bind(company.tenant_id)
        self._conn.execute(
            "INSERT INTO company_configuration.organizational_companies "
            "(tenant_id,company_id,name,kind,home_country,base_currency,status,revision) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                company.tenant_id, company.id.value, company.name, company.kind.value,
                company.home_country.value,
                company.base_currency.value if company.base_currency else None,
                company.status.value, company.revision,
            ),
        )

    def insert_establishment(self, site: Establishment) -> None:
        if not isinstance(site, Establishment):
            raise InvalidOrganization("Typed establishment required")
        self._bind(site.tenant_id)
        self._conn.execute(
            "INSERT INTO company_configuration.organizational_establishments "
            "(tenant_id,establishment_id,legal_entity_id,name,country,"
            "valid_from,valid_to,status,revision) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                site.tenant_id, site.id.value, site.legal_entity_id.value,
                site.name, site.country.value, site.valid.start, site.valid.end,
                site.status.value, site.revision,
            ),
        )

    def insert_legal_identifier(
        self, identifier_id: UUID, identifier: LegalIdentifier,
    ) -> None:
        if type(identifier_id) is not UUID or not isinstance(identifier, LegalIdentifier):
            raise InvalidOrganization("Typed legal identifier registration required")
        self._bind(identifier.tenant_id)
        self._conn.execute(
            "INSERT INTO company_configuration.organizational_legal_identifiers "
            "(tenant_id,identifier_id,legal_entity_id,scheme,value,issuer,"
            "jurisdiction,valid_from,valid_to,source_ref) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                identifier.tenant_id, identifier_id, identifier.legal_entity_id.value,
                identifier.scheme, identifier.value, identifier.issuer,
                identifier.jurisdiction.value, identifier.valid.start,
                identifier.valid.end, identifier.source_ref,
            ),
        )

    def append_evidence(self, evidence: OrganizationEvidence) -> None:
        if not isinstance(evidence, OrganizationEvidence):
            raise InvalidOrganization("Typed command evidence required")
        r = evidence.receipt
        self._bind(r.tenant_id)
        self._conn.execute(
            "INSERT INTO company_configuration.organization_command_audit "
            "(record_id,tenant_id,actor_id,action,target_kind,target_id,"
            "company_id,legal_entity_id,before_revision,after_revision,reason,"
            "correlation_id,recorded_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,0,%s,%s,%s,%s)",
            (
                r.audit_id, r.tenant_id, evidence.actor_id, evidence.action,
                r.target_kind.value, r.target_id, evidence.company_id,
                evidence.legal_entity_id, r.revision, evidence.reason,
                r.correlation_id, evidence.recorded_at,
            ),
        )
        self._conn.execute(
            "INSERT INTO company_configuration.organization_command_outbox "
            "(event_id,tenant_id,event_type,schema_version,target_kind,target_id,"
            "company_id,legal_entity_id,revision,correlation_id,recorded_at) "
            "VALUES (%s,%s,%s,1,%s,%s,%s,%s,%s,%s,%s)",
            (
                r.event_id, r.tenant_id, evidence.action, r.target_kind.value,
                r.target_id, evidence.company_id, evidence.legal_entity_id,
                r.revision, r.correlation_id, evidence.recorded_at,
            ),
        )
        self._conn.execute(
            "INSERT INTO company_configuration.organization_command_requests "
            "(tenant_id,actor_id,action,request_key,request_digest,target_kind,"
            "target_id,revision,correlation_id,audit_id,event_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                r.tenant_id, evidence.actor_id, evidence.action,
                evidence.request_key, evidence.request_digest, r.target_kind.value,
                r.target_id, r.revision, r.correlation_id, r.audit_id, r.event_id,
            ),
        )

    def commit(self) -> None:
        if self._conn is None or self._committed or self._tenant is None:
            raise RuntimeError("Cannot commit empty or closed registration transaction")
        if self._before_commit is not None:
            self._before_commit()
        self._conn.commit()
        self._committed = True
