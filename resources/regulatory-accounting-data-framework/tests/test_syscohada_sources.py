from pathlib import Path
from regacct.config import load_manifest
from regacct.io import sha256_file
def test_hashes():
 m=load_manifest("standards/ohada-syscohada/2017/manifest.yaml");b=Path("standards/ohada-syscohada/2017")
 for a in m.source_documents:
  p=b/a.relative_path;assert p.exists();assert sha256_file(p)==a.sha256
