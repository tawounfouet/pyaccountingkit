import json
from pathlib import Path
from regacct.framework.rag.bm25 import search

def test_ocr_rag_has_quality_notice_and_29_pages():
    d=json.loads(Path("rag/indexes/ebnl-plan-2023-ocr-v1.json").read_text(encoding="utf-8"))
    assert d["statistics"]["pages_with_chunks"]==29
    assert d["source_quality_notice"]["pdf_is_visual_authority"] is True
    assert d["source_quality_notice"]["use_for_authoritative_quote_without_pdf_check"] is False
    assert search(d,"contributions volontaires en nature",top_k=5)
