from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.financial_statements.regulatory import build_regulatory_package
from apps.reporting.models import ReportSnapshot

from .models import ExportJob


MIME_TYPES = {
    ExportJob.Format.XLSX: (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
    ExportJob.Format.PDF: "application/pdf",
    ExportJob.Format.CSV: "text/csv",
    ExportJob.Format.JSON: "application/json",
}

EXTENSIONS = {
    ExportJob.Format.XLSX: "xlsx",
    ExportJob.Format.PDF: "pdf",
    ExportJob.Format.CSV: "csv",
    ExportJob.Format.JSON: "json",
}


def _serialize_decimal(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def serialize_regulatory_package(package):
    return {
        "organization": {
            "id": str(package["organization"].id),
            "name": package["organization"].name,
            "base_currency": package["organization"].base_currency,
        },
        "profile": {
            "id": str(package["profile"].id),
            "name": package["profile"].name,
        },
        "target_framework": {
            "code": package["target_framework"].code,
            "name": package["target_framework"].name,
            "version": package["target_version"].version,
            "source_url": package["target_version"].source_url,
        },
        "fiscal_year": {
            "id": str(package["fiscal_year"].id),
            "name": package["fiscal_year"].name,
            "start_date": package["fiscal_year"].start_date.isoformat(),
            "end_date": package["fiscal_year"].end_date.isoformat(),
        },
        "end_date": package["end_date"].isoformat(),
        "metrics": {
            key: _serialize_decimal(value)
            for key, value in package["metrics"].items()
        },
        "is_ready": package["is_ready"],
        "warnings": package["warnings"],
        "mappings": [
            {
                "source_code": mapping.source_line.code,
                "source_label": mapping.source_line.label,
                "statement_type": mapping.source_line.definition.statement_type,
                "target_code": mapping.target_line.code,
                "target_label": mapping.target_line.label,
                "multiplier": str(mapping.multiplier),
                "mapping_type": mapping.mapping_type,
                "confidence": (
                    str(mapping.confidence)
                    if mapping.confidence is not None
                    else None
                ),
            }
            for mapping in package["profile"].line_mappings.select_related(
                "source_line",
                "source_line__definition",
                "target_line",
            ).order_by(
                "source_line__definition__statement_type",
                "source_line__order",
                "source_line__code",
            )
        ],
        "statements": [
            {
                "code": statement["definition"].code,
                "name": statement["definition"].name,
                "statement_type": statement["statement_type"],
                "comparative_year": (
                    statement["comparative_year"].name
                    if statement["comparative_year"]
                    else None
                ),
                "lines": [
                    {
                        "code": line["code"],
                        "label": line["label"],
                        "standard_reference": line[
                            "standard_reference"
                        ],
                        "is_required": line["is_required"],
                        "is_total": line["is_total"],
                        "depth": line["depth"],
                        "amount": str(line["amount"]),
                        "comparative_amount": str(
                            line["comparative_amount"]
                        ),
                        "metadata": line["metadata"],
                    }
                    for line in statement["lines"]
                ],
                "validations": [
                    {
                        **validation,
                        "value": _serialize_decimal(
                            validation.get("value")
                        ),
                    }
                    for validation in statement["validations"]
                ],
                "unmapped_source_lines": [
                    {
                        "code": line.code,
                        "label": line.label,
                    }
                    for line in statement["unmapped_source_lines"]
                ],
                "unmapped_required_target_lines": [
                    {
                        "code": line.code,
                        "label": line.label,
                    }
                    for line in statement[
                        "unmapped_required_target_lines"
                    ]
                ],
            }
            for statement in package["statements"]
        ],
    }


def create_regulatory_snapshot(*, package, user):
    payload = serialize_regulatory_package(package)
    return ReportSnapshot.objects.create(
        organization=package["organization"],
        fiscal_year=package["fiscal_year"],
        report_type=ReportSnapshot.ReportType.REGULATORY_PACKAGE,
        as_of_date=package["end_date"],
        start_date=package["fiscal_year"].start_date,
        end_date=package["end_date"],
        parameters={
            "regulatory_profile_id": str(package["profile"].id),
            "target_framework": package["target_framework"].code,
            "target_version": package["target_version"].version,
        },
        payload=payload,
        generated_by=user,
    )


def _xlsx_bytes(payload):
    try:
        import xlsxwriter
    except ImportError as exc:
        raise ValidationError(
            "XlsxWriter n'est pas installé. Installez les dépendances du projet."
        ) from exc

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(
        output,
        {"in_memory": True},
    )

    title_format = workbook.add_format(
        {
            "bold": True,
            "font_size": 16,
        }
    )
    header_format = workbook.add_format(
        {
            "bold": True,
            "border": 1,
            "bg_color": "#D9EAF7",
        }
    )
    total_format = workbook.add_format(
        {
            "bold": True,
            "top": 1,
            "num_format": "#,##0.00;[Red](#,##0.00);-",
        }
    )
    amount_format = workbook.add_format(
        {
            "num_format": "#,##0.00;[Red](#,##0.00);-",
        }
    )
    wrap_format = workbook.add_format({"text_wrap": True})

    meta = workbook.add_worksheet("Metadata")
    meta.set_column("A:A", 28)
    meta.set_column("B:B", 55)
    meta.write("A1", "Regulatory Statement Export", title_format)
    metadata_rows = [
        ("Organisation", payload["organization"]["name"]),
        ("Devise", payload["organization"]["base_currency"]),
        ("Profil", payload["profile"]["name"]),
        ("Framework", payload["target_framework"]["code"]),
        ("Version", payload["target_framework"]["version"]),
        ("Source officielle", payload["target_framework"]["source_url"]),
        ("Exercice", payload["fiscal_year"]["name"]),
        ("Date d'arrêté", payload["end_date"]),
        ("Ready", str(payload["is_ready"])),
        (
            "Couverture mapping",
            payload["metrics"].get("source_coverage", "0"),
        ),
    ]
    for row, (label, value) in enumerate(metadata_rows, start=2):
        meta.write(row, 0, label, header_format)
        meta.write(row, 1, value, wrap_format)

    for statement in payload["statements"]:
        sheet_name = re.sub(
            r"[^A-Za-z0-9 _-]",
            "",
            statement["code"],
        )[:31] or "Statement"
        worksheet = workbook.add_worksheet(sheet_name)
        worksheet.freeze_panes(3, 0)
        worksheet.set_column("A:A", 18)
        worksheet.set_column("B:B", 48)
        worksheet.set_column("C:D", 18)
        worksheet.set_column("E:E", 28)
        worksheet.set_column("F:F", 12)

        worksheet.write(0, 0, statement["name"], title_format)
        headers = [
            "Code",
            "Rubrique",
            payload["fiscal_year"]["name"],
            statement["comparative_year"] or "N-1",
            "Référence",
            "Obligatoire",
        ]
        for col, header in enumerate(headers):
            worksheet.write(2, col, header, header_format)

        for row_index, line in enumerate(
            statement["lines"],
            start=3,
        ):
            fmt = total_format if line["is_total"] else amount_format
            label = ("    " * line["depth"]) + line["label"]
            worksheet.write(row_index, 0, line["code"])
            worksheet.write(row_index, 1, label)
            worksheet.write_number(
                row_index,
                2,
                float(Decimal(line["amount"])),
                fmt,
            )
            worksheet.write_number(
                row_index,
                3,
                float(Decimal(line["comparative_amount"])),
                fmt,
            )
            worksheet.write(
                row_index,
                4,
                line["standard_reference"],
                wrap_format,
            )
            worksheet.write(
                row_index,
                5,
                "Oui" if line["is_required"] else "",
            )

    mapping = workbook.add_worksheet("Mapping")
    mapping.set_column("A:A", 24)
    mapping.set_column("B:B", 46)
    mapping.set_column("C:C", 24)
    mapping.set_column("D:D", 46)
    mapping.set_column("E:F", 16)
    for col, header in enumerate(
        [
            "Source code",
            "Source line",
            "Target code",
            "Target line",
            "Multiplier",
            "Type",
        ]
    ):
        mapping.write(0, col, header, header_format)

    for row_index, item in enumerate(payload["mappings"], start=1):
        mapping.write(row_index, 0, item["source_code"])
        mapping.write(row_index, 1, item["source_label"], wrap_format)
        mapping.write(row_index, 2, item["target_code"])
        mapping.write(row_index, 3, item["target_label"], wrap_format)
        mapping.write_number(
            row_index,
            4,
            float(Decimal(item["multiplier"])),
        )
        mapping.write(row_index, 5, item["mapping_type"])

    warnings = workbook.add_worksheet("Warnings")
    warnings.set_column("A:A", 34)
    warnings.set_column("B:B", 80)
    warnings.write(0, 0, "Code", header_format)
    warnings.write(0, 1, "Détail", header_format)
    for row, warning in enumerate(payload["warnings"], start=1):
        warnings.write(row, 0, warning.get("code", ""))
        warnings.write(
            row,
            1,
            json.dumps(
                warning,
                ensure_ascii=False,
                default=str,
            ),
            wrap_format,
        )

    workbook.close()
    return output.getvalue()


def _pdf_bytes(payload):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise ValidationError(
            "ReportLab n'est pas installé. Installez les dépendances du projet."
        ) from exc

    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(
        Paragraph(
            f"Package réglementaire — "
            f"{payload['target_framework']['code']} "
            f"{payload['target_framework']['version']}",
            styles["Title"],
        )
    )
    story.append(
        Paragraph(
            f"{payload['organization']['name']} — "
            f"Exercice {payload['fiscal_year']['name']} — "
            f"Arrêté au {payload['end_date']}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 8 * mm))

    for index, statement in enumerate(payload["statements"]):
        story.append(
            Paragraph(statement["name"], styles["Heading2"])
        )
        data = [
            [
                "Code",
                "Rubrique",
                payload["fiscal_year"]["name"],
                statement["comparative_year"] or "N-1",
                "Référence",
            ]
        ]
        for line in statement["lines"]:
            label = ("· " * line["depth"]) + line["label"]
            data.append(
                [
                    line["code"],
                    label,
                    f"{Decimal(line['amount']):,.2f}",
                    f"{Decimal(line['comparative_amount']):,.2f}",
                    line["standard_reference"],
                ]
            )

        table = Table(
            data,
            colWidths=[
                34 * mm,
                95 * mm,
                32 * mm,
                32 * mm,
                55 * mm,
            ],
            repeatRows=1,
        )
        style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (2, 1), (3, -1), "RIGHT"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ]
        for row_number, line in enumerate(
            statement["lines"],
            start=1,
        ):
            if line["is_total"]:
                style_commands.append(
                    ("FONTNAME", (0, row_number), (-1, row_number), "Helvetica-Bold")
                )
        table.setStyle(TableStyle(style_commands))
        story.append(table)

        if index < len(payload["statements"]) - 1:
            story.append(PageBreak())

    doc.build(story)
    return output.getvalue()


def _csv_bytes(payload):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow(
        [
            "Framework",
            payload["target_framework"]["code"],
            payload["target_framework"]["version"],
        ]
    )
    writer.writerow(
        [
            "Organisation",
            payload["organization"]["name"],
            "Exercice",
            payload["fiscal_year"]["name"],
        ]
    )
    writer.writerow([])

    for statement in payload["statements"]:
        writer.writerow(
            [
                "STATEMENT",
                statement["code"],
                statement["name"],
            ]
        )
        writer.writerow(
            [
                "Code",
                "Rubrique",
                payload["fiscal_year"]["name"],
                statement["comparative_year"] or "N-1",
                "Référence",
                "Obligatoire",
            ]
        )
        for line in statement["lines"]:
            writer.writerow(
                [
                    line["code"],
                    line["label"],
                    line["amount"],
                    line["comparative_amount"],
                    line["standard_reference"],
                    "1" if line["is_required"] else "0",
                ]
            )
        writer.writerow([])

    return output.getvalue().encode("utf-8-sig")


def _json_bytes(payload):
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        default=str,
    ).encode("utf-8")


def render_export_bytes(*, payload, export_format):
    if export_format == ExportJob.Format.XLSX:
        return _xlsx_bytes(payload)
    if export_format == ExportJob.Format.PDF:
        return _pdf_bytes(payload)
    if export_format == ExportJob.Format.CSV:
        return _csv_bytes(payload)
    if export_format == ExportJob.Format.JSON:
        return _json_bytes(payload)
    raise ValidationError(f"Format d'export non supporté : {export_format}.")


def create_regulatory_export(
    *,
    profile,
    fiscal_year,
    end_date,
    export_format,
    user,
    audit_metadata=None,
):
    job = ExportJob.objects.create(
        organization=profile.organization,
        export_type="REGULATORY_PACKAGE",
        format=export_format,
        parameters={
            "profile_id": str(profile.id),
            "fiscal_year_id": str(fiscal_year.id),
            "end_date": end_date.isoformat(),
            "target_framework": profile.target_version.framework.code,
            "target_version": profile.target_version.version,
        },
        status=ExportJob.Status.RUNNING,
        requested_by=user,
        regulatory_profile=profile,
    )

    try:
        package = build_regulatory_package(
            profile=profile,
            fiscal_year=fiscal_year,
            end_date=end_date,
        )
        if not package["is_ready"]:
            raise ValidationError(
                "Le package réglementaire n'est pas exportable : "
                "complétez les mappings et corrigez les warnings bloquants."
            )

        snapshot = create_regulatory_snapshot(
            package=package,
            user=user,
        )
        payload = snapshot.payload
        content = render_export_bytes(
            payload=payload,
            export_format=export_format,
        )

        content_hash = hashlib.sha256(content).hexdigest()
        extension = EXTENSIONS[export_format]
        framework_code = re.sub(
            r"[^a-z0-9_-]+",
            "_",
            profile.target_version.framework.code.lower(),
        )
        fiscal_year_token = re.sub(
            r"[^A-Za-z0-9_-]+",
            "_",
            fiscal_year.name,
        )
        filename = (
            f"{profile.organization.id}_"
            f"{framework_code}_"
            f"{fiscal_year_token}_"
            f"{end_date.isoformat()}."
            f"{extension}"
        )

        job.snapshot = snapshot
        job.mime_type = MIME_TYPES[export_format]
        job.content_sha256 = content_hash
        job.status = ExportJob.Status.DONE
        job.completed_at = timezone.now()
        job.file.save(
            filename,
            ContentFile(content),
            save=False,
        )
        job.save(
            update_fields=[
                "snapshot",
                "mime_type",
                "content_sha256",
                "status",
                "completed_at",
                "file",
                "updated_at",
            ]
        )

        record_audit_event(
            organization=profile.organization,
            actor=user,
            action="REGULATORY_EXPORT_CREATE",
            entity=job,
            before=None,
            after={
                "format": export_format,
                "sha256": content_hash,
                "snapshot_id": str(snapshot.id),
                "profile_id": str(profile.id),
            },
            metadata=audit_metadata or {},
        )

        return job

    except Exception as exc:
        job.status = ExportJob.Status.FAILED
        job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "error_message",
                "completed_at",
                "updated_at",
            ]
        )
        raise
