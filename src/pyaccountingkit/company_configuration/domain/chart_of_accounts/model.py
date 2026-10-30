"""L05-01: pure chart/account *draft* identities and local business rules.

This domain is not a Normative Layer, a published chart, C10 account eligibility,
IAM proof, posting authorization, mapping engine or SQL writer. Chart ownership
and aggregate granularity remain open ADR-COA-01/02.
"""

import re
from dataclasses import dataclass, replace
from datetime import date

from ..shared.accounting_scope import ConfigurationScope
from ..shared.effective_interval import EffectiveInterval
from ..shared.errors import DomainError, VersionConflict
from ..shared.identifiers import CompanyAccountId, CompanyChartId


class InvalidCompanyChart(DomainError):
    code = "INVALID_COMPANY_CHART"


class InvalidCompanyAccount(DomainError):
    code = "INVALID_COMPANY_ACCOUNT"


class DuplicateChartCode(DomainError):
    code = "DUPLICATE_CHART_CODE"


class DuplicateAccountCode(DomainError):
    code = "DUPLICATE_ACCOUNT_CODE"


class ChartAccountScopeConflict(DomainError):
    code = "CHART_ACCOUNT_SCOPE_CONFLICT"


class AccountNotPostable(DomainError):
    code = "ACCOUNT_NOT_POSTABLE"


def _nonblank(value: str, *, kind: str, error: type[DomainError]) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise error(f"{kind} must be nonblank and trimmed")


def _check_revision(
    current: int, *, expected_revision: int, reason: str
) -> None:
    if type(expected_revision) is not int or expected_revision != current:
        raise VersionConflict("Draft chart/account revision mismatch")
    _nonblank(reason, kind="reason", error=InvalidCompanyAccount)


def _covers(outer: EffectiveInterval, inner: EffectiveInterval) -> bool:
    return outer.start <= inner.start and (
        outer.end is None or (inner.end is not None and inner.end <= outer.end)
    )


@dataclass(frozen=True, slots=True)
class ChartCode:
    """Provisional chart namespace shape, not a jurisdictional convention."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not re.fullmatch(
            r"[A-Z][A-Z0-9_-]{0,31}", self.value
        ):
            raise InvalidCompanyChart("ChartCode requires uppercase ASCII code")


@dataclass(frozen=True, slots=True)
class AccountCode:
    """Never coerce to integer: the literal code preserves leading zeroes.

    Syntax is deliberately provisional; official framework conventions require
    approved, external configurable rules, not a hardcoded IFRS/PCG number range.
    """

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._/-]{0,63}", self.value
        ):
            raise InvalidCompanyAccount("AccountCode requires a nonblank canonical string")


@dataclass(frozen=True, slots=True)
class AccountClassificationCode:
    """Opaque internal classification, NOT verified normative account nature."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not re.fullmatch(
            r"[A-Z][A-Z0-9_-]{0,47}", self.value
        ):
            raise InvalidCompanyAccount("Explicit canonical account classification required")


@dataclass(frozen=True, slots=True, eq=False)
class CompanyChartDraft:
    """Entity-scoped chart *intent*, not a final ownership/publishing decision."""

    id: CompanyChartId
    scope: ConfigurationScope
    code: ChartCode
    label: str
    effective: EffectiveInterval
    source_ref: str
    revision: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, CompanyChartId):
            raise InvalidCompanyChart("Typed CompanyChartId required")
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is not None:
            raise InvalidCompanyChart("Explicit entity-level scope required")
        if not isinstance(self.code, ChartCode):
            raise InvalidCompanyChart("Typed ChartCode required")
        _nonblank(self.label, kind="chart label", error=InvalidCompanyChart)
        if not isinstance(self.effective, EffectiveInterval):
            raise InvalidCompanyChart("Typed chart EffectiveInterval required")
        _nonblank(self.source_ref, kind="source_ref", error=InvalidCompanyChart)
        if type(self.revision) is not int or self.revision < 1:
            raise InvalidCompanyChart("Positive chart revision required")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CompanyChartDraft):
            return NotImplemented
        return (self.scope.tenant_id, self.id) == (other.scope.tenant_id, other.id)

    def __hash__(self) -> int:
        return hash((self.scope.tenant_id, self.id))

    def rename(
        self, label: str, *, expected_revision: int, reason: str
    ) -> "CompanyChartDraft":
        _check_revision(self.revision, expected_revision=expected_revision, reason=reason)
        _nonblank(label, kind="chart label", error=InvalidCompanyChart)
        if label == self.label:
            raise InvalidCompanyChart("Rename requires a changed label")
        return replace(self, label=label, revision=self.revision + 1)


