"""Ports for exact-snapshot regulatory reporting models and renderers."""

from __future__ import annotations

from typing import Protocol

from pyaccountingkit.domain.reporting.reference_reporting_model import ReferenceReportingModel


class ReferenceReportingModelProviderProtocol(Protocol):
    """Resolve a regulatory reporting model from exact replay coordinates."""

    def get_reporting_model(
        self,
        *,
        reference_snapshot_id: str,
        framework: str,
        edition: str,
        model_code: str,
    ) -> ReferenceReportingModel:
        """Return the exact pinned model or fail closed."""
        ...


class RegulatoryRendererProtocol(Protocol):
    """Render a precomputed regulatory report without recalculating accounting."""

    renderer_id: str

    def render(self, report: object, definition: object) -> bytes:
        """Return deterministic export bytes for a precomputed report."""
        ...


__all__ = [
    "ReferenceReportingModelProviderProtocol",
    "RegulatoryRendererProtocol",
]
