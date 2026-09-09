from pathlib import Path
import yaml
from regacct.models import AccountingFamily

class FamilyRegistry:
    def __init__(self, base_dir="families"):
        self.base_dir = Path(base_dir)
    def list(self):
        out = []
        for p in sorted(self.base_dir.glob("*/manifest.yaml")):
            out.append(AccountingFamily.model_validate(yaml.safe_load(p.read_text(encoding="utf-8"))))
        return out
    def get(self, family_id: str):
        p = self.base_dir / family_id / "manifest.yaml"
        if not p.exists():
            raise KeyError(f"Unknown accounting family: {family_id}")
        return AccountingFamily.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
