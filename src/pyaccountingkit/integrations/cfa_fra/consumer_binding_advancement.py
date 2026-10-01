"""Reviewed advancement of an already-bound CFA FRA consumer revision."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from pyaccountingkit.integrations.cfa_fra.consumer_binding import (
    LiveConsumerBinding,
    parse_live_consumer_binding_state,
)
from pyaccountingkit.integrations.cfa_fra.consumer_publication import (
    ConsumerPublicationError,
    ConsumerRepositoryObservation,
    PublishedConsumerRepository,
    publication_payload,
    verify_published_consumer_repository,
)

CONSUMER_BINDING_ADVANCEMENT_PLAN_SCHEMA = "cfa_fra_consumer_binding_advancement_plan/v1"


class ConsumerBindingAdvancementError(RuntimeError):
    """Raised when a bound consumer revision cannot be advanced safely."""


@dataclass(frozen=True, slots=True)
class ConsumerBindingRevisionObservation:
    """Observed Git state plus ancestry proof from the currently bound revision."""

    repository: ConsumerRepositoryObservation
    previous_revision_is_ancestor: bool


@dataclass(frozen=True, slots=True)
class ConsumerBindingAdvancementPlan:
    """Reviewed BOUND(old) -> BOUND(new) transition for one consumer repository."""

    current_binding_sha256: str
    from_revision_sha: str
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


def _binding_candidate(publication: PublishedConsumerRepository) -> dict[str, object]:
    return {
        "schema_version": "1",
        "status": "BOUND",
        "consumer": "CFA FRA Django MVP Sprint 7",
        "binding": {
            "schema": "cfa_fra_live_consumer_binding/v2",
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
        },
    }


def _require_same_identity(
    current: LiveConsumerBinding,
    publication: PublishedConsumerRepository,
) -> None:
    if publication.repository != current.repository:
        raise ConsumerBindingAdvancementError("bound consumer repository identity may not change")
    if publication.repository_url != current.repository_url:
        raise ConsumerBindingAdvancementError("bound consumer repository URL may not change")
    if publication.default_branch != current.default_branch:
        raise ConsumerBindingAdvancementError("bound consumer default branch may not change")
    if publication.environment != current.environment:
        raise ConsumerBindingAdvancementError("bound consumer environment may not change")
    if publication.bootstrap_sha256 != current.bootstrap_sha256:
        raise ConsumerBindingAdvancementError("bound consumer bootstrap provenance may not change")
    if publication.revision_sha == current.revision_sha:
        raise ConsumerBindingAdvancementError("bound consumer revision must advance to a new SHA")


def plan_consumer_binding_advancement(
    observation: ConsumerBindingRevisionObservation,
    source_root: Path,
    current_binding: Mapping[str, object],
    *,
    observed_at: str,
    producer: str,
) -> ConsumerBindingAdvancementPlan:
    """Create a side-effect-free reviewed revision advancement plan."""
    state = parse_live_consumer_binding_state(current_binding)
    if state.binding is None:
        raise ConsumerBindingAdvancementError("revision advancement requires canonical state BOUND")
    if not observation.previous_revision_is_ancestor:
        raise ConsumerBindingAdvancementError(
            "currently bound revision must be an ancestor of the observed revision"
        )

    current = state.binding
    try:
        publication = verify_published_consumer_repository(
            observation.repository,
            source_root,
            repository=current.repository,
            default_branch=current.default_branch,
            environment=current.environment,
            observed_at=observed_at,
            producer=producer,
        )
    except ConsumerPublicationError as exc:
        raise ConsumerBindingAdvancementError(str(exc)) from exc

    _require_same_identity(current, publication)
    candidate = _binding_candidate(publication)
    parse_live_consumer_binding_state(candidate)

    current_binding_sha256 = _sha256_mapping(current_binding)
    core: dict[str, object] = {
        "schema": CONSUMER_BINDING_ADVANCEMENT_PLAN_SCHEMA,
        "current_binding_sha256": current_binding_sha256,
        "from_revision_sha": current.revision_sha,
        "publication": publication_payload(publication),
        "candidate_binding_state": candidate,
    }
    return ConsumerBindingAdvancementPlan(
        current_binding_sha256=current_binding_sha256,
        from_revision_sha=current.revision_sha,
        publication=publication,
        candidate_binding_state=candidate,
        plan_sha256=_sha256_mapping(core),
    )


def binding_advancement_plan_payload(
    plan: ConsumerBindingAdvancementPlan,
) -> dict[str, object]:
    """Serialize a revision advancement plan for review."""
    return {
        "schema": CONSUMER_BINDING_ADVANCEMENT_PLAN_SCHEMA,
        "current_binding_sha256": plan.current_binding_sha256,
        "from_revision_sha": plan.from_revision_sha,
        "publication": publication_payload(plan.publication),
        "candidate_binding_state": dict(plan.candidate_binding_state),
        "plan_sha256": plan.plan_sha256,
    }


def apply_consumer_binding_advancement_plan(
    plan_payload: Mapping[str, object],
    observation: ConsumerBindingRevisionObservation,
    source_root: Path,
    current_binding: Mapping[str, object],
) -> dict[str, object]:
    """Revalidate and return the reviewed BOUND revision advancement candidate."""
    if plan_payload.get("schema") != CONSUMER_BINDING_ADVANCEMENT_PLAN_SCHEMA:
        raise ConsumerBindingAdvancementError("consumer binding advancement plan schema is invalid")

    state = parse_live_consumer_binding_state(current_binding)
    if state.binding is None:
        raise ConsumerBindingAdvancementError("revision advancement requires canonical state BOUND")
    current = state.binding

    current_binding_sha256 = plan_payload.get("current_binding_sha256")
    if current_binding_sha256 != _sha256_mapping(current_binding):
        raise ConsumerBindingAdvancementError("canonical consumer binding changed after plan review")
    if plan_payload.get("from_revision_sha") != current.revision_sha:
        raise ConsumerBindingAdvancementError("bound consumer revision changed after plan review")

    raw_publication = plan_payload.get("publication")
    candidate = plan_payload.get("candidate_binding_state")
    if not isinstance(raw_publication, dict) or not isinstance(candidate, dict):
        raise ConsumerBindingAdvancementError("consumer binding advancement plan is incomplete")

    core = {
        "schema": CONSUMER_BINDING_ADVANCEMENT_PLAN_SCHEMA,
        "current_binding_sha256": current_binding_sha256,
        "from_revision_sha": current.revision_sha,
        "publication": raw_publication,
        "candidate_binding_state": candidate,
    }
    if plan_payload.get("plan_sha256") != _sha256_mapping(core):
        raise ConsumerBindingAdvancementError("consumer binding advancement fingerprint is invalid")
    if not observation.previous_revision_is_ancestor:
        raise ConsumerBindingAdvancementError(
            "currently bound revision must remain an ancestor of the observed revision"
        )

    observed_at = raw_publication.get("observed_at")
    producer = raw_publication.get("producer")
    if not isinstance(observed_at, str) or not isinstance(producer, str):
        raise ConsumerBindingAdvancementError("advancement publication metadata is invalid")

    try:
        fresh = verify_published_consumer_repository(
            observation.repository,
            source_root,
            repository=current.repository,
            default_branch=current.default_branch,
            environment=current.environment,
            observed_at=observed_at,
            producer=producer,
        )
    except ConsumerPublicationError as exc:
        raise ConsumerBindingAdvancementError(str(exc)) from exc

    _require_same_identity(current, fresh)
    if publication_payload(fresh) != raw_publication:
        raise ConsumerBindingAdvancementError("consumer repository changed after plan review")

    expected_candidate = _binding_candidate(fresh)
    if expected_candidate != candidate:
        raise ConsumerBindingAdvancementError("binding candidate differs from reviewed advancement")
    return cast(dict[str, object], candidate)


__all__ = [
    "CONSUMER_BINDING_ADVANCEMENT_PLAN_SCHEMA",
    "ConsumerBindingAdvancementError",
    "ConsumerBindingAdvancementPlan",
    "ConsumerBindingRevisionObservation",
    "apply_consumer_binding_advancement_plan",
    "binding_advancement_plan_payload",
    "plan_consumer_binding_advancement",
]
