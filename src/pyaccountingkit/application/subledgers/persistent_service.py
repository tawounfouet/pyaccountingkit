"""Persistent application chain for operational subledgers."""

from __future__ import annotations

from datetime import date, datetime

from pyaccountingkit.application.ledger.posting_orchestrator import PostingOrchestrator
from pyaccountingkit.application.ledger.reversal_orchestrator import ReversalOrchestrator
from pyaccountingkit.core.currency import Currency
from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.identifiers import EntityId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.subledgers.accounting_reference import PostedAccountingReference
from pyaccountingkit.domain.subledgers.aging import (
    AgingEngine,
    AgingPolicy,
    AgingSnapshot,
    AgingSourceItem,
)
from pyaccountingkit.domain.subledgers.allocation import (
    AllocationResult,
    SettlementAllocationService,
    SubledgerItem,
)
from pyaccountingkit.domain.subledgers.control_account import ResolvedControlAccount
from pyaccountingkit.domain.subledgers.errors import InvalidSubledgerItemError
from pyaccountingkit.domain.subledgers.matching import AccountingMatch, MatchingCandidate
from pyaccountingkit.domain.subledgers.open_item import OpenItem
from pyaccountingkit.domain.subledgers.parties import SubledgerParty
from pyaccountingkit.domain.subledgers.payable import Payable
from pyaccountingkit.domain.subledgers.receivable import Receivable
from pyaccountingkit.domain.subledgers.reconciliation import (
    SubledgerReconciliation,
    SubledgerReconciliationService,
)
from pyaccountingkit.domain.subledgers.settlement import Settlement
from pyaccountingkit.domain.subledgers.settlement_reversal import (
    SettlementReversalResult,
    SettlementReversalService,
)
from pyaccountingkit.ports.unit_of_work import UnitOfWorkFactoryProtocol, UnitOfWorkProtocol


class _SubledgerServiceBase:
    def __init__(self, uow_factory: UnitOfWorkFactoryProtocol) -> None:
        self._uow_factory = uow_factory


class PersistentPartnersService(_SubledgerServiceBase):
    def create(
        self,
        *,
        party: SubledgerParty,
        context: object | None = None,
    ) -> SubledgerParty:
        del context
        with self._uow_factory.open() as uow:
            uow.subledgers.add_party(party)
            uow.commit()
        return party

    def get(
        self,
        *,
        party_id: str,
        context: object | None = None,
    ) -> SubledgerParty:
        del context
        with self._uow_factory.open() as uow:
            return uow.subledgers.get_party(party_id)

    def list(
        self,
        *,
        entity_id: EntityId,
        context: object | None = None,
    ) -> tuple[SubledgerParty, ...]:
        del context
        with self._uow_factory.open() as uow:
            return uow.subledgers.list_parties(entity_id)


class _PersistentItemsService(_SubledgerServiceBase):
    def __init__(
        self,
        uow_factory: UnitOfWorkFactoryProtocol,
        posting_orchestrator: PostingOrchestrator,
    ) -> None:
        super().__init__(uow_factory)
        self._posting_orchestrator = posting_orchestrator

    @staticmethod
    def _require_party(uow: UnitOfWorkProtocol, item: Receivable | Payable) -> None:
        party = uow.subledgers.get_party(item.party_id)
        require_same_entity(
            item.entity_id,
            party.entity_id,
            resource=f"subledger party {party.party_id}",
        )


class PersistentReceivablesService(_PersistentItemsService):
    def recognize(
        self,
        *,
        receivable: Receivable,
        entry: JournalEntry,
        actor_id: str,
        context: object | None = None,
    ) -> Receivable:
        del context
        with self._uow_factory.open() as uow:
            self._require_party(uow, receivable)
            posting = self._posting_orchestrator.post_in_uow(
                uow,
                entry,
                actor_id,
                expected_entity_id=receivable.entity_id,
            )
            reference = PostedAccountingReference.from_posted_entry(
                posting.posted_entry,
                entry_entity_id=receivable.entity_id,
            )
            recognized = receivable.open().link_posted_accounting(reference)
            uow.subledgers.add_receivable(recognized)
            uow.commit()
        return recognized

    def get(
        self,
        *,
        receivable_id: str,
        context: object | None = None,
    ) -> Receivable:
        del context
        with self._uow_factory.open() as uow:
            return uow.subledgers.get_receivable(receivable_id)

    def list_open(
        self,
        *,
        entity_id: EntityId,
        subledger_id: str,
        party_id: str | None = None,
        context: object | None = None,
    ) -> tuple[Receivable, ...]:
        del context
        with self._uow_factory.open() as uow:
            return uow.subledgers.list_open_receivables(
                entity_id,
                subledger_id,
                party_id=party_id,
            )


