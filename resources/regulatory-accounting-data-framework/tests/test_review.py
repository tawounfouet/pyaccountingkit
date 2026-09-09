import pytest
from regacct.framework.review.workflow import validate_review_decision

def test_approval_needs_evidence():
    d={'decision_id':'d1','source_node_id':'a','target_node_id':'b','decision':'approved','mapping_type':'closest_semantic_equivalent','reviewer':'r','reviewed_at':'2026-08-25','justification':'ok','evidence_refs':[]}
    with pytest.raises(ValueError): validate_review_decision(d)
