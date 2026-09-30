"""CFA FRA extraction, golden qualification and migration integration."""

from pyaccountingkit.integrations.cfa_fra.golden import (
    ORACLE_MANIFEST_VERSION,
    ORACLE_TREE_SHA,
    DivergenceCategory,
    GoldenCategory,
    GoldenFixture,
    IntentionalDivergence,
    ParityMismatch,
    ParityResult,
    load_golden_fixture,
)

__all__ = [
    "ORACLE_MANIFEST_VERSION",
    "ORACLE_TREE_SHA",
    "DivergenceCategory",
    "GoldenCategory",
    "GoldenFixture",
    "IntentionalDivergence",
    "ParityMismatch",
    "ParityResult",
    "load_golden_fixture",
]
