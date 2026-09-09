import json
from pathlib import Path
from regacct.standards.nonprofit.validation import validate_functioning


def test_functioning_articles_are_source_evidence_not_posting_rules():
    data = json.loads(Path("datasets/annotated/nonprofit_2026_v2_account_functioning.json").read_text(encoding="utf-8"))
    assert validate_functioning(data) == []
    refs = {x["article_ref"] for x in data["annotations"]}
    assert {"331-1","331-2","331-3","331-4","332-1","333-1","333-2"} <= refs
    assert all(x["executable_rules_generated"] is False for x in data["annotations"])


def test_partner_account_rules_are_preserved():
    data = json.loads(Path("datasets/annotated/nonprofit_2026_v2_account_functioning.json").read_text(encoding="utf-8"))
    a = next(x for x in data["annotations"] if x["article_ref"] == "333-2")
    assert "455" in a["account_refs"]
    assert "crédit" in a["text_source"].lower()
