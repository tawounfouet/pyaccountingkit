from regacct.config import load_manifest
from regacct.standards.nonprofit.validation import validate_source_roles


def test_nonprofit_is_overlay_of_pcg():
    m = load_manifest("standards/fr-nonprofit/2026/manifest.yaml")
    assert m.base_standard == "fr-pcg:2026"
    assert m.extension_type == "sector_overlay"
    assert validate_source_roles(m) == []


def test_orcom_is_never_regulatory_primary():
    m = load_manifest("standards/fr-nonprofit/2026/manifest.yaml")
    roles = {x.document_id:x.role for x in m.source_documents}
    assert roles["fr-nonprofit-recueil-2026"] == "official_regulatory_source"
    assert roles["orcom-associations-plan-2025"] == "external_practitioner_reference"
