from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.referentials.models import (
    FrameworkVersion,
    StatementDefinition,
    StatementLine,
)

from .models import (
    RegulatoryStatementLineMapping,
    RegulatoryStatementProfile,
)
from .services import (
    build_balance_sheet,
    build_cash_flow_statement,
    build_income_statement,
    ensure_financial_statement_configuration,
)


ROLE_BY_SOURCE_CODE = {
    "IS_REVENUE": "revenue",
    "IS_COST_OF_SALES": "cost_of_sales",
    "IS_EXTERNAL_SERVICES": "external_services",
    "IS_TAXES": "taxes",
    "IS_PERSONNEL": "personnel_expenses",
    "IS_DEPRECIATION": "depreciation",
    "IS_FINANCE_EXPENSES": "finance_expenses",
    "IS_OTHER_EXPENSES": "other_expenses",
    "IS_INCOME_TAX": "income_tax",
    "BS_CURRENT_ASSETS": "current_assets",
    "BS_NONCURRENT_ASSETS": "noncurrent_assets",
    "BS_CURRENT_LIABILITIES": "current_liabilities",
    "BS_NONCURRENT_LIABILITIES": "noncurrent_liabilities",
    "BS_EQUITY": "equity",
    "BS_CURRENT_RESULT": "current_result",
    "CF_OPENING_CASH": "opening_cash",
    "CF_OPERATING": "operating_cash_flow",
    "CF_INVESTING": "investing_cash_flow",
    "CF_FINANCING": "financing_cash_flow",
    "CF_UNCLASSIFIED": "unclassified_cash_flow",
    "CF_ENDING_CASH": "ending_cash",
    "CF_RECONCILIATION_GAP": "cash_reconciliation_gap",
}


