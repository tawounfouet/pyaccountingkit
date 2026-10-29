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
