"""L06-05 contract simulation vs authoritative C10-Q04: negative acceptance."""

import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from pyaccountingkit.company_configuration.application.fiscal_c10_q04_service_rnd import (
    FiscalC10Q04SimulationService,
    SimulatePeriodStatusContract,
)
from pyaccountingkit.company_configuration.application.fiscal_c10_q04_simulation import (
    AUTHORITY,
    SCHEMA_VERSION,
    InvalidPeriodStatusSimulation,
    SimulatedPeriodStatusQuery,
    UntrustedPeriodStatusForPosting,
    inspect_simulated_period_status_wire,
    reject_simulated_status_for_posting,
    simulate_period_status_contract,
)
from pyaccountingkit.company_configuration.application.fiscal_calendar_candidate_preview import (
    BookCalendarCandidatePreviewService,
)
from pyaccountingkit.company_configuration.application.fiscal_period_control_diagnostics import (
    PeriodControlCandidateDiagnosticService,
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
    ObservationCompleteness,
    PeriodCode,
    PeriodControlDiagnosticDisposition,
    PeriodKind,
    PeriodLockObservationCandidate,
    PeriodLockScopeCandidate,
    PeriodStateObservationCandidate,
    PeriodStatusCandidate,
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
START = date(2027, 1, 1)
MID = date(2027, 2, 1)
END = date(2028, 1, 1)
DAY = date(2027, 2, 15)


def fixture(*, status=PeriodStatusCandidate.OPEN, locked=False,
            completeness=ObservationCompleteness.DECLARED_COMPLETE_RND):
    scope = ConfigurationScope("tenant-a", CompanyId.new(), LegalEntityId.new())
    cal = FiscalCalendarDraft(
        FiscalCalendarId.new(), scope, CalendarCode("FY2027"),
        "R&D calendar", EffectiveInterval(START, END),
        "rnd:jurisdiction", "rnd:calendar",
    )
    year = FiscalYearDraft(
        FiscalYearId.new(), cal.id, scope, FiscalYearCode("FY2027"),
        EffectiveInterval(START, END), "rnd:year",
    )
    first = AccountingPeriodDraft(
        AccountingPeriodId.new(), year.id, cal.id, scope,
        PeriodCode("P01"), PeriodKind.ORDINARY,
        EffectiveInterval(START, MID), "rnd:p1", 1,
    )
    second = AccountingPeriodDraft(
        AccountingPeriodId.new(), year.id, cal.id, scope,
        PeriodCode("P02"), PeriodKind.ORDINARY,
        EffectiveInterval(MID, END), "rnd:p2", 2,
    )
    version = CalendarVersionCandidate(
        CalendarCandidateVersionId.new(), cal, (year,), (first, second),
        CalendarCoveragePolicy.REQUIRE_CONTIGUOUS,
        EffectiveInterval(START, END), KnowledgeInterval(JAN),
        "rnd:version",
    )
    assignment = BookCalendarAssignmentCandidate(
        BookCalendarAssignmentCandidateId.new(),
        replace(scope, book_id=AccountingBookId.new()),
        cal.id, version.id, EffectiveInterval(START, END),
        KnowledgeInterval(JAN), "rnd:assignment",
    )
    receipt = preview_book_calendar_candidate(
        book_scope=assignment.book_scope, as_of=DAY, known_at=FEB,
        assignments=(assignment,), calendar_versions=(version,),
    )
    state = PeriodStateObservationCandidate(
        PeriodStateCandidateId.new(), assignment.book_scope,
        version.id, second.id, status, 1, KnowledgeInterval(JAN), "rnd:state",
    )
    locks = ()
    if locked:
        locks = (PeriodLockObservationCandidate(
            PeriodLockCandidateId.new(), assignment.book_scope,
            version.id, second.id, PeriodLockScopeCandidate.JOURNAL_LOCK,
            "SALES", True, 1, KnowledgeInterval(JAN), "rnd:lock",
        ),)
    diagnostic = preview_period_controls_candidate(
        book_receipt=receipt, states=(state,), locks=locks, transitions=(),
        completeness=completeness,
    )
    query = SimulatedPeriodStatusQuery(assignment.book_scope, DAY, FEB)
    return query, diagnostic, version, assignment, state, locks


def produced(*, status=PeriodStatusCandidate.OPEN, locked=False,
             completeness=ObservationCompleteness.DECLARED_COMPLETE_RND):
    query, diagnostic, *_ = fixture(
        status=status, locked=locked, completeness=completeness,
    )
    return query, simulate_period_status_contract(query=query, diagnostic=diagnostic)


def decoded(wire, query):
    return inspect_simulated_period_status_wire(wire=wire, query=query)


def edit_wire(response, **changes):
    manifest = json.loads(response.to_wire())
    manifest.update(changes)
    return json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )


