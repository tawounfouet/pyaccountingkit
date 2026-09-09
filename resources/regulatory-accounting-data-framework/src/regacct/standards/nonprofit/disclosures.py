from __future__ import annotations


def build_disclosures(article_registry: dict) -> dict:
    requirements = []
    for article in article_registry["articles"]:
        ref = article["article_ref"]
        if not (ref.startswith("431-") or ref.startswith("432-")):
            continue
        requirements.append({
            "requirement_id": f"fr-nonprofit:2026:disclosure:{ref}:{article['article_id'].split(':')[-1]}",
            "article_ref": ref,
            "title_source": article.get("title_source"),
            "text_source": article["text_source"],
            "source": {
                "document_id": article["document_id"],
                "page_start_pdf": article["page_start_pdf"],
                "page_end_pdf": article["page_end_pdf"],
                "heading_path": article["heading_path"],
            },
            "requirement_type": (
                "public_generosity"
                if ref.startswith("432-")
                else "general_annex"
            ),
            "provenance_type": "official_source",
        })
    return {
        "standard_id": "fr-nonprofit",
        "edition": "2026",
        "dataset_layer": "disclosures",
        "requirements": requirements,
        "statistics": {
            "requirements": len(requirements),
            "general_annex": sum(x["requirement_type"] == "general_annex" for x in requirements),
            "public_generosity": sum(x["requirement_type"] == "public_generosity" for x in requirements),
        },
    }
