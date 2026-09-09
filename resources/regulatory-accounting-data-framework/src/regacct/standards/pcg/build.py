from __future__ import annotations
from pathlib import Path
import json

from ...io import dump_json
from .plan import parse_plan_markdown, build_structure
from .articles import parse_articles, extract_titre_xii_annotations
from .doctrine import extract_ir_blocks
from .reporting import build_reporting_dataset
from ...framework.rag.bm25 import build_markdown_page_index


def build_all(project_root: str | Path = ".") -> dict:
    root = Path(project_root)
    sources = root / "standards/fr-pcg/2026/sources"

    plan_md = sources / "Plan-de-comptes_PCG-2026.md"
    regulation_md = sources / "PCG_2026_Reglement_ANC_2014-03_Version_Consolidee.md"
    recueil_md = sources / "Recueil_Normes_Comptables_Francaises_PCG_2026_Entreprises_Industrielles_Commerciales.md"

    v0 = parse_plan_markdown(plan_md)
    dump_json(root/"datasets/raw/pcg_2026_v0_raw.json", v0)

    v1 = build_structure(v0)
    dump_json(root/"datasets/structured/pcg_2026_v1_structure.json", v1)

    article_registry = parse_articles(regulation_md, "fr-pcg-regulation-2026-md")
    dump_json(root/"datasets/annotated/pcg_2026_article_registry.json", article_registry)

    known_codes = {
        n["ref_code"] for n in v1["nodes"]
        if n["node_type"] in {"group","account"}
    }
    code_to_node = {
        n["ref_code"]: n["node_id"] for n in v1["nodes"]
        if n["node_type"] in {"group","account"}
    }
    v2 = extract_titre_xii_annotations(article_registry, known_codes, code_to_node)
    dump_json(root/"datasets/annotated/pcg_2026_v2_account_functioning.json", v2)

    doctrine = extract_ir_blocks(recueil_md, "fr-pcg-recueil-2026-md")
    dump_json(root/"datasets/annotated/pcg_2026_doctrine_ir.json", doctrine)

    rag = build_markdown_page_index(recueil_md, "fr-pcg-recueil-2026-md")
    dump_json(root/"rag/indexes/pcg-recueil-2026-v1.json", rag)

    reporting = build_reporting_dataset(known_codes)
    dump_json(root/"datasets/reporting/pcg_2026_v3_reporting.json", reporting)

    build = {
        "standard_id":"fr-pcg",
        "edition":"2026",
        "status":"built",
        "outputs":{
            "v0":"datasets/raw/pcg_2026_v0_raw.json",
            "v1":"datasets/structured/pcg_2026_v1_structure.json",
            "article_registry":"datasets/annotated/pcg_2026_article_registry.json",
            "v2":"datasets/annotated/pcg_2026_v2_account_functioning.json",
            "doctrine_ir":"datasets/annotated/pcg_2026_doctrine_ir.json",
            "rag":"rag/indexes/pcg-recueil-2026-v1.json",
            "v3_reporting":"datasets/reporting/pcg_2026_v3_reporting.json",
        },
        "statistics":{
            "v0":v0["statistics"],
            "v1":v1["statistics"],
            "articles":article_registry["statistics"],
            "v2":v2["statistics"],
            "doctrine":doctrine["statistics"],
            "rag":rag["statistics"],
            "reporting":reporting["statistics"],
        },
    }
    dump_json(root/"validation/review/pcg_2026_build_manifest.json", build)
    return build
