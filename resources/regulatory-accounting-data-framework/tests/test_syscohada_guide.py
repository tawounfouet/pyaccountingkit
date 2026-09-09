import json
from pathlib import Path
from regacct.standards.syscohada.validation import validate_guide
def L(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def test_registry():
 t=L("datasets/annotated/syscohada_2017_guide_registry.json");a=L("datasets/annotated/syscohada_2017_applications.json")
 assert t["statistics"]=={"parts":4,"chapters":56,"sections":33,"applications":142};assert validate_guide(t,a)==[]
def test_application_pages_and_anomalies():
 d=L("datasets/annotated/syscohada_2017_applications.json");b={x["application_number"]:x for x in d["applications"]}
 assert b[1]["page_start_pdf"]==19;assert b[127]["page_start_pdf"]==341;assert b[127]["page_start_printed_toc"]==343
 assert b[142]["page_start_pdf"]==435;assert b[142]["page_start_printed_toc"]==437
 assert b[53]["application_number_source"]==535;assert b[53]["number_resolution"]=="toc_title_match"
 assert b[61]["application_number_source"]==616;assert b[113]["application_number_source"]==113
def test_app127_local_account():
 d=L("datasets/annotated/syscohada_2017_applications.json");a=next(x for x in d["applications"] if x["application_number"]==127)
 m=[x for x in a["account_mentions"] if x["source_code"]=="101300"];assert m;assert any(x["resolved_code"]=="1013" for x in m)
