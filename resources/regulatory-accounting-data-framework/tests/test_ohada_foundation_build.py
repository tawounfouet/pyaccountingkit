from regacct.standards.ohada.foundation import build_foundation

def test_foundation_build():
    r=build_foundation(".")
    assert r["status"]=="ok"
    assert r["statistics"]["family_members"]==3
    assert r["statistics"]["source_documents"]==13
    assert r["statistics"]["source_hashes_verified"]==13
    assert r["statistics"]["inheritance_relations"]==0
    assert r["statistics"]["concept_bindings"]==0
