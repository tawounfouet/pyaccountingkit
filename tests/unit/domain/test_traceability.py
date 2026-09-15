"""Unit tests for provenance, lineage, hasher and envelope (LOT-08)."""

from __future__ import annotations

from datetime import UTC, datetime

from pyaccountingkit.domain.traceability.envelope import ReproducibilityEnvelope
from pyaccountingkit.domain.traceability.lineage import LineageEdge, LineageQuery
from pyaccountingkit.domain.traceability.provenance import ProvenanceRef, ProvenanceSource
from pyaccountingkit.domain.traceability.trace import CanonicalHasher, TraceContext

NOW = datetime(2024, 5, 1, 12, 0, tzinfo=UTC)


def test_provenance_is_distinct_from_audit() -> None:
    ref = ProvenanceRef(
        entity_id="e1",
        source=ProvenanceSource.IMPORT,
        source_id="fec:2024-01.csv",
        actor_id="u1",
        recorded_at=NOW,
    )
    assert ref.source is ProvenanceSource.IMPORT
    assert ref.source_id == "fec:2024-01.csv"


def test_lineage_is_queryable_both_directions() -> None:
    lineage = LineageQuery()
    lineage.record(LineageEdge("IMPORTED_FROM", "fec:2024-01.csv", "entry:e1", NOW))
    lineage.record(LineageEdge("POSTED", "entry:e1", "ledger:2024-01", NOW))
    assert [e.to_entity for e in lineage.descendants("entry:e1")] == ["ledger:2024-01"]
    assert [e.from_entity for e in lineage.ancestors("entry:e1")] == ["fec:2024-01.csv"]
    assert len(lineage.edges_for("entry:e1")) == 2


def test_edge_key_is_deterministic() -> None:
    a = LineageEdge("R", "x", "y", NOW)
    b = LineageEdge("R", "x", "y", NOW)
    assert a.key == b.key


def test_canonical_hasher_is_order_independent() -> None:
    first = CanonicalHasher.digest({"a": "x", "b": "y"})
    second = CanonicalHasher.digest({"b": "y", "a": "x"})
    assert first == second
    assert CanonicalHasher.digest({"a": "x", "b": "z"}) != first


def test_canonical_hasher_stable_over_datetime() -> None:
    assert CanonicalHasher.digest({"at": NOW}) == CanonicalHasher.digest({"at": NOW})


def test_envelope_seals_inputs_and_outputs() -> None:
    trace = TraceContext(trace_id="t1", actor_id="u1", started_at=NOW)
    envelope = ReproducibilityEnvelope.seal(
        trace=trace,
        inputs={"period": "p_2024_01"},
        output={"total": "100.00"},
        control_versions={"BALANCE": 3},
        created_at=NOW,
    )
    assert envelope.trace_id == "t1"
    assert len(envelope.inputs_hash) == 64
    assert len(envelope.output_hash) == 64
    assert envelope.control_versions == {"BALANCE": 3}


def test_envelope_hash_depends_on_inputs() -> None:
    trace = TraceContext(trace_id="t1", actor_id="u1", started_at=NOW)
    a = ReproducibilityEnvelope.seal(
        trace=trace,
        inputs={"period": "p_2024_01"},
        output={"total": "100.00"},
        control_versions={},
        created_at=NOW,
    )
    b = ReproducibilityEnvelope.seal(
        trace=trace,
        inputs={"period": "p_2024_02"},
        output={"total": "100.00"},
        control_versions={},
        created_at=NOW,
    )
    assert a.inputs_hash != b.inputs_hash
