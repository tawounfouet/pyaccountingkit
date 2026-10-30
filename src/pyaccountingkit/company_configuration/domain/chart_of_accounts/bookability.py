"""L05-02 — proposed account status + local bookability prerequisites.

An enabled proposal plus a leaf shape is *not* a published chart, account
eligibility, a fiscal-period decision, a live authorization or posting right.
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum

from ..shared.accounting_scope import ConfigurationScope
from ..shared.effective_interval import EffectiveInterval
from ..shared.errors import DomainError
from ..shared.identifiers import (
    AccountStatusCandidateId,
    CompanyAccountId,
    CompanyChartId,
)
from .hierarchy import (
    AccountHierarchyEdgeCandidate,
    validate_candidate_account_hierarchy,
)
from .model import (
    AccountCode,
    CompanyAccountDraft,
    CompanyChartDraft,
    require_account_belongs_to_chart,
)


class InvalidAccountStatusCandidate(DomainError):
    code = "INVALID_ACCOUNT_STATUS_CANDIDATE"


class AccountStatusCandidateMissing(DomainError):
    code = "ACCOUNT_STATUS_CANDIDATE_MISSING"


class AccountStatusCandidateAmbiguous(DomainError):
    code = "ACCOUNT_STATUS_CANDIDATE_AMBIGUOUS"


class AccountBookabilityCandidateDenied(DomainError):
    """Denied draft prerequisite, never a Ledger denial or posting response."""

    code = "ACCOUNT_BOOKABILITY_CANDIDATE_DENIED"


class AccountStatusProposal(Enum):
    """Shape-only candidate lifecycle; not certified or published account state."""

    DRAFT = "DRAFT"
    PROPOSED_ENABLED = "PROPOSED_ENABLED"
    PROPOSED_SUSPENDED = "PROPOSED_SUSPENDED"
    PROPOSED_RETIRED = "PROPOSED_RETIRED"


@dataclass(frozen=True, slots=True)
class AccountStatusCandidate:
    id: AccountStatusCandidateId
    scope: ConfigurationScope
    chart_id: CompanyChartId
    account_id: CompanyAccountId
    status: AccountStatusProposal
    effective: EffectiveInterval
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, AccountStatusCandidateId):
            raise InvalidAccountStatusCandidate("Typed status identity required")
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is not None:
            raise InvalidAccountStatusCandidate("Entity-level status scope required")
        if not isinstance(self.chart_id, CompanyChartId):
            raise InvalidAccountStatusCandidate("Typed chart ID required")
        if not isinstance(self.account_id, CompanyAccountId):
            raise InvalidAccountStatusCandidate("Typed account ID required")
        if not isinstance(self.status, AccountStatusProposal):
            raise InvalidAccountStatusCandidate("Typed status proposal required")
        if not isinstance(self.effective, EffectiveInterval):
            raise InvalidAccountStatusCandidate("Business date interval required")
        if (
            not isinstance(self.source_ref, str)
            or not self.source_ref.strip()
            or self.source_ref != self.source_ref.strip()
        ):
            raise InvalidAccountStatusCandidate("Canonical nonblank status source required")


@dataclass(frozen=True, slots=True)
class AccountBookabilityCandidatePreview:
    """Only a favorable local shape check, NEVER GetAccountEligibility."""

    account_id: CompanyAccountId
    chart_id: CompanyChartId
    code: AccountCode
    as_of: date
    candidate_status_id: AccountStatusCandidateId


def _covers(outer: EffectiveInterval, inner: EffectiveInterval) -> bool:
    return outer.start <= inner.start and (
        outer.end is None or (inner.end is not None and inner.end <= outer.end)
    )


def preview_account_bookability_candidate(
    *,
    chart: CompanyChartDraft,
    accounts: tuple[CompanyAccountDraft, ...],
    edges: tuple[AccountHierarchyEdgeCandidate, ...],
    statuses: tuple[AccountStatusCandidate, ...],
    account_id: CompanyAccountId,
    as_of: date,
) -> AccountBookabilityCandidatePreview:
    """Fail closed for leaf, positive shape flag, explicit candidate status.

    A parent in ANY active proposed hierarchy view is denied unless a later
    independently approved policy explicitly authorizes posting to summaries.
    No default status, chart, mapping, or normative reference is substituted.
    """
    if not isinstance(account_id, CompanyAccountId) or type(as_of) is not date:
        raise InvalidAccountStatusCandidate("Typed account ID and business date required")
    if not isinstance(statuses, tuple):
        raise InvalidAccountStatusCandidate("Immutable status catalog required")
    validate_candidate_account_hierarchy(chart=chart, accounts=accounts, edges=edges)
    if not chart.effective.contains(as_of):
        raise AccountBookabilityCandidateDenied("Chart not effective at business date")
    by_id = {account.id: account for account in accounts}
    account = by_id.get(account_id)
    if account is None:
        raise AccountBookabilityCandidateDenied("Account is missing from scoped chart")
    require_account_belongs_to_chart(account=account, chart=chart)
    if not account.postable or not account.effective.contains(as_of):
        raise AccountBookabilityCandidateDenied("Account draft is not a postable candidate")
    if any(
        edge.parent_id == account_id and edge.effective.contains(as_of)
        for edge in edges
    ):
        raise AccountBookabilityCandidateDenied(
            "Account is an active parent/grouping node in a hierarchy view"
        )

    seen: set[AccountStatusCandidateId] = set()
    selected: AccountStatusCandidate | None = None
    for item in statuses:
        if not isinstance(item, AccountStatusCandidate):
            raise InvalidAccountStatusCandidate("Catalog contains non-status candidate")
        if item.id in seen:
            raise AccountStatusCandidateAmbiguous("Duplicate account status identity")
        seen.add(item.id)
        linked = by_id.get(item.account_id)
        if (
            linked is None
            or item.chart_id != chart.id
            or item.scope != chart.scope
            or not _covers(linked.effective, item.effective)
        ):
            raise InvalidAccountStatusCandidate(
                "Foreign/orphan status candidate or invalid effective interval"
            )
        if item.account_id == account_id and item.effective.contains(as_of):
            if selected is not None:
                raise AccountStatusCandidateAmbiguous(
                    "Multiple active statuses for account at business date"
                )
            selected = item

    if selected is None:
        raise AccountStatusCandidateMissing("No explicit account status at business date")
    if selected.status is not AccountStatusProposal.PROPOSED_ENABLED:
        raise AccountBookabilityCandidateDenied(
            "Account status proposal is not enabled for this date"
        )
    return AccountBookabilityCandidatePreview(
        account_id=account.id,
        chart_id=chart.id,
        code=account.code,
        as_of=as_of,
        candidate_status_id=selected.id,
    )
