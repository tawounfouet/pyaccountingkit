import json
from pathlib import Path
from regacct.standards.pcg.validation import validate_reporting
from regacct.standards.pcg.reporting import evaluate_statement


def load():
    return json.loads(Path("datasets/reporting/pcg_2026_v3_reporting.json").read_text(encoding="utf-8"))


def test_four_reporting_templates_are_built():
    data = load()
    assert data["statistics"]["statement_templates"] == 4
    assert validate_reporting(data) == []
    ids = {s["statement_id"] for s in data["statements"]}
    assert "pcg2026:statement:balance_base" in ids
    assert "pcg2026:statement:income_base" in ids
    assert "pcg2026:statement:balance_abrege" in ids
    assert "pcg2026:statement:income_abrege" in ids


def test_base_balance_terrain_net():
    data = load()
    st = next(s for s in data["statements"] if s["statement_id"] == "pcg2026:statement:balance_base")
    trial = [
        {"account_code":"211","debit_balance":50000,"credit_balance":0},
        {"account_code":"2911","debit_balance":0,"credit_balance":5000},
    ]
    result = evaluate_statement(st, trial)
    row = next(r for r in result["rows"] if r["label"] == "Terrains")
    assert row["value"] == 45000


def test_reverse_index_includes_cash():
    data = load()
    assert "53" in data["account_to_statement_lines"]
