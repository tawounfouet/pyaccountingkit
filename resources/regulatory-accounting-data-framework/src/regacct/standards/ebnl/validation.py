def validate_v0(d):
    e=[];s=d["statistics"]
    expected={"classes":9,"class_scopes":2,"groups":84,"account_occurrences":1050,"unique_account_codes":1049,"duplicate_source_codes":1}
    for k,v in expected.items():
        if s.get(k)!=v:e.append(f"{k}:expected={v}:actual={s.get(k)}")
    if "4555" not in d["duplicate_source_codes"]:e.append("duplicate_4555_missing")
    if set(d["duplicate_source_codes"])!={"4555"}:e.append("unexpected_duplicate_codes")
    return e

def validate_v1(d):
    e=[];nodes=d["nodes"];by={n["node_id"]:n for n in nodes}
    if len(by)!=len(nodes):e.append("duplicate_node_id")
    if d["statistics"]["graph_nodes"]!=1145:e.append(f"graph_nodes:{d['statistics']['graph_nodes']}")
    if d["statistics"]["account_occurrence_nodes"]!=1050:e.append("account_nodes")
    if d["statistics"]["unique_account_codes"]!=1049:e.append("unique_codes")
    for n in nodes:
        p=n.get("parent_node_id")
        if p and p not in by:e.append(f"missing_parent:{n['node_id']}")
        if p==n["node_id"]:e.append(f"self_parent:{n['node_id']}")
        if n["depth"]!=len(n["path_node_ids"])-1:e.append(f"bad_depth:{n['node_id']}")
    return e

def validate_duplicate_4555(d):
    rows=[n for n in d["nodes"] if n["node_type"]=="account" and n["ref_code"]=="4555"]
    if len(rows)!=2:return ["4555_occurrence_count"]
    parents=set()
    by={n["node_id"]:n for n in d["nodes"]}
    for r in rows:parents.add(by[r["parent_node_id"]]["ref_code"])
    e=[]
    if parents!={"452","455"}:e.append(f"4555_parents:{parents}")
    if not any(r["attributes"]["non_prefix_source_parent"] for r in rows):e.append("4555_source_anomaly_not_preserved")
    return e

def validate_comparison(d):
    e=[];p=d["comparison_policy"]
    if p["inheritance_asserted"]:e.append("false_inheritance")
    if p["semantic_equivalence_from_code_equality"]:e.append("code_equality_semantic_equivalence")
    if p["automatic_crosswalk_approval"]:e.append("automatic_crosswalk")
    if not any(r["status"]=="ambiguous_ebnl_source_code" and r["ref_code"]=="4555" for r in d["rows"]):e.append("4555_comparison_ambiguity_missing")
    return e

def validate_gaps(d):
    e=[]
    for key in ("v2_account_functioning","v3_reporting","disclosures"):
        if not d["capabilities"][key]["status"].startswith("blocked_missing_normative_corpus"):
            e.append(f"{key}_should_be_blocked")
    return e


def validate_complete_source(d):
    e=[]
    if d.get("page_count")!=438:e.append(f"page_count:{d.get('page_count')}")
    if len(d.get("pages",[]))!=438:e.append("page_registry_length")
    if not d.get("extraction_policy",{}).get("pdf_visual_source_is_authority"):e.append("visual_authority_missing")
    if d.get("extraction_policy",{}).get("full_verbatim_ocr_claimed"):e.append("false_full_ocr_claim")
    return e


def validate_legal_registry(d):
    e=[]
    if d.get("statistics",{}).get("articles")!=28:e.append("article_count")
    nums=[x.get("article_number") for x in d.get("articles",[])]
    if nums!=list(range(1,29)):e.append("article_sequence")
    art4=next((x for x in d.get("articles",[]) if x.get("article_number")==4),None)
    if not art4 or len(art4.get("structured_facts",{}).get("association_order_complete_set",[]))!=4:e.append("article4_association_set")
    art6=next((x for x in d.get("articles",[]) if x.get("article_number")==6),None)
    if not art6 or art6.get("structured_facts",{}).get("sm_treasury_threshold_value")!=30000000:e.append("article6_threshold")
    art28=next((x for x in d.get("articles",[]) if x.get("article_number")==28),None)
    if not art28 or art28.get("structured_facts",{}).get("effective_from")!="2024-01-01":e.append("article28_effective_date")
    return e


