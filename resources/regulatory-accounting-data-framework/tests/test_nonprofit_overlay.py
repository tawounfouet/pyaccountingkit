import json
from pathlib import Path
from regacct.standards.nonprofit.validation import validate_overlay


def load(name):
    return json.loads(Path(name).read_text(encoding="utf-8"))


def test_art_320_2_builds_overlay_not_full_copy():
    overlay = load("datasets/structured/nonprofit_2026_v1_account_overlay.json")
    effective = load("datasets/structured/nonprofit_2026_v1_effective_plan.json")
    assert validate_overlay(overlay, effective) == []
    assert len(overlay["overlay_entries"]) < len(effective["accounts"])


def test_account_102_overrides_pcg_fiduciary_label():
    overlay = load("datasets/structured/nonprofit_2026_v1_account_overlay.json")
    row = next(x for x in overlay["overlay_entries"] if x["ref_code"] == "102")
    assert row["overlay_type"] == "label_or_semantic_override"
    assert "fiducia" in row["base_label_source"].lower()
    assert "sans droit de reprise" in row["extension_label_source"].lower()


def test_group_19_is_nonprofit_specific_addition():
    overlay = load("datasets/structured/nonprofit_2026_v1_account_overlay.json")
    row = next(x for x in overlay["overlay_entries"] if x["ref_code"] == "19")
    assert row["overlay_type"] == "specific_addition"
    assert "fonds dédiés" in row["extension_label_source"].lower() or "fonds dedies" in row["extension_label_source"].lower()


def test_effective_plan_keeps_inherited_pcg_accounts():
    effective = load("datasets/structured/nonprofit_2026_v1_effective_plan.json")
    by_code = {x["ref_code"]:x for x in effective["accounts"]}
    assert by_code["101"]["origin"] == "inherited_from_base_standard"
    assert by_code["196"]["origin"] in {"extension_addition","extension_override"}
