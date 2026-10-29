"""ORG-4c SQL adapter: append-only lifecycle projections and atomic evidence.

Reuse 0016 tenant-bound one-connection UoW/lock, with distinct 0017 evidence.
"""

from datetime import datetime

from ...application.organization_lifecycle import LifecycleEvidence, LifecycleReceipt
from ...application.organization_registration import OrganizationTargetKind
from ...domain.organization.model import (
    Company,
    CompanyKind,
    CompanyStatus,
    Establishment,
    EstablishmentStatus,
)
from ...domain.shared.effective_interval import EffectiveInterval
from ...domain.shared.identifiers import CompanyId, EstablishmentId, LegalEntityId
from ...domain.shared.references import CurrencyCode, JurisdictionCode
from .organization_registration import PostgresOrganizationRegistrationUnitOfWork


class PostgresOrganizationLifecycleUnitOfWork(PostgresOrganizationRegistrationUnitOfWork):
    """All reads, history inserts and three evidence inserts share one transaction."""

    def lookup(
        self, *, tenant_id: str, actor_id: str, action: str, request_key: str,
    ) -> tuple[str, LifecycleReceipt] | None:
        self._bind(tenant_id)
        row = self._conn.execute(
            "SELECT request_digest,target_kind,target_id,revision,correlation_id,"
            "audit_id,event_id FROM company_configuration.organization_lifecycle_requests "
            "WHERE tenant_id=%s AND actor_id=%s AND action=%s AND request_key=%s",
            (tenant_id, actor_id, action, request_key),
        ).fetchone()
        if row is None:
            return None
        receipt = LifecycleReceipt(
            tenant_id, OrganizationTargetKind(row["target_kind"]),
            row["target_id"], row["revision"], row["correlation_id"],
            row["audit_id"], row["event_id"],
        )
        return row["request_digest"].strip(), receipt

    def company(self, *, tenant_id: str, company_id: CompanyId) -> Company | None:
        self._bind(tenant_id)
        row = self._conn.execute(
            "SELECT c.*,COALESCE(r.status,c.status) current_status,"
            "COALESCE(r.revision,c.revision) current_revision "
            "FROM company_configuration.organizational_companies c "
            "LEFT JOIN LATERAL ("
            "SELECT status,revision FROM company_configuration.organizational_company_revisions "
            "WHERE tenant_id=c.tenant_id AND company_id=c.company_id "
            "ORDER BY revision DESC LIMIT 1) r ON true "
            "WHERE c.tenant_id=%s AND c.company_id=%s",
            (tenant_id, company_id.value),
        ).fetchone()
        if row is None:
            return None
        return Company(
            CompanyId(row["company_id"]), row["tenant_id"], row["name"],
            CompanyKind(row["kind"]), JurisdictionCode(row["home_country"].strip()),
            CurrencyCode(row["base_currency"].strip()) if row["base_currency"] else None,
            CompanyStatus(row["current_status"]), row["current_revision"],
        )

    def establishment(
        self, *, tenant_id: str, establishment_id: EstablishmentId,
    ) -> Establishment | None:
        self._bind(tenant_id)
        row = self._conn.execute(
            "SELECT e.*,COALESCE(r.status,e.status) current_status,"
            "COALESCE(r.revision,e.revision) current_revision "
            "FROM company_configuration.organizational_establishments e "
            "LEFT JOIN LATERAL ("
            "SELECT status,revision FROM "
            "company_configuration.organizational_establishment_revisions "
            "WHERE tenant_id=e.tenant_id AND establishment_id=e.establishment_id "
            "ORDER BY revision DESC LIMIT 1) r ON true "
            "WHERE e.tenant_id=%s AND e.establishment_id=%s",
            (tenant_id, establishment_id.value),
        ).fetchone()
        if row is None:
            return None
        return Establishment(
            EstablishmentId(row["establishment_id"]), row["tenant_id"],
            LegalEntityId(row["legal_entity_id"]), row["name"],
            JurisdictionCode(row["country"].strip()),
            EffectiveInterval(row["valid_from"], row["valid_to"]),
            EstablishmentStatus(row["current_status"]), row["current_revision"],
        )

    def append_company(
        self, company: Company, *, recorded_at: datetime, source_ref: str,
    ) -> None:
        self._bind(company.tenant_id)
        self._conn.execute(
            "INSERT INTO company_configuration.organizational_company_revisions "
            "(tenant_id,company_id,revision,status,recorded_at,source_ref) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (
                company.tenant_id, company.id.value, company.revision,
                company.status.value, recorded_at, source_ref,
            ),
        )

    def append_establishment(
        self, site: Establishment, *, recorded_at: datetime, source_ref: str,
    ) -> None:
        self._bind(site.tenant_id)
        self._conn.execute(
            "INSERT INTO company_configuration.organizational_establishment_revisions "
            "(tenant_id,establishment_id,revision,status,recorded_at,source_ref) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (
                site.tenant_id, site.id.value, site.revision, site.status.value,
                recorded_at, source_ref,
            ),
        )

    def append_evidence(self, record: LifecycleEvidence) -> None:
        receipt = record.receipt
        self._bind(receipt.tenant_id)
        self._conn.execute(
            "INSERT INTO company_configuration.organization_lifecycle_audit "
            "(record_id,tenant_id,actor_id,action,target_kind,target_id,"
            "before_revision,after_revision,from_status,to_status,reason,"
            "correlation_id,recorded_at) VALUES "
            "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                receipt.audit_id, receipt.tenant_id, record.actor_id, record.action,
                receipt.target_kind.value, receipt.target_id,
                record.before_revision, receipt.revision, record.from_status,
                record.to_status, record.reason, receipt.correlation_id,
                record.recorded_at,
            ),
        )
        self._conn.execute(
            "INSERT INTO company_configuration.organization_lifecycle_outbox "
            "(event_id,tenant_id,event_type,schema_version,target_kind,target_id,"
            "revision,from_status,to_status,correlation_id,recorded_at) VALUES "
            "(%s,%s,%s,1,%s,%s,%s,%s,%s,%s,%s)",
            (
                receipt.event_id, receipt.tenant_id, record.action,
                receipt.target_kind.value, receipt.target_id, receipt.revision,
                record.from_status, record.to_status, receipt.correlation_id,
                record.recorded_at,
            ),
        )
        self._conn.execute(
            "INSERT INTO company_configuration.organization_lifecycle_requests "
            "(tenant_id,actor_id,action,request_key,request_digest,target_kind,"
            "target_id,revision,correlation_id,audit_id,event_id) VALUES "
            "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                receipt.tenant_id, record.actor_id, record.action,
                record.request_key, record.request_digest, receipt.target_kind.value,
                receipt.target_id, receipt.revision, receipt.correlation_id,
                receipt.audit_id, receipt.event_id,
            ),
        )
