"""ORG-5b3c3: membership UoW with independently controlled SQL authority.

The legacy L02 PostgresUnitOfWork remains unchanged. Only the dedicated
OrganizationMembershipService composition path should receive the restricted
membership issuer DSN; the ordinary tenant runtime cannot perform SQL writes.
"""

from ...application.organization_membership_evidence import MembershipTransactionEvidence
from ...domain.organization.model import OrganizationMembership
from ...domain.shared.accounting_scope import ConfigurationScope
from ...domain.shared.errors import InvalidScope
from .adapter import PostgresOrganizationMembershipRepository, PostgresUnitOfWork


class PostgresControlledMembershipRepository(PostgresOrganizationMembershipRepository):
    """Read from tenant-scoped tables; stage mutations in the owning UoW."""

    def append(
        self, *, scope: ConfigurationScope, membership: OrganizationMembership,
    ) -> None:
        self._uow._bind_scope(scope)
        if (
            not isinstance(membership, OrganizationMembership)
            or membership.tenant_id != scope.tenant_id
            or membership.company_id != scope.company_id
            or membership.legal_entity_id != scope.legal_entity_id
        ):
            raise InvalidScope("Membership must match transaction's exact scope")
        if self._uow._pending_membership is not None:
            raise InvalidScope("Only one membership revision may be staged")
        self._uow._pending_membership = membership


class PostgresOrganizationMembershipUnitOfWork(PostgresUnitOfWork):
    """Single-transaction typed membership revision plus native evidence.

    SQL issuer authority is bound to the original session_user and tenant.
    This class does not authenticate the asserted human actor_id.
    """

    def __init__(self, dsn: str, *, before_commit=None) -> None:
        super().__init__(dsn, before_commit=before_commit)
        self._pending_membership: OrganizationMembership | None = None
        self._pending_membership_evidence: MembershipTransactionEvidence | None = None

    def __enter__(self) -> "PostgresOrganizationMembershipUnitOfWork":
        super().__enter__()
        self.org_memberships = PostgresControlledMembershipRepository(self)
        return self

    def append_membership_evidence(
        self, *, scope: ConfigurationScope, evidence: MembershipTransactionEvidence,
    ) -> None:
        self._bind_scope(scope)
        if not isinstance(evidence, MembershipTransactionEvidence):
            raise InvalidScope("Typed membership evidence required")
        pending = self._pending_membership
        if pending is None or self._pending_membership_evidence is not None:
            raise InvalidScope("Exactly one staged membership revision is required")
        if evidence.membership != pending or (
            pending.tenant_id != scope.tenant_id
            or pending.company_id != scope.company_id
            or pending.legal_entity_id != scope.legal_entity_id
        ):
            raise InvalidScope("Membership evidence does not match staged revision")
        self._pending_membership_evidence = evidence

    def commit(self) -> None:
        membership = self._pending_membership
        evidence = self._pending_membership_evidence
        if membership is None or evidence is None or self._connection is None:
            raise RuntimeError("Membership revision and evidence required before commit")
        receipt = evidence.receipt
        self._connection.execute(
            "SELECT company_configuration.register_membership_revision_controlled("
            "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                membership.tenant_id, membership.id.value, membership.revision,
                membership.company_id.value, membership.legal_entity_id.value,
                membership.kind.value, membership.exclusive, membership.valid.start,
                membership.valid.end, membership.recorded_at, membership.source_ref,
                evidence.actor_id, evidence.request_key, evidence.request_digest,
                receipt.correlation_id, receipt.audit_id, receipt.event_id,
                evidence.reason,
            ),
        )
        # Inherited pre-commit fault hook and rollback semantics remain intact.
        super().commit()
