from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_event, serialize_accounting_entry

from .models import ChartOfAccounts, Journal, JournalEntry, JournalLine


DEFAULT_JOURNALS = [
    ("JAN", "À-nouveaux", Journal.JournalType.OPENING),
    ("JACH", "Journal des achats", Journal.JournalType.PURCHASE),
    ("JVTE", "Journal des ventes", Journal.JournalType.SALES),
    ("BNQ", "Journal de banque", Journal.JournalType.BANK),
    ("CAI", "Journal de caisse", Journal.JournalType.CASH),
    ("PAIE", "Journal de paie", Journal.JournalType.PAYROLL),
    ("TAX", "Journal fiscal", Journal.JournalType.TAX),
    ("JOD", "Opérations diverses", Journal.JournalType.GENERAL),
]


@transaction.atomic
def bootstrap_accounting_core(*, organization):
    chart, _ = ChartOfAccounts.objects.get_or_create(
        organization=organization,
        code="ENTITY",
        defaults={
            "name": "Plan comptable de l'entité",
            "is_default": True,
            "is_active": True,
        },
    )

    journals = []
    for code, name, journal_type in DEFAULT_JOURNALS:
        journal, _ = Journal.objects.get_or_create(
            organization=organization,
            code=code,
            defaults={
                "name": name,
                "journal_type": journal_type,
                "is_active": True,
            },
        )
        journals.append(journal)

    return chart, journals


def validate_entry(entry: JournalEntry) -> None:
    if entry.status in {JournalEntry.Status.POSTED, JournalEntry.Status.REVERSED}:
        raise ValidationError("Une écriture postée ou extournée est immuable.")

    if entry.period.status == "CLOSED":
        raise ValidationError("La période comptable est clôturée.")

    entry.full_clean()

    lines = list(entry.lines.select_related("account").all())
    if len(lines) < 2:
        raise ValidationError("Une écriture doit comporter au moins deux lignes.")

    total_debit = sum((line.debit for line in lines), Decimal("0"))
    total_credit = sum((line.credit for line in lines), Decimal("0"))

    if total_debit != total_credit:
        raise ValidationError(
            f"Écriture non équilibrée : débit={total_debit} crédit={total_credit}."
        )

    if total_debit == Decimal("0"):
        raise ValidationError("Une écriture ne peut pas être nulle.")

    for line in lines:
        line.full_clean()


def _lock_entry(entry: JournalEntry) -> JournalEntry:
    return (
        JournalEntry.objects.select_for_update()
        .select_related("organization", "journal", "period", "period__fiscal_year")
        .prefetch_related(
            "lines__account",
            "lines__counterparty",
            "lines__cost_center",
        )
        .get(pk=entry.pk)
    )


@transaction.atomic
def create_draft_entry(
    *,
    organization,
    user,
    journal,
    period,
    entry_number,
    posting_date,
    description,
    reference="",
    entry_type=JournalEntry.EntryType.NORMAL,
    lines,
    audit_metadata=None,
):
    entry = JournalEntry(
        organization=organization,
        journal=journal,
        period=period,
        entry_number=entry_number,
        posting_date=posting_date,
        description=description,
        reference=reference or "",
        entry_type=entry_type,
        status=JournalEntry.Status.DRAFT,
        source="MANUAL",
        created_by=user,
    )
    entry.full_clean()
    entry.save()

    line_instances = []
    for position, line_data in enumerate(lines, start=1):
        line = JournalLine(
            entry=entry,
            line_number=position,
            account=line_data["account"],
            description=line_data.get("description", ""),
            debit=line_data.get("debit") or Decimal("0"),
            credit=line_data.get("credit") or Decimal("0"),
            counterparty=line_data.get("counterparty"),
            cost_center=line_data.get("cost_center"),
            cash_flow_tag=line_data.get("cash_flow_tag", ""),
        )
        line.full_clean()
        line_instances.append(line)

    JournalLine.objects.bulk_create(line_instances)
    entry.refresh_from_db()

    record_audit_event(
        organization=organization,
        actor=user,
        action="ENTRY_CREATE",
        entity=entry,
        before=None,
        after=serialize_accounting_entry(entry),
        metadata=audit_metadata or {},
    )
    return entry


@transaction.atomic
def update_draft_entry(*, entry, user, header_data, lines, audit_metadata=None):
    entry = _lock_entry(entry)

    if entry.status != JournalEntry.Status.DRAFT:
        raise ValidationError("Seules les écritures brouillon peuvent être modifiées.")

    before = serialize_accounting_entry(entry)

    for field in [
        "journal",
        "period",
        "entry_number",
        "posting_date",
        "description",
        "reference",
        "entry_type",
    ]:
        if field in header_data:
            setattr(entry, field, header_data[field])

    entry.full_clean()
    entry.save()

    entry.lines.all().delete()

    line_instances = []
    for position, line_data in enumerate(lines, start=1):
        line = JournalLine(
            entry=entry,
            line_number=position,
            account=line_data["account"],
            description=line_data.get("description", ""),
            debit=line_data.get("debit") or Decimal("0"),
            credit=line_data.get("credit") or Decimal("0"),
            counterparty=line_data.get("counterparty"),
            cost_center=line_data.get("cost_center"),
            cash_flow_tag=line_data.get("cash_flow_tag", ""),
        )
        line.full_clean()
        line_instances.append(line)

    JournalLine.objects.bulk_create(line_instances)
    entry.refresh_from_db()

    record_audit_event(
        organization=entry.organization,
        actor=user,
        action="ENTRY_UPDATE",
        entity=entry,
        before=before,
        after=serialize_accounting_entry(entry),
        metadata=audit_metadata or {},
    )
    return entry


