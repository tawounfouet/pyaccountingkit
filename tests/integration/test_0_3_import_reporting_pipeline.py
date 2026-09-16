"""Release-0.3 cross-lot integration qualification from FEC source to sealed evidence."""

from datetime import UTC, datetime

from tests.support.release_0_3_pipeline import run_release_0_3_pipeline


def test_fec_import_to_regulatory_evidence_uses_one_canonical_accounting_chain() -> None:
    result = run_release_0_3_pipeline(
        snapshot_created_at=datetime(2027, 1, 2, tzinfo=UTC),
        export_time=datetime(2027, 1, 3, tzinfo=UTC),
        id_seed=1,
        replay_import_in_same_store=True,
    )

    assert result.fec_valid is True
    assert result.imported_entry_id.startswith("imp_")
    assert result.ledger_entry_count == 1
    assert result.audit_event_count == 1
    assert result.same_store_replay_preserved_single_effect is True

    assert result.trial_balance_balanced is True
    assert result.cash_amount == "100.00"
    assert result.supplier_amount == "100.00"
    assert result.financial_control_passed is True
    assert result.report_snapshot_published is True

    assert result.regulatory_assets_amount == "100.00"
    assert result.regulatory_liabilities_equity_amount == "100.00"
    assert result.regulatory_validation_valid is True

    assert len(result.source_checksum) == 64
    assert len(result.import_plan_checksum) == 64
    assert len(result.trial_balance_checksum) == 64
    assert len(result.financial_result_checksum) == 64
    assert len(result.report_snapshot_checksum) == 64
    assert len(result.regulatory_report_checksum) == 64
    assert len(result.regulatory_validation_checksum) == 64
    assert len(result.export_payload_checksum) == 64
    assert len(result.evidence_checksum) == 64
