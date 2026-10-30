"""L05-01: isolated pure CompanyChart/CompanyAccount domain invariants.

Tests are proof of bounded in-memory R&D rules, not C10 account eligibility,
signed legal relationships, approved norms, posting or database concurrency.
"""

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime

import pytest

from pyaccountingkit.company_configuration.domain.chart_of_accounts import (
    AccountClassificationCode,
    AccountCode,
    AccountNotPostable,
    ChartAccountScopeConflict,
    ChartCode,
    CompanyAccountDraft,
    CompanyChartDraft,
    DuplicateAccountCode,
    DuplicateChartCode,
    InvalidCompanyAccount,
    InvalidCompanyChart,
    require_account_belongs_to_chart,
    require_unique_account_code,
    require_unique_chart_code,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
)
from pyaccountingkit.company_configuration.domain.shared.errors import VersionConflict
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountingBookId,
    CompanyAccountId,
    CompanyChartId,
    CompanyId,
    LegalEntityId,
)


def make_chart(
    *, chart_id=None, scope=None, code="LOCAL", start=date(2026, 1, 1),
    end=None, revision=1
):
    target = scope or ConfigurationScope(
        tenant_id="tenant-a",
        company_id=CompanyId.new(),
        legal_entity_id=LegalEntityId.new(),
    )
    return CompanyChartDraft(
        id=chart_id or CompanyChartId.new(),
        scope=target,
        code=ChartCode(code),
        label="Chart intent",
        effective=EffectiveInterval(start, end),
        source_ref="test:chart",
        revision=revision,
    )


def make_account(
    chart, *, account_id=None, code="00123", start=date(2026, 1, 1),
    end=None, postable=True, classification="LOCAL_CLASS"
):
    return CompanyAccountDraft(
        id=account_id or CompanyAccountId.new(),
        chart_id=chart.id,
        scope=chart.scope,
        code=AccountCode(code),
        label="Draft account",
        classification=AccountClassificationCode(classification),
        postable=postable,
        effective=EffectiveInterval(start, end),
        source_ref="test:account",
    )


def test_id_classes_are_distinct_and_lowercase_canonical():
    assert type(CompanyChartId.new()) is CompanyChartId
    assert type(CompanyAccountId.new()) is CompanyAccountId
    assert type(CompanyChartId.new()) is not type(CompanyAccountId.new())
    value = CompanyAccountId.new()
    assert CompanyAccountId.parse(str(value)) == value


@pytest.mark.parametrize("code", ["00123", "0000", "6.001", "A/01", "ACCT_1-2"])
def test_account_code_keeps_exact_literal_not_integer_or_zero_padded(code):
    result = AccountCode(code)
    assert result.value == code
    assert isinstance(result.value, str)
    assert AccountCode(result.value) == result


@pytest.mark.parametrize(
    "code", ["", " ", " 00123", "00123 ", "001 23", "à123", "-123", "A" * 65]
)
def test_bad_account_code_is_refused_without_silent_normalization(code):
    with pytest.raises(InvalidCompanyAccount):
        AccountCode(code)


@pytest.mark.parametrize("code", ["", "lower", "  MAIN", "3MAIN", "MAIN/COA"])
def test_bad_chart_code_is_refused_under_temporary_namespace_policy(code):
    with pytest.raises(InvalidCompanyChart):
        ChartCode(code)


def test_opaque_classification_does_not_infer_pcg_or_ifrs_account_nature():
    classification = AccountClassificationCode("INTERNAL_SEGMENT")
    assert classification.value == "INTERNAL_SEGMENT"
    with pytest.raises(InvalidCompanyAccount):
        AccountClassificationCode("ifrs_asset")
    with pytest.raises(InvalidCompanyAccount):
        AccountClassificationCode("")


def test_chart_account_identity_is_stable_across_draft_renames():
    chart = make_chart()
    account = make_account(chart)
    chart_renamed = chart.rename(
        "New chart name", expected_revision=1, reason="Proposed naming review"
    )
    account_renamed = account.rename(
        "New account name", expected_revision=1, reason="Proposed naming review"
    )
    assert chart_renamed.revision == 2 and chart_renamed.label == "New chart name"
    assert account_renamed.revision == 2 and account_renamed.label == "New account name"
    assert chart_renamed == chart
    assert account_renamed == account
    assert hash(account_renamed) == hash(account)
    assert chart.label == "Chart intent"
    assert account.label == "Draft account"


