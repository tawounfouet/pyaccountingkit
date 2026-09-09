import json
from pathlib import Path
from regacct.framework.rag.bm25 import search


def test_full_source_router_indexes_all_438_pages():
    d=json.loads(Path("rag/indexes/ebnl-sycebnl-2023-source-router-v2.json").read_text(encoding="utf-8"))
    assert d["statistics"]["pages_with_chunks"]==438
    assert d["source_quality_notice"]["complete_page_routing"] is True
    assert d["source_quality_notice"]["router_is_metadata_not_verbatim_ocr"] is True
    hits=search(d,"fonds affectés",top_k=10)
    assert hits
    pages={h["page_pdf"] for h in hits}
    assert 120 in pages or 319 in pages
