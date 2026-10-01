"""Tests for deterministic CFA FRA standalone consumer bootstrap."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    ORACLE_TREE_SHA,
    ConsumerBootstrapError,
    apply_live_consumer_bootstrap,
    plan_live_consumer_bootstrap,
)

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "resources" / "cfa_fra_django_mvp_sprint_7"


def test_plan_matches_frozen_oracle_contract() -> None:
    plan = plan_live_consumer_bootstrap(SOURCE, source_tree_sha=ORACLE_TREE_SHA)

    assert plan.source_tree_sha == ORACLE_TREE_SHA
    assert plan.source_manifest_version == "0.8.0"
    assert plan.source_project_version == "0.8.0"
    assert plan.framework_requirement == "pyaccountingkit>=0.6.0b25,<0.7"
    assert plan.source_file_count > 100
    assert len(plan.bootstrap_sha256) == 64


def test_bootstrap_copies_without_mutating_oracle(tmp_path: Path) -> None:
    source_pyproject = (SOURCE / "pyproject.toml").read_bytes()
    source_settings = (SOURCE / "config" / "settings" / "base.py").read_bytes()
    plan = plan_live_consumer_bootstrap(SOURCE, source_tree_sha=ORACLE_TREE_SHA)
    target = tmp_path / "consumer"

    result = apply_live_consumer_bootstrap(SOURCE, target, plan)

    assert (SOURCE / "pyproject.toml").read_bytes() == source_pyproject
    assert (SOURCE / "config" / "settings" / "base.py").read_bytes() == source_settings
    assert '"pyaccountingkit>=0.6.0b25,<0.7"' in (target / "pyproject.toml").read_text()
    settings = (target / "config" / "settings" / "base.py").read_text()
    assert 'LOGIN_REDIRECT_URL = "analytics:dashboard"' in settings
    manifest = json.loads(result.manifest_path.read_text())
    assert manifest["source"]["oracle_tree_sha"] == ORACLE_TREE_SHA
    assert manifest["binding_state"] == "UNBOUND_UNTIL_PUBLISHED"
    assert manifest["cutover_state"] == "NOT_STARTED"


def test_bootstrap_rejects_wrong_oracle_sha() -> None:
    with pytest.raises(ConsumerBootstrapError, match="tree SHA"):
        plan_live_consumer_bootstrap(SOURCE, source_tree_sha="0" * 40)


def test_bootstrap_rejects_existing_destination(tmp_path: Path) -> None:
    plan = plan_live_consumer_bootstrap(SOURCE, source_tree_sha=ORACLE_TREE_SHA)
    target = tmp_path / "consumer"
    target.mkdir()

    with pytest.raises(ConsumerBootstrapError, match="already exists"):
        apply_live_consumer_bootstrap(SOURCE, target, plan)


def test_bootstrap_rejects_destination_inside_oracle() -> None:
    plan = plan_live_consumer_bootstrap(SOURCE, source_tree_sha=ORACLE_TREE_SHA)

    with pytest.raises(ConsumerBootstrapError, match="inside frozen oracle"):
        apply_live_consumer_bootstrap(SOURCE, SOURCE / "generated-consumer", plan)
