from pathlib import Path
import json
from regacct.config import load_manifest
from regacct.families.registry import FamilyRegistry
from regacct.io import sha256_file, dump_json
from regacct.models import StandardRelation
from regacct.framework.validation.relations import validate_no_unproven_inheritance, validate_no_false_ohada_inheritance, validate_concept_bindings

MEMBERS=(("ohada-syscohada","2017"),("ohada-ebnl","2023"),("cemac-pcemf","2010"))

def build_foundation(project_root="."):
    root=Path(project_root)
    family=FamilyRegistry(root/"families").get("ohada-accounting")
    manifests=[]; sources=[]
    for sid,ed in MEMBERS:
        m=load_manifest(root/"standards"/sid/ed/"manifest.yaml"); manifests.append(m)
        for a in m.source_documents:
            p=root/"standards"/sid/ed/a.relative_path
            sources.append({"standard_ref":f"{sid}:{ed}","document_id":a.document_id,"canonical_eligibility":a.canonical_eligibility,"quality_status":a.quality_status,"sha256_verified":p.exists() and sha256_file(p)==a.sha256})
    rel_data=json.loads((root/"datasets/relations/ohada_accounting_standard_relations.json").read_text(encoding="utf-8"))
    rels=[StandardRelation.model_validate(x) for x in rel_data["relations"]]
    concepts=json.loads((root/"datasets/concepts/accounting_core_concepts_v0.json").read_text(encoding="utf-8"))
    result={
        "release":"0.5.0",
        "family":family.model_dump(mode="json"),
        "members":[{"standard_ref":f"{m.standard_id}:{m.edition}","authority":m.authority,"jurisdiction":m.jurisdiction,"standard_role":m.standard_role,"canonical_status":m.canonical_status,"source_documents":len(m.source_documents)} for m in manifests],
        "statistics":{
            "family_members":len(manifests),"source_documents":len(sources),"source_hashes_verified":sum(x["sha256_verified"] for x in sources),
            "canonical_blocked_sources":sum(not x["canonical_eligibility"] for x in sources),"relations":len(rels),
            "inheritance_relations":sum(x.relation_type.value=="inherits" for x in rels),"crosswalk_relations":sum(x.relation_type.value=="crosswalk" for x in rels),
            "neutral_concepts":len(concepts["concepts"]),"concept_bindings":len(concepts["bindings"])
        },
        "validation":{
            "inheritance":validate_no_unproven_inheritance(rels),
            "ohada_temporal_guards":validate_no_false_ohada_inheritance(rels),
            "concept_bindings":validate_concept_bindings(concepts["bindings"]),
            "source_hashes":[x["document_id"] for x in sources if not x["sha256_verified"]],
        }
    }
    result["status"]="ok" if not any(result["validation"].values()) else "failed"
    dump_json(root/"validation/review/ohada_family_foundation_build.json",result)
    return result