def validate_conceptual_framework(d):
    e=[]
    if d.get("statistics",{}).get("postulates")!=5:e.append("postulates")
    if d.get("statistics",{}).get("conventions")!=5:e.append("conventions")
    if d.get("statistics",{}).get("qualitative_characteristics")!=6:e.append("qualitative_characteristics")
    terms={x.get("term_source") for x in d.get("definitions",[])}
    for term in ("Fonds affectés","Waqf","Zakat","Contribution volontaire en nature"):
        if term not in terms:e.append(f"definition_missing:{term}")
    return e


def validate_v2_complete(d):
    e=[]
    s=d.get("statistics",{})
    if s.get("group_bindings")!=84:e.append(f"group_bindings:{s.get('group_bindings')}")
    if s.get("missing_group_title_pages")!=[]:e.append(f"missing_titles:{s.get('missing_group_title_pages')}")
    if d.get("account_functioning_model",{}).get("executable_posting_rules_generated"):e.append("executable_rules_invented")
    by={x["group_code"]:x for x in d.get("group_bindings",[])}
    if by.get("10",{}).get("title_page_pdf")!=107:e.append("account10_page")
    if by.get("62",{}).get("title_page_pdf")!=243 or by.get("63",{}).get("title_page_pdf")!=243:e.append("62_63_shared_page")
    if by.get("90",{}).get("title_page_pdf")!=306 or by.get("92",{}).get("title_page_pdf")!=308:e.append("class9_pages")
    return e


def validate_specific_operations(d):
    e=[]
    rows=d.get("chapters",[])
    if len(rows)!=6:e.append("chapter_count")
    starts=[x.get("page_range",[None])[0] for x in rows]
    if starts!=[311,319,325,329,333,335]:e.append(f"chapter_starts:{starts}")
    if any(x.get("executable_rules_generated") for x in rows):e.append("specific_ops_executable_inference")
    return e


def validate_reporting_complete(d):
    e=[]
    profiles={p["profile_id"]:p for p in d.get("profiles",[])}
    if set(profiles)!={"association_professional_order","development_project","minimal_cash_system"}:e.append("profile_ids")
    if len(profiles.get("association_professional_order",{}).get("statements",[]))!=4:e.append("association_statements")
    if len(profiles.get("development_project",{}).get("statements",[]))!=6:e.append("project_statements")
    if len(profiles.get("minimal_cash_system",{}).get("statements",[]))!=3:e.append("smt_statements")
    thresholds=profiles.get("minimal_cash_system",{}).get("eligibility_thresholds",[])
    if len(thresholds)!=5 or any(x.get("value")!=30000000 for x in thresholds):e.append("smt_thresholds")
    if d.get("execution_policy",{}).get("automatic_filing_generation"):e.append("automatic_filing_should_be_false")
    return e


def validate_disclosures_complete(d):
    e=[]
    rows=d.get("profiles",[])
    if len(rows)!=3:e.append("disclosure_profiles")
    if any(x.get("field_level_requirements_exhaustively_transcribed") for x in rows):e.append("false_exhaustive_disclosure_claim")
    return e


def validate_capability_status(d):
    e=[]
    if not d.get("normative_source_gap_closed"):e.append("normative_source_gap_not_closed")
    caps=d.get("capabilities",{})
    for key in ("v2_account_functioning","v3_reporting","disclosures"):
        if not str(caps.get(key,{}).get("status","")).startswith("implemented"):
            e.append(f"{key}_not_implemented")
    if caps.get("v2_account_functioning",{}).get("invented_rules_allowed") is not False:e.append("v2_invention_guard")
    if caps.get("v3_reporting",{}).get("invented_templates_allowed") is not False:e.append("v3_invention_guard")
    if caps.get("full_verbatim_ocr",{}).get("status")!="not_claimed":e.append("ocr_non_claim")
    return e

# Backward-compatible validator name now validates the closed-gap status.
def validate_gaps(d):
    return validate_capability_status(d)
