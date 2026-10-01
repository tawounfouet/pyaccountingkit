"""Verified publication handoff from CFA FRA standalone seed to canonical binding."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from pyaccountingkit.integrations.cfa_fra.consumer_binding import (
    LIVE_CONSUMER_BINDING_SCHEMA,
    LiveConsumerBinding,
    LiveConsumerBindingError,
    parse_live_consumer_binding_state,
)
from pyaccountingkit.integrations.cfa_fra.consumer_bootstrap import (
    CONSUMER_BOOTSTRAP_SCHEMA,
    DEFAULT_FRAMEWORK_REQUIREMENT,
    plan_live_consumer_bootstrap,
)
from pyaccountingkit.integrations.cfa_fra.golden import (
    ORACLE_MANIFEST_VERSION,
    ORACLE_TREE_SHA,
)

CONSUMER_PUBLICATION_SCHEMA = "cfa_fra_consumer_publication/v1"
CONSUMER_PUBLICATION_PLAN_SCHEMA = "cfa_fra_consumer_publication_plan/v1"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


class ConsumerPublicationError(RuntimeError):
    """Raised when standalone-consumer publication cannot be proven safely."""


@dataclass(frozen=True, slots=True)
class PublishedConsumerRepository:
    """Verified Git publication identity for a standalone CFA FRA consumer."""

    repository: str
    repository_url: str
    default_branch: str
    revision_sha: str
    environment: str
    observed_at: str
    producer: str
    bootstrap_sha256: str
    bootstrap_manifest_sha256: str
    publication_sha256: str


@dataclass(frozen=True, slots=True)
class ConsumerPublicationPlan:
    """Reviewed transition from canonical UNBOUND state to one verified BOUND candidate."""

    current_binding_sha256: str
    publication: PublishedConsumerRepository
    candidate_binding_state: Mapping[str, object]
    plan_sha256: str


def _canonical_bytes(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_mapping(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
        raise ConsumerPublicationError(detail)
    return completed.stdout.strip()


def _normalize_github_origin(origin: str) -> tuple[str, str]:
    value = origin.strip()
    if value.startswith("https://github.com/"):
        repository = value.removeprefix("https://github.com/")
    elif value.startswith("git@github.com:"):
        repository = value.removeprefix("git@github.com:")
    else:
        raise ConsumerPublicationError("consumer origin must be hosted on github.com")
    if repository.endswith(".git"):
        repository = repository[:-4]
    if repository.count("/") != 1 or any(not part for part in repository.split("/")):
        raise ConsumerPublicationError("consumer origin must resolve to canonical owner/name")
    return repository, f"https://github.com/{repository}"


def _load_bootstrap_manifest(
    consumer_root: Path,
    source_root: Path,
) -> tuple[dict[str, object], str]:
    path = consumer_root / "PYACCOUNTINGKIT_CONSUMER_BOOTSTRAP.json"
    try:
        raw_bytes = path.read_bytes()
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConsumerPublicationError("published consumer bootstrap manifest is missing or invalid") from exc
    if not isinstance(payload, dict):
        raise ConsumerPublicationError("published consumer bootstrap manifest must be a JSON object")
    if payload.get("schema") != CONSUMER_BOOTSTRAP_SCHEMA:
        raise ConsumerPublicationError("published consumer bootstrap schema is invalid")
    if payload.get("kind") != "standalone_consumer_seed":
        raise ConsumerPublicationError("published consumer is not a standalone consumer seed")

    source = payload.get("source")
    if not isinstance(source, dict):
        raise ConsumerPublicationError("published consumer bootstrap source metadata is missing")
    if source.get("oracle_tree_sha") != ORACLE_TREE_SHA:
        raise ConsumerPublicationError("published consumer bootstrap oracle tree does not match")
    if source.get("oracle_manifest_version") != ORACLE_MANIFEST_VERSION:
        raise ConsumerPublicationError("published consumer bootstrap oracle manifest does not match")

    framework_requirement = payload.get("framework_requirement")
    if framework_requirement != DEFAULT_FRAMEWORK_REQUIREMENT:
        raise ConsumerPublicationError("published consumer framework requirement is not current")

    if payload.get("binding_state") != "UNBOUND_UNTIL_PUBLISHED":
        raise ConsumerPublicationError("published consumer seed must still declare pre-binding state")
    if payload.get("cutover_state") != "NOT_STARTED":
        raise ConsumerPublicationError("published consumer seed must still declare pre-cutover state")

    expected_plan = plan_live_consumer_bootstrap(
        source_root,
        source_tree_sha=ORACLE_TREE_SHA,
        framework_requirement=DEFAULT_FRAMEWORK_REQUIREMENT,
    )
    bootstrap_sha256 = payload.get("bootstrap_sha256")
    if bootstrap_sha256 != expected_plan.bootstrap_sha256:
        raise ConsumerPublicationError("published consumer bootstrap fingerprint does not match")
    if not isinstance(bootstrap_sha256, str) or _SHA256.fullmatch(bootstrap_sha256) is None:
        raise ConsumerPublicationError("published consumer bootstrap fingerprint is invalid")

    return cast(dict[str, object], payload), hashlib.sha256(raw_bytes).hexdigest()


def publication_payload(publication: PublishedConsumerRepository) -> dict[str, object]:
    """Serialize verified publication evidence without recomputing it."""
    return {
        "schema": CONSUMER_PUBLICATION_SCHEMA,
        "kind": "published_consumer_repository",
        "repository": publication.repository,
        "repository_url": publication.repository_url,
        "default_branch": publication.default_branch,
        "revision_sha": publication.revision_sha,
        "environment": publication.environment,
        "observed_at": publication.observed_at,
        "producer": publication.producer,
        "bootstrap_sha256": publication.bootstrap_sha256,
        "bootstrap_manifest_sha256": publication.bootstrap_manifest_sha256,
        "publication_sha256": publication.publication_sha256,
    }


def inspect_published_consumer_repository(
    consumer_root: Path,
    source_root: Path,
    *,
    repository: str,
    default_branch: str,
    environment: str,
    observed_at: str,
    producer: str,
) -> PublishedConsumerRepository:
    """Verify Git identity plus immutable bootstrap provenance of a published consumer."""
    root = consumer_root.resolve()
    if not root.is_dir():
        raise ConsumerPublicationError("published consumer root does not exist")

    top_level = Path(_git(root, "rev-parse", "--show-toplevel")).resolve()
    if top_level != root:
        raise ConsumerPublicationError("consumer root must be the top-level Git repository")

    if _git(root, "status", "--porcelain"):
        raise ConsumerPublicationError("published consumer working tree must be clean")

    revision_sha = _git(root, "rev-parse", "HEAD")
    if _GIT_SHA.fullmatch(revision_sha) is None:
        raise ConsumerPublicationError("published consumer HEAD is not a canonical Git SHA")
    if revision_sha == ORACLE_TREE_SHA:
        raise ConsumerPublicationError("published consumer revision may not equal frozen oracle tree")

    current_branch = _git(root, "branch", "--show-current")
    if current_branch != default_branch:
        raise ConsumerPublicationError("published consumer must be checked out on its default branch")

    origin_repository, origin_url = _normalize_github_origin(_git(root, "remote", "get-url", "origin"))
    if origin_repository != repository:
        raise ConsumerPublicationError("published consumer origin does not match reviewed repository")

    bootstrap, bootstrap_manifest_sha256 = _load_bootstrap_manifest(root, source_root)
    bootstrap_sha256 = cast(str, bootstrap["bootstrap_sha256"])

    body: dict[str, object] = {
        "schema": CONSUMER_PUBLICATION_SCHEMA,
        "kind": "published_consumer_repository",
        "repository": repository,
        "repository_url": origin_url,
        "default_branch": default_branch,
        "revision_sha": revision_sha,
        "environment": environment,
        "observed_at": observed_at,
        "producer": producer,
        "bootstrap_sha256": bootstrap_sha256,
        "bootstrap_manifest_sha256": bootstrap_manifest_sha256,
    }
    binding = LiveConsumerBinding.from_mapping(
        {
            "schema": LIVE_CONSUMER_BINDING_SCHEMA,
            "kind": "live_consumer_repository_binding",
            "consumer": "CFA FRA Django MVP Sprint 7",
            **{key: body[key] for key in (
                "repository",
                "repository_url",
                "default_branch",
                "revision_sha",
                "environment",
                "observed_at",
                "producer",
                "bootstrap_sha256",
            )},
            "publication_sha256": _sha256_mapping(body),
        }
    )
    publication_sha256 = binding.publication_sha256

    return PublishedConsumerRepository(
        repository=repository,
        repository_url=origin_url,
        default_branch=default_branch,
        revision_sha=revision_sha,
        environment=environment,
        observed_at=observed_at,
        producer=producer,
        bootstrap_sha256=bootstrap_sha256,
        bootstrap_manifest_sha256=bootstrap_manifest_sha256,
        publication_sha256=publication_sha256,
    )


def _candidate_binding_state(publication: PublishedConsumerRepository) -> dict[str, object]:
    binding = {
        "schema": LIVE_CONSUMER_BINDING_SCHEMA,
        "kind": "live_consumer_repository_binding",
        "consumer": "CFA FRA Django MVP Sprint 7",
        "repository": publication.repository,
        "repository_url": publication.repository_url,
        "default_branch": publication.default_branch,
        "revision_sha": publication.revision_sha,
        "environment": publication.environment,
        "observed_at": publication.observed_at,
        "producer": publication.producer,
        "bootstrap_sha256": publication.bootstrap_sha256,
        "publication_sha256": publication.publication_sha256,
    }
    LiveConsumerBinding.from_mapping(binding)
    return {
        "schema_version": "1",
        "status": "BOUND",
        "consumer": "CFA FRA Django MVP Sprint 7",
        "binding": binding,
    }


def plan_consumer_publication(
    consumer_root: Path,
    source_root: Path,
    current_binding: Mapping[str, object],
    *,
    repository: str,
    default_branch: str,
    environment: str,
    observed_at: str,
    producer: str,
) -> ConsumerPublicationPlan:
    """Build a side-effect-free reviewed publication-to-binding transition."""
    state = parse_live_consumer_binding_state(current_binding)
    if state.bound:
        raise ConsumerPublicationError("publication plan requires canonical consumer state UNBOUND")

    publication = inspect_published_consumer_repository(
        consumer_root,
        source_root,
        repository=repository,
        default_branch=default_branch,
        environment=environment,
        observed_at=observed_at,
        producer=producer,
    )
    candidate = _candidate_binding_state(publication)
    core = {
        "schema": CONSUMER_PUBLICATION_PLAN_SCHEMA,
        "current_binding_sha256": _sha256_mapping(current_binding),
        "publication": publication_payload(publication),
        "candidate_binding_state": candidate,
    }
    return ConsumerPublicationPlan(
        current_binding_sha256=cast(str, core["current_binding_sha256"]),
        publication=publication,
        candidate_binding_state=candidate,
        plan_sha256=_sha256_mapping(core),
    )


def publication_plan_payload(plan: ConsumerPublicationPlan) -> dict[str, object]:
    """Serialize a publication plan for human review and later apply."""
    return {
        "schema": CONSUMER_PUBLICATION_PLAN_SCHEMA,
        "current_binding_sha256": plan.current_binding_sha256,
        "publication": publication_payload(plan.publication),
        "candidate_binding_state": dict(plan.candidate_binding_state),
        "plan_sha256": plan.plan_sha256,
    }


def apply_consumer_publication_plan(
    plan_payload: Mapping[str, object],
    consumer_root: Path,
    source_root: Path,
    current_binding: Mapping[str, object],
) -> dict[str, object]:
    """Revalidate a reviewed plan against unchanged Git and canonical binding state."""
    if plan_payload.get("schema") != CONSUMER_PUBLICATION_PLAN_SCHEMA:
        raise ConsumerPublicationError("consumer publication plan schema is invalid")

    raw_publication = plan_payload.get("publication")
    candidate = plan_payload.get("candidate_binding_state")
    if not isinstance(raw_publication, dict) or not isinstance(candidate, dict):
        raise ConsumerPublicationError("consumer publication plan payload is incomplete")

    current_binding_sha256 = plan_payload.get("current_binding_sha256")
    if current_binding_sha256 != _sha256_mapping(current_binding):
        raise ConsumerPublicationError("canonical consumer binding changed after plan review")

    stored_plan_sha256 = plan_payload.get("plan_sha256")
    core = {
        "schema": CONSUMER_PUBLICATION_PLAN_SCHEMA,
        "current_binding_sha256": current_binding_sha256,
        "publication": raw_publication,
        "candidate_binding_state": candidate,
    }
    if stored_plan_sha256 != _sha256_mapping(core):
        raise ConsumerPublicationError("consumer publication plan fingerprint is invalid")

    for field in (
        "repository",
        "default_branch",
        "environment",
        "observed_at",
        "producer",
    ):
        if not isinstance(raw_publication.get(field), str):
            raise ConsumerPublicationError(f"consumer publication plan field {field} is invalid")

    fresh = inspect_published_consumer_repository(
        consumer_root,
        source_root,
        repository=cast(str, raw_publication["repository"]),
        default_branch=cast(str, raw_publication["default_branch"]),
        environment=cast(str, raw_publication["environment"]),
        observed_at=cast(str, raw_publication["observed_at"]),
        producer=cast(str, raw_publication["producer"]),
    )
    if publication_payload(fresh) != raw_publication:
        raise ConsumerPublicationError("published consumer repository changed after plan review")

    expected_candidate = _candidate_binding_state(fresh)
    if expected_candidate != candidate:
        raise ConsumerPublicationError("binding candidate differs from verified publication")
    return expected_candidate


__all__ = [
    "CONSUMER_PUBLICATION_PLAN_SCHEMA",
    "CONSUMER_PUBLICATION_SCHEMA",
    "ConsumerPublicationError",
    "ConsumerPublicationPlan",
    "PublishedConsumerRepository",
    "apply_consumer_publication_plan",
    "inspect_published_consumer_repository",
    "plan_consumer_publication",
    "publication_payload",
    "publication_plan_payload",
]
