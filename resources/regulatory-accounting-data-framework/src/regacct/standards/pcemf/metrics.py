from __future__ import annotations
from collections import Counter
from typing import Any


def _list_at(data: Any, *keys: str) -> list:
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def _dict_at(data: Any, *keys: str) -> dict:
    if not isinstance(data, dict):
        return {}
    for key in keys:
        value = data.get(key)
        if isinstance(value, dict):
            return value
    return {}


def measure_v0(data: Any) -> dict[str, int]:
    rows = _list_at(data, "records", "entries", "source_entries", "accounts")
    grouped = 0
    for row in rows:
        code = str(row.get("code_source") or row.get("source_code") or row.get("code") or "")
        if "/" in code:
            grouped += 1
    return {"source_entries": len(rows), "grouped_entries": grouped}


def measure_v1(data: Any) -> dict[str, int]:
    nodes = _list_at(data, "nodes", "graph_nodes")
    if not nodes:
        accounts = _list_at(data, "accounts", "account_nodes")
        classes = _list_at(data, "classes", "class_nodes")
        nodes = accounts + classes

    def node_type(n):
        return str(n.get("node_type") or n.get("type") or "").lower()

    class_nodes = [n for n in nodes if node_type(n) in {"class", "account_class", "class_node"}]
    account_nodes = [n for n in nodes if n not in class_nodes]
    depths = Counter(int(n.get("depth", -1)) for n in account_nodes if isinstance(n.get("depth"), int))
    codes = [str(n.get("ref_code") or n.get("account_code") or n.get("code") or "")
             for n in account_nodes]
    ids = {str(n.get("node_id") or n.get("id") or "") for n in nodes}
    missing_parents = sum(
        1 for n in nodes
        if n.get("parent_node_id") and str(n.get("parent_node_id")) not in ids
    )
    self_refs = sum(
        1 for n in nodes
        if n.get("parent_node_id") and n.get("parent_node_id") == n.get("node_id")
    )
    return {
        "account_nodes": len(account_nodes),
        "class_nodes": len(class_nodes),
        "graph_nodes": len(nodes),
        "unique_atomic_codes": len({c for c in codes if c}),
        "depth_1": depths.get(1, 0),
        "depth_2": depths.get(2, 0),
        "depth_3": depths.get(3, 0),
        "depth_4": depths.get(4, 0),
        "self_references": self_refs,
        "missing_parents": missing_parents,
    }


def measure_v2(data: Any, anomaly_data: Any = None) -> dict[str, int]:
    annotations = _list_at(data, "annotations", "records", "sections")
    covered = set()
    grouped = 0
    shared = 0
    for ann in annotations:
        refs = ann.get("account_refs") or ann.get("source_account_codes") or []
        if refs and isinstance(refs[0] if isinstance(refs, list) and refs else None, dict):
            covered.update(str(r.get("account_code")) for r in refs if r.get("account_code"))
        elif isinstance(refs, list):
            covered.update(str(x) for x in refs)
        if len(refs) > 1:
            grouped += 1
        fields = ann.get("fields") or {}
        modes = [v.get("mode") for v in fields.values() if isinstance(v, dict)]
        if "shared_debit_credit" in modes:
            shared += 1
    observations = len(_list_at(anomaly_data or {}, "observations", "items", "anomalies"))
    return {
        "annotations": len(annotations),
        "covered_top_level_accounts": len(covered),
        "grouped_annotation_sections": grouped,
        "shared_debit_credit_sections": shared,
        "observations": observations,
    }


