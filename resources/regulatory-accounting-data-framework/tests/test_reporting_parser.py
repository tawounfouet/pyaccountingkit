from regacct.framework.reporting.mapping_parser import parse_mapping_expression

def test_expression():
    r=parse_mapping_expression('371dr / 372cr / 57')
    assert r['parse_status']=='parsed'
    assert r['selectors'][0]['side']=='debit'
    assert r['selectors'][1]['side']=='credit'
    assert r['selectors'][2]['account_prefix']=='57'
