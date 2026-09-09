from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.accounting.models import Account, JournalEntry, JournalLine
from apps.audit.services import record_audit_event
from apps.organizations.models import FiscalYear
from apps.referentials.models import (
    AccountingFramework,
    FrameworkVersion,
    StatementAccountMapping,
    StatementDefinition,
    StatementLine,
)

from .models import FinancialStatementConfiguration


DECIMAL_FIELD = DecimalField(max_digits=30, decimal_places=4)

FRAMEWORK_CODE = "CFA_FRA_MVP"
FRAMEWORK_VERSION = "1.0"

INCOME_DEFINITION_CODE = "CFA_FRA_IS"
BALANCE_DEFINITION_CODE = "CFA_FRA_BS"
CASH_FLOW_DEFINITION_CODE = "CFA_FRA_CF"

REPORT_STATUSES = [
    JournalEntry.Status.POSTED,
    JournalEntry.Status.REVERSED,
]

INCOME_ENTRY_TYPES = [
    JournalEntry.EntryType.NORMAL,
    JournalEntry.EntryType.ADJUSTING,
    JournalEntry.EntryType.REVERSAL,
]

BALANCE_ENTRY_TYPES = [
    JournalEntry.EntryType.OPENING,
    JournalEntry.EntryType.NORMAL,
    JournalEntry.EntryType.ADJUSTING,
    JournalEntry.EntryType.REVERSAL,
]

CASH_FLOW_ENTRY_TYPES = [
    JournalEntry.EntryType.NORMAL,
    JournalEntry.EntryType.ADJUSTING,
    JournalEntry.EntryType.REVERSAL,
]


INCOME_LINE_SPECS = [
    {
        "code": "IS_NET_INCOME",
        "label": "Résultat net",
        "order": 100,
        "sign": 1,
        "is_total": True,
        "parent": None,
    },
    {
        "code": "IS_REVENUE",
        "label": "Produits / chiffre d'affaires",
        "order": 10,
        "sign": 1,
        "is_total": False,
        "parent": "IS_NET_INCOME",
    },
    {
        "code": "IS_COST_OF_SALES",
        "label": "Achats et coût des ventes",
        "order": 20,
        "sign": -1,
        "is_total": False,
        "parent": "IS_NET_INCOME",
    },
    {
        "code": "IS_EXTERNAL_SERVICES",
        "label": "Services extérieurs",
        "order": 30,
        "sign": -1,
        "is_total": False,
        "parent": "IS_NET_INCOME",
    },
    {
        "code": "IS_TAXES",
        "label": "Impôts, taxes et versements assimilés",
        "order": 40,
        "sign": -1,
        "is_total": False,
        "parent": "IS_NET_INCOME",
    },
    {
        "code": "IS_PERSONNEL",
        "label": "Charges de personnel",
        "order": 50,
        "sign": -1,
        "is_total": False,
        "parent": "IS_NET_INCOME",
    },
    {
        "code": "IS_DEPRECIATION",
        "label": "Dotations aux amortissements et provisions",
        "order": 60,
        "sign": -1,
        "is_total": False,
        "parent": "IS_NET_INCOME",
    },
    {
        "code": "IS_FINANCE_EXPENSES",
        "label": "Charges financières",
        "order": 70,
        "sign": -1,
        "is_total": False,
        "parent": "IS_NET_INCOME",
    },
    {
        "code": "IS_OTHER_EXPENSES",
        "label": "Autres charges",
        "order": 80,
        "sign": -1,
        "is_total": False,
        "parent": "IS_NET_INCOME",
    },
    {
        "code": "IS_INCOME_TAX",
        "label": "Impôt sur le résultat",
        "order": 90,
        "sign": -1,
        "is_total": False,
        "parent": "IS_NET_INCOME",
    },
]


BALANCE_LINE_SPECS = [
    {
        "code": "BS_TOTAL_ASSETS",
        "label": "Total actif",
        "order": 40,
        "sign": 1,
        "is_total": True,
        "parent": None,
    },
    {
        "code": "BS_CURRENT_ASSETS",
        "label": "Actifs courants",
        "order": 10,
        "sign": 1,
        "is_total": False,
        "parent": "BS_TOTAL_ASSETS",
    },
    {
        "code": "BS_NONCURRENT_ASSETS",
        "label": "Actifs non courants",
        "order": 20,
        "sign": 1,
        "is_total": False,
        "parent": "BS_TOTAL_ASSETS",
    },
    {
        "code": "BS_TOTAL_LIAB_EQUITY",
        "label": "Total passif et capitaux propres",
        "order": 100,
        "sign": 1,
        "is_total": True,
        "parent": None,
    },
    {
        "code": "BS_CURRENT_LIABILITIES",
        "label": "Passifs courants",
        "order": 60,
        "sign": 1,
        "is_total": False,
        "parent": "BS_TOTAL_LIAB_EQUITY",
    },
    {
        "code": "BS_NONCURRENT_LIABILITIES",
        "label": "Passifs non courants",
        "order": 70,
        "sign": 1,
        "is_total": False,
        "parent": "BS_TOTAL_LIAB_EQUITY",
    },
    {
        "code": "BS_EQUITY",
        "label": "Capitaux propres avant résultat",
        "order": 80,
        "sign": 1,
        "is_total": False,
        "parent": "BS_TOTAL_LIAB_EQUITY",
    },
    {
        "code": "BS_CURRENT_RESULT",
        "label": "Résultat de l'exercice",
        "order": 90,
        "sign": 1,
        "is_total": False,
        "parent": "BS_TOTAL_LIAB_EQUITY",
    },
]


