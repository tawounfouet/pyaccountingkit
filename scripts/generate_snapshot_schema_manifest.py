#!/usr/bin/env python3
"""Generate the deterministic public snapshot-schema compatibility manifest."""

from __future__ import annotations

import argparse
import json
import tomllib
from dataclasses import fields
from enum import StrEnum
from pathlib import Path
from typing import Any

from pyaccountingkit.domain.analysis.analysis_snapshot import AnalysisSnapshot
from pyaccountingkit.domain.references.snapshots import EffectivePlanSnapshot, ReferenceSnapshot
from pyaccountingkit.domain.reporting.report_snapshot import (
    ReportSnapshot,
    ReportSnapshotFreshness,
    ReportSnapshotLine,
    ReportSnapshotStatus,
)
from pyaccountingkit.domain.reporting.trial_balance import TrialBalance, TrialBalanceSnapshot

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "SNAPSHOT_SCHEMA_MANIFEST.json"

_SNAPSHOT_TYPES = (
    AnalysisSnapshot,
    EffectivePlanSnapshot,
    ReferenceSnapshot,
    ReportSnapshot,
    ReportSnapshotLine,
    TrialBalance,
)

_ENUM_TYPES = (
    ReportSnapshotFreshness,
    ReportSnapshotStatus,
    TrialBalanceSnapshot,
)


def project_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _annotation_name(annotation: object) -> str:
    if isinstance(annotation, str):
        return annotation
    return str(annotation).replace("typing.", "")


def _dataclass_contract(model: type[object]) -> dict[str, Any]:
    params = getattr(model, "__dataclass_params__", None)
    return {
        "module": model.__module__,
        "frozen": bool(params and params.frozen),
        "slots": hasattr(model, "__slots__"),
        "fields": [
            {
                "name": field.name,
                "type": _annotation_name(field.type),
            }
            for field in fields(model)
        ],
    }


def _enum_contract(enum_type: type[StrEnum]) -> dict[str, Any]:
    return {
        "module": enum_type.__module__,
        "values": [member.value for member in enum_type],
    }


def manifest_payload(version: str | None = None) -> dict[str, Any]:
    release = version or project_version()
    return {
        "schema_version": "1",
        "version": release,
        "snapshots": {
            model.__name__: _dataclass_contract(model)
            for model in sorted(_SNAPSHOT_TYPES, key=lambda item: item.__name__)
        },
        "enums": {
            enum_type.__name__: _enum_contract(enum_type)
            for enum_type in sorted(_ENUM_TYPES, key=lambda item: item.__name__)
        },
    }


def render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    expected = render(manifest_payload())
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            print("SNAPSHOT_SCHEMA_MANIFEST.json: STALE")
            return 1
        print("SNAPSHOT_SCHEMA_MANIFEST.json: OK")
        return 0

    OUTPUT.write_text(expected, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
