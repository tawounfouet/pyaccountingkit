from regacct.standards.pcemf.safety import validate_crosswalk_safety, validate_amifond_posting_safety


def test_crosswalk_safety_blocks_code_equality_scoring_and_auto_approval():
    data = {"candidates":[
        {"candidate_id":"x","code_equality_used_in_score":True,"auto_approval_allowed":True}
    ]}
    errors = validate_crosswalk_safety(data)
    assert len(errors) == 2


def test_amifond_posting_models_are_not_executable():
    data = {"posting_rule_models":[
        {"id":"p1","executable":False,"human_validation_required":True}
    ]}
    assert validate_amifond_posting_safety(data) == []
