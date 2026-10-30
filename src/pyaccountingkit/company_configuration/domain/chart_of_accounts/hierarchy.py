"""L05-02 — pure temporal account hierarchy candidates, not published graphs.

ADR-COA-04 (single tree versus multiple views) is OPEN. A provisional view code
makes multiple tree-shaped projections possible without asserting an approved
reporting, statutory, or posting hierarchy.
"""

import re
from dataclasses import dataclass
from datetime import date

from ..shared.accounting_scope import ConfigurationScope
from ..shared.effective_interval import EffectiveInterval
from ..shared.errors import DomainError
from ..shared.identifiers import (
    AccountHierarchyEdgeId,
    CompanyAccountId,
    CompanyChartId,
)
from .model import (
    CompanyAccountDraft,
    CompanyChartDraft,
    InvalidCompanyAccount,
    require_account_belongs_to_chart,
    require_unique_account_code,
)


class InvalidAccountHierarchy(DomainError):
    code = "INVALID_ACCOUNT_HIERARCHY"


class HierarchyCycle(DomainError):
    """COA-INV-06 candidate refusal, NOT proof of published graph validity."""

    code = "HIERARCHY_CYCLE"


class MultipleActiveAccountParents(DomainError):
    """COA-INV-07 candidate refusal in a single view/date."""

    code = "HIERARCHY_MULTIPLE_PARENTS"


class DuplicateHierarchyEdge(DomainError):
    code = "HIERARCHY_DUPLICATE_EDGE"


