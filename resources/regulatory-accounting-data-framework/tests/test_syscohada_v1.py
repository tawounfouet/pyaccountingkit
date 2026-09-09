import json
from pathlib import Path
from regacct.standards.syscohada.validation import validate_v1
def load():return json.loads(Path("datasets/structured/syscohada_2017_v1_structure.json").read_text(encoding="utf-8"))
def test_graph():
 d=load();assert validate_v1(d)==[];assert d["statistics"]["graph_nodes"]==1412;assert d["statistics"]["account_nodes"]==1403
def test_1011_path():
 d=load();bc={n["ref_code"]:n for n in d["nodes"]};bi={n["node_id"]:n for n in d["nodes"]}
 assert bi[bc["1011"]["parent_node_id"]]["ref_code"]=="101";assert bi[bc["101"]["parent_node_id"]]["ref_code"]=="10";assert bi[bc["10"]["parent_node_id"]]["ref_code"]=="1"
