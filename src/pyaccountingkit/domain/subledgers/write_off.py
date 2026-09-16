"""Fail-closed write-off intent: accounting policy/proposal evidence is mandatory."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.errors import WriteOffPolicyRequiredError


@dataclass(frozen=True, slots=True)
class WriteOffAuthorization:
    policy_set_id: str
    policy_version: str
    proposal_checksum: str

    def __post_init__(self) -> None:
        for name in ("policy_set_id", "policy_version", "proposal_checksum"):
            if not getattr(self, name).strip():
                raise WriteOffPolicyRequiredError(
                    f"write-off authorization requires non-empty {name}"
                )


@dataclass(frozen=True, slots=True)
class WriteOffRequest:
    request_id: str
    entity_id: EntityId
    subledger_id: str
    source_item_id: str
    due_item_id: str
    amount: Money
    authorization: WriteOffAuthorization

    def __post_init__(self) -> None:
        for name in ("request_id", "subledger_id", "source_item_id", "due_item_id"):
            if not getattr(self, name).strip():
                raise WriteOffPolicyRequiredError(f"write-off request {name} must not be empty")
        if self.amount.amount <= 0:
            raise WriteOffPolicyRequiredError("write-off amount must be strictly positive")

    @classmethod
    def create(
        cls,
        *,
        request_id: str,
        entity_id: EntityId,
        subledger_id: str,
        source_item_id: str,
        due_item_id: str,
        amount: Money,
        authorization: WriteOffAuthorization | None,
    ) -> WriteOffRequest:
        if authorization is None:
            raise WriteOffPolicyRequiredError(
                "write-off requires explicit accounting policy/proposal evidence"
            )
        return cls(
            request_id=request_id,
            entity_id=entity_id,
            subledger_id=subledger_id,
            source_item_id=source_item_id,
            due_item_id=due_item_id,
            amount=amount,
            authorization=authorization,
        )


__all__ = ["WriteOffAuthorization", "WriteOffRequest"]