class PersistentPayablesService(_PersistentItemsService):
    def recognize(
        self,
        *,
        payable: Payable,
        entry: JournalEntry,
        actor_id: str,
        context: object | None = None,
    ) -> Payable:
        del context
        with self._uow_factory.open() as uow:
            self._require_party(uow, payable)
            posting = self._posting_orchestrator.post_in_uow(
                uow,
                entry,
                actor_id,
                expected_entity_id=payable.entity_id,
            )
            reference = PostedAccountingReference.from_posted_entry(
                posting.posted_entry,
                entry_entity_id=payable.entity_id,
            )
            recognized = payable.open().link_posted_accounting(reference)
            uow.subledgers.add_payable(recognized)
            uow.commit()
        return recognized

    def get(
        self,
        *,
        payable_id: str,
        context: object | None = None,
    ) -> Payable:
        del context
        with self._uow_factory.open() as uow:
            return uow.subledgers.get_payable(payable_id)

    def list_open(
        self,
        *,
        entity_id: EntityId,
        subledger_id: str,
        party_id: str | None = None,
        context: object | None = None,
    ) -> tuple[Payable, ...]:
        del context
        with self._uow_factory.open() as uow:
            return uow.subledgers.list_open_payables(
                entity_id,
                subledger_id,
                party_id=party_id,
            )


