"""Public regulatory-reporting facade."""

from __future__ import annotations

from pyaccountingkit.public._base import PublicNamespace
from pyaccountingkit.public.context import CommandContext


class RegulatoryReportingAPI(PublicNamespace):
    """Framework-neutral reporting namespace."""

    def __init__(self, service: object | None = None) -> None:
        super().__init__("reporting", service)

    def create_profile(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `reporting.create_profile` public operation."""
        return self._invoke("create_profile", context=context, **parameters)

    def activate_profile(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `reporting.activate_profile` public operation."""
        return self._invoke("activate_profile", context=context, **parameters)

    def build_report(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `reporting.build_report` public operation."""
        return self._invoke("build_report", context=context, **parameters)

    def validate_report(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `reporting.validate_report` public operation."""
        return self._invoke("validate_report", context=context, **parameters)

    def export(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `reporting.export` public operation."""
        return self._invoke("export", context=context, **parameters)

    def plan_upgrade(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `reporting.plan_upgrade` public operation."""
        return self._invoke("plan_upgrade", context=context, **parameters)


__all__ = ["RegulatoryReportingAPI"]
