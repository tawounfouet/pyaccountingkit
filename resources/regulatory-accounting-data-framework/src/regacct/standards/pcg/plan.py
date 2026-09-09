from __future__ import annotations
from pathlib import Path
import re

CLASS_RE = re.compile(r"^##\s+CLASSE\s+(\d+)\s*:\s*(.+?)\s*$", re.I)
GROUP_RE = re.compile(r"^###\s+\*\*([0-9]+(?:/[0-9]+)?)\*\*\s*-\s*(.+?)\s*$")
REGULAR_ACCOUNT_RE = re.compile(r"^(?P<indent>\s*)-\s+\*\*(?P<code>\d+)\*\*\s*-\s*(?P<label>.+?)\s*$")
OPTIONAL_ACCOUNT_RE = re.compile(r"^(?P<indent>\s*)-\s+\*(?P<code>\d+(?:\s+à\s+\d+)?)\s*-\s*(?P<label>.+?)\*\s*$")


def parse_plan_markdown(path: str | Path) -> dict:
    path = Path(path)
    records = []
    current_class = None
    current_group = None
    current_bundle = None
    stack_by_indent: dict[int, str] = {}
    source_order = 0

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        m = CLASS_RE.match(raw)
        if m:
            current_class = m.group(1)
            current_group = None
            current_bundle = None
            stack_by_indent.clear()
            source_order += 1
            records.append({
                "record_id": f"pcg2026:plan:l{lineno:04d}",
                "source_order": source_order,
                "record_type": "class",
                "code_source": current_class,
                "code_normalized": current_class,
                "label_source": m.group(2).strip(),
                "optional": False,
                "parent_code": None,
                "class_number_source": int(current_class),
                "source": {
                    "document_id": "fr-pcg-plan-2026-md",
                    "section": "Article 1121-1 - Plan de comptes",
                    "page_pdf": None,
                    "heading_path": [f"CLASSE {current_class}"],
                    "snippet": raw,
                },
                "source_line_md": lineno,
                "source_rows": [raw],
                "extraction_features": {"markdown_role": "class_heading"},
            })
            continue

        m = GROUP_RE.match(raw)
        if m:
            code = m.group(1)
            label = m.group(2).strip()
            stack_by_indent.clear()

            if "/" in code:
                record_type = "group_bundle"
                parent_code = current_class
                current_bundle = code
                current_group = None
                heading_path = [f"CLASSE {current_class}", code]
            else:
                bundle_parts = set(current_bundle.split("/")) if current_bundle else set()
                if current_bundle and code in bundle_parts:
                    parent_code = current_bundle
                    heading_path = [f"CLASSE {current_class}", current_bundle, code]
                else:
                    current_bundle = None
                    parent_code = current_class
                    heading_path = [f"CLASSE {current_class}", code]
                record_type = "group"
                current_group = code

            source_order += 1
            records.append({
                "record_id": f"pcg2026:plan:l{lineno:04d}",
                "source_order": source_order,
                "record_type": record_type,
                "code_source": code,
                "code_normalized": code,
                "label_source": label,
                "optional": False,
                "parent_code": parent_code,
                "class_number_source": int(current_class) if current_class else None,
                "source": {
                    "document_id": "fr-pcg-plan-2026-md",
                    "section": "Article 1121-1 - Plan de comptes",
                    "page_pdf": None,
                    "heading_path": heading_path,
                    "snippet": raw,
                },
                "source_line_md": lineno,
                "source_rows": [raw],
                "extraction_features": {
                    "markdown_role": "group_bundle_heading" if record_type == "group_bundle" else "group_heading"
                },
            })
            continue

        optional = False
        m = REGULAR_ACCOUNT_RE.match(raw)
        if not m:
            m = OPTIONAL_ACCOUNT_RE.match(raw)
            optional = bool(m)
        if not m:
            continue

        source_order += 1
        indent_spaces = len(m.group("indent").replace("\t", "  "))
        code_source = m.group("code").strip()
        label = m.group("label").strip()

        for k in list(stack_by_indent):
            if k >= indent_spaces:
                del stack_by_indent[k]

        parent_code = current_group or current_bundle
        lower_indents = [i for i in stack_by_indent if i < indent_spaces]
        if lower_indents:
            parent_code = stack_by_indent[max(lower_indents)]

        is_range = " à " in code_source
        record_type = "account_range" if is_range else "account"
        normalized = re.sub(r"\s+", "", code_source)
        if not is_range:
            stack_by_indent[indent_spaces] = normalized

        hp = [f"CLASSE {current_class}"]
        if current_bundle:
            hp.append(current_bundle)
        if current_group:
            hp.append(current_group)

        records.append({
            "record_id": f"pcg2026:plan:l{lineno:04d}",
            "source_order": source_order,
            "record_type": record_type,
            "code_source": code_source,
            "code_normalized": normalized,
            "label_source": label,
            "optional": optional,
            "parent_code": parent_code,
            "class_number_source": int(current_class) if current_class else None,
            "source": {
                "document_id": "fr-pcg-plan-2026-md",
                "section": "Article 1121-1 - Plan de comptes",
                "page_pdf": None,
                "heading_path": hp,
                "snippet": raw,
            },
            "source_line_md": lineno,
            "source_rows": [raw],
            "extraction_features": {
                "markdown_role": "optional_account" if optional else "minimum_plan_account",
                "indent_spaces": indent_spaces,
                "italic_source": optional,
            },
        })

    group_types = {"group", "group_bundle"}
    stats = {
        "classes": sum(r["record_type"] == "class" for r in records),
        "groups": sum(r["record_type"] in group_types for r in records),
        "group_bundles": sum(r["record_type"] == "group_bundle" for r in records),
        "accounts": sum(r["record_type"] == "account" for r in records),
        "account_ranges": sum(r["record_type"] == "account_range" for r in records),
        "optional_account_entries": sum(r["optional"] and r["record_type"] in {"account","account_range"} for r in records),
        "minimum_plan_account_entries": sum((not r["optional"]) and r["record_type"] == "account" for r in records),
        "records_total": len(records),
    }
    return {
        "standard_id": "fr-pcg",
        "edition": "2026",
        "dataset_layer": "v0_raw",
        "source_policy": "printed_source_only",
        "records": records,
        "statistics": stats,
    }


