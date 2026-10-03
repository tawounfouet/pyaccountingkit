"""Canonical LOT-27 qualification baseline derived from reviewed repository evidence."""

from __future__ import annotations

from pyaccountingkit.integrations.regulatory_framework.qualification import (
    RegulatoryCapabilityCode as Code,
)
from pyaccountingkit.integrations.regulatory_framework.qualification import (
    RegulatoryCapabilityQualification as Qualification,
)
from pyaccountingkit.integrations.regulatory_framework.qualification import (
    RegulatoryCapabilityStatus as Status,
)
from pyaccountingkit.integrations.regulatory_framework.qualification import (
    RegulatoryFrameworkIntegrationProfile,
)

PROVIDER_ID = "regulatory-accounting-data-framework"
PROVIDER_VERSION = "0.7.1"
DATASET_RELEASE = "0.7.1"
QUALIFIED_AT = "2026-10-01T18:00:00Z"
NONPROFIT_QUALIFIED_AT = "2026-10-02T07:45:00Z"
OHADA_QUALIFIED_AT = "2026-10-02T10:30:00Z"
REPORTING_QUALIFIED_AT = "2026-10-03T08:21:44Z"
REVIEWER = "PyAccountingKit LOT-27 canonical CI"


def _q(
    framework_version: str,
    standard_ref: str,
    capability: Code,
    status: Status,
    *,
    evidence_refs: tuple[str, ...] = (),
    executable: bool = False,
    human_review_required: bool = False,
    auto_inference_allowed: bool = False,
    test_suite: str | None = None,
    golden_refs: tuple[str, ...] = (),
    reviewer: str | None = None,
    qualified_at: str | None = None,
    notes: str = "",
) -> Qualification:
    return Qualification(
        standard_ref=standard_ref,
        capability_code=capability,
        provider_version=PROVIDER_VERSION,
        dataset_release=DATASET_RELEASE,
        framework_version=framework_version,
        status=status,
        evidence_refs=evidence_refs,
        executable=executable,
        human_review_required=human_review_required,
        auto_inference_allowed=auto_inference_allowed,
        test_suite=test_suite,
        golden_refs=golden_refs,
        reviewer=reviewer,
        qualified_at=qualified_at,
        notes=notes,
    )


def _production_structure(
    framework_version: str,
    standard_ref: str,
    dataset: str,
    golden: str,
) -> Qualification:
    return _q(
        framework_version,
        standard_ref,
        Code.STRUCTURE,
        Status.PRODUCTION_QUALIFIED,
        evidence_refs=(
            dataset,
            "resources/regulatory-accounting-data-framework/PROJECT_MANIFEST.json",
        ),
        executable=True,
        test_suite="tests/golden/regulatory/test_lot27_capability_profiles.py",
        golden_refs=(golden,),
        reviewer=REVIEWER,
        qualified_at=QUALIFIED_AT,
        notes=(
            "Structure is provider-backed, identity-preserving and covered by canonical "
            "golden tests."
        ),
    )


def _production_snapshots(
    framework_version: str,
    standard_ref: str,
    golden: str,
) -> Qualification:
    return _q(
        framework_version,
        standard_ref,
        Code.SNAPSHOTS,
        Status.PRODUCTION_QUALIFIED,
        evidence_refs=(
            "src/pyaccountingkit/domain/references/snapshots.py",
            "src/pyaccountingkit/adapters/regulatory/_base.py",
        ),
        executable=True,
        test_suite="tests/golden/regulatory/test_lot27_capability_profiles.py",
        golden_refs=(golden,),
        reviewer=REVIEWER,
        qualified_at=QUALIFIED_AT,
        notes="Snapshot creation is sealed and replay-oriented for the qualified structure.",
    )


