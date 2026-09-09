from __future__ import annotations
from collections import Counter


EXPECTED_PLAN = {
    "classes": 7,
    "groups": 61,
    "accounts": 768,
    "account_ranges": 1,
    "optional_account_entries": 403,
    "records_total": 837,
}


def validate_v0(v0: dict) -> list[str]:
    errors = []
    for key, expected in EXPECTED_PLAN.items():
        actual = v0["statistics"].get(key)
        if actual != expected:
            errors.append(f"{key}: expected={expected} actual={actual}")
    # Source codes must never be right-padded into identity.
    for r in v0["records"]:
        if r["record_type"] in {"group","group_bundle","account"}:
            if r["code_normalized"] != r["code_source"].replace(" ",""):
                errors.append(f"unexpected_code_normalization:{r['record_id']}")
    return errors


def validate_v1(v1: dict) -> list[str]:
    errors = []
    nodes = v1["nodes"]
    ids = [n["node_id"] for n in nodes]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_node_id")
    by_id = {n["node_id"]:n for n in nodes}
    for n in nodes:
        p = n.get("parent_node_id")
        if p and p not in by_id:
            errors.append(f"missing_parent:{n['node_id']}")
        if p == n["node_id"]:
            errors.append(f"self_reference:{n['node_id']}")
        if n["depth"] != len(n["path_node_ids"])-1:
            errors.append(f"bad_depth:{n['node_id']}")
        if n["is_leaf"] != (len(n["children_node_ids"])==0):
            errors.append(f"bad_leaf:{n['node_id']}")
    # Specific anti-padding regression.
    refs = {n["ref_code"]:n["node_id"] for n in nodes if n["node_type"] in {"group","account"}}
    for a,b in [("11","110"),("12","120"),("28","280"),("29","290"),("59","590")]:
        if refs.get(a) == refs.get(b):
            errors.append(f"padding_collision:{a}:{b}")
    return errors


def validate_v2(v2: dict) -> list[str]:
    errors = []
    if v2["statistics"]["annotations"] != 58:
        errors.append(f"expected_58_titre_xii_annotations:{v2['statistics']['annotations']}")
    for a in v2["annotations"]:
        if a["executable_rules_generated"]:
            errors.append(f"v2_executable_rule:{a['annotation_id']}")
        if not a["provenance"]["source_refs"]:
            errors.append(f"missing_source_ref:{a['annotation_id']}")
    return errors


def validate_reporting(reporting: dict) -> list[str]:
    errors = []
    if reporting["statistics"]["statement_templates"] != 4:
        errors.append("expected_four_statement_templates")
    for st in reporting["statements"]:
        for line in st["lines"]:
            for comp in line["mapping_components"]:
                if comp["mapping"]["parse_status"] == "partial":
                    errors.append(f"partial_mapping:{line['line_id']}:{comp['mapping']['raw_expression']}")
    return errors
