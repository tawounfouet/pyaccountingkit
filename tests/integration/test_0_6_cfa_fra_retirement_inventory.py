"""Contract tests for the CFA FRA legacy-retirement inventory."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from pyaccountingkit.integrations.cfa_fra import ORACLE_TREE_SHA

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "tests" / "consumer" / "cfa_fra" / "LEGACY_RETIREMENT_INVENTORY.json"


def _payload() -> dict[str, object]:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def test_retirement_inventory_is_bound_to_frozen_oracle_and_live_consumer() -> None:
    payload = _payload()

    assert payload["oracle"]["tree_sha"] == ORACLE_TREE_SHA
    assert payload["policy"] == {
        "snapshot_is_immutable": True,
        "applies_to": "live-consumer-equivalents",
        "retirement_requires_mig13_ready": True,
    }


def test_retirement_inventory_uses_every_required_disposition() -> None:
    payload = _payload()
    components = payload["components"]
    counts = Counter(item["disposition"] for item in components)

    assert counts["RETIRE_ENGINE"] > 0
    assert counts["REWIRE_CONSUMER"] > 0
    assert counts["MIGRATE_PERSISTENCE"] > 0
    assert counts["KEEP_CONSUMER"] > 0
    assert counts["FROZEN_ORACLE"] > 0


def test_retirement_inventory_never_deletes_django_ui_or_frozen_oracle() -> None:
    payload = _payload()
    components = payload["components"]

    for item in components:
        path = item["path"]
        disposition = item["disposition"]
        if path.endswith(("views.py", "forms.py")):
            assert disposition != "RETIRE_ENGINE"
        if disposition == "FROZEN_ORACLE":
            assert "/tests/" in path
