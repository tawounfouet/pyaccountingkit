"""L06-07 multi-book R&D replay: no real E2E, posting, or G6 approval."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from pyaccountingkit.company_configuration.application.fiscal_c10_q04_simulation import (
    InvalidPeriodStatusSimulation,
    UntrustedPeriodStatusForPosting,
    reject_simulated_status_for_posting,
)
from pyaccountingkit.company_configuration.application.fiscal_multibook_qualification_rnd import (
    BookCandidateFixture,
    BookReplayQueryCandidate,
    InvalidMultiBookCandidate,
    MultiBookCandidateAmbiguous,
    MultiBookQualificationTampered,
    UnprovenL06ProductionGate,
    qualify_multibook_candidate_replay,
)
from pyaccountingkit.company_configuration.domain.fiscal_calendar import (
    AccountingPeriodDraft,
    BookCalendarAssignmentCandidate,
    BookCalendarCandidateMissing,
    CalendarCode,
    CalendarCoveragePolicy,
    CalendarVersionCandidate,
    FiscalCalendarDraft,
    FiscalYearCode,
    FiscalYearDraft,
    ObservationCompleteness,
    PeriodCode,
    PeriodKind,
    PeriodLockObservationCandidate,
    PeriodLockScopeCandidate,
    PeriodStateObservationCandidate,
    PeriodStatusCandidate,
    preview_ordinary_period_candidate,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
    KnowledgeInterval,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountingBookId,
    AccountingPeriodId,
    BookCalendarAssignmentCandidateId,
    CalendarCandidateVersionId,
    CompanyId,
    FiscalCalendarId,
    FiscalYearId,
    LegalEntityId,
    PeriodLockCandidateId,
    PeriodStateCandidateId,
)

JAN = datetime(2027, 1, 1, tzinfo=UTC)
FEB = datetime(2027, 2, 1, tzinfo=UTC)
MAR = datetime(2027, 3, 1, tzinfo=UTC)
DAY = date(2027, 2, 15)
END = date(2028, 1, 1)
APR26 = date(2026, 4, 1)
APR27 = date(2027, 4, 1)
COMPLETE = ObservationCompleteness.DECLARED_COMPLETE_RND


def calendar(scope, code, start, end):
    return FiscalCalendarDraft(
        FiscalCalendarId.new(), scope, CalendarCode(code),
        "Unverified calendar for " + code,
        EffectiveInterval(start, end), "rnd:jurisdiction-unapproved",
        "rnd:calendar",
    )


def year(cal, start, end, code):
    return FiscalYearDraft(
        FiscalYearId.new(), cal.id, cal.scope, FiscalYearCode(code),
        EffectiveInterval(start, end), "rnd:fiscal-year",
    )


def period(fiscal_year, cal, start, end, code, ordinal):
    return AccountingPeriodDraft(
        AccountingPeriodId.new(), fiscal_year.id, cal.id, cal.scope,
        PeriodCode(code), PeriodKind.ORDINARY,
        EffectiveInterval(start, end), "rnd:period", ordinal,
    )


def version(cal, year_obj, items, *, knowledge):
    return CalendarVersionCandidate(
        CalendarCandidateVersionId.new(), cal, (year_obj,), tuple(items),
        CalendarCoveragePolicy.REQUIRE_CONTIGUOUS, cal.effective,
        knowledge, "rnd:calendar-version",
    )


def assignment(scope, value, *, knowledge):
    return BookCalendarAssignmentCandidate(
        BookCalendarAssignmentCandidateId.new(),
        scope, value.calendar.id, value.id, value.effective,
        knowledge, "rnd:book-calendar-assignment",
    )


def state(scope, value, item, status=PeriodStatusCandidate.OPEN, revision=1):
    return PeriodStateObservationCandidate(
        PeriodStateCandidateId.new(), scope, value.id, item.id,
        status, revision, KnowledgeInterval(JAN), "rnd:state-observation",
    )


def scenario():
    """Two claimed books; PCG/IFRS are *names*, not validated normative frameworks."""
    entity = ConfigurationScope("tenant-a", CompanyId.new(), LegalEntityId.new())
    book_pcg = replace(entity, book_id=AccountingBookId.new())
    book_ifrs = replace(entity, book_id=AccountingBookId.new())

    cal_pcg = calendar(entity, "PCG_RND", date(2027, 1, 1), END)
    year_pcg = year(cal_pcg, date(2027, 1, 1), END, "FY2027")
    p1 = period(
        year_pcg, cal_pcg, date(2027, 1, 1), date(2027, 2, 1), "P01", 1
    )
    p2 = period(year_pcg, cal_pcg, date(2027, 2, 1), END, "P02", 2)
    old = version(cal_pcg, year_pcg, (p1, p2), knowledge=KnowledgeInterval(JAN, MAR))
    corrected_p1 = replace(p1, effective=EffectiveInterval(date(2027, 1, 1), date(
        2027, 3, 1
    )))
    corrected_p2 = replace(p2, effective=EffectiveInterval(date(2027, 3, 1), END))
    restated = version(
        cal_pcg, year_pcg, (corrected_p1, corrected_p2),
        knowledge=KnowledgeInterval(MAR),
    )
    pcg_fixture = BookCandidateFixture(
        book_pcg,
        (
            assignment(book_pcg, old, knowledge=KnowledgeInterval(JAN, MAR)),
            assignment(book_pcg, restated, knowledge=KnowledgeInterval(MAR)),
        ),
        (old, restated),
        (
            state(book_pcg, old, p2),
            state(
                book_pcg, restated, corrected_p1,
                status=PeriodStatusCandidate.CLOSED, revision=2,
            ),
        ),
    )

    cal_ifrs = calendar(entity, "IFRS_RND", APR26, APR27)
    year_ifrs = year(cal_ifrs, APR26, APR27, "FY2026_27")
    ifrs_early = period(
        year_ifrs, cal_ifrs, APR26, date(2026, 10, 1), "H01", 1
    )
    ifrs_late = period(
        year_ifrs, cal_ifrs, date(2026, 10, 1), APR27, "H02", 2
    )
    ifrs_version = version(
        cal_ifrs, year_ifrs, (ifrs_early, ifrs_late),
        knowledge=KnowledgeInterval(JAN),
    )
    ifrs_fixture = BookCandidateFixture(
        book_ifrs,
        (assignment(book_ifrs, ifrs_version, knowledge=KnowledgeInterval(JAN)),),
        (ifrs_version,),
        (state(book_ifrs, ifrs_version, ifrs_late),),
        locks=(
            PeriodLockObservationCandidate(
                PeriodLockCandidateId.new(), book_ifrs, ifrs_version.id, ifrs_late.id,
                PeriodLockScopeCandidate.SOURCE_LOCK, "PAYROLL", True, 1,
                KnowledgeInterval(JAN), "rnd:observed-lock",
            ),
        ),
    )
    queries = (
        BookReplayQueryCandidate(book_pcg, DAY, FEB),
        BookReplayQueryCandidate(book_pcg, DAY, MAR),
        BookReplayQueryCandidate(book_ifrs, DAY, FEB),
        BookReplayQueryCandidate(book_ifrs, DAY, MAR),
    )
    return (pcg_fixture, ifrs_fixture), queries


def qualify(fixtures=None, queries=None, completeness=COMPLETE):
    standard_fixtures, standard_queries = scenario()
    return qualify_multibook_candidate_replay(
        fixtures=standard_fixtures if fixtures is None else fixtures,
        queries=standard_queries if queries is None else queries,
        completeness=completeness,
    )


def test_two_books_resolve_distinct_year_structures_and_lock_histories():
    fixtures, queries = scenario()
    report = qualify(fixtures, queries)
    report.verify_integrity()
    assert len(report.evidence) == 4
    by_book = {str(value.book_scope.book_id): value for value in fixtures}
    for result in report.evidence:
        assert result.calendar.assignment.book_scope.book_id in {
            item.book_scope.book_id for item in fixtures
        }
        assert by_book[str(result.query.book_scope.book_id)].book_scope == (
            result.query.book_scope
        )
        assert result.manifest()["posting_authorized"] is False
        assert result.simulated_wire.manifest()["eligible_for_posting"] is False
        with pytest.raises(UntrustedPeriodStatusForPosting):
            reject_simulated_status_for_posting(result.simulated_wire)


def test_same_pcg_business_date_is_different_original_vs_restated():
    fixtures, queries = scenario()
    report = qualify(fixtures, queries)
    pcg = fixtures[0].book_scope.book_id
    snapshots = sorted(
        [r for r in report.evidence if r.query.book_scope.book_id == pcg],
        key=lambda item: item.query.known_at,
    )
    assert snapshots[0].calendar.period.code.value == "P02"
    assert snapshots[1].calendar.period.code.value == "P01"
    assert snapshots[0].controls.state.status is PeriodStatusCandidate.OPEN
    assert snapshots[1].controls.state.status is PeriodStatusCandidate.CLOSED
    assert snapshots[0].calendar.calendar_version.id != (
        snapshots[1].calendar.calendar_version.id
    )
    assert snapshots[0].calendar.content_digest != snapshots[1].calendar.content_digest
    assert snapshots[0].simulated_wire.content_digest != (
        snapshots[1].simulated_wire.content_digest
    )


def test_second_book_unchanged_when_first_book_calendar_restated():
    fixtures, queries = scenario()
    report = qualify(fixtures, queries)
    ifrs_book = fixtures[1].book_scope.book_id
    rows = sorted(
        [item for item in report.evidence if item.query.book_scope.book_id == ifrs_book],
        key=lambda item: item.query.known_at,
    )
    assert len({r.calendar.calendar_version.id for r in rows}) == 1
    assert len({r.calendar.period.period_id for r in rows}) == 1
    assert all(r.calendar.period.code.value == "H02" for r in rows)
    assert all(r.controls.state.status is PeriodStatusCandidate.OPEN for r in rows)
    assert all(len(r.controls.observed_active_locks) == 1 for r in rows)
    assert all(
        r.simulated_wire.diagnostic_disposition.value
        == "LOCKS_OBSERVED_SCOPE_UNEVALUATED" for r in rows
    )


def test_replayed_same_inputs_same_canonical_report_digest():
    fixtures, queries = scenario()
    first = qualify(fixtures, queries)
    second = qualify(fixtures, queries)
    assert first.content_digest == second.content_digest
    assert first.manifest() == second.manifest()
    second.verify_integrity()


def test_input_query_order_and_fixture_order_do_not_change_manifest():
    fixtures, queries = scenario()
    baseline = qualify(fixtures, queries)
    reversed_report = qualify(tuple(reversed(fixtures)), tuple(reversed(queries)))
    assert baseline.manifest() == reversed_report.manifest()
    assert baseline.content_digest == reversed_report.content_digest


def test_aware_timezone_equivalent_query_preserves_checksum():
    fixtures, queries = scenario()
    offset = timezone(timedelta(hours=2))
    shifted = tuple(
        replace(value, known_at=value.known_at.astimezone(offset))
        for value in queries
    )
    assert qualify(fixtures, queries).content_digest == qualify(
        fixtures, shifted
    ).content_digest


def test_unverified_gates_permanently_unproven_for_both_books():
    fixtures, queries = scenario()
    report = qualify(fixtures, queries)
    assert report.unproven_gates == tuple(UnprovenL06ProductionGate)
    assert len(report.unproven_gates) == 6
    assert report.manifest()["live_e2e_qualified"] is False
    assert report.manifest()["migration_to_production_qualified"] is False
    assert report.manifest()["posting_authorized"] is False
    assert report.manifest()["published"] is False
    assert report.manifest()["disposition"] == "MULTIBOOK_CANDIDATE_REPLAY_ONLY_NO_G6_GO"


def test_entire_book_must_be_covered_no_selective_replay():
    fixtures, queries = scenario()
    with pytest.raises(InvalidMultiBookCandidate, match="Every supplied book"):
        qualify(fixtures, queries[:2])


def test_unassigned_book_fails_closed_even_when_other_book_resolves():
    fixtures, queries = scenario()
    missing = replace(fixtures[1], assignments=())
    with pytest.raises(BookCalendarCandidateMissing, match="No calendar assignment"):
        qualify((fixtures[0], missing), queries)


def test_historical_version_missing_never_falls_back_to_later_version():
    fixtures, queries = scenario()
    old_assignment, new_assignment = fixtures[0].assignments
    with pytest.raises(InvalidMultiBookCandidate, match="Missing exact"):
        revised = replace(
            fixtures[0], assignments=(old_assignment, new_assignment),
            versions=(fixtures[0].versions[1],),
        )
        qualify((revised, fixtures[1]), queries)


def test_missing_historical_assignment_is_not_backfilled():
    fixtures, queries = scenario()
    revised = replace(
        fixtures[0], assignments=(fixtures[0].assignments[1],),
    )
    with pytest.raises(BookCalendarCandidateMissing):
        qualify((revised, fixtures[1]), queries)


def test_same_book_duplicate_fixture_rejected():
    fixtures, queries = scenario()
    with pytest.raises(MultiBookCandidateAmbiguous, match="Duplicate book"):
        qualify((fixtures[0], fixtures[0]), queries)


def test_cross_tenant_entity_or_company_book_fixture_fails_closed():
    fixtures, queries = scenario()
    for scope in (
        replace(fixtures[1].book_scope, tenant_id="tenant-b"),
        replace(fixtures[1].book_scope, legal_entity_id=LegalEntityId.new()),
        replace(fixtures[1].book_scope, company_id=CompanyId.new()),
    ):
        with pytest.raises(InvalidMultiBookCandidate):
            altered = replace(
                fixtures[1], book_scope=scope,
                assignments=tuple(
                    replace(item, book_scope=scope) for item in fixtures[1].assignments
                ),
                states=tuple(
                    replace(item, book_scope=scope) for item in fixtures[1].states
                ),
                locks=tuple(
                    replace(item, book_scope=scope) for item in fixtures[1].locks
                ),
            )
            qualify((fixtures[0], altered), queries)


def test_foreign_book_query_refused_without_fallback_to_other_book():
    fixtures, queries = scenario()
    foreign = BookReplayQueryCandidate(
        replace(fixtures[1].book_scope, book_id=AccountingBookId.new()), DAY, FEB
    )
    with pytest.raises(InvalidMultiBookCandidate, match="unregistered"):
        qualify(fixtures, (queries[0], foreign, queries[3]))


def test_duplicate_same_book_date_known_at_query_is_ambiguous():
    fixtures, queries = scenario()
    with pytest.raises(MultiBookCandidateAmbiguous, match="Repeated book"):
        qualify(fixtures, (*queries, queries[0]))


def test_duplicate_query_utc_instant_different_offset_is_still_duplicate():
    fixtures, queries = scenario()
    repeated = replace(
        queries[0], known_at=FEB.astimezone(timezone(timedelta(hours=-4)))
    )
    with pytest.raises(MultiBookCandidateAmbiguous, match="Repeated book"):
        qualify(fixtures, (*queries, repeated))


def test_duplicate_assignment_identity_across_books_rejected():
    fixtures, queries = scenario()
    reused_id = fixtures[0].assignments[0].id
    copy = replace(
        fixtures[1],
        assignments=(replace(fixtures[1].assignments[0], id=reused_id),),
    )
    with pytest.raises(MultiBookCandidateAmbiguous, match="reused across books"):
        qualify((fixtures[0], copy), queries)


def test_foreign_assignment_even_if_nonapplicable_fails_closed():
    fixtures, _ = scenario()
    scope = replace(fixtures[0].book_scope, book_id=AccountingBookId.new())
    with pytest.raises(InvalidMultiBookCandidate, match="Foreign assignment"):
        replace(
            fixtures[0], assignments=(
                *fixtures[0].assignments,
                replace(fixtures[0].assignments[0], book_scope=scope),
            ),
        )


def test_foreign_lock_even_if_inactive_is_denied_early():
    fixtures, _ = scenario()
    lock = replace(
        fixtures[1].locks[0], active=False,
        book_scope=replace(fixtures[1].book_scope, tenant_id="tenant-b"),
    )
    with pytest.raises(InvalidMultiBookCandidate, match="Foreign control"):
        replace(fixtures[1], locks=(*fixtures[1].locks, lock))


def test_orphan_state_version_or_period_fails_catalog_validation():
    fixtures, _ = scenario()
    for patch in (
        {"period_id": AccountingPeriodId.new()},
        {"calendar_version_id": CalendarCandidateVersionId.new()},
    ):
        with pytest.raises(InvalidMultiBookCandidate, match="Orphan control"):
            replace(fixtures[0], states=(
                *fixtures[0].states, replace(fixtures[0].states[0], **patch),
            ))


def test_tampered_calendar_version_not_accepted_into_replay():
    fixtures, queries = scenario()
    report = qualify(fixtures, queries)
    version = fixtures[0].versions[0]
    object.__setattr__(version.calendar, "label", "mutated")
    with pytest.raises(Exception, match="changed"):
        report.verify_integrity()


def test_tampered_state_changes_replay_not_recoverable():
    fixtures, queries = scenario()
    report = qualify(fixtures, queries)
    observation = fixtures[0].states[0]
    object.__setattr__(observation, "source_ref", "mutated")
    with pytest.raises(MultiBookQualificationTampered):
        report.verify_integrity()


def test_fabricated_evidence_and_forged_gate_declaration_refused():
    fixtures, queries = scenario()
    report = qualify(fixtures, queries)
    first = report.evidence[0]
    forged = replace(first, simulated_wire=replace(
        first.simulated_wire, state_revision=999,
    ))
    with pytest.raises(MultiBookQualificationTampered):
        replace(report, evidence=(forged, *report.evidence[1:]))
    with pytest.raises(MultiBookQualificationTampered, match="falsely elevated"):
        replace(report, unproven_gates=())


def test_report_digest_and_evidence_mutation_rejected():
    fixtures, queries = scenario()
    report = qualify(fixtures, queries)
    object.__setattr__(report, "content_digest", "sha256:" + "0" * 64)
    with pytest.raises(MultiBookQualificationTampered, match="digest changed"):
        report.verify_integrity()


def test_query_validation_requires_typed_book_date_and_aware_cutoff():
    fixtures, queries = scenario()
    with pytest.raises(InvalidPeriodStatusSimulation):
        BookReplayQueryCandidate(
            replace(fixtures[0].book_scope, book_id=None), DAY, FEB
        )
    with pytest.raises(InvalidPeriodStatusSimulation):
        BookReplayQueryCandidate(queries[0].book_scope, datetime(2027, 2, 15), FEB)
    with pytest.raises(InvalidPeriodStatusSimulation):
        BookReplayQueryCandidate(queries[0].book_scope, DAY, datetime(2027, 2, 1))


def test_wrong_fixture_or_query_catalog_shape_rejected():
    fixtures, queries = scenario()
    with pytest.raises(InvalidMultiBookCandidate, match="scenario tuples"):
        qualify_multibook_candidate_replay(
            fixtures=list(fixtures), queries=queries, completeness=COMPLETE,
        )
    with pytest.raises(InvalidMultiBookCandidate, match="candidate fixture"):
        qualify((fixtures[0], "raw"), queries)
    with pytest.raises(InvalidMultiBookCandidate, match="Typed historical query"):
        qualify(fixtures, (queries[0], "raw", queries[2]))
    with pytest.raises(InvalidMultiBookCandidate, match="At least two"):
        qualify((fixtures[0],), queries)
    with pytest.raises(InvalidMultiBookCandidate, match="completeness"):
        qualify(fixtures, queries, completeness="DECLARED_COMPLETE_RND")


def test_shared_calendar_version_allowed_only_with_explicit_separate_bindings():
    fixtures, _ = scenario()
    pcg = fixtures[0]
    shared_version = pcg.versions[0]
    other_scope = fixtures[1].book_scope
    other = BookCandidateFixture(
        book_scope=other_scope,
        assignments=(assignment(
            other_scope, shared_version, knowledge=KnowledgeInterval(JAN, MAR)
        ),),
        versions=(shared_version,),
        states=(
            state(other_scope, shared_version, pcg.versions[0].periods[1]),
        ),
    )
    queries = (
        BookReplayQueryCandidate(pcg.book_scope, DAY, FEB),
        BookReplayQueryCandidate(other_scope, DAY, FEB),
    )
    report = qualify((pcg, other), queries)
    assert report.evidence[0].calendar.calendar_version.id == (
        report.evidence[1].calendar.calendar_version.id
    )
    assert len({str(item.query.book_scope.book_id) for item in report.evidence}) == 2


def test_open_no_locks_is_not_posting_eligible_even_when_all_fixture_data_present():
    fixtures, queries = scenario()
    report = qualify(fixtures, queries)
    for item in report.evidence:
        assert item.simulated_wire.authority == "UNTRUSTED_CANDIDATE_SIMULATION"
        with pytest.raises(UntrustedPeriodStatusForPosting):
            reject_simulated_status_for_posting(item.simulated_wire)


def test_unverified_completeness_forces_incomplete_diagnostics_but_not_g6_go():
    fixtures, queries = scenario()
    report = qualify(
        fixtures, queries, completeness=ObservationCompleteness.INCOMPLETE_RND,
    )
    for item in report.evidence:
        assert item.controls.disposition.value == "INCOMPLETE_CANDIDATE_EVIDENCE"
        assert item.manifest()["posting_authorized"] is False


def test_frozen_report_and_fixture_never_export_publishing_or_posting_methods():
    fixtures, queries = scenario()
    report = qualify(fixtures, queries)
    with pytest.raises(FrozenInstanceError):
        report.evidence = ()
    for value in (report, *fixtures, *report.evidence):
        for method in (
            "publish", "post", "commit", "can_post", "save", "close_period",
            "get_period_status",
        ):
            assert not hasattr(value, method)


def test_property_no_date_maps_to_two_ordinary_periods_in_twelve_month_fixture():
    fixtures, _ = scenario()
    v = fixtures[0].versions[0]
    for day_index in range(365):
        day = date(2027, 1, 1) + timedelta(days=day_index)
        selection = preview_ordinary_period_candidate(
            calendar=v.calendar, years=v.years, periods=v.periods,
            coverage_policy=v.coverage_policy, as_of=day,
        )
        assert selection.period_id in {period_obj.id for period_obj in v.periods}


def test_no_sql_ledger_runtime_or_real_iam_imported_into_qualification_module():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.application import (
        fiscal_multibook_qualification_rnd,
    )

    source = Path(fiscal_multibook_qualification_rnd.__file__).read_text("utf-8")
    parsed = ast.parse(source)
    imported = {
        name.name.split(".")[0]
        for node in ast.walk(parsed)
        if isinstance(node, ast.Import)
        for name in node.names
    }
    assert not imported & {"psycopg", "sqlalchemy", "django", "httpx", "requests"}
    for forbidden in (
        "organization_issuer_gateway", "ledger.post", "actual_commit",
        "get_period_status",
    ):
        assert forbidden not in source.lower()
