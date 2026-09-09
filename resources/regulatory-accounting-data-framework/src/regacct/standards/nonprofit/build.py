from __future__ import annotations
from pathlib import Path

from ...io import dump_json, load_json
from ...framework.regulation.markdown import parse_articles, parse_ir_blocks
from ...framework.overlay.merge import classify_overlay, build_effective_plan
from ...framework.comparison.practitioner import compare_practitioner_reference
from ...framework.rag.bm25 import build_markdown_page_index
from .accounts import extract_anc_320_2, extract_orcom_plan
from .functioning import build_account_functioning
from .reporting import build_reporting
from .disclosures import build_disclosures


def build_all(project_root: str | Path = ".") -> dict:
    root = Path(project_root)
    src = root / "standards/fr-nonprofit/2026/sources"
    anc_md = src / "ANC_Recueil-non-lucratif_ONG_Associations_2026.md"
    orcom_md = src / "PCA_plan-comptable-associations_orcom_2025.md"

    base_pcg = load_json(root / "datasets/structured/pcg_2026_v1_structure.json")

    # Primary regulation scope = Tome I, ANC 2018-06.
    articles = parse_articles(
        anc_md,
        "fr-nonprofit-recueil-2026-md",
        start_contains="TOME I : Règlement ANC n° 2018-06",
        end_contains="TOME II : Règlements applicables",
    )
    dump_json(root / "datasets/annotated/nonprofit_2026_primary_article_registry.json", articles)

    doctrine = parse_ir_blocks(
        anc_md,
        "fr-nonprofit-recueil-2026-md",
        start_contains="TOME I : Règlement ANC n° 2018-06",
        end_contains="TOME II : Règlements applicables",
    )
    dump_json(root / "datasets/annotated/nonprofit_2026_doctrine_ir.json", doctrine)

    specific = extract_anc_320_2(anc_md)
    dump_json(root / "datasets/raw/nonprofit_2026_art_320_2_specific_accounts.json", specific)

    overlay = classify_overlay(base_pcg, specific["entries"])
    overlay_payload = {
        "standard_id": "fr-nonprofit",
        "edition": "2026",
        "base_standard": "fr-pcg:2026",
        "regulatory_basis": {
            "inheritance_article": "320-1",
            "specific_accounts_article": "320-2",
            "source_document_id": "fr-nonprofit-recueil-2026-md",
        },
        **overlay,
    }
    dump_json(root / "datasets/structured/nonprofit_2026_v1_account_overlay.json", overlay_payload)

    effective = build_effective_plan(base_pcg, specific["entries"], "fr-nonprofit", "2026")
    dump_json(root / "datasets/structured/nonprofit_2026_v1_effective_plan.json", effective)

    functioning = build_account_functioning(articles)
    dump_json(root / "datasets/annotated/nonprofit_2026_v2_account_functioning.json", functioning)

    disclosures = build_disclosures(articles)
    dump_json(root / "datasets/annotated/nonprofit_2026_disclosures.json", disclosures)

    reporting = build_reporting()
    dump_json(root / "datasets/reporting/nonprofit_2026_v3_reporting.json", reporting)

    rag = build_markdown_page_index(anc_md, "fr-nonprofit-recueil-2026-md")
    dump_json(root / "rag/indexes/nonprofit-recueil-2026-v1.json", rag)

    practitioner = extract_orcom_plan(orcom_md)
    dump_json(root / "datasets/raw/orcom_associations_2025_practitioner_plan.json", practitioner)

    comparison = compare_practitioner_reference(
        effective,
        practitioner["entries"],
        "orcom-associations-plan-2025-md",
    )
    comparison["temporal_warning"] = {
        "canonical_edition": "2026",
        "practitioner_reference_edition": "2025",
        "practitioner_reference_is_older": True,
    }
    dump_json(root / "validation/review/nonprofit_2026_orcom_comparison.json", comparison)

    build = {
        "standard_id": "fr-nonprofit",
        "edition": "2026",
        "base_standard": "fr-pcg:2026",
        "status": "built",
        "source_priority": [
            "ANC Recueil secteur non lucratif 2026 - regulatory primary",
            "ORCOM plan de comptes associations 2025 - practitioner secondary only",
        ],
        "outputs": {
            "articles": "datasets/annotated/nonprofit_2026_primary_article_registry.json",
            "doctrine_ir": "datasets/annotated/nonprofit_2026_doctrine_ir.json",
            "specific_accounts": "datasets/raw/nonprofit_2026_art_320_2_specific_accounts.json",
            "account_overlay": "datasets/structured/nonprofit_2026_v1_account_overlay.json",
            "effective_plan": "datasets/structured/nonprofit_2026_v1_effective_plan.json",
            "functioning": "datasets/annotated/nonprofit_2026_v2_account_functioning.json",
            "disclosures": "datasets/annotated/nonprofit_2026_disclosures.json",
            "reporting": "datasets/reporting/nonprofit_2026_v3_reporting.json",
            "rag": "rag/indexes/nonprofit-recueil-2026-v1.json",
            "orcom_plan": "datasets/raw/orcom_associations_2025_practitioner_plan.json",
            "orcom_comparison": "validation/review/nonprofit_2026_orcom_comparison.json",
        },
        "statistics": {
            "articles": articles["statistics"],
            "doctrine": doctrine["statistics"],
            "specific_accounts": specific["statistics"],
            "overlay": overlay_payload["statistics"],
            "effective_plan": effective["statistics"],
            "functioning": functioning["statistics"],
            "disclosures": disclosures["statistics"],
            "reporting": reporting["statistics"],
            "rag": rag["statistics"],
            "orcom": practitioner["statistics"],
            "orcom_comparison": comparison["statistics"],
        },
    }
    dump_json(root / "validation/review/nonprofit_2026_build_manifest.json", build)
    return build
