from __future__ import annotations


def validate_source_roles(manifest) -> list[str]:
    errors = []
    roles = {a.document_id: a.role for a in manifest.source_documents}
    if roles.get("fr-nonprofit-recueil-2026") != "official_regulatory_source":
        errors.append("ANC PDF must be official_regulatory_source")
    if roles.get("orcom-associations-plan-2025") != "external_practitioner_reference":
        errors.append("ORCOM PDF must be external_practitioner_reference")
    return errors


def validate_overlay(overlay: dict, effective: dict) -> list[str]:
    errors = []
    if overlay.get("base_standard") != "fr-pcg:2026":
        errors.append("wrong_base_standard")
    codes = [x["ref_code"] for x in overlay["overlay_entries"]]
    if len(codes) != len(set(codes)):
        errors.append("duplicate_official_specific_code")
    if "102" not in codes or "196" not in codes:
        errors.append("expected_nonprofit_specific_accounts_missing")
    if not any(x["ref_code"] == "102" and x["overlay_type"] == "label_or_semantic_override" for x in overlay["overlay_entries"]):
        errors.append("102_must_override_pcg_fiduciary_meaning")
    if not any(x["ref_code"] == "19" and x["overlay_type"] == "specific_addition" for x in overlay["overlay_entries"]):
        errors.append("19_must_be_specific_addition")
    if effective["statistics"]["effective_accounts_or_groups"] <= 700:
        errors.append("effective_plan_unexpectedly_small")
    return errors


def validate_functioning(v2: dict) -> list[str]:
    errors = []
    if v2["statistics"]["annotations"] != 7:
        errors.append(f"expected_7_account_functioning_articles:{v2['statistics']['annotations']}")
    if any(x["executable_rules_generated"] for x in v2["annotations"]):
        errors.append("v2_must_not_generate_executable_rules")
    return errors


def validate_practitioner_comparison(comparison: dict) -> list[str]:
    errors = []
    policy = comparison["comparison_policy"]
    if policy["practitioner_reference_is_regulatory_source"]:
        errors.append("practitioner_promoted_to_regulatory_source")
    if policy["canonical_promotion_allowed"]:
        errors.append("practitioner_canonical_promotion_enabled")
    return errors


def validate_reporting(reporting: dict) -> list[str]:
    errors = []
    if reporting["statistics"]["statement_templates"] != 4:
        errors.append("expected_four_nonprofit_reporting_templates")
    if reporting["mapping_policy"]["account_hints_executable"]:
        errors.append("derived_account_hints_must_not_be_executable")
    if not reporting["mapping_policy"]["human_validation_required"]:
        errors.append("derived_account_hints_require_human_validation")
    return errors
