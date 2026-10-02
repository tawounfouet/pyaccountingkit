"""Filesystem provider for reviewed EBNL/SYSCOHADA structural crosswalk evidence."""

from __future__ import annotations

import json
from pathlib import Path

from pyaccountingkit.domain.references.crosswalks import (
    CrosswalkCandidateStatus,
    CrosswalkOccurrence,
    ReviewedStructuralCrosswalk,
    StructuralCrosswalkCandidate,
)

EBNL_SYSCOHADA_CROSSWALK_FILENAME = "ebnl_2023_vs_syscohada_2017_structural_delta.json"


class EBNLSYSCOHADAStructuralCrosswalkAdapter:
    """Expose structural candidates without converting them to executable mappings."""

    def __init__(self, crosswalk_path: Path) -> None:
        self._path = crosswalk_path

    def get_crosswalk(self) -> ReviewedStructuralCrosswalk:
        document = json.loads(
            (self._path / EBNL_SYSCOHADA_CROSSWALK_FILENAME).read_text(encoding="utf-8")
        )
        policy = document["comparison_policy"]
        rows = tuple(
            StructuralCrosswalkCandidate(
                ref_code=row["ref_code"],
                status=CrosswalkCandidateStatus(row["status"]),
                syscohada_label=row.get("syscohada_label"),
                ebnl_occurrences=tuple(
                    CrosswalkOccurrence(
                        record_id=occ["record_id"],
                        label=occ["label_source"],
                        page_pdf=occ["page_pdf"],
                        source_group_context=occ.get("source_group_context"),
                    )
                    for occ in row["ebnl_occurrences"]
                ),
                human_review_required=row["human_review_required"],
                semantic_equivalence_asserted=row["semantic_equivalence_asserted"],
            )
            for row in document["rows"]
        )
        return ReviewedStructuralCrosswalk(
            comparison_id=document["comparison_id"],
            relation_type=policy["relation_type"],
            rows=rows,
            automatic_crosswalk_approval=policy["automatic_crosswalk_approval"],
            human_review_required_for_semantics=policy["human_review_required_for_semantics"],
            inheritance_asserted=policy["inheritance_asserted"],
            semantic_equivalence_from_code_equality=policy[
                "semantic_equivalence_from_code_equality"
            ],
        )


__all__ = ["EBNL_SYSCOHADA_CROSSWALK_FILENAME", "EBNLSYSCOHADAStructuralCrosswalkAdapter"]
