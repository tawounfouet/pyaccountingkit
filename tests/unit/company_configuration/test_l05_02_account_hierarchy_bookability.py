"""L05-02 hierarchy graph and bookability prereq R&D, without C10/posting."""

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime

import pytest

from pyaccountingkit.company_configuration.domain.chart_of_accounts import (
    AccountBookabilityCandidateDenied,
    AccountClassificationCode,
    AccountCode,
    AccountHierarchyEdgeCandidate,
    AccountStatusCandidate,
    AccountStatusCandidateAmbiguous,
    AccountStatusCandidateMissing,
    AccountStatusProposal,
    ChartCode,
    CompanyAccountDraft,
    CompanyChartDraft,
    DuplicateAccountCode,
    DuplicateHierarchyEdge,
    HierarchyCycle,
    HierarchyViewCode,
    InvalidAccountHierarchy,
    InvalidAccountStatusCandidate,
    MultipleActiveAccountParents,
    preview_account_bookability_candidate,
    preview_account_hierarchy,
    validate_candidate_account_hierarchy,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountHierarchyEdgeId,
    AccountStatusCandidateId,
    AccountingBookId,
    CompanyAccountId,
    CompanyChartId,
    CompanyId,
    LegalEntityId,
)

FROM = date(2026, 1, 1)
JUL = date(2026, 7, 1)
DEC = date(2026, 12, 1)
TREE = HierarchyViewCode("TREE")
GROUP = HierarchyViewCode("GROUP")


def chart(*, end=None):
    return CompanyChartDraft(
        id=CompanyChartId.new(),
        scope=ConfigurationScope(
            tenant_id="tenant-a",
            company_id=CompanyId.new(),
            legal_entity_id=LegalEntityId.new(),
        ),
        code=ChartCode("MAIN"),
        label="Draft chart",
        effective=EffectiveInterval(FROM, end),
        source_ref="rnd:chart",
    )


def account(ch, code, *, start=FROM, end=None, postable=True):
    return CompanyAccountDraft(
        id=CompanyAccountId.new(),
        chart_id=ch.id,
        scope=ch.scope,
        code=AccountCode(code),
        label="Candidate " + code,
        classification=AccountClassificationCode("LOCAL"),
        postable=postable,
        effective=EffectiveInterval(start, end),
        source_ref="rnd:account",
    )


def edge(
    ch, child, parent, *, view=TREE, start=FROM, end=None,
    identity=None, scope=None,
):
    return AccountHierarchyEdgeCandidate(
        id=identity or AccountHierarchyEdgeId.new(),
        scope=scope or ch.scope,
        chart_id=ch.id,
        view=view,
        child_id=child.id,
        parent_id=parent.id,
        effective=EffectiveInterval(start, end),
        source_ref="rnd:edge",
    )


def status(
    ch, acc, *, state=AccountStatusProposal.PROPOSED_ENABLED,
    start=FROM, end=None, identity=None, scope=None,
):
    return AccountStatusCandidate(
        id=identity or AccountStatusCandidateId.new(),
        scope=scope or ch.scope,
        chart_id=ch.id,
        account_id=acc.id,
        status=state,
        effective=EffectiveInterval(start, end),
        source_ref="rnd:status",
    )


def preview(ch, accounts, edges, statuses, acc, as_of=FROM):
    return preview_account_bookability_candidate(
        chart=ch,
        accounts=accounts,
        edges=edges,
        statuses=statuses,
        account_id=acc.id,
        as_of=as_of,
    )


