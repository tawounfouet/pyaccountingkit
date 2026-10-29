"""FND-C07: static integrity of the *unsigned* gate decision record.

This does NOT authenticate a GitHub reviewer, fetch external approvals, approve
an ADR, or substitute for branch protection. Default mode validates the record
and prints HOLD. --require-go fails closed until all independent gates have
attributable approval metadata, then still requires external review verification.
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "docs/company_configuration/evidence/gates"
REPO = "tawounfouet/pyaccountingkit"
GATES = ("G0", "G1", "G2")
SHA = re.compile(r"^[0-9a-f]{40}$")


class GateDossierError(ValueError):
    """Governance evidence cannot be accepted as a valid decision record."""


def validate_manifest(data: dict, *, dossier_dir: Path = DOSSIER) -> bool:
    """Validate internally consistent metadata; return true only if all gates claim GO.

    Metadata-based GO is NOT independently verifiable approval: the PR reviewer
    must separately inspect actual GitHub review and signer authority.
    """
    if (
        not isinstance(data, dict)
        or data.get("schema_version") != 1
        or data.get("repository") != REPO
        or data.get("scope") != "standalone-development-only"
        or data.get("observed_pr") != 33
        or not isinstance(data.get("observed_candidate_sha"), str)
        or not SHA.fullmatch(data["observed_candidate_sha"])
    ):
        raise GateDossierError("Unrecognized repository, scope or candidate SHA")

    ci = data.get("evidence")
    if not isinstance(ci, dict) or set(ci) != {
        "python_ci", "postgres_ci", "migration_ci", "packaging_ci"
    }:
        raise GateDossierError("Four distinct CI evidence references are mandatory")
    for name, url in ci.items():
        if (
            not isinstance(url, str)
            or not url.startswith(f"https://github.com/{REPO}/actions/runs/")
            or not url.rsplit("/", 1)[-1].isdigit()
        ):
            raise GateDossierError(f"Invalid CI evidence URL for {name}")

    gates = data.get("gates")
    if not isinstance(gates, dict) or set(gates) != set(GATES):
        raise GateDossierError("Exactly G0, G1 and G2 are required")
    all_go = True
    for gate in GATES:
        detail = gates[gate]
        if not isinstance(detail, dict) or detail.get("dossier") != f"{gate}_DECISION.md":
            raise GateDossierError(f"Missing decision dossier for {gate}")
        if not (dossier_dir / detail["dossier"]).is_file():
            raise GateDossierError(f"Decision document unavailable for {gate}")
        state = detail.get("state")
        if state not in ("PENDING_REVIEW", "NO_GO", "GO"):
            raise GateDossierError(f"Unknown {gate} decision state")
        reviewer = detail.get("reviewer")
        review_sha = detail.get("reviewed_sha")
        decision_url = detail.get("decision_url")
        if state == "GO":
            if (
                not isinstance(reviewer, str) or not reviewer.strip()
                or review_sha != data["observed_candidate_sha"]
                or not isinstance(decision_url, str)
                or not decision_url.startswith(f"https://github.com/{REPO}/")
            ):
                raise GateDossierError(f"Unsigned, stale or unauditable {gate} GO")
        elif reviewer is not None or review_sha is not None or decision_url is not None:
            raise GateDossierError(f"{gate} is not GO, but has approval metadata")
        all_go &= state == "GO"

    integration = data.get("integration")
    if (
        not isinstance(integration, dict)
        or integration.get("dossier") != "INTEGRATION_DECISION.md"
        or not (dossier_dir / integration["dossier"]).is_file()
    ):
        raise GateDossierError("Missing integration decision document")
    status = integration.get("state")
    if status not in ("HOLD", "AUTHORIZED"):
        raise GateDossierError("Invalid integration status")
    if status == "AUTHORIZED":
        if not all_go:
            raise GateDossierError("Cannot authorize integration with a pending gate")
        if (
            integration.get("reviewed_sha") != data["observed_candidate_sha"]
            or not isinstance(integration.get("pr_review_url"), str)
            or not integration["pr_review_url"].startswith(
                f"https://github.com/{REPO}/pull/33"
            )
        ):
            raise GateDossierError("No attributable PR #33 approval on exact SHA")
    elif any(integration.get(key) is not None for key in (
        "pr_review_url", "reviewed_sha", "merged_main_sha", "post_merge_ci_url"
    )):
        raise GateDossierError("HOLD state cannot claim review, merge or release")

    if integration.get("merged_main_sha") is not None:
        raise GateDossierError("This pre-merge dossier cannot claim a main merge")
    if integration.get("post_merge_ci_url") is not None:
        raise GateDossierError("Pre-merge gate record cannot claim post-merge CI")

    return all_go and status == "AUTHORIZED"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-go", action="store_true")
    args = parser.parse_args()
    with (DOSSIER / "decision_manifest.json").open(encoding="utf-8") as stream:
        evidence = json.load(stream)
    approved_metadata = validate_manifest(evidence)
    if args.require_go:
        if not approved_metadata:
            raise SystemExit(
                "HOLD: no approved G0/G1/G2 + PR review; main merge prohibited"
            )
        raise SystemExit(
            "Metadata claims GO, but reviewer authorization MUST be externally "
            "verified on GitHub; this script cannot authorize merging"
        )
    print(
        "PASS FND-C07 static dossier integrity: "
        + ("GO metadata present; independent review still required"
           if approved_metadata else "HOLD; G0/G1/G2 unsigned; no main merge")
    )


if __name__ == "__main__":
    main()