CASH_FLOW_LINE_SPECS = [
    {
        "code": "CF_OPENING_CASH",
        "label": "Trésorerie d'ouverture",
        "order": 10,
        "sign": 1,
        "is_total": False,
        "parent": None,
    },
    {
        "code": "CF_NET_CHANGE",
        "label": "Variation nette de trésorerie",
        "order": 50,
        "sign": 1,
        "is_total": True,
        "parent": None,
    },
    {
        "code": "CF_OPERATING",
        "label": "Flux de trésorerie liés aux activités opérationnelles",
        "order": 20,
        "sign": 1,
        "is_total": False,
        "parent": "CF_NET_CHANGE",
    },
    {
        "code": "CF_INVESTING",
        "label": "Flux de trésorerie liés aux activités d'investissement",
        "order": 30,
        "sign": 1,
        "is_total": False,
        "parent": "CF_NET_CHANGE",
    },
    {
        "code": "CF_FINANCING",
        "label": "Flux de trésorerie liés aux activités de financement",
        "order": 40,
        "sign": 1,
        "is_total": False,
        "parent": "CF_NET_CHANGE",
    },
    {
        "code": "CF_UNCLASSIFIED",
        "label": "Flux non classés",
        "order": 45,
        "sign": 1,
        "is_total": False,
        "parent": "CF_NET_CHANGE",
    },
    {
        "code": "CF_ENDING_CASH",
        "label": "Trésorerie de clôture",
        "order": 60,
        "sign": 1,
        "is_total": False,
        "parent": None,
    },
    {
        "code": "CF_RECONCILIATION_GAP",
        "label": "Écart de rapprochement de trésorerie",
        "order": 70,
        "sign": 1,
        "is_total": False,
        "parent": None,
    },
]


def _ensure_definition(version, code, name, statement_type, line_specs):
    definition, _ = StatementDefinition.objects.get_or_create(
        version=version,
        code=code,
        defaults={
            "name": name,
            "statement_type": statement_type,
        },
    )

    by_code = {}
    for spec in line_specs:
        line, _ = StatementLine.objects.get_or_create(
            definition=definition,
            code=spec["code"],
            defaults={
                "label": spec["label"],
                "order": spec["order"],
                "sign": spec["sign"],
                "is_total": spec["is_total"],
            },
        )
        changed = False
        for field in ("label", "order", "sign", "is_total"):
            if getattr(line, field) != spec[field]:
                setattr(line, field, spec[field])
                changed = True
        if changed:
            line.save(update_fields=[
                "label",
                "order",
                "sign",
                "is_total",
                "updated_at",
            ])
        by_code[spec["code"]] = line

    for spec in line_specs:
        line = by_code[spec["code"]]
        parent = by_code.get(spec["parent"])
        if line.parent_id != (parent.id if parent else None):
            line.parent = parent
            line.save(update_fields=["parent", "updated_at"])

    return definition


@transaction.atomic
def ensure_financial_statement_configuration(*, organization, user=None):
    framework, _ = AccountingFramework.objects.get_or_create(
        code=FRAMEWORK_CODE,
        defaults={
            "name": "CFA FRA — Modèle d'états financiers MVP",
            "description": (
                "Référentiel de présentation interne du MVP. "
                "Il ne remplace pas un format réglementaire SYSCOHADA ou IFRS."
            ),
            "is_active": True,
        },
    )
    version, _ = FrameworkVersion.objects.get_or_create(
        framework=framework,
        version=FRAMEWORK_VERSION,
        defaults={"is_current": True},
    )

    _ensure_definition(
        version,
        INCOME_DEFINITION_CODE,
        "Compte de résultat — CFA FRA MVP",
        StatementDefinition.StatementType.INCOME_STATEMENT,
        INCOME_LINE_SPECS,
    )
    _ensure_definition(
        version,
        BALANCE_DEFINITION_CODE,
        "Bilan — CFA FRA MVP",
        StatementDefinition.StatementType.BALANCE_SHEET,
        BALANCE_LINE_SPECS,
    )
    _ensure_definition(
        version,
        CASH_FLOW_DEFINITION_CODE,
        "Tableau des flux de trésorerie — CFA FRA MVP",
        StatementDefinition.StatementType.CASH_FLOW,
        CASH_FLOW_LINE_SPECS,
    )

    configuration, created = FinancialStatementConfiguration.objects.get_or_create(
        organization=organization,
        defaults={
            "framework_version": version,
            "comparative_enabled": True,
            "cash_account_prefixes": ["5"],
            "infer_cash_flow_categories": True,
            "is_active": True,
        },
    )

    if not configuration.cash_account_prefixes:
        configuration.cash_account_prefixes = ["5"]
        configuration.save(update_fields=["cash_account_prefixes", "updated_at"])

    if created and user:
        record_audit_event(
            organization=organization,
            actor=user,
            action="FINANCIAL_STATEMENTS_BOOTSTRAP",
            entity=configuration,
            before=None,
            after={
                "framework": framework.code,
                "version": version.version,
            },
        )

    return configuration


