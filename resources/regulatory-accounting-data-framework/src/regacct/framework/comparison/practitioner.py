from __future__ import annotations
from collections import Counter, defaultdict
from ..overlay.merge import normalize_label


def compare_practitioner_reference(
    canonical_effective_plan: dict,
    practitioner_entries: list[dict],
    practitioner_document_id: str,
) -> dict:
    canonical = {x["ref_code"]: x for x in canonical_effective_plan["accounts"]}
    by_code = defaultdict(list)
    for entry in practitioner_entries:
        by_code[str(entry["code"])].append(entry)

    comparisons = []
    for code in sorted(set(canonical) | set(by_code), key=lambda x: (len(x), x)):
        c = canonical.get(code)
        prs = by_code.get(code, [])
        if c and not prs:
            status = "missing_from_practitioner_reference"
        elif prs and not c:
            status = "practitioner_extra_not_in_canonical_effective_plan"
        elif len(prs) > 1:
            status = "duplicate_code_meaning_in_practitioner_reference"
        elif normalize_label(c["label"]) == normalize_label(prs[0]["label_source"]):
            status = "label_match"
        else:
            status = "label_variation"

        comparisons.append({
            "ref_code": code,
            "status": status,
            "canonical_label": c["label"] if c else None,
            "canonical_origin": c["origin"] if c else None,
            "practitioner_occurrences": prs,
            "practitioner_document_id": practitioner_document_id,
            "canonical_promotion_allowed": False,
        })

    return {
        "comparison_policy": {
            "practitioner_reference_is_regulatory_source": False,
            "canonical_promotion_allowed": False,
            "use_case": "secondary comparison and validation only",
        },
        "comparisons": comparisons,
        "statistics": dict(sorted(Counter(x["status"] for x in comparisons).items())),
        "duplicate_codes": sorted(code for code, rows in by_code.items() if len(rows) > 1),
    }