class PersistentSettlementsService(_SubledgerServiceBase):
    def __init__(
        self,
        uow_factory: UnitOfWorkFactoryProtocol,
        posting_orchestrator: PostingOrchestrator,
        reversal_orchestrator: ReversalOrchestrator,
        *,
        allocation_service: SettlementAllocationService | None = None,
        settlement_reversal_service: SettlementReversalService | None = None,
    ) -> None:
        super().__init__(uow_factory)
        self._posting_orchestrator = posting_orchestrator
        self._reversal_orchestrator = reversal_orchestrator
        self._allocation_service = allocation_service or SettlementAllocationService()
        self._settlement_reversal_service = (
            settlement_reversal_service or SettlementReversalService(self._allocation_service)
        )

    def record(
        self,
        *,
        settlement: Settlement,
        entry: JournalEntry,
        actor_id: str,
        context: object | None = None,
    ) -> Settlement:
        del context
        with self._uow_factory.open() as uow:
            if settlement.party_id is not None:
                party = uow.subledgers.get_party(settlement.party_id)
                require_same_entity(
                    settlement.entity_id,
                    party.entity_id,
                    resource=f"subledger party {party.party_id}",
                )
            posting = self._posting_orchestrator.post_in_uow(
                uow,
                entry,
                actor_id,
                expected_entity_id=settlement.entity_id,
            )
            reference = PostedAccountingReference.from_posted_entry(
                posting.posted_entry,
                entry_entity_id=settlement.entity_id,
            )
            recorded = settlement.link_posted_accounting(reference)
            uow.subledgers.add_settlement(recorded)
            uow.commit()
        return recorded

    def allocate(
        self,
        *,
        allocation_id: str,
        settlement_id: str,
        source_item_id: str,
        due_item_id: str,
        amount: Money,
        allocation_date: date,
        expected_settlement_revision: int | None = None,
        expected_due_item_revision: int | None = None,
        context: object | None = None,
    ) -> AllocationResult:
        del context
        with self._uow_factory.open() as uow:
            settlement = uow.subledgers.get_settlement(settlement_id, for_update=True)
            item = _get_item(uow, source_item_id, for_update=True)
            result = self._allocation_service.allocate(
                allocation_id=allocation_id,
                settlement=settlement,
                subledger_item=item,
                due_item_id=due_item_id,
                amount=amount,
                allocation_date=allocation_date,
                expected_settlement_revision=expected_settlement_revision,
                expected_due_item_revision=expected_due_item_revision,
            )
            uow.subledgers.save_settlement(result.settlement)
            _save_item(uow, result.subledger_item)
            uow.subledgers.add_allocation(result.allocation)
            uow.commit()
        return result

    def reverse(
        self,
        *,
        settlement_id: str,
        target_period_id: PeriodId,
        reversal_date: date,
        actor_id: str,
        reversal_id: str,
        reason: str,
        reversed_at: datetime,
        expected_settlement_revision: int | None = None,
        expected_due_item_revisions: dict[str, int] | None = None,
        context: object | None = None,
    ) -> SettlementReversalResult:
        del context
        with self._uow_factory.open() as uow:
            settlement = uow.subledgers.get_settlement(settlement_id, for_update=True)
            if settlement.accounting_reference is None:
                raise InvalidSubledgerItemError(
                    "settlement reversal requires persisted posted accounting reference"
                )
            gl_reversal = self._reversal_orchestrator.reverse_in_uow(
                uow,
                settlement.accounting_reference.entry_id,
                target_period_id,
                reversal_date,
                actor_id,
            )
            accounting_reversal_reference = PostedAccountingReference.from_posted_entry(
                gl_reversal.reversal_entry,
                entry_entity_id=settlement.entity_id,
            )
            allocations = uow.subledgers.list_allocations(
                settlement_id,
                for_update=True,
            )
            source_ids = tuple(
                sorted(
                    {
                        allocation.source_item_id
                        for allocation in allocations
                        if allocation.settlement_id == settlement_id
                    }
                )
            )
            items = tuple(_get_item(uow, item_id, for_update=True) for item_id in source_ids)
            result = self._settlement_reversal_service.reverse(
                reversal_id=reversal_id,
                settlement=settlement,
                subledger_items=items,
                allocations=allocations,
                reversed_at=reversed_at,
                accounting_reversal_reference=accounting_reversal_reference,
                reason=reason,
                expected_settlement_revision=expected_settlement_revision,
                expected_due_item_revisions=expected_due_item_revisions,
            )
            uow.subledgers.save_settlement(result.settlement)
            for item in result.subledger_items:
                _save_item(uow, item)
            for allocation in result.allocations:
                uow.subledgers.save_allocation(allocation)
            uow.subledgers.append_reversal(result.reversal)
            uow.commit()
        return result


class PersistentMatchingService(_SubledgerServiceBase):
    def suggest(
        self,
        *,
        candidate: MatchingCandidate,
        context: object | None = None,
    ) -> MatchingCandidate:
        del context
        return candidate

    def validate(
        self,
        *,
        candidate: MatchingCandidate,
        match_id: str,
        validated_at: datetime,
        residual_amount: Money | None = None,
        context: object | None = None,
    ) -> AccountingMatch:
        del context
        match = candidate.validate(
            match_id=match_id,
            validated_at=validated_at,
            residual_amount=residual_amount,
        )
        with self._uow_factory.open() as uow:
            uow.subledgers.add_match(match)
            uow.commit()
        return match


