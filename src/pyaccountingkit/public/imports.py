"""Public accounting-import facade."""

from __future__ import annotations

from pyaccountingkit.public._base import PublicNamespace
from pyaccountingkit.public.context import CommandContext


class ImportsAPI(PublicNamespace):
    """Framework-neutral imports namespace."""

    def __init__(self, service: object | None = None) -> None:
        super().__init__("imports", service)

    def create(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `imports.create` public operation."""
        return self._invoke("create", context=context, **parameters)

    def preflight(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `imports.preflight` public operation."""
        return self._invoke("preflight", context=context, **parameters)

    def discover(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `imports.discover` public operation."""
        return self._invoke("discover", context=context, **parameters)

    def map_account(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `imports.map_account` public operation."""
        return self._invoke("map_account", context=context, **parameters)

    def map_journal(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `imports.map_journal` public operation."""
        return self._invoke("map_journal", context=context, **parameters)

    def validate(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `imports.validate` public operation."""
        return self._invoke("validate", context=context, **parameters)

    def build_plan(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `imports.build_plan` public operation."""
        return self._invoke("build_plan", context=context, **parameters)

    def approve(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `imports.approve` public operation."""
        return self._invoke("approve", context=context, **parameters)

    def execute(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `imports.execute` public operation."""
        return self._invoke("execute", context=context, **parameters)

    def trace(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `imports.trace` public operation."""
        return self._invoke("trace", context=context, **parameters)

    def reprocess(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `imports.reprocess` public operation."""
        return self._invoke("reprocess", context=context, **parameters)


__all__ = ["ImportsAPI"]
