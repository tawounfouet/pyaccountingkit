from __future__ import annotations
from pathlib import Path
import re

PAGE_RE = re.compile(r"<!--\s*Page PDF\s+(\d+)\s*-->")
HEADING_RE = re.compile(r"^(#{1,5})\s+(.+?)\s*$")
ARTICLE_RE = re.compile(r"^######\s+Art\.\s+([0-9]+(?:-[0-9]+)?)(?:\s+(.+?))?\s*$")


def parse_articles(path: str | Path, document_id: str) -> dict:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    page = None
    heading_path = []
    articles = []
    current = None

    def close_current():
        nonlocal current
        if not current:
            return
        current["text_source"] = "\n".join(current.pop("_body")).strip()
        current["page_end_pdf"] = current.pop("_last_page")
        articles.append(current)
        current = None

    occurrence = {}
    for lineno, line in enumerate(lines, start=1):
        m = PAGE_RE.search(line)
        if m:
            page = int(m.group(1))
            if current:
                current["_last_page"] = page
            continue

        m = HEADING_RE.match(line)
        if m and not line.startswith("######"):
            level = len(m.group(1))
            title = m.group(2).strip()
            heading_path = heading_path[:level-1] + [title]
            if current:
                current["_body"].append(line)
            continue

        m = ARTICLE_RE.match(line)
        if m:
            close_current()
            ref, inline_title = m.group(1), (m.group(2) or "").strip()
            occurrence[ref] = occurrence.get(ref, 0) + 1
            article_id = f"{document_id}:article:{ref}"
            if occurrence[ref] > 1:
                article_id += f":occ{occurrence[ref]}"
            current = {
                "article_id": article_id,
                "article_ref": ref,
                "title_source": inline_title or None,
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

    close_current()
    return {
        "document_id": document_id,
        "articles": articles,
        "statistics": {
            "articles": len(articles),
            "unique_article_refs": len({a["article_ref"] for a in articles}),
        },
    }


def extract_titre_xii_annotations(article_registry: dict, known_account_codes: set[str], code_to_node_id: dict[str,str]) -> dict:
    annotations = []
    general_scope = {
        "1212": ("class", "2"),
        "1213": ("class", "3"),
        "1214": ("class", "4"),
        "1221": ("class", "6"),
        "1222": ("class", "7"),
    }

    for art in article_registry["articles"]:
        hp = " / ".join(art.get("heading_path") or [])
        if "Titre XII" not in hp and "TITRE XII" not in hp.upper():
            continue
        text = art["text_source"]
        first_text_line = next(
            (ln.strip() for ln in text.splitlines()
             if ln.strip() and not ln.strip().startswith("<!--")),
            ""
        )
        m_scope = re.match(r"^(\d{2})\s*:\s*(.+)$", first_text_line)

        scope_type = "regulatory_section"
        scope_refs = []
        scope_node_ids = []
        heading_source = first_text_line or art.get("title_source")

        if m_scope:
            scope_type = "account_family"
            code = m_scope.group(1)
            scope_refs = [code]
            if code in code_to_node_id:
                scope_node_ids = [code_to_node_id[code]]
        elif art["article_ref"] in general_scope:
            scope_type, code = general_scope[art["article_ref"]]
            scope_refs = [code]
            class_node = f"class:fr-pcg:2026:{code}"
            scope_node_ids = [class_node]
        else:
            # Class 8 account articles are account-specific, e.g. 1231-80.
            m_code = re.match(r"^(\d{2})\s*:", first_text_line)
            if m_code:
                code = m_code.group(1)
                scope_type = "account_family"
                scope_refs = [code]
                if code in code_to_node_id:
                    scope_node_ids = [code_to_node_id[code]]

        # Only references that are actual known PCG codes.
        mentions = []
        for token in re.findall(r"\b[1-8][0-9]{1,4}\b", text):
            if token in known_account_codes and token not in mentions:
                mentions.append(token)

        evidence = []
        for paragraph in re.split(r"\n\s*\n|(?<=[.;:])\s+(?=[A-ZÀ-ÖØ-Ý])", text):
            norm = " ".join(paragraph.split())
            if not norm:
                continue
            low = norm.lower()
            if any(k in low for k in (" débité", " crédité", " au débit", " au crédit", "solde débiteur", "solde créditeur")):
                evidence.append(norm)

        annotations.append({
            "annotation_id": f"pcg2026:account-functioning:{art['article_ref']}",
            "article_ref": art["article_ref"],
            "scope_type": scope_type,
            "scope_refs": scope_refs,
            "scope_node_ids": scope_node_ids,
            "heading_source": heading_source,
            "account_mentions": mentions,
            "posting_guidance_evidence": evidence,
            "source_range": {
                "document_id": art["document_id"],
                "page_start_pdf": art["page_start_pdf"],
                "page_end_pdf": art["page_end_pdf"],
                "source_line_md": art["source_line_md"],
                "heading_path": art["heading_path"],
            },
            "text_source": text,
            "provenance": {
                "type": "source",
                "method": "titre_xii_article_extraction",
                "source_refs": [{
                    "document_id": art["document_id"],
                    "page_pdf": art["page_start_pdf"],
                    "section": f"Art. {art['article_ref']}",
                    "heading_path": art["heading_path"],
                    "snippet": first_text_line[:400] if first_text_line else None,
                }],
                "confidence": 1.0,
                "review_status": "official_source",
            },
            "executable_rules_generated": False,
            "semantic_inference": False,
        })

    return {
        "standard_id": "fr-pcg",
        "edition": "2026",
        "dataset_layer": "v2_account_functioning",
        "annotations": annotations,
        "statistics": {
            "annotations": len(annotations),
            "with_account_family_scope": sum(a["scope_type"] == "account_family" for a in annotations),
            "with_class_scope": sum(a["scope_type"] == "class" for a in annotations),
            "debit_credit_evidence_fragments": sum(len(a["posting_guidance_evidence"]) for a in annotations),
        },
    }
