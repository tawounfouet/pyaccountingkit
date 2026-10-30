"""L03 ORG-2/3 PostgreSQL adapter; guarded tenant-bound writes and temporal reads.

This adapter is not a public IAM endpoint or an audited application command.
ORG-4 will wrap it with authenticated commands, idempotency and Outbox UoW.
"""

from datetime import date, datetime
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from ...domain.organization.model import (
    Company,
    Establishment,
    LegalIdentifier,
    MembershipKind,
    OrganizationMembership,
)
from ...domain.organization.policies import active_memberships_at
from ...domain.shared.effective_interval import EffectiveInterval
from ...domain.shared.errors import InvalidOrganization
from ...domain.shared.identifiers import CompanyId, LegalEntityId, MembershipId
from .tenant_boundary import require_tenant_connection


class PostgresOrganizationRepository:
    """Open a new scoped SQL transaction for each operation, no schema-owner DSN."""

    def __init__(self, dsn: str) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("Explicit tenant-bound PostgreSQL DSN required")
        self._dsn = dsn

    def __repr__(self) -> str:
        return "PostgresOrganizationRepository(dsn=<redacted>)"

    def add_company(self, company: Company) -> None:
        if not isinstance(company, Company):
            raise InvalidOrganization("Typed Company required")
        with psycopg.connect(self._dsn) as conn:
            require_tenant_connection(conn, company.tenant_id)
            conn.execute(
                "INSERT INTO company_configuration.organizational_companies "
                "(tenant_id,company_id,name,kind,home_country,base_currency,status,revision) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    company.tenant_id, company.id.value, company.name,
                    company.kind.value, company.home_country.value,
                    company.base_currency.value if company.base_currency else None,
                    company.status.value, company.revision,
                ),
            )

    def add_establishment(self, site: Establishment) -> None:
        if not isinstance(site, Establishment):
            raise InvalidOrganization("Typed Establishment required")
        with psycopg.connect(self._dsn) as conn:
            require_tenant_connection(conn, site.tenant_id)
            conn.execute(
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

    def add_legal_identifier(self, item: LegalIdentifier) -> UUID:
        if not isinstance(item, LegalIdentifier):
            raise InvalidOrganization("Typed LegalIdentifier required")
        identifier_id = uuid4()
        with psycopg.connect(self._dsn) as conn:
            require_tenant_connection(conn, item.tenant_id)
            conn.execute(
                "INSERT INTO company_configuration.organizational_legal_identifiers "
                "(tenant_id,identifier_id,legal_entity_id,scheme,value,issuer,"
                "jurisdiction,valid_from,valid_to,source_ref) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    item.tenant_id, identifier_id, item.legal_entity_id.value,
                    item.scheme, item.value, item.issuer, item.jurisdiction.value,
                    item.valid.start, item.valid.end, item.source_ref,
                ),
            )
        return identifier_id

    def append_membership(self, item: OrganizationMembership) -> None:
        """Append a revision; DB trigger rejects gaps, re-parenting and overlap."""
        if not isinstance(item, OrganizationMembership):
            raise InvalidOrganization("Typed OrganizationMembership required")
        with psycopg.connect(self._dsn) as conn:
            require_tenant_connection(conn, item.tenant_id)
            conn.execute(
                "INSERT INTO company_configuration.organizational_membership_revisions "
                "(tenant_id,membership_id,revision,company_id,legal_entity_id,"
                "kind,exclusive,valid_from,valid_to,recorded_at,source_ref) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    item.tenant_id, item.id.value, item.revision,
                    item.company_id.value, item.legal_entity_id.value,
                    item.kind.value, item.exclusive, item.valid.start,
                    item.valid.end, item.recorded_at, item.source_ref,
                ),
            )

    def memberships_at(
        self, *, tenant_id: str, legal_entity_id: LegalEntityId,
        effective_on: date, known_at: datetime,
    ) -> tuple[OrganizationMembership, ...]:
        """No implicit business or knowledge date; RLS also constrains reads."""
        if not isinstance(legal_entity_id, LegalEntityId):
            raise InvalidOrganization("Typed entity id required")
        # Validate dates even when SQL contains no matching history.
        from ...domain.organization.model import _utc

        _utc(known_at)
        if type(effective_on) is not date:
            raise InvalidOrganization("Explicit business date required")
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            require_tenant_connection(conn, tenant_id)
            rows = conn.execute(
                "SELECT * FROM company_configuration.organizational_membership_revisions "
                "WHERE tenant_id=%s AND legal_entity_id=%s AND recorded_at<=%s "
                "ORDER BY membership_id,revision",
                (tenant_id, legal_entity_id.value, known_at),
            ).fetchall()
        versions = tuple(
            OrganizationMembership(
                MembershipId(row["membership_id"]), row["tenant_id"],
                CompanyId(row["company_id"]), LegalEntityId(row["legal_entity_id"]),
                MembershipKind(row["kind"]), row["exclusive"],
                EffectiveInterval(row["valid_from"], row["valid_to"]),
                row["recorded_at"], row["source_ref"], row["revision"],
            )
            for row in rows
        )
        return active_memberships_at(
            versions, tenant_id=tenant_id, legal_entity_id=legal_entity_id,
            effective_on=effective_on, known_at=known_at,
        )
