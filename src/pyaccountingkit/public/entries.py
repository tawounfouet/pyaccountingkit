"""Public journal-entry facade."""

from __future__ import annotations

from pyaccountingkit.public._base import PublicNamespace
from pyaccountingkit.public.context import CommandContext


class EntriesAPI(PublicNamespace):
    """Framework-neutral entries namespace."""

    def __init__(self, service: object | None = None) -> None:
        super().__init__("entries", service)

    def create(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `entries.create` public operation."""
        return self._invoke("create", context=context, **parameters)

    def add_line(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `entries.add_line` public operation."""
        return self._invoke("add_line", context=context, **parameters)

    def remove_line(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `entries.remove_line` public operation."""
        return self._invoke("remove_line", context=context, **parameters)

    def validate(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `entries.validate` public operation."""
        return self._invoke("validate", context=context, **parameters)

    def post(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `entries.post` public operation."""
        return self._invoke("post", context=context, **parameters)

    def reverse(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `entries.reverse` public operation."""
        return self._invoke("reverse", context=context, **parameters)

    def get(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `entries.get` public operation."""
        return self._invoke("get", context=context, **parameters)

    def list(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `entries.list` public operation."""
        return self._invoke("list", context=context, **parameters)


__all__ = ["EntriesAPI"]
