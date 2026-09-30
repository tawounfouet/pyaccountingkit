"""CFA FRA extraction, golden qualification and migration integration."""

from pyaccountingkit.integrations.cfa_fra.compatibility import (
    CFAFRACompatibilityAdapter,
    CFAFRAMigrationRouteError,
    DualRunObservation,
    LegacyIdentityLink,
    LegacyIdentityMap,
    MigrationRouting,
    MutationBackend,
    ReadBackend,
)
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
    "CFAFRACompatibilityAdapter",
    "CFAFRAMigrationRouteError",
    "DivergenceCategory",
    "DualRunObservation",
    "GoldenCategory",
    "GoldenFixture",
    "IntentionalDivergence",
    "LegacyIdentityLink",
    "LegacyIdentityMap",
    "MigrationRouting",
    "MutationBackend",
    "ParityMismatch",
    "ParityResult",
    "ReadBackend",
    "load_golden_fixture",
]
