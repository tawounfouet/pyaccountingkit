from __future__ import annotations
from pathlib import Path
import re

PAGE_RE = re.compile(r"<!--\s*Page PDF\s+(\d+)\s*-->")
ACCOUNT_RE = re.compile(r"^\s*([1-8][0-9]{1,5})\s*[-–]\s*(.+?)\s*$")
ORCOM_ACCOUNT_RE = re.compile(r"^\s*(?:-\s+\*\*)?([1-8][0-9]{1,5})(?:\*\*)?\s*[-–]\s*(.+?)\s*$")
CLASS_RE = re.compile(r"^##\s+Classe\s+([1-8])\s*:", re.I)


def extract_anc_320_2(path: str | Path) -> dict:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    start = next(i for i,l in enumerate(lines) if "Art. 320-2" in l)
    end = next(i for i in range(start+1, len(lines)) if "Titre III" in lines[i] and "Fonctionnement des comptes" in lines[i])

    page = None
    entries = []
    for lineno in range(start, end):
        line = lines[lineno]
        m_page = PAGE_RE.search(line)
        if m_page:
            page = int(m_page.group(1))
            continue
        m = ACCOUNT_RE.match(line)
        if not m:
            continue
        code, label = m.groups()
        entries.append({
            "entry_id": f"fr-nonprofit:2026:art320-2:{code}",
            "standard_id": "fr-nonprofit",
            "edition": "2026",
            "base_standard": "fr-pcg:2026",
            "code": code,
            "label_source": label.strip(),
            "source_ref": {
                "document_id": "fr-nonprofit-recueil-2026-md",
                "page_pdf": page,
                "section": "Art. 320-2",
                "source_line_md": lineno + 1,
                "snippet": line.strip(),
            },
        })
    return {
        "article_ref": "320-2",
        "entries": entries,
        "statistics": {
            "entries": len(entries),
            "unique_codes": len({x["code"] for x in entries}),
        },
    }


def extract_orcom_plan(path: str | Path) -> dict:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    page = None
    current_class = None
    entries = []
    for lineno, line in enumerate(lines, start=1):
        m_page = PAGE_RE.search(line)
        if m_page:
            page = int(m_page.group(1))
            continue
        m_class = CLASS_RE.match(line)
        if m_class:
            current_class = int(m_class.group(1))
            continue
        m = ORCOM_ACCOUNT_RE.match(line.replace("–", "-"))
        if not m:
            # The generated Markdown can also retain plain account lines.
            m = ACCOUNT_RE.match(line)
        if not m:
            continue
        code, label = m.groups()
        entries.append({
            "occurrence_id": f"orcom-2025:p{page or 0:03d}:l{lineno:04d}:{code}",
            "code": code,
            "label_source": label.strip().strip("*"),
            "class_number": current_class or int(code[0]),
            "source_ref": {
                "document_id": "orcom-associations-plan-2025-md",
                "page_pdf": page,
                "source_line_md": lineno,
                "snippet": line.strip(),
            },
            "source_role": "external_practitioner_reference",
        })
    return {
        "document_id": "orcom-associations-plan-2025-md",
        "entries": entries,
        "statistics": {
            "occurrences": len(entries),
            "unique_codes": len({x["code"] for x in entries}),
        },
    }