@dataclass(frozen=True, slots=True, eq=False)
class CompanyAccountDraft:
    """Account candidate; 'postable' is an unverified local shape flag only."""

    id: CompanyAccountId
    chart_id: CompanyChartId
    scope: ConfigurationScope
    code: AccountCode
    label: str
    classification: AccountClassificationCode
    postable: bool
    effective: EffectiveInterval
    source_ref: str
    revision: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, CompanyAccountId):
            raise InvalidCompanyAccount("Typed CompanyAccountId required")
        if not isinstance(self.chart_id, CompanyChartId):
            raise InvalidCompanyAccount("Typed chart ID required")
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is not None:
            raise InvalidCompanyAccount("Explicit entity-level scope required")
        if not isinstance(self.code, AccountCode):
            raise InvalidCompanyAccount("Typed AccountCode required")
        _nonblank(self.label, kind="account label", error=InvalidCompanyAccount)
        if not isinstance(self.classification, AccountClassificationCode):
            raise InvalidCompanyAccount("Typed classification required")
        if type(self.postable) is not bool:
            raise InvalidCompanyAccount("Explicit bool postable shape flag required")
        if not isinstance(self.effective, EffectiveInterval):
            raise InvalidCompanyAccount("Typed account EffectiveInterval required")
        _nonblank(self.source_ref, kind="source_ref", error=InvalidCompanyAccount)
        if type(self.revision) is not int or self.revision < 1:
            raise InvalidCompanyAccount("Positive account revision required")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CompanyAccountDraft):
            return NotImplemented
        return (self.scope.tenant_id, self.id) == (other.scope.tenant_id, other.id)

    def __hash__(self) -> int:
        return hash((self.scope.tenant_id, self.id))

    def rename(
        self, label: str, *, expected_revision: int, reason: str
    ) -> "CompanyAccountDraft":
        _check_revision(self.revision, expected_revision=expected_revision, reason=reason)
        _nonblank(label, kind="account label", error=InvalidCompanyAccount)
        if label == self.label:
            raise InvalidCompanyAccount("Rename requires a changed label")
        return replace(self, label=label, revision=self.revision + 1)

    def propose_postability(
        self, postable: bool, *, expected_revision: int, reason: str
    ) -> "CompanyAccountDraft":
        """Change a DRAFT shape flag, not accounting posting eligibility."""
        _check_revision(self.revision, expected_revision=expected_revision, reason=reason)
        if type(postable) is not bool or postable == self.postable:
            raise InvalidCompanyAccount("Postability proposal must change a bool value")
        return replace(self, postable=postable, revision=self.revision + 1)

    def require_postable_candidate(self, *, as_of: date) -> None:
        """One *necessary*, never sufficient, prerequisite for actual posting."""
        if type(as_of) is not date:
            raise InvalidCompanyAccount("Business date required")
        if not self.postable or not self.effective.contains(as_of):
            raise AccountNotPostable("Draft account not marked postable for this date")


def require_account_belongs_to_chart(
    *, account: CompanyAccountDraft, chart: CompanyChartDraft
) -> None:
    """Check claimed ownership and full validity containment; NOT organization proof."""
    if not isinstance(account, CompanyAccountDraft) or not isinstance(
        chart, CompanyChartDraft
    ):
        raise ChartAccountScopeConflict("Typed chart and account candidates required")
    if (
        account.chart_id != chart.id
        or account.scope != chart.scope
        or not _covers(chart.effective, account.effective)
    ):
        raise ChartAccountScopeConflict("Account/chart scope or validity mismatch")


def require_unique_chart_code(
    *, candidate: CompanyChartDraft, existing: tuple[CompanyChartDraft, ...]
) -> None:
    """Check code collisions within one claimed company/entity and overlapping date."""
    if not isinstance(candidate, CompanyChartDraft) or not isinstance(existing, tuple):
        raise InvalidCompanyChart("Typed chart and immutable catalog required")
    for chart in existing:
        if not isinstance(chart, CompanyChartDraft):
            raise InvalidCompanyChart("Non-chart in catalog")
        if chart.id == candidate.id and chart.scope != candidate.scope:
            raise ChartAccountScopeConflict("Chart ID reused across accounting scopes")
        if chart.id == candidate.id:
            continue
        if (
            chart.scope == candidate.scope
            and chart.code == candidate.code
            and chart.effective.overlaps(candidate.effective)
        ):
            raise DuplicateChartCode("Overlapping chart codes in claimed scope")


def require_unique_account_code(
    *, candidate: CompanyAccountDraft, existing: tuple[CompanyAccountDraft, ...]
) -> None:
    """Local temporal uniqueness by chart and scope, not a durable DB constraint."""
    if not isinstance(candidate, CompanyAccountDraft) or not isinstance(existing, tuple):
        raise InvalidCompanyAccount("Typed account and immutable catalog required")
    for account in existing:
        if not isinstance(account, CompanyAccountDraft):
            raise InvalidCompanyAccount("Non-account in catalog")
        if account.id == candidate.id and (
            account.scope != candidate.scope or account.chart_id != candidate.chart_id
        ):
            raise ChartAccountScopeConflict("Stable account ID reused across chart/scope")
        if account.id == candidate.id:
            continue
        if (
            account.scope == candidate.scope
            and account.chart_id == candidate.chart_id
            and account.code == candidate.code
            and account.effective.overlaps(candidate.effective)
        ):
            raise DuplicateAccountCode("Overlapping account codes in one chart/scope")
