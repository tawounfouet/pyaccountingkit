"""Tests for fail-closed LOT-00 final qualification status."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_lot00_remediation_status.py"
STATUS = ROOT / "docs" / "audits" / "LOT_00_REMEDIATION_STATUS.json"


def _load_validator() -> ModuleType:
    name = "pyaccountingkit_lot00_status_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _status() -> dict[str, object]:
    data = json.loads(STATUS.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_current_lot00_remediation_status_is_internally_consistent() -> None:
    """The checked-in status record must be truthful even while externally blocked."""
    module = _load_validator()
    assert module.status_violations() == []
    assert module.main([]) == 0


def test_require_complete_fails_while_main_protection_is_unenforced() -> None:
    """Repository qualification cannot be promoted while the external blocker remains."""
    module = _load_validator()
    assert module.main(["--require-complete"]) == 2


def test_unprotected_main_cannot_be_marked_complete() -> None:
    """A false COMPLETE state is rejected when branch protection is observed false."""
    module = _load_validator()
    data = copy.deepcopy(_status())
    data["overall_status"] = "COMPLETE"
    sublots = data["sublots"]
    assert isinstance(sublots, list)
    final = next(
        item for item in sublots if isinstance(item, dict) and item.get("id") == "LOT-00.9"
    )
    final["status"] = "COMPLETE"

    violations = module.validate_status_data(data)

    assert any("cannot be COMPLETE" in item for item in violations)
    assert any("LOT-00.9 must be BLOCKED_EXTERNAL_CONTROL" in item for item in violations)


def test_completed_sublot_cannot_silently_regress() -> None:
    """LOT-00.1 through LOT-00.8 remain immutable completion evidence."""
    module = _load_validator()
    data = copy.deepcopy(_status())
    sublots = data["sublots"]
    assert isinstance(sublots, list)
    first = next(
        item for item in sublots if isinstance(item, dict) and item.get("id") == "LOT-00.4"
    )
    first["status"] = "PENDING"

    violations = module.validate_status_data(data)
    assert any("LOT-00.4 must remain COMPLETE" in item for item in violations)


def test_release_claims_cannot_be_invented_by_final_qualification() -> None:
    """LOT-00.9 does not create a tag, publication or stable-release claim."""
    module = _load_validator()
    data = copy.deepcopy(_status())
    claims = data["release_claims"]
    assert isinstance(claims, dict)
    claims["stable_0_7_0_claimed_by_lot_00_9"] = True

    violations = module.validate_status_data(data)
    assert any("release_claims" in item for item in violations)


def test_missing_evidence_file_is_rejected(tmp_path: Path) -> None:
    """Versioned audit references cannot silently point to missing evidence."""
    module = _load_validator()
    data = copy.deepcopy(_status())
    sublots = data["sublots"]
    assert isinstance(sublots, list)
    item = next(
        sublot for sublot in sublots if isinstance(sublot, dict) and sublot.get("id") == "LOT-00.8"
    )
    item["evidence_files"] = ["docs/audits/does-not-exist.md"]

    violations = module.validate_status_data(data, root=tmp_path)
    assert any("evidence file missing" in violation for violation in violations)
