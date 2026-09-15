"""Unit tests for typed identifiers, ObjectRef and IdFactory."""

from __future__ import annotations

import json
import random

import pytest

from pyaccountingkit.core.identifiers import (
    EntryId,
    IdFactory,
    ObjectRef,
    PeriodId,
)


def test_typed_identifiers_are_strings() -> None:
    entry_id = EntryId("entry_1")
    assert entry_id == "entry_1"
    assert isinstance(entry_id, str)
    assert EntryId("entry_1") == EntryId("entry_1")


def test_identifiers_are_json_serializable() -> None:
    period_id = PeriodId("period_2024")
    assert json.loads(json.dumps({"period": period_id})) == {"period": "period_2024"}


def test_id_factory_produces_prefixed_identifiers() -> None:
    factory = IdFactory()
    identifier = factory.new("entry")
    assert identifier.startswith("entry_")
    assert identifier != factory.new("entry")


def test_id_factory_is_deterministic_with_injected_source() -> None:
    first_rng = random.Random(42)
    second_rng = random.Random(42)
    first = IdFactory(first_rng.getrandbits)
    second = IdFactory(second_rng.getrandbits)
    assert first.new("entry") == second.new("entry")


def test_id_factory_rejects_invalid_prefix() -> None:
    with pytest.raises(ValueError):
        IdFactory().new("ENTRY")
    with pytest.raises(ValueError):
        IdFactory().new("")


def test_object_ref_roundtrip() -> None:
    ref = ObjectRef(object_type="journal_entry", object_id="entry_42")
    assert ObjectRef.from_key(ref.to_key()) == ref


def test_object_ref_rejects_malformed_key() -> None:
    with pytest.raises(ValueError):
        ObjectRef.from_key("no-colon")
