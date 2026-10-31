"""L06-01 source-backed fiscal calendar structural kernel, R&D only.

No C10-Q04, approved book, PeriodStatus, SQL fencing, lock, or Ledger posting.
"""

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime

import pytest

from pyaccountingkit.company_configuration.domain.fiscal_calendar import (
    AccountingPeriodDraft,
    CalendarCode,
    CalendarCoveragePolicy,
    FiscalCalendarDraft,
    FiscalStructureConflict,
    FiscalYearCode,
    FiscalYearDraft,
    InvalidAccountingPeriod,
    InvalidFiscalCalendar,
    InvalidFiscalYear,
    PeriodCandidateMissing,
    PeriodCode,
    PeriodKind,
    SpecialPeriodRequiresExplicitTarget,
    preview_adjustment_period_candidate,
    preview_ordinary_period_candidate,
    validate_fiscal_structure,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
)
from pyaccountingkit.company_configuration.domain.shared.errors import InvalidInterval
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountingBookId,
    AccountingPeriodId,
    CompanyId,
    FiscalCalendarId,
    FiscalYearId,
    LegalEntityId,
)

CONTIGUOUS = CalendarCoveragePolicy.REQUIRE_CONTIGUOUS
GAPS = CalendarCoveragePolicy.ALLOW_GAPS
JAN = date(2027, 1, 1)
FEB = date(2027, 2, 1)
MAR = date(2027, 3, 1)
APR = date(2027, 4, 1)
JUL = date(2027, 7, 1)
DEC = date(2027, 12, 1)
END = date(2028, 1, 1)


def calendar(*, start=JAN, end=None):
    return FiscalCalendarDraft(
        id=FiscalCalendarId.new(),
        scope=ConfigurationScope(
            tenant_id="tenant-a",
            company_id=CompanyId.new(),
            legal_entity_id=LegalEntityId.new(),
        ),
        code=CalendarCode("FISCAL_2027"), label="Proposed fiscal calendar",
        effective=EffectiveInterval(start, end),
        jurisdiction_ref="rnd:jurisdiction-claim",
        source_ref="rnd:calendar",
    )


def year(c, *, start=JAN, end=END, code="FY-2027", identity=None):
    return FiscalYearDraft(
        id=identity or FiscalYearId.new(), calendar_id=c.id, scope=c.scope,
        code=FiscalYearCode(code), effective=EffectiveInterval(start, end),
        source_ref="rnd:year",
    )


def period(
    y, *, start=JAN, end=FEB, code="P01", ordinal=1,
    kind=PeriodKind.ORDINARY, target=None, identity=None,
):
    return AccountingPeriodDraft(
        id=identity or AccountingPeriodId.new(),
        fiscal_year_id=y.id, calendar_id=y.calendar_id, scope=y.scope,
        code=PeriodCode(code), kind=kind, effective=EffectiveInterval(start, end),
        source_ref="rnd:period", ordinal=ordinal,
        adjustment_target_id=target,
    )


def structure(*, coverage=CONTIGUOUS):
    c = calendar()
    y = year(c)
    first = period(y)
    second = period(y, start=FEB, end=END, code="P02", ordinal=2)
    return c, (y,), (first, second), coverage


def validate(c, years, periods, coverage=CONTIGUOUS):
    return validate_fiscal_structure(
        calendar=c, years=tuple(years), periods=tuple(periods),
        coverage_policy=coverage,
    )


def ordinary(c, years, periods, day, coverage=CONTIGUOUS):
    return preview_ordinary_period_candidate(
        calendar=c, years=tuple(years), periods=tuple(periods),
        coverage_policy=coverage, as_of=day,
    )


def adjustment(c, years, periods, day, target_id, coverage=CONTIGUOUS):
    return preview_adjustment_period_candidate(
        calendar=c, years=tuple(years), periods=tuple(periods),
        coverage_policy=coverage, as_of=day, adjustment_period_id=target_id,
    )


def test_typed_ids_are_not_interchangeable():
    assert type(FiscalCalendarId.new()) is FiscalCalendarId
    assert type(FiscalYearId.new()) is FiscalYearId
    assert type(AccountingPeriodId.new()) is AccountingPeriodId
    assert type(FiscalCalendarId.new()) is not type(FiscalYearId.new())
    identifier = AccountingPeriodId.new()
    assert AccountingPeriodId.parse(str(identifier)) == identifier


