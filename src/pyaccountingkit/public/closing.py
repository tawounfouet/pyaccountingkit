"""Public closing facade."""

from __future__ import annotations

from pyaccountingkit.public._base import PublicNamespace
from pyaccountingkit.public.context import CommandContext


class ClosingAPI(PublicNamespace):
    """Framework-neutral closing namespace."""

    def __init__(self, service: object | None = None) -> None:
        super().__init__("closing", service)

    def start_review(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `closing.start_review` public operation."""
        return self._invoke("start_review", context=context, **parameters)

    def generate_adjustments(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `closing.generate_adjustments` public operation."""
        return self._invoke("generate_adjustments", context=context, **parameters)

    def validate(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `closing.validate` public operation."""
        return self._invoke("validate", context=context, **parameters)

    def close(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `closing.close` public operation."""
        return self._invoke("close", context=context, **parameters)

    def reopen(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `closing.reopen` public operation."""
        return self._invoke("reopen", context=context, **parameters)

    def status(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `closing.status` public operation."""
        return self._invoke("status", context=context, **parameters)

    def create_snapshot(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `closing.create_snapshot` public operation."""
        return self._invoke("create_snapshot", context=context, **parameters)


__all__ = ["ClosingAPI"]
