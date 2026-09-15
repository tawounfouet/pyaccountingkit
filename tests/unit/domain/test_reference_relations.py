"""Unit tests for negative constraints (LOT-10)."""

from __future__ import annotations

import pytest

from pyaccountingkit.domain.references.relations import (
    ConstraintKind,
    ConstraintRegister,
    NegativeConstraint,
)


def _register() -> ConstraintRegister:
    register = ConstraintRegister("fr-pcg")
    register.add(
        NegativeConstraint(
            node_id="account:fr-pcg:2026:101",
            kind=ConstraintKind.CREDIT_ONLY,
            reason="Capital is a permanent credit balance.",
            standard_id="fr-pcg",
        )
    )
    register.add(
        NegativeConstraint(
            node_id="account:fr-pcg:2026:101",
            kind=ConstraintKind.NO_DIRECT_POSTING,
            reason="Capital posts through 1018 sub-accounts only.",
            standard_id="fr-pcg",
        )
    )
    register.add(
        NegativeConstraint(
            node_id="account:fr-pcg:2026:411",
            kind=ConstraintKind.DEBIT_ONLY,
            reason="Clients hold debit balances.",
            standard_id="fr-pcg",
        )
    )
    return register


def test_register_rejects_cross_standard() -> None:
    register = ConstraintRegister("fr-pcg")
    with pytest.raises(ValueError, match="fr-pcg"):
        register.add(
            NegativeConstraint(
                node_id="x",
                kind=ConstraintKind.CREDIT_ONLY,
                reason="r",
                standard_id="syscohada",
            )
        )


def test_multiple_kinds_per_node() -> None:
    register = _register()
    kinds = {c.kind for c in register.for_node("account:fr-pcg:2026:101")}
    assert kinds == {ConstraintKind.CREDIT_ONLY, ConstraintKind.NO_DIRECT_POSTING}


def test_balance_kind_first_class() -> None:
    register = _register()
    assert register.balance_kind("account:fr-pcg:2026:101") is ConstraintKind.CREDIT_ONLY
    assert register.balance_kind("account:fr-pcg:2026:411") is ConstraintKind.DEBIT_ONLY
    assert register.balance_kind("unknown") is None


def test_all_iteration() -> None:
    register = _register()
    assert len(register.all()) == 3