@pytest.mark.parametrize("code", ["FY-2027", "0001", "P01", "445", "Y_01"])
def test_codes_are_literal_strings_preserving_leading_zeroes(code):
    assert FiscalYearCode(code).value == code
    assert PeriodCode(code).value == code


@pytest.mark.parametrize("code", ["", " ", "p01", " P01", "P 01", "ÉTÉ", "A" * 49])
def test_bad_codes_are_refused_without_normalization(code):
    for code_type, error in (
        (CalendarCode, InvalidFiscalCalendar),
        (FiscalYearCode, InvalidFiscalYear),
        (PeriodCode, InvalidAccountingPeriod),
    ):
        with pytest.raises(error):
            code_type(code)


def test_january_calendar_valid_two_periods_and_half_open_selection():
    c, years, ps, coverage = structure()
    validate(c, years, ps, coverage)
    assert ordinary(c, years, ps, JAN).period_id == ps[0].id
    assert ordinary(c, years, ps, FEB).period_id == ps[1].id
    assert ordinary(c, years, ps, date(2027, 1, 31)).period_id == ps[0].id
    assert ordinary(c, years, ps, FEB).code.value == "P02"
    with pytest.raises(PeriodCandidateMissing):
        ordinary(c, years, ps, END)


def test_calendar_year_is_not_forced_to_calendar_year_or_twelve_months():
    c = calendar(start=date(2026, 4, 1))
    y = year(c, start=date(2026, 4, 1), end=date(2027, 4, 1),
             code="FY-2026-27")
    a = period(y, start=date(2026, 4, 1), end=date(2026, 10, 1))
    b = period(
        y, start=date(2026, 10, 1), end=date(2027, 4, 1),
        ordinal=2, code="P02",
    )
    validate(c, (y,), (a, b))
    assert ordinary(c, (y,), (a, b), date(2027, 2, 1)).period_id == b.id


def test_twelve_months_are_an_illustrative_valid_fixture_not_mandatory():
    c = calendar()
    y = year(c)
    starts = [date(2027, m, 1) for m in range(1, 13)]
    ends = starts[1:] + [END]
    items = tuple(
        period(y, start=starts[i], end=ends[i], ordinal=i + 1,
               code=f"P{i + 1:02d}")
        for i in range(12)
    )
    validate(c, (y,), items)
    assert ordinary(c, (y,), items, DEC).period_id == items[-1].id


def test_overlap_in_any_future_ordinary_period_refused_before_preview():
    c, ys, ps, _ = structure()
    future_overlap = period(
        ys[0], start=MAR, end=JUL, ordinal=3, code="P03",
    )
    with pytest.raises(FiscalStructureConflict, match="Overlapping ordinary"):
        ordinary(c, ys, (*ps, future_overlap), JAN)


def test_adjacent_periods_without_overlap_are_accepted():
    c, ys, ps, _ = structure()
    assert ps[0].effective.end == ps[1].effective.start
    validate(c, ys, ps)


def test_gap_is_refused_only_for_explicit_contiguous_policy():
    c = calendar()
    y = year(c)
    a = period(y, start=JAN, end=FEB)
    b = period(y, start=MAR, end=END, code="P02", ordinal=2)
    with pytest.raises(FiscalStructureConflict, match="continuous"):
        validate(c, (y,), (a, b))
    validate(c, (y,), (a, b), GAPS)
    with pytest.raises(PeriodCandidateMissing, match="No ordinary"):
        ordinary(c, (y,), (a, b), FEB, GAPS)


def test_contiguous_coverage_rejects_missing_first_or_last_day():
    c, years, ps, _ = structure()
    with pytest.raises(FiscalStructureConflict, match="continuous"):
        validate(c, years, (replace(ps[0], effective=EffectiveInterval(FEB, MAR)),
                             replace(ps[1], effective=EffectiveInterval(MAR, END))))
    with pytest.raises(FiscalStructureConflict, match="continuous"):
        validate(c, years, (ps[0], replace(
            ps[1], effective=EffectiveInterval(FEB, DEC)
        )))


