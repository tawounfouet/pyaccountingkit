from regacct.config import load_manifest


def test_manifest_enables_complete_source_capabilities():
    m=load_manifest("standards/ohada-ebnl/2023/manifest.yaml")
    assert m.canonical_status=="complete_official_normative_source_structured_v0_v3"
    assert m.effective_from=="2024-01-01"
    assert m.capabilities.structure is True
    assert m.capabilities.posting_guidance is True
    assert m.capabilities.financial_reporting is True
    assert m.capabilities.disclosures is True
    full=next(x for x in m.source_documents if x.document_id=="ohada-sycebnl-2023-full-act")
    assert full.role=="official_primary_normative_source"
    assert full.canonical_eligibility is True
