import json
from pathlib import Path
from regacct.standards.ebnl.validation import validate_capability_status


def test_complete_normative_corpus_closes_v2_v3_source_gap():
    d=json.loads(Path("validation/review/ebnl_2023_capability_status.json").read_text(encoding="utf-8"))
    assert validate_capability_status(d)==[]
    assert d["normative_source_gap_closed"] is True
    assert d["capabilities"]["v0_chart"]["status"]=="implemented"
    assert d["capabilities"]["v1_structure"]["status"]=="implemented"
    assert d["capabilities"]["v2_account_functioning"]["invented_rules_allowed"] is False
    assert d["capabilities"]["v3_reporting"]["invented_templates_allowed"] is False
    assert d["capabilities"]["full_verbatim_ocr"]["status"]=="not_claimed"
