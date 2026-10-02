"""OHADA standard-relation and negative-constraint filesystem provider (LOT-27)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pyaccountingkit.domain.references.capabilities import (
    ReferenceCapability,
    ReferenceCapabilitySet,
)
from pyaccountingkit.domain.references.standard_relations import (
    ReferenceNegativeConstraint,
    ReferenceRelation,
    ReferenceRelationEvidence,
    ReferenceRelationKind,
    ReferenceRelationRegistry,
    ReferenceRelationSource,
    ReferenceRelationType,
    RelationEvidenceStatus,
)

OHADA_RELATIONS_FILENAME = "ohada_accounting_standard_relations.json"


class OHADARelationFilesystemAdapter:
    """Expose explicit OHADA relations; no implicit inheritance or crosswalk execution."""

    def __init__(
        self,
        base_path: Path,
        *,
        filename: str = OHADA_RELATIONS_FILENAME,
    ) -> None:
        self._base_path = base_path
        self._filename = filename
        self._registry: ReferenceRelationRegistry | None = None

    def registry(self) -> ReferenceRelationRegistry:
        if self._registry is None:
            raw = (self._base_path / self._filename).read_text(encoding="utf-8")
            document: Any = json.loads(raw)
            if not isinstance(document, dict):
                raise ValueError("OHADA relations must contain a JSON object")
            self._registry = parse_relation_registry(document)
        return self._registry

    def relations_for(self, subject_ref: str) -> tuple[ReferenceRelation, ...]:
        return self.registry().relations_for(subject_ref)

    def negative_constraints_for(
        self,
        subject_ref: str,
    ) -> tuple[ReferenceNegativeConstraint, ...]:
        return self.registry().negative_constraints_for(subject_ref)

    def require_auto_inference_allowed(
        self,
        subject_ref: str,
        relation_type: ReferenceRelationType,
        target_ref: str,
    ) -> ReferenceRelation:
        return self.registry().require_auto_inference_allowed(
            subject_ref,
            relation_type,
            target_ref,
        )

    def capabilities(self, standard_ref: str) -> ReferenceCapabilitySet:
        capabilities: set[ReferenceCapability] = set()
        if self.relations_for(standard_ref):
            capabilities.add(ReferenceCapability.RELATIONS)
        if self.negative_constraints_for(standard_ref):
            capabilities.add(ReferenceCapability.NEGATIVE_CONSTRAINTS)
        return ReferenceCapabilitySet(frozenset(capabilities))


def parse_relation_registry(document: Mapping[str, Any]) -> ReferenceRelationRegistry:
    """Parse the canonical OHADA family relation dataset."""
    raw_relations = document.get("relations")
    raw_constraints = document.get("negative_constraints")
    if not isinstance(raw_relations, list):
        raise ValueError("relations must be a list")
    if not isinstance(raw_constraints, list):
        raise ValueError("negative_constraints must be a list")
    return ReferenceRelationRegistry(
        tuple(_parse_relation(raw) for raw in raw_relations),
        tuple(_parse_negative_constraint(raw) for raw in raw_constraints),
    )


def _parse_relation(raw: object) -> ReferenceRelation:
    if not isinstance(raw, dict):
        raise ValueError("relation must be a JSON object")

    raw_evidence = raw.get("evidence")
    if not isinstance(raw_evidence, dict):
        raise ValueError("relation evidence must be a JSON object")
    raw_source_refs = raw_evidence.get("source_refs", [])
    if not isinstance(raw_source_refs, list):
        raise ValueError("relation source_refs must be a list")

    return ReferenceRelation(
        relation_id=_required_string(raw, "relation_id"),
        relation_type=ReferenceRelationType(_required_string(raw, "relation_type")),
        subject_ref=_required_string(raw, "subject_ref"),
        target_ref=_required_string(raw, "target_ref"),
        subject_kind=ReferenceRelationKind(_required_string(raw, "subject_kind")),
        target_kind=ReferenceRelationKind(_required_string(raw, "target_kind")),
        evidence=ReferenceRelationEvidence(
            source_refs=tuple(_parse_source_ref(item) for item in raw_source_refs),
            note=_optional_string(raw_evidence.get("note")),
            status=RelationEvidenceStatus(
                _required_string(raw_evidence, "evidence_status")
            ),
        ),
        human_review_required=_required_bool(raw, "human_review_required"),
        auto_inference_allowed=_required_bool(raw, "auto_inference_allowed"),
    )


def _parse_negative_constraint(raw: object) -> ReferenceNegativeConstraint:
    if not isinstance(raw, dict):
        raise ValueError("negative constraint must be a JSON object")
    return ReferenceNegativeConstraint(
        constraint_id=_required_string(raw, "constraint_id"),
        forbidden_relation_type=ReferenceRelationType(
            _required_string(raw, "forbidden_relation_type")
        ),
        subject_ref=_required_string(raw, "subject_ref"),
        target_ref=_required_string(raw, "target_ref"),
        reason=_required_string(raw, "reason"),
    )


def _parse_source_ref(raw: object) -> ReferenceRelationSource:
    if not isinstance(raw, dict):
        raise ValueError("relation source reference must be a JSON object")
    heading = raw.get("heading_path", [])
    if not isinstance(heading, list) or not all(isinstance(item, str) for item in heading):
        raise ValueError("relation heading_path must be a string list")
    page_pdf = raw.get("page_pdf")
    if page_pdf is not None and not isinstance(page_pdf, int):
        raise ValueError("relation page_pdf must be an integer or null")
    return ReferenceRelationSource(
        document_id=_required_string(raw, "document_id"),
        page_pdf=page_pdf,
        section=_optional_string(raw.get("section")),
        heading_path=tuple(heading),
        snippet=_optional_string(raw.get("snippet")),
    )


def _required_string(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional relation field must be string or null")
    return value


def _required_bool(raw: Mapping[str, Any], key: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


__all__ = [
    "OHADA_RELATIONS_FILENAME",
    "OHADARelationFilesystemAdapter",
    "parse_relation_registry",
]
