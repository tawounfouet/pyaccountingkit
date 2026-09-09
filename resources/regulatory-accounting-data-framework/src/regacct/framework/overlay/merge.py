from __future__ import annotations
import re
import unicodedata
from typing import Any
from collections import Counter


def normalize_label(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.lower()
    value = value.replace("’", "'").replace("–", "-").replace("—", "-")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def accountish_nodes(structure: dict) -> dict[str, dict]:
    return {
        str(n["ref_code"]): n
        for n in structure.get("nodes", [])
        if n.get("node_type") in {"group", "account"}
    }


def classify_overlay(base_structure: dict, extension_entries: list[dict]) -> dict:
    base = accountish_nodes(base_structure)
    overlay = []
    seen_codes = set()

    for entry in extension_entries:
        code = str(entry["code"])
        seen_codes.add(code)
        base_node = base.get(code)
        if base_node is None:
            overlay_type = "specific_addition"
            base_label = None
        else:
            base_label = base_node["label_source"]
            overlay_type = (
                "same_semantics_label"
                if normalize_label(base_label) == normalize_label(entry["label_source"])
                else "label_or_semantic_override"
            )

        overlay.append({
            "overlay_id": f"overlay:{entry['standard_id']}:{entry['edition']}:{code}",
            "standard_id": entry["standard_id"],
            "edition": entry["edition"],
            "base_standard": entry["base_standard"],
            "ref_code": code,
            "overlay_type": overlay_type,
            "base_label_source": base_label,
            "extension_label_source": entry["label_source"],
            "source_ref": entry["source_ref"],
            "regulatory_status": "official_extension",
            "canonical_effect": "replace_or_add",
        })

    return {
        "overlay_entries": overlay,
        "statistics": dict(sorted(Counter(x["overlay_type"] for x in overlay).items())),
        "extension_codes": sorted(seen_codes),
    }


def build_effective_plan(base_structure: dict, extension_entries: list[dict], standard_id: str, edition: str) -> dict:
    base = accountish_nodes(base_structure)
    ext = {str(x["code"]): x for x in extension_entries}
    codes = sorted(set(base) | set(ext), key=lambda x: (int(x[0]) if x and x[0].isdigit() else 99, len(x), x))
    rows = []

    for code in codes:
        if code in ext:
            e = ext[code]
            origin = "extension_override" if code in base else "extension_addition"
            rows.append({
                "account_id": f"account:{standard_id}:{edition}:{code}",
                "ref_code": code,
                "label": e["label_source"],
                "origin": origin,
                "base_account_id": base.get(code, {}).get("node_id"),
                "base_label": base.get(code, {}).get("label_source"),
                "extension_source_ref": e["source_ref"],
                "provenance_type": "official_source",
            })
        else:
            b = base[code]
            rows.append({
                "account_id": f"account:{standard_id}:{edition}:{code}",
                "ref_code": code,
                "label": b["label_source"],
                "origin": "inherited_from_base_standard",
                "base_account_id": b["node_id"],
                "base_label": b["label_source"],
                "extension_source_ref": None,
                "provenance_type": "derived",
            })

    return {
        "standard_id": standard_id,
        "edition": edition,
        "base_standard": "fr-pcg:2026",
        "inheritance_rule": "ANC 2018-06 Art. 320-1: PCG plan applies subject to specific accounts in Art. 320-2",
        "accounts": rows,
        "statistics": {
            "effective_accounts_or_groups": len(rows),
            "inherited": sum(x["origin"] == "inherited_from_base_standard" for x in rows),
            "extension_additions": sum(x["origin"] == "extension_addition" for x in rows),
            "extension_overrides": sum(x["origin"] == "extension_override" for x in rows),
        },
    }
