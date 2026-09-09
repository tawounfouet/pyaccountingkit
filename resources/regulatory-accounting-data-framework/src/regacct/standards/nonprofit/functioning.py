from __future__ import annotations


ACCOUNT_FUNCTIONING_ARTICLES = {
    "331-1": ["102"],
    "331-2": ["1021"],
    "331-3": ["1068"],
    "331-4": ["1631"],
    "332-1": ["2742"],
    "333-1": ["41"],
    "333-2": ["455"],
}


def build_account_functioning(article_registry: dict) -> dict:
    by_ref = {}
    for article in article_registry["articles"]:
        by_ref.setdefault(article["article_ref"], []).append(article)

    annotations = []
    for ref, accounts in ACCOUNT_FUNCTIONING_ARTICLES.items():
        occurrences = by_ref.get(ref, [])
        if not occurrences:
            continue
        article = occurrences[0]
        annotations.append({
            "annotation_id": f"fr-nonprofit:2026:functioning:{ref}",
            "article_ref": ref,
            "account_refs": accounts,
            "text_source": article["text_source"],
            "source_range": {
                "document_id": article["document_id"],
                "page_start_pdf": article["page_start_pdf"],
                "page_end_pdf": article["page_end_pdf"],
                "heading_path": article["heading_path"],
                "source_line_md": article["source_line_md"],
            },
            "provenance": {
                "type": "source",
                "review_status": "official_source",
                "confidence": 1.0,
            },
            "executable_rules_generated": False,
        })

    return {
        "standard_id": "fr-nonprofit",
        "edition": "2026",
        "dataset_layer": "v2_account_functioning",
        "annotations": annotations,
        "statistics": {
            "annotations": len(annotations),
            "account_refs_covered": len({a for x in annotations for a in x["account_refs"]}),
        },
    }
