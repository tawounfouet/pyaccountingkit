"""Public controls and audit facade."""

from __future__ import annotations

from pyaccountingkit.public._base import PublicNamespace
from pyaccountingkit.public.context import CommandContext


class ControlsAPI(PublicNamespace):
    """Framework-neutral controls namespace."""

    def __init__(self, service: object | None = None) -> None:
        super().__init__("controls", service)

    def run(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `controls.run` public operation."""
        return self._invoke("run", context=context, **parameters)

    def evaluate(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `controls.evaluate` public operation."""
        return self._invoke("evaluate", context=context, **parameters)

    def get_run(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `controls.get_run` public operation."""
        return self._invoke("get_run", context=context, **parameters)

    def list_findings(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `controls.list_findings` public operation."""
        return self._invoke("list_findings", context=context, **parameters)

    def gate(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `controls.gate` public operation."""
        return self._invoke("gate", context=context, **parameters)


__all__ = ["ControlsAPI"]
