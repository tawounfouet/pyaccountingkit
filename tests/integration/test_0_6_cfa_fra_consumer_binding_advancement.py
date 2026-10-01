"""CLI qualification for CFA FRA BOUND revision advancement."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / "scripts" / "bootstrap_cfa_fra_live_consumer.py"
PUBLICATION = ROOT / "scripts" / "run_cfa_fra_consumer_publication.py"
ADVANCEMENT = ROOT / "scripts" / "run_cfa_fra_consumer_binding_advancement.py"
CANONICAL = ROOT / "tests" / "consumer" / "cfa_fra" / "CONSUMER_BINDING.json"


def _run(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def _git(root: Path, *args: str) -> str:
    result = _run("git", "-C", str(root), *args)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip()


def _bound_consumer(tmp_path: Path) -> tuple[Path, Path]:
    consumer = tmp_path / "cfa-fra-live"
    bootstrap = _run(
        sys.executable,
        str(BOOTSTRAP),
        "--destination",
        str(consumer),
        "--write",
    )
    assert bootstrap.returncode == 0, bootstrap.stdout + bootstrap.stderr
    for command in (
        ("init", "-b", "main"),
        ("config", "user.email", "qualification@example.invalid"),
        ("config", "user.name", "Qualification"),
        ("add", "."),
        ("commit", "-m", "Bootstrap standalone CFA FRA consumer"),
        ("remote", "add", "origin", "https://github.com/tawounfouet/cfa-fra-live"),
    ):
        _git(consumer, *command)

    binding = tmp_path / "CONSUMER_BINDING.json"
    binding.write_bytes(CANONICAL.read_bytes())
    publication_plan = tmp_path / "publication-plan.json"
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
        str(publication_plan),
    )
    assert planned.returncode == 0, planned.stdout + planned.stderr
    applied = _run(
        sys.executable,
        str(PUBLICATION),
        "--binding",
        str(binding),
        "apply",
        "--consumer-root",
        str(consumer),
        "--plan",
        str(publication_plan),
        "--write",
    )
    assert applied.returncode == 0, applied.stdout + applied.stderr
    return consumer, binding


def test_bound_revision_advancement_is_reviewed_and_monotonic(tmp_path: Path) -> None:
    consumer, binding = _bound_consumer(tmp_path)
    before = json.loads(binding.read_text(encoding="utf-8"))
    old_revision = before["binding"]["revision_sha"]
    old_bootstrap = before["binding"]["bootstrap_sha256"]

    progress = consumer / "CUTOVER_PROGRESS.md"
    progress.write_text("target-only rewiring started\n", encoding="utf-8")
    _git(consumer, "add", progress.name)
    _git(consumer, "commit", "-m", "Start target-only rewiring")
    new_revision = _git(consumer, "rev-parse", "HEAD")
    plan = tmp_path / "advancement-plan.json"

    planned = _run(
        sys.executable,
        str(ADVANCEMENT),
        "--binding",
        str(binding),
        "plan",
        "--consumer-root",
        str(consumer),
        "--observed-at",
        "2026-10-01T08:00:00Z",
        "--producer",
        "integration-test",
        "--plan-output",
        str(plan),
    )
    assert planned.returncode == 0, planned.stdout + planned.stderr
    assert json.loads(binding.read_text())["binding"]["revision_sha"] == old_revision

    dry_run = _run(
        sys.executable,
        str(ADVANCEMENT),
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

    applied = _run(
        sys.executable,
        str(ADVANCEMENT),
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

    after = json.loads(binding.read_text(encoding="utf-8"))
    assert after["status"] == "BOUND"
    assert after["binding"]["revision_sha"] == new_revision
    assert after["binding"]["revision_sha"] != old_revision
    assert after["binding"]["bootstrap_sha256"] == old_bootstrap
