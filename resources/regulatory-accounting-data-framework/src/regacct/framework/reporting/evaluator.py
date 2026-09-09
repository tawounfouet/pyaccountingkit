from __future__ import annotations
from .mapping_parser import account_matches_selector


def net_balance(row: dict) -> tuple[float, str | None]:
    debit = float(row.get("debit_balance", 0) or 0)
    credit = float(row.get("credit_balance", 0) or 0)
    net = debit - credit
    if net > 0:
        return net, "debit"
    if net < 0:
        return -net, "credit"
    return 0.0, None


def evaluate_selectors(trial_balance: list[dict], selectors: list[dict], default_side: str | None = None) -> float:
    total = 0.0
    for row in trial_balance:
        code = str(row["account_code"])
        amount, side = net_balance(row)
        effective_side = side or default_side
        if any(account_matches_selector(code, effective_side, s) for s in selectors):
            total += amount
    return total
