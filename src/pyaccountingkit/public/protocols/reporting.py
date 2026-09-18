"""Public report rendering/export extension contracts."""

from __future__ import annotations

from typing import Protocol

from pyaccountingkit.domain.reporting.regulatory_export import RegulatoryExportDefinition
from pyaccountingkit.domain.reporting.regulatory_report import RegulatoryReport
from pyaccountingkit.ports.regulatory_reporting import (
    RegulatoryRendererProtocol as _InternalRegulatoryRendererProtocol,
)


class RegulatoryRendererProtocol(
    _InternalRegulatoryRendererProtocol,
    Protocol,
):
    """Stable renderer contract over an already-computed regulatory report."""


class RegulatoryExporterProtocol(Protocol):
    """Export a sealed report using an explicit export definition.

    Exporters own transport/integration concerns. They must not recalculate accounting truth.
    """

    exporter_id: str

    def export(
        self,
        report: RegulatoryReport,
        definition: RegulatoryExportDefinition,
    ) -> bytes:
        """Return or transmit the deterministic export representation."""
        ...


__all__ = ["RegulatoryExporterProtocol", "RegulatoryRendererProtocol"]
