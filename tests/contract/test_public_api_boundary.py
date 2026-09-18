"""GAPI contract tests for LOT-21 public API isolation and root imports."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from pyaccountingkit import AccountingApplication, CommandContext, Currency, CurrencyCode, Money

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "src" / "pyaccountingkit" / "public"


def test_public_package_never_imports_optional_orm_frameworks() -> None:
    forbidden = ("django", "sqlalchemy")
    violations: list[str] = []
    for path in sorted(PUBLIC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            for module in modules:
                if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden):
                    violations.append(f"{path.relative_to(ROOT)} imports {module}")
    assert not violations, "\n".join(violations)


def test_core_only_import_does_not_import_django_or_sqlalchemy() -> None:
    script = (
        "import sys; import pyaccountingkit; "
        "bad=[name for name in sys.modules if name.split('.',1)[0] in {'django','sqlalchemy'}]; "
        "assert not bad, bad; "
        "assert pyaccountingkit.AccountingApplication; assert pyaccountingkit.Money"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_package_root_exports_intentional_consumer_primitives() -> None:
    assert AccountingApplication
    assert CommandContext
    assert Currency
    assert CurrencyCode
    assert Money
