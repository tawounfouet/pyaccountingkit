from pathlib import Path
import yaml
from .models import StandardManifest

def load_manifest(path: str | Path) -> StandardManifest:
    path = Path(path)
    return StandardManifest.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))

def discover_manifests(base_dir: str | Path = "standards") -> list[Path]:
    return sorted(Path(base_dir).glob("*/*/manifest.yaml"))