def build_structure(v0: dict) -> dict:
    records = v0["records"]
    nodes = []
    code_to_id = {}

    for r in records:
        rt = r["record_type"]
        code = r["code_normalized"]
        if rt == "class":
            node_id = f"class:fr-pcg:2026:{code}"
        elif rt == "group_bundle":
            node_id = f"bundle:fr-pcg:2026:{code.replace('/','-')}"
        elif rt in {"group","account"}:
            node_id = f"account:fr-pcg:2026:{code}"
        else:
            node_id = f"range:fr-pcg:2026:{code.replace('à','-')}"
        code_to_id[(rt, code)] = node_id
        if rt in {"group","account"}:
            code_to_id[("accountish", code)] = node_id
        if rt == "group_bundle":
            code_to_id[("bundleish", code)] = node_id
        if rt == "class":
            code_to_id[("classish", code)] = node_id

    by_id = {}
    for r in records:
        rt = r["record_type"]
        code = r["code_normalized"]
        node_id = code_to_id[(rt, code)]
        parent_code = r["parent_code"]

        if rt == "class":
            parent_id = None
        elif rt == "group_bundle":
            parent_id = code_to_id.get(("classish", str(parent_code)))
        else:
            if parent_code and "/" in str(parent_code):
                parent_id = code_to_id.get(("bundleish", str(parent_code)))
            elif len(str(parent_code or "")) == 1:
                parent_id = code_to_id.get(("classish", str(parent_code)))
            else:
                parent_id = code_to_id.get(("accountish", str(parent_code)))

        node = {
            "node_id": node_id,
            "node_type": rt,
            "standard_id": "fr-pcg",
            "edition": "2026",
            "source_record_id": r["record_id"],
            "ref_code": code,
            "label_source": r["label_source"],
            "account_class": r["class_number_source"],
            "parent_node_id": parent_id,
            "children_node_ids": [],
            "depth": 0,
            "path_node_ids": [],
            "path_codes": [],
            "is_leaf": True,
            "attributes": {
                "optional": r["optional"],
                "is_minimum_plan_account": (not r["optional"]) if rt in {"group","group_bundle","account"} else None,
                "source_line_md": r["source_line_md"],
                "source_code": r["code_source"],
            },
            "provenance": {
                "type": "derived",
                "method": "pcg_markdown_hierarchy_v1",
                "source_refs": [r["source"]],
                "confidence": 1.0,
                "review_status": "auto_verified",
            },
        }
        if rt == "account_range":
            parts = [x.strip() for x in r["code_source"].split("à")]
            node["attributes"]["range_start"] = parts[0]
            node["attributes"]["range_end"] = parts[1] if len(parts) > 1 else None
        by_id[node_id] = node
        nodes.append(node)

    for n in nodes:
        if n["parent_node_id"]:
            if n["parent_node_id"] not in by_id:
                raise ValueError(f"Missing parent {n['parent_node_id']} for {n['node_id']}")
            by_id[n["parent_node_id"]]["children_node_ids"].append(n["node_id"])

    def build_path(node):
        ids = [node["node_id"]]
        codes = [node["ref_code"]]
        cur = node
        seen = {node["node_id"]}
        while cur["parent_node_id"]:
            parent = by_id[cur["parent_node_id"]]
            if parent["node_id"] in seen:
                raise ValueError(f"cycle detected at {parent['node_id']}")
            seen.add(parent["node_id"])
            ids.append(parent["node_id"])
            codes.append(parent["ref_code"])
            cur = parent
        return list(reversed(ids)), list(reversed(codes))

    for n in nodes:
        ids, codes = build_path(n)
        n["path_node_ids"] = ids
        n["path_codes"] = codes
        n["depth"] = len(ids) - 1
        n["is_leaf"] = len(n["children_node_ids"]) == 0

    stats = {
        "class_nodes": sum(n["node_type"] == "class" for n in nodes),
        "group_nodes": sum(n["node_type"] in {"group","group_bundle"} for n in nodes),
        "group_bundle_nodes": sum(n["node_type"] == "group_bundle" for n in nodes),
        "account_nodes": sum(n["node_type"] == "account" for n in nodes),
        "range_nodes": sum(n["node_type"] == "account_range" for n in nodes),
        "graph_nodes": len(nodes),
        "optional_account_nodes": sum(n["node_type"] == "account" and n["attributes"]["optional"] for n in nodes),
        "minimum_account_or_group_nodes": sum(
            n["node_type"] in {"account","group","group_bundle"} and n["attributes"]["is_minimum_plan_account"] for n in nodes
        ),
    }
    return {
        "standard_id": "fr-pcg",
        "edition": "2026",
        "dataset_layer": "v1_structure",
        "nodes": nodes,
        "statistics": stats,
    }
