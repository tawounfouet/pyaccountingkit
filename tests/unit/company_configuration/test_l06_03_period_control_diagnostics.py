"""L06-03 pure candidate period controls, never live C10 posting authority."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from pyaccountingkit.company_configuration.application.fiscal_calendar_candidate_preview import (
    BookCalendarCandidatePreviewService,
    PreviewBookCalendarCandidate,
)
from pyaccountingkit.company_configuration.application.fiscal_period_control_diagnostics import (
    PeriodControlCandidateDiagnosticService,
    PreviewPeriodControlsCandidate,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal
from pyaccountingkit.company_configuration.domain.fiscal_calendar import (
    AccountingPeriodDraft,
    BookCalendarAssignmentCandidate,
    CalendarCode,
    CalendarCoveragePolicy,
    CalendarVersionCandidate,
    FiscalCalendarDraft,
    FiscalYearCode,
    FiscalYearDraft,
    InvalidPeriodControlCandidate,
    ObservationCompleteness,
    PeriodCode,
    PeriodControlCandidateAmbiguous,
    PeriodControlCandidateDigestMismatch,
    PeriodControlCandidateMissing,
    PeriodControlDiagnosticDisposition,
    PeriodKind,
    PeriodLockObservationCandidate,
    PeriodLockScopeCandidate,
    PeriodStateObservationCandidate,
    PeriodStatusCandidate,
    PeriodTransitionDeclarationCandidate,
    preview_book_calendar_candidate,
    preview_period_controls_candidate,
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
    PeriodTransitionCandidateId,
)
from pyaccountingkit.company_configuration.infrastructure.fiscal_calendar_candidate_memory import (
    MemoryBookCalendarAssignments,
    MemoryCalendarCandidateVersions,
)
from pyaccountingkit.company_configuration.infrastructure.fiscal_period_control_memory import (
    MemoryPeriodControlCandidates,
)

JAN = datetime(2027, 1, 1, tzinfo=UTC)
FEB = datetime(2027, 2, 1, tzinfo=UTC)
MAR = datetime(2027, 3, 1, tzinfo=UTC)
APR = datetime(2027, 4, 1, tzinfo=UTC)
AS_OF = date(2027, 2, 15)
POLICY = CalendarCoveragePolicy.REQUIRE_CONTIGUOUS
COMPLETE = ObservationCompleteness.DECLARED_COMPLETE_RND


def fixture(*, known_at=FEB):
    scope = ConfigurationScope("tenant-a", CompanyId.new(), LegalEntityId.new())
    calendar = FiscalCalendarDraft(
        FiscalCalendarId.new(), scope, CalendarCode("FISCAL_RND"),
        "Fiscal calendar R&D", EffectiveInterval(date(2027, 1, 1), date(2028, 1, 1)),
        "rnd:jurisdiction", "rnd:calendar",
    )
    year = FiscalYearDraft(
        FiscalYearId.new(), calendar.id, scope, FiscalYearCode("FY2027"),
        calendar.effective, "rnd:year",
    )
    first = AccountingPeriodDraft(
        AccountingPeriodId.new(), year.id, calendar.id, scope,
        PeriodCode("P01"), PeriodKind.ORDINARY,
        EffectiveInterval(date(2027, 1, 1), date(2027, 2, 1)),
        "rnd:first", 1,
    )
    second = AccountingPeriodDraft(
        AccountingPeriodId.new(), year.id, calendar.id, scope,
        PeriodCode("P02"), PeriodKind.ORDINARY,
        EffectiveInterval(date(2027, 2, 1), date(2028, 1, 1)),
        "rnd:second", 2,
    )
    version = CalendarVersionCandidate(
        CalendarCandidateVersionId.new(), calendar, (year,),
        (first, second), POLICY, calendar.effective, KnowledgeInterval(JAN),
        "rnd:version",
    )
    assignment = BookCalendarAssignmentCandidate(
        BookCalendarAssignmentCandidateId.new(),
        replace(scope, book_id=AccountingBookId.new()), calendar.id,
        version.id, calendar.effective, KnowledgeInterval(JAN), "rnd:binding",
    )
    receipt = preview_book_calendar_candidate(
        book_scope=assignment.book_scope,
        as_of=AS_OF, known_at=known_at,
        assignments=(assignment,), calendar_versions=(version,),
    )
    return receipt, version, assignment


def state(receipt, status=PeriodStatusCandidate.OPEN, *, start=JAN, end=None,
          revision=1, identity=None):
    return PeriodStateObservationCandidate(
        identity or PeriodStateCandidateId.new(), receipt.assignment.book_scope,
        receipt.calendar_version.id, receipt.period.period_id,
        status, revision, KnowledgeInterval(start, end), "rnd:state",
    )


def lock(receipt, *, identity=None, lock_scope=PeriodLockScopeCandidate.GLOBAL_BOOK_LOCK,
         target=None, active=True, revision=1, start=JAN, end=None):
    return PeriodLockObservationCandidate(
        identity or PeriodLockCandidateId.new(), receipt.assignment.book_scope,
        receipt.calendar_version.id, receipt.period.period_id,
        lock_scope, target, active, revision, KnowledgeInterval(start, end),
        "rnd:lock",
    )


def transition(receipt, *, declared_at=FEB, old=PeriodStatusCandidate.OPEN,
               new=PeriodStatusCandidate.CLOSED):
    return PeriodTransitionDeclarationCandidate(
        PeriodTransitionCandidateId.new(), receipt.assignment.book_scope,
        receipt.calendar_version.id, receipt.period.period_id,
        old, new, 1, 2, declared_at, "actor:unverified",
        "Proposed period transition", "rnd:transition",
    )


def diagnostic(receipt, states, *, locks=(), transitions=(), completeness=COMPLETE):
    return preview_period_controls_candidate(
        book_receipt=receipt, states=tuple(states), locks=tuple(locks),
        transitions=tuple(transitions), completeness=completeness,
    )


def test_open_without_observed_lock_is_still_explicitly_unverified():
    receipt, _, _ = fixture()
    output = diagnostic(receipt, (state(receipt),))
    assert output.disposition is (
        PeriodControlDiagnosticDisposition.NO_OBSERVED_LOCKS_UNVERIFIED
    )
    assert output.state.status is PeriodStatusCandidate.OPEN
    assert output.canonical_manifest()["status"] == (
        "UNPUBLISHED_NONAUTHORITATIVE_PERIOD_DIAGNOSTIC"
    )
    assert output.content_digest.startswith("sha256:")
    assert len(output.content_digest) == 71
    output.verify_integrity()
    for name in ("post", "can_post", "potentially_postable", "commit", "publish"):
        assert not hasattr(output, name)


@pytest.mark.parametrize(
    "status", [
        PeriodStatusCandidate.DRAFT, PeriodStatusCandidate.FUTURE,
        PeriodStatusCandidate.SOFT_CLOSED, PeriodStatusCandidate.CLOSED,
        PeriodStatusCandidate.ARCHIVED,
    ],
)
def test_every_non_open_status_reports_non_open_diagnostic_only(status):
    receipt, _, _ = fixture()
    result = diagnostic(receipt, (state(receipt, status),))
    assert result.disposition is (
        PeriodControlDiagnosticDisposition.NON_OPEN_CANDIDATE_STATUS
    )


def test_locked_is_orthogonal_and_not_a_period_status_enum_member():
    assert "LOCKED" not in {s.value for s in PeriodStatusCandidate}
    receipt, _, _ = fixture()
    item = lock(receipt)
    result = diagnostic(receipt, (state(receipt),), locks=(item,))
    assert result.state.status is PeriodStatusCandidate.OPEN
    assert result.disposition is (
        PeriodControlDiagnosticDisposition.LOCKS_OBSERVED_SCOPE_UNEVALUATED
    )
    assert result.observed_active_locks == (item,)


@pytest.mark.parametrize("kind,target", [
    (PeriodLockScopeCandidate.GLOBAL_BOOK_LOCK, None),
    (PeriodLockScopeCandidate.JOURNAL_LOCK, "SALES"),
    (PeriodLockScopeCandidate.SOURCE_LOCK, "INVOICES"),
    (PeriodLockScopeCandidate.OPERATION_LOCK, "ADJUSTMENT"),
])
def test_four_canonical_lock_scope_categories_can_be_observed(kind, target):
    receipt, _, _ = fixture()
    item = lock(receipt, lock_scope=kind, target=target)
    result = diagnostic(receipt, (state(receipt),), locks=(item,))
    assert result.observed_active_locks[0].lock_scope is kind
    assert result.disposition is (
        PeriodControlDiagnosticDisposition.LOCKS_OBSERVED_SCOPE_UNEVALUATED
    )


@pytest.mark.parametrize("target", ["", "lower", "A B", " ÉTÉ ", "A" * 65, True])
def test_targeted_lock_requires_canonical_target_code(target):
    receipt, _, _ = fixture()
    with pytest.raises(InvalidPeriodControlCandidate, match="canonical target"):
        lock(receipt, lock_scope=PeriodLockScopeCandidate.JOURNAL_LOCK, target=target)


def test_global_lock_cannot_have_hidden_target():
    receipt, _, _ = fixture()
    with pytest.raises(InvalidPeriodControlCandidate, match="no target"):
        lock(receipt, target="SALES")


def test_non_boolean_lock_and_invalid_revisions_are_rejected():
    receipt, _, _ = fixture()
    item = lock(receipt)
    for value in (1, 0, None, "true"):
        with pytest.raises(InvalidPeriodControlCandidate, match="boolean"):
            replace(item, active=value)
    for rev in (True, 0, -1, "1", 1.1):
        with pytest.raises(InvalidPeriodControlCandidate, match="Positive lock"):
            replace(item, revision=rev)


def test_state_requires_typed_positive_revision_and_enum():
    receipt, _, _ = fixture()
    item = state(receipt)
    for revision in (0, -1, True, 1.1, "1"):
        with pytest.raises(InvalidPeriodControlCandidate, match="Positive state"):
            replace(item, state_revision=revision)
    with pytest.raises(InvalidPeriodControlCandidate, match="Typed period"):
        replace(item, status="OPEN")


def test_bitemporal_original_known_and_restated_status_preserved():
    old_receipt, _, _ = fixture(known_at=FEB)
    new_receipt = replace(old_receipt, known_at=MAR)
    first = state(old_receipt, PeriodStatusCandidate.OPEN, start=JAN, end=MAR)
    second = state(old_receipt, PeriodStatusCandidate.CLOSED, start=MAR, revision=2)
    old = diagnostic(old_receipt, (first, second))
    later = diagnostic(new_receipt, (first, second))
    assert old.state.status is PeriodStatusCandidate.OPEN
    assert later.state.status is PeriodStatusCandidate.CLOSED
    assert old.content_digest != later.content_digest
    old.verify_integrity()
    later.verify_integrity()


def test_lock_activated_then_released_at_known_at_boundary():
    initial, _, _ = fixture(known_at=FEB)
    after = replace(initial, known_at=MAR)
    identifier = PeriodLockCandidateId.new()
    activated = lock(initial, identity=identifier, start=JAN, end=MAR)
    released = lock(
        initial, identity=identifier, start=MAR, revision=2, active=False
    )
    s = state(initial)
    old = diagnostic(initial, (s,), locks=(activated, released))
    later = diagnostic(after, (s,), locks=(activated, released))
    assert old.observed_active_locks == (activated,)
    assert later.observed_active_locks == ()
    assert later.disposition is (
        PeriodControlDiagnosticDisposition.NO_OBSERVED_LOCKS_UNVERIFIED
    )


def test_incomplete_observation_catalog_never_claims_readiness():
    receipt, _, _ = fixture()
    observed = diagnostic(
        receipt, (state(receipt),),
        completeness=ObservationCompleteness.INCOMPLETE_RND,
    )
    assert observed.disposition is (
        PeriodControlDiagnosticDisposition.INCOMPLETE_CANDIDATE_EVIDENCE
    )


def test_missing_historical_state_fails_closed_no_latest_fallback():
    receipt, _, _ = fixture(known_at=FEB)
    future = state(receipt, start=MAR)
    with pytest.raises(PeriodControlCandidateMissing, match="No state"):
        diagnostic(receipt, (future,))


def test_concurrent_state_observations_are_rejected_even_same_status():
    receipt, _, _ = fixture()
    a, b = state(receipt), state(receipt, revision=2)
    with pytest.raises(PeriodControlCandidateAmbiguous, match="Concurrent state"):
        diagnostic(receipt, (a, b))


def test_duplicate_state_id_or_revision_rejected_even_disjoint_in_time():
    receipt, _, _ = fixture()
    a = state(receipt, end=MAR)
    with pytest.raises(PeriodControlCandidateAmbiguous, match="Duplicate state"):
        diagnostic(receipt, (a, replace(a, knowledge=KnowledgeInterval(MAR))),)
    b = state(receipt, start=MAR, revision=1)
    with pytest.raises(PeriodControlCandidateAmbiguous, match="Duplicate state"):
        diagnostic(receipt, (a, b))


def test_state_revisions_cannot_regress_when_known_at_advances():
    receipt, _, _ = fixture()
    a = state(receipt, end=MAR, revision=2)
    b = state(receipt, start=MAR, revision=1)
    with pytest.raises(InvalidPeriodControlCandidate, match="regress"):
        diagnostic(receipt, (a, b))


def test_overlapping_lock_revisions_and_duplicate_revision_refused():
    receipt, _, _ = fixture()
    identifier = PeriodLockCandidateId.new()
    a = lock(receipt, identity=identifier, end=MAR)
    b = lock(receipt, identity=identifier, start=FEB, revision=2)
    with pytest.raises(PeriodControlCandidateAmbiguous, match="Overlapping lock"):
        diagnostic(receipt, (state(receipt),), locks=(a, b))
    b = lock(receipt, identity=identifier, start=MAR, revision=1)
    with pytest.raises(PeriodControlCandidateAmbiguous, match="Duplicate lock"):
        diagnostic(receipt, (state(receipt),), locks=(a, b))


def test_lock_target_cannot_mutate_across_revisions():
    receipt, _, _ = fixture()
    identifier = PeriodLockCandidateId.new()
    a = lock(
        receipt, identity=identifier, lock_scope=PeriodLockScopeCandidate.JOURNAL_LOCK,
        target="SALES", end=MAR,
    )
    b = lock(
        receipt, identity=identifier, lock_scope=PeriodLockScopeCandidate.JOURNAL_LOCK,
        target="PURCHASE", start=MAR, revision=2, active=False,
    )
    with pytest.raises(InvalidPeriodControlCandidate, match="changed its target"):
        diagnostic(receipt, (state(receipt),), locks=(a, b))


def test_lock_revisions_cannot_regress_across_disjoint_history():
    receipt, _, _ = fixture()
    identifier = PeriodLockCandidateId.new()
    a = lock(receipt, identity=identifier, revision=3, end=MAR)
    b = lock(receipt, identity=identifier, revision=2, start=MAR, active=False)
    with pytest.raises(InvalidPeriodControlCandidate, match="regress"):
        diagnostic(receipt, (state(receipt),), locks=(a, b))


def test_transition_declaration_is_visible_only_at_or_after_declared_at():
    before, _, _ = fixture(known_at=FEB)
    after = replace(before, known_at=MAR)
    item = transition(before, declared_at=MAR)
    a = diagnostic(before, (state(before),), transitions=(item,))
    b = diagnostic(after, (state(before),), transitions=(item,))
    assert a.visible_declarations == ()
    assert b.visible_declarations == (item,)
    assert b.state.status is PeriodStatusCandidate.OPEN
    assert not hasattr(item, "apply")


def test_transition_declaration_rejects_identity_reason_and_version_conflicts():
    receipt, _, _ = fixture()
    item = transition(receipt)
    for patch in (
        {"expected_revision": 3},
        {"proposed_revision": 1},
        {"proposed_revision": True},
        {"reason": " "},
        {"actor_ref": ""},
        {"declared_at": datetime(2027, 2, 1)},
        {"from_status": PeriodStatusCandidate.CLOSED},
    ):
        with pytest.raises(InvalidPeriodControlCandidate):
            replace(item, **patch)


def test_duplicate_transition_id_is_ambiguous_not_replayed_twice():
    receipt, _, _ = fixture()
    item = transition(receipt)
    with pytest.raises(PeriodControlCandidateAmbiguous, match="Duplicate transition"):
        diagnostic(receipt, (state(receipt),), transitions=(item, item))


def test_foreign_scope_book_period_or_version_rejected_even_if_inactive():
    receipt, _, _ = fixture()
    st = state(receipt)
    for changed in (
        {"book_scope": replace(st.book_scope, tenant_id="tenant-b")},
        {"book_scope": replace(st.book_scope, book_id=AccountingBookId.new())},
        {"calendar_version_id": CalendarCandidateVersionId.new()},
        {"period_id": AccountingPeriodId.new()},
    ):
        foreign = replace(st, **changed)
        with pytest.raises(InvalidPeriodControlCandidate, match="Foreign"):
            diagnostic(receipt, (st, foreign))


def test_foreign_lock_or_transition_entry_rejected():
    receipt, _, _ = fixture()
    st = state(receipt)
    foreign_lock = replace(lock(receipt), period_id=AccountingPeriodId.new())
    with pytest.raises(InvalidPeriodControlCandidate, match="Foreign"):
        diagnostic(receipt, (st,), locks=(foreign_lock,))
    foreign_transition = replace(
        transition(receipt), book_scope=replace(
            receipt.assignment.book_scope, company_id=CompanyId.new()
        )
    )
    with pytest.raises(InvalidPeriodControlCandidate, match="Foreign"):
        diagnostic(receipt, (st,), transitions=(foreign_transition,))


def test_no_untyped_catalogs_and_no_untyped_completeness():
    receipt, _, _ = fixture()
    s = state(receipt)
    with pytest.raises(InvalidPeriodControlCandidate, match="Immutable"):
        preview_period_controls_candidate(
            book_receipt=receipt, states=[s], locks=(),
            transitions=(), completeness=COMPLETE,
        )
    with pytest.raises(InvalidPeriodControlCandidate, match="Explicit"):
        diagnostic(receipt, (s,), completeness="DECLARED_COMPLETE_RND")


def test_digest_stable_under_unordered_catalogs_and_timezone():
    receipt, _, _ = fixture()
    states = (state(receipt),)
    locks = (
        lock(receipt, lock_scope=PeriodLockScopeCandidate.SOURCE_LOCK, target="CRM"),
        lock(receipt, lock_scope=PeriodLockScopeCandidate.JOURNAL_LOCK, target="SALES"),
    )
    first = diagnostic(receipt, states, locks=locks)
    second = diagnostic(receipt, states, locks=tuple(reversed(locks)))
    assert first.content_digest == second.content_digest
    shifted = replace(
        receipt,
        known_at=FEB.astimezone(timezone(timedelta(hours=2))),
    )
    third = diagnostic(shifted, states, locks=locks)
    assert first.content_digest == third.content_digest


def test_nested_receipt_or_observation_tamper_detected():
    receipt, _, _ = fixture()
    s = state(receipt)
    proof = diagnostic(receipt, (s,))
    object.__setattr__(s, "source_ref", "tampered")
    with pytest.raises(PeriodControlCandidateDigestMismatch):
        proof.verify_integrity()
    fresh, _, _ = fixture()
    proof2 = diagnostic(fresh, (state(fresh),))
    object.__setattr__(proof2.book_receipt, "content_digest", "sha256:" + "0" * 64)
    with pytest.raises(Exception, match="changed"):
        proof2.verify_integrity()


def test_fabricated_disposition_lock_and_state_rejected():
    receipt, _, _ = fixture()
    s = state(receipt)
    proof = diagnostic(receipt, (s,))
    with pytest.raises(InvalidPeriodControlCandidate, match="Fabricated"):
        replace(proof, disposition=PeriodControlDiagnosticDisposition.NON_OPEN_CANDIDATE_STATUS)
    with pytest.raises(InvalidPeriodControlCandidate, match="Fabricated"):
        replace(proof, observed_active_locks=(lock(receipt),))


def test_immutable_observations_and_no_mutation_methods():
    receipt, _, _ = fixture()
    s = state(receipt)
    l = lock(receipt)
    t = transition(receipt)
    with pytest.raises(FrozenInstanceError):
        s.status = PeriodStatusCandidate.CLOSED
    with pytest.raises(FrozenInstanceError):
        l.active = False
    with pytest.raises(FrozenInstanceError):
        t.reason = "tampered"
    for obj in (s, l, t):
        for name in ("close", "open", "reopen", "post", "apply", "commit", "publish"):
            assert not hasattr(obj, name)


def test_service_requires_two_separate_test_grants():
    receipt, ver, assignment = fixture()
    s = state(receipt)

    class Grant:
        allowed = set()

        def require(self, *, principal, action, scope):
            if action not in self.allowed:
                raise PermissionError("No candidate preview grant")

    grant = Grant()
    calendar = BookCalendarCandidatePreviewService(
        versions=MemoryCalendarCandidateVersions((ver,)),
        assignments=MemoryBookCalendarAssignments((assignment,)),
        authorization=grant,
    )
    service = PeriodControlCandidateDiagnosticService(
        calendar_preview=calendar,
        observations=MemoryPeriodControlCandidates(states=(s,)),
        authorization=grant,
    )
    query = PreviewPeriodControlsCandidate(
        PreviewBookCalendarCandidate(assignment.book_scope, AS_OF, FEB), COMPLETE
    )
    actor = TrustedPrincipal("rnd-reviewer", "tenant-a")
    with pytest.raises(PermissionError, match="grant"):
        service.preview(query, principal=actor)
    grant.allowed = {"calendar.period.controls.candidate.preview"}
    with pytest.raises(PermissionError, match="grant"):
        service.preview(query, principal=actor)
    grant.allowed.add("calendar.assignment.candidate.preview")
    assert service.preview(query, principal=actor).state.id == s.id
    with pytest.raises(PermissionError, match="Cross-tenant"):
        service.preview(query, principal=TrustedPrincipal("rnd-reviewer", "tenant-b"))
    with pytest.raises(PermissionError, match="Unverified"):
        service.preview(query, principal="untrusted")


def test_malicious_observation_reader_foreign_candidate_fails_in_domain():
    receipt, ver, assignment = fixture()

    class Allow:
        def require(self, *, principal, action, scope):
            return None

    class Malicious:
        def states_for_period(self, scope):
            return (replace(
                state(receipt), book_scope=replace(scope, tenant_id="tenant-b")
            ),)

        def locks_for_period(self, scope):
            return ()

        def declarations_for_period(self, scope):
            return ()

    svc = PeriodControlCandidateDiagnosticService(
        calendar_preview=BookCalendarCandidatePreviewService(
            versions=MemoryCalendarCandidateVersions((ver,)),
            assignments=MemoryBookCalendarAssignments((assignment,)),
            authorization=Allow(),
        ), observations=Malicious(), authorization=Allow(),
    )
    with pytest.raises(InvalidPeriodControlCandidate, match="Foreign"):
        svc.preview(
            PreviewPeriodControlsCandidate(
                PreviewBookCalendarCandidate(assignment.book_scope, AS_OF, FEB),
                COMPLETE,
            ), principal=TrustedPrincipal("rnd", "tenant-a"),
        )


def test_memory_reader_is_scope_specific_read_only_and_non_authoritative():
    receipt, _, _ = fixture()
    st = state(receipt)
    reader = MemoryPeriodControlCandidates(states=(st,))
    assert reader.states_for_period(receipt.assignment.book_scope) == (st,)
    assert reader.states_for_period(
        replace(receipt.assignment.book_scope, book_id=AccountingBookId.new())
    ) == ()
    assert reader.locks_for_period(receipt.assignment.book_scope) == ()
    for name in ("save", "post", "publish", "close", "commit"):
        assert not hasattr(reader, name)


def test_new_modules_import_no_sql_or_live_ledger():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.application import (
        fiscal_period_control_diagnostics,
    )
    from pyaccountingkit.company_configuration.domain.fiscal_calendar import (
        period_controls,
    )
    from pyaccountingkit.company_configuration.infrastructure import (
        fiscal_period_control_memory,
    )

    for module in (
        fiscal_period_control_diagnostics, period_controls, fiscal_period_control_memory,
    ):
        code = Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(code)
        imports = {
            name.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for name in node.names
        }
        assert not imports & {"psycopg", "sqlalchemy", "django", "requests", "httpx"}
        assert "organization_issuer_gateway" not in code
