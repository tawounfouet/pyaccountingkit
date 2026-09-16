"""Subledger-to-control-account reconciliation over an explicit normalized GL balance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pyaccountingkit.core.currency import Currency
from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.control_account import ResolvedControlAccount
from pyaccountingkit.domain.subledgers.errors import SubledgerReconciliationError
from pyaccountingkit.domain.subledgers.open_item import OpenItem


class SubledgerReconciliationStatus(StrEnum):
    MATCHED = "MATCHED"
    DIFFERENCE = "DIFFERENCE"


@dataclass(frozen=True, slots=True)
class SubledgerReconciliation:
    entity_id: EntityId
    subledger_id: str
    as_of: date
    currency: Currency
    control_account_id: str
    control_account_code: str
    chart_id: str
    chart_version: str
    reference_snapshot_id: str
    subledger_open_balance: Money
    normalized_gl_balance: Money
    difference: Money
    source_open_item_ids: tuple[str, ...]
    status: SubledgerReconciliationStatus

    @property
    def matched(self) -> bool:
        return self.status is SubledgerReconciliationStatus.MATCHED


class SubledgerReconciliationService:
    """Compare open-item balance with an already-normalized GL control-account balance."""

    def reconcile(
        self,
        *,
        entity_id: EntityId,
        subledger_id: str,
        as_of: date,
        currency: Currency,
        control_account: ResolvedControlAccount,
        open_items: tuple[OpenItem, ...],
        normalized_gl_balance: Money,
    ) -> SubledgerReconciliation:
        if not subledger_id.strip():
            raise SubledgerReconciliationError("reconciliation subledger_id must not be empty")
        require_same_entity(
            entity_id,
            control_account.entity_id,
            resource="resolved reconciliation control account",
        )
        if control_account.subledger_id != subledger_id:
            raise SubledgerReconciliationError(
                "resolved control account belongs to a different subledger"
            )
        if normalized_gl_balance.currency != currency:
            raise SubledgerReconciliationError("normalized GL balance currency mismatch")
        if normalized_gl_balance.amount < 0:
            raise SubledgerReconciliationError(
                "normalized GL control-account balance must be non-negative"
            )

        total = Money.zero(currency)
        source_ids: list[str] = []
        seen: set[str] = set()
        for open_item in open_items:
            require_same_entity(
                entity_id,
                open_item.entity_id,
                resource=f"open item {open_item.open_item_id}",
            )
            if open_item.subledger_id != subledger_id:
                raise SubledgerReconciliationError(
                    f"open item {open_item.open_item_id!r} belongs to another subledger"
                )
            if open_item.open_amount.currency != currency:
                raise SubledgerReconciliationError(
                    f"open item {open_item.open_item_id!r} currency mismatch"
                )
            if open_item.open_item_id in seen:
                raise SubledgerReconciliationError(
                    f"duplicate reconciliation open item {open_item.open_item_id!r}"
                )
            seen.add(open_item.open_item_id)
            total += open_item.open_amount
            source_ids.append(open_item.open_item_id)

        difference = total - normalized_gl_balance
        status = (
            SubledgerReconciliationStatus.MATCHED
            if difference.is_zero()
            else SubledgerReconciliationStatus.DIFFERENCE
        )
        return SubledgerReconciliation(
            entity_id=entity_id,
            subledger_id=subledger_id,
            as_of=as_of,
            currency=currency,
            control_account_id=str(control_account.account_id),
            control_account_code=control_account.account_code,
            chart_id=control_account.chart_id,
            chart_version=control_account.chart_version,
            reference_snapshot_id=control_account.reference_snapshot_id,
            subledger_open_balance=total,
            normalized_gl_balance=normalized_gl_balance,
            difference=difference,
            source_open_item_ids=tuple(sorted(source_ids)),
            status=status,
        )


__all__ = [
    "SubledgerReconciliation",
    "SubledgerReconciliationService",
    "SubledgerReconciliationStatus",
]
