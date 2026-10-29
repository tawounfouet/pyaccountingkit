"""Cheap, explicit protection against importing infrastructure into domain."""

import ast
from pathlib import Path


def test_domain_does_not_import_frameworks_or_io():
    root = Path(__file__).parents[3] / "src/pyaccountingkit/company_configuration/domain"
    forbidden = {"sqlalchemy", "django", "fastapi", "requests", "httpx", "psycopg",
                 "sqlite3", "socket", "subprocess"}
    files = list(root.rglob("*.py"))
    assert files
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        imports += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import)
                    for a in n.names]
        assert all((name or "").split(".")[0] not in forbidden for name in imports), path


def test_application_ports_do_not_depend_on_infrastructure_adapters():
    """Hexagonal dependency rule: application never imports PostgreSQL or IAM IO."""
    app = Path(__file__).parents[3] / "src/pyaccountingkit/company_configuration/application"
    files = list(app.rglob("*.py"))
    assert files
    forbidden = {
        "infrastructure", "psycopg", "django", "sqlalchemy", "httpx",
        "requests", "socket", "subprocess",
    }
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        modules = [
            n.module for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and n.module
        ]
        modules.extend(
            alias.name for n in ast.walk(tree)
            if isinstance(n, ast.Import) for alias in n.names
        )
        for module in modules:
            assert not (set(module.split(".")) & forbidden), (path, module)


def test_domain_does_not_depend_on_application_or_infrastructure():
    """DDD boundary: aggregates and value objects cannot depend on services."""
    root = Path(__file__).parents[3] / "src/pyaccountingkit/company_configuration/domain"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = [
            n.module for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and n.module
        ]
        imports.extend(
            alias.name for n in ast.walk(tree)
            if isinstance(n, ast.Import) for alias in n.names
        )
        for module in imports:
            assert not (set(module.split(".")) & {"application", "infrastructure"}), (
                path, module
            )
