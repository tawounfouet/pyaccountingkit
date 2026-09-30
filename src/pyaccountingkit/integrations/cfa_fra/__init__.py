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
from pyaccountingkit.integrations.cfa_fra.retirement import (
    LegacyRetirementBlockedError,
    LegacyRetirementDecision,
    LegacyRetirementEvidence,
    LegacyRetirementGate,
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
    "LegacyRetirementBlockedError",
    "LegacyRetirementDecision",
    "LegacyRetirementEvidence",
    "LegacyRetirementGate",
    "MigrationRouting",
    "MutationBackend",
    "ParityMismatch",
    "ParityResult",
    "ReadBackend",
    "load_golden_fixture",
]
