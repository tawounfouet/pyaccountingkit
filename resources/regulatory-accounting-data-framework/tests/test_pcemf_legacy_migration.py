from pathlib import Path
import tempfile

from regacct.standards.pcemf.validator import validate_legacy_root
from regacct.standards.pcemf.migration import migrate_legacy_repository
from regacct.io import sha256_file


FIXTURE = Path("tests/fixtures/legacy_pcemf_small")


def test_legacy_validator_is_observational_when_not_strict():
    result = validate_legacy_root(FIXTURE, strict=False)
    assert result["status"] in {"review", "ok"}
    assert "v0" in result["phases"]
    assert result["phases"]["v0"]["actual"]["source_entries"] == 2


def test_migration_preserves_canonical_bytes():
    with tempfile.TemporaryDirectory() as td:
        target = Path(td)
        report = migrate_legacy_repository(FIXTURE, target, strict=False)
        assert report["status"] == "migrated"

        src = FIXTURE / "datasets/pcemf_2010_v0_raw.json"
        dst = target / "datasets/raw/pcemf_2010_v0_raw.json"
        assert dst.exists()
        assert sha256_file(src) == sha256_file(dst)
        assert (target / "validation/review/pcemf_legacy_migration_report.json").exists()
