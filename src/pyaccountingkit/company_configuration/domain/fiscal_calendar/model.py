"""L06-01 — pure, unpublished fiscal calendar structure (R&D only).

No approved normative calendar, live book, PeriodStatus, lock, transition,
C10-Q04, authoritative postability decision or Ledger posting API exists here.
"""

import re
from dataclasses import dataclass
from datetime import date
from enum import Enum

from ..shared.accounting_scope import ConfigurationScope
from ..shared.effective_interval import EffectiveInterval
from ..shared.errors import DomainError
from ..shared.identifiers import AccountingPeriodId, FiscalCalendarId, FiscalYearId


class InvalidFiscalCalendar(DomainError):
    code = "INVALID_FISCAL_CALENDAR"


class InvalidFiscalYear(DomainError):
    code = "INVALID_FISCAL_YEAR"


class InvalidAccountingPeriod(DomainError):
    code = "INVALID_ACCOUNTING_PERIOD"


class FiscalStructureConflict(DomainError):
    code = "FISCAL_STRUCTURE_CONFLICT"


class PeriodCandidateMissing(DomainError):
    code = "PERIOD_CANDIDATE_MISSING"


class PeriodCandidateAmbiguous(DomainError):
    code = "PERIOD_CANDIDATE_AMBIGUOUS"


class SpecialPeriodRequiresExplicitTarget(DomainError):
    code = "SPECIAL_PERIOD_REQUIRES_EXPLICIT_TARGET"


def _code(value: str, *, error: type[DomainError], name: str) -> None:
    if not isinstance(value, str) or re.fullmatch(
        r"[A-Z0-9][A-Z0-9_-]{0,47}", value
    ) is None:
        raise error(f"{name} requires a canonical uppercase ASCII code")


def _label(value: str, *, error: type[DomainError], name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value.strip() != value
        or len(value) > 200
    ):
        raise error(f"{name} requires a canonical, nonempty label/source")


def _covers(outer: EffectiveInterval, inner: EffectiveInterval) -> bool:
    return outer.start <= inner.start and (
        outer.end is None or (inner.end is not None and inner.end <= outer.end)
    )


@dataclass(frozen=True, slots=True)
class CalendarCode:
    """Provisional opaque business code (not identity or ISO calendar claim)."""

    value: str

    def __post_init__(self) -> None:
        _code(self.value, error=InvalidFiscalCalendar, name="CalendarCode")


@dataclass(frozen=True, slots=True)
class FiscalYearCode:
    value: str

    def __post_init__(self) -> None:
        _code(self.value, error=InvalidFiscalYear, name="FiscalYearCode")


@dataclass(frozen=True, slots=True)
class PeriodCode:
    """Literal period code: leading zeros remain significant text."""

    value: str

    def __post_init__(self) -> None:
        _code(self.value, error=InvalidAccountingPeriod, name="PeriodCode")


class PeriodKind(Enum):
    ORDINARY = "ORDINARY"
    ADJUSTMENT = "ADJUSTMENT"


class CalendarCoveragePolicy(Enum):
    """Explicit local structural choice, not approved jurisdictional policy."""

    REQUIRE_CONTIGUOUS = "REQUIRE_CONTIGUOUS"
    ALLOW_GAPS = "ALLOW_GAPS"


@dataclass(frozen=True, slots=True, eq=False)
class FiscalCalendarDraft:
    id: FiscalCalendarId
    scope: ConfigurationScope
    code: CalendarCode
    label: str
    effective: EffectiveInterval
    jurisdiction_ref: str
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, FiscalCalendarId):
            raise InvalidFiscalCalendar("Typed calendar identity required")
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is not None:
            raise InvalidFiscalCalendar("Entity-level claimed calendar scope required")
        if not isinstance(self.code, CalendarCode):
            raise InvalidFiscalCalendar("Typed calendar code required")
        if not isinstance(self.effective, EffectiveInterval):
            raise InvalidFiscalCalendar("Business-date calendar validity required")
        for name in ("label", "jurisdiction_ref", "source_ref"):
            _label(getattr(self, name), error=InvalidFiscalCalendar, name=name)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, FiscalCalendarDraft)
            and (self.scope, self.id) == (other.scope, other.id)
        )

    def __hash__(self) -> int:
        return hash((self.scope, self.id))


