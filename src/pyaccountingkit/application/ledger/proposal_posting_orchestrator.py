"""Canonical application path from a policy proposal to the ledger.

Policies never post directly.  This orchestrator resolves functional account
roles through the versioned chart authority, builds one immutable
``JournalEntry`` and delegates the actual mutation to ``PostingOrchestrator``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pyaccountingkit.application.ledger.posting_orchestrator import PostingOrchestrator
from pyaccountingkit.core.errors import AccountRoleResolutionError
from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.charts.resolution import ResolvedAccount
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.policies.proposal import DebitCredit, JournalEntryProposal
from pyaccountingkit.domain.traceability.accounting_execution import AccountingExecutionTrace
from pyaccountingkit.ports.account_role_resolution import AccountRoleResolverProtocol


@dataclass(frozen=True, slots=True)
class ProposalPostingResult:
    """Result and replay coordinates of posting one validated proposal."""

    posted_entry: JournalEntry
    resolved_accounts: tuple[ResolvedAccount, ...]
    proposal_checksum: str
    execution_trace: AccountingExecutionTrace
    was_replayed: bool = False


class ProposalPostingOrchestrator:
    """Resolve, materialize and post a ``JournalEntryProposal`` safely."""

    def __init__(
        self,
        *,
        account_role_resolver: AccountRoleResolverProtocol,
        posting_orchestrator: PostingOrchestrator,
        entry_id_factory: Callable[[], EntryId],
    ) -> None:
        self._account_role_resolver = account_role_resolver
        self._posting_orchestrator = posting_orchestrator
        self._entry_id_factory = entry_id_factory

    def post(
        self,
        proposal: JournalEntryProposal,
        *,
        journal_id: JournalId,
        period_id: PeriodId,
        actor_id: str,
        description: str | None = None,
    ) -> ProposalPostingResult:
        """Resolve all roles and delegate the accounting mutation to Posting."""
        resolved_accounts = tuple(
            self._account_role_resolver.resolve(
                entity_id=proposal.entity_id,
                accounting_date=proposal.accounting_date,
                role=line.account_role,
            )
            for line in proposal.lines
        )
        self._validate_resolution(proposal, resolved_accounts)

        lines = tuple(
            JournalLine(
                account_id=resolved.account_id,
                debit=(
                    proposal_line.amount
                    if proposal_line.side is DebitCredit.DEBIT
                    else Money.zero(proposal_line.amount.currency)
                ),
                credit=(
                    proposal_line.amount
                    if proposal_line.side is DebitCredit.CREDIT
                    else Money.zero(proposal_line.amount.currency)
                ),
                label=proposal_line.description,
            )
            for proposal_line, resolved in zip(
                proposal.lines,
                resolved_accounts,
                strict=True,
            )
        )
        entry_id = self._entry_id_factory()
        entry = JournalEntry(
            id=entry_id,
            journal_id=journal_id,
            period_id=period_id,
            entry_date=proposal.accounting_date,
            description=description or self._description_for(proposal),
            lines=lines,
        )
        posting_result = self._posting_orchestrator.post(entry, actor_id=actor_id)
        checksum = proposal.checksum()
        first_resolution = resolved_accounts[0]
        execution_trace = AccountingExecutionTrace(
            trace_id=f"acct:{checksum}",
            entity_id=proposal.entity_id,
            accounting_date=proposal.accounting_date,
            proposal_checksum=checksum,
            resolved_account_ids=tuple(item.account_id for item in resolved_accounts),
            journal_entry_id=posting_result.posted_entry.id,
            company_chart_id=first_resolution.chart_id,
            company_chart_version=first_resolution.chart_version,
            company_chart_reference_snapshot_id=first_resolution.reference_snapshot_id,
            policy_set_ids=tuple(trace.policy_set_id for trace in proposal.policy_traces),
            policy_set_versions=tuple(trace.policy_set_version for trace in proposal.policy_traces),
            policy_ids=tuple(trace.policy_id for trace in proposal.policy_traces),
            policy_versions=tuple(trace.policy_version for trace in proposal.policy_traces),
            policy_reference_snapshot_ids=tuple(
                trace.reference_snapshot_id
                for trace in proposal.policy_traces
                if trace.reference_snapshot_id is not None
            ),
            source_reference=proposal.source_reference,
        )
        return ProposalPostingResult(
            posted_entry=posting_result.posted_entry,
            resolved_accounts=resolved_accounts,
            proposal_checksum=checksum,
            execution_trace=execution_trace,
            was_replayed=posting_result.was_replayed,
        )

    @staticmethod
    def _validate_resolution(
        proposal: JournalEntryProposal,
        resolved_accounts: tuple[ResolvedAccount, ...],
    ) -> None:
        if len(resolved_accounts) != len(proposal.lines):
            raise AccountRoleResolutionError("not every proposal line resolved to one account")
        first = resolved_accounts[0]
        for line, resolved in zip(proposal.lines, resolved_accounts, strict=True):
            if resolved.entity_id != proposal.entity_id:
                raise AccountRoleResolutionError(
                    f"resolved account {resolved.account_id} belongs to {resolved.entity_id}, "
                    f"expected {proposal.entity_id}"
                )
            if (
                resolved.chart_id != first.chart_id
                or resolved.chart_version != first.chart_version
                or resolved.reference_snapshot_id != first.reference_snapshot_id
            ):
                raise AccountRoleResolutionError(
                    "proposal lines resolved through different company-chart coordinates"
                )
            if line.resolved_account_id is not None:
                if line.resolved_account_id != str(resolved.account_id):
                    raise AccountRoleResolutionError(
                        f"pinned account {line.resolved_account_id!r} does not match "
                        f"resolved account {resolved.account_id!s}"
                    )

    @staticmethod
    def _description_for(proposal: JournalEntryProposal) -> str:
        if proposal.source_reference:
            return f"{proposal.entry_type} — {proposal.source_reference}"
        return proposal.entry_type


__all__ = ["ProposalPostingOrchestrator", "ProposalPostingResult"]
