"""Unit tests for IdempotencyKey derivation and canonical serialization."""

from __future__ import annotations

import pytest

from pyaccountingkit.core.idempotency import IdempotencyKey


def test_derive_is_deterministic() -> None:
    first = IdempotencyKey.derive("entity_1", "POST_ENTRY", b"payload")
    second = IdempotencyKey.derive("entity_1", "POST_ENTRY", b"payload")
    assert first == second
    assert first.canonical() == second.canonical()


def test_derive_splits_scopes_and_operations() -> None:
    assert (
        IdempotencyKey.derive("a", "op").canonical() != IdempotencyKey.derive("b", "op").canonical()
    )
    assert (
        IdempotencyKey.derive("a", "op").canonical()
        != IdempotencyKey.derive("a", "other").canonical()
    )


def test_derive_splits_payloads() -> None:
    assert IdempotencyKey.derive("a", "op", b"one") != IdempotencyKey.derive("a", "op", b"two")


def test_canonical_serialization_roundtrip() -> None:
    key = IdempotencyKey.derive("entity_1", "POST_ENTRY", b"payload")
    assert IdempotencyKey.from_canonical(key.canonical()) == key


def test_from_canonical_rejects_malformed_values() -> None:
    for malformed in ("", "noscope", "no:op", "no:op:nodigest:a"):
        with pytest.raises(ValueError):
            IdempotencyKey.from_canonical(malformed)


def test_empty_payload_is_supported() -> None:
    assert (
        IdempotencyKey.derive("a", "op").payload_digest
        == IdempotencyKey.derive("a", "op", b"").payload_digest
    )
