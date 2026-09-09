REQUIRED_FOR_APPROVAL={'decision_id','source_node_id','target_node_id','decision','mapping_type','reviewer','reviewed_at','justification','evidence_refs'}
def validate_review_decision(decision):
    missing=REQUIRED_FOR_APPROVAL-set(decision)
    if missing: raise ValueError(f"Missing review fields: {sorted(missing)}")
    if decision['decision']=='approved' and not decision['evidence_refs']: raise ValueError('Approved mapping requires evidence_refs')