def _expense_line_code(account):
    code = (account.code or "").strip()
    label = (account.name or "").upper()

    if code.startswith(("60", "61")):
        return "IS_COST_OF_SALES"
    if code.startswith(("62", "63")):
        return "IS_EXTERNAL_SERVICES"
    if code.startswith("64"):
        return "IS_TAXES"
    if code.startswith("66") or any(
        token in label for token in ("SALAIRE", "REMUNERATION", "RÉMUNÉRATION", "PERSONNEL")
    ):
        return "IS_PERSONNEL"
    if code.startswith("68") or any(
        token in label for token in ("AMORTIS", "PROVISION", "DOTATION")
    ):
        return "IS_DEPRECIATION"
    if code.startswith("67") or any(
        token in label for token in ("INTERET", "INTÉRÊT", "FINANCI")
    ):
        return "IS_FINANCE_EXPENSES"
    if code.startswith("69") or "IMPOT SUR" in label or "IMPÔT SUR" in label:
        return "IS_INCOME_TAX"
    return "IS_OTHER_EXPENSES"


def infer_statement_mapping(account):
    code = (account.code or "").strip()
    current_noncurrent = (account.current_noncurrent or "").upper()

    account_type = account.account_type

    if account_type == Account.AccountType.REVENUE:
        return "IS_REVENUE", -1

    if account_type == Account.AccountType.EXPENSE:
        return _expense_line_code(account), 1

    if account_type == Account.AccountType.ASSET:
        if "NON" in current_noncurrent or code.startswith("2"):
            return "BS_NONCURRENT_ASSETS", 1
        return "BS_CURRENT_ASSETS", 1

    if account_type == Account.AccountType.LIABILITY:
        if "CURRENT" in current_noncurrent and "NON" not in current_noncurrent:
            return "BS_CURRENT_LIABILITIES", -1
        if code.startswith("4"):
            return "BS_CURRENT_LIABILITIES", -1
        return "BS_NONCURRENT_LIABILITIES", -1

    if account_type == Account.AccountType.EQUITY:
        return "BS_EQUITY", -1

    # Fallback by accounting class when the imported account is still typed OTHER.
    if code.startswith(("6",)):
        return _expense_line_code(account), 1
    if code.startswith(("7",)):
        return "IS_REVENUE", -1
    if code.startswith(("2",)):
        return "BS_NONCURRENT_ASSETS", 1
    if code.startswith(("3", "5")):
        return "BS_CURRENT_ASSETS", 1
    if code.startswith("4"):
        if code.startswith("41"):
            return "BS_CURRENT_ASSETS", 1
        return "BS_CURRENT_LIABILITIES", -1
    if code.startswith("1"):
        if code.startswith(("10", "11", "12", "13")):
            return "BS_EQUITY", -1
        return "BS_NONCURRENT_LIABILITIES", -1

    return None, 1


@transaction.atomic
def auto_map_accounts(*, organization, user=None):
    configuration = ensure_financial_statement_configuration(
        organization=organization,
        user=user,
    )
    version = configuration.framework_version

    line_by_code = {
        line.code: line
        for line in StatementLine.objects.filter(
            definition__version=version,
            definition__statement_type__in=[
                StatementDefinition.StatementType.INCOME_STATEMENT,
                StatementDefinition.StatementType.BALANCE_SHEET,
            ],
            is_total=False,
        ).select_related("definition")
    }

    existing_manual_account_ids = set(
        StatementAccountMapping.objects.filter(
            account__organization=organization,
            statement_line__definition__version=version,
            mapping_type=StatementAccountMapping.MappingType.MANUAL,
        ).values_list("account_id", flat=True)
    )

    StatementAccountMapping.objects.filter(
        account__organization=organization,
        statement_line__definition__version=version,
        mapping_type__in=[
            StatementAccountMapping.MappingType.RULE,
            StatementAccountMapping.MappingType.SUGGESTED,
        ],
    ).delete()

    created = 0
    skipped = 0

    for account in Account.objects.filter(
        organization=organization,
        is_active=True,
    ).order_by("code"):
        if account.id in existing_manual_account_ids:
            skipped += 1
            continue

        line_code, multiplier = infer_statement_mapping(account)
        line = line_by_code.get(line_code)
        if line is None:
            skipped += 1
            continue

        StatementAccountMapping.objects.create(
            account=account,
            statement_line=line,
            balance_multiplier=multiplier,
            mapping_type=StatementAccountMapping.MappingType.RULE,
            confidence=Decimal("0.8000"),
            validated_by=user,
            validated_at=timezone.now() if user else None,
            notes="Mapping automatique Sprint 6.",
        )
        created += 1

    if user:
        record_audit_event(
            organization=organization,
            actor=user,
            action="STATEMENT_AUTO_MAPPING",
            entity=configuration,
            before=None,
            after={
                "created": created,
                "manual_preserved": skipped,
            },
        )

    return {
        "configuration": configuration,
        "created": created,
        "manual_preserved_or_unmapped": skipped,
    }


