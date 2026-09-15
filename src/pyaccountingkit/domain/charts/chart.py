"""Company chart of accounts — an immutable, code-unique collection of accounts."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.errors import AccountRuleError, InvalidAccountCodeError
from pyaccountingkit.core.identifiers import AccountId, EntityId
from pyaccountingkit.domain.charts.account import CompanyAccount


@dataclass(frozen=True, slots=True)
class CompanyChartOfAccounts:
    """Immutable, code-unique collection for one accounting entity."""

    entity_id: EntityId
    accounts: tuple[CompanyAccount, ...] = ()

    def __post_init__(self) -> None:
        for account in self.accounts:
            require_same_entity(
                self.entity_id,
                account.entity_id,
                resource=f"company account {account.id}",
            )
        codes = [account.code for account in self.accounts]
        if len(codes) != len(set(codes)):
            dupes = sorted({code for code in codes if codes.count(code) > 1})
            raise ValueError(f"Duplicate account codes in chart: {dupes}")

    def get_by_code(self, code: str) -> CompanyAccount | None:
        """Lookup by the business code."""
        for account in self.accounts:
            if account.code == code:
                return account
        return None

    def get_by_id(self, account_id: AccountId) -> CompanyAccount | None:
        """Lookup by the opaque identifier."""
        for account in self.accounts:
            if account.id == account_id:
                return account
        return None

    def add(self, account: CompanyAccount) -> CompanyChartOfAccounts:
        """Return a new chart with an additional account (rejects duplicates)."""
        require_same_entity(
            self.entity_id,
            account.entity_id,
            resource=f"company account {account.id}",
        )
        if self.get_by_code(account.code) is not None:
            raise InvalidAccountCodeError(f"Account code {account.code!r} already exists in chart")
        return CompanyChartOfAccounts(
            entity_id=self.entity_id,
            accounts=(*self.accounts, account),
        )

    def deactivate(self, account_id: AccountId) -> CompanyChartOfAccounts:
        """Return a new chart with the identified account deactivated."""
        account = self.get_by_id(account_id)
        if account is None:
            raise AccountRuleError(f"Account {account_id} not found in chart")
        deactivated = account.deactivated()
        return CompanyChartOfAccounts(
            entity_id=self.entity_id,
            accounts=tuple(
                deactivated if item.id == account_id else item for item in self.accounts
            ),
        )


__all__ = ["CompanyChartOfAccounts"]
