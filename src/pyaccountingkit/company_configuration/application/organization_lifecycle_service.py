"""ORG-4c Application Service: explicit DDD state transitions and atomic evidence."""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..domain.shared.digest import ContentDigest
from ..domain.shared.errors import VersionConflict
from .organization_lifecycle import (
    LifecycleEvidence,
    LifecycleReceipt,
    OrganizationLifecycleUnitOfWork,
    TransitionCompany,
    TransitionEstablishment,
)
from .organization_registration import (
    OrganizationRegistrationAuthorizationPort,
    OrganizationTargetKind,
)
from .ports import ClockPort, TrustedPrincipal
from .service import IdempotencyConflict, PermissionDenied, SystemClock


class OrganizationLifecycleService:
    """Fail-closed authorization, optimistic revision, one durable transaction."""

    def __init__(
        self,
        uow_factory: Callable[[], OrganizationLifecycleUnitOfWork],
        authorization: OrganizationRegistrationAuthorizationPort,
        clock: ClockPort | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._authorization = authorization
        self._clock = clock if clock is not None else SystemClock()

    def _execute(
        self, *, principal: TrustedPrincipal, action: str, tenant_id: str,
        kind: OrganizationTargetKind, target_id: UUID, to_status: str,
        expected_revision: int, source_ref: str, request_id: str,
        correlation_id: str, reason: str,
        transition: Callable[[OrganizationLifecycleUnitOfWork], tuple[str, int]],
        append: Callable[[OrganizationLifecycleUnitOfWork, datetime], None],
    ) -> LifecycleReceipt:
        if not isinstance(principal, TrustedPrincipal) or principal.tenant_id != tenant_id:
            raise PermissionDenied("Verified same-tenant principal required")
        self._authorization.require(
            principal=principal, action=action, tenant_id=tenant_id
        )
        digest = ContentDigest.from_canonical_json({
            "tenant": tenant_id, "kind": kind.value, "id": str(target_id),
            "action": action, "to_status": to_status,
            "expected_revision": expected_revision, "source_ref": source_ref,
            "correlation_id": correlation_id, "reason": reason,
        }).hex_sha256
        with self._uow_factory() as uow:
            prior = uow.lookup(
                tenant_id=tenant_id, actor_id=principal.actor_id,
                action=action, request_key=request_id,
            )
            if prior is not None:
                old_digest, receipt = prior
                if old_digest != digest:
                    raise IdempotencyConflict("Idempotency key reused for another transition")
                return receipt
            from_status, revised = transition(uow)
            if revised != expected_revision + 1:
                raise VersionConflict("Unexpected lifecycle revision")
            now = self._clock.now()
            if type(now) is not datetime or now.utcoffset() is None:
                raise ValueError("Clock requires a timezone-aware timestamp")
            now = now.astimezone(UTC)
            receipt = LifecycleReceipt(
                tenant_id, kind, target_id, revised, correlation_id, uuid4(), uuid4()
            )
            append(uow, now)
            uow.append_evidence(LifecycleEvidence(
                receipt, principal.actor_id, action, request_id, digest,
                from_status, to_status, reason, expected_revision, now,
            ))
            uow.commit()
            return receipt

    def transition_company(
        self, command: TransitionCompany, *, principal: TrustedPrincipal,
    ) -> LifecycleReceipt:
        if not isinstance(command, TransitionCompany):
            raise TypeError("Expected TransitionCompany")
        changed: list = []

        def transition(uow: OrganizationLifecycleUnitOfWork) -> tuple[str, int]:
            current = uow.company(
                tenant_id=command.tenant_id, company_id=command.company_id,
            )
            if current is None:
                raise VersionConflict("Company missing in authorized tenant")
            next_state = current.transition(
                to=command.to_status, expected_revision=command.expected_revision,
            )
            changed.append(next_state)
            return current.status.value, next_state.revision

        return self._execute(
            principal=principal, action="organization.company.transition",
            tenant_id=command.tenant_id, kind=OrganizationTargetKind.COMPANY,
            target_id=command.company_id.value, to_status=command.to_status.value,
            expected_revision=command.expected_revision, source_ref=command.source_ref,
            request_id=command.request_id, correlation_id=command.correlation_id,
            reason=command.reason, transition=transition,
            append=lambda uow, instant: uow.append_company(
                changed[0], recorded_at=instant, source_ref=command.source_ref
            ),
        )

    def transition_establishment(
        self, command: TransitionEstablishment, *, principal: TrustedPrincipal,
    ) -> LifecycleReceipt:
        if not isinstance(command, TransitionEstablishment):
            raise TypeError("Expected TransitionEstablishment")
        changed: list = []

        def transition(uow: OrganizationLifecycleUnitOfWork) -> tuple[str, int]:
            current = uow.establishment(
                tenant_id=command.tenant_id,
                establishment_id=command.establishment_id,
            )
            if current is None:
                raise VersionConflict("Establishment missing in authorized tenant")
            next_state = current.transition(
                to=command.to_status, expected_revision=command.expected_revision,
            )
            changed.append(next_state)
            return current.status.value, next_state.revision

        return self._execute(
            principal=principal, action="organization.establishment.transition",
            tenant_id=command.tenant_id, kind=OrganizationTargetKind.ESTABLISHMENT,
            target_id=command.establishment_id.value, to_status=command.to_status.value,
            expected_revision=command.expected_revision, source_ref=command.source_ref,
            request_id=command.request_id, correlation_id=command.correlation_id,
            reason=command.reason, transition=transition,
            append=lambda uow, instant: uow.append_establishment(
                changed[0], recorded_at=instant, source_ref=command.source_ref
            ),
        )