def test_ordinals_must_be_positive_strict_and_chronologically_increasing():
    c, ys, ps, _ = structure()
    for bad in (None, 0, -1, True, 1.0, "1"):
        with pytest.raises(InvalidAccountingPeriod, match="positive ordinal"):
            replace(ps[0], ordinal=bad)
    with pytest.raises(FiscalStructureConflict, match="Duplicate ordinary ordinal"):
        validate(c, ys, (ps[0], replace(ps[1], ordinal=1)))
    with pytest.raises(FiscalStructureConflict, match="not chronological"):
        validate(c, ys, (replace(ps[0], ordinal=2), replace(ps[1], ordinal=1)))


def test_duplicate_period_code_or_identity_is_refused():
    c, ys, ps, _ = structure()
    with pytest.raises(FiscalStructureConflict, match="Duplicate period identity"):
        validate(c, ys, (ps[0], ps[0], ps[1]))
    with pytest.raises(FiscalStructureConflict, match="Duplicate period code"):
        validate(c, ys, (ps[0], replace(ps[1], code=ps[0].code)))


def test_same_period_code_may_be_reused_in_distinct_nonoverlapping_years():
    c, ys, ps, _ = structure()
    y2 = year(c, start=END, end=date(2029, 1, 1), code="FY-2028")
    p2 = period(
        y2, start=END, end=date(2029, 1, 1), code="P01",
    )
    validate(c, (*ys, y2), (*ps, p2))
    assert ordinary(c, (*ys, y2), (*ps, p2), END).period_id == p2.id


def test_overlapping_fiscal_years_rejected_even_with_different_codes():
    c, ys, ps, _ = structure()
    y2 = year(c, start=JUL, end=date(2028, 7, 1), code="FY-OTHER")
    with pytest.raises(FiscalStructureConflict, match="Overlapping fiscal years"):
        validate(c, (*ys, y2), ps)


def test_duplicate_fiscal_year_id_or_code_are_rejected():
    c, ys, ps, _ = structure()
    y2 = year(c, start=END, end=date(2029, 1, 1), code="FY-2027")
    with pytest.raises(FiscalStructureConflict, match="Duplicate fiscal year"):
        validate(c, (*ys, y2), ps)
    with pytest.raises(FiscalStructureConflict, match="Duplicate fiscal year"):
        validate(c, (*ys, replace(y2, id=ys[0].id, code=FiscalYearCode("FY-2028"))), ps)


def test_outside_calendar_and_outside_year_are_rejected():
    c, ys, ps, _ = structure()
    short = replace(c, effective=EffectiveInterval(FEB, END))
    with pytest.raises(FiscalStructureConflict, match="outside calendar"):
        validate(short, ys, ps)
    extraneous = period(ys[0], start=date(2026, 12, 1), end=JAN, code="P00")
    with pytest.raises(FiscalStructureConflict, match="outside fiscal year"):
        validate(c, ys, (*ps, extraneous))


def test_fiscal_year_must_have_finite_interval():
    c = calendar()
    with pytest.raises(InvalidFiscalYear, match="finite"):
        year(c, end=None)


def test_period_must_have_finite_interval():
    c, ys, _, _ = structure()
    with pytest.raises(InvalidAccountingPeriod, match="finite"):
        period(ys[0], end=None)


def test_half_open_interval_rejects_empty_or_reversed_dates():
    with pytest.raises(InvalidInterval):
        EffectiveInterval(JAN, JAN)
    with pytest.raises(InvalidInterval):
        EffectiveInterval(FEB, JAN)


def test_empty_year_and_catalog_types_denied():
    c = calendar()
    with pytest.raises(FiscalStructureConflict, match="At least one"):
        validate_fiscal_structure(
            calendar=c, years=(), periods=(), coverage_policy=CONTIGUOUS
        )
    with pytest.raises(FiscalStructureConflict, match="tuples"):
        validate_fiscal_structure(
            calendar=c, years=[], periods=(), coverage_policy=CONTIGUOUS
        )
    with pytest.raises(InvalidFiscalYear, match="non-year"):
        validate_fiscal_structure(
            calendar=c, years=("raw",), periods=(),
            coverage_policy=CONTIGUOUS,
        )


def test_year_without_any_ordinary_period_is_incomplete_candidate():
    c = calendar()
    y = year(c)
    with pytest.raises(PeriodCandidateMissing, match="no ordinary"):
        validate(c, (y,), ())


