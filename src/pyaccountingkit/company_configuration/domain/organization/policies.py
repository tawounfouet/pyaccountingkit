"""L03 pure organizational policies: deterministic temporal read, no hidden now().

Membership history is append-only in concept: each correction is a new,
later-known revision. The authoritative database will enforce the same
constraints in ORG-3; these pure functions do not provide SQL isolation.
"""

from collections.abc import Iterable
from datetime import date, datetime

from ..shared.errors import AmbiguousOrganization, InvalidOrganization, OrganizationConflict
from ..shared.identifiers import LegalEntityId
from .model import (
    LegalIdentifier,
    OrganizationMembership,
    _utc,
)


def require_unique_legal_identifier(
    candidate: LegalIdentifier, existing: Iterable[LegalIdentifier]
) -> None:
    """ORG-INV-02: no two entities claim an overlapping scoped registry identifier."""
    if not isinstance(candidate, LegalIdentifier):
        raise InvalidOrganization("Typed LegalIdentifier required")
    for prior in existing:
        if not isinstance(prior, LegalIdentifier):
            raise InvalidOrganization("Typed registry identity required")
        if (
            prior.tenant_id == candidate.tenant_id
            and prior.legal_entity_id != candidate.legal_entity_id
            and prior.scheme == candidate.scheme
            and prior.issuer == candidate.issuer
            and prior.jurisdiction == candidate.jurisdiction
            and prior.value == candidate.value
            and prior.valid.overlaps(candidate.valid)
        ):
            raise OrganizationConflict("Conflicting legal identifier in registry and period")


def _latest_membership_versions(
    records: Iterable[OrganizationMembership], *, known_at: datetime,
) -> tuple[OrganizationMembership, ...]:
    """Choose latest known revision per membership, independent of input order."""
    knowledge_cutoff = _utc(known_at)
    versions: dict[tuple[str, object], list[OrganizationMembership]] = {}
    for record in records:
        if not isinstance(record, OrganizationMembership):
            raise InvalidOrganization("Typed OrganizationMembership required")
        versions.setdefault((record.tenant_id, record.id), []).append(record)
    result: list[OrganizationMembership] = []
    for history in versions.values():
        history.sort(key=lambda m: m.revision)
        for position, version in enumerate(history, start=1):
            # Do not infer missing history or backfill a knowledge sequence.
            if version.revision != position:
                raise OrganizationConflict("Missing membership historical revision")
            if position > 1:
                previous = history[position - 2]
                if (
                    _utc(version.recorded_at) <= _utc(previous.recorded_at)
                    or version.company_id != previous.company_id
                    or version.legal_entity_id != previous.legal_entity_id
                    or version.kind != previous.kind
                    or version.exclusive != previous.exclusive
                ):
                    raise OrganizationConflict("Membership identity/history corruption")
        visible = [
            item for item in history if _utc(item.recorded_at) <= knowledge_cutoff
        ]
        if visible:
            result.append(visible[-1])
    return tuple(result)


def active_memberships_at(
    records: Iterable[OrganizationMembership],
    *,
    tenant_id: str,
    legal_entity_id: LegalEntityId,
    effective_on: date,
    known_at: datetime,
) -> tuple[OrganizationMembership, ...]:
    """Resolve as-known affiliations for the effective date; reject ambiguity.

    No ledger, consolidation or shareholder-control inference is permitted.
    Nonexclusive affiliations may coexist; exclusive membership cannot overlap
    any other membership of the same kind for this legal entity and tenant.
    """
    if (
        not isinstance(tenant_id, str) or not tenant_id or tenant_id.strip() != tenant_id
        or not isinstance(legal_entity_id, LegalEntityId)
        or type(effective_on) is not date
    ):
        raise InvalidOrganization("Explicit typed tenant, entity and effective date required")
    candidates = tuple(
        record for record in _latest_membership_versions(records, known_at=known_at)
        if record.tenant_id == tenant_id
        and record.legal_entity_id == legal_entity_id
        and record.valid.contains(effective_on)
    )
    for index, left in enumerate(candidates):
        for right in candidates[index + 1:]:
            if left.kind == right.kind and (left.exclusive or right.exclusive):
                raise AmbiguousOrganization("Overlapping exclusive organization memberships")
    return tuple(sorted(candidates, key=lambda m: (m.kind.value, str(m.id))))


def require_no_exclusive_membership_conflicts(
    records: Iterable[OrganizationMembership], *, known_at: datetime,
) -> None:
    """Check all *known* effective intervals, not merely today's membership."""
    active = _latest_membership_versions(records, known_at=known_at)
    for index, left in enumerate(active):
        for right in active[index + 1:]:
            if (
                left.tenant_id == right.tenant_id
                and left.legal_entity_id == right.legal_entity_id
                and left.kind == right.kind
                and (left.exclusive or right.exclusive)
                and left.valid.overlaps(right.valid)
            ):
                raise OrganizationConflict("Overlapping exclusive organization validity")
