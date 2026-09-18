#!/usr/bin/env python3
"""Shared deterministic manifest rendering helpers."""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def project_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, indent=2) + "\n"


def write_or_check(*, filename: str, payload: dict[str, Any], check: bool) -> int:
    path = ROOT / filename
    rendered = render_json(payload)
    if check:
        if not path.is_file():
            print(f"{filename}: MISSING")
            return 1
        current = path.read_text(encoding="utf-8")
        if current != rendered:
            print(f"{filename}: DRIFT")
            return 1
        print(f"{filename}: OK")
        return 0

    path.write_text(rendered, encoding="utf-8")
    print(f"{filename}: WRITTEN")
    return 0


def parse_check_flag(description: str) -> bool:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when the committed manifest differs from deterministic generation.",
    )
    return bool(parser.parse_args().check)


__all__ = ["ROOT", "parse_check_flag", "project_version", "render_json", "write_or_check"]
