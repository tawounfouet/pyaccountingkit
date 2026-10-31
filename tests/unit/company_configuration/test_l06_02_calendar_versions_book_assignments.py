"""L06-02 adversarial tests: bitemporal book/calendar candidates, NOT C10."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from pyaccountingkit.company_configuration.application.fiscal_calendar_candidate_preview import (
    BookCalendarCandidatePreviewService,
    PreviewBookCalendarCandidate,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal
from pyaccountingkit.company_configuration.domain.fiscal_calendar import (
    AccountingPeriodDraft,
    BookCalendarAssignmentCandidate,
    BookCalendarCandidateAmbiguous,
    BookCalendarCandidateMissing,
    CalendarCandidateDigestMismatch,
    CalendarCode,
    CalendarCoveragePolicy,
    CalendarVersionCandidate,
    FiscalCalendarDraft,
    FiscalStructureConflict,
    FiscalYearCode,
    FiscalYearDraft,
    InvalidBookCalendarAssignment,
    InvalidCalendarCandidateVersion,
    PeriodCode,
    PeriodKind,
    SpecialPeriodRequiresExplicitTarget,
    preview_book_calendar_candidate,
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
)
from pyaccountingkit.company_configuration.infrastructure.fiscal_calendar_candidate_memory import (
    MemoryBookCalendarAssignments,
    MemoryCalendarCandidateVersions,
)

START = date(2027, 1, 1)
FEB_DATE = date(2027, 2, 1)
MAR_DATE = date(2027, 3, 1)
END = date(2028, 1, 1)
JAN = datetime(2027, 1, 1, tzinfo=UTC)
FEB = datetime(2027, 2, 1, tzinfo=UTC)
MAR = datetime(2027, 3, 1, tzinfo=UTC)
DAY = date(2027, 2, 15)
FULL = EffectiveInterval(START, END)
CONTIGUOUS = CalendarCoveragePolicy.REQUIRE_CONTIGUOUS


def fixture():
    c = FiscalCalendarDraft(
        FiscalCalendarId.new(),
        ConfigurationScope("tenant-a", CompanyId.new(), LegalEntityId.new()),
        CalendarCode("FY_CANDIDATE"),
        "R&D fiscal calendar", FULL, "rnd:jurisdiction-claim", "rnd:calendar",
    )
    y = FiscalYearDraft(
        FiscalYearId.new(), c.id, c.scope, FiscalYearCode("FY-2027"),
        FULL, "rnd:year",
    )
    p1 = AccountingPeriodDraft(
        AccountingPeriodId.new(), y.id, c.id, c.scope, PeriodCode("P01"),
        PeriodKind.ORDINARY, EffectiveInterval(START, FEB_DATE),
        "rnd:period-one", 1,
    )
    p2 = AccountingPeriodDraft(
        AccountingPeriodId.new(), y.id, c.id, c.scope, PeriodCode("P02"),
        PeriodKind.ORDINARY, EffectiveInterval(FEB_DATE, END),
        "rnd:period-two", 2,
    )
    return c, y, p1, p2


def version(
    c, y, p1, p2, *, identity=None, knowledge=None, periods=None,
    effective=None, coverage=CONTIGUOUS,
):
    return CalendarVersionCandidate(
        identity or CalendarCandidateVersionId.new(),
        c, (y,), periods if periods is not None else (p1, p2),
        coverage, effective or FULL, knowledge or KnowledgeInterval(JAN),
        "rnd:version",
    )


def binding(c, v, *, scope=None, identity=None, effective=None, knowledge=None):
    return BookCalendarAssignmentCandidate(
        identity or BookCalendarAssignmentCandidateId.new(),
        scope or replace(c.scope, book_id=AccountingBookId.new()),
        c.id, v.id, effective or FULL,
        knowledge or KnowledgeInterval(JAN), "rnd:assignment",
    )


def run(b, versions, assignments=None, *, day=DAY, known_at=FEB, adjustment_id=None):
    return preview_book_calendar_candidate(
        book_scope=b.book_scope, as_of=day, known_at=known_at,
        assignments=tuple(assignments if assignments is not None else (b,)),
        calendar_versions=tuple(versions), adjustment_period_id=adjustment_id,
    )


def test_version_full_content_digest_includes_structure_and_literal_codes():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    v.verify_integrity()
    assert v.content_digest.startswith("sha256:")
    assert len(v.content_digest) == 71
    assert "P01" in str(v.canonical_manifest())
    assert v.canonical_manifest()["status"] == "UNPUBLISHED_CALENDAR_RND_CANDIDATE"
    assert not hasattr(v, "publish")
    assert not hasattr(v, "post")


def test_version_digest_independent_of_year_period_input_order():
    c, y, p1, p2 = fixture()
    vid = CalendarCandidateVersionId.new()
    a = version(c, y, p1, p2, identity=vid)
    z = version(c, y, p1, p2, periods=(p2, p1), identity=vid)
    assert a.canonical_manifest() == z.canonical_manifest()
    assert a.content_digest == z.content_digest


def test_exact_book_candidate_receipt_is_structural_and_pinned():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v)
    receipt = run(b, (v,))
    receipt.verify_integrity()
    assert receipt.calendar_version.id == v.id
    assert receipt.calendar_version.content_digest == v.content_digest
    assert receipt.period.period_id == p2.id
    assert receipt.assignment.id == b.id
    assert receipt.canonical_manifest()["status"] == "UNPUBLISHED_STRUCTURAL_PERIOD_PREVIEW"
    assert receipt.canonical_manifest()["book_scope"]["book"] == str(b.book_scope.book_id)
    for name in ("post", "publish", "close", "open", "can_post", "get_period_status"):
        assert not hasattr(receipt, name)


def test_bitemporal_known_then_restated_february_periods_are_distinct():
    c, y, p1, p2 = fixture()
    first = version(c, y, p1, p2, knowledge=KnowledgeInterval(JAN, MAR))
    new_p1 = replace(p1, effective=EffectiveInterval(START, MAR_DATE))
    new_p2 = replace(p2, effective=EffectiveInterval(MAR_DATE, END))
    amended = version(
        c, y, new_p1, new_p2, knowledge=KnowledgeInterval(MAR)
    )
    scope = replace(c.scope, book_id=AccountingBookId.new())
    old_binding = binding(c, first, scope=scope, knowledge=KnowledgeInterval(JAN, MAR))
    new_binding = binding(c, amended, scope=scope, knowledge=KnowledgeInterval(MAR))
    catalog = (old_binding, new_binding)
    original = run(old_binding, (first, amended), catalog, known_at=FEB)
    restated = run(old_binding, (first, amended), catalog, known_at=MAR)
    assert original.period.period_id == p2.id
    assert restated.period.period_id == p1.id
    assert original.calendar_version.id == first.id
    assert restated.calendar_version.id == amended.id
    assert original.content_digest != restated.content_digest
    original.verify_integrity()
    restated.verify_integrity()


def test_second_book_can_bind_different_version_without_coupling():
    c, y, p1, p2 = fixture()
    v1 = version(c, y, p1, p2)
    v2 = version(c, y, p1, p2, identity=CalendarCandidateVersionId.new())
    b1 = binding(c, v1)
    b2 = binding(c, v2)
    r1 = run(b1, (v1, v2), (b1,))
    r2 = run(b2, (v1, v2), (b2,))
    assert r1.calendar_version.id != r2.calendar_version.id
    assert r1.period.period_id == r2.period.period_id


def test_missing_book_assignment_is_explicit_fail_closed():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v)
    with pytest.raises(BookCalendarCandidateMissing, match="No calendar assignment"):
        run(b, (v,), ())


def test_future_recorded_assignment_never_backfills_old_known_at():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v, knowledge=KnowledgeInterval(MAR))
    with pytest.raises(BookCalendarCandidateMissing):
        run(b, (v,), known_at=FEB)


def test_future_recorded_calendar_version_cannot_be_replayed_earlier():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2, knowledge=KnowledgeInterval(MAR))
    b = binding(c, v)
    with pytest.raises(InvalidBookCalendarAssignment, match="time mismatch"):
        run(b, (v,), known_at=FEB)


def test_missing_exact_calendar_version_never_falls_back_to_latest():
    c, y, p1, p2 = fixture()
    target = version(c, y, p1, p2)
    latest = version(c, y, p1, p2)
    b = binding(c, target)
    with pytest.raises(BookCalendarCandidateMissing, match="Exact"):
        run(b, (latest,))


def test_ambiguous_overlapping_book_assignments_rejected():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b1 = binding(c, v)
    b2 = binding(c, v, scope=b1.book_scope)
    with pytest.raises(BookCalendarCandidateAmbiguous, match="Concurrent"):
        run(b1, (v,), (b1, b2))


def test_adjacent_half_open_effective_assignments_are_unambiguous():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    bs = replace(c.scope, book_id=AccountingBookId.new())
    earlier = binding(
        c, v, scope=bs, effective=EffectiveInterval(START, FEB_DATE),
    )
    later = binding(c, v, scope=bs, effective=EffectiveInterval(FEB_DATE, END))
    assert run(earlier, (v,), (earlier, later), day=START).assignment.id == earlier.id
    assert run(earlier, (v,), (earlier, later), day=FEB_DATE).assignment.id == later.id


def test_duplicate_assignment_identity_even_if_not_overlapping_is_rejected():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v, effective=EffectiveInterval(START, FEB_DATE))
    another = replace(b, effective=EffectiveInterval(FEB_DATE, END))
    with pytest.raises(BookCalendarCandidateAmbiguous, match="Duplicate assignment"):
        run(b, (v,), (b, another))


def test_duplicate_version_identity_in_catalog_is_rejected():
    c, y, p1, p2 = fixture()
    vid = CalendarCandidateVersionId.new()
    old = version(c, y, p1, p2, identity=vid)
    revised = version(c, y, p1, p2, identity=vid, knowledge=KnowledgeInterval(MAR))
    b = binding(c, old)
    with pytest.raises(BookCalendarCandidateAmbiguous, match="Duplicate candidate"):
        run(b, (old, revised))


def test_leaked_foreign_book_company_entity_tenant_scope_refused():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v)
    for altered in (
        replace(b.book_scope, tenant_id="tenant-b"),
        replace(b.book_scope, company_id=CompanyId.new()),
        replace(b.book_scope, legal_entity_id=LegalEntityId.new()),
        replace(b.book_scope, book_id=AccountingBookId.new()),
    ):
        with pytest.raises(InvalidBookCalendarAssignment, match="Foreign book scope"):
            run(b, (v,), (replace(b, book_scope=altered),))


def test_leaked_foreign_calendar_scope_fails_without_silent_filtering():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v)
    foreign_calendar, fy, fp1, fp2 = fixture()
    foreign = version(foreign_calendar, fy, fp1, fp2)
    with pytest.raises(InvalidCalendarCandidateVersion, match="Foreign entity"):
        run(b, (v, foreign))


def test_mismatched_calendar_identity_in_assignment_rejected():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v)
    with pytest.raises(InvalidBookCalendarAssignment, match="identity"):
        run(b, (v,), (replace(b, calendar_id=FiscalCalendarId.new()),))


def test_assignment_must_fit_exact_version_effective_window():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v, effective=EffectiveInterval(date(2026, 1, 1), END))
    with pytest.raises(InvalidBookCalendarAssignment, match="time mismatch"):
        run(b, (v,), day=DAY)


def test_calendar_version_cannot_escape_calendar_or_leave_year_out():
    c, y, p1, p2 = fixture()
    with pytest.raises(InvalidCalendarCandidateVersion, match="exceeds"):
        version(c, y, p1, p2, effective=EffectiveInterval(date(2026, 1, 1), END))
    with pytest.raises(InvalidCalendarCandidateVersion, match="Fiscal year outside"):
        version(c, y, p1, p2, effective=EffectiveInterval(FEB_DATE, END))


def test_version_construction_revalidates_every_period_including_future():
    c, y, p1, p2 = fixture()
    invalid_p2 = replace(p2, effective=EffectiveInterval(START, END))
    with pytest.raises(FiscalStructureConflict, match="Overlapping ordinary"):
        version(c, y, p1, invalid_p2)


def test_versions_can_model_non_january_fiscal_years_and_gaps_with_policy():
    c, y, p1, p2 = fixture()
    c = replace(c, effective=EffectiveInterval(date(2026, 4, 1), END))
    y = replace(y, effective=EffectiveInterval(date(2026, 4, 1), END))
    p1 = replace(p1, effective=EffectiveInterval(date(2026, 4, 1), FEB_DATE))
    v = version(
        c, y, p1, p2,
        effective=EffectiveInterval(date(2026, 4, 1), END),
    )
    assert v.calendar.effective.start == date(2026, 4, 1)
    with_gap = replace(p2, effective=EffectiveInterval(MAR_DATE, END))
    v_gap = version(
        c, y, p1, with_gap, coverage=CalendarCoveragePolicy.ALLOW_GAPS,
        effective=EffectiveInterval(date(2026, 4, 1), END),
    )
    v_gap.verify_integrity()


def test_special_period_is_selected_only_by_explicit_exact_id():
    c, y, p1, p2 = fixture()
    adj = AccountingPeriodDraft(
        AccountingPeriodId.new(), y.id, c.id, c.scope, PeriodCode("ADJ"),
        PeriodKind.ADJUSTMENT, EffectiveInterval(FEB_DATE, MAR_DATE),
        "rnd:adjustment", None, p2.id,
    )
    v = version(c, y, p1, p2, periods=(p1, p2, adj))
    b = binding(c, v)
    ordinary = run(b, (v,))
    selected = run(b, (v,), adjustment_id=adj.id)
    assert ordinary.period.period_id == p2.id
    assert selected.period.period_id == adj.id
    assert selected.period.adjustment_target_id == p2.id
    with pytest.raises(SpecialPeriodRequiresExplicitTarget):
        run(b, (v,), adjustment_id=AccountingPeriodId.new())


def test_version_mutated_nested_period_is_detected_by_digest():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    object.__setattr__(p1, "source_ref", "tampered")
    with pytest.raises(CalendarCandidateDigestMismatch):
        v.verify_integrity()


def test_receipt_detects_assignment_tampering_and_fabricated_period():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v)
    receipt = run(b, (v,))
    object.__setattr__(b, "source_ref", "tampered")
    with pytest.raises(CalendarCandidateDigestMismatch):
        receipt.verify_integrity()
    fresh_b = binding(c, v)
    with pytest.raises(InvalidBookCalendarAssignment, match="Fabricated"):
        replace(run(fresh_b, (v,)), period=replace(receipt.period, period_id=p1.id))


def test_version_and_assignment_frozen_immutable():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v)
    with pytest.raises(FrozenInstanceError):
        v.source_ref = "x"
    with pytest.raises(FrozenInstanceError):
        b.source_ref = "x"


def test_invalid_date_or_naive_known_at_rejected():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v)
    with pytest.raises(InvalidBookCalendarAssignment, match="business date"):
        run(b, (v,), day=datetime(2027, 2, 15))
    with pytest.raises(InvalidBookCalendarAssignment, match="Timezone-aware"):
        run(b, (v,), known_at=datetime(2027, 2, 15))


def test_normalize_aware_known_at_to_utc_in_digest():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v)
    utc = run(b, (v,), known_at=FEB)
    local = run(
        b, (v,), known_at=FEB.astimezone(timezone(timedelta(hours=2)))
    )
    assert utc.content_digest == local.content_digest


def test_duplicate_or_untyped_catalogs_denied():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v)
    with pytest.raises(InvalidBookCalendarAssignment, match="tuples"):
        preview_book_calendar_candidate(
            book_scope=b.book_scope, as_of=DAY, known_at=FEB,
            assignments=[b], calendar_versions=(v,),
        )
    with pytest.raises(InvalidBookCalendarAssignment, match="Non-assignment"):
        run(b, (v,), ("raw",))
    with pytest.raises(InvalidCalendarCandidateVersion, match="Non-calendar"):
        run(b, ("raw",))


def test_typed_inputs_required_at_model_construction():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v)
    with pytest.raises(InvalidCalendarCandidateVersion, match="Typed"):
        replace(v, id=FiscalCalendarId.new())
    with pytest.raises(InvalidCalendarCandidateVersion, match="knowledge"):
        replace(v, knowledge="not-timestamp")
    with pytest.raises(InvalidBookCalendarAssignment, match="typed calendar version"):
        replace(b, calendar_version_id=FiscalCalendarId.new())
    with pytest.raises(InvalidBookCalendarAssignment, match="book scope"):
        replace(b, book_scope=c.scope)


def test_read_service_denies_missing_test_grant_and_cross_tenant():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v)

    class FakeGrants:
        allow = False

        def require(self, *, principal, action, scope):
            assert action == "calendar.assignment.candidate.preview"
            if not self.allow:
                raise PermissionError("Candidate preview denied")

    grant = FakeGrants()
    svc = BookCalendarCandidatePreviewService(
        versions=MemoryCalendarCandidateVersions((v,)),
        assignments=MemoryBookCalendarAssignments((b,)),
        authorization=grant,
    )
    q = PreviewBookCalendarCandidate(b.book_scope, DAY, FEB)
    actor = TrustedPrincipal("rnd-actor", "tenant-a")
    with pytest.raises(PermissionError, match="denied"):
        svc.preview(q, principal=actor)
    grant.allow = True
    assert svc.preview(q, principal=actor).period.period_id == p2.id
    with pytest.raises(PermissionError, match="Cross-tenant"):
        svc.preview(q, principal=TrustedPrincipal("rnd-actor", "tenant-b"))
    with pytest.raises(PermissionError, match="Unverified"):
        svc.preview(q, principal="caller-supplied-user")


def test_malicious_reader_leaking_foreign_book_is_denied_by_domain():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v)

    class Allow:
        def require(self, *, principal, action, scope):
            return None

    class MaliciousAssignments:
        def list_for_book(self, scope):
            return (replace(b, book_scope=replace(scope, tenant_id="tenant-b")),)

    svc = BookCalendarCandidatePreviewService(
        versions=MemoryCalendarCandidateVersions((v,)),
        assignments=MaliciousAssignments(), authorization=Allow(),
    )
    with pytest.raises(InvalidBookCalendarAssignment, match="Foreign book scope"):
        svc.preview(
            PreviewBookCalendarCandidate(b.book_scope, DAY, FEB),
            principal=TrustedPrincipal("rnd-actor", "tenant-a"),
        )


def test_memory_readers_are_scope_precise_and_have_no_mutators():
    c, y, p1, p2 = fixture()
    v = version(c, y, p1, p2)
    b = binding(c, v)
    ver = MemoryCalendarCandidateVersions((v,))
    ass = MemoryBookCalendarAssignments((b,))
    assert ver.list_for_book(b.book_scope) == (v,)
    assert ass.list_for_book(b.book_scope) == (b,)
    assert ass.list_for_book(
        replace(b.book_scope, book_id=AccountingBookId.new())
    ) == ()
    for obj in (ver, ass):
        assert not hasattr(obj, "save")
        assert not hasattr(obj, "publish")


def test_new_l06_candidate_modules_have_no_sql_live_book_or_posting_api():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.application import (
        fiscal_calendar_candidate_preview,
    )
    from pyaccountingkit.company_configuration.domain.fiscal_calendar import (
        versions_assignments,
    )
    from pyaccountingkit.company_configuration.infrastructure import (
        fiscal_calendar_candidate_memory,
    )

    for module in (
        versions_assignments, fiscal_calendar_candidate_preview,
        fiscal_calendar_candidate_memory,
    ):
        text = Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(text)
        imports = {
            x.name.split(".")[0]
            for node in ast.walk(tree) if isinstance(node, ast.Import)
            for x in node.names
        }
        assert not imports & {"psycopg", "sqlalchemy", "django", "requests", "httpx"}
        for forbidden in ("organization_issuer_gateway", "accounting_books"):
            assert forbidden not in text
        for action in ("publish", "post", "close", "commit", "reopen", "allocate"):
            assert not hasattr(module, action)
