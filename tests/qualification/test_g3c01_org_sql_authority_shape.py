"""Pure G3-C01 posture-input checks (no PostgreSQL or IAM required)."""

import pytest

from scripts.verify_org_sql_authority import FAMILIES, FUNCTIONS, GUARDS, TABLES, parse_claims


def test_require_each_independent_family_for_every_tenant():
    roles = parse_claims(
        ["runtime_a:tenant-a", "runtime_b:tenant-b"],
        [
            f"{family}:{family}_{suffix}:{tenant}"
            for family in FAMILIES
            for suffix, tenant in (("a", "tenant-a"), ("b", "tenant-b"))
        ],
    )
    assert len(roles) == 10
    assert len({claim.role for claim in roles}) == len(roles)
    assert set(FUNCTIONS) == set(FAMILIES)
    assert set(GUARDS) == set(TABLES)


@pytest.mark.parametrize(
    ("runtimes", "issuers"),
    [
        ([], []),
        (["app:a"], []),
        (["app:a"], ["company:app:a"]),
        (["app:a"], ["company:issuer:b"]),
        (["app:a", "app:a"], []),
        (["bad:runtime:syntax"], []),
        (["app:a"], ["unsupported:issuer:a"]),
        (["app:a"], ["registry:issuer:"]),
        (["app:a"], ["company:issuer:a", "company:issuer:a"]),
    ],
)
def test_missing_duplicated_or_misbound_role_arguments_fail_closed(runtimes, issuers):
    with pytest.raises(ValueError):
        parse_claims(runtimes, issuers)
