import json
from pathlib import Path
from regacct.standards.nonprofit.validation import validate_reporting


def test_nonprofit_reporting_has_four_templates():
    data = json.loads(Path("datasets/reporting/nonprofit_2026_v3_reporting.json").read_text(encoding="utf-8"))
    assert validate_reporting(data) == []
    ids = {x["statement_id"] for x in data["statements"]}
    assert ids == {
        "nonprofit2026:balance",
        "nonprofit2026:income",
        "nonprofit2026:crod",
        "nonprofit2026:cer",
    }


def test_nonprofit_specific_balance_lines_exist():
    data = json.loads(Path("datasets/reporting/nonprofit_2026_v3_reporting.json").read_text(encoding="utf-8"))
    balance = next(x for x in data["statements"] if x["statement_id"] == "nonprofit2026:balance")
    labels = {x["label_source"] for x in balance["lines"]}
    assert "Fonds dédiés" in labels
    assert "Biens reçus par legs ou donations destinés à être cédés" in labels


def test_reporting_account_hints_are_not_executable():
    data = json.loads(Path("datasets/reporting/nonprofit_2026_v3_reporting.json").read_text(encoding="utf-8"))
    assert data["mapping_policy"]["account_hints_executable"] is False
    assert data["mapping_policy"]["human_validation_required"] is True
