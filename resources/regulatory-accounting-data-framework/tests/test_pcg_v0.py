import json
from pathlib import Path
from regacct.standards.pcg.validation import validate_v0


def load():
    return json.loads(Path("datasets/raw/pcg_2026_v0_raw.json").read_text(encoding="utf-8"))


def test_pcg_v0_exact_plan_counts():
    data = load()
    assert data["statistics"]["classes"] == 7
    assert data["statistics"]["groups"] == 61
    assert data["statistics"]["accounts"] == 768
    assert data["statistics"]["account_ranges"] == 1
    assert data["statistics"]["records_total"] == 837
    assert data["statistics"]["optional_account_entries"] == 403
    assert validate_v0(data) == []


def test_pcg_optional_status_from_markdown_italics():
    data = load()
    by_code = {r["code_normalized"]:r for r in data["records"]}
    assert by_code["101"]["optional"] is False
    assert by_code["1011"]["optional"] is True
    assert by_code["1061"]["optional"] is False


def test_account_range_is_not_silently_split():
    data = load()
    ranges = [r for r in data["records"] if r["record_type"] == "account_range"]
    assert len(ranges) == 1
    assert ranges[0]["code_source"] == "471 à 473"