def _mapping_queryset(organization, version, statement_type):
    return (
        StatementAccountMapping.objects.filter(
            account__organization=organization,
            statement_line__definition__version=version,
            statement_line__definition__statement_type=statement_type,
        )
        .select_related(
            "account",
            "statement_line",
            "statement_line__definition",
        )
        .order_by("account__code")
    )


def _movement_by_account(
    *,
    organization,
    fiscal_year,
    start_date,
    end_date,
    entry_types,
):
    movement = ExpressionWrapper(
        F("debit") - F("credit"),
        output_field=DECIMAL_FIELD,
    )

    rows = (
        JournalLine.objects.filter(
            entry__organization=organization,
            entry__period__fiscal_year=fiscal_year,
            entry__status__in=REPORT_STATUSES,
            entry__entry_type__in=entry_types,
            entry__posting_date__gte=start_date,
            entry__posting_date__lte=end_date,
        )
        .values("account_id")
        .annotate(
            signed_amount=Coalesce(
                Sum(movement),
                Value(Decimal("0")),
                output_field=DECIMAL_FIELD,
            )
        )
    )
    return {
        row["account_id"]: row["signed_amount"]
        for row in rows
    }


def _balance_by_account(
    *,
    organization,
    fiscal_year,
    as_of_date,
):
    movement = ExpressionWrapper(
        F("debit") - F("credit"),
        output_field=DECIMAL_FIELD,
    )

    rows = (
        JournalLine.objects.filter(
            entry__organization=organization,
            entry__period__fiscal_year=fiscal_year,
            entry__status__in=REPORT_STATUSES,
            entry__entry_type__in=BALANCE_ENTRY_TYPES,
            entry__posting_date__lte=as_of_date,
        )
        .values("account_id")
        .annotate(
            signed_amount=Coalesce(
                Sum(movement),
                Value(Decimal("0")),
                output_field=DECIMAL_FIELD,
            )
        )
    )
    return {
        row["account_id"]: row["signed_amount"]
        for row in rows
    }


def _statement_lines(definition, direct_amounts, comparative_amounts=None, synthetic=None, comparative_synthetic=None):
    lines = list(
        definition.lines.all()
        .select_related("parent")
        .order_by("order", "code")
    )

    by_id = {line.id: line for line in lines}
    children = defaultdict(list)
    for line in lines:
        children[line.parent_id].append(line)

    synthetic = synthetic or {}
    comparative_synthetic = comparative_synthetic or {}
    comparative_amounts = comparative_amounts or {}

    current_cache = {}
    comparative_cache = {}

    def amount_for(line, source, synth, cache):
        if line.id in cache:
            return cache[line.id]

        amount = source.get(line.id, Decimal("0")) + synth.get(
            line.code,
            Decimal("0"),
        )
        for child in children.get(line.id, []):
            amount += amount_for(child, source, synth, cache) * Decimal(child.sign)

        cache[line.id] = amount
        return amount

    output = []
    for line in lines:
        current = amount_for(line, direct_amounts, synthetic, current_cache)
        comparative = amount_for(
            line,
            comparative_amounts,
            comparative_synthetic,
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
                "order": line.order,
                "sign": line.sign,
                "is_total": line.is_total,
                "parent_id": line.parent_id,
                "depth": depth,
                "amount": current,
                "comparative_amount": comparative,
            }
        )

    return output


def previous_fiscal_year(*, organization, fiscal_year):
    return (
        FiscalYear.objects.filter(
            organization=organization,
            end_date__lt=fiscal_year.start_date,
        )
        .order_by("-end_date")
        .first()
    )


def _direct_amounts_from_mappings(mappings, account_amounts):
    direct = defaultdict(lambda: Decimal("0"))
    mapped_accounts = set()

    for mapping in mappings:
        signed = account_amounts.get(mapping.account_id, Decimal("0"))
        direct[mapping.statement_line_id] += (
            signed * Decimal(mapping.balance_multiplier)
        )
        mapped_accounts.add(mapping.account_id)

    return dict(direct), mapped_accounts


