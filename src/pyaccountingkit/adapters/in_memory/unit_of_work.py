"""In-memory UnitOfWork — isolated reference transaction boundary.

Each entered UnitOfWork operates on a detached working copy. Commit validates
that every touched key still matches the baseline observed at entry, then
merges only the local delta into the shared store. Rollback therefore never
restores an old global snapshot and cannot erase another transaction's commit.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from types import TracebackType
from typing import Any, Self

from pyaccountingkit.adapters.in_memory.repositories import (
    InMemoryAccountingExecutionTraceRepository,
    InMemoryJournalEntryRepository,
    InMemoryJournalRepository,
    InMemoryPeriodRepository,
)
from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.core.clock import ClockProtocol, SystemClock
from pyaccountingkit.core.errors import IdempotencyConflictError, RevisionConflictError
from pyaccountingkit.domain.audit.events import AuditEvent
from pyaccountingkit.ports.outbox import OutboxRecord


class InMemoryAuditLogSink:
    """Append audit events to the transaction-local working store."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def record(self, event: AuditEvent) -> None:
        self._store.audit_log.append(event)


class InMemoryIdempotencyStore:
    """Claim and complete idempotency keys in transaction-local state."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def claim(self, key: str, payload_fingerprint: str = "") -> bool:
        if key in self._store.idempotency:
            existing = self._store.idempotency_fingerprints.get(key, "")
            if existing != payload_fingerprint:
                raise IdempotencyConflictError(
                    f"Idempotency key {key} is already bound to a different payload"
                )
            return False
        self._store.idempotency[key] = "claimed"
        self._store.idempotency_fingerprints[key] = payload_fingerprint
        return True

    def complete(self, key: str) -> None:
        self._store.idempotency[key] = "completed"


class InMemoryOutboxPublisher:
    """Append outbox records to the transaction-local working store."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def publish(self, record: OutboxRecord) -> None:
        self._store.outbox.append(record)


