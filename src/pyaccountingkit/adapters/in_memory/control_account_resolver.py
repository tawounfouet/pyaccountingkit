"""In-memory reference adapter for LOT-18 control-account resolution."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from pyaccountingkit.core.currency import Currency
from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.errors import InactiveAccountError, NonPostableAccountError, UnknownAccountError
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.subledgers.control_account import (
    ControlAccountBinding,
    ResolvedControlAccount,
)
from pyaccountingkit.domain.subledgers.errors import (
    AmbiguousControlAccountError,
    ControlAccountNotConfiguredError,
)
from pyaccountingkit.domain.subledgers.primitives import SubledgerPartyType
from pyaccountingkit.ports.company_chart_resolution import CompanyChartResolverProtocol


class InMemoryControlAccountResolver:
    """Resolve one effective binding, then validate the account in the applicable chart."""

    def __init__(
        self,
        *,
        bindings: Iterable[ControlAccountBinding],
        chart_resolver: CompanyChartResolverProtocol,
    ) -> None:
        self._bindings = tuple(bindings)
        self._chart_resolver = chart_resolver

    def resolve(
        self,
        *,
        entity_id: EntityId,
        subledger_id: str,
        accounting_date: date,
        party_type: SubledgerPartyType | None = None,
        currency: Currency | None = None,
    ) -> ResolvedControlAccount:
        candidates = tuple(
            binding
            for binding in self._bindings
            if binding.matches(
                entity_id=entity_id,
                subledger_id=subledger_id,
                accounting_date=accounting_date,
                party_type=party_type,
                currency=currency,
            )
        )
        if not candidates:
            raise ControlAccountNotConfiguredError(
                "no active/effective control-account binding matches the subledger context"
            )

        max_specificity = max(binding.specificity() for binding in candidates)
        most_specific = tuple(
            binding for binding in candidates if binding.specificity() == max_specificity
        )
        if len(most_specific) != 1:
            raise AmbiguousControlAccountError(
                "multiple control-account bindings match with the same specificity: "
                + ", ".join(sorted(binding.binding_id for binding in most_specific))
            )
        binding = most_specific[0]

        resolved_chart = self._chart_resolver.resolve(
            entity_id=entity_id,
            accounting_date=accounting_date,
        )
        account = resolved_chart.chart.get_by_id(binding.company_account_id)
        if account is None:
            raise UnknownAccountError(
                f"control account {binding.company_account_id!s} is absent from "
                f"chart version {resolved_chart.chart_version!r}"
            )
        require_same_entity(
            entity_id,
            account.entity_id,
            resource=f"control account {account.id}",
        )
        if not account.active:
            raise InactiveAccountError(f"control account {account.code!r} is inactive")
        if not account.postable:
            raise NonPostableAccountError(f"control account {account.code!r} is not postable")

        return ResolvedControlAccount(
            binding_id=binding.binding_id,
            account_id=account.id,
            account_code=account.code,
            entity_id=entity_id,
            subledger_id=subledger_id,
            chart_id=resolved_chart.chart_id,
            chart_version=resolved_chart.chart_version,
            reference_snapshot_id=resolved_chart.reference_snapshot_id,
        )


__all__ = ["InMemoryControlAccountResolver"]
