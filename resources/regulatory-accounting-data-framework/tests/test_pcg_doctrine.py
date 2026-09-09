import json
from pathlib import Path
from regacct.framework.rag.bm25 import search


def test_ir_registry_has_all_five_categories():
    data = json.loads(Path("datasets/annotated/pcg_2026_doctrine_ir.json").read_text(encoding="utf-8"))
    assert data["statistics"]["total"] > 100
    for k in ("IR1","IR2","IR3","IR4","IR5"):
        assert data["statistics"][k] > 0


def test_rag_returns_article_context():
    index = json.loads(Path("rag/indexes/pcg-recueil-2026-v1.json").read_text(encoding="utf-8"))
    results = search(index, "1209 acomptes dividendes", top_k=5)
    assert results
    assert any("1209" in r["snippet_source"] for r in results)
