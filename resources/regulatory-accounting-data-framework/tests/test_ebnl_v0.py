import json
from pathlib import Path
from regacct.standards.ebnl.validation import validate_v0

def load():
    return json.loads(Path("datasets/raw/ebnl_2023_v0_reviewed_structure.json").read_text(encoding="utf-8"))

def test_v0_exact_counts():
    d=load()
    assert validate_v0(d)==[]
    s=d["statistics"]
    assert s["classes"]==9
    assert s["class_scopes"]==2
    assert s["groups"]==84
    assert s["account_occurrences"]==1050
    assert s["unique_account_codes"]==1049

def test_corrected_codes_exist_and_bad_ocr_codes_do_not():
    d=load()
    codes=[x["code_source"] for x in d["records"]]
    for code in ("4421","4571","4781","4991","5023","5025","5032","522","525","572","592","777","811"):
        assert code in codes
    for bad in ("023","032","22","25","72","92","7717","719"):
        assert bad not in codes

def test_duplicate_4555_is_preserved():
    d=load()
    rows=[x for x in d["records"] if x["code_source"]=="4555"]
    assert len(rows)==2
    assert {x["source_group_context"] for x in rows}=={"45"}
    assert {x["source_parent_context"] for x in rows}=={"452","455"}
