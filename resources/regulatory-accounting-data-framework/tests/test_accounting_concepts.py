import json
from pathlib import Path
from regacct.framework.validation.relations import validate_concept_bindings

def test_seed_concepts_without_bindings():
    d=json.loads(Path("datasets/concepts/accounting_core_concepts_v0.json").read_text(encoding="utf-8"))
    assert len(d["concepts"])==12
    assert d["bindings"]==[]
    assert validate_concept_bindings(d["bindings"])==[]
    assert d["binding_policy"]["code_equality_is_semantic_evidence"] is False
    assert d["binding_policy"]["auto_approval_allowed"] is False
