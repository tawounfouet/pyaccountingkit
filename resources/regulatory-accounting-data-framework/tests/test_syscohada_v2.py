import json
from pathlib import Path
from regacct.standards.syscohada.validation import validate_v2
def test_v2():
 d=json.loads(Path("datasets/annotated/syscohada_2017_v2_accounting_knowledge.json").read_text(encoding="utf-8"));assert validate_v2(d)==[]
 assert d["statistics"]["applications"]==142;assert d["knowledge_policy"]["executable_rules_generated"] is False
 assert len(d["capability_groups"]["current_operations"])==24;assert len(d["capability_groups"]["specific_operations"])==102
 assert len(d["capability_groups"]["financial_statements"])==1;assert len(d["capability_groups"]["consolidation_and_combination"])==15
