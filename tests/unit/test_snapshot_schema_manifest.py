"""Tests for deterministic snapshot-schema compatibility evidence."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "generate_snapshot_schema_manifest.py"


def _load_module() -> ModuleType:
    name = "pyaccountingkit_snapshot_schema_manifest_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_committed_snapshot_schema_manifest_matches_generator() -> None:
    module = _load_module()
    committed = json.loads((ROOT / "SNAPSHOT_SCHEMA_MANIFEST.json").read_text(encoding="utf-8"))

    assert committed == module.manifest_payload()
    assert committed["schema_version"] == "1"
    assert set(committed["snapshots"]) == {
        "AnalysisSnapshot",
        "EffectivePlanSnapshot",
        "ReferenceSnapshot",
        "ReportSnapshot",
        "ReportSnapshotLine",
        "TrialBalance",
    }


def test_snapshot_manifest_tracks_replay_relevant_enums() -> None:
    payload = _load_module().manifest_payload()

    assert payload["enums"]["TrialBalanceSnapshot"]["values"] == [
        "BEFORE_ADJUSTMENTS",
        "ADJUSTED",
        "POST_CLOSING",
    ]
    assert payload["enums"]["ReportSnapshotStatus"]["values"] == [
        "DRAFT",
        "VALIDATED",
        "PUBLISHED",
        "SUPERSEDED",
    ]
