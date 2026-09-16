"""Unit qualification for LOT-18 subledger foundations."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import EntityScopeMismatchError
from pyaccountingkit.core.identifiers import AccountId, EntityId, EntryId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.subledgers.accounting_reference import PostedAccountingReference
from pyaccountingkit.domain.subledgers.auxiliary import AuxiliaryReference
from pyaccountingkit.domain.subledgers.due_item import DueItem
from pyaccountingkit.domain.subledgers.errors import (
    AuxiliaryPolicyNotActiveError,
    AuxiliaryPolicyNotEffectiveError,
    InvalidDueItemError,
    InvalidSubledgerConfigurationError,
    InvalidSubledgerItemError,
    SubledgerAccountingLinkError,
)
from pyaccountingkit.domain.subledgers.open_item import OpenItem
from pyaccountingkit.domain.subledgers.payable import Payable
from pyaccountingkit.domain.subledgers.policy import AuxiliaryAccountingPolicy
from pyaccountingkit.domain.subledgers.primitives import (
    AccountingEffectStatus,
    AuxiliaryMode,
    AuxiliaryPolicyStatus,
)
from pyaccountingkit.domain.subledgers.receivable import Receivable

ENTITY = EntityId("ent")
OTHER_ENTITY = EntityId("other")
AR = "subledger:ar"
AP = "subledger:ap"


def _money(value: str) -> Money:
    return Money.from_str(value, EUR)


def _due(item_id: str, due_id: str, amount: str, *, entity_id: EntityId = ENTITY) -> DueItem:
    return DueItem.create(
        due_item_id=due_id,
        entity_id=entity_id,
        source_subledger_item_id=item_id,
        due_date=date(2026, 10, 31),
        original_amount=_money(amount),
    )


def _posted_reference(entity_id: EntityId = ENTITY) -> PostedAccountingReference:
    return PostedAccountingReference(
        entity_id=entity_id,
        entry_id=EntryId("entry:posted"),
        posted_at=datetime(2026, 9, 16, 8, 0, tzinfo=timezone.utc),
    )


def _entry(*, status: EntryStatus, posted_at: datetime | None = None) -> JournalEntry:
    return JournalEntry(
        id=EntryId("entry:1"),
        journal_id=JournalId("journal:sales"),
        period_id=PeriodId("period:2026-09"),
        entry_date=date(2026, 9, 16),
        description="customer invoice",
        lines=(
            JournalLine(
                account_id=AccountId("411000"),
                debit=_money("100.00"),
                credit=Money.zero(EUR),
            ),
            JournalLine(
                account_id=AccountId("706000"),
                debit=Money.zero(EUR),
                credit=_money("100.00"),
            ),
        ),
        status=status,
        posted_at=posted_at,
    )


def test_due_item_starts_fully_open() -> None:
    due = _due("rec:1", "due:1", "100.00")
    assert due.open_amount == due.original_amount


def test_due_item_rejects_pre_settled_amount_in_lot18() -> None:
    with pytest.raises(InvalidDueItemError):
        DueItem(
            due_item_id="due:1",
            entity_id=ENTITY,
            source_subledger_item_id="rec:1",
            due_date=date(2026, 10, 31),
            original_amount=_money("100.00"),
            open_amount=_money("80.00"),
        )


def test_receivable_requires_due_schedule_to_reconcile_original_amount() -> None:
    with pytest.raises(InvalidSubledgerItemError):
        Receivable(
            receivable_id="rec:1",
            entity_id=ENTITY,
            subledger_id=AR,
            party_id="party:customer",
            source_document_ref="invoice:1",
            original_amount=_money("100.00"),
            accounting_date=date(2026, 9, 16),
            due_items=(_due("rec:1", "due:1", "90.00"),),
        )


def test_receivable_rejects_cross_entity_due_item() -> None:
    with pytest.raises(EntityScopeMismatchError):
        Receivable(
            receivable_id="rec:1",
            entity_id=ENTITY,
            subledger_id=AR,
            party_id="party:customer",
            source_document_ref="invoice:1",
            original_amount=_money("100.00"),
            accounting_date=date(2026, 9, 16),
            due_items=(_due("rec:1", "due:1", "100.00", entity_id=OTHER_ENTITY),),
        )


def test_receivable_operational_and_accounting_states_are_distinct() -> None:
    receivable = Receivable(
        receivable_id="rec:1",
        entity_id=ENTITY,
        subledger_id=AR,
        party_id="party:customer",
        source_document_ref="invoice:1",
        original_amount=_money("100.00"),
        accounting_date=date(2026, 9, 16),
        due_items=(_due("rec:1", "due:1", "100.00"),),
    )

    opened = receivable.open()
    assert opened.operational_status.value == "OPEN"
    assert opened.accounting_status is AccountingEffectStatus.PENDING
    assert not opened.accounting_effective

    posted = opened.link_posted_accounting(_posted_reference())
    assert posted.operational_status.value == "OPEN"
    assert posted.accounting_status is AccountingEffectStatus.POSTED
    assert posted.accounting_effective


def test_payable_uses_same_due_item_invariants() -> None:
    payable = Payable(
        payable_id="pay:1",
        entity_id=ENTITY,
        subledger_id=AP,
        party_id="party:supplier",
        source_document_ref="supplier-invoice:1",
        original_amount=_money("120.00"),
        accounting_date=date(2026, 9, 16),
        due_items=(
            _due("pay:1", "due:a", "60.00"),
            _due("pay:1", "due:b", "60.00"),
        ),
    )
    assert payable.original_amount == _money("120.00")
    assert len(payable.due_items) == 2


def test_open_item_requires_accounting_effective_parent() -> None:
    due = _due("rec:1", "due:1", "100.00")
    receivable = Receivable(
        receivable_id="rec:1",
        entity_id=ENTITY,
        subledger_id=AR,
        party_id="party:customer",
        source_document_ref="invoice:1",
        original_amount=_money("100.00"),
        accounting_date=date(2026, 9, 16),
        due_items=(due,),
    )
    with pytest.raises(InvalidSubledgerItemError):
        OpenItem.from_receivable(open_item_id="open:1", receivable=receivable, due_item=due)


def test_open_item_is_derived_from_due_item_not_gl_line() -> None:
    due = _due("rec:1", "due:1", "100.00")
    receivable = Receivable(
        receivable_id="rec:1",
        entity_id=ENTITY,
        subledger_id=AR,
        party_id="party:customer",
        source_document_ref="invoice:1",
        original_amount=_money("100.00"),
        accounting_date=date(2026, 9, 16),
        due_items=(due,),
    ).link_posted_accounting(_posted_reference())

    open_item = OpenItem.from_receivable(
        open_item_id="open:1",
        receivable=receivable,
        due_item=due,
    )

    assert open_item.source_item_id == "rec:1"
    assert open_item.due_item_id == "due:1"
    assert open_item.open_amount == _money("100.00")
    assert open_item.accounting_reference.entry_id == EntryId("entry:posted")


def test_posted_accounting_reference_rejects_draft_entry() -> None:
    with pytest.raises(SubledgerAccountingLinkError):
        PostedAccountingReference.from_posted_entry(
            _entry(status=EntryStatus.DRAFT),
            entry_entity_id=ENTITY,
        )


def test_posted_accounting_reference_accepts_posted_entry() -> None:
    posted_at = datetime(2026, 9, 16, 8, 0, tzinfo=timezone.utc)
    reference = PostedAccountingReference.from_posted_entry(
        _entry(status=EntryStatus.POSTED, posted_at=posted_at),
        entry_entity_id=ENTITY,
    )
    assert reference.entry_id == EntryId("entry:1")
    assert reference.posted_at == posted_at


def test_auxiliary_policy_is_fail_closed_for_lifecycle_and_effectivity() -> None:
    draft = AuxiliaryAccountingPolicy(
        policy_id="policy:ar",
        entity_id=ENTITY,
        subledger_id=AR,
        version="1",
        auxiliary_mode=AuxiliaryMode.SUBLEDGER,
        status=AuxiliaryPolicyStatus.DRAFT,
        effective_from=date(2026, 1, 1),
    )
    with pytest.raises(AuxiliaryPolicyNotActiveError):
        draft.assert_executable(
            entity_id=ENTITY,
            subledger_id=AR,
            accounting_date=date(2026, 9, 16),
        )

    active = AuxiliaryAccountingPolicy(
        policy_id="policy:ar",
        entity_id=ENTITY,
        subledger_id=AR,
        version="2",
        auxiliary_mode=AuxiliaryMode.SUBLEDGER,
        status=AuxiliaryPolicyStatus.ACTIVE,
        effective_from=date(2027, 1, 1),
    )
    with pytest.raises(AuxiliaryPolicyNotEffectiveError):
        active.assert_executable(
            entity_id=ENTITY,
            subledger_id=AR,
            accounting_date=date(2026, 9, 16),
        )


def test_auxiliary_policy_can_require_explicit_auxiliary_reference() -> None:
    policy = AuxiliaryAccountingPolicy(
        policy_id="policy:ar",
        entity_id=ENTITY,
        subledger_id=AR,
        version="1",
        auxiliary_mode=AuxiliaryMode.SUBLEDGER,
        status=AuxiliaryPolicyStatus.ACTIVE,
        effective_from=date(2026, 1, 1),
        require_auxiliary_reference=True,
    )
    with pytest.raises(InvalidSubledgerConfigurationError):
        policy.assert_executable(
            entity_id=ENTITY,
            subledger_id=AR,
            accounting_date=date(2026, 9, 16),
        )

    policy.assert_executable(
        entity_id=ENTITY,
        subledger_id=AR,
        accounting_date=date(2026, 9, 16),
        auxiliary_reference=AuxiliaryReference(system="FEC", code="CUST001"),
    )