class InMemoryUnitOfWork:
    """Transactionally isolated scope over one shared ``InMemoryStore``."""

    def __init__(
        self,
        store: InMemoryStore,
        clock: ClockProtocol | None = None,
    ) -> None:
        self._store = store
        self.clock = clock if clock is not None else SystemClock()
        self._baseline: InMemoryStore | None = None
        self._read_dependencies: set[tuple[str, Any]] = set()
        self._working = store.copy()
        self._committed = False
        self._bind(self._working)

    def _bind(self, store: InMemoryStore) -> None:
        self.entries = InMemoryJournalEntryRepository(store, self._track_read)
        self.periods = InMemoryPeriodRepository(store, self._track_read)
        self.journals = InMemoryJournalRepository(store, self._track_read)
        self.audit = InMemoryAuditLogSink(store)
        self.idempotency = InMemoryIdempotencyStore(store)
        self.outbox = InMemoryOutboxPublisher(store)
        self.execution_traces = InMemoryAccountingExecutionTraceRepository(store, self._track_read)

    def _track_read(self, kind: str, key: Any) -> None:
        self._read_dependencies.add((kind, key))

    def __enter__(self) -> Self:
        self._baseline = self._store.copy()
        self._read_dependencies = set()
        self._working = self._baseline.copy()
        self._bind(self._working)
        self._committed = False
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None or not self._committed:
            self.rollback()

    def commit(self) -> None:
        baseline = self._baseline
        if baseline is None:
            raise RuntimeError("Cannot commit an un-entered UnitOfWork")
        self._validate_concurrent_changes(baseline)
        self._validate_read_dependencies(baseline)
        self._merge_delta(baseline)
        self._baseline = None
        self._committed = True

    def rollback(self) -> None:
        """Discard local state without mutating the shared store."""
        self._baseline = None
        self._read_dependencies = set()
        self._working = self._store.copy()
        self._bind(self._working)
        self._committed = False

    def _validate_concurrent_changes(self, baseline: InMemoryStore) -> None:
        for entry_id in set(baseline.entries) | set(self._working.entries):
            changed = baseline.entries.get(entry_id) != self._working.entries.get(
                entry_id
            ) or baseline.entry_revisions.get(entry_id) != self._working.entry_revisions.get(
                entry_id
            )
            if changed and (
                self._store.entries.get(entry_id) != baseline.entries.get(entry_id)
                or self._store.entry_revisions.get(entry_id)
                != baseline.entry_revisions.get(entry_id)
            ):
                raise RevisionConflictError(f"Entry {entry_id} changed after UnitOfWork snapshot")

        self._validate_mapping_changes(
            "Period",
            baseline.periods,
            self._working.periods,
            self._store.periods,
        )
        self._validate_mapping_changes(
            "Journal",
            baseline.journals,
            self._working.journals,
            self._store.journals,
        )
        self._validate_mapping_changes(
            "Idempotency key",
            baseline.idempotency,
            self._working.idempotency,
            self._store.idempotency,
        )
        self._validate_mapping_changes(
            "Idempotency fingerprint",
            baseline.idempotency_fingerprints,
            self._working.idempotency_fingerprints,
            self._store.idempotency_fingerprints,
        )
        self._validate_mapping_changes(
            "Accounting execution trace",
            baseline.execution_traces,
            self._working.execution_traces,
            self._store.execution_traces,
        )

        if self._working.audit_log[: len(baseline.audit_log)] != baseline.audit_log:
            raise RevisionConflictError("audit log prefix changed inside UnitOfWork")
        if self._working.outbox[: len(baseline.outbox)] != baseline.outbox:
            raise RevisionConflictError("outbox prefix changed inside UnitOfWork")

    def _validate_read_dependencies(self, baseline: InMemoryStore) -> None:
        for kind, key in self._read_dependencies:
            if kind == "entry":
                entry_id = key
                if (
                    self._store.entries.get(entry_id) != baseline.entries.get(entry_id)
                    or self._store.entry_revisions.get(entry_id)
                    != baseline.entry_revisions.get(entry_id)
                ):
                    raise RevisionConflictError(
                        f"Read dependency Entry {entry_id} changed after UnitOfWork snapshot"
                    )
            elif kind == "period":
                if self._store.periods.get(key) != baseline.periods.get(key):
                    raise RevisionConflictError(
                        f"Read dependency Period {key} changed after UnitOfWork snapshot"
                    )
            elif kind == "journal":
                if self._store.journals.get(key) != baseline.journals.get(key):
                    raise RevisionConflictError(
                        f"Read dependency Journal {key} changed after UnitOfWork snapshot"
                    )
            elif kind == "execution_trace":
                if self._store.execution_traces.get(key) != baseline.execution_traces.get(key):
                    raise RevisionConflictError(
                        f"Read dependency execution trace {key} changed after UnitOfWork snapshot"
                    )
            elif kind == "entries_by_period":
                if self._posted_entries_for_period(self._store, key) != self._posted_entries_for_period(
                    baseline, key
                ):
                    raise RevisionConflictError(
                        f"Read dependency entries for Period {key} changed after UnitOfWork snapshot"
                    )
            elif kind == "entries_by_journal":
                if self._posted_entries_for_journal(
                    self._store, key
                ) != self._posted_entries_for_journal(baseline, key):
                    raise RevisionConflictError(
                        f"Read dependency entries for Journal {key} changed after UnitOfWork snapshot"
                    )
            elif kind == "reversals_of":
                if self._reversals_of(self._store, key) != self._reversals_of(baseline, key):
                    raise RevisionConflictError(
                        f"Read dependency reversals of Entry {key} changed after UnitOfWork snapshot"
                    )
            elif kind == "periods_all" and self._store.periods != baseline.periods:
                raise RevisionConflictError(
                    "Read dependency period collection changed after UnitOfWork snapshot"
                )

    @staticmethod
    def _posted_entries_for_period(
        store: InMemoryStore,
        period_id: Any,
    ) -> tuple[tuple[object, object, object], ...]:
        return tuple(
            sorted(
                (
                    entry_id,
                    entry,
                    store.entry_revisions.get(entry_id),
                )
                for entry_id, entry in store.entries.items()
                if entry.period_id == period_id
                and entry.status.value in {"POSTED", "REVERSED"}
            , key=lambda row: str(row[0]))
        )

    @staticmethod
    def _posted_entries_for_journal(
        store: InMemoryStore,
        journal_id: Any,
    ) -> tuple[tuple[object, object, object], ...]:
        return tuple(
            sorted(
                (
                    entry_id,
                    entry,
                    store.entry_revisions.get(entry_id),
                )
                for entry_id, entry in store.entries.items()
                if entry.journal_id == journal_id
                and entry.status.value in {"POSTED", "REVERSED"}
            , key=lambda row: str(row[0]))
        )

    @staticmethod
    def _reversals_of(
        store: InMemoryStore,
        entry_id: Any,
    ) -> tuple[tuple[object, object, object], ...]:
        return tuple(
            sorted(
                (
                    candidate_id,
                    entry,
                    store.entry_revisions.get(candidate_id),
                )
                for candidate_id, entry in store.entries.items()
                if entry.reversal_of_id == entry_id
            , key=lambda row: str(row[0]))
        )

    @staticmethod
    def _validate_mapping_changes(
        resource: str,
        baseline: Mapping[Any, Any],
        working: Mapping[Any, Any],
        shared: Mapping[Any, Any],
    ) -> None:
        for key in set(baseline) | set(working):
            if baseline.get(key) != working.get(key) and shared.get(key) != baseline.get(key):
                raise RevisionConflictError(f"{resource} {key} changed after UnitOfWork snapshot")

    def _merge_delta(self, baseline: InMemoryStore) -> None:
        self._merge_mapping(baseline.entries, self._working.entries, self._store.entries)
        self._merge_mapping(
            baseline.entry_revisions,
            self._working.entry_revisions,
            self._store.entry_revisions,
        )
        self._merge_mapping(baseline.periods, self._working.periods, self._store.periods)
        self._merge_mapping(baseline.journals, self._working.journals, self._store.journals)
        self._merge_mapping(
            baseline.idempotency,
            self._working.idempotency,
            self._store.idempotency,
        )
        self._merge_mapping(
            baseline.idempotency_fingerprints,
            self._working.idempotency_fingerprints,
            self._store.idempotency_fingerprints,
        )
        self._merge_mapping(
            baseline.execution_traces,
            self._working.execution_traces,
            self._store.execution_traces,
        )
        self._store.audit_log.extend(self._working.audit_log[len(baseline.audit_log) :])
        self._store.outbox.extend(self._working.outbox[len(baseline.outbox) :])

    @staticmethod
    def _merge_mapping(
        baseline: Mapping[Any, Any],
        working: Mapping[Any, Any],
        shared: MutableMapping[Any, Any],
    ) -> None:
        for key in set(baseline) | set(working):
            if baseline.get(key) == working.get(key):
                continue
            if key in working:
                shared[key] = working[key]
            else:
                shared.pop(key, None)


class InMemoryUnitOfWorkFactory:
    """Open fresh isolated transaction scopes over one shared store."""

    def __init__(self, store: InMemoryStore | None = None) -> None:
        self._store = store if store is not None else InMemoryStore()

    @property
    def store(self) -> InMemoryStore:
        return self._store

    def open(self) -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(self._store)


__all__ = [
    "InMemoryUnitOfWork",
    "InMemoryUnitOfWorkFactory",
    "InMemoryAuditLogSink",
    "InMemoryIdempotencyStore",
    "InMemoryOutboxPublisher",
]
