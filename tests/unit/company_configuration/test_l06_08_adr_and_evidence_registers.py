"""L06-08 documentary governance: exact R&D receipts, NO G6 approval."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs" / "company_configuration"


def load(name: str) -> dict:
    return json.loads((DOCS / name).read_text(encoding="utf-8"))


def adrs() -> dict:
    return load("L06_08_FISCAL_CALENDAR_ADR_REGISTER.json")


def evidence() -> dict:
    return load("L06_08_RND_EVIDENCE_AND_GATE_LEDGER.json")


def test_all_ten_source_adrs_recorded_once_and_remain_open():
    register = adrs()
    rows = register["adrs"]
    assert register["decision_count"] == 10
    assert register["all_decisions_unapproved"] is True
    assert {entry["id"] for entry in rows} == {
        f"ADR-CAL-{index:02d}" for index in range(1, 11)
    }
    assert all(entry["status"] == "OPEN" for entry in rows)
    assert all(entry["decision_record"] is None for entry in rows)
    assert all(entry["approver_signoff"] is None for entry in rows)


def test_every_adr_has_real_decision_questions_and_nonbinding_work():
    for entry in adrs()["adrs"]:
        assert len(entry["options"]) >= 2
        assert len(set(entry["options"])) == len(entry["options"])
        assert entry["non_binding_recommendation"].strip()
        assert entry["tradeoffs_and_risks"].strip()
        assert entry["accountable_roles"]
        assert len(entry["acceptance_criteria"]) >= 3
        assert entry["evidence_prs"]
        assert all(88 <= pr <= 94 for pr in entry["evidence_prs"])
        assert entry["blocks_live"]


def test_core_commit_adrs_open_and_proof_gates_not_forged():
    rows = {entry["id"]: entry for entry in adrs()["adrs"]}
    for ident in ("ADR-CAL-07", "ADR-CAL-08"):
        assert rows[ident]["priority"] == "BLOCKER"
        assert rows[ident]["status"] == "OPEN"
        assert rows[ident]["approver_signoff"] is None
    assert "ADR-CC-007" in rows["ADR-CAL-07"][
        "non_binding_recommendation"
    ]


def test_seven_prs_and_exact_head_workflows_are_unique():
    ledger = evidence()
    entries = ledger["verified_prs"]
    assert len(entries) == 7
    assert [row["lot"] for row in entries] == [
        f"L06-{index:02d}" for index in range(1, 8)
    ]
    assert [row["pr"] for row in entries] == list(range(88, 95))
    assert len({row["sha"] for row in entries}) == 7
    workflows = [
        run for row in entries for run in row["workflow_run_ids"].values()
    ]
    assert len(workflows) == 28
    assert len(set(workflows)) == len(workflows)
    assert all(
        row["ci_status"] == "4_OF_4_WORKFLOWS_SUCCESS_AT_EXACT_SHA"
        and row["pr_state"] == "OPEN_DRAFT_UNMERGED"
        and len(row["sha"]) == 40
        and len(row["workflow_run_ids"]) == 4
        for row in entries
    )


@pytest.mark.parametrize("python", ["python_311", "python_312"])
def test_qualified_rnd_suite_counts_and_foundation_lineage(python):
    rows = evidence()["verified_prs"]
    assert [row[python]["passed"] for row in rows] == [
        346, 378, 422, 457, 498, 528, 560
    ]
    assert all(row[python]["skipped"] == 19 for row in rows)
    assert all(
        row["postgres_311"]["passed"] == 134
        and row["postgres_312"]["passed"] == 134
        and row["migration_recovery_311"]["passed"] == 6
        and row["migration_recovery_312"]["passed"] == 6
        and row["original_foundation_sql_migration_count"] == 14
        for row in rows
    )


def test_source_matrix_has_all_invariants_and_scenarios_without_live_go():
    matrix = load("L06_07_CAL_INVARIANTS_AND_SCENARIOS_COVERAGE.json")
    assert {item["id"] for item in matrix["invariants"]} == {
        f"CAL-INV-{index:02d}" for index in range(1, 13)
    }
    assert {item["id"] for item in matrix["scenarios"]} == {
        f"CAL-SC-{index:02d}" for index in range(1, 21)
    }
    for row in (*matrix["invariants"], *matrix["scenarios"]):
        assert row["status"] in {"CANDIDATE_PARTIAL", "NOT_IMPLEMENTED_LIVE"}
    assert matrix["ci_status"] == "PENDING_EXACT_HEAD"
    assert "PENDING_EXACT_HEAD" in evidence()["source_traceability"]["matrix_stale_field"]


def test_security_hold_and_unverified_gates_are_preserved():
    adr_gates = adrs()["gates"]
    actual = evidence()
    assert actual["gates"] == adr_gates
    assert adr_gates["G3"] == "HOLD_SECURITY"
    assert adr_gates["G6"] == "NOT_APPROVED"
    assert adrs()["security_issue"] == {"number": 71, "state": "OPEN"}
    assert actual["security_issue"] == {"number": 71, "state": "OPEN"}
    assert actual["g6_approved"] is False
    assert actual["live_acceptance"] is False
    for key in (
        "publication_actual",
        "real_get_period_status",
        "real_ledger_posting",
        "real_post_close_sql_fencing",
        "real_multibook_e2e",
    ):
        assert actual[key] is False
    assert actual["no_new_sql_migration"] is True


def test_consolidated_registers_cross_linked_and_no_approved_adr():
    adr_doc = (DOCS / "L06_08_FISCAL_CALENDAR_ADR_REGISTER.md").read_text(
        encoding="utf-8"
    )
    summary = (DOCS / "L06_08_RND_CONSOLIDATION_AND_PRODUCTION_GAPS.md").read_text(
        encoding="utf-8"
    )
    for number in range(1, 11):
        assert f"ADR-CAL-{number:02d}" in adr_doc
    for number in range(88, 95):
        assert f"/pull/{number}" in summary
    assert "ADR-CC-007" in adr_doc
    assert "ADR-CC-07" in adr_doc
    assert "CAL-SC-09" in summary
    assert "G6_GO" in summary
    assert "NONE APPROVED" in adr_doc
    assert "NOT_APPROVED" in summary


def test_registers_do_not_define_runtime_permission_or_live_writer():
    docs = (
        "L06_08_FISCAL_CALENDAR_ADR_REGISTER.json",
        "L06_08_RND_EVIDENCE_AND_GATE_LEDGER.json",
    )
    for name in docs:
        body = load(name)
        assert body["gates"]["G6"] == "NOT_APPROVED"
    assert not (ROOT / "src" / "pyaccountingkit" / "company_configuration"
                / "application" / "fiscal_l06_08_publisher.py").exists()
