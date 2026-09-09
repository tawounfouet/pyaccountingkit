import json
from pathlib import Path

def ledger():
    return json.loads(Path("validation/review/ebnl_2023_visual_review_ledger.json").read_text(encoding="utf-8"))

def test_visual_review_ledger_has_verified_corrections():
    d=ledger()
    assert len(d["line_corrections"])==23
    by_line={x["source_line_md"]:x for x in d["line_corrections"]}
    assert by_line[833]["reviewed_code"]=="5023"
    assert by_line[868]["reviewed_code"]=="522"
    assert by_line[1317]["reviewed_code"]=="777"
    assert by_line[1377]["reviewed_code"]=="811"

def test_source_duplicate_4555_is_explicit():
    d=ledger()
    a=next(x for x in d["source_anomalies_verified"] if x["anomaly_id"]=="ebnl2023:duplicate-4555")
    assert a["code"]=="4555"
    assert len(a["occurrences"])==2
    assert a["policy"]=="preserve_both_occurrences_no_silent_correction"
