"""Fail-closed FND-C07 Foundation gate register and promotion preflight.

'check' validates provenance and documentation structure; successful execution
does NOT mean that the gates are approved. The default 'report' command always
prints an explicit gate verdict. 'enforce' additionally requires independent,
live GitHub review and exact-head CI evidence before allowing promotion.

This module never writes to GitHub and cannot merge a pull request.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

EVIDENCE_ROOT = Path(__file__).resolve().parents[1] / "docs/company_configuration/evidence"
EXPECTED_GATES = frozenset({"G0", "G1", "G2"})
EXPECTED_WORKFLOWS = frozenset({
    "Python CI",
    "PostgreSQL integration (L02 candidate)",
    "Company Configuration migration recovery (FND-C04)",
    "Company Configuration standalone Foundation artifact qualification (FND-C06)",
})
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class FoundationGateError(ValueError):
    """Gate register is invalid or promotion is missing required proof."""


def _sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or SHA_PATTERN.fullmatch(value) is None:
        raise FoundationGateError(f"{field} must be a 40-digit lowercase Git SHA")
    return value


def validate_register(data: Any, *, evidence_root: Path = EVIDENCE_ROOT) -> dict:
    """Check schema, pinned proof integrity and explicit fail-closed decisions."""
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise FoundationGateError("Unsupported FND-C07 gate register")
    if (data.get("repository") != "tawounfouet/pyaccountingkit"
            or data.get("integration_pr") != 32
            or data.get("scope") != "standalone-development-foundation"):
        raise FoundationGateError("Incorrect standalone repository/PR/scope")
    checkpoint = _sha(data.get("pre_merge_qualified_sha"), "qualified checkpoint")
    _sha(data.get("main_baseline_sha"), "main baseline")
    workflows = data.get("workflows")
    if not isinstance(workflows, list) or len(workflows) != 4:
        raise FoundationGateError("Four required exact-SHA workflow records expected")
    found = set()
    run_ids = set()
    for item in workflows:
        if not isinstance(item, dict):
            raise FoundationGateError("Invalid workflow proof entry")
        name = item.get("name")
        run_id = item.get("run_id")
        if (name not in EXPECTED_WORKFLOWS or name in found
                or type(run_id) is not int or run_id <= 0 or run_id in run_ids
                or item.get("conclusion") != "success"
                or _sha(item.get("head_sha"), "workflow SHA") != checkpoint):
            raise FoundationGateError("Workflow list is not exact, unique and successful")
        found.add(name)
        run_ids.add(run_id)
    if found != EXPECTED_WORKFLOWS:
        raise FoundationGateError("Missing required workflow proof")

    gates = data.get("gates")
    if not isinstance(gates, dict) or set(gates) != EXPECTED_GATES:
        raise FoundationGateError("Exactly G0, G1, G2 are required")
    for gate, value in gates.items():
        if not isinstance(value, dict) or value.get("status") not in (
            "PENDING_REVIEW", "APPROVED", "REJECTED",
        ):
            raise FoundationGateError(f"Invalid {gate} decision")
        relative = value.get("decision_ref")
        if (not isinstance(relative, str) or not relative.startswith("GATES/")
                or not relative.endswith(".md") or ".." in Path(relative).parts
                or not (evidence_root / relative).is_file()):
            raise FoundationGateError(f"Missing or unsafe {gate} decision reference")
        blockers = value.get("blockers")
        if not isinstance(blockers, list) or any(
            not isinstance(x, str) or not x.strip() for x in blockers
        ):
            raise FoundationGateError(f"Invalid {gate} blocker list")
        reviewer = value.get("reviewer")
        approved_sha = value.get("approved_sha")
        if value["status"] == "APPROVED":
            if (not isinstance(reviewer, str) or not reviewer.strip()
                    or approved_sha is None):
                raise FoundationGateError(f"{gate} GO without reviewer/commit proof")
            _sha(approved_sha, f"{gate} approved SHA")
            if blockers:
                raise FoundationGateError(f"{gate} approved while blockers remain")
        elif reviewer is not None or approved_sha is not None:
            raise FoundationGateError(f"{gate} unsigned decision claims approval metadata")

    controls = data.get("external_controls")
    if not isinstance(controls, dict) or not controls or any(
        type(value) is not bool for value in controls.values()
    ):
        raise FoundationGateError("External control evidence flags must be explicit")
    promotion = data.get("promotion")
    if not isinstance(promotion, dict) or set(promotion) != {
        "merge_permitted", "main_merged", "foundation_closed",
    } or any(type(value) is not bool for value in promotion.values()):
        raise FoundationGateError("Invalid promotion state")
    if promotion["main_merged"] or promotion["foundation_closed"]:
        raise FoundationGateError("Pre-merge register cannot claim post-merge success")
    if promotion["merge_permitted"] and any(
        gate["status"] != "APPROVED" for gate in gates.values()
    ):
        raise FoundationGateError("Merge permission cannot bypass a gate")
    return data


def pending_reasons(register: dict, *, head_sha: str | None = None) -> list[str]:
    """Local assessment; never interpret a documented proof as a live review."""
    reasons = []
    if head_sha is not None:
        _sha(head_sha, "current PR HEAD")
    for name, gate in register["gates"].items():
        if gate["status"] != "APPROVED":
            reasons.append(f"{name}: {gate['status']} ({', '.join(gate['blockers'])})")
        elif head_sha is not None and gate["approved_sha"] != head_sha:
            reasons.append(f"{name}: approval is not bound to current PR HEAD")
    if not register["promotion"]["merge_permitted"]:
        reasons.append("Promotion: merge_permitted=false")
    if not register["external_controls"].get("reviewers"):
        reasons.append("GitHub: independent code review not verified")
    if not register["external_controls"].get("branch_protection_verified"):
        reasons.append("GitHub: main protection requirements not verified")
    return reasons


def _github_get(path: str, *, token: str) -> Any:
    if not token:
        raise FoundationGateError("Live GitHub token required to enforce gates")
    request = Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "pyaccountingkit-fnd-c07-gate",
        },
    )
    try:
        with urlopen(request, timeout=12) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise FoundationGateError("GitHub evidence unavailable or unauthorized") from exc


def enforce(register: dict, *, head_sha: str, token: str) -> None:
    """Demand local decisions AND live, independent GitHub proof. Never merge."""
    _sha(head_sha, "current PR HEAD")
    reasons = pending_reasons(register, head_sha=head_sha)
    if reasons:
        raise FoundationGateError("NO_GO: " + "; ".join(reasons))
    repo = register["repository"]
    pr_number = register["integration_pr"]
    pr = _github_get(f"/repos/{repo}/pulls/{pr_number}", token=token)
    if (pr.get("head", {}).get("sha") != head_sha or pr.get("base", {}).get("ref") != "main"
            or pr.get("draft") is not False or pr.get("state") != "open"):
        raise FoundationGateError("Live PR is not an exact-head, reviewed main candidate")
    reviews = _github_get(f"/repos/{repo}/pulls/{pr_number}/reviews?per_page=100", token=token)
    author = pr.get("user", {}).get("login", "").lower()
    latest = {}
    for review in reviews:
        user = review.get("user", {}).get("login", "").lower()
        if user:
            latest[user] = (review.get("state"), review.get("commit_id"))
    verified = {
        user for user, (state, review_sha) in latest.items()
        if state == "APPROVED" and review_sha == head_sha and user != author
    }
    if not verified:
        raise FoundationGateError("No independent live GitHub approval on the PR")
    for name, gate in register["gates"].items():
        if gate["reviewer"].lower() not in verified:
            raise FoundationGateError(f"{name} reviewer lacks live PR approval")
    runs = _github_get(
        f"/repos/{repo}/actions/runs?head_sha={head_sha}&per_page=100", token=token
    )
    completed = {
        run.get("name") for run in runs.get("workflow_runs", [])
        if run.get("head_sha") == head_sha and run.get("status") == "completed"
        and run.get("conclusion") == "success"
    }
    if not EXPECTED_WORKFLOWS.issubset(completed):
        raise FoundationGateError("Missing exact-head live CI successes")
    _github_get(f"/repos/{repo}/branches/main/protection", token=token)
    if not register["external_controls"].get("branch_protection_verified"):
        raise FoundationGateError("Branch protection evidence not independently recorded")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FND-C07 pre-merge gate register check")
    parser.add_argument(
        "--register", type=Path,
        default=EVIDENCE_ROOT / "FND_C07_GATE_REGISTER.json",
    )
    parser.add_argument("--mode", choices=("report", "enforce"), default="report")
    parser.add_argument("--head-sha", help="Exact current PR head for enforcement")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.register.read_text(encoding="utf-8"))
        register = validate_register(data, evidence_root=args.register.parent)
        reasons = pending_reasons(register, head_sha=args.head_sha)
        if args.mode == "report":
            print("FND-C07 gate register: SCHEMA / EVIDENCE STRUCTURE VALID")
            print("FND-C07 promotion verdict: NO_GO" if reasons else
                  "FND-C07 local register claims readiness; verify live evidence")
            for reason in reasons:
                print(f"  BLOCKED: {reason}")
            return 0  # Green check means only that the register is truthful/parseable!
        if args.head_sha is None:
            raise FoundationGateError("Exact current PR HEAD required for enforcement")
        enforce(register, head_sha=args.head_sha, token=os.getenv("GITHUB_TOKEN", ""))
        print("FND-C07: independent live gate evidence verified, merge still manual")
        return 0
    except (FoundationGateError, OSError, json.JSONDecodeError) as exc:
        print(f"FND-C07: NO_GO — {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
