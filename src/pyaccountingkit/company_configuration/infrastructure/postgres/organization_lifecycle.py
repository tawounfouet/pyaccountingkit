"""ORG-4c SQL adapter: append-only lifecycle projections and atomic evidence.

Reuse 0016 tenant-bound one-connection UoW/lock, with distinct 0017 evidence.
"""

from datetime import datetime
from uuid import UUID

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
    """Stage lifecycle revision and evidence for independently scoped SQL commit.

    This UoW uses a tenant-bound lifecycle issuer DSN, not a runtime login;
    one controlled SQL command atomically appends all four records.
    """

    def __init__(self, dsn: str, *, before_commit=None) -> None:
        super().__init__(dsn, before_commit=before_commit)
        self._pending_lifecycle: (
            tuple[OrganizationTargetKind, str, UUID, int, str, datetime, str] | None
        ) = None
        self._pending_lifecycle_evidence: LifecycleEvidence | None = None


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
        self._stage(
            OrganizationTargetKind.COMPANY, company.tenant_id, company.id.value,
            company.revision, company.status.value, recorded_at, source_ref,
        )

    def append_establishment(
        self, site: Establishment, *, recorded_at: datetime, source_ref: str,
    ) -> None:
        self._bind(site.tenant_id)
        self._stage(
            OrganizationTargetKind.ESTABLISHMENT, site.tenant_id, site.id.value,
            site.revision, site.status.value, recorded_at, source_ref,
        )

    def _stage(
        self, kind: OrganizationTargetKind, tenant: str, target: UUID,
        revision: int, status: str, instant: datetime, source_ref: str,
    ) -> None:
        if self._pending_lifecycle is not None:
            raise RuntimeError("Only one lifecycle transition per transaction")
        self._pending_lifecycle = (
            kind, tenant, target, revision, status, instant, source_ref,
        )

    def append_evidence(self, record: LifecycleEvidence) -> None:
        if not isinstance(record, LifecycleEvidence):
            raise TypeError("Typed LifecycleEvidence required")
        receipt = record.receipt
        self._bind(receipt.tenant_id)
        pending = self._pending_lifecycle
        if pending is None or self._pending_lifecycle_evidence is not None:
            raise RuntimeError("Lifecycle revision must precede unique evidence")
        kind, tenant, target, revision, status, instant, _ = pending
        action = (
            "organization.company.transition"
            if kind is OrganizationTargetKind.COMPANY
            else "organization.establishment.transition"
        )
        if (
            receipt.target_kind is not kind
            or receipt.tenant_id != tenant or receipt.target_id != target
            or receipt.revision != revision or record.action != action
            or record.to_status != status or record.recorded_at != instant
            or record.before_revision != revision - 1
        ):
            raise RuntimeError("Lifecycle evidence must match staged revision")
        self._pending_lifecycle_evidence = record

    def commit(self) -> None:
        pending = self._pending_lifecycle
        evidence = self._pending_lifecycle_evidence
        if pending is None or evidence is None or self._conn is None:
            raise RuntimeError("Lifecycle commit requires revision and evidence")
        kind, tenant, target, revision, status, instant, source_ref = pending
        receipt = evidence.receipt
        # SQL checks actual previous state/revision and original session login
        # before one atomic revision + request/audit/outbox transaction.
        self._conn.execute(
            "SELECT company_configuration.transition_organization_controlled("
            "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                tenant, kind.value, target, revision, evidence.from_status, status,
                instant, source_ref, evidence.actor_id, evidence.request_key,
                evidence.request_digest, receipt.correlation_id, receipt.audit_id,
                receipt.event_id, evidence.reason,
            ),
        )
        super().commit()