def test_valid_three_level_hierarchy_and_deterministic_preview():
    ch = chart()
    root = account(ch, "60")
    mid = account(ch, "606")
    leaf = account(ch, "00606100")
    links = (edge(ch, leaf, mid), edge(ch, mid, root))
    validate_candidate_account_hierarchy(
        chart=ch, accounts=(root, mid, leaf), edges=links
    )
    first = preview_account_hierarchy(
        chart=ch, accounts=(root, mid, leaf), edges=links,
        view=TREE, as_of=FROM,
    )
    second = preview_account_hierarchy(
        chart=ch, accounts=(leaf, root, mid), edges=tuple(reversed(links)),
        view=TREE, as_of=FROM,
    )
    assert first.relations == second.relations
    assert set(first.relations) == {(leaf.id, mid.id), (mid.id, root.id)}
    assert first.view == TREE and first.as_of == FROM
    assert "00606100" == leaf.code.value
    assert not hasattr(first, "publish")


def test_self_edge_immediately_denied():
    ch = chart()
    a = account(ch, "1")
    with pytest.raises(HierarchyCycle):
        edge(ch, a, a)


@pytest.mark.parametrize("length", [2, 3, 8])
def test_cycles_of_multiple_lengths_denied(length):
    ch = chart()
    nodes = tuple(account(ch, str(i + 1)) for i in range(length))
    links = tuple(edge(ch, nodes[i], nodes[(i + 1) % length])
                  for i in range(length))
    with pytest.raises(HierarchyCycle):
        validate_candidate_account_hierarchy(chart=ch, accounts=nodes, edges=links)


def test_future_cycle_is_rejected_even_if_current_query_would_be_acyclic():
    ch = chart()
    a, b = account(ch, "1"), account(ch, "2")
    links = (edge(ch, a, b), edge(ch, b, a, start=JUL))
    with pytest.raises(HierarchyCycle):
        preview_account_hierarchy(
            chart=ch, accounts=(a, b), edges=links, view=TREE, as_of=FROM
        )


def test_nonoverlapping_reverse_edges_are_valid_across_half_open_boundary():
    ch = chart()
    a, b = account(ch, "1"), account(ch, "2")
    links = (
        edge(ch, a, b, end=JUL),
        edge(ch, b, a, start=JUL),
    )
    before = preview_account_hierarchy(
        chart=ch, accounts=(a, b), edges=links,
        view=TREE, as_of=date(2026, 6, 30),
    )
    after = preview_account_hierarchy(
        chart=ch, accounts=(a, b), edges=links, view=TREE, as_of=JUL
    )
    assert before.relations == ((a.id, b.id),)
    assert after.relations == ((b.id, a.id),)


def test_two_active_parents_in_same_view_fail():
    ch = chart()
    child, p1, p2 = (account(ch, x) for x in ("1", "2", "3"))
    with pytest.raises(MultipleActiveAccountParents):
        validate_candidate_account_hierarchy(
            chart=ch, accounts=(child, p1, p2),
            edges=(edge(ch, child, p1), edge(ch, child, p2, start=JUL)),
        )


def test_adjacent_parent_switch_same_view_is_allowed():
    ch = chart()
    child, p1, p2 = (account(ch, x) for x in ("1", "2", "3"))
    links = (
        edge(ch, child, p1, end=JUL),
        edge(ch, child, p2, start=JUL),
    )
    result = preview_account_hierarchy(
        chart=ch, accounts=(child, p1, p2), edges=links,
        view=TREE, as_of=JUL,
    )
    assert result.relations == ((child.id, p2.id),)


def test_multiple_hierarchy_views_allow_distinct_parents():
    ch = chart()
    child, statutory, group = (account(ch, x) for x in ("1", "2", "3"))
    links = (edge(ch, child, statutory), edge(ch, child, group, view=GROUP))
    validate_candidate_account_hierarchy(
        chart=ch, accounts=(child, statutory, group), edges=links
    )
    assert preview_account_hierarchy(
        chart=ch, accounts=(child, statutory, group), edges=links,
        view=GROUP, as_of=FROM,
    ).relations == ((child.id, group.id),)


def test_duplicate_child_parent_active_in_same_view_is_rejected():
    ch = chart()
    child, parent = account(ch, "1"), account(ch, "2")
    with pytest.raises(DuplicateHierarchyEdge):
        validate_candidate_account_hierarchy(
            chart=ch, accounts=(child, parent),
            edges=(edge(ch, child, parent), edge(ch, child, parent)),
        )


