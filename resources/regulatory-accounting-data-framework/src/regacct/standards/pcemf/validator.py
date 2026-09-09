from __future__ import annotations
from pathlib import Path
import json
from typing import Any

from .contracts import HISTORICAL_INVARIANTS
from .metrics import measure_v0, measure_v1, measure_v2, measure_v3, measure_v4, measure_v5, measure_v6


def load_json_if_exists(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def compare_metrics(phase: str, actual: dict[str, int], strict: bool = True) -> list[dict]:
    expected = HISTORICAL_INVARIANTS[phase]
    observations = []
    for key, expected_value in expected.items():
        if key not in actual:
            observations.append({
                "phase": phase, "metric": key, "status": "not_measured",
                "expected": expected_value, "actual": None,
            })
            continue
        actual_value = actual[key]
        status = "ok" if actual_value == expected_value else "mismatch"
        observations.append({
            "phase": phase, "metric": key, "status": status,
            "expected": expected_value, "actual": actual_value,
        })
    if strict and any(o["status"] == "mismatch" for o in observations):
        return observations
    return observations


def validate_legacy_root(root: str | Path, strict: bool = False) -> dict:
    root = Path(root)
    results: dict[str, Any] = {"root": str(root), "phases": {}, "strict": strict}

    v0 = load_json_if_exists(root / "datasets/pcemf_2010_v0_raw.json")
    if v0 is not None:
        actual = measure_v0(v0)
        results["phases"]["v0"] = {"actual": actual, "checks": compare_metrics("v0", actual, strict)}

    v1 = load_json_if_exists(root / "datasets/pcemf_2010_v1_structure.json")
    if v1 is not None:
        actual = measure_v1(v1)
        # cycle checking is handled by structural graph validator after canonical migration
        results["phases"]["v1"] = {"actual": actual, "checks": compare_metrics("v1", actual, strict)}

    v2 = load_json_if_exists(root / "datasets/pcemf_2010_v2_annotated.json")
    if v2 is not None:
        anom = load_json_if_exists(root / "validation/anomalies/pcemf_2010_v2_anomalies.json")
        actual = measure_v2(v2, anom)
        results["phases"]["v2"] = {"actual": actual, "checks": compare_metrics("v2", actual, strict)}

    v3 = load_json_if_exists(root / "datasets/pcemf_2010_v3_reporting.json")
    if v3 is not None:
        anom = load_json_if_exists(root / "validation/anomalies/pcemf_2010_v3_reporting_anomalies.json")
        actual = measure_v3(v3, anom)
        results["phases"]["v3"] = {"actual": actual, "checks": compare_metrics("v3", actual, strict)}

    v4 = load_json_if_exists(root / "datasets/pcemf_2010_v4_prudential.json")
    if v4 is not None:
        anom = load_json_if_exists(root / "validation/anomalies/pcemf_2010_v4_prudential_anomalies.json")
        actual = measure_v4(v4, anom)
        results["phases"]["v4"] = {"actual": actual, "checks": compare_metrics("v4", actual, strict)}

    v5_path = root / "datasets/pcemf_syscohada_v5_crosswalk_registry.json"
    if not v5_path.exists():
        v5_path = root / "crosswalks/pcemf2010-syscohada2017/v1/candidates.json"
    v5 = load_json_if_exists(v5_path)
    if v5 is not None:
        rag = load_json_if_exists(root / "rag/syscohada-guide/v1/index.json")
        approved = load_json_if_exists(root / "crosswalks/pcemf2010-syscohada2017/v1/approved.json")
        actual = measure_v5(v5, rag_data=rag, approved_data=approved)
        results["phases"]["v5"] = {"actual": actual, "checks": compare_metrics("v5", actual, strict)}

    v6 = None
    for rel in (
        "datasets/amifond_v6_business_enrichment.json",
        "datasets/amifond_2026_v6_business_enrichment.json",
        "business/amifond_v6_business_enrichment.json",
    ):
        v6 = load_json_if_exists(root / rel)
        if v6 is not None:
            break
    if v6 is not None:
        actual = measure_v6(v6)
        results["phases"]["v6"] = {"actual": actual, "checks": compare_metrics("v6", actual, strict)}

    results["missing_phases"] = [p for p in ("v0","v1","v2","v3","v4","v5","v6") if p not in results["phases"]]
    results["mismatches"] = [
        x for phase in results["phases"].values()
        for x in phase["checks"] if x["status"] == "mismatch"
    ]
    results["status"] = "ok" if not results["mismatches"] else ("failed" if strict else "review")
    return results
