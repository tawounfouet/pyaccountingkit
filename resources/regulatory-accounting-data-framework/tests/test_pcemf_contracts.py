from regacct.standards.pcemf.contracts import HISTORICAL_INVARIANTS


def test_historical_contract_matches_documented_release():
    assert HISTORICAL_INVARIANTS["v0"]["source_entries"] == 1502
    assert HISTORICAL_INVARIANTS["v1"]["account_nodes"] == 1552
    assert HISTORICAL_INVARIANTS["v2"]["annotations"] == 86
    assert HISTORICAL_INVARIANTS["v3"]["statement_lines"] == 635
    assert HISTORICAL_INVARIANTS["v4"]["prudential_rules"] == 13
    assert HISTORICAL_INVARIANTS["v5"]["candidate_mappings"] == 4656
    assert HISTORICAL_INVARIANTS["v6"]["executable_posting_rules"] == 0
