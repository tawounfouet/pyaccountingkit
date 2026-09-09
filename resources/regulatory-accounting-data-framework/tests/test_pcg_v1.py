import json
from pathlib import Path
from regacct.standards.pcg.validation import validate_v1


def load():
    return json.loads(Path("datasets/structured/pcg_2026_v1_structure.json").read_text(encoding="utf-8"))


def test_pcg_v1_graph_is_valid():
    data = load()
    assert validate_v1(data) == []


def test_no_padding_collisions():
    data = load()
    refs = {n["ref_code"]:n["node_id"] for n in data["nodes"] if n["node_type"] in {"group","account"}}
    for a,b in [("11","110"),("12","120"),("28","280"),("29","290"),("59","590")]:
        assert refs[a] != refs[b]


def test_pcg_parentage():
    data = load()
    by_ref = {n["ref_code"]:n for n in data["nodes"] if n["node_type"] in {"group","account"}}
    by_id = {n["node_id"]:n for n in data["nodes"]}
    assert by_id[by_ref["10131"]["parent_node_id"]]["ref_code"] == "1013"
    assert by_id[by_ref["1013"]["parent_node_id"]]["ref_code"] == "101"
    assert by_id[by_ref["101"]["parent_node_id"]]["ref_code"] == "10"
