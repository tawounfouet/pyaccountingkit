from pathlib import Path
from regacct.config import load_manifest
from regacct.io import sha256_file


def test_pcg_source_bundle_hashes_match_manifest():
    manifest = load_manifest("standards/fr-pcg/2026/manifest.yaml")
    base = Path("standards/fr-pcg/2026")
    assert len(manifest.source_documents) == 6
    for a in manifest.source_documents:
        path = base / a.relative_path
        assert path.exists()
        assert sha256_file(path) == a.sha256