def test_revision_conflicts_reject_stale_bool_and_missing_reason():
    chart = make_chart()
    account = make_account(chart)
    for bad in (0, True, 2):
        with pytest.raises(VersionConflict):
            chart.rename("Changed", expected_revision=bad, reason="reason")
        with pytest.raises(VersionConflict):
            account.rename("Changed", expected_revision=bad, reason="reason")
        with pytest.raises(VersionConflict):
            account.propose_postability(
                False, expected_revision=bad, reason="reason"
            )
    with pytest.raises(InvalidCompanyAccount):
        chart.rename("Changed", expected_revision=1, reason="")
    with pytest.raises(InvalidCompanyAccount):
        account.rename("Changed", expected_revision=1, reason=" ")
    with pytest.raises(InvalidCompanyAccount):
        account.propose_postability(False, expected_revision=1, reason="")


def test_unmodified_values_do_not_create_false_draft_revision():
    chart = make_chart()
    account = make_account(chart)
    with pytest.raises(InvalidCompanyChart):
        chart.rename(chart.label, expected_revision=1, reason="reason")
    with pytest.raises(InvalidCompanyAccount):
        account.rename(account.label, expected_revision=1, reason="reason")
    with pytest.raises(InvalidCompanyAccount):
        account.propose_postability(True, expected_revision=1, reason="reason")


def test_proposed_postability_change_updates_draft_only():
    chart = make_chart()
    account = make_account(chart)
    updated = account.propose_postability(
        False, expected_revision=1, reason="Prepare summary node"
    )
    assert updated.revision == 2 and not updated.postable
    assert account.postable and account.revision == 1
    assert not hasattr(updated, "post")
    assert not hasattr(updated, "activate")
    assert not hasattr(updated, "publish")


def test_non_postable_and_out_of_effective_date_are_local_shape_failures():
    chart = make_chart()
    summary = make_account(chart, postable=False)
    with pytest.raises(AccountNotPostable):
        summary.require_postable_candidate(as_of=date(2026, 1, 1))
    future = make_account(chart, start=date(2026, 7, 1))
    with pytest.raises(AccountNotPostable):
        future.require_postable_candidate(as_of=date(2026, 6, 30))
    future.require_postable_candidate(as_of=date(2026, 7, 1))
    with pytest.raises(InvalidCompanyAccount):
        future.require_postable_candidate(as_of=datetime(2026, 7, 1))


def test_chart_and_account_are_pure_frozen_values():
    chart = make_chart()
    account = make_account(chart)
    with pytest.raises(FrozenInstanceError):
        chart.label = "tampered"
    with pytest.raises(FrozenInstanceError):
        account.code = AccountCode("999")


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", CompanyAccountId.new()),
        ("code", "LOCAL"),
        ("scope", "untyped-scope"),
        ("revision", 0),
        ("revision", True),
        ("effective", "2026"),
        ("source_ref", " "),
        ("label", ""),
    ],
)
def test_invalid_chart_fields_fail_closed(field, value):
    with pytest.raises(InvalidCompanyChart):
        replace(make_chart(), **{field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", CompanyChartId.new()),
        ("chart_id", CompanyAccountId.new()),
        ("code", "00123"),
        ("classification", "ASSET"),
        ("scope", "untyped"),
        ("postable", 1),
        ("revision", 0),
        ("revision", False),
        ("effective", "2026"),
        ("label", " "),
        ("source_ref", " bad "),
    ],
)
def test_invalid_account_fields_fail_closed(field, value):
    chart = make_chart()
    with pytest.raises(InvalidCompanyAccount):
        replace(make_account(chart), **{field: value})


def test_book_level_scope_is_not_treated_as_chart_ownership_evidence():
    chart = make_chart()
    illegal = replace(chart.scope, book_id=AccountingBookId.new())
    with pytest.raises(InvalidCompanyChart):
        replace(chart, scope=illegal)
    with pytest.raises(InvalidCompanyAccount):
        replace(make_account(chart), scope=illegal)


def test_account_must_match_chart_id_scope_and_full_validity():
    chart = make_chart()
    account = make_account(chart)
    require_account_belongs_to_chart(account=account, chart=chart)
    wrong_chart = replace(chart, id=CompanyChartId.new())
    with pytest.raises(ChartAccountScopeConflict):
        require_account_belongs_to_chart(account=account, chart=wrong_chart)
    wrong_scope = replace(chart, scope=replace(
        chart.scope, company_id=CompanyId.new()
    ))
    with pytest.raises(ChartAccountScopeConflict):
        require_account_belongs_to_chart(account=account, chart=wrong_scope)


