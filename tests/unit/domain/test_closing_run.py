"""Unit tests for closing runs, close gate and evidence (LOT-09)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from pyaccountingkit.core.errors import ControlFailureError
from pyaccountingkit.domain.closing.closing_run import (
    CloseGate,
    ClosingEvidenceBundle,
    ClosingPhase,
    ClosingRun,
    ClosingRunBook,
)
from pyaccountingkit.domain.controls.control import (
    ControlOutcome,
    ControlResult,
    ControlRun,
)

NOW = datetime(2024, 12, 31, 23, 0, tzinfo=UTC)


def _evidence() -> ClosingEvidenceBundle:
    return ClosingEvidenceBundle(
        run_id="c1",
        period_id="p_2024_12",
        trial_balance_checksum="sha256:abc",
        control_runs_hash="sha256:ctl",
        total_debit="1000.00",
        total_credit="1000.00",
        sealed_at=NOW,
    )


def test_run_starts_running_and_seals_with_evidence() -> None:
    run = ClosingRun(id="c1", period_id="p_2024_12")
    assert run.phase is ClosingPhase.RUNNING
    sealed = run.with_evidence(_evidence())
    assert sealed.is_sealed
    assert sealed.evidence == _evidence()


def test_evidence_digest_is_stable() -> None:
    sealed = ClosingRun(id="c1", period_id="p_2024_12").with_evidence(_evidence())
    assert sealed.evidence_digest() == ClosingRun.evidence_digest_from(_evidence())


def _control(
    outcome: ControlOutcome,
    *,
    code: str = "BALANCE",
    period_id: str = "p_2024_12",
    run_id: str | None = None,
) -> ControlRun:
    return ControlRun(
        id=run_id or f"run:{code}:{outcome.value}",
        definition_code=code,
        version=1,
        period_id=period_id,
        result=ControlResult(outcome=outcome, detail="qualification"),
        executed_at=NOW,
    )


def test_close_gate_blocks_missing_required_control() -> None:
    gate = CloseGate()
    gate.require("BALANCE")

    with pytest.raises(ControlFailureError, match="absents.*BALANCE"):
        gate.assert_passes([], period_id="p_2024_12")


@pytest.mark.parametrize("outcome", (ControlOutcome.FAIL, ControlOutcome.ERROR))
def test_close_gate_blocks_non_pass_required_control(outcome: ControlOutcome) -> None:
    gate = CloseGate()
    gate.require("BALANCE")

    with pytest.raises(ControlFailureError, match=f"BALANCE:{outcome.value}"):
        gate.assert_passes(
            [_control(outcome)],
            period_id="p_2024_12",
        )


def test_close_gate_blocks_required_control_from_another_period() -> None:
    gate = CloseGate()
    gate.require("BALANCE")

    with pytest.raises(ControlFailureError, match="BALANCE:FOREIGN_PERIOD"):
        gate.assert_passes(
            [_control(ControlOutcome.PASS, period_id="p_2024_11")],
            period_id="p_2024_12",
        )


def test_close_gate_blocks_ambiguous_required_control_evidence() -> None:
    gate = CloseGate()
    gate.require("BALANCE")

    with pytest.raises(ControlFailureError, match="BALANCE:AMBIGUOUS"):
        gate.assert_passes(
            [
                _control(ControlOutcome.PASS, run_id="run:1"),
                _control(ControlOutcome.PASS, run_id="run:2"),
            ],
            period_id="p_2024_12",
        )


def test_close_gate_ignores_non_blocking_failures_when_required_controls_pass() -> None:
    gate = CloseGate()
    gate.require("BALANCE")
    gate.assert_passes(
        [
            _control(ControlOutcome.PASS),
            _control(ControlOutcome.FAIL, code="CROSS_CHECK"),
        ],
        period_id="p_2024_12",
    )


def test_run_book_preserves_previous_evidence_on_reopen() -> None:
    book = ClosingRunBook()
    first = ClosingRun(id="c1", period_id="p_2024_12").with_evidence(_evidence())
    book.record(first)
    later = ClosingRun(id="c2", period_id="p_2025_01").with_evidence(_evidence())
    book.record(later)
    assert book.get("c1").evidence == _evidence()
    assert len(book.runs_for_period("p_2024_12")) == 1


def test_run_book_is_append_only() -> None:
    book = ClosingRunBook()
    book.record(ClosingRun(id="c1", period_id="p_2024_12").with_evidence(_evidence()))
    with pytest.raises(ValueError, match="immuable"):
        book.record(ClosingRun(id="c1", period_id="p_2024_12"))
