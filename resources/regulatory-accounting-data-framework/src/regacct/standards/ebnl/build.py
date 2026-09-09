from pathlib import Path
from regacct.io import dump_json,load_json
from regacct.framework.rag.bm25 import build_markdown_page_index
from .plan import parse_plan_markdown,build_structure
from .comparison import compare_to_syscohada
from .complete import build_complete


def build_all(project_root="."):
    root=Path(project_root)
    src=root/"standards/ohada-ebnl/2023/sources"
    md=src/"PC-EBNL_Liste des comptes.md"
    ledger=root/"validation/review/ebnl_2023_visual_review_ledger.json"

    # V0/V1 remain anchored to the reviewed chart extract from release 0.7.0.
    v0=parse_plan_markdown(md,ledger)
    dump_json(root/"datasets/raw/ebnl_2023_v0_reviewed_structure.json",v0)

    v1=build_structure(v0)
    dump_json(root/"datasets/structured/ebnl_2023_v1_structure.json",v1)

    syscohada=load_json(root/"datasets/structured/syscohada_2017_v1_structure.json")
    comparison=compare_to_syscohada(v0,syscohada)
    dump_json(root/"datasets/crosswalk/ebnl_2023_vs_syscohada_2017_structural_delta.json",comparison)

    # Preserve the original chart OCR index as a secondary lookup artifact.
    chart_rag=build_markdown_page_index(md,"ohada-ebnl-plan-2023-md")
    chart_rag["source_quality_notice"]={
        "quality_status":"ocr_review_required",
        "use_for_authoritative_quote_without_pdf_check":False,
        "pdf_is_visual_authority":True,
        "role":"secondary_chart_extract_index",
    }
    dump_json(root/"rag/indexes/ebnl-plan-2023-ocr-v1.json",chart_rag)

    complete=build_complete(root)
    build={
        "standard_id":"ohada-ebnl","edition":"2023","release":"0.7.1",
        "status":"complete_official_normative_source_structured",
        "outputs":{
            "review_ledger":"validation/review/ebnl_2023_visual_review_ledger.json",
            "v0":"datasets/raw/ebnl_2023_v0_reviewed_structure.json",
            "v1":"datasets/structured/ebnl_2023_v1_structure.json",
            "legal_registry":"datasets/annotated/ebnl_2023_legal_act_registry.json",
            "conceptual_framework":"datasets/annotated/ebnl_2023_conceptual_framework.json",
            "v2":"datasets/annotated/ebnl_2023_v2_account_functioning.json",
            "specific_operations":"datasets/annotated/ebnl_2023_specific_operations.json",
            "v3":"datasets/reporting/ebnl_2023_v3_reporting.json",
            "disclosures":"datasets/annotated/ebnl_2023_disclosures_registry.json",
            "source_page_registry":"datasets/annotated/ebnl_2023_source_page_registry.json",
            "syscohada_delta":"datasets/crosswalk/ebnl_2023_vs_syscohada_2017_structural_delta.json",
            "capability_status":"validation/review/ebnl_2023_capability_status.json",
            "chart_ocr_rag":"rag/indexes/ebnl-plan-2023-ocr-v1.json",
            "full_source_router_rag":"rag/indexes/ebnl-sycebnl-2023-source-router-v2.json",
        },
        "statistics":{
            "v0":v0["statistics"],
            "v1":v1["statistics"],
            "legal":complete["legal"]["statistics"],
            "conceptual":complete["conceptual"]["statistics"],
            "v2":complete["v2"]["statistics"],
            "specific_operations":complete["specific"]["statistics"],
            "v3":complete["reporting"]["statistics"],
            "disclosures":complete["disclosures"]["statistics"],
            "source_pages":complete["page_registry"]["statistics"],
            "syscohada_delta":comparison["statistics"],
            "full_source_router_rag":complete["rag"]["statistics"],
        },
        "blocked_capabilities":[],
        "non_claims":[
            "No executable posting rule is inferred from narrative source guidance.",
            "No perfect verbatim OCR is claimed for image-heavy pages.",
            "Reporting template line items are source-page bound, not silently reconstructed when visual extraction is uncertain.",
        ],
    }
    dump_json(root/"validation/review/ebnl_2023_build_manifest.json",build)
    return build
