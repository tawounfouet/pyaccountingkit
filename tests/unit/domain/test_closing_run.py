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


def test_close_gate_blocks_on_blocking_control() -> None:
    gate = CloseGate()
    gate.require("BALANCE")
    gate.assert_passes([])
    with pytest.raises(ControlFailureError, match="BALANCE"):
        gate.assert_passes(["BALANCE"])


def test_close_gate_ignores_non_blocking_failures() -> None:
    gate = CloseGate()
    gate.require("BALANCE")
    gate.assert_passes(["CROSS_CHECK"])


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