def _normalize_text(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _source_report_for_type(
    *,
    organization,
    fiscal_year,
    end_date,
    statement_type,
):
    if statement_type == StatementDefinition.StatementType.INCOME_STATEMENT:
        return build_income_statement(
            organization=organization,
            fiscal_year=fiscal_year,
            end_date=end_date,
        )

    if statement_type == StatementDefinition.StatementType.BALANCE_SHEET:
        return build_balance_sheet(
            organization=organization,
            fiscal_year=fiscal_year,
            as_of_date=end_date,
        )

    if statement_type == StatementDefinition.StatementType.CASH_FLOW:
        return build_cash_flow_statement(
            organization=organization,
            fiscal_year=fiscal_year,
            end_date=end_date,
        )

    raise ValidationError(
        f"Type d'état non pris en charge par le moteur Sprint 7 : {statement_type}."
    )


def profile_metrics(profile):
    source_lines = StatementLine.objects.filter(
        definition__version=profile.source_version,
        definition__statement_type__in=[
            StatementDefinition.StatementType.INCOME_STATEMENT,
            StatementDefinition.StatementType.BALANCE_SHEET,
            StatementDefinition.StatementType.CASH_FLOW,
        ],
        is_total=False,
    )
    target_required = StatementLine.objects.filter(
        definition__version=profile.target_version,
        is_required=True,
        is_total=False,
    )

    mapped_source_ids = set(
        profile.line_mappings.values_list("source_line_id", flat=True)
    )
    mapped_target_ids = set(
        profile.line_mappings.values_list("target_line_id", flat=True)
    )

    source_count = source_lines.count()
    source_mapped = source_lines.filter(id__in=mapped_source_ids).count()
    required_count = target_required.count()
    required_mapped = target_required.filter(id__in=mapped_target_ids).count()

    return {
        "source_line_count": source_count,
        "mapped_source_count": source_mapped,
        "unmapped_source_count": max(source_count - source_mapped, 0),
        "source_coverage": (
            (Decimal(source_mapped) / Decimal(source_count)) * Decimal("100")
            if source_count
            else Decimal("0")
        ),
        "required_target_count": required_count,
        "mapped_required_target_count": required_mapped,
        "unmapped_required_target_count": max(
            required_count - required_mapped,
            0,
        ),
        "is_ready": (
            source_mapped > 0
            and required_mapped == required_count
        ),
    }


@transaction.atomic
def create_regulatory_profile(
    *,
    organization,
    target_version,
    user,
    name=None,
):
    configuration = ensure_financial_statement_configuration(
        organization=organization,
        user=user,
    )
    source_version = configuration.framework_version

    if target_version.id == source_version.id:
        raise ValidationError(
            "La version réglementaire cible doit être différente "
            "du framework interne de présentation."
        )

    if not target_version.statement_definitions.exists():
        raise ValidationError(
            "La version cible ne contient aucune définition d'état financier. "
            "Chargez un JSON réglementaire avec la section 'statements'."
        )

    supported_types = [
        StatementDefinition.StatementType.INCOME_STATEMENT,
        StatementDefinition.StatementType.BALANCE_SHEET,
        StatementDefinition.StatementType.CASH_FLOW,
    ]
    for statement_type in supported_types:
        definition_count = target_version.statement_definitions.filter(
            statement_type=statement_type,
        ).count()
        if definition_count > 1:
            raise ValidationError(
                "Le MVP Sprint 7 exige au maximum une définition par type "
                f"d'état pour une version cible. {statement_type}: "
                f"{definition_count} définitions détectées."
            )

    profile, created = RegulatoryStatementProfile.objects.get_or_create(
        organization=organization,
        target_version=target_version,
        defaults={
            "name": name
            or (
                f"{target_version.framework.code} "
                f"{target_version.version}"
            ),
            "source_version": source_version,
            "is_active": True,
            "is_default": not organization.regulatory_statement_profiles.exists(),
        },
    )

    if not created and profile.source_version_id != source_version.id:
        profile.source_version = source_version
        profile.save(update_fields=["source_version", "updated_at"])

    if created:
        record_audit_event(
            organization=organization,
            actor=user,
            action="REGULATORY_PROFILE_CREATE",
            entity=profile,
            before=None,
            after={
                "source_version": str(source_version.id),
                "target_version": str(target_version.id),
                "target_framework": target_version.framework.code,
            },
        )

    return profile


def _target_candidates(source_line, profile):
    statement_type = source_line.definition.statement_type
    candidates = list(
        StatementLine.objects.filter(
            definition__version=profile.target_version,
            definition__statement_type=statement_type,
            is_total=False,
        )
        .select_related("definition")
        .order_by("order", "code")
    )

    source_code = source_line.code
    source_role = ROLE_BY_SOURCE_CODE.get(source_code)
    normalized_source_label = _normalize_text(source_line.label)

    ranked = []

    for target in candidates:
        metadata = target.metadata or {}
        source_codes = metadata.get("source_codes") or []
        if isinstance(source_codes, str):
            source_codes = [source_codes]

        source_code_meta = metadata.get("source_code")
        role = metadata.get("role")

        score = 0
        reason = ""

        if source_code == target.code:
            score = 100
            reason = "code exact"
        elif source_code_meta == source_code:
            score = 98
            reason = "metadata.source_code"
        elif source_code in source_codes:
            score = 96
            reason = "metadata.source_codes"
        elif source_role and role == source_role:
            score = 92
            reason = "role réglementaire"
        elif normalized_source_label == _normalize_text(target.label):
            score = 85
            reason = "libellé normalisé exact"

        if score:
            ranked.append((score, reason, target))

    ranked.sort(key=lambda item: (-item[0], item[2].order, item[2].code))
    return ranked


@transaction.atomic
def auto_map_regulatory_profile(*, profile, user):
    profile = (
        RegulatoryStatementProfile.objects.select_for_update()
        .select_related(
            "organization",
            "source_version",
            "target_version",
            "target_version__framework",
        )
        .get(pk=profile.pk)
    )

    manual_source_ids = set(
        profile.line_mappings.filter(
            mapping_type=RegulatoryStatementLineMapping.MappingType.MANUAL,
        ).values_list("source_line_id", flat=True)
    )

    profile.line_mappings.filter(
        mapping_type__in=[
            RegulatoryStatementLineMapping.MappingType.RULE,
            RegulatoryStatementLineMapping.MappingType.SUGGESTED,
        ]
    ).delete()

    created = 0
    unresolved = 0

    source_lines = (
        StatementLine.objects.filter(
            definition__version=profile.source_version,
            definition__statement_type__in=[
                StatementDefinition.StatementType.INCOME_STATEMENT,
                StatementDefinition.StatementType.BALANCE_SHEET,
                StatementDefinition.StatementType.CASH_FLOW,
            ],
            is_total=False,
        )
        .select_related("definition")
        .order_by(
            "definition__statement_type",
            "order",
            "code",
        )
    )

    for source_line in source_lines:
        if source_line.id in manual_source_ids:
            continue

        candidates = _target_candidates(source_line, profile)
        if not candidates:
            unresolved += 1
            continue

        score, reason, target = candidates[0]
        RegulatoryStatementLineMapping.objects.create(
            profile=profile,
            source_line=source_line,
            target_line=target,
            multiplier=Decimal("1"),
            mapping_type=RegulatoryStatementLineMapping.MappingType.RULE,
            confidence=Decimal(score) / Decimal("100"),
            validated_by=user,
            validated_at=timezone.now(),
            notes=f"Auto-mapping Sprint 7 : {reason}.",
        )
        created += 1

    metrics = profile_metrics(profile)

    record_audit_event(
        organization=profile.organization,
        actor=user,
        action="REGULATORY_AUTO_MAPPING",
        entity=profile,
        before=None,
        after={
            "created": created,
            "unresolved": unresolved,
            "coverage": str(metrics["source_coverage"]),
            "required_unmapped": metrics[
                "unmapped_required_target_count"
            ],
        },
    )

    return {
        "created": created,
        "unresolved": unresolved,
        "metrics": metrics,
    }


@transaction.atomic
def update_regulatory_mapping(
    *,
    profile,
    source_line,
    target_line,
    multiplier,
    user,
):
    if source_line.definition.version_id != profile.source_version_id:
        raise ValidationError(
            "La ligne source n'appartient pas au framework source du profil."
        )

    if target_line:
        if target_line.definition.version_id != profile.target_version_id:
            raise ValidationError(
                "La ligne cible n'appartient pas au framework réglementaire."
            )
        if (
            target_line.definition.statement_type
            != source_line.definition.statement_type
        ):
            raise ValidationError(
                "La ligne source et la ligne cible doivent appartenir "
                "au même type d'état financier."
            )
        if target_line.is_total:
            raise ValidationError(
                "Une ligne source ne peut pas être mappée directement "
                "sur un total réglementaire."
            )

    existing = profile.line_mappings.filter(source_line=source_line).first()
    before = (
        {
            "target_line": existing.target_line.code,
            "multiplier": str(existing.multiplier),
            "mapping_type": existing.mapping_type,
        }
        if existing
        else None
    )

    profile.line_mappings.filter(source_line=source_line).delete()

    mapping = None
    if target_line:
        mapping = RegulatoryStatementLineMapping.objects.create(
            profile=profile,
            source_line=source_line,
            target_line=target_line,
            multiplier=multiplier,
            mapping_type=RegulatoryStatementLineMapping.MappingType.MANUAL,
            confidence=Decimal("1.0000"),
            validated_by=user,
            validated_at=timezone.now(),
            notes="Mapping réglementaire manuel.",
        )

    record_audit_event(
        organization=profile.organization,
        actor=user,
        action="REGULATORY_MAPPING_UPDATE",
        entity=profile,
        before=before,
        after={
            "source_line": source_line.code,
            "target_line": target_line.code if target_line else None,
            "multiplier": str(multiplier),
        },
    )

    return mapping


def _hierarchical_target_lines(
    definition,
    current_direct,
    comparative_direct,
):
    lines = list(
        definition.lines.all()
        .select_related("parent")
        .order_by("order", "code")
    )
    by_id = {line.id: line for line in lines}
    children = defaultdict(list)
    for line in lines:
        children[line.parent_id].append(line)

    current_cache = {}
    comparative_cache = {}

    def amount_for(line, source, cache):
        if line.id in cache:
            return cache[line.id]

        amount = source.get(line.id, Decimal("0"))
        for child in children.get(line.id, []):
            amount += amount_for(child, source, cache) * Decimal(
                child.sign
            )
        cache[line.id] = amount
        return amount

    output = []
    for line in lines:
        current = amount_for(line, current_direct, current_cache)
        comparative = amount_for(
            line,
            comparative_direct,
            comparative_cache,
        )

        depth = 0
        parent = line.parent
        while parent:
            depth += 1
            parent = by_id.get(parent.parent_id)

        output.append(
            {
                "id": line.id,
                "code": line.code,
                "label": line.label,
                "standard_reference": line.standard_reference,
                "metadata": line.metadata or {},
                "is_required": line.is_required,
                "is_total": line.is_total,
                "depth": depth,
                "amount": current,
                "comparative_amount": comparative,
            }
        )

    return output


def build_regulatory_statement(
    *,
    profile,
    fiscal_year,
    statement_type,
    end_date=None,
):
    definition = (
        StatementDefinition.objects.filter(
            version=profile.target_version,
            statement_type=statement_type,
        )
        .prefetch_related("lines")
        .order_by("code")
        .first()
    )
    if definition is None:
        raise ValidationError(
            f"Aucune définition {statement_type} "
            f"dans {profile.target_version}."
        )

    source_report = _source_report_for_type(
        organization=profile.organization,
        fiscal_year=fiscal_year,
        end_date=end_date,
        statement_type=statement_type,
    )

    source_values = source_report["values"]
    comparative_values = source_report.get("comparative_values", {})

    mappings = list(
        profile.line_mappings.filter(
            source_line__definition__statement_type=statement_type,
            target_line__definition=definition,
        ).select_related(
            "source_line",
            "target_line",
        )
    )

    current_direct = defaultdict(lambda: Decimal("0"))
    comparative_direct = defaultdict(lambda: Decimal("0"))

    mapped_source_ids = set()
    mapped_target_ids = set()

    for mapping in mappings:
        source_amount = source_values.get(
            mapping.source_line.code,
            Decimal("0"),
        )
        comparative_amount = comparative_values.get(
            mapping.source_line.code,
            Decimal("0"),
        )

        current_direct[mapping.target_line_id] += (
            source_amount * mapping.multiplier
        )
        comparative_direct[mapping.target_line_id] += (
            comparative_amount * mapping.multiplier
        )

        mapped_source_ids.add(mapping.source_line_id)
        mapped_target_ids.add(mapping.target_line_id)

    lines = _hierarchical_target_lines(
        definition,
        dict(current_direct),
        dict(comparative_direct),
    )

    source_lines = StatementLine.objects.filter(
        definition__version=profile.source_version,
        definition__statement_type=statement_type,
        is_total=False,
    )
    unmapped_source = [
        line
        for line in source_lines.exclude(id__in=mapped_source_ids)
        .order_by("order", "code")
        if (
            source_values.get(line.code, Decimal("0")) != Decimal("0")
            or comparative_values.get(line.code, Decimal("0")) != Decimal("0")
        )
    ]

    required_unmapped = list(
        definition.lines.filter(
            is_required=True,
            is_total=False,
        )
        .exclude(id__in=mapped_target_ids)
        .order_by("order", "code")
    )

    values = {line["code"]: line["amount"] for line in lines}
    comparative = {
        line["code"]: line["comparative_amount"]
        for line in lines
    }

    validations = []
    if statement_type == StatementDefinition.StatementType.BALANCE_SHEET:
        total_assets = next(
            (
                line["amount"]
                for line in lines
                if line["metadata"].get("role") == "total_assets"
            ),
            None,
        )
        total_liab_equity = next(
            (
                line["amount"]
                for line in lines
                if line["metadata"].get("role")
                in {
                    "total_liabilities_equity",
                    "total_equity_liabilities",
                }
            ),
            None,
        )
        if total_assets is not None and total_liab_equity is not None:
            validations.append(
                {
                    "code": "BALANCE_EQUATION",
                    "label": "Équation du bilan réglementaire",
                    "value": total_assets - total_liab_equity,
                    "is_ok": total_assets == total_liab_equity,
                }
            )

    if statement_type == StatementDefinition.StatementType.CASH_FLOW:
        reconciliation = next(
            (
                line["amount"]
                for line in lines
                if line["metadata"].get("role")
                == "cash_reconciliation_gap"
            ),
            None,
        )
        if reconciliation is not None:
            validations.append(
                {
                    "code": "CASH_RECONCILIATION",
                    "label": "Rapprochement de trésorerie",
                    "value": reconciliation,
                    "is_ok": reconciliation == Decimal("0"),
                }
            )

    return {
        "profile": profile,
        "definition": definition,
        "statement_type": statement_type,
        "fiscal_year": fiscal_year,
        "end_date": end_date or fiscal_year.end_date,
        "comparative_year": source_report.get("comparative_year"),
        "lines": lines,
        "values": values,
        "comparative_values": comparative,
        "unmapped_source_lines": unmapped_source,
        "unmapped_required_target_lines": required_unmapped,
        "validations": validations,
    }


def build_regulatory_package(
    *,
    profile,
    fiscal_year,
    end_date=None,
):
    statements = []
    warnings = []

    available_types = set(
        profile.target_version.statement_definitions.values_list(
            "statement_type",
            flat=True,
        )
    )

    for statement_type in [
        StatementDefinition.StatementType.INCOME_STATEMENT,
        StatementDefinition.StatementType.BALANCE_SHEET,
        StatementDefinition.StatementType.CASH_FLOW,
    ]:
        if statement_type not in available_types:
            warnings.append(
                {
                    "code": "MISSING_TARGET_STATEMENT",
                    "message": (
                        f"Aucune définition {statement_type} "
                        f"dans {profile.target_version}."
                    ),
                }
            )
            continue

        statement = build_regulatory_statement(
            profile=profile,
            fiscal_year=fiscal_year,
            statement_type=statement_type,
            end_date=end_date,
        )
        statements.append(statement)

        if statement["unmapped_source_lines"]:
            warnings.append(
                {
                    "code": "UNMAPPED_SOURCE_LINES",
                    "statement_type": statement_type,
                    "count": len(statement["unmapped_source_lines"]),
                }
            )
        if statement["unmapped_required_target_lines"]:
            warnings.append(
                {
                    "code": "UNMAPPED_REQUIRED_TARGET_LINES",
                    "statement_type": statement_type,
                    "count": len(
                        statement["unmapped_required_target_lines"]
                    ),
                }
            )

    metrics = profile_metrics(profile)

    return {
        "profile": profile,
        "organization": profile.organization,
        "target_framework": profile.target_version.framework,
        "target_version": profile.target_version,
        "fiscal_year": fiscal_year,
        "end_date": end_date or fiscal_year.end_date,
        "metrics": metrics,
        "statements": statements,
        "warnings": warnings,
        "is_ready": bool(statements) and metrics["is_ready"] and not warnings,
    }