def test_account_interval_must_be_contained_by_chart_interval():
    chart = make_chart(start=date(2026, 1, 1), end=date(2027, 1, 1))
    for start, end in (
        (date(2025, 12, 1), date(2026, 4, 1)),
        (date(2026, 2, 1), None),
        (date(2026, 2, 1), date(2027, 2, 1)),
    ):
        with pytest.raises(ChartAccountScopeConflict):
            require_account_belongs_to_chart(
                account=make_account(chart, start=start, end=end), chart=chart
            )
    require_account_belongs_to_chart(
        account=make_account(
            chart, start=date(2026, 2, 1), end=date(2026, 12, 1)
        ),
        chart=chart,
    )


def test_duplicate_account_code_overlapping_same_chart_is_rejected():
    chart = make_chart()
    existing = make_account(chart, code="00123")
    duplicate = make_account(chart, code="00123")
    with pytest.raises(DuplicateAccountCode):
        require_unique_account_code(candidate=duplicate, existing=(existing,))


def test_account_codes_do_not_collide_across_different_charts():
    first = make_chart()
    second = make_chart(scope=first.scope)
    a = make_account(first, code="00123")
    b = make_account(second, code="00123")
    require_unique_account_code(candidate=b, existing=(a,))


def test_account_code_can_be_reused_in_adjacent_half_open_periods():
    chart = make_chart()
    existing = make_account(
        chart, code="00123", end=date(2026, 7, 1)
    )
    candidate = make_account(
        chart, code="00123", start=date(2026, 7, 1)
    )
    require_unique_account_code(candidate=candidate, existing=(existing,))


def test_same_account_id_is_revision_not_a_collision():
    chart = make_chart()
    old = make_account(chart)
    revised = old.rename("New", expected_revision=1, reason="Change")
    require_unique_account_code(candidate=revised, existing=(old,))


def test_same_account_id_cannot_be_reassigned_to_another_chart_or_entity():
    chart = make_chart()
    original = make_account(chart)
    other_chart = replace(original, chart_id=CompanyChartId.new())
    with pytest.raises(ChartAccountScopeConflict):
        require_unique_account_code(candidate=other_chart, existing=(original,))
    other_tenant = replace(
        original, scope=replace(original.scope, tenant_id="tenant-b")
    )
    with pytest.raises(ChartAccountScopeConflict):
        require_unique_account_code(candidate=other_tenant, existing=(original,))


def test_chart_code_overlap_in_same_company_and_entity_is_rejected():
    chart = make_chart(code="LOCAL")
    another = make_chart(scope=chart.scope, code="LOCAL")
    with pytest.raises(DuplicateChartCode):
        require_unique_chart_code(candidate=another, existing=(chart,))


def test_chart_code_can_be_reused_in_adjacent_windows_and_other_scopes():
    original = make_chart(end=date(2026, 7, 1))
    next_chart = make_chart(
        scope=original.scope, start=date(2026, 7, 1)
    )
    require_unique_chart_code(candidate=next_chart, existing=(original,))
    different_scope = make_chart(code=original.code.value)
    require_unique_chart_code(candidate=different_scope, existing=(original,))


def test_same_chart_id_cannot_be_attached_to_another_scope():
    chart = make_chart()
    changed = replace(chart, scope=replace(
        chart.scope, legal_entity_id=LegalEntityId.new()
    ))
    with pytest.raises(ChartAccountScopeConflict):
        require_unique_chart_code(candidate=changed, existing=(chart,))


def test_reject_untyped_catalog_values_and_non_tuple_source():
    chart = make_chart()
    account = make_account(chart)
    with pytest.raises(InvalidCompanyAccount):
        require_unique_account_code(candidate=account, existing=[account])
    with pytest.raises(InvalidCompanyAccount):
        require_unique_account_code(candidate=account, existing=("raw",))
    with pytest.raises(InvalidCompanyChart):
        require_unique_chart_code(candidate=chart, existing=[chart])
    with pytest.raises(InvalidCompanyChart):
        require_unique_chart_code(candidate=chart, existing=("raw",))


def test_no_publication_ledger_or_account_mapping_in_pure_domain():
    import ast
    from pathlib import Path

    import pyaccountingkit.company_configuration.domain.chart_of_accounts.model as model

    source = Path(model.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name for node in ast.walk(tree)
        if isinstance(node, ast.Import) for alias in node.names
    }
    assert not imports.intersection({"psycopg", "sqlalchemy", "httpx", "requests"})
    assert "organization_issuer_gateway" not in source
    assert not hasattr(CompanyAccountDraft, "post")
    assert not hasattr(CompanyAccountDraft, "publish")
    assert not hasattr(CompanyChartDraft, "publish")
    assert not hasattr(CompanyChartDraft, "activate")
