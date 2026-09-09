from __future__ import annotations

import csv
import hashlib
import io
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounting.models import Account, ChartOfAccounts, Journal, JournalEntry, JournalLine
from apps.audit.services import record_audit_event
from apps.organizations.models import AccountingPeriod

from .models import (
    FECImport,
    FECRawLine,
    ImportError,
    ImportMapping,
    JournalImportMapping,
)


REQUIRED_FEC_COLUMNS = [
    "JournalCode",
    "JournalLib",
    "EcritureNum",
    "EcritureDate",
    "CompteNum",
    "CompteLib",
    "CompAuxNum",
    "CompAuxLib",
    "PieceRef",
    "PieceDate",
    "EcritureLib",
    "Debit",
    "Credit",
    "EcritureLet",
    "DateLet",
    "ValidDate",
    "Montantdevise",
    "Idevise",
]

BLOCKING_SEVERITIES = {
    ImportError.Severity.BLOCKING,
}

FEC_DATE_FORMATS = (
    "%Y%m%d",
    "%Y-%m-%d",
    "%d/%m/%Y",
)

ADJUSTING_JOURNALS = {"JOD"}
OPENING_JOURNALS = {"JAN"}


@dataclass(slots=True)
class ParsedAmount:
    value: Decimal
    valid: bool


@dataclass(slots=True)
class ParsedDate:
    value: object | None
    valid: bool


def _clean(value) -> str:
    return str(value or "").strip()


def _normalized_code(value) -> str:
    return _clean(value).upper()


def sha256_uploaded_file(uploaded_file) -> str:
    hasher = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        hasher.update(chunk)
    uploaded_file.seek(0)
    return hasher.hexdigest()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def parse_decimal(value) -> ParsedAmount:
    raw = _clean(value)
    if not raw:
        return ParsedAmount(Decimal("0"), True)

    normalized = (
        raw.replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
    )
    try:
        return ParsedAmount(Decimal(normalized), True)
    except InvalidOperation:
        return ParsedAmount(Decimal("0"), False)


def parse_fec_date(value) -> ParsedDate:
    raw = _clean(value)
    if not raw:
        return ParsedDate(None, True)

    for date_format in FEC_DATE_FORMATS:
        try:
            return ParsedDate(datetime.strptime(raw, date_format).date(), True)
        except ValueError:
            continue
    return ParsedDate(None, False)


