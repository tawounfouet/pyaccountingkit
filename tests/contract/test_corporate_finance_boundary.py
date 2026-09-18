"""Architecture guard keeping Corporate Finance concepts outside analysis core."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_IDENTIFIERS = {
    "dcf",
    "discounted_cash_flow",
    "financing_optimization",
    "forecast_cash_flow",
    "investment_appraisal",
    "irr",
    "monte_carlo",
    "npv",
    "valuation",
    "wacc",
}


def test_analysis_core_does_not_expose_corporate_finance_runtime_vocabulary() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "pyaccountingkit" / "domain" / "analysis"
    violations: list[str] = []

    for path in sorted(root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: tuple[str, ...] = ()
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                names = (node.name,)
            elif isinstance(node, ast.Name):
                names = (node.id,)
            elif isinstance(node, ast.Attribute):
                names = (node.attr,)
            elif isinstance(node, ast.Import):
                names = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names = tuple(
                    item
                    for item in ((node.module or ""), *(alias.name for alias in node.names))
                    if item
                )
            for name in names:
                normalized = name.lower()
                if any(
                    normalized == forbidden
                    or normalized.startswith(f"{forbidden}_")
                    or normalized.endswith(f"_{forbidden}")
                    for forbidden in FORBIDDEN_IDENTIFIERS
                ):
                    violations.append(f"{path.name}:{name}")

    assert violations == []
