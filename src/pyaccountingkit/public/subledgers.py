"""Framework-neutral public subledger facade."""

from __future__ import annotations

from pyaccountingkit.public._base import PublicNamespace
from pyaccountingkit.public.context import CommandContext


class PartnersAPI(PublicNamespace):
    def __init__(self, service: object | None = None) -> None:
        super().__init__("subledgers.partners", service)

    def create(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        return self._invoke("create", context=context, **parameters)

    def get(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        return self._invoke("get", context=context, **parameters)

    def list(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        return self._invoke("list", context=context, **parameters)


class ReceivablesAPI(PublicNamespace):
    def __init__(self, service: object | None = None) -> None:
        super().__init__("subledgers.receivables", service)

    def recognize(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        return self._invoke("recognize", context=context, **parameters)

    def get(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        return self._invoke("get", context=context, **parameters)

    def list_open(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        return self._invoke("list_open", context=context, **parameters)


class PayablesAPI(PublicNamespace):
    def __init__(self, service: object | None = None) -> None:
        super().__init__("subledgers.payables", service)

    def recognize(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        return self._invoke("recognize", context=context, **parameters)

    def get(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        return self._invoke("get", context=context, **parameters)

    def list_open(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        return self._invoke("list_open", context=context, **parameters)


class SettlementsAPI(PublicNamespace):
    def __init__(self, service: object | None = None) -> None:
        super().__init__("subledgers.settlements", service)

    def record(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        return self._invoke("record", context=context, **parameters)

    def allocate(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        return self._invoke("allocate", context=context, **parameters)

    def reverse(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        return self._invoke("reverse", context=context, **parameters)


class MatchingAPI(PublicNamespace):
    def __init__(self, service: object | None = None) -> None:
        super().__init__("subledgers.matching", service)

    def suggest(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        return self._invoke("suggest", context=context, **parameters)

    def validate(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        return self._invoke("validate", context=context, **parameters)


class SubledgersAPI(PublicNamespace):
    """Root subledger namespace with explicit operational child facades."""

    __slots__ = ("partners", "payables", "receivables", "settlements", "matching")

    def __init__(self, service: object | None = None) -> None:
        super().__init__("subledgers", service)
        self.partners = PartnersAPI(self._child_service("partners"))
        self.receivables = ReceivablesAPI(self._child_service("receivables"))
        self.payables = PayablesAPI(self._child_service("payables"))
        self.settlements = SettlementsAPI(self._child_service("settlements"))
        self.matching = MatchingAPI(self._child_service("matching"))

    def reconcile(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        return self._invoke("reconcile", context=context, **parameters)

    def aging(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        return self._invoke("aging", context=context, **parameters)


__all__ = [
    "MatchingAPI",
    "PartnersAPI",
    "PayablesAPI",
    "ReceivablesAPI",
    "SettlementsAPI",
    "SubledgersAPI",
]
