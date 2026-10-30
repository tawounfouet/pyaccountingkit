"""ORG-4b typed registration contracts and explicit organization identities."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from pyaccountingkit.company_configuration.application.organization_registration import (
    OrganizationEvidence,
    OrganizationRegistrationReceipt,
    OrganizationTargetKind,
    RegisterCompany,
    RegisterEstablishment,
    RegisterLegalIdentifier,
)
from pyaccountingkit.company_configuration.domain.organization.model import (
    Company,
    CompanyKind,
    Establishment,
    LegalIdentifier,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import EffectiveInterval
from pyaccountingkit.company_configuration.domain.shared.errors import InvalidOrganization
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    CompanyId,
    EstablishmentId,
    LegalEntityId,
)
from pyaccountingkit.company_configuration.domain.shared.references import JurisdictionCode


def test_company_registration_needs_no_fabricated_legal_entity_scope():
    org = Company(
        CompanyId.new(), "tenant-a", "New group", CompanyKind.GROUP,
        JurisdictionCode("FR"),
    )
    cmd = RegisterCompany(org, "request", "correlation", "board approval")
    assert cmd.company.id == org.id
    assert not hasattr(cmd, "scope")
    assert not hasattr(cmd.company, "legal_entity_id")


def test_establishment_registration_uses_real_legal_entity_parent():
    entity_id = LegalEntityId.new()
    site = Establishment(
        EstablishmentId.new(), "tenant-a", entity_id, "Paris",
        JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)),
    )
    assert RegisterEstablishment(site, "request", "correlation", "reason").establishment == site


def test_registry_registration_requires_explicit_stable_uuid():
    item = LegalIdentifier(
        "tenant-a", LegalEntityId.new(), "SIREN", "123456789", "INSEE",
        JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)), "register",
    )
    with pytest.raises(InvalidOrganization):
        RegisterLegalIdentifier("not-uuid", item, "request", "correlation", "reason")
    identifier = uuid4()
    assert RegisterLegalIdentifier(
        identifier, item, "request", "correlation", "reason"
    ).identifier_id == identifier


def test_receipt_and_evidence_preserve_typed_target_and_utc_instant():
    receipt = OrganizationRegistrationReceipt(
        "tenant-a", OrganizationTargetKind.COMPANY, uuid4(), 1,
        "corr", uuid4(), uuid4(),
    )
    row = OrganizationEvidence(
        receipt, "actor", "organization.company.register", "request",
        "a" * 64, "reason", datetime(2026, 10, 29, tzinfo=UTC),
        receipt.target_id, None,
    )
    assert row.receipt.target_id == row.company_id
    assert row.legal_entity_id is None
    with pytest.raises(InvalidOrganization):
        OrganizationRegistrationReceipt(
            "tenant-a", OrganizationTargetKind.COMPANY, uuid4(), 2,
            "corr", uuid4(), uuid4(),
        )
