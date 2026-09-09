import json
from pathlib import Path
from regacct.standards.ebnl.validation import validate_comparison

def load():
    return json.loads(Path("datasets/crosswalk/ebnl_2023_vs_syscohada_2017_structural_delta.json").read_text(encoding="utf-8"))

def test_delta_is_not_inheritance_or_semantic_crosswalk():
    d=load()
    assert validate_comparison(d)==[]
    p=d["comparison_policy"]
    assert p["inheritance_asserted"] is False
    assert p["semantic_equivalence_from_code_equality"] is False
    assert p["automatic_crosswalk_approval"] is False

def test_4555_is_ambiguous_in_delta():
    d=load()
    r=next(x for x in d["rows"] if x["ref_code"]=="4555")
    assert r["status"]=="ambiguous_ebnl_source_code"
    assert len(r["ebnl_occurrences"])==2
