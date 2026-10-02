"""OHADA EBNL reporting-registry provider."""

from __future__ import annotations

import json
from pathlib import Path

from pyaccountingkit.domain.reporting.regulatory_registry import (
    RegulatoryReportingRegistry,
    ReportingEligibilityThreshold,
    ReportingProfileDescriptor,
    ReportingSource,
    ReportingStatementDescriptor,
)

EBNL_REPORTING_FILENAME = "ebnl_2023_v3_reporting.json"


class EBNLReportingRegistryAdapter:
    def __init__(self, reporting_directory: Path) -> None:
        self._reporting_directory = reporting_directory

    def get_registry(self) -> RegulatoryReportingRegistry:
        payload = json.loads(
            (self._reporting_directory / EBNL_REPORTING_FILENAME).read_text(encoding="utf-8")
        )
        profiles = tuple(self._profile(item) for item in payload["profiles"])
        policy = payload["execution_policy"]
        return RegulatoryReportingRegistry(
            standard_id=payload["standard_id"],
            edition=payload["edition"],
            dataset_version=payload["dataset_version"],
            document_id=payload["document_id"],
            part=payload["part"],
            source_range=tuple(payload["source_range"]),
            automatic_filing_generation=policy["automatic_filing_generation"],
            template_visual_verification_required=policy["template_visual_verification_required"],
            profiles=profiles,
        )

    @staticmethod
    def _source(payload: dict[str, object]) -> ReportingSource:
        return ReportingSource(
            document_id=str(payload["document_id"]),
            page_pdf=int(payload["page_pdf"]),
            section=str(payload["section"]),
        )

    def _profile(self, payload: dict[str, object]) -> ReportingProfileDescriptor:
        legal_basis = payload["legal_basis"]
        if not isinstance(legal_basis, dict):\n            raise ValueError("reporting profile legal_basis must be an object")
        source = payload["source"]
        if not isinstance(source, dict):\n            raise ValueError("reporting profile source must be an object")
        statements = payload["statements"]
        if not isinstance(statements, list):\n            raise ValueError("reporting profile statements must be a list")
        thresholds = payload.get("eligibility_thresholds", [])
        if not isinstance(thresholds, list):\n            raise ValueError("reporting profile eligibility_thresholds must be a list")
        return ReportingProfileDescriptor(
            profile_id=str(payload["profile_id"]),
            label_source=str(payload["label_source"]),
            chapter_page=int(payload["chapter_page"]),
            legal_basis_article=int(legal_basis["article"]),
            legal_basis_page_pdf=int(legal_basis["page_pdf"]),
            source=self._source(source),
            statements=tuple(self._statement(item) for item in statements),
            eligibility_thresholds=tuple(
                ReportingEligibilityThreshold(
                    category=str(item["category"]),
                    comparator=str(item["comparator"]),
                    currency=str(item["currency"]),
                    value=int(item["value"]),
                )
                for item in thresholds
            ),
        )

    def _statement(self, payload: dict[str, object]) -> ReportingStatementDescriptor:
        source = payload["source"]
        if not isinstance(source, dict):\n            raise ValueError("reporting statement source must be an object")
        raw_range = payload.get("source_range")
        source_range = tuple(raw_range) if isinstance(raw_range, list) else None
        return ReportingStatementDescriptor(
            statement_id=str(payload["statement_id"]),
            label_source=str(payload["label_source"]),
            model_page_pdf=int(payload["model_page_pdf"]),
            line_level_extraction_status=str(payload["line_level_extraction_status"]),
            source=self._source(source),
            source_range=source_range,
        )


__all__ = ["EBNL_REPORTING_FILENAME", "EBNLReportingRegistryAdapter"]
