"""CLI qualification for reviewed CFA FRA publication-to-binding handoff."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / "scripts" / "bootstrap_cfa_fra_live_consumer.py"
PUBLICATION = ROOT / "scripts" / "run_cfa_fra_consumer_publication.py"
CANONICAL = ROOT / "tests" / "consumer" / "cfa_fra" / "CONSUMER_BINDING.json"


def _run(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def _published_consumer(tmp_path: Path) -> Path:
    target = tmp_path / "cfa-fra-live"
    bootstrap = _run(
        sys.executable,
        str(BOOTSTRAP),
        "--destination",
        str(target),
        "--write",
    )
    assert bootstrap.returncode == 0, bootstrap.stdout + bootstrap.stderr
    for command in (
        ("git", "init", "-b", "main"),
        ("git", "config", "user.email", "qualification@example.invalid"),
        ("git", "config", "user.name", "Qualification"),
        ("git", "add", "."),
        ("git", "commit", "-m", "Bootstrap standalone CFA FRA consumer"),
        ("git", "remote", "add", "origin", "https://github.com/tawounfouet/cfa-fra-live"),
    ):
        result = _run(*command, cwd=target)
        assert result.returncode == 0, result.stdout + result.stderr
    return target


def test_publication_plan_apply_promotes_only_isolated_binding(tmp_path: Path) -> None:
    consumer = _published_consumer(tmp_path)
    binding = tmp_path / "CONSUMER_BINDING.json"
    binding.write_bytes(CANONICAL.read_bytes())
    plan = tmp_path / "publication-plan.json"

    planned = _run(
        sys.executable,
        str(PUBLICATION),
        "--binding",
        str(binding),
        "plan",
        "--consumer-root",
        str(consumer),
        "--repository",
        "tawounfouet/cfa-fra-live",
        "--observed-at",
        "2026-10-01T07:00:00Z",
        "--producer",
        "integration-test",
        "--plan-output",
        str(plan),
    )
    assert planned.returncode == 0, planned.stdout + planned.stderr
    assert json.loads(binding.read_text())["status"] == "UNBOUND"

    dry_run = _run(
        sys.executable,
        str(PUBLICATION),
        "--binding",
        str(binding),
        "apply",
        "--consumer-root",
        str(consumer),
        "--plan",
        str(plan),
    )
    assert dry_run.returncode == 0, dry_run.stdout + dry_run.stderr
    assert "APPLY DRY_RUN" in dry_run.stdout
    assert json.loads(binding.read_text())["status"] == "UNBOUND"

    applied = _run(
        sys.executable,
        str(PUBLICATION),
        "--binding",
        str(binding),
        "apply",
        "--consumer-root",
        str(consumer),
        "--plan",
        str(plan),
        "--write",
    )
    assert applied.returncode == 0, applied.stdout + applied.stderr
    payload = json.loads(binding.read_text())
    assert payload["status"] == "BOUND"
    assert payload["binding"]["repository"] == "tawounfouet/cfa-fra-live"
    assert len(payload["binding"]["bootstrap_sha256"]) == 64
    assert len(payload["binding"]["publication_sha256"]) == 64