def decode_fec(content: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        try:
            return content.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValidationError("Encodage FEC non reconnu.")


def compute_row_hash(row: dict) -> str:
    canonical = "\x1f".join(_clean(row.get(column)) for column in REQUIRED_FEC_COLUMNS)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalized_entry_key(
    *,
    journal_code: str,
    entry_number: str,
    entry_date,
    piece_reference: str,
    fiscal_year_name: str,
) -> str:
    journal_code = _normalized_code(journal_code)
    entry_number = _clean(entry_number)
    piece_reference = _clean(piece_reference)
    date_token = entry_date.isoformat() if entry_date else "NO-DATE"

    if journal_code in OPENING_JOURNALS:
        return f"{journal_code}|OPENING|{fiscal_year_name}"

    if journal_code in {"JOD", "TAX", "PAIE"}:
        return f"{journal_code}|{entry_number}|{date_token}"

    return f"{journal_code}|{entry_number}|{date_token}|{piece_reference}"


def infer_account_classification(code: str, label: str = "") -> tuple[str, str]:
    code = _clean(code)
    label_upper = _clean(label).upper()

    if not code:
        return Account.AccountType.OTHER, Account.NormalBalance.DEBIT

    first = code[0]

    if first == "1":
        if code.startswith(("10", "11", "12", "13")):
            return Account.AccountType.EQUITY, Account.NormalBalance.CREDIT
        return Account.AccountType.LIABILITY, Account.NormalBalance.CREDIT

    if first in {"2", "3", "5"}:
        return Account.AccountType.ASSET, Account.NormalBalance.DEBIT

    if first == "4":
        if code.startswith(("40", "42", "43", "44")):
            return Account.AccountType.LIABILITY, Account.NormalBalance.CREDIT
        if code.startswith("41"):
            return Account.AccountType.ASSET, Account.NormalBalance.DEBIT
        if any(token in label_upper for token in ("CREANCE", "DEBITEUR", "AVANCE", "ACOMPTE")):
            return Account.AccountType.ASSET, Account.NormalBalance.DEBIT
        return Account.AccountType.LIABILITY, Account.NormalBalance.CREDIT

    if first == "6":
        return Account.AccountType.EXPENSE, Account.NormalBalance.DEBIT

    if first == "7":
        return Account.AccountType.REVENUE, Account.NormalBalance.CREDIT

    return Account.AccountType.OTHER, Account.NormalBalance.DEBIT


def infer_journal_type(code: str, label: str = "") -> str:
    code_upper = _normalized_code(code)
    label_upper = _clean(label).upper()
    token = f"{code_upper} {label_upper}"

    if code_upper in OPENING_JOURNALS or "NOUVEAUX" in token or "OUVERTURE" in token:
        return Journal.JournalType.OPENING
    if "ACH" in token or "PURCHASE" in token:
        return Journal.JournalType.PURCHASE
    if "VTE" in token or "VENTE" in token or "SALES" in token:
        return Journal.JournalType.SALES
    if "BNQ" in token or "BANQ" in token or "BANK" in token:
        return Journal.JournalType.BANK
    if "CAI" in token or "CAISSE" in token or "CASH" in token:
        return Journal.JournalType.CASH
    if "PAIE" in token or "PAYROLL" in token:
        return Journal.JournalType.PAYROLL
    if "TAX" in token or "FISC" in token:
        return Journal.JournalType.TAX
    return Journal.JournalType.GENERAL


def safe_reference_code(source_code: str, max_length: int) -> str:
    source_code = _clean(source_code)
    if len(source_code) <= max_length:
        return source_code

    digest = hashlib.sha1(source_code.encode("utf-8")).hexdigest()[:8]
    prefix_length = max_length - len(digest) - 1
    return f"{source_code[:prefix_length]}-{digest}"


def _active_default_chart(organization):
    chart = (
        ChartOfAccounts.objects.filter(
            organization=organization,
            is_active=True,
            is_default=True,
        )
        .order_by("created_at")
        .first()
    )
    if chart:
        return chart

    chart = (
        ChartOfAccounts.objects.filter(
            organization=organization,
            is_active=True,
        )
        .order_by("created_at")
        .first()
    )
    if chart:
        return chart

    return ChartOfAccounts.objects.create(
        organization=organization,
        code="ENTITY",
        name="Plan comptable de l'entité",
        is_default=True,
        is_active=True,
    )


def refresh_import_readiness(import_batch: FECImport) -> FECImport:
    if import_batch.status == FECImport.Status.IMPORTED:
        return import_batch

    blocking_count = import_batch.errors.filter(
        severity=ImportError.Severity.BLOCKING,
        is_resolved=False,
    ).count()
    account_unmapped = import_batch.mappings.filter(account__isnull=True).count()
    journal_unmapped = import_batch.journal_mappings.filter(journal__isnull=True).count()

    if blocking_count:
        status = FECImport.Status.PARSED
    elif account_unmapped or journal_unmapped:
        status = FECImport.Status.MAPPING
    else:
        status = FECImport.Status.READY

    summary = dict(import_batch.summary or {})
    summary.update(
        {
            "blocking_error_count": blocking_count,
            "unmapped_account_count": account_unmapped,
            "unmapped_journal_count": journal_unmapped,
        }
    )

    import_batch.status = status
    import_batch.summary = summary
    import_batch.save(update_fields=["status", "summary", "updated_at"])
    return import_batch


@transaction.atomic
def create_fec_import(
    *,
    organization,
    fiscal_year,
    uploaded_file,
    user,
    audit_metadata=None,
) -> FECImport:
    if fiscal_year.organization_id != organization.id:
        raise ValidationError("L'exercice sélectionné appartient à une autre organisation.")

    file_hash = sha256_uploaded_file(uploaded_file)

    existing = FECImport.objects.filter(
        organization=organization,
        fiscal_year=fiscal_year,
        sha256=file_hash,
    ).first()
    if existing:
        raise ValidationError(
            f"Ce FEC a déjà été chargé dans cet exercice "
            f"(import {existing.id}, statut {existing.get_status_display()})."
        )

    import_batch = FECImport(
        organization=organization,
        fiscal_year=fiscal_year,
        original_filename=Path(uploaded_file.name).name,
        original_file=uploaded_file,
        sha256=file_hash,
        status=FECImport.Status.UPLOADED,
        uploaded_by=user,
    )
    import_batch.full_clean()
    import_batch.save()

    record_audit_event(
        organization=organization,
        actor=user,
        action="FEC_UPLOAD",
        entity=import_batch,
        before=None,
        after={
            "filename": import_batch.original_filename,
            "sha256": file_hash,
            "fiscal_year": fiscal_year.name,
            "status": import_batch.status,
        },
        metadata=audit_metadata or {},
    )

    return import_batch


def _create_mapping_records(import_batch: FECImport, raw_lines: Iterable[FECRawLine]):
    organization = import_batch.organization

    account_counts = Counter()
    account_labels = {}
    journal_counts = Counter()
    journal_labels = {}

    for raw_line in raw_lines:
        if raw_line.account_number:
            account_counts[raw_line.account_number] += 1
            account_labels.setdefault(raw_line.account_number, raw_line.account_label)

        if raw_line.journal_code:
            journal_counts[raw_line.journal_code] += 1
            journal_labels.setdefault(raw_line.journal_code, raw_line.journal_label)

    exact_accounts = {}
    for account in (
        Account.objects.filter(
            organization=organization,
            code__in=list(account_counts.keys()),
            is_active=True,
        )
        .select_related("chart")
        .order_by("-chart__is_default", "code")
    ):
        exact_accounts.setdefault(account.code, account)

    exact_journals = {}
    for journal in Journal.objects.filter(
        organization=organization,
        is_active=True,
    ):
        exact_journals.setdefault(journal.code.upper(), journal)

    account_mapping_objects = []
    for code in sorted(account_counts):
        account = exact_accounts.get(code)
        account_mapping_objects.append(
            ImportMapping(
                import_batch=import_batch,
                source_account_number=code,
                source_account_label=account_labels.get(code, ""),
                occurrence_count=account_counts[code],
                account=account,
                created_automatically=bool(account),
            )
        )

    journal_mapping_objects = []
    for code in sorted(journal_counts):
        journal = exact_journals.get(code.upper())
        journal_mapping_objects.append(
            JournalImportMapping(
                import_batch=import_batch,
                source_journal_code=code,
                source_journal_label=journal_labels.get(code, ""),
                occurrence_count=journal_counts[code],
                journal=journal,
                created_automatically=bool(journal),
            )
        )

    ImportMapping.objects.bulk_create(account_mapping_objects)
    JournalImportMapping.objects.bulk_create(journal_mapping_objects)


@transaction.atomic
def parse_fec_import(
    *,
    import_batch: FECImport,
    user,
    audit_metadata=None,
) -> FECImport:
    import_batch = FECImport.objects.select_for_update().select_related(
        "organization",
        "fiscal_year",
    ).get(pk=import_batch.pk)

    if import_batch.status == FECImport.Status.IMPORTED:
        raise ValidationError("Un FEC déjà importé ne peut pas être reparsé.")

    import_batch.raw_lines.all().delete()
    import_batch.errors.all().delete()
    import_batch.mappings.all().delete()
    import_batch.journal_mappings.all().delete()

    import_batch.original_file.open("rb")
    try:
        content = import_batch.original_file.read()
    finally:
        import_batch.original_file.close()

    text, encoding = decode_fec(content)
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")

    fieldnames = reader.fieldnames or []
    missing_columns = [
        column for column in REQUIRED_FEC_COLUMNS if column not in fieldnames
    ]
    if missing_columns:
        ImportError.objects.create(
            import_batch=import_batch,
            code="FEC_REQUIRED_COLUMNS",
            severity=ImportError.Severity.BLOCKING,
            message=f"Colonnes FEC manquantes : {', '.join(missing_columns)}",
            details={"missing_columns": missing_columns},
        )
        import_batch.encoding = encoding
        import_batch.status = FECImport.Status.PARSED
        import_batch.parsed_at = timezone.now()
        import_batch.summary = {
            "line_count": 0,
            "blocking_error_count": 1,
            "missing_columns": missing_columns,
        }
        import_batch.save(
            update_fields=[
                "encoding",
                "status",
                "parsed_at",
                "summary",
                "updated_at",
            ]
        )
        return import_batch

    raw_objects = []
    pending_errors = []
    seen_hashes = {}
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    for line_number, row in enumerate(reader, start=2):
        row = {key: _clean(value) for key, value in row.items()}
        debit = parse_decimal(row.get("Debit"))
        credit = parse_decimal(row.get("Credit"))
        currency_amount = parse_decimal(row.get("Montantdevise"))

        entry_date = parse_fec_date(row.get("EcritureDate"))
        piece_date = parse_fec_date(row.get("PieceDate"))
        letter_date = parse_fec_date(row.get("DateLet"))
        validation_date = parse_fec_date(row.get("ValidDate"))

        journal_code = _normalized_code(row.get("JournalCode"))
        entry_number = _clean(row.get("EcritureNum"))
        account_number = _clean(row.get("CompteNum"))
        account_label = _clean(row.get("CompteLib"))
        piece_reference = _clean(row.get("PieceRef"))

        row_hash = compute_row_hash(row)

        raw_line = FECRawLine(
            import_batch=import_batch,
            line_number=line_number,
            journal_code=journal_code,
            journal_label=_clean(row.get("JournalLib")),
            entry_number=entry_number,
            entry_date=entry_date.value,
            account_number=account_number,
            account_label=account_label,
            auxiliary_number=_clean(row.get("CompAuxNum")),
            auxiliary_label=_clean(row.get("CompAuxLib")),
            piece_reference=piece_reference,
            piece_date=piece_date.value,
            entry_label=_clean(row.get("EcritureLib")),
            debit=debit.value,
            credit=credit.value,
            letter=_clean(row.get("EcritureLet")),
            letter_date=letter_date.value,
            validation_date=validation_date.value,
            currency_amount=currency_amount.value,
            currency_code=_clean(row.get("Idevise")),
            row_hash=row_hash,
            normalized_entry_key=normalized_entry_key(
                journal_code=journal_code,
                entry_number=entry_number,
                entry_date=entry_date.value,
                piece_reference=piece_reference,
                fiscal_year_name=import_batch.fiscal_year.name,
            ),
            is_valid=True,
            raw_data=row,
        )

        line_errors = []

        if not journal_code:
            line_errors.append(
                (
                    "FEC_MISSING_JOURNAL_CODE",
                    ImportError.Severity.BLOCKING,
                    "JournalCode est obligatoire.",
                )
            )
        if not entry_number:
            line_errors.append(
                (
                    "FEC_MISSING_ENTRY_NUMBER",
                    ImportError.Severity.BLOCKING,
                    "EcritureNum est obligatoire.",
                )
            )
        if not account_number:
            line_errors.append(
                (
                    "FEC_MISSING_ACCOUNT_NUMBER",
                    ImportError.Severity.BLOCKING,
                    "CompteNum est obligatoire.",
                )
            )
        if not account_label:
            line_errors.append(
                (
                    "FEC_MISSING_ACCOUNT_LABEL",
                    ImportError.Severity.BLOCKING,
                    "CompteLib est obligatoire.",
                )
            )
        if not entry_date.valid or entry_date.value is None:
            line_errors.append(
                (
                    "FEC_INVALID_ENTRY_DATE",
                    ImportError.Severity.BLOCKING,
                    f"EcritureDate invalide : {row.get('EcritureDate', '')}",
                )
            )
        elif not (
            import_batch.fiscal_year.start_date
            <= entry_date.value
            <= import_batch.fiscal_year.end_date
        ):
            line_errors.append(
                (
                    "FEC_DATE_OUTSIDE_FISCAL_YEAR",
                    ImportError.Severity.BLOCKING,
                    f"Date {entry_date.value} hors exercice {import_batch.fiscal_year.name}.",
                )
            )

        if not debit.valid:
            line_errors.append(
                (
                    "FEC_INVALID_DEBIT",
                    ImportError.Severity.BLOCKING,
                    f"Débit invalide : {row.get('Debit', '')}",
                )
            )
        if not credit.valid:
            line_errors.append(
                (
                    "FEC_INVALID_CREDIT",
                    ImportError.Severity.BLOCKING,
                    f"Crédit invalide : {row.get('Credit', '')}",
                )
            )
        if not currency_amount.valid:
            line_errors.append(
                (
                    "FEC_INVALID_CURRENCY_AMOUNT",
                    ImportError.Severity.WARNING,
                    f"Montantdevise invalide : {row.get('Montantdevise', '')}",
                )
            )

        if debit.value > 0 and credit.value > 0:
            line_errors.append(
                (
                    "FEC_DEBIT_AND_CREDIT",
                    ImportError.Severity.BLOCKING,
                    "Une ligne ne peut pas porter simultanément un débit et un crédit.",
                )
            )
        if debit.value == 0 and credit.value == 0:
            line_errors.append(
                (
                    "FEC_ZERO_LINE",
                    ImportError.Severity.BLOCKING,
                    "Une ligne FEC doit porter un montant au débit ou au crédit.",
                )
            )
        if debit.value < 0 or credit.value < 0:
            line_errors.append(
                (
                    "FEC_NEGATIVE_AMOUNT",
                    ImportError.Severity.BLOCKING,
                    "Les montants Débit / Crédit doivent être positifs.",
                )
            )

        if row_hash in seen_hashes:
            line_errors.append(
                (
                    "FEC_DUPLICATE_LINE",
                    ImportError.Severity.WARNING,
                    f"Ligne potentiellement dupliquée de la ligne {seen_hashes[row_hash]}.",
                )
            )
        else:
            seen_hashes[row_hash] = line_number

        if any(severity in BLOCKING_SEVERITIES for _, severity, _ in line_errors):
            raw_line.is_valid = False

        raw_objects.append(raw_line)
        total_debit += debit.value
        total_credit += credit.value

        for code, severity, message in line_errors:
            pending_errors.append((raw_line, code, severity, message, {}))

    FECRawLine.objects.bulk_create(raw_objects, batch_size=1000)

    error_objects = [
        ImportError(
            import_batch=import_batch,
            raw_line=raw_line,
            code=code,
            severity=severity,
            message=message,
            details=details,
        )
        for raw_line, code, severity, message, details in pending_errors
    ]

    groups = defaultdict(list)
    for raw_line in raw_objects:
        if raw_line.is_valid:
            groups[raw_line.normalized_entry_key].append(raw_line)

    for group_key, lines in groups.items():
        group_debit = sum((line.debit for line in lines), Decimal("0"))
        group_credit = sum((line.credit for line in lines), Decimal("0"))
        if group_debit != group_credit:
            error_objects.append(
                ImportError(
                    import_batch=import_batch,
                    code="FEC_UNBALANCED_ENTRY",
                    severity=ImportError.Severity.BLOCKING,
                    message=(
                        f"Écriture normalisée non équilibrée : {group_key} "
                        f"(Débit={group_debit}, Crédit={group_credit})."
                    ),
                    details={
                        "entry_key": group_key,
                        "debit": str(group_debit),
                        "credit": str(group_credit),
                        "gap": str(group_debit - group_credit),
                        "source_lines": [line.line_number for line in lines],
                    },
                )
            )

    if total_debit != total_credit:
        error_objects.append(
            ImportError(
                import_batch=import_batch,
                code="FEC_GLOBAL_UNBALANCED",
                severity=ImportError.Severity.BLOCKING,
                message=(
                    f"Le FEC global n'est pas équilibré : "
                    f"Débit={total_debit}, Crédit={total_credit}."
                ),
                details={
                    "debit": str(total_debit),
                    "credit": str(total_credit),
                    "gap": str(total_debit - total_credit),
                },
            )
        )

    ImportError.objects.bulk_create(error_objects, batch_size=1000)
    _create_mapping_records(import_batch, raw_objects)

    duplicate_count = sum(
        1 for _, code, _, _, _ in pending_errors if code == "FEC_DUPLICATE_LINE"
    )
    blocking_count = sum(
        1 for error in error_objects if error.severity == ImportError.Severity.BLOCKING
    )
    warning_count = sum(
        1 for error in error_objects if error.severity == ImportError.Severity.WARNING
    )

    summary = {
        "line_count": len(raw_objects),
        "entry_group_count": len(groups),
        "account_count": len({line.account_number for line in raw_objects if line.account_number}),
        "journal_count": len({line.journal_code for line in raw_objects if line.journal_code}),
        "total_debit": str(total_debit),
        "total_credit": str(total_credit),
        "balance_gap": str(total_debit - total_credit),
        "duplicate_count": duplicate_count,
        "blocking_error_count": blocking_count,
        "warning_count": warning_count,
    }

    import_batch.encoding = encoding
    import_batch.status = FECImport.Status.PARSED
    import_batch.parsed_at = timezone.now()
    import_batch.summary = summary
    import_batch.save(
        update_fields=[
            "encoding",
            "status",
            "parsed_at",
            "summary",
            "updated_at",
        ]
    )

    refresh_import_readiness(import_batch)
    import_batch.refresh_from_db()

    record_audit_event(
        organization=import_batch.organization,
        actor=user,
        action="FEC_PARSE",
        entity=import_batch,
        before={"status": FECImport.Status.UPLOADED},
        after={
            "status": import_batch.status,
            "summary": import_batch.summary,
            "encoding": import_batch.encoding,
        },
        metadata=audit_metadata or {},
    )

    return import_batch


@transaction.atomic
def update_account_mapping(
    *,
    mapping: ImportMapping,
    account,
    user,
    audit_metadata=None,
):
    mapping = ImportMapping.objects.select_for_update().select_related(
        "import_batch",
        "import_batch__organization",
    ).get(pk=mapping.pk)

    if mapping.import_batch.status == FECImport.Status.IMPORTED:
        raise ValidationError("Les mappings d'un FEC importé sont immuables.")

    if account and account.organization_id != mapping.import_batch.organization_id:
        raise ValidationError("Le compte cible appartient à une autre organisation.")

    before = {
        "source_account_number": mapping.source_account_number,
        "account_id": str(mapping.account_id) if mapping.account_id else None,
    }

    mapping.account = account
    mapping.created_automatically = False
    mapping.save(update_fields=["account", "created_automatically", "updated_at"])

    refresh_import_readiness(mapping.import_batch)

    record_audit_event(
        organization=mapping.import_batch.organization,
        actor=user,
        action="FEC_ACCOUNT_MAPPING_UPDATE",
        entity=mapping,
        before=before,
        after={
            "source_account_number": mapping.source_account_number,
            "account_id": str(account.id) if account else None,
        },
        metadata=audit_metadata or {},
    )
    return mapping


@transaction.atomic
def update_journal_mapping(
    *,
    mapping: JournalImportMapping,
    journal,
    user,
    audit_metadata=None,
):
    mapping = JournalImportMapping.objects.select_for_update().select_related(
        "import_batch",
        "import_batch__organization",
    ).get(pk=mapping.pk)

    if mapping.import_batch.status == FECImport.Status.IMPORTED:
        raise ValidationError("Les mappings d'un FEC importé sont immuables.")

    if journal and journal.organization_id != mapping.import_batch.organization_id:
        raise ValidationError("Le journal cible appartient à une autre organisation.")

    before = {
        "source_journal_code": mapping.source_journal_code,
        "journal_id": str(mapping.journal_id) if mapping.journal_id else None,
    }

    mapping.journal = journal
    mapping.created_automatically = False
    mapping.save(update_fields=["journal", "created_automatically", "updated_at"])

    refresh_import_readiness(mapping.import_batch)

    record_audit_event(
        organization=mapping.import_batch.organization,
        actor=user,
        action="FEC_JOURNAL_MAPPING_UPDATE",
        entity=mapping,
        before=before,
        after={
            "source_journal_code": mapping.source_journal_code,
            "journal_id": str(journal.id) if journal else None,
        },
        metadata=audit_metadata or {},
    )
    return mapping


@transaction.atomic
def auto_create_unmapped_references(
    *,
    import_batch: FECImport,
    user,
    audit_metadata=None,
) -> FECImport:
    import_batch = FECImport.objects.select_for_update().select_related(
        "organization"
    ).get(pk=import_batch.pk)

    if import_batch.status == FECImport.Status.IMPORTED:
        raise ValidationError("Un FEC importé ne peut plus être remappé.")

    organization = import_batch.organization
    chart = _active_default_chart(organization)

    created_accounts = 0
    created_journals = 0

    for mapping in import_batch.mappings.filter(account__isnull=True):
        account_type, normal_balance = infer_account_classification(
            mapping.source_account_number,
            mapping.source_account_label,
        )
        target_account_code = safe_reference_code(
            mapping.source_account_number,
            Account._meta.get_field("code").max_length,
        )
        account, created = Account.objects.get_or_create(
            organization=organization,
            chart=chart,
            code=target_account_code,
            defaults={
                "name": mapping.source_account_label or mapping.source_account_number,
                "account_type": account_type,
                "normal_balance": normal_balance,
                "is_active": True,
            },
        )
        mapping.account = account
        mapping.created_automatically = True
        mapping.save(update_fields=["account", "created_automatically", "updated_at"])
        if created:
            created_accounts += 1

    for mapping in import_batch.journal_mappings.filter(journal__isnull=True):
        target_journal_code = safe_reference_code(
            mapping.source_journal_code,
            Journal._meta.get_field("code").max_length,
        )
        journal, created = Journal.objects.get_or_create(
            organization=organization,
            code=target_journal_code,
            defaults={
                "name": mapping.source_journal_label or mapping.source_journal_code,
                "journal_type": infer_journal_type(
                    mapping.source_journal_code,
                    mapping.source_journal_label,
                ),
                "is_active": True,
            },
        )
        mapping.journal = journal
        mapping.created_automatically = True
        mapping.save(update_fields=["journal", "created_automatically", "updated_at"])
        if created:
            created_journals += 1

    refresh_import_readiness(import_batch)
    import_batch.refresh_from_db()

    record_audit_event(
        organization=organization,
        actor=user,
        action="FEC_AUTO_MAPPING",
        entity=import_batch,
        before=None,
        after={
            "status": import_batch.status,
            "created_accounts": created_accounts,
            "created_journals": created_journals,
        },
        metadata=audit_metadata or {},
    )

    return import_batch


def _resolve_period(periods, entry_date):
    for period in periods:
        if period.start_date <= entry_date <= period.end_date:
            return period
    return None


def _entry_type_for_journal(source_journal_code: str):
    source_journal_code = _normalized_code(source_journal_code)
    if source_journal_code in OPENING_JOURNALS:
        return JournalEntry.EntryType.OPENING
    if source_journal_code in ADJUSTING_JOURNALS:
        return JournalEntry.EntryType.ADJUSTING
    return JournalEntry.EntryType.NORMAL


def _safe_entry_number(base: str, collision_number: int) -> str:
    base = _clean(base) or "FEC"
    if collision_number <= 1:
        return base[:150]

    suffix = f"-{collision_number}"
    return f"{base[:150-len(suffix)]}{suffix}"


@transaction.atomic
def _execute_fec_import_atomic(
    *,
    import_batch: FECImport,
    user,
    audit_metadata=None,
) -> FECImport:
    import_batch = (
        FECImport.objects.select_for_update()
        .select_related("organization", "fiscal_year")
        .get(pk=import_batch.pk)
    )

    refresh_import_readiness(import_batch)
    import_batch.refresh_from_db()

    if not import_batch.can_import:
        raise ValidationError(
            "Le FEC n'est pas prêt : corrigez les erreurs bloquantes et complétez les mappings."
        )

    existing_entries = JournalEntry.objects.filter(
        organization=import_batch.organization,
        source="FEC",
        source_reference__startswith=f"{import_batch.id}:",
    )
    if existing_entries.exists():
        raise ValidationError(
            "Des écritures existent déjà pour cet import FEC. "
            "L'import transactionnel est volontairement idempotent."
        )

    account_mapping = {
        mapping.source_account_number: mapping.account
        for mapping in import_batch.mappings.select_related("account")
    }
    journal_mapping = {
        mapping.source_journal_code: mapping.journal
        for mapping in import_batch.journal_mappings.select_related("journal")
    }

    periods = list(
        AccountingPeriod.objects.filter(
            fiscal_year=import_batch.fiscal_year,
        ).order_by("start_date")
    )
    if not periods:
        raise ValidationError(
            "Aucune période comptable n'existe pour cet exercice."
        )

    raw_lines = list(
        import_batch.raw_lines.filter(is_valid=True).order_by(
            "normalized_entry_key",
            "line_number",
        )
    )

    groups = defaultdict(list)
    for raw_line in raw_lines:
        groups[raw_line.normalized_entry_key].append(raw_line)

    now = timezone.now()
    entries = []
    entry_source_pairs = []
    collisions = defaultdict(int)

    for group_key in sorted(groups):
        source_lines = groups[group_key]
        first = source_lines[0]

        if not first.entry_date:
            raise ValidationError(
                f"Date d'écriture absente pour le groupe {group_key}."
            )

        journal = journal_mapping.get(first.journal_code)
        if journal is None:
            raise ValidationError(
                f"Journal non mappé : {first.journal_code}."
            )

        period = _resolve_period(periods, first.entry_date)
        if period is None:
            raise ValidationError(
                f"Aucune période comptable ne couvre la date {first.entry_date}."
            )

        if period.status != AccountingPeriod.Status.OPEN:
            raise ValidationError(
                f"La période {period.name} n'est pas ouverte."
            )

        total_debit = sum((line.debit for line in source_lines), Decimal("0"))
        total_credit = sum((line.credit for line in source_lines), Decimal("0"))
        if total_debit != total_credit:
            raise ValidationError(
                f"Groupe {group_key} non équilibré : "
                f"Débit={total_debit}, Crédit={total_credit}."
            )

        if first.journal_code in OPENING_JOURNALS:
            base_number = f"OPENING-{import_batch.fiscal_year.name}"
        else:
            base_number = first.entry_number or f"FEC-{first.line_number}"

        collision_key = (
            journal.id,
            base_number,
            first.entry_date,
        )
        collisions[collision_key] += 1
        entry_number = _safe_entry_number(
            base_number,
            collisions[collision_key],
        )

        entry = JournalEntry(
            organization=import_batch.organization,
            journal=journal,
            period=period,
            entry_number=entry_number,
            posting_date=first.entry_date,
            description=first.entry_label or first.journal_label or entry_number,
            reference=first.piece_reference,
            entry_type=_entry_type_for_journal(first.journal_code),
            status=JournalEntry.Status.POSTED,
            source="FEC",
            source_reference=f"{import_batch.id}:{group_key}",
            created_by=user,
            validated_by=user,
            validated_at=now,
            posted_by=user,
            posted_at=now,
        )
        entry.full_clean(validate_unique=False)
        entries.append(entry)
        entry_source_pairs.append((entry, source_lines))

    # JournalEntry IDs are UUIDs generated client-side, but the rows are persisted first
    # so ForeignKey validation on JournalLine can resolve the parent entry.
    JournalEntry.objects.bulk_create(entries, batch_size=500)

    lines_to_create = []
    for entry, source_lines in entry_source_pairs:
        for line_number, source_line in enumerate(source_lines, start=1):
            account = account_mapping.get(source_line.account_number)
            if account is None:
                raise ValidationError(
                    f"Compte non mappé : {source_line.account_number}."
                )

            line = JournalLine(
                entry=entry,
                line_number=line_number,
                account=account,
                description=source_line.entry_label,
                debit=source_line.debit,
                credit=source_line.credit,
                source_line_number=source_line.line_number,
                metadata={
                    "fec_import_id": str(import_batch.id),
                    "fec_raw_line_id": str(source_line.id),
                    "source_account_number": source_line.account_number,
                    "source_journal_code": source_line.journal_code,
                    "piece_reference": source_line.piece_reference,
                    "auxiliary_number": source_line.auxiliary_number,
                    "auxiliary_label": source_line.auxiliary_label,
                },
            )
            line.full_clean(validate_unique=False)
            lines_to_create.append(line)

    JournalLine.objects.bulk_create(lines_to_create, batch_size=2000)

    import_batch.status = FECImport.Status.IMPORTED
    import_batch.imported_by = user
    import_batch.imported_at = now

    summary = dict(import_batch.summary or {})
    summary.update(
        {
            "imported_entry_count": len(entries),
            "imported_line_count": len(lines_to_create),
            "import_completed_at": now.isoformat(),
        }
    )
    import_batch.summary = summary
    import_batch.save(
        update_fields=[
            "status",
            "imported_by",
            "imported_at",
            "summary",
            "updated_at",
        ]
    )

    record_audit_event(
        organization=import_batch.organization,
        actor=user,
        action="FEC_IMPORT",
        entity=import_batch,
        before={"status": FECImport.Status.READY},
        after={
            "status": FECImport.Status.IMPORTED,
            "imported_entry_count": len(entries),
            "imported_line_count": len(lines_to_create),
        },
        metadata=audit_metadata or {},
    )

    return import_batch


def execute_fec_import(
    *,
    import_batch: FECImport,
    user,
    audit_metadata=None,
) -> FECImport:
    if import_batch.status == FECImport.Status.IMPORTED:
        raise ValidationError("Ce FEC a déjà été importé.")

    refresh_import_readiness(import_batch)
    import_batch.refresh_from_db()

    if not import_batch.can_import:
        raise ValidationError(
            "Le FEC n'est pas prêt : corrigez les contrôles bloquants "
            "et complétez les mappings."
        )

    import_batch.status = FECImport.Status.IMPORTING
    import_batch.save(update_fields=["status", "updated_at"])

    try:
        result = _execute_fec_import_atomic(
            import_batch=import_batch,
            user=user,
            audit_metadata=audit_metadata,
        )
    except Exception:
        FECImport.objects.filter(pk=import_batch.pk).update(
            status=FECImport.Status.FAILED,
            updated_at=timezone.now(),
        )
        raise

    return result
