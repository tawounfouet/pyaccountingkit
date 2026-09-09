import json
from pathlib import Path
from regacct.families.registry import FamilyRegistry

def test_ohada_family_members():
    f=FamilyRegistry("families").get("ohada-accounting")
    assert f.member_standard_refs==["ohada-syscohada:2017","ohada-ebnl:2023","cemac-pcemf:2010"]
    assert f.relation_policy["membership_does_not_imply_inheritance"] is True

def test_no_inheritance_edges():
    d=json.loads(Path("datasets/relations/ohada_accounting_standard_relations.json").read_text(encoding="utf-8"))
    assert all(x["relation_type"]!="inherits" for x in d["relations"])