@dataclass(frozen=True, slots=True, eq=False)
class FiscalYearDraft:
    id: FiscalYearId
    calendar_id: FiscalCalendarId
    scope: ConfigurationScope
    code: FiscalYearCode
    effective: EffectiveInterval
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, FiscalYearId):
            raise InvalidFiscalYear("Typed fiscal-year identity required")
        if not isinstance(self.calendar_id, FiscalCalendarId):
            raise InvalidFiscalYear("Typed calendar identity required")
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is not None:
            raise InvalidFiscalYear("Entity-level claimed year scope required")
        if not isinstance(self.code, FiscalYearCode):
            raise InvalidFiscalYear("Typed fiscal-year code required")
        if (
            not isinstance(self.effective, EffectiveInterval)
            or self.effective.end is None
        ):
            raise InvalidFiscalYear("Fiscal year needs a finite business-date interval")
        _label(self.source_ref, error=InvalidFiscalYear, name="source_ref")

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, FiscalYearDraft)
            and (self.scope, self.id) == (other.scope, other.id)
        )

    def __hash__(self) -> int:
        return hash((self.scope, self.id))


@dataclass(frozen=True, slots=True, eq=False)
class AccountingPeriodDraft:
    """Ordinary period or explicitly linked special adjustment candidate."""

    id: AccountingPeriodId
    fiscal_year_id: FiscalYearId
    calendar_id: FiscalCalendarId
    scope: ConfigurationScope
    code: PeriodCode
    kind: PeriodKind
    effective: EffectiveInterval
    source_ref: str
    ordinal: int | None = None
    adjustment_target_id: AccountingPeriodId | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, AccountingPeriodId):
            raise InvalidAccountingPeriod("Typed period identity required")
        if not isinstance(self.fiscal_year_id, FiscalYearId) or not isinstance(
            self.calendar_id, FiscalCalendarId
        ):
            raise InvalidAccountingPeriod("Typed year and calendar IDs required")
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is not None:
            raise InvalidAccountingPeriod("Entity-level claimed period scope required")
        if not isinstance(self.code, PeriodCode) or not isinstance(
            self.kind, PeriodKind
        ):
            raise InvalidAccountingPeriod("Typed code and kind required")
        if (
            not isinstance(self.effective, EffectiveInterval)
            or self.effective.end is None
        ):
            raise InvalidAccountingPeriod("Period needs finite business-date interval")
        _label(self.source_ref, error=InvalidAccountingPeriod, name="source_ref")
        if self.kind is PeriodKind.ORDINARY:
            if type(self.ordinal) is not int or self.ordinal <= 0:
                raise InvalidAccountingPeriod("Ordinary period needs positive ordinal")
            if self.adjustment_target_id is not None:
                raise InvalidAccountingPeriod("Ordinary period cannot target adjustment")
        else:
            if self.ordinal is not None:
                raise InvalidAccountingPeriod("Adjustment is not an ordinary ordinal")
            if not isinstance(self.adjustment_target_id, AccountingPeriodId):
                raise SpecialPeriodRequiresExplicitTarget(
                    "Adjustment must target an explicit ordinary period identity"
                )
            if self.adjustment_target_id == self.id:
                raise SpecialPeriodRequiresExplicitTarget("Special period cannot target itself")

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, AccountingPeriodDraft)
            and (self.scope, self.id) == (other.scope, other.id)
        )

    def __hash__(self) -> int:
        return hash((self.scope, self.id))


@dataclass(frozen=True, slots=True)
class FiscalPeriodCandidatePreview:
    """Structural selection only; NOT a C10-Q04 posting-period authorization."""

    calendar_id: FiscalCalendarId
    fiscal_year_id: FiscalYearId
    period_id: AccountingPeriodId
    code: PeriodCode
    kind: PeriodKind
    as_of: date
    adjustment_target_id: AccountingPeriodId | None = None


