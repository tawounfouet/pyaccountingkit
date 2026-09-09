from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.accounting.models import Account, JournalEntry
from apps.accounting.services import (
    bootstrap_accounting_core,
    create_draft_entry,
    post_journal_entry,
    reverse_journal_entry,
    validate_journal_entry,
)
from apps.audit.models import AuditEvent
from apps.organizations.models import AccountingPeriod, FiscalYear, Organization, OrganizationMembership

pytestmark = pytest.mark.django_db


@pytest.fixture
def workflow_case():
    User = get_user_model()
    reviewer = User.objects.create_user(
        username="reviewer",
        email="reviewer@example.com",
        password="secret1234",
    )
    accountant = User.objects.create_user(
        username="accountant-s3",
        email="accountant-s3@example.com",
        password="secret1234",
    )

    organization = Organization.objects.create(
        name="Sprint 3 Demo",
        base_currency="XAF",
        country_code="CM",
    )
    OrganizationMembership.objects.create(
        organization=organization,
        user=reviewer,
        role=OrganizationMembership.Role.REVIEWER,
    )
    OrganizationMembership.objects.create(
        organization=organization,
        user=accountant,
        role=OrganizationMembership.Role.ACCOUNTANT,
    )

    fiscal_year = FiscalYear.objects.create(
        organization=organization,
        name="2025",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )
    period = AccountingPeriod.objects.create(
        fiscal_year=fiscal_year,
        period_number=1,
        name="2025-01",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
    )

    chart, journals = bootstrap_accounting_core(organization=organization)
    journal = next(item for item in journals if item.code == "JOD")

    cash = Account.objects.create(
        organization=organization,
        chart=chart,
        code="57110000",
        name="Caisse",
        account_type=Account.AccountType.ASSET,
        normal_balance=Account.NormalBalance.DEBIT,
    )
    capital = Account.objects.create(
        organization=organization,
        chart=chart,
        code="10110000",
        name="Capital",
        account_type=Account.AccountType.EQUITY,
        normal_balance=Account.NormalBalance.CREDIT,
    )

    return {
        "reviewer": reviewer,
        "accountant": accountant,
        "organization": organization,
        "period": period,
        "journal": journal,
        "cash": cash,
        "capital": capital,
    }


def create_balanced_draft(case, *, user=None, number="S3-001"):
    return create_draft_entry(
        organization=case["organization"],
        user=user or case["accountant"],
        journal=case["journal"],
        period=case["period"],
        entry_number=number,
        posting_date=date(2025, 1, 15),
        description="Écriture Sprint 3",
        lines=[
            {
                "account": case["cash"],
                "debit": Decimal("1000"),
                "credit": Decimal("0"),
            },
            {
                "account": case["capital"],
                "debit": Decimal("0"),
                "credit": Decimal("1000"),
            },
        ],
    )


def set_active_organization(client, case, user):
    client.force_login(user)
    session = client.session
    session["active_organization_id"] = str(case["organization"].pk)
    session.save()


def test_strict_draft_validated_posted_workflow(workflow_case):
    entry = create_balanced_draft(workflow_case)

    entry = validate_journal_entry(
        entry=entry,
        user=workflow_case["reviewer"],
    )
    assert entry.status == JournalEntry.Status.VALIDATED
    assert entry.validated_by == workflow_case["reviewer"]

    entry = post_journal_entry(
        entry=entry,
        user=workflow_case["reviewer"],
    )
    assert entry.status == JournalEntry.Status.POSTED
    assert entry.posted_by == workflow_case["reviewer"]

    actions = list(
        AuditEvent.objects.filter(
            organization=workflow_case["organization"],
            entity_id=str(entry.id),
        )
        .order_by("created_at")
        .values_list("action", flat=True)
    )
    assert actions == ["ENTRY_CREATE", "ENTRY_VALIDATE", "ENTRY_POST"]


def test_draft_cannot_be_posted_directly(workflow_case):
    entry = create_balanced_draft(workflow_case, number="S3-002")

    with pytest.raises(ValidationError):
        post_journal_entry(
            entry=entry,
            user=workflow_case["reviewer"],
        )

    entry.refresh_from_db()
    assert entry.status == JournalEntry.Status.DRAFT


