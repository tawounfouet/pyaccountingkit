EXPECTED={"classes":9,"source_entries":1403,"groups":85,"main_accounts":432,"sub_accounts":886,"unique_codes":1403}
def validate_v0(d):
    return [f"{k}:{d['statistics'].get(k)}" for k,v in EXPECTED.items() if d["statistics"].get(k)!=v]
def validate_v1(d):
    e=[];nodes=d["nodes"];by={n["node_id"]:n for n in nodes}
    if len(by)!=len(nodes):e.append("duplicate_node_ids")
    for n in nodes:
        p=n.get("parent_node_id")
        if p and p not in by:e.append(f"missing_parent:{n['node_id']}")
        if p==n["node_id"]:e.append(f"self_reference:{n['node_id']}")
        if n["depth"]!=len(n["path_node_ids"])-1:e.append(f"depth:{n['node_id']}")
    if d["statistics"]["account_nodes"]!=1403:e.append("account_nodes")
    if d["statistics"]["class_nodes"]!=9:e.append("class_nodes")
    return e
def validate_guide(toc,apps):
    e=[];exp={"parts":4,"chapters":56,"sections":33,"applications":142}
    for k,v in exp.items():
        if toc["statistics"].get(k)!=v:e.append(f"toc_{k}")
    nums=[a["application_number"] for a in apps["applications"]]
    if nums!=list(range(1,143)):e.append("application_sequence")
    return e
def validate_v2(d):
    e=[]
    if d["statistics"]["applications"]!=142:e.append("applications")
    if d["knowledge_policy"]["executable_rules_generated"]:e.append("executable")
    if d["knowledge_policy"]["application_examples_are_regulatory_posting_rules"]:e.append("examples_promoted")
    return e
def validate_v3(d):
    e=[];s=d["statistics"];exp={"statement_types":4,"balance_model_lines":48,"income_model_lines":34,"cashflow_model_lines":23,"notes":46}
    for k,v in exp.items():
        if s.get(k)!=v:e.append(k)
    if d["source_scope"]["official_exhaustive_post_account_correspondence_table_available_in_bundle"]:e.append("invented_mapping")
    if not any(o["type"]=="duplicate_source_ref_code" and "ZF" in o["source_ref_codes"] for o in d["observations"]):e.append("ZF")
    return e