def validate_fiscal_structure(
    *,
    calendar: FiscalCalendarDraft,
    years: tuple[FiscalYearDraft, ...],
    periods: tuple[AccountingPeriodDraft, ...],
    coverage_policy: CalendarCoveragePolicy,
) -> None:
    """Validate the COMPLETE candidate catalog and all dates, not merely today.

    Period coverage is a mandatory EXPLICIT choice. Neither choice implies
    legal calendar compatibility or rights to book journal entries.
    """
    if not isinstance(calendar, FiscalCalendarDraft):
        raise InvalidFiscalCalendar("Typed calendar draft required")
    if not isinstance(coverage_policy, CalendarCoveragePolicy):
        raise InvalidFiscalCalendar("Explicit structural coverage policy required")
    if not isinstance(years, tuple) or not isinstance(periods, tuple):
        raise FiscalStructureConflict("Immutable year/period tuples required")
    if not years:
        raise FiscalStructureConflict("At least one proposed fiscal year required")

    by_year: dict[FiscalYearId, FiscalYearDraft] = {}
    codes: set[str] = set()
    for year in years:
        if not isinstance(year, FiscalYearDraft):
            raise InvalidFiscalYear("Catalog includes non-year")
        if year.calendar_id != calendar.id or year.scope != calendar.scope:
            raise FiscalStructureConflict("Foreign year calendar/tenant/entity scope")
        if not _covers(calendar.effective, year.effective):
            raise FiscalStructureConflict("Fiscal year outside calendar validity")
        if year.id in by_year or year.code.value in codes:
            raise FiscalStructureConflict("Duplicate fiscal year identity/code")
        if any(year.effective.overlaps(other.effective) for other in by_year.values()):
            raise FiscalStructureConflict("Overlapping fiscal years in calendar")
        by_year[year.id] = year
        codes.add(year.code.value)

    by_period: dict[AccountingPeriodId, AccountingPeriodDraft] = {}
    ordinary_by_year: dict[FiscalYearId, list[AccountingPeriodDraft]] = {
        year_id: [] for year_id in by_year
    }
    code_by_year: set[tuple[FiscalYearId, str]] = set()
    ordinal_by_year: set[tuple[FiscalYearId, int]] = set()
    adjustments: list[AccountingPeriodDraft] = []
    for period in periods:
        if not isinstance(period, AccountingPeriodDraft):
            raise InvalidAccountingPeriod("Catalog includes non-period")
        if period.id in by_period:
            raise FiscalStructureConflict("Duplicate period identity")
        by_period[period.id] = period
        year = by_year.get(period.fiscal_year_id)
        if (
            year is None
            or period.calendar_id != calendar.id
            or period.scope != calendar.scope
        ):
            raise FiscalStructureConflict("Orphan/cross-scope period")
        if not _covers(year.effective, period.effective):
            raise FiscalStructureConflict("Period outside fiscal year interval")
        key = (year.id, period.code.value)
        if key in code_by_year:
            raise FiscalStructureConflict("Duplicate period code within year")
        code_by_year.add(key)
        if period.kind is PeriodKind.ORDINARY:
            ordinal = (year.id, period.ordinal)
            if ordinal in ordinal_by_year:
                raise FiscalStructureConflict("Duplicate ordinary ordinal in year")
            ordinal_by_year.add(ordinal)
            ordinary_by_year[year.id].append(period)
        else:
            adjustments.append(period)

    for year_id, items in ordinary_by_year.items():
        if not items:
            raise PeriodCandidateMissing("Fiscal year has no ordinary period")
        items.sort(key=lambda p: p.effective.start)
        for left, right in zip(items, items[1:]):
            if left.effective.overlaps(right.effective):
                raise FiscalStructureConflict("Overlapping ordinary periods")
            if left.ordinal >= right.ordinal:
                raise FiscalStructureConflict("Ordinary ordinals not chronological")
        if coverage_policy is CalendarCoveragePolicy.REQUIRE_CONTIGUOUS:
            year = by_year[year_id]
            if (
                items[0].effective.start != year.effective.start
                or items[-1].effective.end != year.effective.end
                or any(a.effective.end != z.effective.start
                       for a, z in zip(items, items[1:]))
            ):
                raise FiscalStructureConflict("Required continuous year coverage is missing")

    for special in adjustments:
        target = by_period.get(special.adjustment_target_id)
        if target is None or target.kind is not PeriodKind.ORDINARY:
            raise SpecialPeriodRequiresExplicitTarget(
                "Adjustment targets absent/nonordinary period"
            )
        if target.fiscal_year_id != special.fiscal_year_id or not (
            target.effective.overlaps(special.effective)
        ):
            raise SpecialPeriodRequiresExplicitTarget(
                "Adjustment target is outside corresponding year/period"
            )


