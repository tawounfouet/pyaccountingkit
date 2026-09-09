import json
from pathlib import Path
from regacct.framework.rag.bm25 import search


def test_primary_doctrine_contains_ir1_to_ir5():
    data = json.loads(Path("datasets/annotated/nonprofit_2026_doctrine_ir.json").read_text(encoding="utf-8"))
    assert data["statistics"]["total"] > 50
    for key in ("IR1","IR2","IR3","IR4","IR5"):
        assert data["statistics"][key] > 0


def test_rag_finds_fonds_dedies():
    idx = json.loads(Path("rag/indexes/nonprofit-recueil-2026-v1.json").read_text(encoding="utf-8"))
    results = search(idx, "fonds dédiés générosité du public", top_k=5)
    assert results
    assert any("fonds" in x["snippet_source"].lower() for x in results)
