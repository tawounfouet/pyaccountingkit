"""L04-08 — executable R&D evidence/ADR drift guards, never a G4 approval.

Tests cross-check checked-in specs and test files against a machine-readable
inventory. They do NOT validate real IAM, external normative truth or live SQL.
"""

import ast
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "company_configuration"
REGISTER = BASE / "L04_08_ADR_REGISTER.json"


@pytest.fixture(scope="module")
def register():
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def test_registry_is_versioned_parseable_and_evidence_complete(register):
    assert register["schema"] == "pyaccountingkit.company_configuration.l04_adr_register.v1"
    assert register["as_of"] == "2026-10-30"
    assert register["baseline"]["stacked_draft_prs"] == list(range(74, 81))
    assert register["baseline"]["l04_07_head_sha"] == (
        "2d0b2e67592e4aa90ec58c73c0a3336cf9d0ce81"
    )
    slices = register["evidence_slices"]
    assert [item["milestone"] for item in slices] == [
        f"L04-{index:02d}" for index in range(1, 8)
    ]
    assert [item["draft_pr"] for item in slices] == list(range(74, 81))
    assert all(
        item["qualification"] == "RND_TECHNICALLY_QUALIFIED_NOT_RELEASED"
        for item in slices
    )


def test_every_l04_slice_has_real_nonempty_source_and_test_file(register):
    for slice_info in register["evidence_slices"]:
        for field in ("spec_file", "test_file"):
            relative = Path(slice_info[field])
            assert not relative.is_absolute()
            assert ".." not in relative.parts
            path = ROOT / relative
            assert path.is_file(), f"Missing {slice_info['milestone']} {field}: {relative}"
            assert path.stat().st_size > 100
            if field == "test_file":
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source)
                assert any(
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name.startswith("test_")
                    for node in tree.body
                ), slice_info["milestone"]


def test_canonical_book_and_temporality_adr_ids_are_exactly_once(register):
    decisions = register["decisions"]
    ids = [item["id"] for item in decisions]
    assert len(ids) == len(set(ids)) == 24
    assert {x for x in ids if x.startswith("BOOK-ADR-")} == {
        f"BOOK-ADR-{index:02d}" for index in range(1, 11)
    }
    assert {x for x in ids if x.startswith("TMP-ADR-")} == {
        f"TMP-ADR-{index:02d}" for index in range(1, 11)
    }
    assert {
        "L04-NORM-AUTH-01", "L04-DEP-CARD-01",
        "L04-C10-CONTRACT-01", "SEC-G3-71",
    } == set(ids) - {
        *(f"BOOK-ADR-{index:02d}" for index in range(1, 11)),
        *(f"TMP-ADR-{index:02d}" for index in range(1, 11)),
    }


def test_book_adr03_is_multi_book_not_normative_provider_alias(register):
    decisions = {entry["id"]: entry for entry in register["decisions"]}
    assert "Multi-book" in decisions["BOOK-ADR-03"]["question"]
    assert "normative provider" not in decisions["BOOK-ADR-03"]["question"].lower()
    assert "reference" in decisions["BOOK-ADR-07"]["question"].lower()
    corrections = register["canonical_id_corrections"]
    assert "NOT normative registry authority" in corrections["BOOK-ADR-03"]
    assert "NEW local placeholder" in corrections["L04-NORM-AUTH-01"]
    assert "BOOK-ADR-03" not in decisions["L04-NORM-AUTH-01"]["id"]


def test_no_go_signature_or_approval_is_invented_in_registry(register):
    gates = register["gate_assertions"]
    assert [gates[key] for key in ("G0", "G1", "G2")] == [
        "PENDING_REVIEW", "PENDING_REVIEW", "PENDING_REVIEW"
    ]
    assert gates["G3"] == "HOLD_SECURITY"
    assert gates["G4"] == "NOT_APPROVED"
    assert gates["C10"] == "NOT_IMPLEMENTED"
    for entry in register["decisions"]:
        assert entry["decision_status"] == (
            "BLOCKED_HOLD_SECURITY" if entry["id"] == "SEC-G3-71"
            else "OPEN_UNAPPROVED"
        )
        assert entry["signed_decision_ref"] is None
        assert entry["proposed_owner_role"]
        assert entry["canonical_spec"]
    assert register["constraints"] == [
        "NO_MERGE_NO_RELEASE",
        "NO_SQL_MIGRATION_OR_PRIVILEGED_ISSUER",
        "NO_C10_PUBLISHED_READ_RECEIPT",
        "NO_IAM_OR_LEGAL_ATTESTATION_FROM_TEST_FAKES",
        "NO_LEDGER_POSTING_OR_ACCOUNT_ELIGIBILITY",
        "SHA256_CHECKSUM_IS_NOT_SIGNATURE",
    ]


def test_consolidation_and_l05_handoff_acknowledge_explicit_stop(register):
    consolidated = BASE / "L04_08_ACCOUNTING_BOOKS_RND_CONSOLIDATION_AND_DECISIONS.md"
    handoff = BASE / "L04_08_L05_CHART_OF_ACCOUNTS_HANDOFF.md"
    a = consolidated.read_text(encoding="utf-8")
    b = handoff.read_text(encoding="utf-8")
    assert "BOOK-ADR-03" in a and "Multi-books" in a
    assert "G3" in a and "HOLD_SECURITY" in a and "#71" in a
    assert "L04_08_ADR_REGISTER.json" in a
    assert "L05-01" in b and "AccountCode" in b
    assert "C10-Q05" in b
    assert "NO_SQL_MIGRATION_OR_PRIVILEGED_ISSUER" in register["constraints"]


def test_l04_rnd_components_do_not_import_live_sql_or_http_clients():
    modules = (
        ROOT / "src" / "pyaccountingkit" / "company_configuration"
    )
    paths = (
        list((modules / "domain" / "accounting_books").glob("*.py"))
        + list((modules / "application").glob("accounting_book*.py"))
        + list((modules / "infrastructure").glob("accounting_book*.py"))
    )
    assert len(paths) >= 15
    forbidden = {"psycopg", "sqlalchemy", "django", "requests", "httpx"}
    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden, path
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                assert node.module.split(".")[0] not in forbidden, path
        assert "organization_issuer_gateway" not in source, path


def test_no_publish_or_post_surface_exists_in_l04_rnd_facades():
    folder = ROOT / "src" / "pyaccountingkit" / "company_configuration"
    for path in (folder / "application").glob("accounting_book*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and (
                node.name.endswith("Service") or node.name.endswith("PreviewService")
            ):
                methods = {
                    x.name for x in node.body if isinstance(x, ast.FunctionDef)
                }
                assert not {"publish", "post", "activate", "approve"} & methods, path


def test_original_foundation_sql_lineage_is_unchanged_by_this_static_slice():
    migrations = (
        ROOT / "src" / "pyaccountingkit" / "company_configuration"
        / "infrastructure" / "postgres" / "migrations"
    )
    existing = sorted(migrations.glob("*.sql"))
    assert len(existing) == 14
    assert not list(migrations.glob("0030*.sql"))
