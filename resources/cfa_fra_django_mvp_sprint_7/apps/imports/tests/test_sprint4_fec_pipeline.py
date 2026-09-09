from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounting.models import JournalEntry
from apps.accounting.services import bootstrap_accounting_core
from apps.audit.models import AuditEvent
from apps.imports.models import FECImport, ImportError
from apps.imports.services import (
    auto_create_unmapped_references,
    create_fec_import,
    execute_fec_import,
    parse_fec_import,
)
from apps.organizations.models import FiscalYear, Organization, OrganizationMembership
from apps.organizations.services import generate_monthly_periods

pytestmark = pytest.mark.django_db


HEADER = (
    "JournalCode\tJournalLib\tEcritureNum\tEcritureDate\tCompteNum\tCompteLib\t"
    "CompAuxNum\tCompAuxLib\tPieceRef\tPieceDate\tEcritureLib\tDebit\tCredit\t"
    "EcritureLet\tDateLet\tValidDate\tMontantdevise\tIdevise"
)


def build_fec(*, balanced=True):
    closing_credit = "100,00" if balanced else "90,00"
    rows = [
        (
            "JAN\tÀ-nouveaux\t0001\t20250101\t57110000\tCaisse générale\t\t\tOPEN\t"
            "20250101\tSolde d'ouverture\t1000,00\t0\t\t\t20250101\t0\tXAF"
        ),
        (
            "JAN\tÀ-nouveaux\t0001\t20250101\t10110000\tCapital social\t\t\tOPEN\t"
            "20250101\tSolde d'ouverture\t0\t1000,00\t\t\t20250101\t0\tXAF"
        ),
        (
            "JOD\tOpérations diverses\t0002\t20250115\t67110000\tCharge financière\t\t\tOD-1\t"
            "20250115\tAjustement\t100,00\t0\t\t\t20250115\t0\tXAF"
        ),
        (
            f"JOD\tOpérations diverses\t0002\t20250115\t52110000\tBanque principale\t\t\tOD-1\t"
            f"20250115\tAjustement\t0\t{closing_credit}\t\t\t20250115\t0\tXAF"
        ),
    ]
    return (HEADER + "\n" + "\n".join(rows) + "\n").encode("cp1252")


