"""Replay qualification for LOT-20 financial analysis."""

from __future__ import annotations

from datetime import UTC, datetime

from tests.support.financial_analysis import run_golden_analysis


def test_same_pinned_analysis_inputs_replay_to_same_semantic_checksum() -> None:
    first = run_golden_analysis(
        analysis_snapshot_id="analysis:snapshot:first",
        generated_at=datetime(2027, 1, 2, tzinfo=UTC),
    )
    replay = run_golden_analysis(
        analysis_snapshot_id="analysis:snapshot:replay",
        generated_at=datetime(2028, 6, 1, tzinfo=UTC),
    )

    assert first.result_checksum == replay.result_checksum
    assert first.analysis_snapshot.checksum == replay.analysis_snapshot.checksum
    assert first.analysis_snapshot.snapshot_id != replay.analysis_snapshot.snapshot_id
    assert first.analysis_snapshot.generated_at != replay.analysis_snapshot.generated_at
