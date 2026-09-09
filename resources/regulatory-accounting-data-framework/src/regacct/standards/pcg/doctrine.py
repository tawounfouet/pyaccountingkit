from __future__ import annotations
from pathlib import Path
import re

PAGE_RE = re.compile(r"<!--\s*Page PDF\s+(\d+)\s*-->")
ARTICLE_RE = re.compile(r"^######\s+Art\.\s+([0-9]+(?:-[0-9]+)?)(?:\s+(.+?))?\s*$")
HEADING_RE = re.compile(r"^(#{1,5})\s+(.+?)\s*$")
IR_RE = re.compile(r"^\s*I\s*R\s*([1-5])\s*[-–:]?\s*(.+?)\s*$", re.I)


def normalize_ir_heading(text: str) -> str:
    # Preserve source elsewhere; this normalized form only aids retrieval.
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("Ex em ple", "Exemple").replace("M odèle", "Modèle")
    return text


def extract_ir_blocks(path: str | Path, document_id: str) -> dict:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    page = None
    article_ref = None
    heading_path = []
    current = None
    blocks = []

    def close():
        nonlocal current
        if not current:
            return
        current["text_source"] = "\n".join(current.pop("_body")).strip()
        current["page_end_pdf"] = current.pop("_last_page")
        blocks.append(current)
        current = None

    counters = {i: 0 for i in range(1,6)}
    for lineno, line in enumerate(lines, start=1):
        m = PAGE_RE.search(line)
        if m:
            page = int(m.group(1))
            if current:
                current["_last_page"] = page
            continue

        m = ARTICLE_RE.match(line)
        if m:
            close()
            article_ref = m.group(1)
            continue

        m = HEADING_RE.match(line)
        if m and not line.startswith("######"):
            level = len(m.group(1))
            heading_path = heading_path[:level-1] + [m.group(2).strip()]
            if current:
                current["_body"].append(line)
            continue

        m = IR_RE.match(line)
        if m:
            close()
            ir_type = int(m.group(1))
            heading = m.group(2).strip()
            counters[ir_type] += 1
            current = {
                "ir_id": f"pcg2026:ir{ir_type}:{counters[ir_type]:04d}",
                "ir_type": f"IR{ir_type}",
                "heading_source": heading,
                "heading_normalized": normalize_ir_heading(heading),
                "article_ref": article_ref,
                "document_id": document_id,
                "page_start_pdf": page,
                "_last_page": page,
                "source_line_md": lineno,
                "heading_path": list(heading_path),
                "_body": [],
            }
            continue

        if current:
            current["_body"].append(line)

    close()
    stats = {f"IR{i}": sum(b["ir_type"] == f"IR{i}" for b in blocks) for i in range(1,6)}
    stats["total"] = len(blocks)
    stats["linked_to_article"] = sum(bool(b["article_ref"]) for b in blocks)
    return {
        "standard_id": "fr-pcg",
        "edition": "2026",
        "dataset_layer": "doctrine_ir",
        "blocks": blocks,
        "statistics": stats,
    }
