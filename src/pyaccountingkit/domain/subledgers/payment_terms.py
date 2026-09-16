"""Deterministic payment-term and due-date schedule generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.due_item import DueItem
from pyaccountingkit.domain.subledgers.errors import InvalidPaymentTermError

_ONE = Decimal("1")
_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class DueDateRule:
    rule_id: str
    days_after_document_date: int
    allocation: Decimal
    order: int

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise InvalidPaymentTermError("due-date rule_id must not be empty")
        if self.days_after_document_date < 0:
            raise InvalidPaymentTermError("days_after_document_date cannot be negative")
        if not isinstance(self.allocation, Decimal):
            raise InvalidPaymentTermError("due-date allocation must be Decimal")
        if not self.allocation.is_finite() or not _ZERO < self.allocation <= _ONE:
            raise InvalidPaymentTermError("due-date allocation must be in (0, 1]")
        if self.order < 0:
            raise InvalidPaymentTermError("due-date rule order cannot be negative")


@dataclass(frozen=True, slots=True)
class PaymentTerm:
    payment_term_id: str
    code: str
    version: str
    rules: tuple[DueDateRule, ...]

    def __post_init__(self) -> None:
        for name in ("payment_term_id", "code", "version"):
            if not getattr(self, name).strip():
                raise InvalidPaymentTermError(f"{name} must not be empty")
        if not self.rules:
            raise InvalidPaymentTermError("payment term requires at least one due-date rule")
        rule_ids = tuple(rule.rule_id for rule in self.rules)
        orders = tuple(rule.order for rule in self.rules)
        if len(set(rule_ids)) != len(rule_ids):
            raise InvalidPaymentTermError("payment-term rule ids must be unique")
        if len(set(orders)) != len(orders):
            raise InvalidPaymentTermError("payment-term rule orders must be unique")
        if sum((rule.allocation for rule in self.rules), start=_ZERO) != _ONE:
            raise InvalidPaymentTermError("payment-term allocations must sum exactly to Decimal('1')")

    @property
    def ordered_rules(self) -> tuple[DueDateRule, ...]:
        return tuple(sorted(self.rules, key=lambda rule: (rule.order, rule.rule_id)))

    def generate_due_items(
        self,
        *,
        entity_id: EntityId,
        source_subledger_item_id: str,
        document_date: date,
        amount: Money,
    ) -> tuple[DueItem, ...]:
        if not source_subledger_item_id.strip():
            raise InvalidPaymentTermError("source_subledger_item_id must not be empty")
        if amount.amount <= 0:
            raise InvalidPaymentTermError("payment-term source amount must be strictly positive")

        rules = self.ordered_rules
        allocated = Money.zero(amount.currency)
        due_items: list[DueItem] = []
        for index, rule in enumerate(rules):
            if index == len(rules) - 1:
                due_amount = amount - allocated
            else:
                due_amount = amount * rule.allocation
                allocated += due_amount
            if due_amount.amount <= 0:
                raise InvalidPaymentTermError(
                    "payment-term rounding produced a non-positive due amount"
                )
            due_items.append(
                DueItem.create(
                    due_item_id=(
                        f"{source_subledger_item_id}:due:{self.payment_term_id}:"
                        f"{self.version}:{rule.rule_id}"
                    ),
                    entity_id=entity_id,
                    source_subledger_item_id=source_subledger_item_id,
                    due_date=document_date + timedelta(days=rule.days_after_document_date),
                    original_amount=due_amount,
                )
            )

        total = Money.zero(amount.currency)
        for due_item in due_items:
            total += due_item.original_amount
        if total != amount:
            raise InvalidPaymentTermError(
                "generated due-item amounts must reconcile exactly to source amount"
            )
        return tuple(due_items)


__all__ = ["DueDateRule", "PaymentTerm"]
