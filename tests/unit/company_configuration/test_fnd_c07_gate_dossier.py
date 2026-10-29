"""FND-C07: no unsigned or stale GO can pass the gate-record validator."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.check_foundation_gate_dossier import (
    DOSSIER,
    GateDossierError,
    validate_manifest,
)


@pytest.fixture
def manifest():
    with (DOSSIER / "decision_manifest.json").open(encoding="utf-8") as stream:
        return json.load(stream)


def test_current_gate_evidence_is_well_formed_but_not_approved(manifest):
    assert validate_manifest(manifest) is False
    assert all(manifest["gates"][gate]["state"] == "PENDING_REVIEW"
               for gate in ("G0", "G1", "G2"))
    assert manifest["integration"]["state"] == "HOLD"


def test_cli_validation_succeeds_without_claiming_go():
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [sys.executable, "scripts/check_foundation_gate_dossier.py"],
        cwd=root, capture_output=True, text=True, check=True,
    )
    assert "HOLD" in result.stdout and "unsigned" in result.stdout


def test_cli_require_go_fails_closed_while_reviews_missing():
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [sys.executable, "scripts/check_foundation_gate_dossier.py", "--require-go"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "main merge prohibited" in (result.stderr + result.stdout)


@pytest.mark.parametrize("mutation", [
    lambda m: m.update(repository="unexpected/fork"),
    lambda m: m.update(observed_candidate_sha="invalid-sha"),
    lambda m: m["evidence"].pop("postgres_ci"),
    lambda m: m["gates"]["G1"].update(state="GO"),
    lambda m: m["gates"]["G0"].update(reviewer="invented-person"),
    lambda m: m["integration"].update(state="AUTHORIZED"),
    lambda m: m["integration"].update(merged_main_sha="a" * 40),
])
def test_forged_or_incomplete_gate_claims_are_rejected(manifest, mutation):
    data = copy.deepcopy(manifest)
    mutation(data)
    with pytest.raises(GateDossierError):
        validate_manifest(data)


def test_metadata_go_without_external_review_still_cannot_authorize_merge(manifest):
    # Even syntactically complete self-asserted metadata is NOT an independent
    # GitHub review. The --require-go CLI deliberately refuses to sign off.
    data = copy.deepcopy(manifest)
    for gate in ("G0", "G1", "G2"):
        data["gates"][gate].update(
            state="GO", reviewer=f"claimed-reviewer-{gate}",
            reviewed_sha=data["observed_candidate_sha"],
            decision_url="https://github.com/tawounfouet/pyaccountingkit/pull/33",
        )
    data["integration"].update(
        state="AUTHORIZED",
        reviewed_sha=data["observed_candidate_sha"],
        pr_review_url="https://github.com/tawounfouet/pyaccountingkit/pull/33",
    )
    assert validate_manifest(data) is True  # document consistency only!
