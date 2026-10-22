"""Corrective regressions for deeply immutable audit/outbox evidence (F14)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import cast

import pytest

from pyaccountingkit.domain.audit.events import AuditEvent
from pyaccountingkit.ports.outbox import OutboxRecord


def _source_payload() -> dict[str, object]:
    return {
        "entry_id": "entry:1",
        "context": {
            "roles": ["author", "reviewer"],
            "flags": {"validated": True},
        },
    }


def test_audit_event_detaches_and_deeply_freezes_payload() -> None:
    source = _source_payload()
    event = AuditEvent(
        event_type="ENTRY_POSTED",
        entity_id="entity:1",
        actor_id="user:1",
        occurred_at=datetime(2026, 10, 22, tzinfo=UTC),
        payload=source,
    )

    context = cast(Mapping[str, object], event.payload["context"])
    roles = cast(tuple[object, ...], context["roles"])
    flags = cast(Mapping[str, object], context["flags"])

    cast(dict[str, object], source["context"])["roles"] = ["tampered"]

    assert roles == ("author", "reviewer")
    assert flags["validated"] is True
    with pytest.raises(TypeError):
        event.payload["entry_id"] = "other"  # type: ignore[index]
    with pytest.raises(TypeError):
        context["roles"] = ("tampered",)  # type: ignore[index]


def test_outbox_record_detaches_and_deeply_freezes_payload() -> None:
    source = _source_payload()
    record = OutboxRecord(
        event_type="ENTRY_POSTED",
        entity_id="entity:1",
        payload=source,
        idempotency_key="post:entry:1",
    )

    context = cast(Mapping[str, object], record.payload["context"])
    roles = cast(tuple[object, ...], context["roles"])

    cast(dict[str, object], source["context"])["roles"] = ["tampered"]

    assert roles == ("author", "reviewer")
    with pytest.raises(TypeError):
        record.payload["new"] = "value"  # type: ignore[index]
    with pytest.raises(TypeError):
        context["roles"] = ("tampered",)  # type: ignore[index]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: AuditEvent(
            event_type="BAD",
            entity_id="entity:1",
            actor_id="user:1",
            occurred_at=datetime(2026, 10, 22, tzinfo=UTC),
            payload={"bad": object()},
        ),
        lambda: OutboxRecord(
            event_type="BAD",
            entity_id="entity:1",
            payload={"bad": object()},
        ),
    ],
)
def test_evidence_payload_rejects_non_json_values(factory: object) -> None:
    with pytest.raises(TypeError, match="Unsupported JSON evidence value"):
        cast(object, factory)()
