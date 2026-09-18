"""Public financial-analysis facade."""

from __future__ import annotations

from pyaccountingkit.public._base import PublicNamespace
from pyaccountingkit.public.context import CommandContext


class FinancialAnalysisAPI(PublicNamespace):
    """Framework-neutral analysis namespace."""

    def __init__(self, service: object | None = None) -> None:
        super().__init__("analysis", service)

    def define_indicator(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `analysis.define_indicator` public operation."""
        return self._invoke("define_indicator", context=context, **parameters)

    def define_ratio(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `analysis.define_ratio` public operation."""
        return self._invoke("define_ratio", context=context, **parameters)

    def create_definition_set(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `analysis.create_definition_set` public operation."""
        return self._invoke("create_definition_set", context=context, **parameters)

    def activate_definition_set(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `analysis.activate_definition_set` public operation."""
        return self._invoke("activate_definition_set", context=context, **parameters)

    def run(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `analysis.run` public operation."""
        return self._invoke("run", context=context, **parameters)

    def snapshot(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `analysis.snapshot` public operation."""
        return self._invoke("snapshot", context=context, **parameters)

    def drilldown(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `analysis.drilldown` public operation."""
        return self._invoke("drilldown", context=context, **parameters)

    def trend(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `analysis.trend` public operation."""
        return self._invoke("trend", context=context, **parameters)

    def diagnostic(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `analysis.diagnostic` public operation."""
        return self._invoke("diagnostic", context=context, **parameters)


__all__ = ["FinancialAnalysisAPI"]
