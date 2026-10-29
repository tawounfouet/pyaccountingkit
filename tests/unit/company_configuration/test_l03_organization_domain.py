"""L03 ORG-1/2: organizational identities, lifecycle and time-aware membership."""

from datetime import UTC, date, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyaccountingkit.company_configuration.domain.organization import (
    Company,
    CompanyKind,
    CompanyStatus,
    Establishment,
    EstablishmentStatus,
    LegalEntity,
    LegalIdentifier,
    MembershipKind,
    OrganizationMembership,
    active_memberships_at,
    require_establishment_parent,
    require_membership_parents,
    require_no_exclusive_membership_conflicts,
    require_unique_legal_identifier,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import EffectiveInterval
from pyaccountingkit.company_configuration.domain.shared.errors import (
    AmbiguousOrganization,
    InvalidOrganization,
    OrganizationConflict,
    VersionConflict,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    CompanyId,
    EstablishmentId,
    LegalEntityId,
    MembershipId,
)
from pyaccountingkit.company_configuration.domain.shared.references import (
    CurrencyCode,
    JurisdictionCode,
)

KNOWN = datetime(2026, 4, 8, 12, tzinfo=UTC)


def company(tenant="tenant-a"):
    return Company(
        CompanyId.new(), tenant, "Group", CompanyKind.GROUP,
        JurisdictionCode("FR"), CurrencyCode("EUR"),
    )


def entity(*, tenant="tenant-a"):
    legal_id = LegalEntityId.new()
    return LegalEntity(
        legal_id, ConfigurationScope(tenant, CompanyId.new(), legal_id),
        "Example SARL", JurisdictionCode("FR"), CurrencyCode("EUR"),
    )


def membership(
    legal_entity_id, company_id, *, tenant="tenant-a", recorded_at=KNOWN,
    start=date(2026, 1, 1), end=None, exclusive=True,
    kind=MembershipKind.ADMINISTRATIVE,
):
    return OrganizationMembership(
        MembershipId.new(), tenant, company_id, legal_entity_id,
        kind, exclusive, EffectiveInterval(start, end), recorded_at, "source-1",
    )


def test_company_identity_is_stable_across_revisions_and_tenants():
    source = company()
    amended = source.rename(name="Renamed", expected_revision=1)
    assert amended == source and hash(amended) == hash(source)
    assert amended.revision == 2 and source.name == "Group"
    other = Company(
        source.id, "tenant-b", source.name, source.kind, source.home_country
    )
    assert other != source
    with pytest.raises(VersionConflict):
        amended.rename(name="Stale", expected_revision=1)


def test_company_state_machine_rejects_illegal_transitions():
    draft = company()
    with pytest.raises(InvalidOrganization):
        draft.transition(to=CompanyStatus.ARCHIVED, expected_revision=1)
    active = draft.transition(to=CompanyStatus.ACTIVE, expected_revision=1)
    inactive = active.transition(to=CompanyStatus.INACTIVE, expected_revision=2)
    archived = inactive.transition(to=CompanyStatus.ARCHIVED, expected_revision=3)
    with pytest.raises(InvalidOrganization):
        archived.transition(to=CompanyStatus.ACTIVE, expected_revision=4)
    with pytest.raises(VersionConflict):
        active.transition(to=CompanyStatus.INACTIVE, expected_revision=True)


@pytest.mark.parametrize("bad", [None, "", " extra", "trailing ", 5])
def test_invalid_company_name_fails(bad):
    with pytest.raises(InvalidOrganization):
        Company(CompanyId.new(), "tenant-a", bad, CompanyKind.GROUP, JurisdictionCode("FR"))


def test_establishment_is_a_site_and_needs_matching_legal_person():
    legal = entity()
    site = Establishment(
        EstablishmentId.new(), "tenant-a", legal.id, "Paris HQ",
        JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)),
    )
    require_establishment_parent(site, legal)
    active = site.transition(to=EstablishmentStatus.ACTIVE, expected_revision=1)
    assert active.id == site.id and active != legal
    with pytest.raises(InvalidOrganization):
        require_establishment_parent(site, entity())
    with pytest.raises(InvalidOrganization):
        require_establishment_parent(site, entity(tenant="tenant-b"))


def test_membership_references_are_explicit_and_do_not_transfer_identity():
    legal = entity()
    group = company()
    affiliation = membership(legal.id, group.id)
    require_membership_parents(affiliation, group, legal)
    assert legal.scope.company_id != group.id
    with pytest.raises(InvalidOrganization):
        require_membership_parents(affiliation, company(tenant="tenant-b"), legal)
    with pytest.raises(InvalidOrganization):
        require_membership_parents(affiliation, group, entity())