@dataclass(frozen=True, slots=True)
class HierarchyViewCode:
    """Provisional named tree view; does not ratify ADR-COA-04."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or re.fullmatch(
            r"[A-Z][A-Z0-9_-]{0,31}", self.value
        ) is None:
            raise InvalidAccountHierarchy("Canonical uppercase hierarchy view required")


@dataclass(frozen=True, slots=True)
class AccountHierarchyEdgeCandidate:
    """One typed, dated directed child → parent proposal in a named view."""

    id: AccountHierarchyEdgeId
    scope: ConfigurationScope
    chart_id: CompanyChartId
    view: HierarchyViewCode
    child_id: CompanyAccountId
    parent_id: CompanyAccountId
    effective: EffectiveInterval
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, AccountHierarchyEdgeId):
            raise InvalidAccountHierarchy("Typed hierarchy edge ID required")
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is not None:
            raise InvalidAccountHierarchy("Entity-level hierarchy scope required")
        if not isinstance(self.chart_id, CompanyChartId):
            raise InvalidAccountHierarchy("Typed chart ID required")
        if not isinstance(self.view, HierarchyViewCode):
            raise InvalidAccountHierarchy("Typed hierarchy view required")
        if (
            not isinstance(self.child_id, CompanyAccountId)
            or not isinstance(self.parent_id, CompanyAccountId)
        ):
            raise InvalidAccountHierarchy("Typed parent and child IDs required")
        if not isinstance(self.effective, EffectiveInterval):
            raise InvalidAccountHierarchy("Business-date interval required")
        if (
            not isinstance(self.source_ref, str)
            or not self.source_ref.strip()
            or self.source_ref != self.source_ref.strip()
        ):
            raise InvalidAccountHierarchy("Canonical nonempty source reference required")
        if self.child_id == self.parent_id:
            raise HierarchyCycle("An account cannot be its own direct parent")


@dataclass(frozen=True, slots=True)
class AccountHierarchyCandidatePreview:
    """At-date proposed graph, neither a published chart nor a C10 answer."""

    chart_id: CompanyChartId
    scope: ConfigurationScope
    view: HierarchyViewCode
    as_of: date
    relations: tuple[tuple[CompanyAccountId, CompanyAccountId], ...]


def _covers(outer: EffectiveInterval, inner: EffectiveInterval) -> bool:
    return outer.start <= inner.start and (
        outer.end is None or (inner.end is not None and inner.end <= outer.end)
    )


def _check_point(
    *, edges: tuple[AccountHierarchyEdgeCandidate, ...], point: date
) -> None:
    """At each change point, each view must be an acyclic forest."""
    for view in {edge.view for edge in edges}:
        relevant = (
            edge for edge in edges
            if edge.view == view and edge.effective.contains(point)
        )
        parents: dict[CompanyAccountId, CompanyAccountId] = {}
        for edge in relevant:
            previous = parents.get(edge.child_id)
            if previous is not None:
                if previous == edge.parent_id:
                    raise DuplicateHierarchyEdge(
                        "Overlapping identical child/parent relation in one view"
                    )
                raise MultipleActiveAccountParents(
                    "An account has two active parents in the same view/date"
                )
            parents[edge.child_id] = edge.parent_id

        # A parent chain forms a cycle iff a node is re-encountered on that chain.
        # Iterative traversal also handles deeply nested graphs without recursion.
        finished: set[CompanyAccountId] = set()
        for child in parents:
            if child in finished:
                continue
            chain: set[CompanyAccountId] = set()
            cursor = child
            while cursor in parents and cursor not in finished:
                if cursor in chain:
                    raise HierarchyCycle("Cyclic account ancestry in view/date")
                chain.add(cursor)
                cursor = parents[cursor]
            finished.update(chain)


def validate_candidate_account_hierarchy(
    *,
    chart: CompanyChartDraft,
    accounts: tuple[CompanyAccountDraft, ...],
    edges: tuple[AccountHierarchyEdgeCandidate, ...],
) -> None:
    """Validate *all* represented business time slices, not only today.

    Scope, edge endpoints, validity, code uniqueness, duplicate identities,
    one-parent-per-view and cycles are checked before returning any preview.
    No SQL foreign-key, IAM, publication or normative integrity is implied.
    """
    if not isinstance(chart, CompanyChartDraft):
        raise InvalidAccountHierarchy("Typed chart required")
    if not isinstance(accounts, tuple) or not isinstance(edges, tuple):
        raise InvalidAccountHierarchy("Immutable account and edge catalogs required")

    by_id: dict[CompanyAccountId, CompanyAccountDraft] = {}
    seen_accounts: list[CompanyAccountDraft] = []
    for account in accounts:
        if not isinstance(account, CompanyAccountDraft):
            raise InvalidAccountHierarchy("Account catalog contains non-account")
        require_account_belongs_to_chart(account=account, chart=chart)
        if account.id in by_id:
            raise InvalidAccountHierarchy("Duplicate account identity in graph catalog")
        try:
            require_unique_account_code(candidate=account, existing=tuple(seen_accounts))
        except InvalidCompanyAccount as exc:
            raise InvalidAccountHierarchy("Malformed account catalog") from exc
        by_id[account.id] = account
        seen_accounts.append(account)

    seen_edges: set[AccountHierarchyEdgeId] = set()
    points: set[date] = set()
    for edge in edges:
        if not isinstance(edge, AccountHierarchyEdgeCandidate):
            raise InvalidAccountHierarchy("Edge catalog contains non-edge")
        if edge.id in seen_edges:
            raise DuplicateHierarchyEdge("Duplicate hierarchy edge identity")
        seen_edges.add(edge.id)
        if edge.chart_id != chart.id or edge.scope != chart.scope:
            raise InvalidAccountHierarchy("Cross-chart/tenant/entity hierarchy relation")
        child = by_id.get(edge.child_id)
        parent = by_id.get(edge.parent_id)
        if child is None or parent is None:
            raise InvalidAccountHierarchy("Orphan hierarchy edge endpoint")
        for period in (chart.effective, child.effective, parent.effective):
            if not _covers(period, edge.effective):
                raise InvalidAccountHierarchy(
                    "Hierarchy edge extends beyond chart/account validity"
                )
        points.add(edge.effective.start)
        if edge.effective.end is not None:
            points.add(edge.effective.end)

    # In a half-open finite set of intervals, graph membership only changes
    # at one of these start/end boundaries. Checking each such point exhausts
    # ALL active graphs, including future and retroactive proposed cycles.
    for point in sorted(points):
        _check_point(edges=edges, point=point)


def preview_account_hierarchy(
    *,
    chart: CompanyChartDraft,
    accounts: tuple[CompanyAccountDraft, ...],
    edges: tuple[AccountHierarchyEdgeCandidate, ...],
    view: HierarchyViewCode,
    as_of: date,
) -> AccountHierarchyCandidatePreview:
    """Read a deterministic, validated, view-specific candidate edge set."""
    if not isinstance(view, HierarchyViewCode) or type(as_of) is not date:
        raise InvalidAccountHierarchy("Typed view and business date required")
    validate_candidate_account_hierarchy(chart=chart, accounts=accounts, edges=edges)
    if not chart.effective.contains(as_of):
        raise InvalidAccountHierarchy("Chart is not effective at query date")
    active = [
        (edge.child_id, edge.parent_id)
        for edge in edges if edge.view == view and edge.effective.contains(as_of)
    ]
    return AccountHierarchyCandidatePreview(
        chart_id=chart.id,
        scope=chart.scope,
        view=view,
        as_of=as_of,
        relations=tuple(sorted(active, key=lambda pair: (str(pair[0]), str(pair[1])))),
    )
