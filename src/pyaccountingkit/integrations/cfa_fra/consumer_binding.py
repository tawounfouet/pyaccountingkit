"""Canonical live-consumer repository binding for CFA FRA LOT-26."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import cast

LIVE_CONSUMER_BINDING_SCHEMA = "cfa_fra_live_consumer_binding/v1"

_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


class LiveConsumerBindingError(ValueError):
    """Raised when a canonical live-consumer binding is invalid."""


def _string(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise LiveConsumerBindingError(f"{field} must be a non-empty string")
    return value.strip()


def _utc_timestamp(payload: Mapping[str, object], field: str) -> str:
    value = _string(payload, field)
    if not value.endswith("Z"):
        raise LiveConsumerBindingError(f"{field} must use an explicit UTC Z suffix")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise LiveConsumerBindingError(f"{field} must be ISO-8601") from exc
    offset = parsed.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise LiveConsumerBindingError(f"{field} must be UTC")
    return value


def _canonical_bytes(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class LiveConsumerBinding:
    """Verified identity of the repository that owns the live CFA FRA consumer."""

    consumer: str
    repository: str
    repository_url: str
    default_branch: str
    revision_sha: str
    environment: str
    observed_at: str
    producer: str
    binding_sha256: str

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> "LiveConsumerBinding":
        if payload.get("schema") != LIVE_CONSUMER_BINDING_SCHEMA:
            raise LiveConsumerBindingError(
                f"consumer binding schema must be {LIVE_CONSUMER_BINDING_SCHEMA!r}"
            )
        if payload.get("kind") != "live_consumer_repository_binding":
            raise LiveConsumerBindingError(
                "consumer binding kind must be 'live_consumer_repository_binding'"
            )

        consumer = _string(payload, "consumer")
        repository = _string(payload, "repository")
        if _REPOSITORY.fullmatch(repository) is None:
            raise LiveConsumerBindingError("repository must use canonical owner/name form")

        repository_url = _string(payload, "repository_url")
        expected_url = f"https://github.com/{repository}"
        if repository_url != expected_url:
            raise LiveConsumerBindingError(
                f"repository_url must be the canonical GitHub URL {expected_url!r}"
            )

        default_branch = _string(payload, "default_branch")
        revision_sha = _string(payload, "revision_sha")
        if _GIT_SHA.fullmatch(revision_sha) is None:
            raise LiveConsumerBindingError("revision_sha must be 40 lowercase hexadecimal characters")

        environment = _string(payload, "environment")
        observed_at = _utc_timestamp(payload, "observed_at")
        producer = _string(payload, "producer")

        body: dict[str, object] = {
            "schema": LIVE_CONSUMER_BINDING_SCHEMA,
            "kind": "live_consumer_repository_binding",
            "consumer": consumer,
            "repository": repository,
            "repository_url": repository_url,
            "default_branch": default_branch,
            "revision_sha": revision_sha,
            "environment": environment,
            "observed_at": observed_at,
            "producer": producer,
        }
        return cls(
            consumer=consumer,
            repository=repository,
            repository_url=repository_url,
            default_branch=default_branch,
            revision_sha=revision_sha,
            environment=environment,
            observed_at=observed_at,
            producer=producer,
            binding_sha256=hashlib.sha256(_canonical_bytes(body)).hexdigest(),
        )


@dataclass(frozen=True, slots=True)
class LiveConsumerBindingState:
    """Canonical binding state; UNBOUND is explicit and non-promotable."""

    status: str
    consumer: str
    reason: str | None
    binding: LiveConsumerBinding | None

    @property
    def bound(self) -> bool:
        return self.binding is not None


def parse_live_consumer_binding_state(payload: Mapping[str, object]) -> LiveConsumerBindingState:
    """Parse BOUND/UNBOUND canonical repository identity state."""
    if payload.get("schema_version") != "1":
        raise LiveConsumerBindingError("consumer binding state must use schema_version='1'")

    status = _string(payload, "status")
    consumer = _string(payload, "consumer")
    if status == "UNBOUND":
        reason = _string(payload, "reason")
        if payload.get("binding") is not None:
            raise LiveConsumerBindingError("UNBOUND consumer state must not contain a binding")
        return LiveConsumerBindingState(
            status=status,
            consumer=consumer,
            reason=reason,
            binding=None,
        )
    if status != "BOUND":
        raise LiveConsumerBindingError("consumer binding status must be BOUND or UNBOUND")

    raw_binding = payload.get("binding")
    if not isinstance(raw_binding, dict):
        raise LiveConsumerBindingError("BOUND consumer state requires a binding object")
    binding = LiveConsumerBinding.from_mapping(cast(Mapping[str, object], raw_binding))
    if binding.consumer != consumer:
        raise LiveConsumerBindingError("binding consumer must match canonical consumer identity")
    return LiveConsumerBindingState(
        status=status,
        consumer=consumer,
        reason=None,
        binding=binding,
    )


__all__ = [
    "LIVE_CONSUMER_BINDING_SCHEMA",
    "LiveConsumerBinding",
    "LiveConsumerBindingError",
    "LiveConsumerBindingState",
    "parse_live_consumer_binding_state",
]
