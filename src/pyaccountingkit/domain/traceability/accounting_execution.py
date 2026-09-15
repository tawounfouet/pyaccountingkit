"""End-to-end trace for one accounting execution path.

The trace is an immutable evidence DTO.  It deliberately carries identifiers
and pinned versions only; it owns no repository, service or framework state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pyaccountingkit.core.identifiers import AccountId, EntityId, EntryId


@dataclass(frozen=True, slots=True)
class AccountingExecutionTrace:
    """Pinned coordinates required to explain and replay an accounting run."""

    trace_id: str
    entity_id: EntityId
    accounting_date: date
    proposal_checksum: str
    resolved_account_ids: tuple[AccountId, ...]
    journal_entry_id: EntryId
    company_chart_id: str
    company_chart_version: str
    company_chart_reference_snapshot_id: str
    policy_set_ids: tuple[str, ...] = ()
    policy_set_versions: tuple[str, ...] = ()
    policy_ids: tuple[str, ...] = ()
    policy_versions: tuple[str, ...] = ()
    policy_reference_snapshot_ids: tuple[str, ...] = ()
    source_reference: str = ""


__all__ = ["AccountingExecutionTrace"]
