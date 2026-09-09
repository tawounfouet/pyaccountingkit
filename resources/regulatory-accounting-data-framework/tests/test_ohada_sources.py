from pathlib import Path
from regacct.config import load_manifest
from regacct.io import sha256_file

MEMBERS=[("ohada-syscohada","2017"),("ohada-ebnl","2023"),("cemac-pcemf","2010")]

def test_hashes():
    for sid,ed in MEMBERS:
        m=load_manifest(f"standards/{sid}/{ed}/manifest.yaml")
        base=Path("standards")/sid/ed
        for a in m.source_documents:
            p=base/a.relative_path
            assert p.exists()
            assert sha256_file(p)==a.sha256

def test_ebnl_ocr_blocked():
    m=load_manifest("standards/ohada-ebnl/2023/manifest.yaml")
    md=next(x for x in m.source_documents if x.document_id=="ohada-ebnl-plan-2023-md")
    assert md.canonical_eligibility is False
    assert md.quality_status=="ocr_needs_human_review"

def test_pcemf_list_md_secondary():
    m=load_manifest("standards/cemac-pcemf/2010/manifest.yaml")
    md=next(x for x in m.source_documents if x.document_id=="pcemf-list-2010-md")
    assert md.canonical_eligibility is False
    assert set(md.derived_from)=={"pcemf-2010","pcemf-list-2010"}
