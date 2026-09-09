from __future__ import annotations
from typing import Any


def validate_crosswalk_safety(data: Any) -> list[str]:
    errors = []
    candidates = []
    if isinstance(data, dict):
        candidates = data.get("candidates") or data.get("candidate_mappings") or []
        if not candidates:
            for group in data.get("candidate_groups") or []:
                candidates.extend(group.get("candidates") or [])
    for c in candidates:
        if c.get("code_equality_used_in_score") is True:
            errors.append(f"code_equality_used_in_score:{c.get('candidate_id')}")
        if c.get("auto_approval_allowed") is True:
            errors.append(f"auto_approval_allowed:{c.get('candidate_id')}")
    return errors


def validate_amifond_posting_safety(data: Any) -> list[str]:
    errors = []
    if not isinstance(data, dict):
        return errors
    models = data.get("posting_rule_models") or data.get("posting_models") or []
    for model in models:
        if model.get("executable") is True:
            errors.append(f"executable_posting_model:{model.get('id') or model.get('posting_rule_id')}")
        if model.get("human_validation_required") is False:
            errors.append(f"human_validation_disabled:{model.get('id') or model.get('posting_rule_id')}")
    return errors
