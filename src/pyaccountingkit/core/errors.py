"""Hierarchy of canonical accounting errors for PyAccountingKit.

Every error carries a stable machine-readable ``code`` used for API stability
(see PUBLIC_ERROR_CODES.json) and machine handling. The hierarchy merges the
domain error tree and the accounting rule error tree defined in the canonical
specs (02 and 03).
"""

from __future__ import annotations


class AccountingError(Exception):
    """Root of every PyAccountingKit error."""

    code: str = "PYAK_ERROR"

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message


class CoreError(AccountingError):
    """Root of core-layer errors."""

    code: str = "CORE_ERROR"


class InvalidAmountError(CoreError):
    """A monetary amount violates Money's immutability contract."""

    code: str = "CORE_INVALID_AMOUNT"


class IncompatibleCurrenciesError(CoreError):
    """An operation mixes two distinct currencies without conversion."""

    code: str = "CORE_INCOMPATIBLE_CURRENCIES"


class UnknownCurrencyError(CoreError):
    """A currency lookup failed against the ISO 4217 registry."""

    code: str = "CORE_UNKNOWN_CURRENCY"


class DomainError(AccountingError):
    """Root of domain-layer errors."""

    code: str = "DOMAIN_ERROR"


class EntityScopeMismatchError(DomainError):
    """Objects from different accounting entities were combined in one operation."""

    code: str = "ENTITY_SCOPE_MISMATCH"


class EntryError(DomainError):
    """Root of journal-entry errors."""

    code: str = "ENTRY_ERROR"


class EntryRuleError(EntryError):
    """A universal double-entry rule was violated."""

    code: str = "ENTRY_RULE_ERROR"


class UnbalancedEntryError(EntryRuleError):
    """Debits and credits do not sum equally at the centime."""

    code: str = "ENTRY_UNBALANCED"


class EmptyEntryError(EntryRuleError):
    """An entry must carry at least two accounting lines."""

    code: str = "ENTRY_EMPTY"


class ZeroEntryError(EntryRuleError):
    """A validated entry must not be entirely null."""

    code: str = "ENTRY_ZERO"


class InvalidEntryStateError(EntryError):
    """An entry transition was requested from an incompatible status."""

    code: str = "ENTRY_INVALID_STATE"


class EntryAlreadyPostedError(EntryError):
    """A non-DRAFT entry cannot be posted again."""

    code: str = "ENTRY_ALREADY_POSTED"


class EntryNotPostedError(EntryError):
    """An operation requires a posted entry but the entry is not POSTED."""

    code: str = "ENTRY_NOT_POSTED"


class AlreadyReversedError(EntryError):
    """An entry that is already reversed cannot be reversed again."""

    code: str = "ENTRY_ALREADY_REVERSED"


class EntryNotFoundError(EntryError):
    """A journal entry lookup failed."""

    code: str = "ENTRY_NOT_FOUND"


class JournalLineRuleError(DomainError):
    """A universal accounting-line rule was violated."""

    code: str = "LINE_RULE_ERROR"


class NegativeAmountError(JournalLineRuleError):
    """An accounting line carries a negative amount."""

    code: str = "LINE_NEGATIVE_AMOUNT"


class DebitAndCreditSetError(JournalLineRuleError):
    """A single line cannot debit and credit simultaneously."""

    code: str = "LINE_DEBIT_AND_CREDIT"


class ZeroLineError(JournalLineRuleError):
    """A validated line cannot be zero in both debit and credit."""

    code: str = "LINE_ZERO"


class PeriodError(DomainError):
    """Root of accounting-period errors."""

    code: str = "PERIOD_ERROR"


class PeriodClosedError(PeriodError):
    """An operation is refused because the period is locked or closed."""

    code: str = "PERIOD_CLOSED"


class DateOutsidePeriodError(PeriodError):
    """A business date falls outside its accounting period bounds."""

    code: str = "PERIOD_DATE_OUTSIDE"


class PeriodNotFoundError(PeriodError):
    """An accounting period lookup failed."""

    code: str = "PERIOD_NOT_FOUND"


class JournalNotFoundError(DomainError):
    """A journal lookup failed."""

    code: str = "JOURNAL_NOT_FOUND"


