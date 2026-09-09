import json
from pathlib import Path
from regacct.standards.syscohada.validation import validate_v3
def L():return json.loads(Path("datasets/reporting/syscohada_2017_v3_reporting.json").read_text(encoding="utf-8"))
def test_counts():
 d=L();assert validate_v3(d)==[];assert d["statistics"]["balance_model_lines"]==48;assert d["statistics"]["income_model_lines"]==34;assert d["statistics"]["cashflow_model_lines"]==23;assert d["statistics"]["notes"]==46
def test_source_gaps_and_conflicts():
 d=L();assert d["source_scope"]["official_exhaustive_post_account_correspondence_table_available_in_bundle"] is False
 assert len([x for x in d["model_example"]["cashflow"]["lines"] if x["source_ref_code"]=="ZF"])==2
 assert next(x for x in d["source_supported_narrative_rules"] if x["rule_id"].endswith("hao-source-conflict"))["evaluation_status"]=="blocked_source_conflict"
