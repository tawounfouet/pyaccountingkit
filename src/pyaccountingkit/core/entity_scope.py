"""Canonical AccountingEntity isolation guards.

Every accounting mutation in PyAccountingKit belongs to one and only one
``AccountingEntity``.  Cross-context orchestration calls this module instead
of reimplementing ad-hoc comparisons in each bounded context.
"""

from __future__ import annotations

from collections.abc import Iterable

from pyaccountingkit.core.errors import EntityScopeMismatchError
from pyaccountingkit.core.identifiers import EntityId


def require_same_entity(
    expected: EntityId,
    actual: EntityId,
    *,
    resource: str,
) -> None:
    """Reject a resource that does not belong to the expected entity."""
    if actual != expected:
        raise EntityScopeMismatchError(
            f"{resource} belongs to entity {actual!s}, expected {expected!s}"
        )


def require_all_same_entity(
    expected: EntityId,
    resources: Iterable[tuple[str, EntityId]],
) -> None:
    """Apply :func:`require_same_entity` to a sequence of named resources."""
    for resource, actual in resources:
        require_same_entity(expected, actual, resource=resource)


__all__ = ["require_all_same_entity", "require_same_entity"]
