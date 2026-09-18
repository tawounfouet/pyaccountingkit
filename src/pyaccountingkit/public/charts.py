"""Public company-chart facade."""

from __future__ import annotations

from pyaccountingkit.public._base import PublicNamespace
from pyaccountingkit.public.context import CommandContext


class ChartsAPI(PublicNamespace):
    """Framework-neutral charts namespace."""

    def __init__(self, service: object | None = None) -> None:
        super().__init__("charts", service)

    def create(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `charts.create` public operation."""
        return self._invoke("create", context=context, **parameters)

    def generate_from_reference(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `charts.generate_from_reference` public operation."""
        return self._invoke("generate_from_reference", context=context, **parameters)

    def add_account(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `charts.add_account` public operation."""
        return self._invoke("add_account", context=context, **parameters)

    def activate_account(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `charts.activate_account` public operation."""
        return self._invoke("activate_account", context=context, **parameters)

    def deactivate_account(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `charts.deactivate_account` public operation."""
        return self._invoke("deactivate_account", context=context, **parameters)

    def bind_reference(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `charts.bind_reference` public operation."""
        return self._invoke("bind_reference", context=context, **parameters)

    def validate(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `charts.validate` public operation."""
        return self._invoke("validate", context=context, **parameters)

    def activate(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `charts.activate` public operation."""
        return self._invoke("activate", context=context, **parameters)

    def migrate(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `charts.migrate` public operation."""
        return self._invoke("migrate", context=context, **parameters)

    def get(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `charts.get` public operation."""
        return self._invoke("get", context=context, **parameters)

    def search_accounts(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `charts.search_accounts` public operation."""
        return self._invoke("search_accounts", context=context, **parameters)


__all__ = ["ChartsAPI"]
