import unicodedata,re
from collections import Counter,defaultdict

def norm(s):
    s=unicodedata.normalize("NFKD",s or "")
    s="".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()

def compare_to_syscohada(ebnl_v0, syscohada_v1):
    e_by=defaultdict(list)
    for r in ebnl_v0["records"]: e_by[r["code_source"]].append(r)
    s_by={
        n["ref_code"]:n for n in syscohada_v1["nodes"]
        if n["node_type"] in {"group","account"}
    }

    rows=[]
    for code in sorted(set(e_by)|set(s_by),key=lambda x:(int(x[0]),len(x),x)):
        erows=e_by.get(code,[])
        s=s_by.get(code)
        if len(erows)>1:
            status="ambiguous_ebnl_source_code"
        elif erows and not s:
            status="ebnl_only_code"
        elif s and not erows:
            status="syscohada_only_code"
        else:
            e=erows[0]
            status="same_code_same_normalized_label" if norm(e["label_source"])==norm(s["label_source"]) else "same_code_label_variation"
        rows.append({
            "ref_code":code,
            "status":status,
            "ebnl_occurrences":[
                {"record_id":r["record_id"],"label_source":r["label_source"],"source_group_context":r["source_group_context"],"page_pdf":r["page_pdf"]}
                for r in erows
            ],
            "syscohada_label":s["label_source"] if s else None,
            "semantic_equivalence_asserted":False,
            "human_review_required":True if status!="same_code_same_normalized_label" else False,
        })

    return {
        "comparison_id":"ohada-ebnl-2023_vs_syscohada-2017_code_delta",
        "subject_standard":"ohada-ebnl:2023",
        "target_standard":"ohada-syscohada:2017",
        "comparison_policy":{
            "relation_type":"structural_code_delta",
            "inheritance_asserted":False,
            "semantic_equivalence_from_code_equality":False,
            "automatic_crosswalk_approval":False,
            "human_review_required_for_semantics":True,
            "note":"This is a structural comparison, not a regulatory inheritance or semantic crosswalk."
        },
        "rows":rows,
        "statistics":dict(sorted(Counter(r["status"] for r in rows).items())),
    }
