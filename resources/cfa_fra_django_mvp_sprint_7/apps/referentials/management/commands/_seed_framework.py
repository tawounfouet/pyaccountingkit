import json
from pathlib import Path

from django.core.management.base import CommandError
from django.db import transaction

from apps.referentials.models import (
    AccountingFramework,
    FrameworkAccount,
    FrameworkVersion,
    StatementDefinition,
    StatementLine,
)


VALID_STATEMENT_TYPES = {
    StatementDefinition.StatementType.BALANCE_SHEET,
    StatementDefinition.StatementType.INCOME_STATEMENT,
    StatementDefinition.StatementType.CASH_FLOW,
    StatementDefinition.StatementType.EQUITY_CHANGES,
}


def _seed_accounts(version, accounts):
    by_code = {}

    for item in accounts:
        if "code" not in item or "name" not in item:
            raise CommandError("Chaque compte doit contenir 'code' et 'name'.")

        account, _ = FrameworkAccount.objects.update_or_create(
            version=version,
            code=str(item["code"]),
            defaults={
                "name": item["name"],
                "name_en": item.get("name_en", ""),
                "account_type": item.get("account_type", ""),
                "normal_balance": item.get("normal_balance", ""),
                "current_noncurrent": item.get("current_noncurrent", ""),
                "statement": item.get("statement", ""),
                "statement_section": item.get("statement_section", ""),
                "standard_reference": item.get("standard_reference", ""),
                "metadata": item.get("metadata", {}),
            },
        )
        by_code[account.code] = account

    for item in accounts:
        parent_code = str(item.get("parent_code") or "")
        if parent_code and parent_code in by_code:
            account = by_code[str(item["code"])]
            account.parent = by_code[parent_code]
            account.save(update_fields=["parent", "updated_at"])

    return len(accounts)


def _seed_statements(version, statements):
    statement_count = 0
    line_count = 0

    for item in statements:
        statement_type = item.get("statement_type")
        if statement_type not in VALID_STATEMENT_TYPES:
            raise CommandError(
                f"Type d'état invalide pour {item.get('code')}: {statement_type}"
            )

        if "code" not in item or "name" not in item:
            raise CommandError(
                "Chaque définition d'état doit contenir 'code' et 'name'."
            )

        definition, _ = StatementDefinition.objects.update_or_create(
            version=version,
            code=str(item["code"]),
            defaults={
                "name": item["name"],
                "statement_type": statement_type,
            },
        )
        statement_count += 1

        lines = item.get("lines", [])
        by_code = {}

        for position, line_data in enumerate(lines, start=1):
            if "code" not in line_data or "label" not in line_data:
                raise CommandError(
                    f"Ligne invalide dans {item['code']}: code/label obligatoires."
                )

            line, _ = StatementLine.objects.update_or_create(
                definition=definition,
                code=str(line_data["code"]),
                defaults={
                    "label": line_data["label"],
                    "order": line_data.get("order", position * 10),
                    "sign": line_data.get("sign", 1),
                    "is_total": line_data.get("is_total", False),
                    "is_required": line_data.get("is_required", False),
                    "standard_reference": line_data.get(
                        "standard_reference",
                        "",
                    ),
                    "metadata": line_data.get("metadata", {}),
                },
            )
            by_code[line.code] = line
            line_count += 1

        for line_data in lines:
            parent_code = str(line_data.get("parent_code") or "")
            line = by_code[str(line_data["code"])]
            parent = by_code.get(parent_code)
            expected_parent_id = parent.id if parent else None
            if line.parent_id != expected_parent_id:
                line.parent = parent
                line.save(update_fields=["parent", "updated_at"])

    return statement_count, line_count


def seed_framework(
    *,
    path: str,
    framework_code: str,
    framework_name: str,
    version_name: str,
):
    file_path = Path(path)
    if not file_path.exists():
        raise CommandError(f"Fichier introuvable: {file_path}")

    payload = json.loads(file_path.read_text(encoding="utf-8"))

    # Backward compatible schema: a bare list still means "accounts only".
    if isinstance(payload, list):
        accounts = payload
        statements = []
        metadata = {}
    elif isinstance(payload, dict):
        accounts = payload.get("accounts", [])
        statements = payload.get("statements", [])
        metadata = payload.get("framework", {})

        framework_code = metadata.get("code", framework_code)
        framework_name = metadata.get("name", framework_name)
        version_name = metadata.get("version", version_name)
    else:
        raise CommandError(
            "Le JSON doit être une liste de comptes ou un objet "
            "{framework, accounts, statements}."
        )

    if not isinstance(accounts, list) or not isinstance(statements, list):
        raise CommandError("'accounts' et 'statements' doivent être des listes.")

    with transaction.atomic():
        framework, _ = AccountingFramework.objects.update_or_create(
            code=framework_code,
            defaults={
                "name": framework_name,
                "description": metadata.get("description", ""),
                "is_active": metadata.get("is_active", True),
            },
        )
        version, _ = FrameworkVersion.objects.update_or_create(
            framework=framework,
            version=version_name,
            defaults={
                "effective_from": metadata.get("effective_from") or None,
                "effective_to": metadata.get("effective_to") or None,
                "source_url": metadata.get("source_url", ""),
                "is_current": metadata.get("is_current", True),
            },
        )

        account_count = _seed_accounts(version, accounts)
        statement_count, line_count = _seed_statements(
            version,
            statements,
        )

    return {
        "accounts": account_count,
        "statements": statement_count,
        "statement_lines": line_count,
        "framework": framework.code,
        "version": version.version,
    }
