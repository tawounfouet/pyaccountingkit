import json
from pathlib import Path
from regacct.standards.ebnl.validation import (
    validate_complete_source, validate_legal_registry, validate_conceptual_framework,
    validate_v2_complete, validate_specific_operations, validate_reporting_complete,
    validate_disclosures_complete,
)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_full_official_source_page_registry():
    d=load("datasets/annotated/ebnl_2023_source_page_registry.json")
    assert validate_complete_source(d)==[]
    assert d["statistics"]["pages"]==438
    assert d["statistics"]["pages_sparse_or_header_only"]>=400
    assert d["extraction_policy"]["full_verbatim_ocr_claimed"] is False


def test_legal_and_conceptual_registries():
    legal=load("datasets/annotated/ebnl_2023_legal_act_registry.json")
    conceptual=load("datasets/annotated/ebnl_2023_conceptual_framework.json")
    assert validate_legal_registry(legal)==[]
    assert validate_conceptual_framework(conceptual)==[]
    assert legal["statistics"]["articles"]==28
    assert conceptual["statistics"]["definitions"]==47


def test_v2_binds_all_84_account_groups_to_visual_source_pages():
    d=load("datasets/annotated/ebnl_2023_v2_account_functioning.json")
    assert validate_v2_complete(d)==[]
    assert d["statistics"]["group_bindings"]==84
    assert d["statistics"]["visual_title_pages_bound"]==84
    assert d["account_functioning_model"]["executable_posting_rules_generated"] is False


def test_specific_operations_have_six_official_chapters():
    d=load("datasets/annotated/ebnl_2023_specific_operations.json")
    assert validate_specific_operations(d)==[]
    assert [x["page_range"][0] for x in d["chapters"]]==[311,319,325,329,333,335]


def test_reporting_has_three_profiles_and_13_models():
    d=load("datasets/reporting/ebnl_2023_v3_reporting.json")
    assert validate_reporting_complete(d)==[]
    assert d["statistics"]["profiles"]==3
    assert d["statistics"]["statement_models"]==13
    profiles={p["profile_id"]:p for p in d["profiles"]}
    assert [s["model_page_pdf"] for s in profiles["association_professional_order"]["statements"][:3]]==[346,347,348]
    assert [s["model_page_pdf"] for s in profiles["development_project"]["statements"][:5]]==[398,399,400,401,402]
    assert [s["model_page_pdf"] for s in profiles["minimal_cash_system"]["statements"][:2]]==[434,435]


def test_disclosures_registry_is_source_bound_without_false_exhaustiveness():
    d=load("datasets/annotated/ebnl_2023_disclosures_registry.json")
    assert validate_disclosures_complete(d)==[]
    assert all(x["field_level_requirements_exhaustively_transcribed"] is False for x in d["profiles"])
