"""LOT-17 qualification for RegulatoryReportingProfile."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.core.errors import EntityScopeMismatchError
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.reporting.errors import (
    RegulatoryProfileError,
    RegulatoryProfileNotActiveError,
    RegulatoryProfileNotEffectiveError,
    RegulatoryReferenceMismatchError,
)
from pyaccountingkit.domain.reporting.regulatory_profile import (
    RegulatoryProfileStatus,
    RegulatoryReportingProfile,
)

ENTITY = EntityId("entity-a")
OTHER_ENTITY = EntityId("entity-b")


def _profile(
    *,
    status: RegulatoryProfileStatus = RegulatoryProfileStatus.ACTIVE,
    entity_id: EntityId | None = ENTITY,
    effective_from: date = date(2026, 1, 1),
    effective_to: date | None = None,
) -> RegulatoryReportingProfile:
    return RegulatoryReportingProfile(
        profile_id="profile-pcg-2026",
        code="PCG_FR_2026",
        framework="PCG",
        jurisdiction="FR",
        edition="2026",
        version="1",
        status=status,
        reference_snapshot_id="ref-pcg-2026",
        reference_snapshot_checksum="a" * 64,
        financial_statement_definition_ids=("bs-pcg", "is-pcg"),
        regulatory_mapping_set_id="reg-map-pcg-2026",
        export_definition_ids=("json-pcg",),
        effective_from=effective_from,
        effective_to=effective_to,
        accounting_entity_id=entity_id,
    )


def test_active_profile_accepts_exact_execution_coordinates() -> None:
    profile = _profile()

    profile.assert_executable(
        entity_id=ENTITY,
        as_of=date(2026, 12, 31),
        reference_snapshot_id="ref-pcg-2026",
        reference_snapshot_checksum="a" * 64,
    )


def test_draft_profile_is_not_executable() -> None:
    with pytest.raises(RegulatoryProfileNotActiveError):
        _profile(status=RegulatoryProfileStatus.DRAFT).assert_executable(
            entity_id=ENTITY,
            as_of=date(2026, 12, 31),
            reference_snapshot_id="ref-pcg-2026",
            reference_snapshot_checksum="a" * 64,
        )


def test_profile_must_be_effective_on_execution_date() -> None:
    with pytest.raises(RegulatoryProfileNotEffectiveError):
        _profile(effective_from=date(2027, 1, 1)).assert_executable(
            entity_id=ENTITY,
            as_of=date(2026, 12, 31),
            reference_snapshot_id="ref-pcg-2026",
            reference_snapshot_checksum="a" * 64,
        )


def test_entity_scoped_profile_rejects_cross_entity_execution() -> None:
    with pytest.raises(EntityScopeMismatchError):
        _profile().assert_executable(
            entity_id=OTHER_ENTITY,
            as_of=date(2026, 12, 31),
            reference_snapshot_id="ref-pcg-2026",
            reference_snapshot_checksum="a" * 64,
        )


def test_global_profile_can_execute_for_any_entity() -> None:
    _profile(entity_id=None).assert_executable(
        entity_id=OTHER_ENTITY,
        as_of=date(2026, 12, 31),
        reference_snapshot_id="ref-pcg-2026",
        reference_snapshot_checksum="a" * 64,
    )


def test_reference_snapshot_coordinates_are_exact() -> None:
    with pytest.raises(RegulatoryReferenceMismatchError):
        _profile().assert_executable(
            entity_id=ENTITY,
            as_of=date(2026, 12, 31),
            reference_snapshot_id="ref-pcg-latest",
            reference_snapshot_checksum="a" * 64,
        )

    with pytest.raises(RegulatoryReferenceMismatchError):
        _profile().assert_executable(
            entity_id=ENTITY,
            as_of=date(2026, 12, 31),
            reference_snapshot_id="ref-pcg-2026",
            reference_snapshot_checksum="b" * 64,
        )


def test_profile_rejects_invalid_effective_interval() -> None:
    with pytest.raises(RegulatoryProfileError):
        _profile(
            effective_from=date(2026, 12, 31),
            effective_to=date(2026, 1, 1),
        )


def test_profile_checksum_is_deterministic() -> None:
    first = _profile()
    second = RegulatoryReportingProfile(
        profile_id=first.profile_id,
        code=first.code,
        framework=first.framework,
        jurisdiction=first.jurisdiction,
        edition=first.edition,
        version=first.version,
        status=first.status,
        reference_snapshot_id=first.reference_snapshot_id,
        reference_snapshot_checksum=first.reference_snapshot_checksum,
        financial_statement_definition_ids=("is-pcg", "bs-pcg"),
        regulatory_mapping_set_id=first.regulatory_mapping_set_id,
        export_definition_ids=first.export_definition_ids,
        effective_from=first.effective_from,
        effective_to=first.effective_to,
        accounting_entity_id=first.accounting_entity_id,
    )

    assert first.checksum == second.checksum
