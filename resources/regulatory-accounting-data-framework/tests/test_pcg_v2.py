import json
from pathlib import Path
from regacct.standards.pcg.validation import validate_v2


def load():
    return json.loads(Path("datasets/annotated/pcg_2026_v2_account_functioning.json").read_text(encoding="utf-8"))


def test_titre_xii_is_extracted_without_executable_rules():
    data = load()
    assert data["statistics"]["annotations"] == 58
    assert validate_v2(data) == []
    assert all(a["executable_rules_generated"] is False for a in data["annotations"])


def test_account_109_specific_evidence_is_preserved():
    data = load()
    art = next(a for a in data["annotations"] if a["article_ref"] == "1211-10")
    assert "109" in art["account_mentions"]
    assert any("109" in frag and "débité" in frag.lower() for frag in art["posting_guidance_evidence"])


def test_1209_specific_source_is_present():
    data = load()
    art = next(a for a in data["annotations"] if a["article_ref"] == "1211-12")
    assert "1209" in art["account_mentions"]
    assert "Acomptes sur dividendes" in art["text_source"]