def _is_relevant_unmapped_account(account, statement_type):
    code = (account.code or "").strip()

    if statement_type == StatementDefinition.StatementType.INCOME_STATEMENT:
        return (
            account.account_type in {
                Account.AccountType.REVENUE,
                Account.AccountType.EXPENSE,
            }
            or code.startswith(("6", "7"))
        )

    if statement_type == StatementDefinition.StatementType.BALANCE_SHEET:
        return (
            account.account_type in {
                Account.AccountType.ASSET,
                Account.AccountType.LIABILITY,
                Account.AccountType.EQUITY,
            }
            or code.startswith(("1", "2", "3", "4", "5"))
        )

    return True


def _unmapped_accounts(
    organization,
    account_amounts,
    mapped_accounts,
    statement_type,
):
    nonzero_ids = {
        account_id
        for account_id, amount in account_amounts.items()
        if amount != Decimal("0")
    } - mapped_accounts

    accounts = Account.objects.filter(
        organization=organization,
        id__in=nonzero_ids,
    ).order_by("code")

    return [
        account
        for account in accounts
        if _is_relevant_unmapped_account(account, statement_type)
    ]


def build_income_statement(
    *,
    organization,
    fiscal_year,
    end_date=None,
    include_comparative=True,
):
    configuration = ensure_financial_statement_configuration(
        organization=organization
    )
    version = configuration.framework_version
    end_date = end_date or fiscal_year.end_date

    definition = StatementDefinition.objects.get(
        version=version,
        code=INCOME_DEFINITION_CODE,
    )

    mappings = list(
        _mapping_queryset(
            organization,
            version,
            StatementDefinition.StatementType.INCOME_STATEMENT,
        )
    )

    account_amounts = _movement_by_account(
        organization=organization,
        fiscal_year=fiscal_year,
        start_date=fiscal_year.start_date,
        end_date=end_date,
        entry_types=INCOME_ENTRY_TYPES,
    )
    direct, mapped_accounts = _direct_amounts_from_mappings(
        mappings,
        account_amounts,
    )

    comparative_year = None
    comparative_direct = {}
    if include_comparative and configuration.comparative_enabled:
        comparative_year = previous_fiscal_year(
            organization=organization,
            fiscal_year=fiscal_year,
        )
        if comparative_year:
            comparative_accounts = _movement_by_account(
                organization=organization,
                fiscal_year=comparative_year,
                start_date=comparative_year.start_date,
                end_date=comparative_year.end_date,
                entry_types=INCOME_ENTRY_TYPES,
            )
            comparative_direct, _ = _direct_amounts_from_mappings(
                mappings,
                comparative_accounts,
            )

    lines = _statement_lines(
        definition,
        direct,
        comparative_direct,
    )
    values = {line["code"]: line["amount"] for line in lines}
    comparative_values = {
        line["code"]: line["comparative_amount"]
        for line in lines
    }

    return {
        "definition": definition,
        "fiscal_year": fiscal_year,
        "end_date": end_date,
        "comparative_year": comparative_year,
        "lines": lines,
        "values": values,
        "comparative_values": comparative_values,
        "unmapped_accounts": _unmapped_accounts(
            organization,
            account_amounts,
            mapped_accounts,
            StatementDefinition.StatementType.INCOME_STATEMENT,
        ),
    }


def build_balance_sheet(
    *,
    organization,
    fiscal_year,
    as_of_date=None,
    include_comparative=True,
):
    configuration = ensure_financial_statement_configuration(
        organization=organization
    )
    version = configuration.framework_version
    as_of_date = as_of_date or fiscal_year.end_date

    definition = StatementDefinition.objects.get(
        version=version,
        code=BALANCE_DEFINITION_CODE,
    )
    mappings = list(
        _mapping_queryset(
            organization,
            version,
            StatementDefinition.StatementType.BALANCE_SHEET,
        )
    )

    account_amounts = _balance_by_account(
        organization=organization,
        fiscal_year=fiscal_year,
        as_of_date=as_of_date,
    )
    direct, mapped_accounts = _direct_amounts_from_mappings(
        mappings,
        account_amounts,
    )

    income = build_income_statement(
        organization=organization,
        fiscal_year=fiscal_year,
        end_date=as_of_date,
        include_comparative=False,
    )
    synthetic = {
        "BS_CURRENT_RESULT": income["values"].get(
            "IS_NET_INCOME",
            Decimal("0"),
        )
    }

    comparative_year = None
    comparative_direct = {}
    comparative_synthetic = {}

    if include_comparative and configuration.comparative_enabled:
        comparative_year = previous_fiscal_year(
            organization=organization,
            fiscal_year=fiscal_year,
        )
        if comparative_year:
            comparative_accounts = _balance_by_account(
                organization=organization,
                fiscal_year=comparative_year,
                as_of_date=comparative_year.end_date,
            )
            comparative_direct, _ = _direct_amounts_from_mappings(
                mappings,
                comparative_accounts,
            )
            comparative_income = build_income_statement(
                organization=organization,
                fiscal_year=comparative_year,
                end_date=comparative_year.end_date,
                include_comparative=False,
            )
            comparative_synthetic = {
                "BS_CURRENT_RESULT": comparative_income["values"].get(
                    "IS_NET_INCOME",
                    Decimal("0"),
                )
            }

    lines = _statement_lines(
        definition,
        direct,
        comparative_direct,
        synthetic=synthetic,
        comparative_synthetic=comparative_synthetic,
    )
    values = {line["code"]: line["amount"] for line in lines}
    comparative_values = {
        line["code"]: line["comparative_amount"]
        for line in lines
    }

    total_assets = values.get("BS_TOTAL_ASSETS", Decimal("0"))
    total_liab_equity = values.get(
        "BS_TOTAL_LIAB_EQUITY",
        Decimal("0"),
    )

    return {
        "definition": definition,
        "fiscal_year": fiscal_year,
        "as_of_date": as_of_date,
        "comparative_year": comparative_year,
        "lines": lines,
        "values": values,
        "comparative_values": comparative_values,
        "balance_gap": total_assets - total_liab_equity,
        "is_balanced": total_assets == total_liab_equity,
        "unmapped_accounts": _unmapped_accounts(
            organization,
            account_amounts,
            mapped_accounts,
            StatementDefinition.StatementType.BALANCE_SHEET,
        ),
    }