def test_open_without_locks_is_untrusted_and_unpostable():
    query, response = produced()
    assert response.schema_version == SCHEMA_VERSION
    assert response.authority == AUTHORITY
    manifest = response.manifest()
    assert manifest["eligible_for_posting"] is False
    assert manifest["observed_status"] == "OPEN"
    assert manifest["diagnostic_disposition"] == "NO_OBSERVED_LOCKS_UNVERIFIED"
    assert manifest["observed_lock_observations"] == []
    assert not hasattr(response, "potentially_postable")
    assert not hasattr(response, "can_post")
    assert not hasattr(response, "commit")
    assert decoded(response.to_wire(), query).content_digest == response.content_digest
    with pytest.raises(UntrustedPeriodStatusForPosting):
        reject_simulated_status_for_posting(response)


@pytest.mark.parametrize("status", list(PeriodStatusCandidate))
def test_all_statuses_rejected_for_posting_even_open(status):
    _, response = produced(status=status)
    with pytest.raises(UntrustedPeriodStatusForPosting):
        reject_simulated_status_for_posting(response)


def test_observed_scoped_lock_not_automatically_computed_as_blocking():
    query, response = produced(locked=True)
    assert response.diagnostic_disposition is (
        PeriodControlDiagnosticDisposition.LOCKS_OBSERVED_SCOPE_UNEVALUATED
    )
    assert response.observed_locks[0].scope == "JOURNAL_LOCK"
    assert response.observed_locks[0].target_code == "SALES"
    assert "has_blocking_lock" not in response.manifest()
    assert "potentially_postable" not in response.manifest()
    assert decoded(response.to_wire(), query) == response
    with pytest.raises(UntrustedPeriodStatusForPosting):
        reject_simulated_status_for_posting(response)


def test_incomplete_catalog_explicit_and_remains_non_authoritative():
    _, response = produced(completeness=ObservationCompleteness.INCOMPLETE_RND)
    assert response.diagnostic_disposition is (
        PeriodControlDiagnosticDisposition.INCOMPLETE_CANDIDATE_EVIDENCE
    )
    with pytest.raises(UntrustedPeriodStatusForPosting):
        reject_simulated_status_for_posting(response)


def test_wire_contains_expected_c10_q04_shape_but_unpublished_sources():
    query, response = produced()
    body = json.loads(response.to_wire())
    assert body["book_id"] == str(query.book_scope.book_id)
    assert body["posting_date"] == DAY.isoformat()
    assert body["known_at"].endswith("Z")
    assert body["calendar_candidate_version_id"]
    assert body["period_id"] and body["period_code"] == "P02"
    assert body["state_revision"] == 1
    assert body["period_control_candidate_digest"].startswith("sha256:")
    assert body["calendar_candidate_digest"].startswith("sha256:")
    assert body["authority"] == "UNTRUSTED_CANDIDATE_SIMULATION"
    assert "published_at" not in body
    assert "control_version" not in body
    assert "observed_at" not in body


def test_wire_is_canonical_and_reproducible():
    query, response = produced()
    assert response.to_wire() == decoded(response.to_wire(), query).to_wire()
    assert response.to_wire() == response.to_wire()
    assert response.content_digest.startswith("sha256:")
    assert len(response.content_digest) == 71


def test_utc_equivalent_query_instants_match():
    query, response = produced()
    shifted = SimulatedPeriodStatusQuery(
        query.book_scope, query.posting_date,
        query.known_at.astimezone(timezone(timedelta(hours=2))),
    )
    assert decoded(response.to_wire(), shifted).content_digest == response.content_digest


@pytest.mark.parametrize("changed", [
    {"schema_version": "1.0"},
    {"schema_version": "C10-Q04"},
    {"authority": "AUTHORITATIVE"},
    {"authority": "SIGNED"},
    {"eligible_for_posting": True},
    {"eligible_for_posting": "false"},
])
def test_no_authority_upgrade_via_wire(changed):
    query, response = produced()
    with pytest.raises(InvalidPeriodStatusSimulation, match="authority"):
        decoded(edit_wire(response, **changed), query)