def test_later_known_backdated_membership_end_preserves_old_known_at():
    legal = entity()
    group = company()
    first = membership(legal.id, group.id, recorded_at=KNOWN - timedelta(days=7))
    second = first.end(
        effective_end=date(2026, 4, 1), recorded_at=KNOWN,
        source_ref="sale-1", expected_revision=1,
    )
    assert first.revision == 1 and first.valid.end is None
    assert second.revision == 2 and second.valid.end == date(2026, 4, 1)

    old_view = active_memberships_at(
        [second, first], tenant_id="tenant-a", legal_entity_id=legal.id,
        effective_on=date(2026, 4, 3), known_at=KNOWN - timedelta(days=1),
    )
    new_view = active_memberships_at(
        [first, second], tenant_id="tenant-a", legal_entity_id=legal.id,
        effective_on=date(2026, 4, 3), known_at=KNOWN,
    )
    assert len(old_view) == 1 and old_view[0].revision == 1
    assert new_view == ()


def test_incompatible_history_and_non_monotone_amendments_fail():
    group, legal = company(), entity()
    source = membership(legal.id, group.id)
    with pytest.raises(InvalidOrganization):
        source.end(
            effective_end=date(2025, 12, 31), recorded_at=KNOWN + timedelta(days=1),
            source_ref="bad", expected_revision=1,
        )
    with pytest.raises(InvalidOrganization):
        source.end(
            effective_end=date(2026, 5, 1), recorded_at=KNOWN,
            source_ref="bad", expected_revision=1,
        )
    revision = source.end(
        effective_end=date(2026, 5, 1), recorded_at=KNOWN + timedelta(days=1),
        source_ref="closed", expected_revision=1,
    )
    with pytest.raises(OrganizationConflict):
        active_memberships_at(
            [revision], tenant_id="tenant-a", legal_entity_id=legal.id,
            effective_on=date(2026, 4, 1), known_at=KNOWN + timedelta(days=2),
        )


def test_exclusive_collisions_fail_and_nonexclusive_affiliations_coexist():
    legal, a, b = entity(), company(), company()
    first = membership(legal.id, a.id)
    overlapping = membership(legal.id, b.id)
    with pytest.raises(OrganizationConflict):
        require_no_exclusive_membership_conflicts([first, overlapping], known_at=KNOWN)
    with pytest.raises(AmbiguousOrganization):
        active_memberships_at(
            [first, overlapping], tenant_id="tenant-a", legal_entity_id=legal.id,
            effective_on=date(2026, 2, 1), known_at=KNOWN,
        )
    other = membership(
        legal.id, b.id, exclusive=False, kind=MembershipKind.OPERATIONAL
    )
    require_no_exclusive_membership_conflicts([first, other], known_at=KNOWN)
    assert len(active_memberships_at(
        [other, first], tenant_id="tenant-a", legal_entity_id=legal.id,
        effective_on=date(2026, 2, 1), known_at=KNOWN,
    )) == 2


def test_touching_exclusive_intervals_do_not_overlap():
    legal, a, b = entity(), company(), company()
    before = membership(legal.id, a.id, end=date(2026, 4, 1))
    after = membership(legal.id, b.id, start=date(2026, 4, 1))
    require_no_exclusive_membership_conflicts([before, after], known_at=KNOWN)
    result = active_memberships_at(
        [before, after], tenant_id="tenant-a", legal_entity_id=legal.id,
        effective_on=date(2026, 4, 1), known_at=KNOWN,
    )
    assert result == (after,)


def test_legal_identifier_conflict_is_scoped_by_registry_and_effectivity():
    a, b = entity(), entity()
    identifier = LegalIdentifier(
        "tenant-a", a.id, "SIREN", "123456789", "INSEE",
        JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)), "registry",
    )
    conflict = LegalIdentifier(
        "tenant-a", b.id, "SIREN", "123456789", "INSEE",
        JurisdictionCode("FR"), EffectiveInterval(date(2026, 2, 1)), "registry",
    )
    with pytest.raises(OrganizationConflict):
        require_unique_legal_identifier(conflict, [identifier])
    independent = LegalIdentifier(
        "tenant-b", b.id, "SIREN", "123456789", "INSEE",
        JurisdictionCode("FR"), EffectiveInterval(date(2026, 2, 1)), "registry",
    )
    require_unique_legal_identifier(independent, [identifier])
    later = LegalIdentifier(
        "tenant-a", b.id, "SIREN", "123456789", "INSEE",
        JurisdictionCode("FR"),
        EffectiveInterval(date(2027, 1, 1)), "registry",
    )
    old = LegalIdentifier(
        "tenant-a", a.id, "SIREN", "123456789", "INSEE",
        JurisdictionCode("FR"),
        EffectiveInterval(date(2026, 1, 1), date(2027, 1, 1)), "registry",
    )
    require_unique_legal_identifier(later, [old])


@given(
    start=st.dates(min_value=date(2020, 1, 1), max_value=date(2040, 1, 1)),
    duration=st.integers(min_value=1, max_value=200),
)
def test_membership_half_open_end_matches_effective_intervals(start, duration):
    end = start + timedelta(days=duration)
    legal, group = entity(), company()
    first = membership(legal.id, group.id, start=start, end=end)
    assert first.valid.contains(start)
    assert not first.valid.contains(end)
    assert active_memberships_at(
        [first], tenant_id=first.tenant_id,
        legal_entity_id=first.legal_entity_id,
        effective_on=end, known_at=KNOWN,
    ) == ()