def _is_cash_account(account, prefixes):
    code = account.code or ""
    return any(code.startswith(prefix) for prefix in prefixes)


def _cash_flow_category(cash_lines, noncash_lines, infer_categories):
    explicit = {
        line.cash_flow_tag
        for line in cash_lines
        if line.cash_flow_tag in {
            JournalLine.CashFlowTag.OPERATING,
            JournalLine.CashFlowTag.INVESTING,
            JournalLine.CashFlowTag.FINANCING,
        }
    }
    if len(explicit) == 1:
        return explicit.pop(), "explicit"

    if not infer_categories:
        return "UNCLASSIFIED", "unclassified"

    if any(
        line.account.code.startswith("2")
        for line in noncash_lines
    ):
        return JournalLine.CashFlowTag.INVESTING, "inferred"

    if any(
        line.account.account_type in {
            Account.AccountType.EQUITY,
            Account.AccountType.LIABILITY,
        }
        and (
            line.account.code.startswith("1")
            or any(
                token in (line.account.name or "").upper()
                for token in ("EMPRUNT", "LOAN", "CAPITAL", "FINANCEMENT")
            )
        )
        for line in noncash_lines
    ):
        return JournalLine.CashFlowTag.FINANCING, "inferred"

    return JournalLine.CashFlowTag.OPERATING, "inferred"


def _cash_flow_values(
    *,
    organization,
    fiscal_year,
    start_date,
    end_date,
    prefixes,
    infer_categories,
):
    lines = list(
        JournalLine.objects.filter(
            entry__organization=organization,
            entry__period__fiscal_year=fiscal_year,
            entry__status__in=REPORT_STATUSES,
            entry__posting_date__gte=start_date,
            entry__posting_date__lte=end_date,
            entry__entry_type__in=(
                [JournalEntry.EntryType.OPENING]
                + CASH_FLOW_ENTRY_TYPES
            ),
        )
        .select_related(
            "entry",
            "account",
        )
        .order_by(
            "entry__posting_date",
            "entry_id",
            "line_number",
        )
    )

    grouped = defaultdict(list)
    for line in lines:
        grouped[line.entry_id].append(line)

    opening_cash = Decimal("0")
    operating = Decimal("0")
    investing = Decimal("0")
    financing = Decimal("0")
    unclassified = Decimal("0")
    inferred_count = 0
    explicit_count = 0
    transfer_count = 0

    for entry_lines in grouped.values():
        entry = entry_lines[0].entry
        cash_lines = [
            line
            for line in entry_lines
            if _is_cash_account(line.account, prefixes)
        ]
        if not cash_lines:
            continue

        net_cash = sum(
            (line.debit - line.credit for line in cash_lines),
            Decimal("0"),
        )

        if entry.entry_type == JournalEntry.EntryType.OPENING:
            opening_cash += net_cash
            continue

        if net_cash == Decimal("0"):
            transfer_count += 1
            continue

        noncash_lines = [
            line
            for line in entry_lines
            if not _is_cash_account(line.account, prefixes)
        ]

        category, source = _cash_flow_category(
            cash_lines,
            noncash_lines,
            infer_categories,
        )
        if source == "inferred":
            inferred_count += 1
        elif source == "explicit":
            explicit_count += 1

        if category == JournalLine.CashFlowTag.OPERATING:
            operating += net_cash
        elif category == JournalLine.CashFlowTag.INVESTING:
            investing += net_cash
        elif category == JournalLine.CashFlowTag.FINANCING:
            financing += net_cash
        else:
            unclassified += net_cash

    net_change = operating + investing + financing + unclassified
    ending_cash = opening_cash + net_change

    actual_cash = sum(
        (
            line.debit - line.credit
            for line in lines
            if _is_cash_account(line.account, prefixes)
            and line.entry.entry_type != JournalEntry.EntryType.CLOSING
        ),
        Decimal("0"),
    )

    return {
        "CF_OPENING_CASH": opening_cash,
        "CF_OPERATING": operating,
        "CF_INVESTING": investing,
        "CF_FINANCING": financing,
        "CF_NET_CHANGE": operating + investing + financing + unclassified,
        "CF_UNCLASSIFIED": unclassified,
        "CF_ENDING_CASH": ending_cash,
        "CF_RECONCILIATION_GAP": actual_cash - ending_cash,
        "unclassified_cash_flow": unclassified,
        "inferred_count": inferred_count,
        "explicit_count": explicit_count,
        "transfer_count": transfer_count,
        "actual_cash": actual_cash,
    }


