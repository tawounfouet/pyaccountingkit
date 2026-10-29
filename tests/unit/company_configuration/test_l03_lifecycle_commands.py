"""ORG-4c domain command contracts: explicit scopes, revisions and terminal states."""

from dataclasses import replace
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from pyaccountingkit.company_configuration.application.organization_lifecycle import (
    LifecycleEvidence,
    LifecycleReceipt,
    TransitionCompany,
    TransitionEstablishment,
)
from pyaccountingkit.company_configuration.application.organization_registration import (
    OrganizationTargetKind,
)
from pyaccountingkit.company_configuration.domain.organization.model import (
    Company,
    CompanyKind,
    CompanyStatus,
    Establishment,
    EstablishmentStatus,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
)
from pyaccountingkit.company_configuration.domain.shared.errors import (
    InvalidOrganization,
    VersionConflict,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    CompanyId,
    EstablishmentId,
    LegalEntityId,
)
from pyaccountingkit.company_configuration.domain.shared.references import (
    JurisdictionCode,
)


def test_company_transition_command_requires_positive_revision_and_typed_state():
    company_id = CompanyId.new()
    valid = TransitionCompany(
        "tenant-a", company_id, CompanyStatus.ACTIVE, 1,
        "source", "request", "correlation", "reason",
    )
    assert valid.company_id == company_id
    with pytest.raises(InvalidOrganization):
        replace(valid, expected_revision=True)
    with pytest.raises(InvalidOrganization):
        replace(valid, to_status="ACTIVE")
    with pytest.raises(InvalidOrganization):
        replace(valid, tenant_id=" tenant-a ")


def test_establishment_command_guards_and_terminal_domain_transition():
    site_id = EstablishmentId.new()
    command = TransitionEstablishment(
        "tenant-a", site_id, EstablishmentStatus.ACTIVE, 1,
        "source", "request", "correlation", "reason",
    )
    assert command.establishment_id == site_id
    with pytest.raises(InvalidOrganization):
        replace(command, establishment_id=uuid4())
    site = Establishment(
        site_id, "tenant-a", LegalEntityId.new(), "Paris",
        JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)),
    )
    closed = site.transition(
        to=EstablishmentStatus.CLOSED, expected_revision=1,
    )
    with pytest.raises(InvalidOrganization):
        closed.transition(to=EstablishmentStatus.ACTIVE, expected_revision=2)


def test_company_domain_identity_survives_status_revisions():
    org = Company(
        CompanyId.new(), "tenant-a", "Group", CompanyKind.GROUP,
        JurisdictionCode("FR"),
    )
    active = org.transition(to=CompanyStatus.ACTIVE, expected_revision=1)
    assert active.id == org.id and active == org and active.revision == 2
    with pytest.raises(VersionConflict):
        active.transition(to=CompanyStatus.INACTIVE, expected_revision=1)


def test_lifecycle_evidence_keeps_real_target_not_fabricated_legal_entity():
    receipt = LifecycleReceipt(
        "tenant-a", OrganizationTargetKind.COMPANY, uuid4(), 2,
        "correlation", uuid4(), uuid4(),
    )
    row = LifecycleEvidence(
        receipt, "actor", "organization.company.transition", "req",
        "a" * 64, "DRAFT", "ACTIVE", "approved", 1,
        datetime(2026, 10, 29, tzinfo=UTC),
    )
    assert row.receipt.target_kind is OrganizationTargetKind.COMPANY
    with pytest.raises(InvalidOrganization):
        replace(row, before_revision=2)
    with pytest.raises(InvalidOrganization):
        replace(row, to_status="DRAFT")
