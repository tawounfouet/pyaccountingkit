"""L05-06: executable source-traced R&D evidence register and no-GO guards.

An inventory check is NOT independent IAM, Accounting or governance approval.
"""

import ast
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs" / "company_configuration"
REGISTER = DOCS / "L05_06_COA_RND_EVIDENCE_AND_ADR_REGISTER.json"


@pytest.fixture(scope="module")
def evidence():
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def test_register_is_parseable_versioned_and_exactly_based_on_draft_parent(evidence):
    assert evidence["schema"] == "pyaccountingkit.company_configuration.l05_rnd_gap_register.v1"
    assert evidence["as_of"] == "2026-10-31"
    assert evidence["scope_label"] == "RND_STATIC_EVIDENCE_CATALOG_NOT_PRODUCTION_SIGNOFF"
    base = evidence["baseline"]
    assert base["base_main_sha"] == "acdee98ca2736d79e17174f510ac767defd90db8"
    assert base["parent_l05_05_pr"] == 86
    assert base["parent_head_sha"] == "191a9429239b88a064029cfb1869d8c16ac77be4"
    assert base["stacked_draft_prs"] == [82, 83, 84, 85, 86]
    assert base["sql_migrations_unchanged_count"] == 14
    assert base["package_version_status"] == "0.0.0_UNPUBLISHED_PLACEHOLDER"


def test_all_five_real_l05_slices_point_to_existing_specs_and_unit_tests(evidence):
    records = evidence["evidence_slices"]
    assert [item["milestone"] for item in records] == [
        "L05-01", "L05-02", "L05-03", "L05-04", "L05-05"
    ]
    assert [item["draft_pr"] for item in records] == [82, 83, 84, 85, 86]
    assert len({item["qualified_head_sha"] for item in records}) == 5
    for item in records:
        assert item["qualification"] == "RND_TECHNICALLY_QUALIFIED_NOT_RELEASED"
        for key in ("spec_file", "test_file"):
            relative = Path(item[key])
            assert not relative.is_absolute() and ".." not in relative.parts
            path = ROOT / relative
            assert path.is_file(), f"Missing {item['milestone']}: {relative}"
            assert path.stat().st_size > 200
            if key == "test_file":
                tree = ast.parse(path.read_text(encoding="utf-8"))
                assert any(
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name.startswith("test_")
                    for node in tree.body
                ), item["milestone"]


def test_all_ten_source_canonical_coa_adrs_are_open_and_unsigned(evidence):
    entries = evidence["canonical_adrs"]
    assert len(entries) == 10
    assert [entry["id"] for entry in entries] == [
        f"ADR-COA-{i:02d}" for i in range(1, 11)
    ]
    assert "Propriété du chart" == entries[0]["question"]
    assert "Granularité des agrégats" == entries[1]["question"]
    assert "Mapping 1:N" == entries[4]["question"]
    assert "Priorité des mappings" == entries[5]["question"]
    assert "Gestion de la couverture" == entries[7]["question"]
    for entry in entries:
        assert entry["source_section"] == "13 §21"
        assert entry["decision_status"] == "OPEN_UNAPPROVED"
        assert entry["selected_option"] is None
        assert entry["signed_decision_ref"] is None
        assert entry["options"] and entry["proposed_owner_role"]


def test_all_eighteen_source_invariants_have_truthful_local_or_missing_status(evidence):
    entries = evidence["source_invariants"]
    assert len(entries) == 18
    assert [item["id"] for item in entries] == [
        f"COA-INV-{i:02d}" for i in range(1, 19)
    ]
    valid = {"RND_LOCAL_PARTIAL", "NOT_IMPLEMENTED"}
    assert {item["status"] for item in entries} == valid
    by_id = {item["id"]: item for item in entries}
    for number in (4, 12, 14, 15, 18):
        assert by_id[f"COA-INV-{number:02d}"]["status"] == "NOT_IMPLEMENTED"
    for item in entries:
        assert item["source_section"] == "13 §11"
        assert item["status"] in valid
        assert item["proof_boundary"]
        if item["status"] == "NOT_IMPLEMENTED":
            assert item["evidence_milestone"] is None
        else:
            assert item["evidence_milestone"] in {
                f"L05-{i:02d}" for i in range(1, 6)
            }


def test_all_twenty_qualification_scenarios_are_traced_without_false_e2e(evidence):
    entries = evidence["source_scenarios"]
    assert len(entries) == 20
    assert [item["id"] for item in entries] == [
        f"COA-S{i:02d}" for i in range(1, 21)
    ]
    by_id = {item["id"]: item for item in entries}
    for number in (6, 13, 14, 15, 16, 19, 20):
        assert by_id[f"COA-S{number:02d}"]["status"] == "NOT_IMPLEMENTED"
    assert by_id["COA-S17"]["status"] == "RND_LOCAL_PARTIAL"
    assert by_id["COA-S10"]["status"] == "RND_LOCAL_PARTIAL"
    for item in entries:
        assert item["source_section"] == "13 §19"
        assert item["proof_boundary"]
        if item["status"] == "NOT_IMPLEMENTED":
            assert item["evidence_milestone"] is None
        else:
            assert item["status"] == "RND_LOCAL_PARTIAL"
            assert item["evidence_milestone"] in {
                f"L05-{i:02d}" for i in range(1, 6)
            }


