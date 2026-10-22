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

    def canonical_payload(self) -> dict[str, object]:
        """Return the deterministic semantic payload persisted for replay."""
        return {
            "trace_id": self.trace_id,
            "entity_id": str(self.entity_id),
            "accounting_date": self.accounting_date.isoformat(),
            "proposal_checksum": self.proposal_checksum,
            "resolved_account_ids": [str(item) for item in self.resolved_account_ids],
            "journal_entry_id": str(self.journal_entry_id),
            "company_chart_id": self.company_chart_id,
            "company_chart_version": self.company_chart_version,
            "company_chart_reference_snapshot_id": self.company_chart_reference_snapshot_id,
            "policy_set_ids": list(self.policy_set_ids),
            "policy_set_versions": list(self.policy_set_versions),
            "policy_ids": list(self.policy_ids),
            "policy_versions": list(self.policy_versions),
            "policy_reference_snapshot_ids": list(self.policy_reference_snapshot_ids),
            "source_reference": self.source_reference,
        }


__all__ = ["AccountingExecutionTrace"]
