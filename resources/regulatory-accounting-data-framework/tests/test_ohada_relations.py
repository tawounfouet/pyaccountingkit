import json
from pathlib import Path
from regacct.models import StandardRelation
from regacct.framework.validation.relations import validate_no_false_ohada_inheritance, validate_no_unproven_inheritance

def get_relations():
    d=json.loads(Path("datasets/relations/ohada_accounting_standard_relations.json").read_text(encoding="utf-8"))
    return [StandardRelation.model_validate(x) for x in d["relations"]]

def test_temporal_guard_green():
    rs=get_relations()
    assert validate_no_false_ohada_inheritance(rs)==[]
    assert validate_no_unproven_inheritance(rs)==[]

def test_pcemf_sector_relation():
    r=next(x for x in get_relations() if x.relation_id=="ohada-family:pcemf-member")
    assert r.relation_type.value=="sector_specialization_within_family"
    assert r.target_ref=="ohada-accounting"
    assert r.evidence.source_refs[0].page_pdf==3

def test_crosswalk_review():
    r=next(x for x in get_relations() if x.relation_type.value=="crosswalk")
    assert r.human_review_required is True
    assert r.auto_inference_allowed is False
