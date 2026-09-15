"""Explicit fail-closed mapping decisions for generic imports."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pyaccountingkit.core.identifiers import AccountId, JournalId


class ImportMappingStatus(StrEnum):
    RESOLVED = "RESOLVED"
    UNMAPPED = "UNMAPPED"
    AMBIGUOUS = "AMBIGUOUS"
    CANDIDATE = "CANDIDATE"


@dataclass(frozen=True, slots=True)
class ImportAccountMappingDecision:
    source_account_code: str
    status: ImportMappingStatus
    target_account_id: AccountId | None = None
    method: str = "EXPLICIT"
    rationale: str = ""

    @property
    def executable(self) -> bool:
        return self.status is ImportMappingStatus.RESOLVED and self.target_account_id is not None


@dataclass(frozen=True, slots=True)
class ImportJournalMappingDecision:
    source_journal_code: str
    status: ImportMappingStatus
    journal_id: JournalId | None = None
    method: str = "EXPLICIT"
    rationale: str = ""

    @property
    def executable(self) -> bool:
        return self.status is ImportMappingStatus.RESOLVED and self.journal_id is not None


class ExplicitImportAccountMapper:
    """Resolve only configured mappings; never infer by prefix or create accounts."""

    def __init__(self, mappings: dict[str, AccountId]) -> None:
        self._mappings = dict(mappings)

    def resolve(self, source_account_code: str) -> ImportAccountMappingDecision:
        target = self._mappings.get(source_account_code)
        if target is None:
            return ImportAccountMappingDecision(
                source_account_code=source_account_code,
                status=ImportMappingStatus.UNMAPPED,
                rationale="no explicit account mapping",
            )
        return ImportAccountMappingDecision(
            source_account_code=source_account_code,
            status=ImportMappingStatus.RESOLVED,
            target_account_id=target,
        )


class ExplicitImportJournalMapper:
    """Resolve only configured journal mappings; unknown journals are not auto-created."""

    def __init__(self, mappings: dict[str, JournalId]) -> None:
        self._mappings = dict(mappings)

    def resolve(self, source_journal_code: str) -> ImportJournalMappingDecision:
        target = self._mappings.get(source_journal_code)
        if target is None:
            return ImportJournalMappingDecision(
                source_journal_code=source_journal_code,
                status=ImportMappingStatus.UNMAPPED,
                rationale="no explicit journal mapping",
            )
        return ImportJournalMappingDecision(
            source_journal_code=source_journal_code,
            status=ImportMappingStatus.RESOLVED,
            journal_id=target,
        )


__all__ = [
    "ExplicitImportAccountMapper",
    "ExplicitImportJournalMapper",
    "ImportAccountMappingDecision",
    "ImportJournalMappingDecision",
    "ImportMappingStatus",
]
