"""French FEC import adapter for PyAccountingKit."""

from .adapter import FECAdapter, FECAdapterCapabilities
from .controls import FECValidator
from .discovery import FECDiscoveryReport, discover_fec
from .grouping import FECGroupingStrategy
from .normalizer import FECNormalizationError, FECNormalizer
from .parser import FECParseError, FECParser
from .reconciliation import FECReconciliationReport, build_fec_reconciliation_report
from .schema import FEC_FIELDS, FEC_FIELD_NAMES, FECFieldDefinition, FECSourceDescriptor

__all__ = [
    "FECAdapter",
    "FECAdapterCapabilities",
    "FECDiscoveryReport",
    "FECFieldDefinition",
    "FECGroupingStrategy",
    "FECNormalizationError",
    "FECNormalizer",
    "FECParseError",
    "FECParser",
    "FECReconciliationReport",
    "FECSourceDescriptor",
    "FECValidator",
    "FEC_FIELDS",
    "FEC_FIELD_NAMES",
    "build_fec_reconciliation_report",
    "discover_fec",
]