def build_cash_flow_statement(
    *,
    organization,
    fiscal_year,
    end_date=None,
    include_comparative=True,
):
    configuration = ensure_financial_statement_configuration(
        organization=organization
    )
    version = configuration.framework_version
    end_date = end_date or fiscal_year.end_date
    prefixes = configuration.cash_account_prefixes or ["5"]

    definition = StatementDefinition.objects.get(
        version=version,
        code=CASH_FLOW_DEFINITION_CODE,
    )

    current_values = _cash_flow_values(
        organization=organization,
        fiscal_year=fiscal_year,
        start_date=fiscal_year.start_date,
        end_date=end_date,
        prefixes=prefixes,
        infer_categories=configuration.infer_cash_flow_categories,
    )

    comparative_year = None
    comparative_values = {}
    if include_comparative and configuration.comparative_enabled:
        comparative_year = previous_fiscal_year(
            organization=organization,
            fiscal_year=fiscal_year,
        )
        if comparative_year:
            comparative_values = _cash_flow_values(
                organization=organization,
                fiscal_year=comparative_year,
                start_date=comparative_year.start_date,
                end_date=comparative_year.end_date,
                prefixes=prefixes,
                infer_categories=configuration.infer_cash_flow_categories,
            )

    # Cash-flow lines are synthetic transaction classifications, not account mappings.
    lines = _statement_lines(
        definition,
        {},
        {},
        synthetic={
            code: value
            for code, value in current_values.items()
            if code.startswith("CF_") and code != "CF_NET_CHANGE"
        },
        comparative_synthetic={
            code: value
            for code, value in comparative_values.items()
            if code.startswith("CF_") and code != "CF_NET_CHANGE"
        },
    )

    values = {line["code"]: line["amount"] for line in lines}
    comparative_line_values = {
        line["code"]: line["comparative_amount"]
        for line in lines
    }

    return {
        "definition": definition,
        "fiscal_year": fiscal_year,
        "end_date": end_date,
        "comparative_year": comparative_year,
        "lines": lines,
        "values": values,
        "comparative_values": comparative_line_values,
        "unclassified_cash_flow": current_values["unclassified_cash_flow"],
        "inferred_count": current_values["inferred_count"],
        "explicit_count": current_values["explicit_count"],
        "transfer_count": current_values["transfer_count"],
        "actual_cash": current_values["actual_cash"],
        "cash_account_prefixes": prefixes,
    }


def _safe_divide(numerator, denominator):
    if not denominator:
        return None
    return numerator / denominator


def build_ratios(
    *,
    organization,
    fiscal_year,
    end_date=None,
):
    income = build_income_statement(
        organization=organization,
        fiscal_year=fiscal_year,
        end_date=end_date,
    )
    balance = build_balance_sheet(
        organization=organization,
        fiscal_year=fiscal_year,
        as_of_date=end_date,
    )
    cash_flow = build_cash_flow_statement(
        organization=organization,
        fiscal_year=fiscal_year,
        end_date=end_date,
    )

    iv = income["values"]
    bv = balance["values"]
    cv = cash_flow["values"]

    revenue = iv.get("IS_REVENUE", Decimal("0"))
    net_income = iv.get("IS_NET_INCOME", Decimal("0"))
    assets = bv.get("BS_TOTAL_ASSETS", Decimal("0"))
    current_assets = bv.get("BS_CURRENT_ASSETS", Decimal("0"))
    current_liabilities = bv.get(
        "BS_CURRENT_LIABILITIES",
        Decimal("0"),
    )
    noncurrent_liabilities = bv.get(
        "BS_NONCURRENT_LIABILITIES",
        Decimal("0"),
    )
    equity = (
        bv.get("BS_EQUITY", Decimal("0"))
        + bv.get("BS_CURRENT_RESULT", Decimal("0"))
    )
    cfo = cv.get("CF_OPERATING", Decimal("0"))

    ratios = [
        {
            "code": "NET_MARGIN",
            "label": "Marge nette",
            "value": _safe_divide(net_income, revenue),
            "format": "percent",
        },
        {
            "code": "ROA",
            "label": "Résultat net / actif total",
            "value": _safe_divide(net_income, assets),
            "format": "percent",
        },
        {
            "code": "CURRENT_RATIO",
            "label": "Ratio de liquidité générale",
            "value": _safe_divide(current_assets, current_liabilities),
            "format": "multiple",
        },
        {
            "code": "DEBT_TO_ASSETS",
            "label": "Passifs / actif total",
            "value": _safe_divide(
                current_liabilities + noncurrent_liabilities,
                assets,
            ),
            "format": "percent",
        },
        {
            "code": "EQUITY_RATIO",
            "label": "Capitaux propres / actif total",
            "value": _safe_divide(equity, assets),
            "format": "percent",
        },
        {
            "code": "CFO_TO_REVENUE",
            "label": "Flux opérationnel / chiffre d'affaires",
            "value": _safe_divide(cfo, revenue),
            "format": "percent",
        },
        {
            "code": "ASSET_TURNOVER",
            "label": "Chiffre d'affaires / actif total",
            "value": _safe_divide(revenue, assets),
            "format": "multiple",
        },
    ]

    return {
        "fiscal_year": fiscal_year,
        "ratios": ratios,
        "income_statement": income,
        "balance_sheet": balance,
        "cash_flow": cash_flow,
    }


