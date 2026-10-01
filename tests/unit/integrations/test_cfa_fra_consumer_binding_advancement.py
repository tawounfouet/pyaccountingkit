"""Tests for reviewed CFA FRA consumer binding revision advancement."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    ORACLE_TREE_SHA,
    ConsumerBindingAdvancementError,
    ConsumerBindingRevisionObservation,
    ConsumerRepositoryObservation,
    apply_consumer_binding_advancement_plan,
    apply_live_consumer_bootstrap,
    binding_advancement_plan_payload,
    plan_consumer_binding_advancement,
    plan_consumer_publication,
    plan_live_consumer_bootstrap,
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


def _consumer(tmp_path: Path) -> Path:
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


def _repo_observation(consumer: Path) -> ConsumerRepositoryObservation:
    manifest = json.loads(
        (consumer / "PYACCOUNTINGKIT_CONSUMER_BOOTSTRAP.json").read_text(encoding="utf-8")
    )
    assert isinstance(manifest, dict)
    return ConsumerRepositoryObservation(
        repository_is_top_level=True,
        worktree_clean=not bool(_git(consumer, "status", "--porcelain")),
        revision_sha=_git(consumer, "rev-parse", "HEAD"),
        current_branch=_git(consumer, "branch", "--show-current"),
        origin=_git(consumer, "remote", "get-url", "origin"),
        bootstrap_manifest=manifest,
    )


def _initial_bound(consumer: Path) -> dict[str, object]:
    unbound = {
        "schema_version": "1",
        "status": "UNBOUND",
        "consumer": "CFA FRA Django MVP Sprint 7",
        "reason": "repository identity not supplied",
    }
    plan = plan_consumer_publication(
        _repo_observation(consumer),
        SOURCE,
        unbound,
        repository="tawounfouet/cfa-fra-live",
        default_branch="main",
        environment="production",
        observed_at="2026-10-01T07:00:00Z",
        producer="publication-test",
    )
    return dict(plan.candidate_binding_state)


def _advance_commit(consumer: Path) -> str:
    path = consumer / "CUTOVER_PROGRESS.md"
    path.write_text("target-only rewiring started\n", encoding="utf-8")
    _git(consumer, "add", path.name)
    _git(consumer, "commit", "-m", "Start target-only rewiring")
    return _git(consumer, "rev-parse", "HEAD")


def test_bound_revision_advances_with_same_identity_and_provenance(tmp_path: Path) -> None:
    consumer = _consumer(tmp_path)
    current = _initial_bound(consumer)
    old_binding = current["binding"]
    assert isinstance(old_binding, dict)
    old_revision = old_binding["revision_sha"]
    old_bootstrap = old_binding["bootstrap_sha256"]
    new_revision = _advance_commit(consumer)

    observation = ConsumerBindingRevisionObservation(
        repository=_repo_observation(consumer),
        previous_revision_is_ancestor=True,
    )
    plan = plan_consumer_binding_advancement(
        observation,
        SOURCE,
        current,
        observed_at="2026-10-01T08:00:00Z",
        producer="advancement-test",
    )
    candidate = plan.candidate_binding_state
    binding = candidate["binding"]
    assert isinstance(binding, dict)

    assert old_revision != new_revision
    assert binding["revision_sha"] == new_revision
    assert binding["repository"] == old_binding["repository"]
    assert binding["bootstrap_sha256"] == old_bootstrap
    assert binding["publication_sha256"] != old_binding["publication_sha256"]


def test_advancement_rejects_non_descendant_revision(tmp_path: Path) -> None:
    consumer = _consumer(tmp_path)
    current = _initial_bound(consumer)
    _advance_commit(consumer)

    observation = ConsumerBindingRevisionObservation(
        repository=_repo_observation(consumer),
        previous_revision_is_ancestor=False,
    )
    with pytest.raises(ConsumerBindingAdvancementError, match="must be an ancestor"):
        plan_consumer_binding_advancement(
            observation,
            SOURCE,
            current,
            observed_at="2026-10-01T08:00:00Z",
            producer="advancement-test",
        )


def test_advancement_rejects_same_revision(tmp_path: Path) -> None:
    consumer = _consumer(tmp_path)
    current = _initial_bound(consumer)

    observation = ConsumerBindingRevisionObservation(
        repository=_repo_observation(consumer),
        previous_revision_is_ancestor=True,
    )
    with pytest.raises(ConsumerBindingAdvancementError, match="advance to a new SHA"):
        plan_consumer_binding_advancement(
            observation,
            SOURCE,
            current,
            observed_at="2026-10-01T08:00:00Z",
            producer="advancement-test",
        )


def test_apply_rejects_revision_changed_after_review(tmp_path: Path) -> None:
    consumer = _consumer(tmp_path)
    current = _initial_bound(consumer)
    _advance_commit(consumer)

    observation = ConsumerBindingRevisionObservation(
        repository=_repo_observation(consumer),
        previous_revision_is_ancestor=True,
    )
    plan = plan_consumer_binding_advancement(
        observation,
        SOURCE,
        current,
        observed_at="2026-10-01T08:00:00Z",
        producer="advancement-test",
    )

    second = consumer / "SECOND_CHANGE.md"
    second.write_text("changed after review\n", encoding="utf-8")
    _git(consumer, "add", second.name)
    _git(consumer, "commit", "-m", "Change after advancement review")

    changed_observation = ConsumerBindingRevisionObservation(
        repository=_repo_observation(consumer),
        previous_revision_is_ancestor=True,
    )
    with pytest.raises(ConsumerBindingAdvancementError, match="changed after plan review"):
        apply_consumer_binding_advancement_plan(
            binding_advancement_plan_payload(plan),
            changed_observation,
            SOURCE,
            current,
        )
