"""Unit tests for LOT-27 capability-scoped regulatory qualification."""

from __future__ import annotations

import pytest

from pyaccountingkit.integrations.regulatory_framework import (
    RegulatoryCapabilityCode,
    RegulatoryCapabilityQualification,
    RegulatoryCapabilityStatus,
    RegulatoryFrameworkIntegrationProfile,
    RegulatorySupportLevel,
)


def _qualification(
    status: RegulatoryCapabilityStatus,
    *,
    executable: bool = False,
    human_review_required: bool = False,
) -> RegulatoryCapabilityQualification:
    return RegulatoryCapabilityQualification(
        standard_ref="fr-pcg:2026",
        capability_code=RegulatoryCapabilityCode.STRUCTURE,
        provider_version="0.7.1",
        dataset_release="0.7.1",
        framework_version="0.7.0a1",
        status=status,
        executable=executable,
        human_review_required=human_review_required,
    )


def test_support_level_is_derived_per_capability() -> None:
    assert (
        _qualification(RegulatoryCapabilityStatus.VALIDATED).support_level
        is RegulatorySupportLevel.REFERENCE_VALIDATED
    )
    assert (
        _qualification(
            RegulatoryCapabilityStatus.REVIEW_REQUIRED,
            human_review_required=True,
        ).support_level
        is RegulatorySupportLevel.REVIEW_REQUIRED
    )


def test_non_executable_status_cannot_claim_execution() -> None:
    with pytest.raises(ValueError, match="may execute"):
        _qualification(
            RegulatoryCapabilityStatus.REVIEW_REQUIRED,
            executable=True,
            human_review_required=True,
        )


def test_review_required_status_requires_human_review() -> None:
    with pytest.raises(ValueError, match="must require human review"):
        _qualification(RegulatoryCapabilityStatus.REVIEW_REQUIRED)


def test_production_qualified_requires_complete_evidence() -> None:
    with pytest.raises(ValueError, match="requires evidence"):
        _qualification(
            RegulatoryCapabilityStatus.PRODUCTION_QUALIFIED,
            executable=True,
        )


def test_profile_rejects_duplicate_capability_claims() -> None:
    qualification = _qualification(RegulatoryCapabilityStatus.VALIDATED)
    with pytest.raises(ValueError, match="duplicate capability"):
        RegulatoryFrameworkIntegrationProfile(
            profile_id="pcg",
            standard_ref="fr-pcg:2026",
            provider_id="regulatory-accounting-data-framework",
            dataset_release="0.7.1",
            tested_framework_version="0.7.0a1",
            capabilities=(qualification, qualification),
        )


def test_profile_rejects_mixed_release_coordinates() -> None:
    qualification = RegulatoryCapabilityQualification(
        standard_ref="fr-pcg:2026",
        capability_code=RegulatoryCapabilityCode.STRUCTURE,
        provider_version="0.7.1",
        dataset_release="0.7.0",
        framework_version="0.7.0a1",
        status=RegulatoryCapabilityStatus.VALIDATED,
    )

    with pytest.raises(ValueError, match="dataset_release"):
        RegulatoryFrameworkIntegrationProfile(
            profile_id="pcg",
            standard_ref="fr-pcg:2026",
            provider_id="regulatory-accounting-data-framework",
            dataset_release="0.7.1",
            tested_framework_version="0.7.0a1",
            capabilities=(qualification,),
        )


def test_profile_rejects_mixed_framework_versions() -> None:
    qualification = RegulatoryCapabilityQualification(
        standard_ref="fr-pcg:2026",
        capability_code=RegulatoryCapabilityCode.STRUCTURE,
        provider_version="0.7.1",
        dataset_release="0.7.1",
        framework_version="0.7.0a2",
        status=RegulatoryCapabilityStatus.VALIDATED,
    )

    with pytest.raises(ValueError, match="framework_version"):
        RegulatoryFrameworkIntegrationProfile(
            profile_id="pcg",
            standard_ref="fr-pcg:2026",
            provider_id="regulatory-accounting-data-framework",
            dataset_release="0.7.1",
            tested_framework_version="0.7.0a1",
            capabilities=(qualification,),
        )


def test_forbidden_inference_never_allows_auto_inference() -> None:
    with pytest.raises(ValueError, match="cannot allow automatic inference"):
        RegulatoryCapabilityQualification(
            standard_ref="ohada-ebnl:2023",
            capability_code=RegulatoryCapabilityCode.NEGATIVE_CONSTRAINTS,
            provider_version="0.7.1",
            dataset_release="0.7.1",
            framework_version="0.7.0a1",
            status=RegulatoryCapabilityStatus.FORBIDDEN_INFERENCE,
            auto_inference_allowed=True,
        )