@pytest.mark.parametrize("changed", [
    {"observed_status": "UNKNOWN"},
    {"diagnostic_disposition": "APPROVED"},
    {"state_revision": "1"},
    {"state_revision": 0},
    {"calendar_candidate_version_id": "latest"},
    {"book_id": "wrong"},
    {"posting_date": "2027-02-16"},
    {"known_at": "2027-02-01T00:00:00"},
    {"period_id": "wrong"},
    {"period_code": "p02"},
    {"calendar_candidate_digest": "sha256:wrong"},
])
def test_malformed_or_changed_wire_values_are_rejected(changed):
    query, response = produced()
    with pytest.raises(InvalidPeriodStatusSimulation):
        decoded(edit_wire(response, **changed), query)


def test_reject_extra_missing_and_unknown_wire_fields():
    query, response = produced()
    with pytest.raises(InvalidPeriodStatusSimulation, match="fields"):
        decoded(edit_wire(response, can_post=True), query)
    body = json.loads(response.to_wire())
    body.pop("content_digest")
    with pytest.raises(InvalidPeriodStatusSimulation, match="fields"):
        decoded(json.dumps(body), query)


def test_reject_duplicate_json_keys_and_noncannonical_whitespace():
    query, response = produced()
    with pytest.raises(InvalidPeriodStatusSimulation, match="Noncanonical"):
        decoded(response.to_wire() + " ", query)
    wire = response.to_wire()
    duplicate = wire.replace(
        '"authority":"UNTRUSTED_CANDIDATE_SIMULATION",',
        '"authority":"UNTRUSTED_CANDIDATE_SIMULATION",'
        '"authority":"UNTRUSTED_CANDIDATE_SIMULATION",',
    )
    with pytest.raises(InvalidPeriodStatusSimulation, match="Noncanonical"):
        decoded(duplicate, query)


def test_wire_digest_mutation_and_self_checksum_are_not_signatures():
    query, response = produced()
    with pytest.raises(InvalidPeriodStatusSimulation, match="checksum"):
        decoded(edit_wire(response, period_code="P03"), query)
    tampered = json.loads(response.to_wire())
    tampered["source"] = "signed"
    with pytest.raises(InvalidPeriodStatusSimulation):
        decoded(json.dumps(tampered), query)


def test_reject_lock_malformed_or_forged_applicability_fields():
    query, response = produced(locked=True)
    for bad in (
        [{"lock_id": "bad", "scope": "JOURNAL_LOCK", "target_code": "SALES"}],
        [{"lock_id": str(response.observed_locks[0].lock_id), "scope": "JOURNAL_LOCK"}],
        [{"lock_id": response.observed_locks[0].lock_id,
          "scope": "GLOBAL_BOOK_LOCK", "target_code": "SALES"}],
        [{"lock_id": response.observed_locks[0].lock_id,
          "scope": "JOURNAL_LOCK", "target_code": "sales"}],
    ):
        with pytest.raises(InvalidPeriodStatusSimulation):
            decoded(edit_wire(response, observed_lock_observations=bad), query)


def test_cannot_create_contradictory_open_no_lock_payload():
    query, response = produced(locked=True)
    with pytest.raises(InvalidPeriodStatusSimulation, match="Contradictory"):
        replace(
            response,
            diagnostic_disposition=(
                PeriodControlDiagnosticDisposition.NO_OBSERVED_LOCKS_UNVERIFIED
            ),
        )
    with pytest.raises(InvalidPeriodStatusSimulation, match="Contradictory"):
        replace(
            response,
            observed_status=PeriodStatusCandidate.CLOSED,
        )


def test_empty_or_duplicate_or_unsorted_lock_catalog_rejected():
    query, response = produced(locked=True)
    lock = response.observed_locks[0]
    with pytest.raises(InvalidPeriodStatusSimulation, match="unique"):
        replace(response, observed_locks=(lock, lock))
    with pytest.raises(InvalidPeriodStatusSimulation):
        replace(response, observed_locks=[lock])
    with pytest.raises(InvalidPeriodStatusSimulation):
        replace(response, observed_locks=(replace(lock, lock_id="bad"),))


