"""LOT-26 tests for the canonical CFA FRA live-consumer repository binding."""

from __future__ import annotations

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    LIVE_CONSUMER_BINDING_SCHEMA,
    LiveConsumerBindingError,
    parse_live_consumer_binding_state,
)


def _bound_payload() -> dict[str, object]:
    return {
        "schema_version": "1",
        "status": "BOUND",
        "consumer": "CFA FRA Django MVP Sprint 7",
        "binding": {
            "schema": LIVE_CONSUMER_BINDING_SCHEMA,
            "kind": "live_consumer_repository_binding",
            "consumer": "CFA FRA Django MVP Sprint 7",
            "repository": "tawounfouet/cfa-fra-live",
            "repository_url": "https://github.com/tawounfouet/cfa-fra-live",
            "default_branch": "main",
            "revision_sha": "a" * 40,
            "environment": "production",
            "observed_at": "2026-10-01T06:00:00Z",
            "producer": "cfa-fra-cutover",
        },
    }


def test_unbound_state_is_explicit_and_valid() -> None:
    state = parse_live_consumer_binding_state(
        {
            "schema_version": "1",
            "status": "UNBOUND",
            "consumer": "CFA FRA Django MVP Sprint 7",
            "reason": "repository identity not supplied",
        }
    )

    assert state.bound is False
    assert state.binding is None
    assert state.reason == "repository identity not supplied"


def test_bound_state_has_deterministic_repository_identity() -> None:
    state = parse_live_consumer_binding_state(_bound_payload())

    assert state.bound is True
    assert state.binding is not None
    assert state.binding.repository == "tawounfouet/cfa-fra-live"
    assert state.binding.revision_sha == "a" * 40
    assert len(state.binding.binding_sha256) == 64


def test_binding_rejects_noncanonical_repository_url() -> None:
    payload = _bound_payload()
    binding = payload["binding"]
    assert isinstance(binding, dict)
    binding["repository_url"] = "https://example.invalid/cfa-fra-live"

    with pytest.raises(LiveConsumerBindingError, match="canonical GitHub URL"):
        parse_live_consumer_binding_state(payload)


def test_binding_rejects_non_git_revision() -> None:
    payload = _bound_payload()
    binding = payload["binding"]
    assert isinstance(binding, dict)
    binding["revision_sha"] = "not-a-sha"

    with pytest.raises(LiveConsumerBindingError, match="40 lowercase hexadecimal"):
        parse_live_consumer_binding_state(payload)


def test_unbound_state_rejects_embedded_binding() -> None:
    payload = _bound_payload()
    payload["status"] = "UNBOUND"
    payload["reason"] = "not yet verified"

    with pytest.raises(LiveConsumerBindingError, match="must not contain a binding"):
        parse_live_consumer_binding_state(payload)
