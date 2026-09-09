from __future__ import annotations

from typing import Any

from .models import AuditEvent


def serialize_accounting_entry(entry) -> dict[str, Any]:
    return {
        "id": str(entry.id),
        "entry_number": entry.entry_number,
        "posting_date": entry.posting_date.isoformat() if entry.posting_date else None,
        "journal": entry.journal.code if entry.journal_id else None,
        "period": entry.period.name if entry.period_id else None,
        "description": entry.description,
        "reference": entry.reference,
        "entry_type": entry.entry_type,
        "status": entry.status,
        "total_debit": str(entry.total_debit),
        "total_credit": str(entry.total_credit),
        "difference": str(entry.difference),
        "lines": [
            {
                "id": str(line.id),
                "line_number": line.line_number,
                "account": line.account.code,
                "description": line.description,
                "debit": str(line.debit),
                "credit": str(line.credit),
                "counterparty": line.counterparty.code if line.counterparty_id else None,
                "cost_center": line.cost_center.code if line.cost_center_id else None,
            }
            for line in entry.lines.select_related(
                "account",
                "counterparty",
                "cost_center",
            ).order_by("line_number")
        ],
    }


def record_audit_event(
    *,
    organization,
    actor,
    action: str,
    entity,
    before=None,
    after=None,
    metadata=None,
    source_ip=None,
    request_id="",
):
    event_metadata = metadata or {}
    resolved_source_ip = source_ip or event_metadata.get("source_ip")

    return AuditEvent.objects.create(
        organization=organization,
        actor=actor,
        action=action,
        entity_type=entity.__class__.__name__,
        entity_id=str(entity.pk),
        before=before,
        after=after,
        metadata=event_metadata,
        source_ip=resolved_source_ip,
        request_id=request_id or "",
    )