def baseline_profiles(
    framework_version: str,
) -> tuple[RegulatoryFrameworkIntegrationProfile, ...]:
    """Return deterministic capability profiles without global standard support claims."""
    pcg = "fr-pcg:2026"
    syscohada = "ohada-syscohada:2017"
    nonprofit = "fr-nonprofit:2026"
    ebnl = "ohada-ebnl:2023"
    pcemf = "cemac-pcemf:2010"

    profiles = (
        RegulatoryFrameworkIntegrationProfile(
            profile_id="regulatory-profile-fr-pcg-2026",
            standard_ref=pcg,
            provider_id=PROVIDER_ID,
            dataset_release=DATASET_RELEASE,
            tested_framework_version=framework_version,
            capabilities=(
                _production_structure(
                    framework_version,
                    pcg,
                    "resources/regulatory-accounting-data-framework/datasets/structured/"
                    "pcg_2026_v1_structure.json",
                    "tests/golden/regulatory/test_pcg_baseline.py",
                ),
                _production_snapshots(
                    framework_version,
                    pcg,
                    "tests/golden/regulatory/test_pcg_baseline.py",
                ),
                _q(
                    framework_version,
                    pcg,
                    Code.REPORTING_STRUCTURE,
                    Status.PRODUCTION_QUALIFIED,
                    evidence_refs=(
                        "resources/regulatory-accounting-data-framework/datasets/reporting/"
                        "pcg_2026_v3_reporting.json",
                        "src/pyaccountingkit/adapters/regulatory/reporting.py",
                    ),
                    executable=True,
                    test_suite="tests/golden/regulatory/test_reporting_structure_provider.py",
                    golden_refs=("tests/golden/regulatory/test_reporting_structure_provider.py",),
                    reviewer=REVIEWER,
                    qualified_at=REPORTING_QUALIFIED_AT,
                    notes="Official reporting structure is provider-backed; source mapping "
                    "expressions remain non-executable review evidence.",
                ),
                _q(
                    framework_version,
                    pcg,
                    Code.REPORTING_ACCOUNT_MAPPINGS,
                    Status.REVIEW_REQUIRED,
                    evidence_refs=("tests/golden/regulatory/test_pcg_regulatory_reporting.py",),
                    human_review_required=True,
                    notes="Reporting account hints remain candidate input, not statutory mapping.",
                ),
                _q(
                    framework_version,
                    pcg,
                    Code.CONCEPTS,
                    Status.VALIDATED,
                    evidence_refs=(
                        "resources/regulatory-accounting-data-framework/datasets/concepts/"
                        "accounting_core_concepts_v0.json",
                    ),
                    notes="Neutral concepts are navigation pivots, not accounting rules.",
                ),
                _q(
                    framework_version,
                    pcg,
                    Code.CONCEPT_BINDINGS,
                    Status.NOT_ASSERTED,
                    notes="No standard-specific concept binding is inferred.",
                ),
            ),
        ),
        RegulatoryFrameworkIntegrationProfile(
            profile_id="regulatory-profile-ohada-syscohada-2017",
            standard_ref=syscohada,
            provider_id=PROVIDER_ID,
            dataset_release=DATASET_RELEASE,
            tested_framework_version=framework_version,
            capabilities=(
                _production_structure(
                    framework_version,
                    syscohada,
                    "resources/regulatory-accounting-data-framework/datasets/structured/"
                    "syscohada_2017_v1_structure.json",
                    "tests/golden/regulatory/test_syscohada_baseline.py",
                ),
                _production_snapshots(
                    framework_version,
                    syscohada,
                    "tests/golden/regulatory/test_syscohada_baseline.py",
                ),
                _q(
                    framework_version,
                    syscohada,
                    Code.REPORTING_STRUCTURE,
                    Status.PRODUCTION_QUALIFIED,
                    evidence_refs=(
                        "resources/regulatory-accounting-data-framework/datasets/reporting/"
                        "syscohada_2017_v3_reporting.json",
                        "src/pyaccountingkit/adapters/regulatory/reporting.py",
                    ),
                    executable=True,
                    test_suite="tests/golden/regulatory/test_reporting_structure_provider.py",
                    golden_refs=("tests/golden/regulatory/test_reporting_structure_provider.py",),
                    reviewer=REVIEWER,
                    qualified_at=REPORTING_QUALIFIED_AT,
                    notes="Materialized SYSCOHADA reporting models are provider-backed while "
                    "account mappings remain outside automatic execution.",
                ),
                _q(
                    framework_version,
                    syscohada,
                    Code.REPORTING_ACCOUNT_MAPPINGS,
                    Status.REVIEW_REQUIRED,
                    evidence_refs=(
                        "tests/golden/regulatory/test_syscohada_regulatory_reporting.py",
                    ),
                    human_review_required=True,
                    notes="Account hints are non-executable without validated mappings.",
                ),
                _q(
                    framework_version,
                    syscohada,
                    Code.RELATIONS,
                    Status.PRODUCTION_QUALIFIED,
                    evidence_refs=(
                        "resources/regulatory-accounting-data-framework/datasets/relations/"
                        "ohada_accounting_standard_relations.json",
                        "src/pyaccountingkit/adapters/regulatory/ohada.py",
                    ),
                    executable=True,
                    test_suite="tests/golden/regulatory/test_ohada_standard_relations.py",
                    golden_refs=("tests/golden/regulatory/test_ohada_standard_relations.py",),
                    reviewer=REVIEWER,
                    qualified_at=OHADA_QUALIFIED_AT,
                    notes="Family membership is explicit, queryable and never implies inheritance.",
                ),
            ),
        ),
        RegulatoryFrameworkIntegrationProfile(
            profile_id="regulatory-profile-fr-nonprofit-2026",
            standard_ref=nonprofit,
            provider_id=PROVIDER_ID,
            dataset_release=DATASET_RELEASE,
            tested_framework_version=framework_version,
            capabilities=(
                _q(
                    framework_version,
                    nonprofit,
                    Code.EFFECTIVE_PLAN,
                    Status.PRODUCTION_QUALIFIED,
                    evidence_refs=(
                        "resources/regulatory-accounting-data-framework/datasets/structured/"
                        "nonprofit_2026_v1_effective_plan.json",
                        "src/pyaccountingkit/adapters/regulatory/nonprofit.py",
                    ),
                    executable=True,
                    test_suite="tests/golden/regulatory/test_nonprofit_effective_plan.py",
                    golden_refs=("tests/golden/regulatory/test_nonprofit_effective_plan.py",),
                    reviewer=REVIEWER,
                    qualified_at=NONPROFIT_QUALIFIED_AT,
                    notes=(
                        "Provider consumes the upstream resolved effective plan directly without "
                        "replaying PCG plus overlays."
                    ),
                ),
                _q(
                    framework_version,
                    nonprofit,
                    Code.OVERLAYS,
                    Status.VALIDATED,
                    evidence_refs=(
                        "resources/regulatory-accounting-data-framework/datasets/structured/"
                        "nonprofit_2026_v1_account_overlay.json",
                        "src/pyaccountingkit/adapters/regulatory/nonprofit.py",
                    ),
                    test_suite="tests/golden/regulatory/test_nonprofit_effective_plan.py",
                    golden_refs=("tests/golden/regulatory/test_nonprofit_effective_plan.py",),
                    notes=(
                        "Overlay provenance is provider-readable for audit and explanation only; "
                        "automatic chart mutation remains forbidden."
                    ),
                ),
                _q(
                    framework_version,
                    nonprofit,
                    Code.REPORTING_STRUCTURE,
                    Status.PRODUCTION_QUALIFIED,
                    evidence_refs=(
                        "resources/regulatory-accounting-data-framework/datasets/reporting/"
                        "nonprofit_2026_v3_reporting.json",
                        "src/pyaccountingkit/adapters/regulatory/reporting.py",
                    ),
                    executable=True,
                    test_suite="tests/golden/regulatory/test_reporting_structure_provider.py",
                    golden_refs=("tests/golden/regulatory/test_reporting_structure_provider.py",),
                    reviewer=REVIEWER,
                    qualified_at=REPORTING_QUALIFIED_AT,
                    notes="Official statement structure is provider-backed; all 33 derived "
                    "account-hint lines remain human-reviewed and non-executable.",
                ),
                _q(
                    framework_version,
                    nonprofit,
                    Code.REPORTING_ACCOUNT_MAPPINGS,
                    Status.REVIEW_REQUIRED,
                    evidence_refs=(
                        "resources/regulatory-accounting-data-framework/datasets/reporting/"
                        "nonprofit_2026_v3_reporting.json",
                    ),
                    human_review_required=True,
                    notes="Source explicitly sets account_hints_executable=false.",
                ),
                _q(
                    framework_version,
                    nonprofit,
                    Code.SNAPSHOTS,
                    Status.PRODUCTION_QUALIFIED,
                    evidence_refs=(
                        "src/pyaccountingkit/domain/references/snapshots.py",
                        "src/pyaccountingkit/adapters/regulatory/nonprofit.py",
                    ),
                    executable=True,
                    test_suite="tests/golden/regulatory/test_nonprofit_effective_plan.py",
                    golden_refs=("tests/golden/regulatory/test_nonprofit_effective_plan.py",),
                    reviewer=REVIEWER,
                    qualified_at=NONPROFIT_QUALIFIED_AT,
                    notes="Resolved effective-plan snapshots are deterministic and replayable.",
                ),
            ),
        ),
        RegulatoryFrameworkIntegrationProfile(
            profile_id="regulatory-profile-ohada-ebnl-2023",
            standard_ref=ebnl,
            provider_id=PROVIDER_ID,
            dataset_release=DATASET_RELEASE,
            tested_framework_version=framework_version,
            capabilities=(
                _q(
                    framework_version,
                    ebnl,
                    Code.STRUCTURE,
                    Status.PRODUCTION_QUALIFIED,
                    evidence_refs=(
                        "resources/regulatory-accounting-data-framework/datasets/structured/"
                        "ebnl_2023_v1_structure.json",
                        "src/pyaccountingkit/adapters/regulatory/ohada.py",
                    ),
                    executable=True,
                    test_suite="tests/golden/regulatory/test_ebnl_structure_provider.py",
                    golden_refs=("tests/golden/regulatory/test_ebnl_structure_provider.py",),
                    reviewer=REVIEWER,
                    qualified_at=OHADA_QUALIFIED_AT,
                    notes=(
                        "The reviewed 1,145-node EBNL graph is consumed with explicit class scopes "
                        "and ambiguous source identities preserved."
                    ),
                ),
                _q(
                    framework_version,
                    ebnl,
                    Code.RELATIONS,
                    Status.PRODUCTION_QUALIFIED,
                    evidence_refs=(
                        "resources/regulatory-accounting-data-framework/datasets/relations/"
                        "ohada_accounting_standard_relations.json",
                        "src/pyaccountingkit/adapters/regulatory/ohada.py",
                    ),
                    executable=True,
                    test_suite="tests/golden/regulatory/test_ohada_standard_relations.py",
                    golden_refs=("tests/golden/regulatory/test_ohada_standard_relations.py",),
                    reviewer=REVIEWER,
                    qualified_at=OHADA_QUALIFIED_AT,
                    notes=(
                        "Specialization relation is queryable and remains distinct from "
                        "inheritance."
                    ),
                ),
                _q(
                    framework_version,
                    ebnl,
                    Code.NEGATIVE_CONSTRAINTS,
                    Status.FORBIDDEN_INFERENCE,
                    evidence_refs=(
                        "resources/regulatory-accounting-data-framework/datasets/relations/"
                        "ohada_accounting_standard_relations.json",
                        "src/pyaccountingkit/domain/references/standard_relations.py",
                        "src/pyaccountingkit/adapters/regulatory/ohada.py",
                    ),
                    test_suite="tests/golden/regulatory/test_ohada_standard_relations.py",
                    golden_refs=("tests/golden/regulatory/test_ohada_standard_relations.py",),
                    notes=(
                        "Runtime guard rejects EBNL 2023 -> SYSCOHADA 2017 inheritance and "
                        "automatic inference remains fail-closed."
                    ),
                ),
                _q(
                    framework_version,
                    ebnl,
                    Code.CROSSWALKS,
                    Status.REVIEW_REQUIRED,
                    evidence_refs=(
                        "resources/regulatory-accounting-data-framework/datasets/crosswalk/"
                        "ebnl_2023_vs_syscohada_2017_structural_delta.json",
                    ),
                    human_review_required=True,
                    notes="Structural delta is not semantic equivalence.",
                ),
                _q(
                    framework_version,
                    ebnl,
                    Code.SNAPSHOTS,
                    Status.PRODUCTION_QUALIFIED,
                    evidence_refs=(
                        "src/pyaccountingkit/domain/references/snapshots.py",
                        "src/pyaccountingkit/adapters/regulatory/ohada.py",
                    ),
                    executable=True,
                    test_suite="tests/golden/regulatory/test_ebnl_structure_provider.py",
                    golden_refs=("tests/golden/regulatory/test_ebnl_structure_provider.py",),
                    reviewer=REVIEWER,
                    qualified_at=OHADA_QUALIFIED_AT,
                    notes="EBNL structural snapshots are deterministic and replayable.",
                ),
                _q(
                    framework_version,
                    ebnl,
                    Code.REPORTING_STRUCTURE,
                    Status.DISCOVERED,
                    evidence_refs=(
                        "resources/regulatory-accounting-data-framework/datasets/reporting/"
                        "ebnl_2023_v3_reporting.json",
                    ),
                    notes=(
                        "Reporting artifact exists but PyAccountingKit execution is not asserted."
                    ),
                ),
                _q(
                    framework_version,
                    ebnl,
                    Code.CONCEPT_BINDINGS,
                    Status.NOT_ASSERTED,
                    notes="Upstream OHADA family manifest reports zero concept bindings.",
                ),
            ),
        ),
        RegulatoryFrameworkIntegrationProfile(
            profile_id="regulatory-profile-cemac-pcemf-2010",
            standard_ref=pcemf,
            provider_id=PROVIDER_ID,
            dataset_release=DATASET_RELEASE,
            tested_framework_version=framework_version,
            capabilities=(
                _q(
                    framework_version,
                    pcemf,
                    Code.STRUCTURE,
                    Status.NOT_ASSERTED,
                    notes="No PCEMF structure dataset is present in the reviewed bundled evidence.",
                ),
                _q(
                    framework_version,
                    pcemf,
                    Code.RELATIONS,
                    Status.PRODUCTION_QUALIFIED,
                    evidence_refs=(
                        "resources/regulatory-accounting-data-framework/datasets/relations/"
                        "ohada_accounting_standard_relations.json",
                        "src/pyaccountingkit/adapters/regulatory/ohada.py",
                    ),
                    executable=True,
                    test_suite="tests/golden/regulatory/test_ohada_standard_relations.py",
                    golden_refs=("tests/golden/regulatory/test_ohada_standard_relations.py",),
                    reviewer=REVIEWER,
                    qualified_at=OHADA_QUALIFIED_AT,
                    notes="Sector specialization within the OHADA accounting family is queryable.",
                ),
                _q(
                    framework_version,
                    pcemf,
                    Code.NEGATIVE_CONSTRAINTS,
                    Status.FORBIDDEN_INFERENCE,
                    evidence_refs=(
                        "resources/regulatory-accounting-data-framework/datasets/relations/"
                        "ohada_accounting_standard_relations.json",
                        "src/pyaccountingkit/domain/references/standard_relations.py",
                        "src/pyaccountingkit/adapters/regulatory/ohada.py",
                    ),
                    test_suite="tests/golden/regulatory/test_ohada_standard_relations.py",
                    golden_refs=("tests/golden/regulatory/test_ohada_standard_relations.py",),
                    notes=(
                        "Runtime guard rejects PCEMF 2010 -> SYSCOHADA 2017 inheritance because "
                        "the source supports family/sector framing only."
                    ),
                ),
                _q(
                    framework_version,
                    pcemf,
                    Code.CROSSWALKS,
                    Status.NOT_ASSERTED,
                    human_review_required=True,
                    notes="No executable crosswalk artifact is asserted in the bundled release.",
                ),
                _q(
                    framework_version,
                    pcemf,
                    Code.CONCEPT_BINDINGS,
                    Status.NOT_ASSERTED,
                    notes="Neutral concepts do not create PCEMF bindings automatically.",
                ),
            ),
        ),
    )
    return tuple(sorted(profiles, key=lambda profile: profile.standard_ref))


__all__ = [
    "DATASET_RELEASE",
    "PROVIDER_ID",
    "PROVIDER_VERSION",
    "baseline_profiles",
]