def measure_v3(data: Any, anomaly_data: Any = None) -> dict[str, int]:
    statements = _list_at(data, "statements", "statement_templates")
    all_lines = []
    direct_mapped = 0
    parsed_components = 0
    trial = 0
    combo = 0
    for st in statements:
        mode = str(st.get("mode") or st.get("statement_type") or "").lower()
        if "comb" in mode:
            combo += 1
        else:
            trial += 1
        lines = st.get("lines") or st.get("statement_lines") or []
        all_lines.extend(lines)
        for line in lines:
            if line.get("direct_mapping") or line.get("mapping_components"):
                direct_mapped += 1
            for comp in line.get("mapping_components") or []:
                mapping = comp.get("mapping") if isinstance(comp, dict) else None
                if isinstance(mapping, dict) and mapping.get("parse_status") == "parsed":
                    parsed_components += 1
    reverse = _dict_at(data, "account_to_statement_lines", "reverse_index")
    observations = len(_list_at(anomaly_data or {}, "observations", "items", "anomalies"))
    return {
        "statement_templates": len(statements),
        "trial_balance_statements": trial,
        "combination_statements": combo,
        "statement_lines": len(all_lines),
        "direct_mapped_lines": direct_mapped,
        "parsed_mapping_components": parsed_components,
        "leaf_accounts_reverse_indexed": len(reverse),
        "observations": observations,
    }


def measure_v4(data: Any, anomaly_data: Any = None) -> dict[str, int]:
    rules = _list_at(data, "rules", "prudential_rules")
    components = formulas = thresholds = with_selectors = 0
    refs = set()
    for rule in rules:
        ref = rule.get("regulation_reference") or rule.get("regulation")
        if ref:
            refs.add(str(ref))
        comps = rule.get("components") or []
        components += len(comps)
        with_selectors += sum(
            1 for c in comps
            if c.get("account_selectors") or c.get("mapping") or c.get("selectors")
        )
        formulas += len(rule.get("formulas") or [])
        thresholds += len(rule.get("thresholds") or [])
    observations = len(_list_at(anomaly_data or {}, "observations", "items", "anomalies"))
    return {
        "prudential_rules": len(rules),
        "regulation_references": len(refs),
        "components": components,
        "components_with_account_selectors": with_selectors,
        "formulas": formulas,
        "thresholds": thresholds,
        "observations": observations,
    }


def measure_v5(data: Any, *, rag_data: Any = None, approved_data: Any = None) -> dict[str, int]:
    groups = _list_at(data, "candidate_groups", "groups")
    candidates = _list_at(data, "candidates", "candidate_mappings")
    if groups and not candidates:
        candidates = [c for g in groups for c in (g.get("candidates") or [])]
    chunks = _list_at(rag_data or {}, "chunks")
    terms = _dict_at(rag_data or {}, "terms", "inverted_index", "vocabulary")
    approved = _list_at(approved_data or {}, "mappings", "approved", "records")
    same_code_used = sum(1 for c in candidates if c.get("code_equality_used_in_score") is True)
    pcemf_accounts = len(groups) if groups else len({c.get("source_node_id") for c in candidates if c.get("source_node_id")})
    return {
        "guide_chunks": len(chunks),
        "guide_terms": len(terms),
        "candidate_groups": len(groups) or pcemf_accounts,
        "candidate_mappings": len(candidates),
        "approved_mappings": len(approved),
        "same_code_used_in_score": same_code_used,
    }


def measure_v6(data: Any) -> dict[str, int]:
    return {
        "business_tags": len(_list_at(data, "tags", "business_tags")),
        "account_links": len(_list_at(data, "account_links", "links")),
        "products": len(_list_at(data, "products", "business_products")),
        "fee_models": len(_list_at(data, "fee_models", "fees", "fees_commissions")),
        "events": len(_list_at(data, "events", "accounting_events")),
        "posting_rule_models": len(_list_at(data, "posting_rule_models", "posting_models")),
        "executable_posting_rules": sum(
            1 for x in _list_at(data, "posting_rule_models", "posting_models")
            if x.get("executable") is True
        ),
        "control_rules": len(_list_at(data, "control_rules", "controls")),
        "business_scenarios": len(_list_at(data, "business_scenarios", "scenarios")),
    }
