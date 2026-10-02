"""Source-backed regulatory reporting registry metadata."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.domain.reporting.errors import RegulatoryReportingError

INCOMPLETE_LINE_EXTRACTION = "visual_template_bound_not_exhaustively_transcribed"


@dataclass(frozen=True, slots=True)
class ReportingSource:
    document_id: str
    page_pdf: int
    section: str

    def __post_init__(self) -> None:
        if not self.document_id.strip() or not self.section.strip() or self.page_pdf <= 0:
            raise RegulatoryReportingError("reporting source requires document, section and page")


@dataclass(frozen=True, slots=True)
class ReportingStatementDescriptor:
    statement_id: str
    label_source: str
    model_page_pdf: int
    line_level_extraction_status: str
    source: ReportingSource
    source_range: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        if not self.statement_id.strip() or not self.label_source.strip():
            raise RegulatoryReportingError("reporting statement identity must not be empty")
        if self.model_page_pdf <= 0:
            raise RegulatoryReportingError("reporting statement page must be positive")
        if self.source_range is not None and self.source_range[0] > self.source_range[1]:
            raise RegulatoryReportingError("reporting statement source range is invalid")

    @property
    def line_level_executable(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class ReportingEligibilityThreshold:
    category: str
    comparator: str
    currency: str
    value: int

    def __post_init__(self) -> None:
        if not self.category.strip() or self.comparator != "<" or not self.currency.strip():
            raise RegulatoryReportingError("unsupported reporting eligibility threshold")
        if self.value <= 0:
            raise RegulatoryReportingError("reporting eligibility threshold must be positive")


@dataclass(frozen=True, slots=True)
class ReportingProfileDescriptor:
    profile_id: str
    label_source: str
    chapter_page: int
    legal_basis_article: int
    legal_basis_page_pdf: int
    source: ReportingSource
    statements: tuple[ReportingStatementDescriptor, ...]
    eligibility_thresholds: tuple[ReportingEligibilityThreshold, ...] = ()

    def __post_init__(self) -> None:
        if not self.profile_id.strip() or not self.label_source.strip():
            raise RegulatoryReportingError("reporting profile identity must not be empty")
        if self.chapter_page <= 0 or self.legal_basis_page_pdf <= 0:
            raise RegulatoryReportingError("reporting profile pages must be positive")
        if not self.statements:
            raise RegulatoryReportingError("reporting profile requires statements")


@dataclass(frozen=True, slots=True)
class RegulatoryReportingRegistry:
    standard_id: str
    edition: str
    dataset_version: str
    document_id: str
    part: str
    source_range: tuple[int, int]
    automatic_filing_generation: bool
    template_visual_verification_required: bool
    profiles: tuple[ReportingProfileDescriptor, ...]

    def __post_init__(self) -> None:
        if self.automatic_filing_generation:
            raise RegulatoryReportingError(
                "registry metadata must not enable automatic filing generation"
            )
        if not self.template_visual_verification_required:
            raise RegulatoryReportingError("visual template verification must remain required")
        if not self.profiles:
            raise RegulatoryReportingError("reporting registry requires profiles")
        if any(
            statement.line_level_extraction_status != INCOMPLETE_LINE_EXTRACTION
            for profile in self.profiles
            for statement in profile.statements
        ):
            raise RegulatoryReportingError("unsupported line-level extraction status")

    @property
    def statements(self) -> tuple[ReportingStatementDescriptor, ...]:
        return tuple(statement for profile in self.profiles for statement in profile.statements)

    def require_line_level_model(self, profile_id: str, statement_id: str) -> None:
        for profile in self.profiles:
            if profile.profile_id == profile_id:
                if any(statement.statement_id == statement_id for statement in profile.statements):
                    raise PermissionError(
                        "line-level reporting model is not exhaustively transcribed"
                    )
                raise KeyError(statement_id)
        raise KeyError(profile_id)


__all__ = [
    "INCOMPLETE_LINE_EXTRACTION",
    "RegulatoryReportingRegistry",
    "ReportingEligibilityThreshold",
    "ReportingProfileDescriptor",
    "ReportingSource",
    "ReportingStatementDescriptor",
]
