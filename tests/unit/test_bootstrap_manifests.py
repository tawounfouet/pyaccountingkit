"""Tests for versioned bootstrap manifests."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_SPECS = (
    ("PUBLIC_API_MANIFEST.json", "public_api", dict),
    ("PUBLIC_ERROR_CODES.json", "error_codes", dict),
    ("ADAPTER_CONTRACT_MANIFEST.json", "adapter_contracts", dict),
    ("REGULATORY_COMPATIBILITY_MATRIX.json", "regulatory_frameworks", list),
)


def _project_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


@pytest.mark.parametrize(("filename", "payload_key", "payload_type"), MANIFEST_SPECS)
def test_bootstrap_manifest_contract(
    filename: str,
    payload_key: str,
    payload_type: type[dict] | type[list],
) -> None:
    """Each public manifest is parseable, version-aligned, typed and empty at 0.0.1."""
    path = ROOT / filename
    assert path.is_file(), f"missing manifest: {filename}"

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["version"] == _project_version() == "0.0.1"
    assert isinstance(payload[payload_key], payload_type)
    assert not payload[payload_key]


def test_manifest_set_is_complete() -> None:
    """The bootstrap exposes exactly the four governed root manifests."""
    expected = {filename for filename, _, _ in MANIFEST_SPECS}
    actual = {path.name for path in ROOT.glob("*.json") if path.name in expected}
    assert actual == expected
