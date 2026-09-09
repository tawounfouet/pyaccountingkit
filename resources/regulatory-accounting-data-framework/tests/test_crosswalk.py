from regacct.framework.crosswalk.ranker import candidate_score

def test_no_code_in_score_api():
    assert candidate_score('Caisse','Caisse',2,2)>0.8
