#!/usr/bin/env python3
"""Validate PyAccountingKit architecture and bootstrap boundaries."""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "src" / "pyaccountingkit"

ISOLATED_LAYERS = ("core", "domain", "ports")
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "django",
    "fastapi",
    "flask",
    "psycopg",
    "requests",
    "sqlalchemy",
    "pyaccountingkit.adapters",
    "pyaccountingkit.application",
    "pyaccountingkit.integrations",
    "pyaccountingkit.public",
)


def project_version() -> str:
    """Return the canonical version declared in pyproject.toml."""
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def imports_from(tree: ast.AST) -> list[str]:
    """Extract absolute import module names from an AST."""
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def boundary_violations() -> list[str]:
    """Return forbidden imports found in isolated architecture layers."""
    violations: list[str] = []
    for layer in ISOLATED_LAYERS:
        directory = PACKAGE_ROOT / layer
        for path in sorted(directory.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for imported in imports_from(tree):
                for forbidden in FORBIDDEN_IMPORT_PREFIXES:
                    if imported == forbidden or imported.startswith(f"{forbidden}."):
                        rel = path.relative_to(PACKAGE_ROOT)
                        violations.append(f"{rel}: forbidden import {imported}")
    return violations


def bootstrap_scaffold_violations() -> list[str]:
    """Ensure 0.0.1 contains no premature executable business modules."""
    if project_version() != "0.0.1":
        return []

    violations: list[str] = []
    root_init = PACKAGE_ROOT / "__init__.py"
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        if path == root_init:
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        body = list(tree.body)
        if body and isinstance(body[0], ast.Expr):
            value = body[0].value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                body = body[1:]

        executable = []
        for node in body:
            is_future_import = isinstance(node, ast.ImportFrom) and node.module == "__future__"
            if not is_future_import:
                executable.append(type(node).__name__)

        if executable:
            rel = path.relative_to(PACKAGE_ROOT)
            kinds = ", ".join(executable)
            violations.append(f"{rel}: executable bootstrap nodes present: {kinds}")

    return violations


def root_surface_violations() -> list[str]:
    """Ensure the bootstrap package root does not expose business symbols."""
    if project_version() != "0.0.1":
        return []

    path = PACKAGE_ROOT / "__init__.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            violations.append(f"__init__.py: premature public symbol {node.name}")
    return violations


def main() -> int:
    """Run all architecture checks and return a process exit code."""
    if not PACKAGE_ROOT.is_dir():
        print(f"ARCHITECTURE ERROR: package root missing: {PACKAGE_ROOT}", file=sys.stderr)
        return 1

    violations = [
        *boundary_violations(),
        *bootstrap_scaffold_violations(),
        *root_surface_violations(),
    ]

    if violations:
        print("Architecture validation: FAIL", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    source_modules = sum(1 for _ in PACKAGE_ROOT.rglob("*.py"))
    print("Architecture validation: PASS")
    print(f"Project version: {project_version()}")
    print(f"Source modules inspected: {source_modules}")
    print(f"Isolated layers: {', '.join(ISOLATED_LAYERS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
