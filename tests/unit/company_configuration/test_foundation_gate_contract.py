"""FND-C07: a green gate-register validation is NOT a GO for promotion."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
EVIDENCE = REPO / "docs/company_configuration/evidence"
REGISTER = EVIDENCE / "FND_C07_GATE_REGISTER.json"
SCRIPT = REPO / "scripts/qualify_foundation_gates.py"
spec = importlib.util.spec_from_file_location("fnd_c07_validator", SCRIPT)
assert spec is not None and spec.loader is not None
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


@pytest.fixture
def register():
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def test_current_register_validates_but_is_explicitly_no_go(register):
    assert gate.validate_register(register) is register
    reasons = gate.pending_reasons(register)
    assert len(reasons) >= 5
    assert all(register["gates"][name]["status"] == "PENDING_REVIEW"
               for name in ("G0", "G1", "G2"))
    assert not register["promotion"]["merge_permitted"]
    assert not register["promotion"]["foundation_closed"]


def test_enforcement_rejects_unsigned_gates_before_any_network_call(register):
    with pytest.raises(gate.FoundationGateError, match="NO_GO"):
        gate.enforce(
            register, head_sha="a" * 40, token="not_a_real_token",
        )


@pytest.mark.parametrize("gate_name", ["G0", "G1", "G2"])
def test_cannot_forge_gate_approval_without_identity_or_commit(register, gate_name):
    corrupted = copy.deepcopy(register)
    corrupted["gates"][gate_name]["status"] = "APPROVED"
    with pytest.raises(gate.FoundationGateError, match="without reviewer/commit"):
        gate.validate_register(corrupted)


def test_pending_gate_cannot_claim_approval_metadata(register):
    corrupted = copy.deepcopy(register)
    corrupted["gates"]["G1"]["reviewer"] = "unverified-person"
    with pytest.raises(gate.FoundationGateError, match="unsigned"):
        gate.validate_register(corrupted)


def test_bogus_green_workflow_or_mismatched_head_is_denied(register):
    corrupted = copy.deepcopy(register)
    corrupted["workflows"][2]["conclusion"] = "failure"
    with pytest.raises(gate.FoundationGateError, match="Workflow list"):
        gate.validate_register(corrupted)
    corrupted = copy.deepcopy(register)
    corrupted["workflows"][2]["head_sha"] = "b" * 40
    with pytest.raises(gate.FoundationGateError, match="Workflow list"):
        gate.validate_register(corrupted)


def test_missing_fourth_workflow_or_duplicate_run_is_rejected(register):
    corrupted = copy.deepcopy(register)
    corrupted["workflows"].pop()
    with pytest.raises(gate.FoundationGateError, match="Four required"):
        gate.validate_register(corrupted)
    corrupted = copy.deepcopy(register)
    corrupted["workflows"][1]["run_id"] = corrupted["workflows"][0]["run_id"]
    with pytest.raises(gate.FoundationGateError, match="Workflow list"):
        gate.validate_register(corrupted)


def test_decision_files_must_exist_in_gate_directory(register):
    corrupted = copy.deepcopy(register)
    corrupted["gates"]["G2"]["decision_ref"] = "GATES/NO_FAKE_APPROVAL.md"
    with pytest.raises(gate.FoundationGateError, match="Missing or unsafe"):
        gate.validate_register(corrupted)
    corrupted = copy.deepcopy(register)
    corrupted["gates"]["G1"]["decision_ref"] = "GATES/../../secrets.md"
    with pytest.raises(gate.FoundationGateError, match="Missing or unsafe"):
        gate.validate_register(corrupted)


def test_no_premerge_claims_about_main_or_foundation_closure(register):
    corrupted = copy.deepcopy(register)
    corrupted["promotion"]["main_merged"] = True
    with pytest.raises(gate.FoundationGateError, match="Pre-merge register"):
        gate.validate_register(corrupted)
    corrupted = copy.deepcopy(register)
    corrupted["promotion"]["foundation_closed"] = True
    with pytest.raises(gate.FoundationGateError, match="Pre-merge register"):
        gate.validate_register(corrupted)


def test_approved_gate_with_unresolved_blockers_is_not_accepted(register):
    corrupted = copy.deepcopy(register)
    corrupted["gates"]["G0"].update(
        status="APPROVED", reviewer="claimed", approved_sha="a" * 40,
    )
    with pytest.raises(gate.FoundationGateError, match="blockers remain"):
        gate.validate_register(corrupted)


def test_approval_must_match_current_pr_head(register):
    changed = copy.deepcopy(register)
    changed["gates"]["G0"].update(
        status="APPROVED", reviewer="real-independent-reviewer",
        approved_sha="a" * 40, blockers=[],
    )
    gate.validate_register(changed)
    assert "G0: approval is not bound" in " ".join(
        gate.pending_reasons(changed, head_sha="b" * 40)
    )


def test_report_mode_names_no_go_even_with_valid_evidence_structure():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--mode", "report"],
        cwd=REPO, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert "promotion verdict: NO_GO" in result.stdout
    assert "G0:" in result.stdout and "G2:" in result.stdout


def test_strict_mode_fails_on_present_pr_head():
    result = subprocess.run(
        [
            sys.executable, str(SCRIPT), "--mode", "enforce",
            "--head-sha", "098f6de80b916d0545b65c2dfec9357f854cddcd",
        ],
        cwd=REPO, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert "NO_GO" in result.stderr


def _signed_candidate(register, head):
    data = copy.deepcopy(register)
    for key, reviewer in (
        ("G0", "architecture-reviewer"),
        ("G1", "domain-reviewer"),
        ("G2", "security-reviewer"),
    ):
        data["gates"][key].update(
            status="APPROVED", reviewer=reviewer, approved_sha=head, blockers=[],
        )
    data["promotion"]["merge_permitted"] = True
    data["external_controls"]["reviewers"] = True
    data["external_controls"]["branch_protection_verified"] = True
    gate.validate_register(data)
    return data


def test_live_github_reviews_must_apply_to_exact_head_not_prior_commit(
    register, monkeypatch,
):
    """A stale GitHub APPROVED review must not certify a newly changed SHA."""
    head = "a" * 40
    signed = _signed_candidate(register, head)

    def fake_get(path, *, token):
        assert token == "fake"
        if path.endswith("/pulls/32"):
            return {
                "head": {"sha": head}, "base": {"ref": "main"},
                "draft": False, "state": "open", "user": {"login": "owner"},
            }
        if "/reviews?" in path:
            return [
                {
                    "user": {"login": name},
                    "state": "APPROVED",
                    "commit_id": "b" * 40,
                }
                for name in ("architecture-reviewer", "domain-reviewer", "security-reviewer")
            ]
        raise AssertionError(f"stale review must stop before {path}")

    monkeypatch.setattr(gate, "_github_get", fake_get)
    with pytest.raises(gate.FoundationGateError, match="lacks live PR approval"):
        gate.enforce(signed, head_sha=head, token="fake")


def test_gate_enforcement_requires_four_live_workflows_and_protection(
    register, monkeypatch,
):
    head = "a" * 40
    signed = _signed_candidate(register, head)
    state = {"complete": False, "protected": False}

    def fake_get(path, *, token):
        assert token == "fake"
        if path.endswith("/pulls/32"):
            return {
                "head": {"sha": head}, "base": {"ref": "main"},
                "draft": False, "state": "open", "user": {"login": "owner"},
            }
        if "/reviews?" in path:
            return [
                {
                    "user": {"login": name}, "state": "APPROVED",
                    "commit_id": head,
                }
                for name in ("architecture-reviewer", "domain-reviewer", "security-reviewer")
            ]
        if "/actions/runs?" in path:
            names = sorted(gate.EXPECTED_WORKFLOWS)
            if not state["complete"]:
                names = names[:3]
            return {"workflow_runs": [
                {
                    "name": name, "status": "completed",
                    "conclusion": "success", "head_sha": head,
                }
                for name in names
            ]}
        if "/branches/main/protection" in path:
            if not state["protected"]:
                raise gate.FoundationGateError("GitHub protection unavailable")
            return {"required_pull_request_reviews": {}}
        raise AssertionError(path)

    monkeypatch.setattr(gate, "_github_get", fake_get)
    with pytest.raises(gate.FoundationGateError, match="Missing exact-head"):
        gate.enforce(signed, head_sha=head, token="fake")
    state["complete"] = True
    with pytest.raises(gate.FoundationGateError, match="protection unavailable"):
        gate.enforce(signed, head_sha=head, token="fake")
    state["protected"] = True
    gate.enforce(signed, head_sha=head, token="fake")
