from pathlib import Path
from regacct.io import dump_json
from regacct.framework.rag.bm25 import build_markdown_page_index
from .plan import parse_plan_markdown,build_structure
from .guide import parse_toc,parse_applications
from .knowledge import build_accounting_knowledge,build_consolidation_registry
from .reporting import build_reporting

def build_all(project_root="."):
    root=Path(project_root);src=root/"standards/ohada-syscohada/2017/sources"
    plan=src/"OHADA-Plan-comptable-2017.md";guide=src/"Guide-d-application-du-SYSCOHADA.md"
    v0=parse_plan_markdown(plan);dump_json(root/"datasets/raw/syscohada_2017_v0_raw.json",v0)
    v1=build_structure(v0);dump_json(root/"datasets/structured/syscohada_2017_v1_structure.json",v1)
    toc=parse_toc(guide);dump_json(root/"datasets/annotated/syscohada_2017_guide_registry.json",toc)
    known={n["ref_code"] for n in v1["nodes"] if n["node_type"]!="class"}
    apps=parse_applications(guide,toc,known);dump_json(root/"datasets/annotated/syscohada_2017_applications.json",apps)
    v2=build_accounting_knowledge(toc,apps);dump_json(root/"datasets/annotated/syscohada_2017_v2_accounting_knowledge.json",v2)
    consolidation=build_consolidation_registry(apps);dump_json(root/"datasets/annotated/syscohada_2017_consolidation_registry.json",consolidation)
    v3=build_reporting();dump_json(root/"datasets/reporting/syscohada_2017_v3_reporting.json",v3)
    rag=build_markdown_page_index(guide,"syscohada-guide-2017-md");dump_json(root/"rag/indexes/syscohada-guide-2017-v2.json",rag)
    out={"standard_id":"ohada-syscohada","edition":"2017","status":"built",
         "outputs":{"v0":"datasets/raw/syscohada_2017_v0_raw.json","v1":"datasets/structured/syscohada_2017_v1_structure.json",
                    "guide_registry":"datasets/annotated/syscohada_2017_guide_registry.json","applications":"datasets/annotated/syscohada_2017_applications.json",
                    "v2":"datasets/annotated/syscohada_2017_v2_accounting_knowledge.json","consolidation":"datasets/annotated/syscohada_2017_consolidation_registry.json",
                    "v3":"datasets/reporting/syscohada_2017_v3_reporting.json","rag":"rag/indexes/syscohada-guide-2017-v2.json"},
         "statistics":{"v0":v0["statistics"],"v1":v1["statistics"],"guide":toc["statistics"],"applications":apps["statistics"],
                       "v2":v2["statistics"],"consolidation":consolidation["statistics"],"v3":v3["statistics"],"rag":rag["statistics"]}}
    dump_json(root/"validation/review/syscohada_2017_build_manifest.json",out);return out
