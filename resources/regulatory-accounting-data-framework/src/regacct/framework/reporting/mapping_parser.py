from __future__ import annotations
import re


def normalize_account_expression(expr: str) -> str:
    return re.sub(r"(?<=\d)\s+(?=\d)", "", expr.strip())


def _split_top_level(expr: str, separator: str = "/") -> list[str]:
    out, buf, depth = [], [], 0
    for ch in expr:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(depth - 1, 0)
        if ch == separator and depth == 0:
            token = "".join(buf).strip()
            if token:
                out.append(token)
            buf = []
        else:
            buf.append(ch)
    token = "".join(buf).strip()
    if token:
        out.append(token)
    return out


def _parse_exclusions(text: str) -> dict:
    excludes = {"exclude_prefixes": [], "exclude_ranges": []}
    if not text:
        return excludes
    for part in re.split(r"[,;/]", text):
        part = part.strip().strip("()")
        if not part:
            continue
        m = re.fullmatch(r"(\d+)\s*(?:à|-)\s*(\d+)", part)
        if m:
            excludes["exclude_ranges"].append({"start": m.group(1), "end": m.group(2)})
        else:
            digits = re.sub(r"\D", "", part)
            if digits:
                excludes["exclude_prefixes"].append(digits)
    return excludes


def parse_selector(token: str) -> dict:
    token = token.strip()
    parenthetical = token.startswith("(") and token.endswith(")") and "sauf" not in token.lower()
    if parenthetical:
        token = token[1:-1].strip()

    exclusion_text = ""
    m_excl = re.search(r"\(\s*sauf\s+(.+?)\s*\)\s*$", token, flags=re.I)
    if m_excl:
        exclusion_text = m_excl.group(1)
        token = token[:m_excl.start()].strip()

    side = None
    if token.lower().endswith("dr"):
        side, token = "debit", token[:-2]
    elif token.lower().endswith("cr"):
        side, token = "credit", token[:-2]

    result = {"side": side, **_parse_exclusions(exclusion_text)}

    m_range = re.fullmatch(r"(\d+)\s*(?:à|-)\s*(\d+)", token)
    if m_range:
        result.update({"match_type": "range", "start": m_range.group(1), "end": m_range.group(2)})
        return result

    digits = re.sub(r"\s+", "", token)
    if digits.isdigit():
        result.update({"match_type": "prefix", "account_prefix": digits})
        if parenthetical:
            result["component_hint"] = "contra_asset_or_credit_component"
        return result

    result.update({"match_type": "unparsed", "raw": token})
    return result


def parse_mapping_expression(raw_expression: str) -> dict:
    normalized = normalize_account_expression(raw_expression)
    parts = _split_top_level(normalized)
    selectors = [parse_selector(p) for p in parts]
    return {
        "raw_expression": raw_expression,
        "normalized_expression": normalized,
        "selectors": selectors,
        "parse_status": "parsed" if selectors and all(s["match_type"] != "unparsed" for s in selectors)
                        else ("empty" if not selectors else "partial"),
    }


def account_matches_selector(account_code: str, net_side: str | None, selector: dict) -> bool:
    if selector.get("side") and net_side != selector["side"]:
        return False
    match_type = selector.get("match_type")
    if match_type == "prefix":
        matched = account_code.startswith(selector["account_prefix"])
    elif match_type == "range":
        # lexical numeric comparison is safe only after equal-length normalization
        width = max(len(selector["start"]), len(selector["end"]), len(account_code))
        a = account_code.ljust(width, "0")
        start = selector["start"].ljust(width, "0")
        end = selector["end"].ljust(width, "9")
        matched = start <= a <= end
    else:
        return False
    if not matched:
        return False
    if any(account_code.startswith(p) for p in selector.get("exclude_prefixes", [])):
        return False
    for rng in selector.get("exclude_ranges", []):
        width = max(len(rng["start"]), len(rng["end"]), len(account_code))
        a = account_code.ljust(width, "0")
        if rng["start"].ljust(width, "0") <= a <= rng["end"].ljust(width, "9"):
            return False
    return True
