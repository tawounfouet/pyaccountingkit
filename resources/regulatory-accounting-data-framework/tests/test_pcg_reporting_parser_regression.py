from regacct.standards.pcg.reporting import parse_pcg_expression


def test_sauf_et_clause_stays_attached_to_parent_selector():
    p = parse_pcg_expression("50 [sauf 502 et 509]")
    assert p["parse_status"] == "parsed"
    assert len(p["selectors"]) == 1
    assert p["selectors"][0]["account_prefix"] == "50"
    assert p["selectors"][0]["exclude_prefixes"] == ["502", "509"]


def test_other_exclusion_clauses():
    for expr, prefix, exclusions in [
        ("75 [sauf 757 et 755]", "75", ["757","755"]),
        ("65 [sauf 657 et 655]", "65", ["657","655"]),
        ("16 [sauf 167 et 169]", "16", ["167","169"]),
    ]:
        p = parse_pcg_expression(expr)
        assert p["selectors"][0]["account_prefix"] == prefix
        assert p["selectors"][0]["exclude_prefixes"] == exclusions
