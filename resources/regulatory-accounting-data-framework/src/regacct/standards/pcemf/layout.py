from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class LegacyArtifact:
    phase: str
    source_candidates: tuple[str, ...]
    target: str
    required: bool = True


CORE_ARTIFACTS = (
    LegacyArtifact(
        "v0",
        ("datasets/pcemf_2010_v0_raw.json",),
        "datasets/raw/pcemf_2010_v0_raw.json",
    ),
    LegacyArtifact(
        "v1",
        ("datasets/pcemf_2010_v1_structure.json",),
        "datasets/structured/pcemf_2010_v1_structure.json",
    ),
    LegacyArtifact(
        "v2",
        ("datasets/pcemf_2010_v2_annotated.json",),
        "datasets/annotated/pcemf_2010_v2_annotated.json",
    ),
    LegacyArtifact(
        "v3",
        ("datasets/pcemf_2010_v3_reporting.json",),
        "datasets/reporting/pcemf_2010_v3_reporting.json",
    ),
    LegacyArtifact(
        "v4",
        ("datasets/pcemf_2010_v4_prudential.json",),
        "datasets/prudential/pcemf_2010_v4_prudential.json",
    ),
    LegacyArtifact(
        "syscohada_v0",
        ("datasets/syscohada_2017_v0_raw.json",),
        "datasets/raw/syscohada_2017_v0_raw.json",
        required=False,
    ),
    LegacyArtifact(
        "syscohada_v1",
        ("datasets/syscohada_2017_v1_structure.json",),
        "datasets/structured/syscohada_2017_v1_structure.json",
        required=False,
    ),
    LegacyArtifact(
        "v5",
        ("datasets/pcemf_syscohada_v5_crosswalk_registry.json",
         "crosswalks/pcemf2010-syscohada2017/v1/candidates.json"),
        "datasets/crosswalk/pcemf_syscohada_v5_crosswalk_registry.json",
        required=False,
    ),
    LegacyArtifact(
        "v6",
        ("datasets/amifond_v6_business_enrichment.json",
         "datasets/amifond_2026_v6_business_enrichment.json",
         "business/amifond_v6_business_enrichment.json"),
        "datasets/business/amifond_v6_business_enrichment.json",
        required=False,
    ),
)

OPTIONAL_FILES = {
    "rag_index": (
        "rag/syscohada-guide/v1/index.json",
        "rag/indexes/syscohada-guide-v1.json",
    ),
    "crosswalk_manifest": (
        "crosswalks/pcemf2010-syscohada2017/v1/manifest.json",
        "datasets/crosswalk/pcemf_syscohada_v5_manifest.json",
    ),
    "crosswalk_approved": (
        "crosswalks/pcemf2010-syscohada2017/v1/approved.json",
        "datasets/crosswalk/pcemf_syscohada_v5_approved.json",
    ),
    "crosswalk_reviews": (
        "crosswalks/pcemf2010-syscohada2017/v1/reviews/review_decisions.json",
        "validation/review/pcemf_syscohada_v5_review_decisions.json",
    ),
}

ANOMALY_FILES = (
    "validation/anomalies/pcemf_2010_v1_anomalies.json",
    "validation/anomalies/pcemf_2010_v2_anomalies.json",
    "validation/anomalies/pcemf_2010_v3_reporting_anomalies.json",
    "validation/anomalies/pcemf_2010_v4_prudential_anomalies.json",
    "validation/anomalies/pcemf_syscohada_v5_crosswalk_observations.json",
    "validation/anomalies/syscohada_2017_v1_anomalies.json",
    "validation/anomalies/amifond_v6_business_enrichment_observations.json",
)