def test_producer_refuses_mismatch_on_book_business_date_known_at():
    query, diagnostic, *_ = fixture()
    other_book = replace(query.book_scope, book_id=AccountingBookId.new())
    for changed in (
        SimulatedPeriodStatusQuery(other_book, DAY, FEB),
        SimulatedPeriodStatusQuery(query.book_scope, date(2027, 2, 16), FEB),
        SimulatedPeriodStatusQuery(query.book_scope, DAY, JAN),
    ):
        with pytest.raises(InvalidPeriodStatusSimulation, match="mismatch"):
            simulate_period_status_contract(query=changed, diagnostic=diagnostic)


def test_consumer_refuses_other_tenant_book_date_or_time():
    query, response = produced()
    for changed in (
        SimulatedPeriodStatusQuery(
            replace(query.book_scope, tenant_id="tenant-b"), DAY, FEB,
        ),
        SimulatedPeriodStatusQuery(
            replace(query.book_scope, book_id=AccountingBookId.new()), DAY, FEB,
        ),
        SimulatedPeriodStatusQuery(query.book_scope, date(2027, 2, 16), FEB),
        SimulatedPeriodStatusQuery(query.book_scope, DAY, JAN),
    ):
        with pytest.raises(InvalidPeriodStatusSimulation, match="mismatch"):
            decoded(response.to_wire(), changed)


def test_diagnostic_nested_digest_tamper_fails_before_producer_simulation():
    query, diag, *_ = fixture()
    object.__setattr__(diag, "content_digest", "sha256:" + "0" * 64)
    with pytest.raises(Exception, match="changed"):
        simulate_period_status_contract(query=query, diagnostic=diag)


def test_frozen_wire_response_cannot_set_posting_authorization():
    _, response = produced()
    with pytest.raises(FrozenInstanceError):
        response.state_revision = 10
    with pytest.raises((FrozenInstanceError, TypeError)):
        response.eligible_for_posting = True


def test_three_separate_fake_read_grants_required_for_service():
    query, diag, version, assignment, state, locks = fixture()

    class Grant:
        allowed = set()

        def require(self, *, principal, action, scope):
            if action not in self.allowed:
                raise PermissionError("Fake candidate grant denied")

    grant = Grant()
    calendar = BookCalendarCandidatePreviewService(
        versions=MemoryCalendarCandidateVersions((version,)),
        assignments=MemoryBookCalendarAssignments((assignment,)),
        authorization=grant,
    )
    observations = MemoryPeriodControlCandidates(states=(state,), locks=locks)
    diagnostics = PeriodControlCandidateDiagnosticService(
        calendar_preview=calendar, observations=observations,
        authorization=grant,
    )
    service = FiscalC10Q04SimulationService(
        diagnostics=diagnostics, authorization=grant,
    )
    req = SimulatePeriodStatusContract(
        query, ObservationCompleteness.DECLARED_COMPLETE_RND,
    )
    principal = TrustedPrincipal("rnd-actor", "tenant-a")
    with pytest.raises(PermissionError, match="denied"):
        service.simulate(req, principal=principal)
    grant.allowed = {"calendar.c10_q04.contract.simulation.preview"}
    with pytest.raises(PermissionError, match="denied"):
        service.simulate(req, principal=principal)
    grant.allowed.add("calendar.period.controls.candidate.preview")
    with pytest.raises(PermissionError, match="denied"):
        service.simulate(req, principal=principal)
    grant.allowed.add("calendar.assignment.candidate.preview")
    result = service.simulate(req, principal=principal)
    assert result.observed_status is PeriodStatusCandidate.OPEN
    with pytest.raises(UntrustedPeriodStatusForPosting):
        reject_simulated_status_for_posting(result)
    with pytest.raises(PermissionError, match="Cross-tenant"):
        service.simulate(
            req, principal=TrustedPrincipal("rnd-actor", "tenant-b"),
        )
    with pytest.raises(PermissionError, match="Unverified"):
        service.simulate(req, principal="fake")


def test_simulation_service_does_not_expose_live_get_period_status():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.application import (
        fiscal_c10_q04_service_rnd,
        fiscal_c10_q04_simulation,
    )

    for module in (fiscal_c10_q04_service_rnd, fiscal_c10_q04_simulation):
        assert not hasattr(module, "get_period_status")
        for forbidden_method in (
            "publish", "post", "commit", "close", "reopen",
            "can_post", "authorize_posting",
        ):
            assert not hasattr(module, forbidden_method)
        text = Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(text)
        direct_imports = {
            item.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for item in node.names
        }
        assert not direct_imports & {
            "psycopg", "sqlalchemy", "requests", "httpx", "django",
        }
        assert "organization_issuer_gateway" not in text
