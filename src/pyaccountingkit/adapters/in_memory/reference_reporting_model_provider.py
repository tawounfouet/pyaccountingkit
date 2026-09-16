"""In-memory reference provider for exact regulatory reporting models."""

from __future__ import annotations

from pyaccountingkit.domain.reporting.errors import RegulatoryModelNotFoundError
from pyaccountingkit.domain.reporting.reference_reporting_model import ReferenceReportingModel


class InMemoryReferenceReportingModelProvider:
    """Behavioral reference adapter keyed by exact regulatory coordinates."""

    def __init__(self, models: tuple[ReferenceReportingModel, ...]) -> None:
        self._models = models

    def get_reporting_model(
        self,
        *,
        reference_snapshot_id: str,
        framework: str,
        edition: str,
        model_code: str,
    ) -> ReferenceReportingModel:
        matches = [
            model
            for model in self._models
            if model.reference_snapshot_id == reference_snapshot_id
            and model.framework == framework
            and model.edition == edition
            and model.model_code == model_code
        ]
        if len(matches) != 1:
            raise RegulatoryModelNotFoundError(
                "exact reference reporting model coordinates did not resolve uniquely"
            )
        return matches[0]


__all__ = ["InMemoryReferenceReportingModelProvider"]
