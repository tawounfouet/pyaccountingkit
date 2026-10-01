"""Tests for verified CFA FRA standalone-consumer publication handoff."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    ORACLE_TREE_SHA,
    ConsumerPublicationError,
    apply_consumer_publication_plan,
    apply_live_consumer_bootstrap,
    plan_consumer_publication,
    plan_live_consumer_bootstrap,
    publication_plan_payload,
)

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "resources" / "cfa_fra_django_mvp_sprint_7"


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _published_consumer(tmp_path: Path) -> Path:
    target = tmp_path / "cfa-fra-live"
    bootstrap = plan_live_consumer_bootstrap(SOURCE, source_tree_sha=ORACLE_TREE_SHA)
    apply_live_consumer_bootstrap(SOURCE, target, bootstrap)
    _git(target, "init", "-b", "main")
    _git(target, "config", "user.email", "qualification@example.invalid")
    _git(target, "config", "user.name", "Qualification")
    _git(target, "add", ".")
    _git(target, "commit", "-m", "Bootstrap standalone CFA FRA consumer")
    _git(target, "remote", "add", "origin", "https://github.com/tawounfouet/cfa-fra-live")
    return target


def _unbound() -> dict[str, object]:
    return {
        "schema_version": "1",
        "status": "UNBOUND",
        "consumer": "CFA FRA Django MVP Sprint 7",
        "reason": "repository identity not supplied",
    }


def test_publication_plan_binds_exact_clean_git_revision(tmp_path: Path) -> None:
    consumer = _published_consumer(tmp_path)
    plan = plan_consumer_publication(
        consumer,
        SOURCE,
        _unbound(),
        repository="tawounfouet/cfa-fra-live",
        default_branch="main",
        environment="production",
        observed_at="2026-10-01T07:00:00Z",
        producer="publication-test",
    )

    candidate = plan.candidate_binding_state
    binding = candidate["binding"]
    assert isinstance(binding, dict)
    assert candidate["status"] == "BOUND"
    assert binding["revision_sha"] == _git(consumer, "rev-parse", "HEAD")
    assert binding["bootstrap_sha256"]
    assert binding["publication_sha256"]
    assert len(plan.plan_sha256) == 64


def test_publication_rejects_wrong_origin(tmp_path: Path) -> None:
    consumer = _published_consumer(tmp_path)

    with pytest.raises(ConsumerPublicationError, match="origin does not match"):
        plan_consumer_publication(
            consumer,
            SOURCE,
            _unbound(),
            repository="tawounfouet/not-the-consumer",
            default_branch="main",
            environment="production",
            observed_at="2026-10-01T07:00:00Z",
            producer="publication-test",
        )


def test_publication_rejects_dirty_worktree(tmp_path: Path) -> None:
    consumer = _published_consumer(tmp_path)
    (consumer / "README.md").write_text("dirty\n", encoding="utf-8")

    with pytest.raises(ConsumerPublicationError, match="working tree must be clean"):
        plan_consumer_publication(
            consumer,
            SOURCE,
            _unbound(),
            repository="tawounfouet/cfa-fra-live",
            default_branch="main",
            environment="production",
            observed_at="2026-10-01T07:00:00Z",
            producer="publication-test",
        )


def test_apply_rejects_repo_changed_after_review(tmp_path: Path) -> None:
    consumer = _published_consumer(tmp_path)
    current = _unbound()
    plan = plan_consumer_publication(
        consumer,
        SOURCE,
        current,
        repository="tawounfouet/cfa-fra-live",
        default_branch="main",
        environment="production",
        observed_at="2026-10-01T07:00:00Z",
        producer="publication-test",
    )
    payload = publication_plan_payload(plan)

    (consumer / "README.md").write_text("post-review change\n", encoding="utf-8")
    _git(consumer, "add", "README.md")
    _git(consumer, "commit", "-m", "Change after publication review")

    with pytest.raises(ConsumerPublicationError, match="changed after plan review"):
        apply_consumer_publication_plan(payload, consumer, SOURCE, current)


def test_apply_rejects_binding_changed_after_review(tmp_path: Path) -> None:
    consumer = _published_consumer(tmp_path)
    current = _unbound()
    plan = plan_consumer_publication(
        consumer,
        SOURCE,
        current,
        repository="tawounfouet/cfa-fra-live",
        default_branch="main",
        environment="production",
        observed_at="2026-10-01T07:00:00Z",
        producer="publication-test",
    )
    changed = dict(current)
    changed["reason"] = "changed while plan awaited review"

    with pytest.raises(ConsumerPublicationError, match="binding changed"):
        apply_consumer_publication_plan(
            publication_plan_payload(plan),
            consumer,
            SOURCE,
            changed,
        )
