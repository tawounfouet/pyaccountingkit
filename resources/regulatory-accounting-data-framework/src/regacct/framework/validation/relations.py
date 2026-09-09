def validate_no_unproven_inheritance(relations):
    errors = []
    for r in relations:
        if r.relation_type.value == "inherits":
            if r.evidence.evidence_status != "source_supported":
                errors.append(f"inheritance_without_source:{r.relation_id}")
            if not r.evidence.source_refs:
                errors.append(f"inheritance_without_evidence:{r.relation_id}")
    return errors

def validate_no_false_ohada_inheritance(relations):
    forbidden = {
        ("cemac-pcemf:2010", "ohada-syscohada:2017"),
        ("ohada-ebnl:2023", "ohada-syscohada:2017"),
    }
    return [
        f"false_inheritance:{r.subject_ref}->{r.target_ref}"
        for r in relations
        if r.relation_type.value == "inherits" and (r.subject_ref, r.target_ref) in forbidden
    ]

def validate_concept_bindings(bindings):
    errors = []
    for b in bindings:
        if b.get("auto_approval_allowed") is True:
            errors.append(f"auto_approval_forbidden:{b.get('binding_id')}")
        if b.get("code_equality_used_as_evidence") is True:
            errors.append(f"code_equality_not_semantic_evidence:{b.get('binding_id')}")
        if b.get("review_status") == "approved" and not b.get("evidence"):
            errors.append(f"approved_binding_without_evidence:{b.get('binding_id')}")
    return errors