def test_duplicate_edge_identity_is_rejected_even_for_adjacent_intervals():
    ch = chart()
    child, parent = account(ch, "1"), account(ch, "2")
    first = edge(ch, child, parent, end=JUL)
    second = edge(ch, child, parent, identity=first.id, start=JUL)
    with pytest.raises(DuplicateHierarchyEdge, match="identity"):
        validate_candidate_account_hierarchy(
            chart=ch, accounts=(child, parent), edges=(first, second)
        )


def test_orphan_endpoint_rejected_not_silently_filtered():
    ch = chart()
    child, parent = account(ch, "1"), account(ch, "2")
    with pytest.raises(InvalidAccountHierarchy, match="Orphan"):
        validate_candidate_account_hierarchy(
            chart=ch, accounts=(child,), edges=(edge(ch, child, parent),)
        )


def test_cross_tenant_entity_chart_edges_fail_closed():
    ch = chart()
    child, parent = account(ch, "1"), account(ch, "2")
    for mutated in (
        replace(edge(ch, child, parent), chart_id=CompanyChartId.new()),
        replace(edge(ch, child, parent),
                scope=replace(ch.scope, tenant_id="tenant-b")),
        replace(edge(ch, child, parent),
                scope=replace(ch.scope, legal_entity_id=LegalEntityId.new())),
    ):
        with pytest.raises(InvalidAccountHierarchy, match="Cross-chart"):
            validate_candidate_account_hierarchy(
                chart=ch, accounts=(child, parent), edges=(mutated,)
            )


def test_edge_interval_must_fit_both_account_validities_and_chart():
    ch = chart(end=DEC)
    child = account(ch, "1", start=JUL, end=DEC)
    parent = account(ch, "2", end=DEC)
    invalid = edge(ch, child, parent, start=FROM, end=DEC)
    with pytest.raises(InvalidAccountHierarchy, match="beyond"):
        validate_candidate_account_hierarchy(
            chart=ch, accounts=(child, parent), edges=(invalid,)
        )
    invalid_end = edge(ch, child, parent, start=JUL)
    with pytest.raises(InvalidAccountHierarchy, match="beyond"):
        validate_candidate_account_hierarchy(
            chart=ch, accounts=(child, parent), edges=(invalid_end,)
        )


def test_catalog_duplicate_account_ids_and_codes_are_rejected():
    ch = chart()
    a = account(ch, "1")
    with pytest.raises(InvalidAccountHierarchy, match="Duplicate account identity"):
        validate_candidate_account_hierarchy(chart=ch, accounts=(a, a), edges=())
    with pytest.raises(DuplicateAccountCode):
        validate_candidate_account_hierarchy(
            chart=ch, accounts=(a, account(ch, "1")), edges=()
        )


@pytest.mark.parametrize("bad", ["", "tree", " TREE", "1TREE", "TREE/1", "X" * 33])
def test_hierarchy_view_requires_conservative_canonical_code(bad):
    with pytest.raises(InvalidAccountHierarchy):
        HierarchyViewCode(bad)


def test_edge_fields_are_strictly_typed():
    ch = chart()
    child, parent = account(ch, "1"), account(ch, "2")
    one = edge(ch, child, parent)
    for changes in (
        {"id": child.id},
        {"child_id": parent.chart_id},
        {"view": "TREE"},
        {"effective": "2026-01-01"},
        {"source_ref": " invalid "},
        {"scope": replace(ch.scope, book_id=AccountingBookId.new())},
    ):
        with pytest.raises(InvalidAccountHierarchy):
            replace(one, **changes)


