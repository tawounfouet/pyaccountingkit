from __future__ import annotations
from pathlib import Path
import math
import re
import unicodedata
from collections import Counter, defaultdict

PAGE_RE = re.compile(r"<!--\s*Page PDF\s+(\d+)\s*-->")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s


def tokenize(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", normalize_text(s)) if len(t) > 2]


def build_markdown_page_index(path: str | Path, document_id: str, max_chars: int = 1600) -> dict:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    chunks = []
    page = None
    heading_path = []
    buffer = []
    buffer_page = None
    buffer_heading = []

    def flush():
        nonlocal buffer
        text = "\n".join(buffer).strip()
        if not text:
            buffer = []
            return
        chunk_id = f"{document_id}:p{buffer_page or 0:03d}:c{len(chunks)+1:04d}"
        toks = tokenize(text)
        chunks.append({
            "chunk_id": chunk_id,
            "page_pdf": buffer_page,
            "heading_path": list(buffer_heading),
            "text_source": text,
            "token_count": len(toks),
        })
        buffer = []

    for line in lines:
        m = PAGE_RE.search(line)
        if m:
            flush()
            page = int(m.group(1))
            buffer_page = page
            continue

        m = HEADING_RE.match(line)
        if m:
            if buffer and sum(len(x)+1 for x in buffer) > max_chars // 2:
                flush()
            level = len(m.group(1))
            heading_path = heading_path[:level-1] + [m.group(2).strip()]
            buffer_heading = list(heading_path)
            if buffer_page is None:
                buffer_page = page
            buffer.append(line)
            continue

        if buffer_page is None:
            buffer_page = page
        if not buffer_heading:
            buffer_heading = list(heading_path)

        if buffer and sum(len(x)+1 for x in buffer) + len(line) > max_chars:
            flush()
            buffer_page = page
            buffer_heading = list(heading_path)
        buffer.append(line)

    flush()

    terms = defaultdict(list)
    dfs = Counter()
    for idx, chunk in enumerate(chunks):
        unique = set(tokenize(chunk["text_source"]))
        for term in sorted(unique):
            terms[term].append(idx)
            dfs[term] += 1

    return {
        "index_version": "deterministic_bm25_lexical_v1",
        "document_id": document_id,
        "chunks": chunks,
        "terms": dict(sorted(terms.items())),
        "statistics": {
            "chunks": len(chunks),
            "terms": len(terms),
            "pages_with_chunks": len({c["page_pdf"] for c in chunks if c["page_pdf"] is not None}),
            "average_tokens": round(sum(c["token_count"] for c in chunks) / max(len(chunks),1), 2),
        },
    }


def search(index: dict, query: str, top_k: int = 5) -> list[dict]:
    qterms = tokenize(query)
    chunks = index["chunks"]
    N = len(chunks)
    avgdl = sum(c.get("token_count",0) for c in chunks) / max(N,1)
    scores = defaultdict(float)
    k1, b = 1.5, 0.75

    candidate_ids = set()
    for term in qterms:
        candidate_ids.update(index.get("terms", {}).get(term, []))

    for idx in candidate_ids:
        chunk = chunks[idx]
        toks = tokenize(chunk["text_source"])
        counts = Counter(toks)
        dl = max(len(toks),1)
        for term in qterms:
            tf = counts.get(term, 0)
            if not tf:
                continue
            df = len(index.get("terms", {}).get(term, []))
            idf = math.log(1 + (N - df + 0.5) / (df + 0.5))
            scores[idx] += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / max(avgdl,1)))
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:top_k]
    return [{
        "chunk_id": chunks[i]["chunk_id"],
        "page_pdf": chunks[i]["page_pdf"],
        "heading_path": chunks[i]["heading_path"],
        "score": round(score, 6),
        "snippet_source": chunks[i]["text_source"][:800],
    } for i, score in ranked]
