"""Single account within a company chart of accounts.

An account code is a free-form string (no universal numeric-length
assumption per LOT-03 DoD).  Uniqueness is enforced at the chart level.
"""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.identifiers import AccountId, EntityId
from pyaccountingkit.domain.charts.account_role import AccountRole

_MAX_CODE_LENGTH = 50


@dataclass(frozen=True, slots=True)
class CompanyAccount:
    """One leaf or node of the chart of accounts."""

    id: AccountId
    entity_id: EntityId
    code: str
    label: str
    role: AccountRole | None = None
    parent_id: AccountId | None = None
    active: bool = True
    postable: bool = True

    def __post_init__(self) -> None:
        if not self.code or len(self.code) > _MAX_CODE_LENGTH:
            raise ValueError(f"Account code must be 1-{_MAX_CODE_LENGTH} chars, got {self.code!r}")

    def is_active(self) -> bool:
        return self.active

    def deactivated(self) -> CompanyAccount:
        """Return a deactivated copy (company accounts are immutable)."""
        if not self.active:
            return self
        return CompanyAccount(
            id=self.id,
            entity_id=self.entity_id,
            code=self.code,
            label=self.label,
            role=self.role,
            parent_id=self.parent_id,
            active=False,
            postable=self.postable,
        )


__all__ = ["CompanyAccount"]
