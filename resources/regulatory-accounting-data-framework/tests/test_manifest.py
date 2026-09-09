from regacct.config import discover_manifests, load_manifest

def test_manifests_are_valid():
    paths=discover_manifests('standards')
    assert len(paths)>=9
    ms=[load_manifest(p) for p in paths]
    assert any(m.standard_id=='fr-pcg' and m.edition=='2026' for m in ms)
    assert any(m.standard_id=='cemac-pcemf' and m.capabilities.prudential for m in ms)
