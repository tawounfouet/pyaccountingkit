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


    def relations_for(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `references.relations_for` public operation."""
        return self._invoke("relations_for", context=context, **parameters)

    def require_not_forbidden(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `references.require_not_forbidden` guard."""
        return self._invoke("require_not_forbidden", context=context, **parameters)

    def require_auto_inference_allowed(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `references.require_auto_inference_allowed` guard."""
        return self._invoke(
            "require_auto_inference_allowed",
            context=context,
            **parameters,
        )

    def can_auto_infer(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `references.can_auto_infer` public operation."""
        return self._invoke("can_auto_infer", context=context, **parameters)


__all__ = ["ReferencesAPI"]