def test_wrong_scope_calendar_year_and_period_fail_closed():
    c, ys, ps, _ = structure()
    foreign = replace(ys[0], scope=replace(c.scope, tenant_id="tenant-b"))
    with pytest.raises(FiscalStructureConflict, match="Foreign year"):
        validate(c, (foreign,), ps)
    foreign_period = replace(ps[0], scope=replace(c.scope, company_id=CompanyId.new()))
    with pytest.raises(FiscalStructureConflict, match="cross-scope period"):
        validate(c, ys, (foreign_period, ps[1]))
    with pytest.raises(FiscalStructureConflict, match="Orphan"):
        validate(c, ys, (replace(ps[0], fiscal_year_id=FiscalYearId.new()), ps[1]))


def test_book_scope_cannot_fake_calendar_ownership():
    c, ys, ps, _ = structure()
    scope = replace(c.scope, book_id=AccountingBookId.new())
    with pytest.raises(InvalidFiscalCalendar, match="Entity-level"):
        replace(c, scope=scope)
    with pytest.raises(InvalidFiscalYear, match="Entity-level"):
        replace(ys[0], scope=scope)
    with pytest.raises(InvalidAccountingPeriod, match="Entity-level"):
        replace(ps[0], scope=scope)


def test_wrong_typed_id_and_field_are_refused():
    c, ys, ps, _ = structure()
    for obj, changes, error in (
        (c, {"id": FiscalYearId.new()}, InvalidFiscalCalendar),
        (c, {"code": "FISCAL"}, InvalidFiscalCalendar),
        (ys[0], {"id": c.id}, InvalidFiscalYear),
        (ys[0], {"calendar_id": FiscalYearId.new()}, InvalidFiscalYear),
        (ys[0], {"code": "FY"}, InvalidFiscalYear),
        (ps[0], {"id": ys[0].id}, InvalidAccountingPeriod),
        (ps[0], {"kind": "ORDINARY"}, InvalidAccountingPeriod),
        (ps[0], {"code": "P01"}, InvalidAccountingPeriod),
    ):
        with pytest.raises(error):
            replace(obj, **changes)


def test_malformed_metadata_and_sources_are_refused():
    c, ys, ps, _ = structure()
    for change in ({"label": ""}, {"jurisdiction_ref": " bad "}, {"source_ref": ""}):
        with pytest.raises(InvalidFiscalCalendar):
            replace(c, **change)
    with pytest.raises(InvalidFiscalYear):
        replace(ys[0], source_ref=" ")
    with pytest.raises(InvalidAccountingPeriod):
        replace(ps[0], source_ref=" wrong ")


def test_entity_identity_stable_under_label_changes():
    c, ys, ps, _ = structure()
    new_label = replace(c, label="Amended proposed calendar")
    assert new_label is not c and new_label == c
    assert hash(new_label) == hash(c)
    assert replace(ys[0], source_ref="revised") == ys[0]
    assert replace(ps[0], source_ref="revised") == ps[0]


def test_adjustment_requires_explicit_ordinary_target_id():
    c, ys, ps, _ = structure()
    with pytest.raises(SpecialPeriodRequiresExplicitTarget):
        period(ys[0], start=FEB, end=MAR, kind=PeriodKind.ADJUSTMENT,
               ordinal=None, code="ADJ")
    with pytest.raises(InvalidAccountingPeriod, match="cannot target"):
        replace(ps[0], adjustment_target_id=ps[1].id)


def test_adjustment_overlapping_ordinary_is_allowed_but_never_default_selected():
    c, ys, ps, _ = structure()
    special = period(
        ys[0], start=FEB, end=MAR, kind=PeriodKind.ADJUSTMENT,
        ordinal=None, target=ps[1].id, code="ADJ",
    )
    validate(c, ys, (*ps, special))
    ordinary_result = ordinary(c, ys, (*ps, special), FEB)
    explicit = adjustment(c, ys, (*ps, special), FEB, special.id)
    assert ordinary_result.period_id == ps[1].id
    assert ordinary_result.kind is PeriodKind.ORDINARY
    assert explicit.period_id == special.id
    assert explicit.kind is PeriodKind.ADJUSTMENT
    assert explicit.adjustment_target_id == ps[1].id
    assert not hasattr(explicit, "post")
    assert not hasattr(explicit, "potentially_postable")
    assert not hasattr(explicit, "open")


