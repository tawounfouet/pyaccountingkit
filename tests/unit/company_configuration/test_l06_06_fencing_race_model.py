"""L06-06 abstract fencing traces: prove MODEL behavior, NEVER SQL safety."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime
from itertools import permutations
from uuid import uuid4

import pytest

from pyaccountingkit.company_configuration.application.fiscal_c10_q04_simulation import (
    ObservedLockWireCandidate,
    SimulatedPeriodStatusResponse,
    UntrustedPeriodStatusForPosting,
)
from pyaccountingkit.company_configuration.application.fiscal_fencing_race_model_rnd import (
    MODEL_SCHEMA,
    InvalidSymbolicFenceTrace,
    SymbolicFenceTraceTampered,
    SymbolicPeriodControl,
    SymbolicPreflightObservation,
    SymbolicRaceOutcome,
    SymbolicRaceStep,
    UnverifiedPostingFenceGate,
    refuse_symbolic_fence_for_posting,
    simulate_symbolic_close_post_race,
)
from pyaccountingkit.company_configuration.domain.fiscal_calendar.period_controls import (
    PeriodControlDiagnosticDisposition,
    PeriodStatusCandidate,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountingBookId,
    AccountingPeriodId,
    CalendarCandidateVersionId,
    CompanyId,
    LegalEntityId,
)

CLOSE = SymbolicRaceStep.MODEL_CLOSE
POST = SymbolicRaceStep.MODEL_POST_ATTEMPT
NOTIFY = SymbolicRaceStep.MODEL_DELAYED_CLOSE_NOTIFICATION


def source(*, status=PeriodStatusCandidate.OPEN, locks=(), completeness=False):
    scope = ConfigurationScope(
        "tenant-a", CompanyId.new(), LegalEntityId.new(), AccountingBookId.new()
    )
    if completeness:
        disposition = PeriodControlDiagnosticDisposition.INCOMPLETE_CANDIDATE_EVIDENCE
    elif status is not PeriodStatusCandidate.OPEN:
        disposition = PeriodControlDiagnosticDisposition.NON_OPEN_CANDIDATE_STATUS
    elif locks:
        disposition = PeriodControlDiagnosticDisposition.LOCKS_OBSERVED_SCOPE_UNEVALUATED
    else:
        disposition = PeriodControlDiagnosticDisposition.NO_OBSERVED_LOCKS_UNVERIFIED
    return SimulatedPeriodStatusResponse(
        book_scope=scope,
        posting_date=date(2027, 2, 15),
        known_at=datetime(2027, 2, 1, tzinfo=UTC),
        calendar_version_id=CalendarCandidateVersionId.new(),
        period_id=AccountingPeriodId.new(),
        period_code="P02", observed_status=status, state_revision=17,
        diagnostic_disposition=disposition,
        observed_locks=tuple(locks),
        calendar_candidate_digest="sha256:" + "a" * 64,
        period_control_candidate_digest="sha256:" + "b" * 64,
    )


def inputs(response=None):
    response = response or source()
    state = SymbolicPeriodControl(
        response.book_scope, response.calendar_version_id, response.period_id,
        response.state_revision, 23, response.observed_status,
    )
    token = SymbolicPreflightObservation(
        state.book_scope, state.calendar_version_id, state.period_id,
        state.revision, state.fence_epoch, response.content_digest,
    )
    return response, state, token


def model(response, initial, token, *steps):
    return simulate_symbolic_close_post_race(
        initial=initial, preflight=token, source_response=response, steps=steps,
    )


def assert_no_real_authority(proof):
    proof.verify_integrity()
    manifest = proof.manifest()
    assert manifest["schema"] == MODEL_SCHEMA
    assert manifest["disposition"] == "ABSTRACT_TRACE_ONLY_NO_LEDGER_AUTHORITY"
    assert manifest["sql_committed"] is False
    assert manifest["journal_entry_created"] is False
    assert manifest["posting_authorized"] is False
    assert manifest["signed"] is False
    assert proof.unverified_gates == tuple(UnverifiedPostingFenceGate)
    assert len(proof.unverified_gates) == 6
    assert "ATOMIC_LEDGER_COMMIT_FENCE" in manifest["unverified_gates"]
    assert "SIGNED_ISSUER_ACTOR_AT_COMMIT" in manifest["unverified_gates"]
    for attribute in (
        "post", "commit", "can_post", "authorize_posting", "publish", "save",
        "post_journal_entry", "get_period_status",
    ):
        assert not hasattr(proof, attribute)
    with pytest.raises(UntrustedPeriodStatusForPosting):
        refuse_symbolic_fence_for_posting(proof)


def test_close_before_post_rejects_stale_revision_and_epoch_model_only():
    response, initial, token = inputs()
    proof = model(response, initial, token, CLOSE, POST)
    assert [event.outcome for event in proof.observations] == [
        SymbolicRaceOutcome.MODEL_CLOSE_ORDERED,
        SymbolicRaceOutcome.MODEL_REJECTED_STALE_STATE,
    ]
    assert proof.final_state.status is PeriodStatusCandidate.CLOSED
    assert proof.final_state.revision == 18
    assert proof.final_state.fence_epoch == 24
    assert_no_real_authority(proof)


def test_post_before_close_can_only_be_described_as_abstract_order():
    response, initial, token = inputs()
    proof = model(response, initial, token, POST, CLOSE)
    assert proof.observations[0].outcome is (
        SymbolicRaceOutcome.MODEL_ORDERED_PRE_CLOSE_ONLY
    )
    assert proof.observations[1].outcome is SymbolicRaceOutcome.MODEL_CLOSE_ORDERED
    assert proof.final_state.status is PeriodStatusCandidate.CLOSED
    assert_no_real_authority(proof)


def test_all_pairwise_close_post_permutations_explored_and_never_authorize():
    response, initial, token = inputs()
    seen = set()
    for order in permutations((POST, CLOSE)):
        proof = model(response, initial, token, *order)
        seen.add((order, tuple(item.outcome for item in proof.observations)))
        assert_no_real_authority(proof)
    assert len(seen) == 2


def test_second_close_is_nonmutating_in_abstract_history():
    response, initial, token = inputs()
    proof = model(response, initial, token, CLOSE, CLOSE, POST)
    assert [event.outcome for event in proof.observations] == [
        SymbolicRaceOutcome.MODEL_CLOSE_ORDERED,
        SymbolicRaceOutcome.MODEL_CLOSE_ALREADY_PRESENT,
        SymbolicRaceOutcome.MODEL_REJECTED_STALE_STATE,
    ]
    assert proof.final_state.revision == initial.revision + 1
    assert proof.final_state.fence_epoch == initial.fence_epoch + 1
    assert_no_real_authority(proof)


@pytest.mark.parametrize("order", [
    (CLOSE, NOTIFY, POST),
    (NOTIFY, CLOSE, POST),
    (POST, CLOSE, NOTIFY),
])
def test_delayed_close_event_is_never_an_authoritative_fence(order):
    response, initial, token = inputs()
    proof = model(response, initial, token, *order)
    assert any(item.outcome is (
        SymbolicRaceOutcome.MODEL_EVENT_IGNORED_NOT_AUTHORITY
    ) for item in proof.observations)
    assert_no_real_authority(proof)


def test_delayed_notification_alone_does_not_change_abstract_status():
    response, initial, token = inputs()
    proof = model(response, initial, token, NOTIFY, POST)
    assert proof.final_state == initial
    assert proof.observations[0].before_epoch == proof.observations[0].after_epoch
    assert proof.observations[1].outcome is (
        SymbolicRaceOutcome.MODEL_ORDERED_PRE_CLOSE_ONLY
    )
    assert_no_real_authority(proof)


@pytest.mark.parametrize("status", [
    PeriodStatusCandidate.DRAFT, PeriodStatusCandidate.FUTURE,
    PeriodStatusCandidate.SOFT_CLOSED, PeriodStatusCandidate.CLOSED,
    PeriodStatusCandidate.ARCHIVED,
])
def test_every_non_open_state_is_denied_in_symbolic_model(status):
    response, initial, token = inputs(source(status=status))
    proof = model(response, initial, token, POST)
    assert proof.observations[0].outcome is (
        SymbolicRaceOutcome.MODEL_REJECTED_NON_OPEN
    )
    assert_no_real_authority(proof)


def test_observed_lock_must_not_be_treated_as_authorized_posting_scope():
    lock = ObservedLockWireCandidate(str(uuid4()), "JOURNAL_LOCK", "SALES")
    response, initial, token = inputs(source(locks=(lock,)))
    trace = model(response, initial, token, POST)
    assert trace.observations[0].outcome is (
        SymbolicRaceOutcome.MODEL_REJECTED_UNVERIFIED_LOCKS
    )
    assert_no_real_authority(trace)


def test_incomplete_candidate_lock_catalog_is_not_a_commit_proof():
    response, initial, token = inputs(source(completeness=True))
    proof = model(response, initial, token, POST)
    assert proof.observations[0].outcome is (
        SymbolicRaceOutcome.MODEL_REJECTED_INCOMPLETE_EVIDENCE
    )
    assert_no_real_authority(proof)


def test_changed_status_revision_without_fence_epoch_advancement_is_stale():
    response, initial, token = inputs()
    # Abstract concurrent state change, not SQL transition.
    newer = replace(initial, revision=initial.revision + 1)
    with pytest.raises(InvalidSymbolicFenceTrace, match="Unpinned"):
        model(response, newer, token, POST)


def test_changed_fence_epoch_without_revision_is_not_a_usable_preflight():
    response, initial, token = inputs()
    newer = replace(initial, fence_epoch=initial.fence_epoch + 1)
    with pytest.raises(InvalidSymbolicFenceTrace, match="Unpinned"):
        model(response, newer, token, POST)


def test_foreign_tenant_or_book_or_calendar_or_period_is_rejected():
    response, initial, token = inputs()
    mutations = [
        {"book_scope": replace(initial.book_scope, tenant_id="tenant-b")},
        {"book_scope": replace(initial.book_scope, book_id=AccountingBookId.new())},
        {"calendar_version_id": CalendarCandidateVersionId.new()},
        {"period_id": AccountingPeriodId.new()},
    ]
    for fields in mutations:
        with pytest.raises(InvalidSymbolicFenceTrace, match="Unpinned"):
            model(response, replace(initial, **fields), token, POST)


def test_token_forgery_scope_version_period_revision_epoch_digest_rejected():
    response, initial, token = inputs()
    alterations = [
        {"book_scope": replace(token.book_scope, company_id=CompanyId.new())},
        {"calendar_version_id": CalendarCandidateVersionId.new()},
        {"period_id": AccountingPeriodId.new()},
        {"read_revision": token.read_revision + 1},
        {"read_epoch": token.read_epoch + 1},
        {"source_receipt_digest": "sha256:" + "0" * 64},
    ]
    for changes in alterations:
        with pytest.raises(InvalidSymbolicFenceTrace, match="Unpinned"):
            model(response, initial, replace(token, **changes), POST)


def test_forged_initial_status_unrelated_to_preflight_is_rejected():
    response, initial, token = inputs()
    with pytest.raises(InvalidSymbolicFenceTrace, match="Unpinned"):
        model(
            response, replace(initial, status=PeriodStatusCandidate.CLOSED),
            token, POST,
        )


def test_simulated_source_digest_tamper_blocks_model_before_any_step():
    response, initial, token = inputs()
    object.__setattr__(response, "content_digest", "sha256:" + "0" * 64)
    with pytest.raises(Exception, match="tampered"):
        model(response, initial, token, POST)


def test_missing_or_invalid_symbolic_steps_are_refused():
    response, initial, token = inputs()
    for sequence in ((), (CLOSE,), (POST, POST), (POST, "CLOSE")):
        with pytest.raises(InvalidSymbolicFenceTrace):
            model(response, initial, token, *sequence)
    with pytest.raises(InvalidSymbolicFenceTrace, match="At most two"):
        model(response, initial, token, CLOSE, CLOSE, CLOSE, POST)


def test_untyped_or_nonpositive_epoch_revision_is_refused():
    response, initial, token = inputs()
    for value in (0, -1, True, 1.5, "1"):
        with pytest.raises(InvalidSymbolicFenceTrace):
            replace(initial, revision=value)
        with pytest.raises(InvalidSymbolicFenceTrace):
            replace(initial, fence_epoch=value)
        with pytest.raises(InvalidSymbolicFenceTrace):
            replace(token, read_epoch=value)
        with pytest.raises(InvalidSymbolicFenceTrace):
            replace(token, read_revision=value)


def test_trace_is_deterministic_with_full_content_checksum():
    response, initial, token = inputs()
    a = model(response, initial, token, CLOSE, POST)
    b = model(response, initial, token, CLOSE, POST)
    assert a.manifest() == b.manifest()
    assert a.content_digest == b.content_digest
    assert a.content_digest.startswith("sha256:")
    assert len(a.content_digest) == 71
    a.verify_integrity()


def test_trace_step_order_is_not_sortable_without_changing_meaning():
    response, initial, token = inputs()
    close_first = model(response, initial, token, CLOSE, POST)
    post_first = model(response, initial, token, POST, CLOSE)
    assert close_first.content_digest != post_first.content_digest
    assert close_first.observations[-1].outcome is (
        SymbolicRaceOutcome.MODEL_REJECTED_STALE_STATE
    )


def test_fabricated_observation_or_final_state_rejected_even_with_rechecksum():
    response, initial, token = inputs()
    proof = model(response, initial, token, CLOSE, POST)
    fake = replace(
        proof.observations[1],
        outcome=SymbolicRaceOutcome.MODEL_ORDERED_PRE_CLOSE_ONLY,
    )
    with pytest.raises(InvalidSymbolicFenceTrace, match="Fabricated"):
        replace(proof, observations=(proof.observations[0], fake))
    with pytest.raises(InvalidSymbolicFenceTrace, match="Fabricated"):
        replace(proof, final_state=initial)


def test_cannot_delete_external_gates_and_claim_safety():
    response, initial, token = inputs()
    proof = model(response, initial, token, POST, CLOSE)
    with pytest.raises(InvalidSymbolicFenceTrace, match="falsely elevated"):
        replace(proof, unverified_gates=())


def test_nested_or_digest_mutation_detected_on_reverification():
    response, initial, token = inputs()
    proof = model(response, initial, token, POST, CLOSE)
    object.__setattr__(proof, "content_digest", "sha256:" + "0" * 64)
    with pytest.raises(SymbolicFenceTraceTampered):
        proof.verify_integrity()
    fresh = model(response, initial, token, CLOSE, POST)
    object.__setattr__(fresh.final_state, "fence_epoch", 900)
    with pytest.raises(SymbolicFenceTraceTampered):
        fresh.verify_integrity()


def test_models_are_frozen_and_have_no_ledger_methods():
    response, initial, token = inputs()
    proof = model(response, initial, token, POST)
    with pytest.raises(FrozenInstanceError):
        proof.steps = ()
    with pytest.raises(FrozenInstanceError):
        token.read_epoch = 999
    for obj in (proof, initial, token):
        for action in ("commit", "post", "insert", "acquire_lock", "publish", "close"):
            assert not hasattr(obj, action)


def test_l06_06_no_sql_ledger_provider_or_authoritative_c10_import():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.application import (
        fiscal_fencing_race_model_rnd,
    )

    text = Path(fiscal_fencing_race_model_rnd.__file__).read_text(encoding="utf-8")
    tree = ast.parse(text)
    imports = {
        item.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for item in node.names
    }
    assert not imports.intersection({
        "psycopg", "sqlalchemy", "django", "requests", "httpx"
    })
    for forbidden in (
        "organization_issuer_gateway", "ledger.post", "get_period_status",
        "journalentry",
    ):
        assert forbidden not in text.lower()
