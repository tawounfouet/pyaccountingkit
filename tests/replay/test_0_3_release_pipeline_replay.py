"""Release-0.3 replay qualification across import, ledger and reporting boundaries."""

from datetime import UTC, datetime

from tests.support.release_0_3_pipeline import run_release_0_3_pipeline


def test_same_source_and_semantic_coordinates_replay_to_same_evidence_chain() -> None:
    first = run_release_0_3_pipeline(
        snapshot_created_at=datetime(2027, 1, 2, tzinfo=UTC),
        export_time=datetime(2027, 1, 3, tzinfo=UTC),
        id_seed=1,
        replay_import_in_same_store=False,
    )
    replay = run_release_0_3_pipeline(
        snapshot_created_at=datetime(2028, 6, 1, tzinfo=UTC),
        export_time=datetime(2028, 6, 2, tzinfo=UTC),
        id_seed=100,
        replay_import_in_same_store=False,
    )

    assert first.replay_fingerprint == replay.replay_fingerprint
    assert first.import_plan_checksum == replay.import_plan_checksum
    assert first.ledger_entry_count == replay.ledger_entry_count == 1
    assert first.audit_event_count == replay.audit_event_count == 1
