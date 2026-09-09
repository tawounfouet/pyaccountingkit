from pathlib import Path
from regacct.config import load_manifest
from regacct.io import sha256_file


def test_nonprofit_source_hashes_match_manifest():
    m = load_manifest("standards/fr-nonprofit/2026/manifest.yaml")
    base = Path("standards/fr-nonprofit/2026")
    assert len(m.source_documents) == 4
    for a in m.source_documents:
        path = base / a.relative_path
        assert path.exists()
        assert sha256_file(path) == a.sha256
