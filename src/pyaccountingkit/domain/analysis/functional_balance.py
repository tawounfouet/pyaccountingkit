"""Definition-driven functional balance derived from explicit analytical inputs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date

from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.analysis.errors import InvalidFunctionalBalanceError
from pyaccountingkit.domain.analysis.indicators import DefinitionStatus, IndicatorValueStatus
from pyaccountingkit.domain.analysis.source import FinancialAnalysisSource
from pyaccountingkit.domain.analysis.values import AnalysisInputValue


@dataclass(frozen=True, slots=True)
class FunctionalBalanceDefinition:
    definition_id: str
    version: str
    stable_resources_ref: str
    stable_uses_ref: str
    operating_current_assets_ref: str
    operating_current_liabilities_ref: str
    non_operating_current_assets_ref: str
    non_operating_current_liabilities_ref: str
    cash_assets_ref: str
    cash_liabilities_ref: str
    status: DefinitionStatus = DefinitionStatus.DRAFT
    effective_from: date | None = None
    effective_to: date | None = None
    checksum: str = field(init=False)

    def __post_init__(self) -> None:
        refs = (
            self.stable_resources_ref,
            self.stable_uses_ref,
            self.operating_current_assets_ref,
            self.operating_current_liabilities_ref,
            self.non_operating_current_assets_ref,
            self.non_operating_current_liabilities_ref,
            self.cash_assets_ref,
            self.cash_liabilities_ref,
        )
        if not self.definition_id.strip() or not self.version.strip():
            raise InvalidFunctionalBalanceError(
                "functional balance definition identity must not be empty"
            )
        if any(not ref.strip() for ref in refs):
            raise InvalidFunctionalBalanceError("functional balance refs must not be empty")
        if self.effective_to is not None and self.effective_from is None:
            raise InvalidFunctionalBalanceError("effective_to requires effective_from")
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise InvalidFunctionalBalanceError("functional balance effective dates are inverted")
        object.__setattr__(self, "checksum", self._compute_checksum())

    def is_effective_on(self, on_date: date) -> bool:
        if self.effective_from is not None and on_date < self.effective_from:
            return False
        if self.effective_to is not None and on_date > self.effective_to:
            return False
        return True

    @property
    def executable(self) -> bool:
        return self.status is DefinitionStatus.ACTIVE

    def _compute_checksum(self) -> str:
        payload = {
            "definition_id": self.definition_id,
            "version": self.version,
            "refs": list(
                (
                    self.stable_resources_ref,
                    self.stable_uses_ref,
                    self.operating_current_assets_ref,
                    self.operating_current_liabilities_ref,
                    self.non_operating_current_assets_ref,
                    self.non_operating_current_liabilities_ref,
                    self.cash_assets_ref,
                    self.cash_liabilities_ref,
                )
            ),
            "status": self.status.value,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class FunctionalBalanceResult:
    definition_id: str
    definition_version: str
    definition_checksum: str
    source_checksum: str
    status: IndicatorValueStatus
    stable_resources: Money | None
    stable_uses: Money | None
    operating_current_assets: Money | None
    operating_current_liabilities: Money | None
    non_operating_current_assets: Money | None
    non_operating_current_liabilities: Money | None
    cash_assets: Money | None
    cash_liabilities: Money | None
    missing_refs: tuple[str, ...]
    checksum: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "checksum", self._compute_checksum())

    def _compute_checksum(self) -> str:
        def amount(value: Money | None) -> str | None:
            return str(value.amount) if value is not None else None

        payload = {
            "definition_id": self.definition_id,
            "definition_version": self.definition_version,
            "definition_checksum": self.definition_checksum,
            "source_checksum": self.source_checksum,
            "status": self.status.value,
            "stable_resources": amount(self.stable_resources),
            "stable_uses": amount(self.stable_uses),
            "operating_current_assets": amount(self.operating_current_assets),
            "operating_current_liabilities": amount(self.operating_current_liabilities),
            "non_operating_current_assets": amount(self.non_operating_current_assets),
            "non_operating_current_liabilities": amount(self.non_operating_current_liabilities),
            "cash_assets": amount(self.cash_assets),
            "cash_liabilities": amount(self.cash_liabilities),
            "missing_refs": list(self.missing_refs),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


class FunctionalBalanceEngine:
    def build(
        self,
        *,
        definition: FunctionalBalanceDefinition,
        source: FinancialAnalysisSource,
        inputs: tuple[AnalysisInputValue, ...],
        historical_replay: bool = False,
    ) -> FunctionalBalanceResult:
        source.assert_publishable(historical_replay=historical_replay)
        if not definition.executable or not definition.is_effective_on(source.as_of):
            raise InvalidFunctionalBalanceError(
                "functional balance definition must be ACTIVE and effective"
            )
        input_map = {item.key: item for item in inputs}
        refs = (
            definition.stable_resources_ref,
            definition.stable_uses_ref,
            definition.operating_current_assets_ref,
            definition.operating_current_liabilities_ref,
            definition.non_operating_current_assets_ref,
            definition.non_operating_current_liabilities_ref,
            definition.cash_assets_ref,
            definition.cash_liabilities_ref,
        )
        missing = tuple(ref for ref in refs if ref not in input_map)
        if missing:
            return FunctionalBalanceResult(
                definition_id=definition.definition_id,
                definition_version=definition.version,
                definition_checksum=definition.checksum,
                source_checksum=source.checksum,
                status=IndicatorValueStatus.INDETERMINATE,
                stable_resources=None,
                stable_uses=None,
                operating_current_assets=None,
                operating_current_liabilities=None,
                non_operating_current_assets=None,
                non_operating_current_liabilities=None,
                cash_assets=None,
                cash_liabilities=None,
                missing_refs=missing,
            )

        def money(ref: str) -> Money:
            return Money(input_map[ref].value, source.currency)

        return FunctionalBalanceResult(
            definition_id=definition.definition_id,
            definition_version=definition.version,
            definition_checksum=definition.checksum,
            source_checksum=source.checksum,
            status=IndicatorValueStatus.CALCULATED,
            stable_resources=money(definition.stable_resources_ref),
            stable_uses=money(definition.stable_uses_ref),
            operating_current_assets=money(definition.operating_current_assets_ref),
            operating_current_liabilities=money(definition.operating_current_liabilities_ref),
            non_operating_current_assets=money(definition.non_operating_current_assets_ref),
            non_operating_current_liabilities=money(
                definition.non_operating_current_liabilities_ref
            ),
            cash_assets=money(definition.cash_assets_ref),
            cash_liabilities=money(definition.cash_liabilities_ref),
            missing_refs=(),
        )


__all__ = [
    "FunctionalBalanceDefinition",
    "FunctionalBalanceEngine",
    "FunctionalBalanceResult",
]