def test_query_date_and_catalog_types_strictly_checked():
    ch = chart()
    a = account(ch, "1")
    for aa, ee in (([a], ()), ((a,), []), ((a,), ("edge",))):
        with pytest.raises(InvalidAccountHierarchy):
            validate_candidate_account_hierarchy(chart=ch, accounts=aa, edges=ee)
    with pytest.raises(InvalidAccountHierarchy):
        preview_account_hierarchy(
            chart=ch, accounts=(a,), edges=(), view="TREE", as_of=FROM
        )
    with pytest.raises(InvalidAccountHierarchy):
        preview_account_hierarchy(
            chart=ch, accounts=(a,), edges=(),
            view=TREE, as_of=datetime(2026, 1, 1),
        )


def test_empty_named_view_does_not_fallback_to_other_view():
    ch = chart()
    a, b = account(ch, "1"), account(ch, "2")
    result = preview_account_hierarchy(
        chart=ch, accounts=(a, b), edges=(edge(ch, a, b, view=GROUP),),
        view=TREE, as_of=FROM,
    )
    assert result.relations == ()


def test_valid_leaf_with_explicit_enabled_proposal_yields_only_local_preview():
    ch = chart()
    root, leaf = account(ch, "60"), account(ch, "0606100")
    proposal = status(ch, leaf)
    result = preview(
        ch, (root, leaf), (edge(ch, leaf, root),), (proposal,), leaf
    )
    assert result.account_id == leaf.id
    assert result.code.value == "0606100"
    assert result.candidate_status_id == proposal.id
    assert not hasattr(result, "post")
    assert not hasattr(result, "eligible")
    assert not hasattr(result, "publish")


def test_active_parent_rejected_even_when_flag_and_status_are_positive():
    ch = chart()
    parent, child = account(ch, "60"), account(ch, "606")
    with pytest.raises(AccountBookabilityCandidateDenied, match="parent/grouping"):
        preview(
            ch, (parent, child), (edge(ch, child, parent),),
            (status(ch, parent),), parent
        )


def test_parent_in_different_view_also_denied_no_default_view_override():
    ch = chart()
    parent, child = account(ch, "60"), account(ch, "606")
    with pytest.raises(AccountBookabilityCandidateDenied, match="parent/grouping"):
        preview(
            ch, (parent, child), (edge(ch, child, parent, view=GROUP),),
            (status(ch, parent),), parent
        )


def test_parent_allowed_as_local_leaf_only_after_edge_interval_expires():
    ch = chart()
    parent, child = account(ch, "60"), account(ch, "606")
    result = preview(
        ch, (parent, child),
        (edge(ch, child, parent, end=JUL),),
        (status(ch, parent),), parent, as_of=JUL,
    )
    assert result.account_id == parent.id


def test_non_postable_leaf_denied_even_with_enabled_candidate_status():
    ch = chart()
    summary = account(ch, "60", postable=False)
    with pytest.raises(AccountBookabilityCandidateDenied, match="not a postable"):
        preview(ch, (summary,), (), (status(ch, summary),), summary)


@pytest.mark.parametrize(
    "proposal",
    [
        AccountStatusProposal.DRAFT,
        AccountStatusProposal.PROPOSED_SUSPENDED,
        AccountStatusProposal.PROPOSED_RETIRED,
    ],
)
def test_draft_suspended_or_retired_candidates_never_look_bookable(proposal):
    ch = chart()
    a = account(ch, "1")
    with pytest.raises(AccountBookabilityCandidateDenied, match="not enabled"):
        preview(ch, (a,), (), (status(ch, a, state=proposal),), a)


def test_absent_status_is_not_defaulted_to_enabled():
    ch = chart()
    a = account(ch, "1")
    with pytest.raises(AccountStatusCandidateMissing):
        preview(ch, (a,), (), (), a)


def test_two_active_status_proposals_are_ambiguous_even_when_same_state():
    ch = chart()
    a = account(ch, "1")
    with pytest.raises(AccountStatusCandidateAmbiguous):
        preview(ch, (a,), (), (status(ch, a), status(ch, a, start=JUL)), a,
                as_of=JUL)


