import json
from pathlib import Path
def test_registry():
 d=json.loads(Path("datasets/annotated/syscohada_2017_consolidation_registry.json").read_text(encoding="utf-8"))
 assert d["statistics"]=={"applications":15,"first_application":128,"last_application":142}
