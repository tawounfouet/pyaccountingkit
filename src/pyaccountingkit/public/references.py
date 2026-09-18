"""Public accounting-reference facade."""

from __future__ import annotations

from pyaccountingkit.public._base import PublicNamespace
from pyaccountingkit.public.context import CommandContext


class ReferencesAPI(PublicNamespace):
    """Framework-neutral references namespace."""

    def __init__(self, service: object | None = None) -> None:
        super().__init__("references", service)

    def get_standard(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `references.get_standard` public operation."""
        return self._invoke("get_standard", context=context, **parameters)

    def list_standards(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `references.list_standards` public operation."""
        return self._invoke("list_standards", context=context, **parameters)

    def get_structure(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `references.get_structure` public operation."""
        return self._invoke("get_structure", context=context, **parameters)

    def get_effective_plan(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `references.get_effective_plan` public operation."""
        return self._invoke("get_effective_plan", context=context, **parameters)

    def get_reporting_model(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `references.get_reporting_model` public operation."""
        return self._invoke("get_reporting_model", context=context, **parameters)

    def create_snapshot(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `references.create_snapshot` public operation."""
        return self._invoke("create_snapshot", context=context, **parameters)


__all__ = ["ReferencesAPI"]
