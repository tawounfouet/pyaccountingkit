#!/usr/bin/env python3
"""Validate active release documentation and local Markdown references."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_DOCS = (
    ROOT / "README.md",
    ROOT / "CHANGELOG.md",
    ROOT / "docs" / "plans" / "README.md",
    ROOT / "docs" / "plans" / "LOT-27_REGULATORY_PRODUCTION_QUALIFICATION_PLAN.md",
)
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def project_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _local_link_violations(path: Path, text: str) -> list[str]:
    violations: list[str] = []
    for raw_target in LINK_PATTERN.findall(text):
        target = raw_target.strip().split("#", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            violations.append(
                f"{path.relative_to(ROOT)}: broken local Markdown link {raw_target!r}"
            )
    return violations


def documentation_violations() -> list[str]:
    version = project_version()
    violations: list[str] = []
    texts: dict[Path, str] = {}

    for path in ACTIVE_DOCS:
        if not path.is_file():
            violations.append(f"active documentation missing: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        texts[path] = text
        violations.extend(_local_link_violations(path, text))

    readme = texts.get(ROOT / "README.md", "")
    changelog = texts.get(ROOT / "CHANGELOG.md", "")
    plans_index = texts.get(ROOT / "docs" / "plans" / "README.md", "")
    lot27 = texts.get(
        ROOT / "docs" / "plans" / "LOT-27_REGULATORY_PRODUCTION_QUALIFICATION_PLAN.md",
        "",
    )

    if f"PyAccountingKit **{version}**" not in readme:
        violations.append("README status must match pyproject version")
    if f"## [{version}]" not in changelog:
        violations.append("CHANGELOG must contain the active project version")
    if version not in plans_index:
        violations.append("active plans index must mention the project version")
    if f"**Current slice:** `{version}`" not in lot27:
        violations.append("LOT-27 current slice must match pyproject version")
    if "## Deferred slices" in lot27:
        violations.append("LOT-27 may not classify its current slice as deferred")
    return violations


def main() -> int:
    violations = documentation_violations()
    if violations:
        print("Documentation validation: FAIL", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    print("Documentation validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