class InactiveJournalError(DomainError):
    """An operation is refused because the journal is deactivated."""

    code: str = "JOURNAL_INACTIVE"


class AccountRuleError(DomainError):
    """Root of account-rule errors."""

    code: str = "ACCOUNT_RULE_ERROR"


class UnknownAccountError(AccountRuleError):
    """An account is not registered in the chart."""

    code: str = "ACCOUNT_UNKNOWN"


class InactiveAccountError(AccountRuleError):
    """An account is deactivated and cannot be used."""

    code: str = "ACCOUNT_INACTIVE"


class NonPostableAccountError(AccountRuleError):
    """An account is not postable in the ledger."""

    code: str = "ACCOUNT_NON_POSTABLE"


class InvalidAccountCodeError(AccountRuleError):
    """An account code is malformed or outside the chart constraints."""

    code: str = "ACCOUNT_INVALID_CODE"


class ChartVersionNotFoundError(AccountRuleError):
    """No company-chart version applies to the requested accounting date."""

    code: str = "CHART_VERSION_NOT_FOUND"


class AmbiguousChartVersionError(AccountRuleError):
    """Several company-chart versions apply to the same accounting date."""

    code: str = "CHART_VERSION_AMBIGUOUS"


class ReversalRuleError(DomainError):
    """Root of reversal rule errors."""

    code: str = "REVERSAL_RULE_ERROR"


class InvalidReversalDateError(ReversalRuleError):
    """A reversal-date policy was violated."""

    code: str = "REVERSAL_INVALID_DATE"


class ConcurrencyError(DomainError):
    """Root of optimistic-concurrency conflicts."""

    code: str = "CONCURRENCY_ERROR"


class RevisionConflictError(ConcurrencyError):
    """An optimistic-lock revision mismatch rejected a mutation."""

    code: str = "CONCURRENCY_REVISION_CONFLICT"


class IdempotencyReplayError(DomainError):
    """A duplicate idempotency key was detected."""

    code: str = "IDEMPOTENCY_REPLAY"


class ControlFailureError(DomainError):
    """A control gate blocked processing on a failed control run."""

    code: str = "CONTROL_FAILED"


class PolicyError(DomainError):
    """Root of accounting-policy errors."""

    code: str = "POLICY_ERROR"


class PolicyNotFoundError(PolicyError):
    """No applicable policy was found for the given context."""

    code: str = "POLICY_NOT_FOUND"


class AmbiguousPolicyResolutionError(PolicyError):
    """Two or more policies matched at the same scope priority (fail-closed)."""

    code: str = "POLICY_AMBIGUOUS_RESOLUTION"


class PolicySetNotActiveError(PolicyError):
    """Current execution attempted to use a non-ACTIVE policy set."""

    code: str = "POLICY_SET_NOT_ACTIVE"


class PolicySetNotEffectiveError(PolicyError):
    """A policy set is outside its effective-date window."""

    code: str = "POLICY_SET_NOT_EFFECTIVE"


class PolicyReferenceMismatchError(PolicyError):
    """Policy context and the pinned regulatory reference do not agree."""

    code: str = "POLICY_REFERENCE_MISMATCH"


class MeasurementError(DomainError):
    """Root of measurement-policy errors."""

    code: str = "MEASUREMENT_ERROR"


class InvalidMeasurementError(MeasurementError):
    """A measurement policy produced an inconsistent result."""

    code: str = "MEASUREMENT_INVALID"


class AccountRoleResolutionError(DomainError):
    """No company account could be resolved for an ``AccountRole`` (fail-closed)."""

    code: str = "ACCOUNT_ROLE_UNRESOLVED"


class AmbiguousAccountRoleError(DomainError):
    """Several company accounts match an ``AccountRole`` with no tie-breaker."""

    code: str = "ACCOUNT_ROLE_AMBIGUOUS"


class ProposalError(DomainError):
    """Root of journal-entry-proposal errors."""

    code: str = "PROPOSAL_ERROR"


class UnbalancedProposalError(ProposalError):
    """A proposal's debits and credits do not balance at the centime."""

    code: str = "PROPOSAL_UNBALANCED"


__all__ = [name for name in globals() if name.endswith("Error")]