def test_adjustment_requires_correct_exact_id_and_in_period_date():
    c, ys, ps, _ = structure()
    special = period(
        ys[0], start=FEB, end=MAR, kind=PeriodKind.ADJUSTMENT,
        ordinal=None, target=ps[1].id, code="ADJ",
    )
    with pytest.raises(SpecialPeriodRequiresExplicitTarget):
        adjustment(c, ys, (*ps, special), FEB, AccountingPeriodId.new())
    with pytest.raises(SpecialPeriodRequiresExplicitTarget):
        adjustment(c, ys, (*ps, special), JAN, special.id)
    with pytest.raises(SpecialPeriodRequiresExplicitTarget):
        adjustment(c, ys, (*ps, special), FEB, "ADJ")


def test_adjustment_target_must_exist_be_ordinary_and_overlap():
    c, ys, ps, _ = structure()
    special = period(
        ys[0], start=FEB, end=MAR, kind=PeriodKind.ADJUSTMENT,
        ordinal=None, target=AccountingPeriodId.new(), code="ADJ",
    )
    with pytest.raises(SpecialPeriodRequiresExplicitTarget, match="absent"):
        validate(c, ys, (*ps, special))
    valid = replace(special, adjustment_target_id=ps[0].id)
    with pytest.raises(SpecialPeriodRequiresExplicitTarget, match="outside"):
        validate(c, ys, (*ps, valid))


def test_period_overlap_allowed_only_for_explicit_special_kind():
    c, ys, ps, _ = structure()
    third_ordinary = period(
        ys[0], start=FEB, end=MAR, code="P03", ordinal=3,
    )
    with pytest.raises(FiscalStructureConflict, match="Overlapping ordinary"):
        validate(c, ys, (*ps, third_ordinary))
    special = period(
        ys[0], start=FEB, end=MAR, code="ADJ", kind=PeriodKind.ADJUSTMENT,
        ordinal=None, target=ps[1].id,
    )
    validate(c, ys, (*ps, special))


def test_explicit_coverage_policy_is_mandatory():
    c, years, ps, _ = structure()
    with pytest.raises(InvalidFiscalCalendar, match="Explicit"):
        validate_fiscal_structure(
            calendar=c, years=years, periods=ps, coverage_policy="REQUIRE_CONTIGUOUS"
        )


def test_preview_requires_business_date_not_technical_datetime():
    c, years, ps, _ = structure()
    with pytest.raises(InvalidAccountingPeriod, match="business date"):
        ordinary(c, years, ps, datetime(2027, 1, 5))
    with pytest.raises(InvalidAccountingPeriod, match="business date"):
        adjustment(c, years, ps, datetime(2027, 1, 5), AccountingPeriodId.new())


def test_no_default_calendar_or_unknown_year_fallback():
    c, ys, ps, _ = structure()
    with pytest.raises(PeriodCandidateMissing, match="No proposed fiscal year"):
        ordinary(c, ys, ps, date(2026, 12, 31))
    with pytest.raises(PeriodCandidateMissing, match="No proposed fiscal year"):
        ordinary(c, ys, ps, date(2028, 1, 2))


def test_immutable_drafts_and_pure_domain_no_publish_or_status_mutation():
    c, ys, ps, _ = structure()
    with pytest.raises(FrozenInstanceError):
        c.label = "tampered"
    with pytest.raises(FrozenInstanceError):
        ys[0].source_ref = "tampered"
    with pytest.raises(FrozenInstanceError):
        ps[0].code = PeriodCode("NEW")
    for obj in (c, ys[0], ps[0]):
        for method in ("publish", "open", "close", "reopen", "post", "lock"):
            assert not hasattr(obj, method)


def test_no_sql_ledger_authorization_or_durable_booking_imports():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.domain.fiscal_calendar import model

    source = Path(model.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    third_party = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not third_party.intersection({
        "sqlalchemy", "psycopg", "requests", "httpx", "django"
    })
    for text in ("organization_issuer_gateway", "get_period_status", "commit_posting"):
        assert text not in source.lower()