def test_reversal_swaps_debit_credit_and_marks_original_reversed(workflow_case):
    original = create_balanced_draft(workflow_case, number="S3-003")
    original = validate_journal_entry(
        entry=original,
        user=workflow_case["reviewer"],
    )
    original = post_journal_entry(
        entry=original,
        user=workflow_case["reviewer"],
    )

    reversal = reverse_journal_entry(
        entry=original,
        user=workflow_case["reviewer"],
        period=workflow_case["period"],
        posting_date=date(2025, 1, 20),
        reason="Correction de test",
    )

    original.refresh_from_db()
    reversal.refresh_from_db()

    assert original.status == JournalEntry.Status.REVERSED
    assert reversal.status == JournalEntry.Status.POSTED
    assert reversal.entry_type == JournalEntry.EntryType.REVERSAL
    assert reversal.reversal_of_id == original.id

    original_lines = list(original.lines.order_by("line_number"))
    reversal_lines = list(reversal.lines.order_by("line_number"))

    assert reversal_lines[0].debit == original_lines[0].credit
    assert reversal_lines[0].credit == original_lines[0].debit
    assert reversal_lines[1].debit == original_lines[1].credit
    assert reversal_lines[1].credit == original_lines[1].debit

    assert AuditEvent.objects.filter(
        organization=workflow_case["organization"],
        entity_id=str(original.id),
        action="ENTRY_REVERSE",
    ).exists()


def test_htmx_totals_endpoint_reports_balanced_entry(client, workflow_case):
    set_active_organization(client, workflow_case, workflow_case["accountant"])

    response = client.post(
        reverse("accounting:entry-totals"),
        {
            "lines-TOTAL_FORMS": "2",
            "lines-0-debit": "1000",
            "lines-0-credit": "",
            "lines-1-debit": "",
            "lines-1-credit": "1000",
        },
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "1,000" in content or "1000" in content
    assert "ÉQUILIBRÉ" in content


def test_htmx_add_line_returns_next_form_index(client, workflow_case):
    set_active_organization(client, workflow_case, workflow_case["accountant"])

    response = client.get(
        reverse("accounting:entry-line-form"),
        {"lines-TOTAL_FORMS": "2"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "lines-2-account" in content
    assert 'id="line-row-2"' in content
    assert "HX-Trigger" not in response.headers


def test_htmx_remove_line_returns_delete_tombstone(client, workflow_case):
    set_active_organization(client, workflow_case, workflow_case["accountant"])

    response = client.post(
        reverse("accounting:entry-line-remove", kwargs={"index": 1}),
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert 'name="lines-1-DELETE"' in content
    assert 'value="on"' in content
    assert response.headers["HX-Trigger"] == "entryLineChanged"


def test_accountant_cannot_validate_entry_from_ui(client, workflow_case):
    entry = create_balanced_draft(workflow_case, number="S3-004")
    set_active_organization(client, workflow_case, workflow_case["accountant"])

    response = client.post(
        reverse("accounting:entry-validate", kwargs={"pk": entry.pk}),
    )

    assert response.status_code == 403
    entry.refresh_from_db()
    assert entry.status == JournalEntry.Status.DRAFT


def test_reviewer_can_validate_and_post_from_ui(client, workflow_case):
    entry = create_balanced_draft(workflow_case, number="S3-005")
    set_active_organization(client, workflow_case, workflow_case["reviewer"])

    response = client.post(
        reverse("accounting:entry-validate", kwargs={"pk": entry.pk}),
    )
    assert response.status_code == 302

    entry.refresh_from_db()
    assert entry.status == JournalEntry.Status.VALIDATED

    response = client.post(
        reverse("accounting:entry-post", kwargs={"pk": entry.pk}),
    )
    assert response.status_code == 302

    entry.refresh_from_db()
    assert entry.status == JournalEntry.Status.POSTED


def test_posted_entry_edit_route_is_not_available(client, workflow_case):
    entry = create_balanced_draft(workflow_case, number="S3-006")
    entry = validate_journal_entry(
        entry=entry,
        user=workflow_case["reviewer"],
    )
    entry = post_journal_entry(
        entry=entry,
        user=workflow_case["reviewer"],
    )

    set_active_organization(client, workflow_case, workflow_case["reviewer"])

    response = client.get(
        reverse("accounting:entry-update", kwargs={"pk": entry.pk}),
    )
    assert response.status_code == 404
