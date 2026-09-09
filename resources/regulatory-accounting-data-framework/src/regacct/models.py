from __future__ import annotations
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator

class ProvenanceType(str, Enum):
    SOURCE = "source"
    DERIVED = "derived"
    OFFICIAL_EXTERNAL = "official_external"
    HUMAN_VERIFIED = "human_verified"
    AI_INFERRED = "ai_inferred"

class ReviewStatus(str, Enum):
    UNVERIFIED = "unverified"
    AUTO_VERIFIED = "auto_verified"
    HUMAN_REVIEWED = "human_reviewed"
    OFFICIAL_SOURCE = "official_source"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"

class SourceReference(BaseModel):
    document_id: str
    page_pdf: int | None = None
    section: str | None = None
    heading_path: list[str] = Field(default_factory=list)
    snippet: str | None = None

class Provenance(BaseModel):
    type: ProvenanceType
    method: str | None = None
    source_refs: list[SourceReference] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    review_status: ReviewStatus = ReviewStatus.UNVERIFIED
    model: str | None = None
    prompt_version: str | None = None
    reviewer: str | None = None
    reviewed_at: str | None = None

class SourceArtifact(BaseModel):
    document_id: str
    relative_path: str
    media_type: str
    role: str
    sha256: str | None = None
    derived_from: list[str] = Field(default_factory=list)
    authority_level: str | None = None
    quality_status: str | None = None
    canonical_eligibility: bool = True
    notes: str | None = None

class CapabilitySet(BaseModel):
    chart_of_accounts: bool = True
    structure: bool = True
    posting_guidance: bool = False
    financial_reporting: bool = False
    prudential: bool = False
    disclosures: bool = False
    consolidation: bool = False
    sector_adaptations: bool = False
    crosswalk: bool = True
    business_enrichment: bool = False

class StandardManifest(BaseModel):
    standard_id: str
    standard_name: str
    authority: str
    jurisdiction: str
    language: str = "fr"
    edition: str
    effective_from: str | None = None
    effective_to: str | None = None
    base_standard: str | None = None
    extension_type: str | None = None
    family_ids: list[str] = Field(default_factory=list)
    standard_role: str | None = None
    edition_basis: str | None = None
    canonical_status: str = "active"
    source_documents: list[SourceArtifact] = Field(default_factory=list)
    capabilities: CapabilitySet = Field(default_factory=CapabilitySet)

class RawAccountEntry(BaseModel):
    record_id: str
    source_order: int
    code_source: str
    code_normalized: str | None = None
    label_source: str
    class_number_source: int | None = None
    class_heading_source: str | None = None
    marker_source: str | None = None
    source: SourceReference
    source_rows: list[str] = Field(default_factory=list)
    extraction_features: dict[str, Any] = Field(default_factory=dict)

class StructuredAccount(BaseModel):
    node_id: str
    standard_id: str
    edition: str
    source_record_id: str
    ref_code: str
    label_source: str
    node_type: str = "account"
    attributes: dict[str, Any] = Field(default_factory=dict)
    account_class: int | None = None
    parent_node_id: str | None = None
    children_node_ids: list[str] = Field(default_factory=list)
    depth: int = 0
    path_node_ids: list[str] = Field(default_factory=list)
    path_codes: list[str] = Field(default_factory=list)
    is_leaf: bool = True
    is_grouped_source: bool = False
    source_code: str | None = None
    provenance: Provenance

    @model_validator(mode="after")
    def validate_graph_fields(self):
        if self.node_id in self.children_node_ids:
            raise ValueError("Self reference detected")
        if self.depth != max(len(self.path_node_ids) - 1, 0):
            raise ValueError("depth must equal len(path_node_ids) - 1")
        if self.is_leaf != (len(self.children_node_ids) == 0):
            raise ValueError("is_leaf inconsistent with children")
        return self

class Observation(BaseModel):
    observation_id: str
    standard_id: str
    edition: str
    type: str
    severity: Literal["info", "warning", "error", "blocking"] = "warning"
    source_value: Any = None
    normalized_value: Any = None
    reason: str | None = None
    source_refs: list[SourceReference] = Field(default_factory=list)
    status: Literal["open", "reviewed", "resolved", "accepted"] = "open"

class AnnotationField(BaseModel):
    present_in_source: bool
    mode: str = "normal"
    text_source: str = ""
    fragments: list[SourceReference] = Field(default_factory=list)

class AccountAnnotation(BaseModel):
    annotation_id: str
    standard_id: str
    edition: str
    account_node_ids: list[str]
    heading_source: str | None = None
    fields: dict[str, AnnotationField] = Field(default_factory=dict)
    provenance: Provenance

class StatementLine(BaseModel):
    line_id: str
    statement_id: str
    line_code: str
    label_source: str
    section: str | None = None
    source: SourceReference
    mapping_expression_source: str | None = None
    mapping_components: list[dict[str, Any]] = Field(default_factory=list)

class PrudentialThreshold(BaseModel):
    comparator: Literal[">", ">=", "<", "<=", "=="]
    value: float | None = None
    unit: str | None = None
    source_text: str
    evaluation_status: str = "ready"

class CrosswalkCandidate(BaseModel):
    candidate_id: str
    source_node_id: str
    target_node_id: str
    candidate_score: float
    ranking_band: str
    code_equality_observed: bool = False
    code_equality_used_in_score: bool = False
    evidence: list[SourceReference] = Field(default_factory=list)
    review_status: Literal["pending_human_review", "approved", "rejected", "needs_more_evidence"] = "pending_human_review"
    auto_approval_allowed: bool = False


class StandardRelationType(str, Enum):
    MEMBER_OF_FAMILY = "member_of_family"
    SECTOR_SPECIALIZATION_WITHIN_FAMILY = "sector_specialization_within_family"
    SPECIALIZED_STANDARD_WITHIN_FAMILY = "specialized_standard_within_family"
    INHERITS = "inherits"
    SUPERSEDES = "supersedes"
    CROSSWALK = "crosswalk"
    RELATED_REFERENCE = "related_reference"


class RelationEvidence(BaseModel):
    source_refs: list[SourceReference] = Field(default_factory=list)
    note: str | None = None
    evidence_status: Literal["source_supported", "structural", "pending_review"] = "source_supported"


class StandardRelation(BaseModel):
    relation_id: str
    relation_type: StandardRelationType
    subject_ref: str
    target_ref: str
    subject_kind: Literal["standard", "family"] = "standard"
    target_kind: Literal["standard", "family"] = "standard"
    evidence: RelationEvidence = Field(default_factory=RelationEvidence)
    human_review_required: bool = False
    auto_inference_allowed: bool = False


class AccountingFamily(BaseModel):
    family_id: str
    family_name: str
    description: str
    jurisdiction_scopes: list[str] = Field(default_factory=list)
    member_standard_refs: list[str] = Field(default_factory=list)
    relation_policy: dict[str, Any] = Field(default_factory=dict)


class AccountingConcept(BaseModel):
    concept_id: str
    label: str
    definition: str
    concept_type: str
    status: Literal["seed", "reviewed", "deprecated"] = "seed"


class ConceptBinding(BaseModel):
    binding_id: str
    concept_id: str
    standard_ref: str
    account_ref: str
    mapping_type: Literal["exact_semantic_equivalent","closest_semantic_equivalent","partial_overlap","contextual"]
    evidence: list[SourceReference] = Field(default_factory=list)
    review_status: Literal["pending_human_review","approved","rejected"] = "pending_human_review"
    auto_approval_allowed: bool = False
    code_equality_used_as_evidence: bool = False
