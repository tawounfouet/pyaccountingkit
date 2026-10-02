"""Resolved effective account plans supplied by regulatory providers (LOT-27)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class EffectiveAccountOrigin(StrEnum):
    """Observed origins in provider-resolved effective account plans."""

    INHERITED_FROM_BASE_STANDARD = "inherited_from_base_standard"
    EXTENSION_OVERRIDE = "extension_override"
    EXTENSION_ADDITION = "extension_addition"


@dataclass(frozen=True, slots=True)
class RegulatorySourceReference:
    """Traceable source location attached to one regulatory fact."""

    document_id: str
    section: str
    snippet: str
    page_pdf: int | None = None
    source_line_md: int | None = None

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("document_id must be non-empty")
        if not self.section.strip():
            raise ValueError("section must be non-empty")
        if not self.snippet.strip():
            raise ValueError("snippet must be non-empty")


@dataclass(frozen=True, slots=True)
class EffectiveReferenceAccount:
    """One account from a provider-resolved effective plan."""

    account_id: str
    ref_code: str
    label: str
    origin: EffectiveAccountOrigin
    provenance_type: str
    base_account_id: str | None = None
    base_label: str | None = None
    extension_source_ref: RegulatorySourceReference | None = None

    def __post_init__(self) -> None:
        if not self.account_id.strip() or not self.ref_code.strip() or not self.label.strip():
            raise ValueError("effective account identity fields must be non-empty")
        if not self.provenance_type.strip():
            raise ValueError("provenance_type must be non-empty")

        if self.origin is EffectiveAccountOrigin.INHERITED_FROM_BASE_STANDARD:
            if self.base_account_id is None:
                raise ValueError("inherited account requires base_account_id")
            if self.extension_source_ref is not None:
                raise ValueError("inherited account cannot carry extension_source_ref")
        elif self.origin is EffectiveAccountOrigin.EXTENSION_OVERRIDE:
            if self.base_account_id is None or self.extension_source_ref is None:
                raise ValueError("extension override requires base account and source reference")
        elif self.origin is EffectiveAccountOrigin.EXTENSION_ADDITION:
            if self.base_account_id is not None or self.extension_source_ref is None:
                raise ValueError("extension addition requires source and no base account")


@dataclass(frozen=True, slots=True)
class EffectiveAccountPlan:
    """Immutable effective plan already resolved by the regulatory source."""

    standard_id: str
    edition: str
    base_standard: str
    accounts: tuple[EffectiveReferenceAccount, ...]
    inheritance_rule: str = ""
    statistics: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.standard_id.strip() or not self.edition.strip() or not self.base_standard.strip():
            raise ValueError("effective plan coordinates must be non-empty")
        if not self.accounts:
            raise ValueError("effective plan must contain accounts")

        account_ids = [account.account_id for account in self.accounts]
        ref_codes = [account.ref_code for account in self.accounts]
        if len(account_ids) != len(set(account_ids)):
            raise ValueError("effective plan contains duplicate account_id")
        if len(ref_codes) != len(set(ref_codes)):
            raise ValueError("effective plan contains duplicate ref_code")

        prefix = f"account:{self.standard_id}:{self.edition}:"
        if any(not account.account_id.startswith(prefix) for account in self.accounts):
            raise ValueError("effective account_id does not match plan coordinates")

        observed = Counter(account.origin.value for account in self.accounts)
        expected = {
            "inherited": observed[EffectiveAccountOrigin.INHERITED_FROM_BASE_STANDARD.value],
            "extension_overrides": observed[EffectiveAccountOrigin.EXTENSION_OVERRIDE.value],
            "extension_additions": observed[EffectiveAccountOrigin.EXTENSION_ADDITION.value],
            "effective_accounts_or_groups": len(self.accounts),
        }
        for key, value in expected.items():
            if key in self.statistics and self.statistics[key] != value:
                raise ValueError(f"effective plan statistic mismatch for {key}")

    def account(self, code_or_id: str) -> EffectiveReferenceAccount | None:
        """Resolve by exact provider account id or exact reference code."""
        for account in self.accounts:
            if account.account_id == code_or_id or account.ref_code == code_or_id:
                return account
        return None

    def canonical_payload(self) -> dict[str, object]:
        """Return deterministic payload used by snapshot sealing."""
        return {
            "standard_id": self.standard_id,
            "edition": self.edition,
            "base_standard": self.base_standard,
            "inheritance_rule": self.inheritance_rule,
            "statistics": dict(sorted(self.statistics.items())),
            "accounts": [
                {
                    "account_id": account.account_id,
                    "ref_code": account.ref_code,
                    "label": account.label,
                    "base_account_id": account.base_account_id,
                    "base_label": account.base_label,
                    "origin": account.origin.value,
                    "provenance_type": account.provenance_type,
                    "extension_source_ref": (
                        None
                        if account.extension_source_ref is None
                        else {
                            "document_id": account.extension_source_ref.document_id,
                            "page_pdf": account.extension_source_ref.page_pdf,
                            "section": account.extension_source_ref.section,
                            "snippet": account.extension_source_ref.snippet,
                            "source_line_md": account.extension_source_ref.source_line_md,
                        }
                    ),
                }
                for account in sorted(self.accounts, key=lambda item: item.account_id)
            ],
        }


__all__ = [
    "EffectiveAccountOrigin",
    "EffectiveAccountPlan",
    "EffectiveReferenceAccount",
    "RegulatorySourceReference",
]