def test_adjacent_half_open_status_windows_select_exact_boundary():
    ch = chart()
    a = account(ch, "1")
    old = status(ch, a, state=AccountStatusProposal.PROPOSED_SUSPENDED, end=JUL)
    current = status(ch, a, start=JUL)
    with pytest.raises(AccountBookabilityCandidateDenied):
        preview(ch, (a,), (), (old, current), a, as_of=date(2026, 6, 30))
    assert preview(ch, (a,), (), (old, current), a, as_of=JUL
                   ).candidate_status_id == current.id


def test_future_status_not_available_at_previous_business_date():
    ch = chart()
    a = account(ch, "1")
    with pytest.raises(AccountStatusCandidateMissing):
        preview(ch, (a,), (), (status(ch, a, start=JUL),), a)


def test_status_duplicate_id_rejected_even_in_disjoint_windows():
    ch = chart()
    a = account(ch, "1")
    first = status(ch, a, end=JUL)
    second = status(ch, a, identity=first.id, start=JUL)
    with pytest.raises(AccountStatusCandidateAmbiguous, match="identity"):
        preview(ch, (a,), (), (first, second), a)


def test_foreign_tenant_and_orphan_status_not_silently_filtered():
    ch = chart()
    a = account(ch, "1")
    for candidate in (
        status(ch, a, scope=replace(ch.scope, tenant_id="tenant-b")),
        replace(status(ch, a), chart_id=CompanyChartId.new()),
        replace(status(ch, a), account_id=CompanyAccountId.new()),
    ):
        with pytest.raises(InvalidAccountStatusCandidate, match="Foreign/orphan"):
            preview(ch, (a,), (), (candidate,), a)


def test_status_effective_interval_must_fit_account_validity():
    ch = chart()
    a = account(ch, "1", start=JUL)
    candidate = status(ch, a, start=FROM)
    with pytest.raises(InvalidAccountStatusCandidate, match="interval"):
        preview(ch, (a,), (), (candidate,), a, as_of=JUL)


def test_status_candidate_fields_are_typed_and_frozen():
    ch = chart()
    a = account(ch, "1")
    candidate = status(ch, a)
    changes = (
        {"id": a.id},
        {"chart_id": a.id},
        {"account_id": ch.id},
        {"status": "PROPOSED_ENABLED"},
        {"effective": "2026"},
        {"source_ref": " bad "},
        {"scope": replace(ch.scope, book_id=AccountingBookId.new())},
    )
    for change in changes:
        with pytest.raises((InvalidAccountStatusCandidate, ValueError)):
            replace(candidate, **change)
    with pytest.raises(FrozenInstanceError):
        candidate.source_ref = "mutated"


def test_query_rejects_foreign_account_and_wrong_types():
    ch = chart()
    a = account(ch, "1")
    with pytest.raises(AccountBookabilityCandidateDenied, match="missing"):
        preview_account_bookability_candidate(
            chart=ch, accounts=(a,), edges=(), statuses=(status(ch, a),),
            account_id=CompanyAccountId.new(), as_of=FROM,
        )
    with pytest.raises(InvalidAccountStatusCandidate):
        preview_account_bookability_candidate(
            chart=ch, accounts=(a,), edges=(), statuses=(status(ch, a),),
            account_id=ch.id, as_of=FROM,
        )
    with pytest.raises(InvalidAccountStatusCandidate):
        preview_account_bookability_candidate(
            chart=ch, accounts=(a,), edges=(), statuses=[],
            account_id=a.id, as_of=FROM,
        )


def test_no_sql_live_iam_c10_posting_or_api_surface():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.domain.chart_of_accounts import (
        bookability,
        hierarchy,
    )

    for module in (bookability, hierarchy):
        content = Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(content)
        external = {
            alias.name.split(".")[0] for node in ast.walk(tree)
            if isinstance(node, ast.Import) for alias in node.names
        }
        assert not ({"psycopg", "sqlalchemy", "requests", "httpx"} & external)
        assert "organization_issuer_gateway" not in content
        assert not hasattr(module, "publish")
        assert not hasattr(module, "post")
        assert not hasattr(module, "get_account_eligibility")
