from pathlib import Path
from .config import discover_manifests, load_manifest

class StandardRegistry:
    def __init__(self, base_dir: str | Path = "standards"):
        self.base_dir = Path(base_dir)
    def list(self):
        return [load_manifest(p) for p in discover_manifests(self.base_dir)]
    def get(self, standard_id: str, edition: str):
        p = self.base_dir / standard_id / edition / "manifest.yaml"
        if not p.exists():
            raise KeyError(f"Unknown standard edition: {standard_id}:{edition}")
        return load_manifest(p)