@pytest.fixture
def fec_case():
    User = get_user_model()
    reviewer = User.objects.create_user(
        username="fec-reviewer",
        email="fec-reviewer@example.com",
        password="secret1234",
    )
    accountant = User.objects.create_user(
        username="fec-accountant",
        email="fec-accountant@example.com",
        password="secret1234",
    )

    organization = Organization.objects.create(
        name="FEC Sprint 4",
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
    generate_monthly_periods(fiscal_year=fiscal_year)
    bootstrap_accounting_core(organization=organization)

    return {
        "reviewer": reviewer,
        "accountant": accountant,
        "organization": organization,
        "fiscal_year": fiscal_year,
    }


def upload_file(content=None, name="FEC_2025.txt"):
    return SimpleUploadedFile(
        name,
        content or build_fec(),
        content_type="text/plain",
    )


def create_and_parse(case, *, content=None):
    batch = create_fec_import(
        organization=case["organization"],
        fiscal_year=case["fiscal_year"],
        uploaded_file=upload_file(content),
        user=case["accountant"],
    )
    return parse_fec_import(
        import_batch=batch,
        user=case["accountant"],
    )


def set_active_organization(client, case, user):
    client.force_login(user)
    session = client.session
    session["active_organization_id"] = str(case["organization"].pk)
    session.save()


def test_upload_and_parse_preserves_raw_lines(fec_case):
    batch = create_and_parse(fec_case)

    assert batch.encoding == "cp1252"
    assert batch.raw_lines.count() == 4
    assert batch.summary["line_count"] == 4
    assert batch.summary["entry_group_count"] == 2
    assert batch.summary["total_debit"] == "1100.00"
    assert batch.summary["total_credit"] == "1100.00"
    assert batch.summary["balance_gap"] == "0.00"
    assert batch.status == FECImport.Status.MAPPING

    first = batch.raw_lines.get(line_number=2)
    assert first.raw_data["CompteLib"] == "Caisse générale"
    assert first.row_hash
    assert first.normalized_entry_key.startswith("JAN|OPENING|2025")


def test_exact_journal_mappings_are_detected(fec_case):
    batch = create_and_parse(fec_case)

    jan = batch.journal_mappings.get(source_journal_code="JAN")
    jod = batch.journal_mappings.get(source_journal_code="JOD")

    assert jan.journal is not None
    assert jod.journal is not None
    assert jan.created_automatically
    assert jod.created_automatically


def test_auto_mapping_creates_missing_accounts_and_makes_import_ready(fec_case):
    batch = create_and_parse(fec_case)

    batch = auto_create_unmapped_references(
        import_batch=batch,
        user=fec_case["reviewer"],
    )

    assert batch.status == FECImport.Status.READY
    assert batch.unresolved_account_mapping_count == 0
    assert batch.unresolved_journal_mapping_count == 0

    codes = set(
        fec_case["organization"].accounts.values_list("code", flat=True)
    )
    assert {"57110000", "10110000", "67110000", "52110000"} <= codes


def test_execute_fec_import_creates_posted_entries_and_lines(fec_case):
    batch = create_and_parse(fec_case)
    batch = auto_create_unmapped_references(
        import_batch=batch,
        user=fec_case["reviewer"],
    )

    batch = execute_fec_import(
        import_batch=batch,
        user=fec_case["reviewer"],
    )

    assert batch.status == FECImport.Status.IMPORTED
    assert batch.imported_by == fec_case["reviewer"]
    assert batch.summary["imported_entry_count"] == 2
    assert batch.summary["imported_line_count"] == 4

    entries = JournalEntry.objects.filter(
        organization=fec_case["organization"],
        source="FEC",
    ).order_by("posting_date", "entry_number")

    assert entries.count() == 2
    assert entries.filter(status=JournalEntry.Status.POSTED).count() == 2
    assert sum(entry.lines.count() for entry in entries) == 4

    source_lines = set(
        entries.values_list("lines__source_line_number", flat=True)
    )
    assert {2, 3, 4, 5} <= source_lines

    opening = entries.get(entry_type=JournalEntry.EntryType.OPENING)
    assert opening.entry_number == "OPENING-2025"
    assert opening.total_debit == opening.total_credit

    assert AuditEvent.objects.filter(
        organization=fec_case["organization"],
        action="FEC_IMPORT",
        entity_id=str(batch.id),
    ).exists()


def test_duplicate_file_is_rejected_by_sha256(fec_case):
    batch = create_and_parse(fec_case)
    assert batch.pk

    with pytest.raises(ValidationError):
        create_fec_import(
            organization=fec_case["organization"],
            fiscal_year=fec_case["fiscal_year"],
            uploaded_file=upload_file(),
            user=fec_case["accountant"],
        )


def test_unbalanced_fec_is_blocked(fec_case):
    batch = create_and_parse(
        fec_case,
        content=build_fec(balanced=False),
    )

    assert batch.status == FECImport.Status.PARSED
    assert batch.blocking_error_count > 0
    assert batch.errors.filter(
        code="FEC_GLOBAL_UNBALANCED",
        severity=ImportError.Severity.BLOCKING,
    ).exists()

    with pytest.raises(ValidationError):
        execute_fec_import(
            import_batch=batch,
            user=fec_case["reviewer"],
        )

    batch.refresh_from_db()
    assert batch.status == FECImport.Status.PARSED


def test_ui_upload_parses_immediately(client, fec_case):
    set_active_organization(
        client,
        fec_case,
        fec_case["accountant"],
    )

    response = client.post(
        reverse("imports:fec-upload"),
        {
            "fiscal_year": str(fec_case["fiscal_year"].pk),
            "file": upload_file(name="FEC_UI.txt"),
        },
    )

    assert response.status_code == 302
    batch = FECImport.objects.get(original_filename="FEC_UI.txt")
    assert batch.raw_lines.count() == 4
    assert batch.status == FECImport.Status.MAPPING


def test_accountant_cannot_execute_final_import(client, fec_case):
    batch = create_and_parse(fec_case)
    batch = auto_create_unmapped_references(
        import_batch=batch,
        user=fec_case["reviewer"],
    )

    set_active_organization(
        client,
        fec_case,
        fec_case["accountant"],
    )

    response = client.post(
        reverse("imports:fec-execute", kwargs={"pk": batch.pk}),
    )

    assert response.status_code == 403
    batch.refresh_from_db()
    assert batch.status == FECImport.Status.READY


def test_reviewer_can_execute_final_import_from_ui(client, fec_case):
    batch = create_and_parse(fec_case)
    batch = auto_create_unmapped_references(
        import_batch=batch,
        user=fec_case["reviewer"],
    )

    set_active_organization(
        client,
        fec_case,
        fec_case["reviewer"],
    )

    response = client.post(
        reverse("imports:fec-execute", kwargs={"pk": batch.pk}),
    )

    assert response.status_code == 302
    batch.refresh_from_db()
    assert batch.status == FECImport.Status.IMPORTED
