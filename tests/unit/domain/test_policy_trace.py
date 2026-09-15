"""Unit tests for PolicyExecutionTrace (LOT-12)."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from pyaccountingkit.domain.policies.policy_set import PolicyType
from pyaccountingkit.domain.policies.policy_trace import PolicyExecutionTrace


def _trace() -> PolicyExecutionTrace:
    return PolicyExecutionTrace(
        trace_id="tr:1",
        policy_type=PolicyType.RECOGNITION,
        policy_id="rec-sale-on-doc-date",
        policy_version="1.0",
        policy_set_id="ps:1",
        policy_set_version="1",
        accounting_entity_id="ent:1",
        accounting_date=date(2026, 6, 30),
        reference_snapshot_id="snap:1",
        evaluated_at=datetime(2026, 7, 1, 12, 0, 0),
        outcome="RECOGNIZED",
    )


def test_trace_is_immutable() -> None:
    trace = _trace()
    with pytest.raises(AttributeError):
        trace.outcome = "CHANGED"  # type: ignore[misc]


def test_trace_required_fields() -> None:
    with pytest.raises(ValueError, match="trace_id must be non-empty"):
        PolicyExecutionTrace(
            trace_id="",
            policy_type=PolicyType.RECOGNITION,
            policy_id="p",
            policy_version="1",
            policy_set_id="ps",
            policy_set_version="1",
            accounting_entity_id="ent",
            accounting_date=date(2026, 6, 30),
        )


def test_trace_pins_policy_version_and_snapshot() -> None:
    trace = _trace()
    assert trace.policy_version == "1.0"
    assert trace.reference_snapshot_id == "snap:1"
    assert trace.policy_set_version == "1"


def test_trace_fields_are_typed() -> None:
    trace = _trace()
    assert trace.policy_type is PolicyType.RECOGNITION
    assert trace.accounting_date == date(2026, 6, 30)
    assert trace.evaluated_at is not None
