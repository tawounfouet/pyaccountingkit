"""FND-C05: architectural boundaries as executable dependency contracts.

DDD / Hexagonal / Dependency Inversion: Domain and Application never depend
on Infrastructure, PostgreSQL, IAM adapters or delivery transport providers.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "src/pyaccountingkit/company_configuration"
FRAMEWORKS = frozenset({
    "psycopg", "sqlalchemy", "django", "fastapi", "requests", "httpx",
    "sqlite3", "socket", "subprocess",
})


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, 0
        elif isinstance(node, ast.ImportFrom):
            yield node.module or "", node.level


def test_domain_has_no_upstream_application_infrastructure_or_external_io():
    files = list((ROOT / "domain").rglob("*.py"))
    assert files
    for path in files:
        for module, level in _imports(path):
            fragments = module.split(".")
            assert fragments[0] not in FRAMEWORKS, (path, module)
            assert "infrastructure" not in fragments, (path, module)
            assert "application" not in fragments, (path, module)
            assert level < 3 or not module.startswith("infrastructure"), (path, module)


def test_application_depends_on_domain_ports_and_stdlib_not_infrastructure():
    files = list((ROOT / "application").rglob("*.py"))
    assert files
    for path in files:
        for module, _ in _imports(path):
            fragments = module.split(".")
            assert fragments[0] not in FRAMEWORKS, (path, module)
            assert "infrastructure" not in fragments, (path, module)
            assert "adapters" not in fragments, (path, module)
