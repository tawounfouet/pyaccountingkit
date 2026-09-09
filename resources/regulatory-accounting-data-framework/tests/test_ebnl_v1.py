import json
from pathlib import Path
from regacct.standards.ebnl.validation import validate_v1,validate_duplicate_4555

def load():
    return json.loads(Path("datasets/structured/ebnl_2023_v1_structure.json").read_text(encoding="utf-8"))

def test_v1_graph():
    d=load()
    assert validate_v1(d)==[]
    assert d["statistics"]["graph_nodes"]==1145
    assert d["statistics"]["class_nodes"]==9
    assert d["statistics"]["class_scope_nodes"]==2
    assert d["statistics"]["group_nodes"]==84
    assert d["statistics"]["account_occurrence_nodes"]==1050

def test_duplicate_4555_has_two_occurrence_identities_and_source_parents():
    d=load()
    assert validate_duplicate_4555(d)==[]
    rows=[n for n in d["nodes"] if n["node_type"]=="account" and n["ref_code"]=="4555"]
    assert {n["node_id"] for n in rows}=={
        "account:ohada-ebnl:2023:4555:occ01",
        "account:ohada-ebnl:2023:4555:occ02",
    }

def test_class9_scopes():
    d=load()
    scopes=[n for n in d["nodes"] if n["node_type"]=="class_scope"]
    assert {x["attributes"]["scope_id"] for x in scopes}=={"voluntary_contributions","management_accounting"}
    by={n["ref_code"]:n for n in d["nodes"] if n["node_type"]=="group"}
    parent_ids={x["attributes"]["scope_id"]:x["node_id"] for x in scopes}
    assert by["90"]["parent_node_id"]==parent_ids["voluntary_contributions"]
    assert by["92"]["parent_node_id"]==parent_ids["management_accounting"]
