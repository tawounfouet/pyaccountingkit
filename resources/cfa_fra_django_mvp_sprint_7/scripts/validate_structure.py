from pathlib import Path
import ast
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "manage.py",
    "docker-compose.yml",
    "entrypoint.sh",

    "apps/referentials/models.py",
    "apps/referentials/migrations/0003_sprint7_regulatory_statement_fields.py",
    "apps/referentials/management/commands/seed_regulatory_framework.py",

    "apps/financial_statements/models.py",
    "apps/financial_statements/regulatory.py",
    "apps/financial_statements/regulatory_views.py",
    "apps/financial_statements/forms.py",
    "apps/financial_statements/urls.py",
    "apps/financial_statements/migrations/0002_sprint7_regulatory_profiles.py",
    "apps/financial_statements/tests/test_sprint7_regulatory_exports.py",

    "apps/reporting/models.py",
    "apps/reporting/migrations/0002_sprint7_regulatory_snapshot_type.py",

    "apps/exports/models.py",
    "apps/exports/services.py",
    "apps/exports/views.py",
    "apps/exports/urls.py",
    "apps/exports/migrations/0002_sprint7_regulatory_exports.py",

    "templates/financial_statements/regulatory/list.html",
    "templates/financial_statements/regulatory/detail.html",
    "templates/financial_statements/regulatory/mappings.html",
    "templates/exports/list.html",
    "templates/exports/detail.html",

    "docs/REGULATORY_FRAMEWORK_SCHEMA.md",
    "examples/regulatory_framework_template.json",
    "SPRINT_7_README.md",
]

missing = [item for item in REQUIRED if not (ROOT / item).exists()]
if missing:
    print("Missing required files:")
    for item in missing:
        print(" -", item)
    sys.exit(1)

syntax_errors = []
for path in ROOT.rglob("*.py"):
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        syntax_errors.append((path, exc))

if syntax_errors:
    for path, exc in syntax_errors:
        print(f"Syntax error: {path}: {exc}")
    sys.exit(1)

regulatory = (
    ROOT / "apps/financial_statements/regulatory.py"
).read_text(encoding="utf-8")
exports = (
    ROOT / "apps/exports/services.py"
).read_text(encoding="utf-8")
ref_models = (
    ROOT / "apps/referentials/models.py"
).read_text(encoding="utf-8")
export_models = (
    ROOT / "apps/exports/models.py"
).read_text(encoding="utf-8")
seed = (
    ROOT / "apps/referentials/management/commands/_seed_framework.py"
).read_text(encoding="utf-8")
pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

semantic_checks = {
    "regulatory_profile_model": "class RegulatoryStatementProfile" in (
        ROOT / "apps/financial_statements/models.py"
    ).read_text(encoding="utf-8"),
    "regulatory_mapping_model": "class RegulatoryStatementLineMapping" in (
        ROOT / "apps/financial_statements/models.py"
    ).read_text(encoding="utf-8"),
    "statement_regulatory_metadata": (
        "is_required = models.BooleanField" in ref_models
        and "standard_reference = models.CharField" in ref_models
        and "metadata = models.JSONField" in ref_models
    ),
    "auto_mapping": "def auto_map_regulatory_profile" in regulatory,
    "manual_mapping": "def update_regulatory_mapping" in regulatory,
    "regulatory_package": "def build_regulatory_package" in regulatory,
    "balance_validation": '"BALANCE_EQUATION"' in regulatory,
    "cash_validation": '"CASH_RECONCILIATION"' in regulatory,
    "rich_seed_schema": "statements = payload.get" in seed,
    "snapshot": "def create_regulatory_snapshot" in exports,
    "xlsx_export": "def _xlsx_bytes" in exports,
    "pdf_export": "def _pdf_bytes" in exports,
    "csv_export": "def _csv_bytes" in exports,
    "json_export": "def _json_bytes" in exports,
    "sha256_export": "hashlib.sha256(content)" in exports,
    "download_view": "class ExportDownloadView" in (
        ROOT / "apps/exports/views.py"
    ).read_text(encoding="utf-8"),
    "export_snapshot_fk": "snapshot = models.ForeignKey" in export_models,
    "xlsx_dependency": "XlsxWriter" in pyproject,
    "reportlab_dependency": "reportlab" in pyproject,
}

failed = [name for name, ok in semantic_checks.items() if not ok]
if failed:
    print("Failed semantic checks:")
    for name in failed:
        print(" -", name)
    sys.exit(1)

print(
    f"Structure Sprint 7 OK — "
    f"{len(list(ROOT.rglob('*.py')))} Python files parsed; "
    f"{len(semantic_checks)} semantic checks passed."
)
