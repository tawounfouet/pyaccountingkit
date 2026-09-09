from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class EvaluationResult:
    value: float | None
    missing_inputs: tuple[str, ...] = ()


def evaluate_ast(ast: dict, values: Mapping[str, float]) -> EvaluationResult:
    op = ast.get("op")
    if op == "literal":
        return EvaluationResult(float(ast["value"]))
    if op == "value":
        ref = ast["ref"]
        if ref not in values:
            return EvaluationResult(None, (ref,))
        return EvaluationResult(float(values[ref]))

    if op == "neg":
        inner = evaluate_ast(ast["value"], values)
        return EvaluationResult(None, inner.missing_inputs) if inner.missing_inputs else EvaluationResult(-inner.value)

    left = evaluate_ast(ast["left"], values)
    right = evaluate_ast(ast["right"], values)
    missing = tuple(dict.fromkeys(left.missing_inputs + right.missing_inputs))
    if missing:
        return EvaluationResult(None, missing)

    a, b = left.value, right.value
    if op == "add":
        return EvaluationResult(a + b)
    if op == "sub":
        return EvaluationResult(a - b)
    if op == "mul":
        return EvaluationResult(a * b)
    if op == "div":
        if b == 0:
            raise ZeroDivisionError("Prudential denominator is zero")
        return EvaluationResult(a / b)
    raise ValueError(f"Unsupported op: {op}")


def evaluate_threshold(value: float | None, threshold: dict) -> dict:
    if value is None:
        return {"status": "not_evaluated", "breach": None}
    if threshold.get("evaluation_status") not in (None, "ready"):
        return {"status": threshold["evaluation_status"], "breach": None}

    target = threshold.get("value")
    if target is None:
        return {"status": "missing_threshold_value", "breach": None}
    comp = threshold["comparator"]
    ok = {
        ">": value > target,
        ">=": value >= target,
        "<": value < target,
        "<=": value <= target,
        "==": value == target,
    }[comp]
    return {"status": "evaluated", "breach": not ok, "value": value, "threshold": target, "comparator": comp}
