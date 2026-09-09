from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.organizations.models import Organization, OrganizationMembership

pytestmark = pytest.mark.django_db

def test_user_can_create_organization(client):
    user = get_user_model().objects.create_user(
        username="thomas",
        email="thomas@example.com",
        password="secret1234",
    )
    client.force_login(user)

    response = client.post(
        reverse("organizations:create"),
        {
            "name": "Demo SARL",
            "legal_name": "Demo SARL",
            "registration_number": "RC-001",
            "base_currency": "XAF",
            "country_code": "CM",
        },
    )

    assert response.status_code == 302
    organization = Organization.objects.get(name="Demo SARL")
    membership = OrganizationMembership.objects.get(organization=organization, user=user)
    assert membership.role == OrganizationMembership.Role.ADMIN
    assert organization.charts_of_accounts.filter(code="ENTITY").exists()
    assert organization.journals.count() == 8

def test_admin_can_create_fiscal_year_and_periods(client):
    user = get_user_model().objects.create_user(
        username="admin2",
        email="admin2@example.com",
        password="secret1234",
    )
    organization = Organization.objects.create(name="Org")
    OrganizationMembership.objects.create(
        organization=organization,
        user=user,
        role=OrganizationMembership.Role.ADMIN,
    )
    client.force_login(user)

    response = client.post(
        reverse("organizations:fiscal-year-create", kwargs={"organization_id": organization.pk}),
        {
            "name": "2025",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        },
    )

    assert response.status_code == 302
    fiscal_year = organization.fiscal_years.get(name="2025")
    assert fiscal_year.periods.count() == 12
