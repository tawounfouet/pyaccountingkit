"""CLI qualification for the standalone CFA FRA consumer bootstrap."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "bootstrap_cfa_fra_live_consumer.py"


def test_bootstrap_cli_dry_run_is_side_effect_free(tmp_path: Path) -> None:
    target = tmp_path / "consumer"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--destination", str(target)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "CFA FRA standalone consumer bootstrap: DRY_RUN" in result.stdout
    assert '"binding_state": "UNBOUND_UNTIL_PUBLISHED"' in result.stdout
    assert target.exists() is False


def test_bootstrap_cli_materializes_standalone_seed(tmp_path: Path) -> None:
    target = tmp_path / "consumer"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--destination",
            str(target),
            "--write",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (target / "manage.py").is_file()
    assert (target / "PYACCOUNTINGKIT_CONSUMER_BOOTSTRAP.json").is_file()
    manifest = json.loads(
        (target / "PYACCOUNTINGKIT_CONSUMER_BOOTSTRAP.json").read_text(encoding="utf-8")
    )
    assert manifest["framework_requirement"] == "pyaccountingkit>=0.6.0b26,<0.7"
    assert manifest["binding_state"] == "UNBOUND_UNTIL_PUBLISHED"
    assert "Canonical live consumer binding remains UNBOUND" in result.stdout
