from __future__ import annotations
from pathlib import Path
import re

PAGE_RE = re.compile(r"<!--\s*Page PDF\s+(\d+)\s*-->")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ARTICLE_RE = re.compile(r"^######\s+(?:Art\.|Article)\s+([0-9]+(?:[-.][0-9A-Za-z]+)*)(?:\s*[-–:]?\s*(.*))?$", re.I)
IR_RE = re.compile(r"^\*\*IR\s*([1-5])\s*[-–:]\s*(.+?)\*\*\s*$", re.I)


def slice_lines(path: str | Path, start_contains: str | None = None, end_contains: str | None = None) -> list[tuple[int,str]]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    start = 0
    end = len(lines)
    if start_contains:
        for i, line in enumerate(lines):
            if start_contains.lower() in line.lower():
                start = i
                break
    if end_contains:
        for i in range(start + 1, len(lines)):
            if end_contains.lower() in lines[i].lower():
                end = i
                break
    return [(i + 1, lines[i]) for i in range(start, end)]


def parse_articles(
    path: str | Path,
    document_id: str,
    *,
    start_contains: str | None = None,
    end_contains: str | None = None,
) -> dict:
    lines = slice_lines(path, start_contains, end_contains)
    page = None
    heading_path: list[str] = []
    articles = []
    current = None
    occurrences = {}

    def close():
        nonlocal current
        if current is None:
            return
        current["text_source"] = "\n".join(current.pop("_body")).strip()
        current["page_end_pdf"] = current.pop("_last_page")
        articles.append(current)
        current = None

    for lineno, line in lines:
        m = PAGE_RE.search(line)
        if m:
            page = int(m.group(1))
            if current:
                current["_last_page"] = page
            continue

        m = HEADING_RE.match(line)
        if m and not line.startswith("######"):
            level = len(m.group(1))
            heading_path = heading_path[:level-1] + [m.group(2).strip()]
            if current:
                current["_body"].append(line)
            continue

        m = ARTICLE_RE.match(line)
        if m:
            close()
            ref = m.group(1)
            occurrences[ref] = occurrences.get(ref, 0) + 1
            current = {
                "article_id": f"{document_id}:article:{ref}:occ{occurrences[ref]:02d}",
                "article_ref": ref,
                "title_source": (m.group(2) or "").strip() or None,
                "document_id": document_id,
                "page_start_pdf": page,
                "_last_page": page,
                "heading_path": list(heading_path),
                "source_line_md": lineno,
                "_body": [],
            }
            continue

        if current:
            current["_body"].append(line)

    close()
    return {
        "document_id": document_id,
        "articles": articles,
        "statistics": {
            "articles": len(articles),
            "unique_article_refs": len({a["article_ref"] for a in articles}),
        },
    }


def parse_ir_blocks(
    path: str | Path,
    document_id: str,
    *,
    start_contains: str | None = None,
    end_contains: str | None = None,
) -> dict:
    lines = slice_lines(path, start_contains, end_contains)
    page = None
    heading_path: list[str] = []
    current_article = None
    current = None
    blocks = []
    counters = {i: 0 for i in range(1, 6)}

    def close():
        nonlocal current
        if current is None:
            return
        current["text_source"] = "\n".join(current.pop("_body")).strip()
        current["page_end_pdf"] = current.pop("_last_page")
        blocks.append(current)
        current = None

    for lineno, line in lines:
        m = PAGE_RE.search(line)
        if m:
            page = int(m.group(1))
            if current:
                current["_last_page"] = page
            continue

        m = ARTICLE_RE.match(line)
        if m:
            close()
            current_article = m.group(1)
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
            counters[ir_type] += 1
            current = {
                "ir_id": f"{document_id}:IR{ir_type}:{counters[ir_type]:04d}",
                "ir_type": f"IR{ir_type}",
                "heading_source": m.group(2).strip(),
                "article_ref": current_article,
                "document_id": document_id,
                "page_start_pdf": page,
                "_last_page": page,
                "heading_path": list(heading_path),
                "source_line_md": lineno,
                "_body": [],
            }
            continue

        if current:
            current["_body"].append(line)

    close()
    stats = {f"IR{i}": sum(x["ir_type"] == f"IR{i}" for x in blocks) for i in range(1,6)}
    stats["total"] = len(blocks)
    stats["linked_to_article"] = sum(bool(x["article_ref"]) for x in blocks)
    return {
        "document_id": document_id,
        "blocks": blocks,
        "statistics": stats,
    }
