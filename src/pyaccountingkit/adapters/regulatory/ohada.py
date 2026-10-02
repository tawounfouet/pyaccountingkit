"""OHADA EBNL structure and standard-relation providers (LOT-27)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pyaccountingkit.adapters.regulatory.filesystem import LocalFilesystemReferenceAdapter
from pyaccountingkit.core.clock import ClockProtocol
from pyaccountingkit.domain.references.capabilities import (
    EBNL_STRUCTURE_CAPABILITIES,
    ReferenceCapabilitySet,
)
from pyaccountingkit.domain.references.standard_relations import (
    ForbiddenStandardRelation,
    RelationEvidenceSource,
    StandardRelation,
    StandardRelationEvidence,
    StandardRelationRegister,
    StandardRelationType,
)
from pyaccountingkit.domain.references.standards import StandardType

EBNL_STRUCTURE_FILENAME = "ebnl_2023_v1_structure.json"
OHADA_RELATIONS_FILENAME = "ohada_accounting_standard_relations.json"


class EBNLFilesystemReferenceAdapter(LocalFilesystemReferenceAdapter):
    """Structural provider for the reviewed OHADA EBNL 2023 chart."""

    def __init__(
        self,
        structured_path: Path,
        *,
        clock: ClockProtocol | None = None,
    ) -> None:
        super().__init__(
            structured_path,
            clock=clock,
            resource_names={StandardType.OHADA_EBNL: EBNL_STRUCTURE_FILENAME},
        )

    def capabilities(self, standard: StandardType) -> ReferenceCapabilitySet:
        if standard is not StandardType.OHADA_EBNL:
            return ReferenceCapabilitySet()
        self.get_hierarchy(standard)
        return EBNL_STRUCTURE_CAPABILITIES


class OHADAStandardRelationFilesystemAdapter:
    """Read the explicit OHADA family relation and negative-constraint dataset."""

    def __init__(
        self,
        relation_path: Path,
        *,
        filename: str = OHADA_RELATIONS_FILENAME,
    ) -> None:
        self._relation_path = relation_path
        self._filename = filename
        self._register: StandardRelationRegister | None = None

    def relation_register(self) -> StandardRelationRegister:
        if self._register is None:
            raw = (self._relation_path / self._filename).read_text(encoding="utf-8")
            document = json.loads(raw)
            if not isinstance(document, dict):
                raise ValueError("OHADA relation dataset must be a JSON object")
            self._register = parse_standard_relation_register(document)
        return self._register

    def relations_for(
        self,
        subject_ref: str,
        relation_type: StandardRelationType | None = None,
    ) -> tuple[StandardRelation, ...]:
        return self.relation_register().relations_for(subject_ref, relation_type)

    def require_not_forbidden(
        self,
        subject_ref: str,
        relation_type: StandardRelationType,
        target_ref: str,
    ) -> None:
        self.relation_register().require_not_forbidden(
            subject_ref,
            relation_type,
            target_ref,
        )

    def require_auto_inference_allowed(
        self,
        subject_ref: str,
        relation_type: StandardRelationType,
        target_ref: str,
    ) -> None:
        self.relation_register().require_auto_inference_allowed(
            subject_ref,
            relation_type,
            target_ref,
        )

    def can_auto_infer(
        self,
        subject_ref: str,
        relation_type: StandardRelationType,
        target_ref: str,
    ) -> bool:
        return self.relation_register().can_auto_infer(
            subject_ref,
            relation_type,
            target_ref,
        )


def parse_standard_relation_register(
    document: Mapping[str, Any],
) -> StandardRelationRegister:
    """Parse explicit relations and negative constraints without deriving new edges."""
    raw_relations = document.get("relations")
    raw_constraints = document.get("negative_constraints")
    if not isinstance(raw_relations, list):
        raise ValueError("relations must be a list")
    if not isinstance(raw_constraints, list):
        raise ValueError("negative_constraints must be a list")

    return StandardRelationRegister(
        family_id=_required_string(document, "family_id"),
        relations=tuple(_parse_relation(raw) for raw in raw_relations),
        negative_constraints=tuple(
            _parse_negative_constraint(raw) for raw in raw_constraints
        ),
    )


def _parse_relation(raw: object) -> StandardRelation:
    if not isinstance(raw, dict):
        raise ValueError("standard relation must be a JSON object")
    evidence = raw.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError("standard relation evidence must be a JSON object")
    source_refs = evidence.get("source_refs")
    if not isinstance(source_refs, list):
        raise ValueError("standard relation source_refs must be a list")

    return StandardRelation(
        relation_id=_required_string(raw, "relation_id"),
        relation_type=StandardRelationType(_required_string(raw, "relation_type")),
        subject_ref=_required_string(raw, "subject_ref"),
        target_ref=_required_string(raw, "target_ref"),
        subject_kind=_required_string(raw, "subject_kind"),
        target_kind=_required_string(raw, "target_kind"),
        evidence=StandardRelationEvidence(
            source_refs=tuple(_parse_evidence_source(item) for item in source_refs),
            note=_required_string(evidence, "note"),
            evidence_status=_required_string(evidence, "evidence_status"),
        ),
        human_review_required=_required_bool(raw, "human_review_required"),
        auto_inference_allowed=_required_bool(raw, "auto_inference_allowed"),
    )


def _parse_negative_constraint(raw: object) -> ForbiddenStandardRelation:
    if not isinstance(raw, dict):
        raise ValueError("negative constraint must be a JSON object")
    return ForbiddenStandardRelation(
        constraint_id=_required_string(raw, "constraint_id"),
        relation_type=StandardRelationType(
            _required_string(raw, "forbidden_relation_type")
        ),
        subject_ref=_required_string(raw, "subject_ref"),
        target_ref=_required_string(raw, "target_ref"),
        reason=_required_string(raw, "reason"),
    )


def _parse_evidence_source(raw: object) -> RelationEvidenceSource:
    if not isinstance(raw, dict):
        raise ValueError("relation evidence source must be a JSON object")
    heading_path = raw.get("heading_path") or []
    if not isinstance(heading_path, list) or not all(
        isinstance(item, str) for item in heading_path
    ):
        raise ValueError("relation evidence heading_path must be a string list")
    page = raw.get("page_pdf")
    if page is not None and not isinstance(page, int):
        raise ValueError("relation evidence page_pdf must be an integer or null")
    return RelationEvidenceSource(
        document_id=_required_string(raw, "document_id"),
        page_pdf=page,
        section=_required_string(raw, "section"),
        heading_path=tuple(heading_path),
        snippet=_required_string(raw, "snippet"),
    )


def _required_string(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _required_bool(raw: Mapping[str, Any], key: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


__all__ = [
    "EBNLFilesystemReferenceAdapter",
    "EBNL_STRUCTURE_FILENAME",
    "OHADA_RELATIONS_FILENAME",
    "OHADAStandardRelationFilesystemAdapter",
    "parse_standard_relation_register",
]