class PersistentSubledgerApplicationService(_SubledgerServiceBase):
    """Composition service consumed directly by the public SubledgersAPI."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactoryProtocol,
        posting_orchestrator: PostingOrchestrator,
        reversal_orchestrator: ReversalOrchestrator,
        *,
        allocation_service: SettlementAllocationService | None = None,
        settlement_reversal_service: SettlementReversalService | None = None,
        aging_engine: AgingEngine | None = None,
        reconciliation_service: SubledgerReconciliationService | None = None,
    ) -> None:
        super().__init__(uow_factory)
        self.partners = PersistentPartnersService(uow_factory)
        self.receivables = PersistentReceivablesService(uow_factory, posting_orchestrator)
        self.payables = PersistentPayablesService(uow_factory, posting_orchestrator)
        self.settlements = PersistentSettlementsService(
            uow_factory,
            posting_orchestrator,
            reversal_orchestrator,
            allocation_service=allocation_service,
            settlement_reversal_service=settlement_reversal_service,
        )
        self.matching = PersistentMatchingService(uow_factory)
        self._aging_engine = aging_engine or AgingEngine()
        self._reconciliation_service = reconciliation_service or SubledgerReconciliationService()

    def aging(
        self,
        *,
        entity_id: EntityId,
        subledger_id: str,
        item_type: str,
        as_of: date,
        currency: Currency,
        policy: AgingPolicy,
        party_id: str | None = None,
        context: object | None = None,
    ) -> AgingSnapshot:
        del context
        with self._uow_factory.open() as uow:
            items = _list_open_items(
                uow,
                item_type=item_type,
                entity_id=entity_id,
                subledger_id=subledger_id,
                party_id=party_id,
            )
        sources: list[AgingSourceItem] = []
        for item in items:
            for due_item in item.due_items:
                if due_item.open_amount.is_zero():
                    continue
                source = (
                    AgingSourceItem.from_receivable(item, due_item)
                    if isinstance(item, Receivable)
                    else AgingSourceItem.from_payable(item, due_item)
                )
                sources.append(source)
        return self._aging_engine.snapshot(
            entity_id=entity_id,
            subledger_id=subledger_id,
            as_of=as_of,
            currency=currency,
            policy=policy,
            sources=tuple(sources),
        )

    def reconcile(
        self,
        *,
        entity_id: EntityId,
        subledger_id: str,
        item_type: str,
        as_of: date,
        currency: Currency,
        control_account: ResolvedControlAccount,
        normalized_gl_balance: Money,
        party_id: str | None = None,
        context: object | None = None,
    ) -> SubledgerReconciliation:
        del context
        with self._uow_factory.open() as uow:
            items = _list_open_items(
                uow,
                item_type=item_type,
                entity_id=entity_id,
                subledger_id=subledger_id,
                party_id=party_id,
            )
        open_items: list[OpenItem] = []
        for item in items:
            for due_item in item.due_items:
                if due_item.open_amount.is_zero():
                    continue
                open_item_id = f"{_item_id(item)}:{due_item.due_item_id}"
                open_item = (
                    OpenItem.from_receivable(
                        open_item_id=open_item_id,
                        receivable=item,
                        due_item=due_item,
                    )
                    if isinstance(item, Receivable)
                    else OpenItem.from_payable(
                        open_item_id=open_item_id,
                        payable=item,
                        due_item=due_item,
                    )
                )
                open_items.append(open_item)
        return self._reconciliation_service.reconcile(
            entity_id=entity_id,
            subledger_id=subledger_id,
            as_of=as_of,
            currency=currency,
            control_account=control_account,
            open_items=tuple(open_items),
            normalized_gl_balance=normalized_gl_balance,
        )


def _get_item(
    uow: UnitOfWorkProtocol,
    item_id: str,
    *,
    for_update: bool,
) -> SubledgerItem:
    try:
        return uow.subledgers.get_receivable(item_id, for_update=for_update)
    except InvalidSubledgerItemError:
        return uow.subledgers.get_payable(item_id, for_update=for_update)


def _save_item(uow: UnitOfWorkProtocol, item: SubledgerItem) -> None:
    if isinstance(item, Receivable):
        uow.subledgers.save_receivable(item)
    else:
        uow.subledgers.save_payable(item)


def _list_open_items(
    uow: UnitOfWorkProtocol,
    *,
    item_type: str,
    entity_id: EntityId,
    subledger_id: str,
    party_id: str | None,
) -> tuple[SubledgerItem, ...]:
    if item_type == "receivable":
        return uow.subledgers.list_open_receivables(
            entity_id,
            subledger_id,
            party_id=party_id,
        )
    if item_type == "payable":
        return uow.subledgers.list_open_payables(
            entity_id,
            subledger_id,
            party_id=party_id,
        )
    raise InvalidSubledgerItemError(
        "item_type must be either 'receivable' or 'payable'"
    )


def _item_id(item: SubledgerItem) -> str:
    return item.receivable_id if isinstance(item, Receivable) else item.payable_id


__all__ = [
    "PersistentMatchingService",
    "PersistentPartnersService",
    "PersistentPayablesService",
    "PersistentReceivablesService",
    "PersistentSettlementsService",
    "PersistentSubledgerApplicationService",
]
