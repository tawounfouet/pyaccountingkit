"""Public financial-statement facade."""

from __future__ import annotations

from pyaccountingkit.public._base import PublicNamespace
from pyaccountingkit.public.context import CommandContext


class StatementsAPI(PublicNamespace):
    """Framework-neutral statements namespace."""

    def __init__(self, service: object | None = None) -> None:
        super().__init__("statements", service)

    def build(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `statements.build` public operation."""
        return self._invoke("build", context=context, **parameters)

    def preview(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `statements.preview` public operation."""
        return self._invoke("preview", context=context, **parameters)

    def snapshot(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `statements.snapshot` public operation."""
        return self._invoke("snapshot", context=context, **parameters)

    def publish(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `statements.publish` public operation."""
        return self._invoke("publish", context=context, **parameters)

    def drilldown(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `statements.drilldown` public operation."""
        return self._invoke("drilldown", context=context, **parameters)

    def compare(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `statements.compare` public operation."""
        return self._invoke("compare", context=context, **parameters)


__all__ = ["StatementsAPI"]
