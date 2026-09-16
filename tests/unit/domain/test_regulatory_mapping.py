"""LOT-17 qualification for statement-line to regulatory-node mappings."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.reporting.errors import (
    NonExecutableRegulatoryMappingError,
    RegulatoryMappingError,
)
from pyaccountingkit.domain.reporting.regulatory_mapping import (
    RegulatoryMappingProvenance,
    RegulatoryMappingSet,
    RegulatoryMappingSetStatus,
    RegulatoryMappingStatus,
    RegulatoryStatementMapping,
)

ENTITY = EntityId("entity-a")
AS_OF = date(2026, 12, 31)


def _mapping(
    mapping_id: str,
    source: str,
    target: str,
    *,
    allocation: str = "1",
    status: RegulatoryMappingStatus = RegulatoryMappingStatus.VALIDATED,
    provenance: RegulatoryMappingProvenance = RegulatoryMappingProvenance.MANUAL,
    review_required: bool = False,
) -> RegulatoryStatementMapping:
    return RegulatoryStatementMapping(
        mapping_id=mapping_id,
        statement_line_code=source,
        reference_node_id=target,
        allocation=Decimal(allocation),
        status=status,
        provenance=provenance,
        effective_from=date(2026, 1, 1),
        review_required=review_required,
    )


def _set(
    *mappings: RegulatoryStatementMapping,
    status: RegulatoryMappingSetStatus = RegulatoryMappingSetStatus.ACTIVE,
) -> RegulatoryMappingSet:
    return RegulatoryMappingSet(
        mapping_set_id="reg-map-1",
        accounting_entity_id=ENTITY,
        profile_id="profile-pcg-2026",
        reference_model_id="pcg-balance-sheet",
        version="1",
        status=status,
        mappings=mappings,
        effective_from=date(2026, 1, 1),
    )


def test_active_validated_mapping_set_is_executable() -> None:
    mapping_set = _set(_mapping("m1", "ASSETS", "node-assets"))

    assert mapping_set.is_executable is True
    assert mapping_set.executable_mappings_for("ASSETS", as_of=AS_OF)[0].reference_node_id == (
        "node-assets"
    )


def test_candidate_mapping_makes_set_non_executable() -> None:
    mapping_set = _set(
        _mapping(
            "m1",
            "ASSETS",
            "node-assets",
            status=RegulatoryMappingStatus.CANDIDATE,
            provenance=RegulatoryMappingProvenance.REFERENCE_HINT,
            review_required=True,
        )
    )

    assert mapping_set.is_executable is False
    with pytest.raises(NonExecutableRegulatoryMappingError):
        mapping_set.executable_mappings_for("ASSETS", as_of=AS_OF)


def test_reference_hint_cannot_be_marked_validated_directly() -> None:
    with pytest.raises(RegulatoryMappingError, match="explicit validation provenance"):
        _mapping(
            "m1",
            "ASSETS",
            "node-assets",
            status=RegulatoryMappingStatus.VALIDATED,
            provenance=RegulatoryMappingProvenance.REFERENCE_HINT,
        )


def test_review_required_mapping_cannot_be_validated() -> None:
    with pytest.raises(RegulatoryMappingError, match="review-required"):
        _mapping("m1", "ASSETS", "node-assets", review_required=True)


def test_validated_candidate_requires_explicit_validated_provenance() -> None:
    mapping = _mapping(
        "m1",
        "ASSETS",
        "node-assets",
        provenance=RegulatoryMappingProvenance.VALIDATED_CANDIDATE,
    )

    assert mapping.is_executable is True


def test_one_to_many_allocations_must_sum_to_one() -> None:
    mapping_set = _set(
        _mapping("m1", "RESULT", "node-a", allocation="0.6"),
        _mapping("m2", "RESULT", "node-b", allocation="0.4"),
    )

    mapping_set.assert_allocations(as_of=AS_OF)

    invalid = _set(_mapping("m3", "RESULT", "node-a", allocation="0.6"))
    with pytest.raises(RegulatoryMappingError, match="allocate exactly 1"):
        invalid.assert_allocations(as_of=AS_OF)


def test_non_active_mapping_set_is_not_executable() -> None:
    mapping_set = _set(
        _mapping("m1", "ASSETS", "node-assets"),
        status=RegulatoryMappingSetStatus.DRAFT,
    )

    assert mapping_set.is_executable is False
    with pytest.raises(NonExecutableRegulatoryMappingError):
        mapping_set.assert_allocations(as_of=AS_OF)


def test_mapping_set_checksum_is_deterministic() -> None:
    first = _set(
        _mapping("m1", "A", "node-a"),
        _mapping("m2", "B", "node-b"),
    )
    second = _set(
        _mapping("m2", "B", "node-b"),
        _mapping("m1", "A", "node-a"),
    )

    assert first.checksum == second.checksum
