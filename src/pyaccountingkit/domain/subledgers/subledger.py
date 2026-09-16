"""Subledger definition and entity-scoped instance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.subledgers.errors import InvalidSubledgerConfigurationError
from pyaccountingkit.domain.subledgers.primitives import (
    AuxiliaryMode,
    SubledgerStatus,
    SubledgerType,
)


@dataclass(frozen=True, slots=True)
class SubledgerDefinition:
    definition_id: str
    code: str
    label: str
    subledger_type: SubledgerType
    default_auxiliary_mode: AuxiliaryMode
    effective_from: date
    effective_to: date | None = None

    def __post_init__(self) -> None:
        for name in ("definition_id", "code", "label"):
            if not getattr(self, name).strip():
                raise InvalidSubledgerConfigurationError(f"{name} must not be empty")
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise InvalidSubledgerConfigurationError(
                "subledger definition effective_to must be after effective_from"
            )

    def effective_on(self, accounting_date: date) -> bool:
        return self.effective_from <= accounting_date and (
            self.effective_to is None or accounting_date < self.effective_to
        )


@dataclass(frozen=True, slots=True)
class Subledger:
    subledger_id: str
    entity_id: EntityId
    definition: SubledgerDefinition
    status: SubledgerStatus = SubledgerStatus.ACTIVE

    def __post_init__(self) -> None:
        if not self.subledger_id.strip():
            raise InvalidSubledgerConfigurationError("subledger_id must not be empty")

    @property
    def subledger_type(self) -> SubledgerType:
        return self.definition.subledger_type

    def is_active_on(self, accounting_date: date) -> bool:
        return self.status is SubledgerStatus.ACTIVE and self.definition.effective_on(
            accounting_date
        )


__all__ = ["Subledger", "SubledgerDefinition"]
