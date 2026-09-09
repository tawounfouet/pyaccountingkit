import json
from pathlib import Path
from regacct.framework.rag.bm25 import search
def test_rag():
 d=json.loads(Path("rag/indexes/syscohada-guide-2017-v2.json").read_text(encoding="utf-8"));assert d["statistics"]["pages_with_chunks"]==437;assert d["statistics"]["chunks"]>=600
 assert search(d,"amortissement unités oeuvre",top_k=5)