def test_no_gate_go_signatures_or_c10_entitlement_are_declared(evidence):
    gate = evidence["gate_assertions"]
    assert [gate[x] for x in ("G0", "G1", "G2")] == [
        "PENDING_REVIEW", "PENDING_REVIEW", "PENDING_REVIEW"
    ]
    assert gate["G3"] == "HOLD_SECURITY"
    assert gate["G4"] == gate["G5"] == "NOT_APPROVED"
    assert gate["C10"] == "NOT_IMPLEMENTED"
    assert evidence["security_blocker"]["github_issue"] == 71
    assert evidence["security_blocker"]["state_at_baseline"] == "OPEN"
    assert set(evidence["cut_constraints"]) == {
        "NO_MERGE_NO_RELEASE",
        "NO_SQL_MIGRATION_OR_PRIVILEGED_ISSUER",
        "NO_C10_GET_ACCOUNT_ELIGIBILITY_OR_POSTING",
        "NO_PUBLISHED_CHART_OR_BOOK_BINDING",
        "NO_LEDGER_POSTING_OR_MONETARY_ALLOCATION",
        "NO_IAM_OR_LEGAL_ATTESTATION_FROM_TEST_FAKES",
        "NO_SIGNED_ADR_CLAIMS",
        "SHA256_CHECKSUM_IS_NOT_SIGNATURE",
    }


def test_consolidation_text_explicitly_distinguishes_rnd_from_production(evidence):
    text = (
        DOCS / "L05_06_COA_RND_CONSOLIDATION_AND_DECISIONS.md"
    ).read_text(encoding="utf-8")
    required = (
        "COA-INV-18", "COA-S20", "ADR-COA-10",
        "L05_06_COA_RND_EVIDENCE_AND_ADR_REGISTER.json",
        "HOLD_SECURITY", "#71", "NOT_IMPLEMENTED", "RND_LOCAL_PARTIAL",
        "L06", "C10-Q05", "SHA256",
    )
    for token in required:
        assert token in text, token
    assert evidence["next_domain"]["milestone"] == "L06-01"
    assert evidence["next_domain"]["approved"] is False


def test_l06_handoff_has_exact_source_adrs_and_posting_race_stop(evidence):
    handoff = (
        DOCS / "L05_06_L06_FISCAL_CALENDAR_HANDOFF.md"
    ).read_text(encoding="utf-8")
    for i in range(1, 11):
        assert f"ADR-CAL-{i:02d}" in handoff
    for item in (
        "CAL-INV-01", "CAL-INV-10", "CAL-INV-11",
        "CAL-SC-09", "CAL-SC-13", "C10-Q04", "TOCTOU",
        "fencing", "HOLD_SECURITY", "L06-01", "NOT",
    ):
        assert item in handoff
    assert evidence["next_domain"]["expected_source_adrs"] == 10
    assert evidence["next_domain"]["c10_period_query"] == "C10-Q04"


def test_l05_domain_and_query_prototypes_do_not_import_live_sql_or_ledger():
    root = ROOT / "src" / "pyaccountingkit" / "company_configuration"
    domain = root / "domain" / "chart_of_accounts"
    modules = list(domain.glob("*.py"))
    modules += list((root / "application").glob("chart_*.py"))
    modules += list((root / "infrastructure").glob("chart_*.py"))
    assert len(modules) >= 12
    forbidden = {"sqlalchemy", "psycopg", "django", "requests", "httpx"}
    for path in modules:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden, path
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                assert node.module.split(".")[0] not in forbidden, path
        assert "organization_issuer_gateway" not in source, path


def test_l05_domain_classes_do_not_expose_publish_post_or_amount_execution():
    domain = (
        ROOT / "src" / "pyaccountingkit" / "company_configuration"
        / "domain" / "chart_of_accounts"
    )
    for path in domain.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            methods = {
                item.name for item in cls.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            assert not methods.intersection({
                "publish", "post", "allocate", "execute", "commit", "approve"
            }), (path.name, cls.name)


def test_sql_migrations_remain_original_foundation_fourteen():
    migrations = (
        ROOT / "src" / "pyaccountingkit" / "company_configuration"
        / "infrastructure" / "postgres" / "migrations"
    )
    assert migrations.is_dir()
    assert len(list(migrations.glob("*.sql"))) == 14
    assert not list(migrations.glob("0030*.sql"))
