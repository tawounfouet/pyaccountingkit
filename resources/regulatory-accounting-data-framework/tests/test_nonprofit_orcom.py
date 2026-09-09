import json
from pathlib import Path
from regacct.standards.nonprofit.validation import validate_practitioner_comparison


def test_orcom_is_secondary_comparison_only():
    data = json.loads(Path("validation/review/nonprofit_2026_orcom_comparison.json").read_text(encoding="utf-8"))
    assert validate_practitioner_comparison(data) == []
    assert data["comparison_policy"]["canonical_promotion_allowed"] is False
    assert data["temporal_warning"]["practitioner_reference_is_older"] is True


def test_orcom_duplicate_meanings_are_detected():
    data = json.loads(Path("validation/review/nonprofit_2026_orcom_comparison.json").read_text(encoding="utf-8"))
    # ORCOM explicitly prints 102 twice for historical reasons.
    assert "102" in data["duplicate_codes"]
