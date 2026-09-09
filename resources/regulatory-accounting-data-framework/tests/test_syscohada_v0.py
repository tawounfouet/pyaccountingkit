import json
from pathlib import Path
from regacct.standards.syscohada.validation import validate_v0
def load():return json.loads(Path("datasets/raw/syscohada_2017_v0_raw.json").read_text(encoding="utf-8"))
def test_counts():
 d=load();assert d["statistics"]=={"classes":9,"source_entries":1403,"groups":85,"main_accounts":432,"sub_accounts":886,"unique_codes":1403};assert validate_v0(d)==[]
def test_class9_label():
 d=load();c=next(x for x in d["classes"] if x["code_source"]=="9");assert "comptabilité analytique de gestion" in c["label_source"]
def test_no_padding():
 codes={x["code_source"] for x in load()["records"]};assert {"10","101","1011"}<=codes;assert "10000" not in codes
