"""ORG-4b PostgreSQL UoW: new company/site/registry row and evidence atomically.

Company registration requires an independently provisioned SQL issuer DSN,
not the ordinary API runtime credential. Establishment and LegalIdentifier
registration have their own independently provisioned issuer DSN (ORG-5b3c1).
No schema-owner DSN is permitted.
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
        self._pending_company: Company | None = None
        self._pending_company_evidence: OrganizationEvidence | None = None
        self._pending_establishment: Establishment | None = None
        self._pending_identifier: tuple[UUID, LegalIdentifier] | None = None
        self._pending_registry_evidence: OrganizationEvidence | None = None

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
        """Stage Company data for the controlled, single-statement SQL command."""
        if not isinstance(company, Company):
            raise InvalidOrganization("Typed company required")
        self._bind(company.tenant_id)
        if self._pending_company is not None:
            raise InvalidOrganization("Only one Company registration per transaction")
        self._pending_company = company

    def insert_establishment(self, site: Establishment) -> None:
        """Stage the object for an independently authorized atomic SQL command."""
        if not isinstance(site, Establishment):
            raise InvalidOrganization("Typed establishment required")
        self._bind(site.tenant_id)
        if self._pending_establishment is not None or self._pending_identifier is not None:
            raise InvalidOrganization("Only one registry registration per transaction")
        self._pending_establishment = site

    def insert_legal_identifier(
        self, identifier_id: UUID, identifier: LegalIdentifier,
    ) -> None:
        if type(identifier_id) is not UUID or not isinstance(identifier, LegalIdentifier):
            raise InvalidOrganization("Typed legal identifier registration required")
        self._bind(identifier.tenant_id)
        if self._pending_establishment is not None or self._pending_identifier is not None:
            raise InvalidOrganization("Only one registry registration per transaction")
        self._pending_identifier = (identifier_id, identifier)

    def append_evidence(self, evidence: OrganizationEvidence) -> None:
        if not isinstance(evidence, OrganizationEvidence):
            raise InvalidOrganization("Typed command evidence required")
        r = evidence.receipt
        self._bind(r.tenant_id)
        if r.target_kind is OrganizationTargetKind.COMPANY:
            if (
                self._pending_company is None
                or self._pending_company.id.value != r.target_id
                or self._pending_company.tenant_id != r.tenant_id
                or evidence.action != "organization.company.register"
                or self._pending_company_evidence is not None
            ):
                raise InvalidOrganization("Company evidence must match staged Company")
            self._pending_company_evidence = evidence
            return
        if r.target_kind is OrganizationTargetKind.ESTABLISHMENT:
            site = self._pending_establishment
            if (
                site is None or site.id.value != r.target_id
                or site.tenant_id != r.tenant_id
                or site.legal_entity_id.value != evidence.legal_entity_id
                or evidence.company_id is not None
                or evidence.action != "organization.establishment.register"
                or self._pending_registry_evidence is not None
            ):
                raise InvalidOrganization("Establishment evidence must match staged object")
        elif r.target_kind is OrganizationTargetKind.LEGAL_IDENTIFIER:
            pending = self._pending_identifier
            if (
                pending is None or pending[0] != r.target_id
                or pending[1].tenant_id != r.tenant_id
                or pending[1].legal_entity_id.value != evidence.legal_entity_id
                or evidence.company_id is not None
                or evidence.action != "organization.legal_identifier.register"
                or self._pending_registry_evidence is not None
            ):
                raise InvalidOrganization("LegalIdentifier evidence must match staged object")
        else:
            raise InvalidOrganization("Unknown registration evidence type")
        self._pending_registry_evidence = evidence

    def commit(self) -> None:
        if self._conn is None or self._committed or self._tenant is None:
            raise RuntimeError("Cannot commit empty or closed registration transaction")
        if self._pending_company is not None:
            item = self._pending_company
            evidence = self._pending_company_evidence
            if evidence is None:
                raise InvalidOrganization("Company requires matching evidence")
            receipt = evidence.receipt
            # The SQL function owns the atomic domain + request/audit/outbox
            # transaction; the ordinary runtime role has no EXECUTE grant.
            self._conn.execute(
                "SELECT company_configuration.register_company_controlled("
                "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    item.tenant_id, item.id.value, item.name, item.kind.value,
                    item.home_country.value,
                    item.base_currency.value if item.base_currency else None,
                    item.status.value, item.revision, evidence.actor_id,
                    evidence.request_key, evidence.request_digest,
                    receipt.correlation_id, receipt.audit_id, receipt.event_id,
                    evidence.reason, evidence.recorded_at,
                ),
            )
        if self._pending_establishment is not None:
            site = self._pending_establishment
            evidence = self._pending_registry_evidence
            if evidence is None:
                raise InvalidOrganization("Establishment requires matching evidence")
            receipt = evidence.receipt
            self._conn.execute(
                "SELECT company_configuration.register_establishment_controlled("
                "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    site.tenant_id, site.id.value, site.legal_entity_id.value,
                    site.name, site.country.value, site.valid.start,
                    site.valid.end, site.status.value, site.revision,
                    evidence.actor_id, evidence.request_key, evidence.request_digest,
                    receipt.correlation_id, receipt.audit_id, receipt.event_id,
                    evidence.reason, evidence.recorded_at,
                ),
            )
        if self._pending_identifier is not None:
            identifier_id, item = self._pending_identifier
            evidence = self._pending_registry_evidence
            if evidence is None:
                raise InvalidOrganization("LegalIdentifier requires matching evidence")
            receipt = evidence.receipt
            self._conn.execute(
                "SELECT company_configuration.register_legal_identifier_controlled("
                "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    item.tenant_id, identifier_id, item.legal_entity_id.value,
                    item.scheme, item.value, item.issuer, item.jurisdiction.value,
                    item.valid.start, item.valid.end, item.source_ref,
                    evidence.actor_id, evidence.request_key, evidence.request_digest,
                    receipt.correlation_id, receipt.audit_id, receipt.event_id,
                    evidence.reason, evidence.recorded_at,
                ),
            )
        if self._before_commit is not None:
            self._before_commit()
        self._conn.commit()
        self._committed = True