@transaction.atomic
def validate_journal_entry(
    *,
    entry: JournalEntry,
    user,
    audit_metadata=None,
) -> JournalEntry:
    entry = _lock_entry(entry)

    if entry.status != JournalEntry.Status.DRAFT:
        raise ValidationError("Seule une écriture brouillon peut être validée.")

    before = serialize_accounting_entry(entry)
    validate_entry(entry)

    entry.status = JournalEntry.Status.VALIDATED
    entry.validated_by = user
    entry.validated_at = timezone.now()
    entry.save(update_fields=["status", "validated_by", "validated_at", "updated_at"])

    record_audit_event(
        organization=entry.organization,
        actor=user,
        action="ENTRY_VALIDATE",
        entity=entry,
        before=before,
        after=serialize_accounting_entry(entry),
        metadata=audit_metadata or {},
    )
    return entry


@transaction.atomic
def post_journal_entry(
    *,
    entry: JournalEntry,
    user,
    audit_metadata=None,
) -> JournalEntry:
    entry = _lock_entry(entry)

    if entry.status != JournalEntry.Status.VALIDATED:
        raise ValidationError(
            "Une écriture doit être VALIDATED avant de pouvoir être postée."
        )

    before = serialize_accounting_entry(entry)
    validate_entry(entry)

    entry.status = JournalEntry.Status.POSTED
    entry.posted_by = user
    entry.posted_at = timezone.now()
    entry.save(update_fields=["status", "posted_by", "posted_at", "updated_at"])

    record_audit_event(
        organization=entry.organization,
        actor=user,
        action="ENTRY_POST",
        entity=entry,
        before=before,
        after=serialize_accounting_entry(entry),
        metadata=audit_metadata or {},
    )
    return entry


@transaction.atomic
def reverse_journal_entry(
    *,
    entry: JournalEntry,
    user,
    posting_date,
    period,
    reason="",
    audit_metadata=None,
) -> JournalEntry:
    entry = _lock_entry(entry)

    if entry.status != JournalEntry.Status.POSTED:
        raise ValidationError("Seule une écriture postée peut être extournée.")

    if hasattr(entry, "reversal_entry"):
        raise ValidationError("Cette écriture a déjà été extournée.")

    if period.status != "OPEN":
        raise ValidationError("La période d'extourne doit être ouverte.")

    if period.fiscal_year.organization_id != entry.organization_id:
        raise ValidationError("La période d'extourne appartient à une autre organisation.")

    if not (period.start_date <= posting_date <= period.end_date):
        raise ValidationError("La date d'extourne n'appartient pas à la période sélectionnée.")

    original_before = serialize_accounting_entry(entry)

    reversal = JournalEntry.objects.create(
        organization=entry.organization,
        journal=entry.journal,
        period=period,
        entry_number=f"REV-{entry.entry_number}",
        posting_date=posting_date,
        description=f"Extourne — {entry.description}",
        reference=entry.reference,
        entry_type=JournalEntry.EntryType.REVERSAL,
        status=JournalEntry.Status.DRAFT,
        source="REVERSAL",
        source_reference=str(entry.id),
        created_by=user,
        reversal_of=entry,
    )

    reversal_lines = []
    for line in entry.lines.all():
        reversal_lines.append(
            JournalLine(
                entry=reversal,
                line_number=line.line_number,
                account=line.account,
                description=f"Extourne — {line.description}",
                debit=line.credit,
                credit=line.debit,
                counterparty=line.counterparty,
                cost_center=line.cost_center,
                cash_flow_tag=line.cash_flow_tag,
                metadata={"reversal_of_line": str(line.id)},
            )
        )
    JournalLine.objects.bulk_create(reversal_lines)

    metadata = {
        **(audit_metadata or {}),
        "reason": reason,
        "original_entry_id": str(entry.id),
    }

    validate_journal_entry(
        entry=reversal,
        user=user,
        audit_metadata={**metadata, "automatic_reversal_step": True},
    )
    reversal.refresh_from_db()

    post_journal_entry(
        entry=reversal,
        user=user,
        audit_metadata={**metadata, "automatic_reversal_step": True},
    )
    reversal.refresh_from_db()

    entry.status = JournalEntry.Status.REVERSED
    entry.save(update_fields=["status", "updated_at"])

    record_audit_event(
        organization=entry.organization,
        actor=user,
        action="ENTRY_REVERSE",
        entity=entry,
        before=original_before,
        after=serialize_accounting_entry(entry),
        metadata={
            **metadata,
            "reversal_entry_id": str(reversal.id),
            "reversal_entry_number": reversal.entry_number,
        },
    )

    return reversal
