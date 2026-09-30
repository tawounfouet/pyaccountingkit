"""Integrity checks for the sealed CFA FRA LOT-25 evidence baseline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

from pyaccountingkit.integrations.cfa_fra import (
    ORACLE_MANIFEST_VERSION,
    ORACLE_TREE_SHA,
    load_golden_fixture,
)

ROOT = Path(__file__).resolve().parents[3]
CFA_DIR = Path(__file__).parent
FIXTURES = CFA_DIR / "fixtures"


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    payload = f"blob {len(content)}\0".encode() + content
    return hashlib.sha1(payload, usedforsecurity=False).hexdigest()


def test_baseline_manifest_pins_oracle_documents_and_fixture_checksums() -> None:
    raw = json.loads((CFA_DIR / "BASELINE.json").read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    baseline = cast(dict[str, object], raw)
    oracle = cast(dict[str, str], baseline["oracle"])
    assert oracle["tree_sha"] == ORACLE_TREE_SHA
    assert oracle["manifest_version"] == ORACLE_MANIFEST_VERSION

    documents = cast(dict[str, dict[str, str]], baseline["evidence_documents"])
    for relative_path, evidence in documents.items():
        assert _git_blob_sha(ROOT / relative_path) == evidence["git_blob_sha"]

    fixtures = cast(dict[str, dict[str, str]], baseline["fixtures"])
    for filename, evidence in fixtures.items():
        fixture = load_golden_fixture(FIXTURES / filename)
        assert fixture.scenario_id == evidence["scenario_id"]
        assert fixture.checksum == evidence["semantic_checksum"]


def test_closing_gap_is_explicit_and_does_not_fabricate_parity() -> None:
    raw = json.loads((CFA_DIR / "BASELINE.json").read_text(encoding="utf-8"))
    closing = cast(dict[str, str], raw["closing_evidence"])
    assert closing["status"] == "DOCUMENTED_ORACLE_GAP"
    assert closing["claim"].startswith("No executable CFA FRA closing parity")
