from regacct.framework.reporting.mapping_parser import parse_mapping_expression, account_matches_selector


def test_pcemf_sauf_expression():
    parsed = parse_mapping_expression("101 / 102 (sauf 10 129, 10 139)")
    assert parsed["parse_status"] == "parsed"
    s102 = parsed["selectors"][1]
    assert "10129" in s102["exclude_prefixes"]
    assert "10139" in s102["exclude_prefixes"]


def test_pcemf_range_exclusion():
    parsed = parse_mapping_expression("30 (sauf 30 139 à 30 939)")
    s = parsed["selectors"][0]
    assert s["account_prefix"] == "30"
    assert s["exclude_ranges"][0] == {"start":"30139","end":"30939"}
    assert account_matches_selector("30140", "debit", s) is False
    assert account_matches_selector("30010", "debit", s) is True