def statement_line_account_ids(line):
    definition_lines = list(
        line.definition.lines.all().only(
            "id",
            "parent_id",
        )
    )
    children = defaultdict(list)
    for item in definition_lines:
        children[item.parent_id].append(item.id)

    descendant_ids = {line.id}
    queue = [line.id]
    while queue:
        current = queue.pop()
        for child_id in children.get(current, []):
            if child_id not in descendant_ids:
                descendant_ids.add(child_id)
                queue.append(child_id)

    return list(
        StatementAccountMapping.objects.filter(
            statement_line_id__in=descendant_ids,
        ).values_list("account_id", flat=True)
    )


@transaction.atomic
def update_financial_statement_configuration(
    *,
    configuration,
    comparative_enabled,
    infer_cash_flow_categories,
    cash_account_prefixes,
    user=None,
):
    configuration = FinancialStatementConfiguration.objects.select_for_update().get(
        pk=configuration.pk
    )
    before = {
        "comparative_enabled": configuration.comparative_enabled,
        "infer_cash_flow_categories": configuration.infer_cash_flow_categories,
        "cash_account_prefixes": configuration.cash_account_prefixes,
    }

    configuration.comparative_enabled = comparative_enabled
    configuration.infer_cash_flow_categories = infer_cash_flow_categories
    configuration.cash_account_prefixes = cash_account_prefixes
    configuration.save(
        update_fields=[
            "comparative_enabled",
            "infer_cash_flow_categories",
            "cash_account_prefixes",
            "updated_at",
        ]
    )

    if user:
        record_audit_event(
            organization=configuration.organization,
            actor=user,
            action="FINANCIAL_STATEMENTS_CONFIG_UPDATE",
            entity=configuration,
            before=before,
            after={
                "comparative_enabled": comparative_enabled,
                "infer_cash_flow_categories": infer_cash_flow_categories,
                "cash_account_prefixes": cash_account_prefixes,
            },
        )

    return configuration


def _manual_multiplier_for_account(account):
    if account.normal_balance == Account.NormalBalance.CREDIT:
        return -1
    return 1


@transaction.atomic
def update_statement_account_mapping(
    *,
    organization,
    account,
    statement_line,
    user=None,
):
    configuration = ensure_financial_statement_configuration(
        organization=organization,
        user=user,
    )
    version = configuration.framework_version

    if account.organization_id != organization.id:
        raise ValueError("Compte appartenant à une autre organisation.")

    if statement_line and statement_line.definition.version_id != version.id:
        raise ValueError("Rubrique appartenant à une autre version de présentation.")

    existing = list(
        StatementAccountMapping.objects.filter(
            account=account,
            statement_line__definition__version=version,
        ).select_related("statement_line")
    )
    before = [
        {
            "line": item.statement_line.code,
            "mapping_type": item.mapping_type,
            "multiplier": item.balance_multiplier,
        }
        for item in existing
    ]

    StatementAccountMapping.objects.filter(
        account=account,
        statement_line__definition__version=version,
    ).delete()

    created = None
    if statement_line:
        created = StatementAccountMapping.objects.create(
            account=account,
            statement_line=statement_line,
            balance_multiplier=_manual_multiplier_for_account(account),
            mapping_type=StatementAccountMapping.MappingType.MANUAL,
            confidence=Decimal("1.0000"),
            validated_by=user,
            validated_at=timezone.now() if user else None,
            notes="Mapping manuel Sprint 6.",
        )

    if user:
        record_audit_event(
            organization=organization,
            actor=user,
            action="STATEMENT_MAPPING_UPDATE",
            entity=account,
            before={"mappings": before},
            after={
                "statement_line": statement_line.code if statement_line else None,
                "multiplier": created.balance_multiplier if created else None,
            },
        )

    return created
