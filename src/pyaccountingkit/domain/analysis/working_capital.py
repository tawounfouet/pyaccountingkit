"""Working-capital identities derived from a functional balance."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.analysis.functional_balance import FunctionalBalanceResult
from pyaccountingkit.domain.analysis.indicators import IndicatorValueStatus


@dataclass(frozen=True, slots=True)
class WorkingCapitalAnalysis:
    status: IndicatorValueStatus
    frng: Money | None
    bfre: Money | None
    bfrhe: Money | None
    bfr: Money | None
    net_treasury: Money | None
    net_treasury_cash: Money | None
    reconciliation_difference: Money | None
    reconciled: bool | None
    source_functional_balance_checksum: str
    checksum: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "checksum", self._compute_checksum())

    @classmethod
    def from_functional_balance(
        cls,
        functional_balance: FunctionalBalanceResult,
    ) -> WorkingCapitalAnalysis:
        if functional_balance.status is not IndicatorValueStatus.CALCULATED:
            return cls(
                status=IndicatorValueStatus.INDETERMINATE,
                frng=None,
                bfre=None,
                bfrhe=None,
                bfr=None,
                net_treasury=None,
                net_treasury_cash=None,
                reconciliation_difference=None,
                reconciled=None,
                source_functional_balance_checksum=functional_balance.checksum,
            )

        required = (
            functional_balance.stable_resources,
            functional_balance.stable_uses,
            functional_balance.operating_current_assets,
            functional_balance.operating_current_liabilities,
            functional_balance.non_operating_current_assets,
            functional_balance.non_operating_current_liabilities,
            functional_balance.cash_assets,
            functional_balance.cash_liabilities,
        )
        if any(value is None for value in required):
            raise ValueError("calculated functional balance is missing required values")

        stable_resources = functional_balance.stable_resources
        stable_uses = functional_balance.stable_uses
        operating_assets = functional_balance.operating_current_assets
        operating_liabilities = functional_balance.operating_current_liabilities
        non_operating_assets = functional_balance.non_operating_current_assets
        non_operating_liabilities = functional_balance.non_operating_current_liabilities
        cash_assets = functional_balance.cash_assets
        cash_liabilities = functional_balance.cash_liabilities
        if (
            stable_resources is None
            or stable_uses is None
            or operating_assets is None
            or operating_liabilities is None
            or non_operating_assets is None
            or non_operating_liabilities is None
            or cash_assets is None
            or cash_liabilities is None
        ):
            raise ValueError("calculated functional balance is incomplete")

        frng = stable_resources - stable_uses
        bfre = operating_assets - operating_liabilities
        bfrhe = non_operating_assets - non_operating_liabilities
        bfr = bfre + bfrhe
        net_treasury = frng - bfr
        net_treasury_cash = cash_assets - cash_liabilities
        difference = net_treasury - net_treasury_cash
        return cls(
            status=IndicatorValueStatus.CALCULATED,
            frng=frng,
            bfre=bfre,
            bfrhe=bfrhe,
            bfr=bfr,
            net_treasury=net_treasury,
            net_treasury_cash=net_treasury_cash,
            reconciliation_difference=difference,
            reconciled=difference.is_zero(),
            source_functional_balance_checksum=functional_balance.checksum,
        )

    def _compute_checksum(self) -> str:
        def amount(value: Money | None) -> str | None:
            return str(value.amount) if value is not None else None

        payload = {
            "status": self.status.value,
            "frng": amount(self.frng),
            "bfre": amount(self.bfre),
            "bfrhe": amount(self.bfrhe),
            "bfr": amount(self.bfr),
            "net_treasury": amount(self.net_treasury),
            "net_treasury_cash": amount(self.net_treasury_cash),
            "reconciliation_difference": amount(self.reconciliation_difference),
            "reconciled": self.reconciled,
            "source_functional_balance_checksum": self.source_functional_balance_checksum,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


__all__ = ["WorkingCapitalAnalysis"]
