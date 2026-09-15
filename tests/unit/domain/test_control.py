"""Unit tests for the controls domain (LOT-08)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from pyaccountingkit.core.errors import ControlFailureError
from pyaccountingkit.domain.controls.control import (
    ControlDefinition,
    ControlGate,
    ControlOutcome,
    ControlResult,
    ControlRun,
    ControlRunBook,
)


def _definition(version: int = 3) -> ControlDefinition:
    return ControlDefinition(code="BALANCE", label="Équilibre débit/crédit", version=version)


def _run(
    run_id: str = "run_1",
    *,
    outcome: ControlOutcome = ControlOutcome.PASS,
) -> ControlRun:
    return ControlRun(
        id=run_id,
        definition_code="BALANCE",
        version=3,
        period_id="p_2024_01",
        result=ControlResult(
            outcome=outcome,
            detail="ok" if outcome is ControlOutcome.PASS else "ko",
        ),
        executed_at=datetime(2024, 1, 31, 10, 0, tzinfo=UTC),
    )


def test_definitions_are_versioned() -> None:
    assert _definition().version == 3
    with pytest.raises(ValueError):
        ControlDefinition(code="B", label="b", version=0)


def test_failed_run_flagged() -> None:
    assert not _run().failed
    assert _run(outcome=ControlOutcome.FAIL).failed


def test_gate_passes_on_success() -> None:
    gate = ControlGate(_definition())
    assert gate.evaluate(_run()) is True


def test_gate_blocks_on_failure() -> None:
    gate = ControlGate(_definition())
    with pytest.raises(ControlFailureError):
        gate.evaluate(_run(outcome=ControlOutcome.FAIL))


def test_gate_rejects_definition_mismatch() -> None:
    gate = ControlGate(_definition())
    wrong = ControlRun(
        id="run_2",
        definition_code="OTHER",
        version=3,
        period_id="p",
        result=ControlResult.passed(),
        executed_at=datetime(2024, 1, 31, tzinfo=UTC),
    )
    with pytest.raises(ValueError, match="mismatch"):
        gate.evaluate(wrong)


def test_run_book_history_is_append_only() -> None:
    book = ControlRunBook()
    failed = _run(run_id="run_fail", outcome=ControlOutcome.FAIL)
    book.record(failed)
    assert book.get("run_fail") == failed
    with pytest.raises(ValueError, match="immuable"):
        book.record(_run(run_id="run_fail", outcome=ControlOutcome.PASS))


def test_failed_control_history_immutable() -> None:
    book = ControlRunBook()
    failed = _run(run_id="run_1", outcome=ControlOutcome.FAIL)
    book.record(failed)
    history = book.history()
    assert history == (failed,)
    assert history[0].failed
    assert len(book.history()) == 1