def _resolve(
    *,
    calendar: FiscalCalendarDraft,
    years: tuple[FiscalYearDraft, ...],
    periods: tuple[AccountingPeriodDraft, ...],
    coverage_policy: CalendarCoveragePolicy,
    as_of: date,
    explicit_adjustment_id: AccountingPeriodId | None,
) -> FiscalPeriodCandidatePreview:
    if type(as_of) is not date:
        raise InvalidAccountingPeriod("Explicit business date (not datetime) required")
    if explicit_adjustment_id is not None and not isinstance(
        explicit_adjustment_id, AccountingPeriodId
    ):
        raise InvalidAccountingPeriod("Typed special period selection ID required")
    validate_fiscal_structure(
        calendar=calendar, years=years, periods=periods, coverage_policy=coverage_policy
    )
    year_matches = [y for y in years if y.effective.contains(as_of)]
    if not year_matches:
        raise PeriodCandidateMissing("No proposed fiscal year for requested business date")
    if len(year_matches) != 1:
        raise PeriodCandidateAmbiguous("Multiple applicable fiscal years")
    year = year_matches[0]
    candidates = [
        p for p in periods
        if p.fiscal_year_id == year.id
        and p.effective.contains(as_of)
        and (
            (p.kind is PeriodKind.ORDINARY)
            if explicit_adjustment_id is None
            else (p.kind is PeriodKind.ADJUSTMENT and p.id == explicit_adjustment_id)
        )
    ]
    if not candidates:
        if explicit_adjustment_id is not None:
            raise SpecialPeriodRequiresExplicitTarget(
                "Requested adjustment ID is not applicable at business date"
            )
        raise PeriodCandidateMissing("No ordinary period for business date; no fallback")
    if len(candidates) != 1:
        raise PeriodCandidateAmbiguous("Multiple applicable candidate periods")
    selected = candidates[0]
    return FiscalPeriodCandidatePreview(
        calendar_id=calendar.id,
        fiscal_year_id=year.id,
        period_id=selected.id,
        code=selected.code,
        kind=selected.kind,
        as_of=as_of,
        adjustment_target_id=selected.adjustment_target_id,
    )


def preview_ordinary_period_candidate(
    *, calendar: FiscalCalendarDraft,
    years: tuple[FiscalYearDraft, ...],
    periods: tuple[AccountingPeriodDraft, ...],
    coverage_policy: CalendarCoveragePolicy,
    as_of: date,
) -> FiscalPeriodCandidatePreview:
    """Ordinary date-based preview, never implicitly selects ADJUSTMENT."""
    return _resolve(
        calendar=calendar, years=years, periods=periods,
        coverage_policy=coverage_policy, as_of=as_of,
        explicit_adjustment_id=None,
    )


def preview_adjustment_period_candidate(
    *, calendar: FiscalCalendarDraft,
    years: tuple[FiscalYearDraft, ...],
    periods: tuple[AccountingPeriodDraft, ...],
    coverage_policy: CalendarCoveragePolicy,
    as_of: date,
    adjustment_period_id: AccountingPeriodId,
) -> FiscalPeriodCandidatePreview:
    """Explicit ID required; neither a reopening nor special posting permission."""
    if not isinstance(adjustment_period_id, AccountingPeriodId):
        raise SpecialPeriodRequiresExplicitTarget("Typed explicit adjustment ID required")
    return _resolve(
        calendar=calendar, years=years, periods=periods,
        coverage_policy=coverage_policy, as_of=as_of,
        explicit_adjustment_id=adjustment_period_id,
    )
