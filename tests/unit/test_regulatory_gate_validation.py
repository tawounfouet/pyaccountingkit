"""Tests for the executable LOT-27 regulatory gate."""

from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_regulatory_gate.py"
MATRIX = ROOT / "REGULATORY_COMPATIBILITY_MATRIX.json"


def _load_module() -> ModuleType:
    name = "pyaccountingkit_regulatory_gate_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _matrix() -> dict[str, object]:
    payload = json.loads(MATRIX.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_current_regulatory_matrix_passes_gr() -> None:
    violations = _load_module().validate_payload(_matrix())
    assert violations == []


def test_gr_rejects_review_required_mapping_made_executable() -> None:
    module = _load_module()
    payload = deepcopy(_matrix())
    profiles = payload["regulatory_frameworks"]
    assert isinstance(profiles, list)
    pcg = next(item for item in profiles if item["standard_ref"] == "fr-pcg:2026")
    mapping = pcg["capabilities"]["REPORTING_ACCOUNT_MAPPINGS"]
    mapping["executable"] = True

    violations = module.validate_payload(payload)
    assert any(
        "REVIEW_REQUIRED capability must remain non-executable" in item for item in violations
    )


def test_gr_rejects_automatic_semantic_inference() -> None:
    module = _load_module()
    payload = deepcopy(_matrix())
    profiles = payload["regulatory_frameworks"]
    assert isinstance(profiles, list)
    ebnl = next(item for item in profiles if item["standard_ref"] == "ohada-ebnl:2023")
    relation = ebnl["capabilities"]["RELATIONS"]
    relation["auto_inference_allowed"] = True

    violations = module.validate_payload(payload)
    assert any("automatic semantic inference is not qualified" in item for item in violations)
