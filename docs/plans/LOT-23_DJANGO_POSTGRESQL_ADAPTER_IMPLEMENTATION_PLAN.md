# LOT-23 — Django/PostgreSQL Adapter Implementation Plan

**Target:** `0.5.0b1`  
**Baseline:** LOT-22 / `0.5.0a2` at `8670ab0e6cf796ee36a911f9b86b97f69fe9d586`

## Objective

Implement the first Production-oriented persistence adapter for PyAccountingKit using Django 5.2
and PostgreSQL, while preserving the framework-neutral domain and the LOT-21/22 public surfaces.

LOT-23 is an infrastructure lot. Accounting rules remain authoritative in the existing domain
and application services.

## Delivery slices

### Slice A — installable Django app and schema

```text
pyaccountingkit.adapters.django
├── apps.py
├── models.py
├── migrations/
│   └── 0001_initial.py
├── mappers.py
├── repositories.py
└── unit_of_work.py
```

Persisted foundations: journals, accounting periods, journal entries and lines, optimistic
entry revision, audit events, idempotency records, and transactional outbox.

### Slice B — strict domain/ORM mapping

ORM rows are transport/persistence representations only. Django models are converted to/from
immutable domain objects by explicit mappers and never cross the public facade.

### Slice C — repository contracts

Implement the current JournalEntry, Period, Journal, Audit, Idempotency and Outbox ports without
widening them. Optimistic entry saves use an atomic conditional update on `revision`; rowcount
zero maps to `RevisionConflictError`.

### Slice D — Unit of Work

`DjangoUnitOfWork` uses `transaction.atomic()` and exposes bound repository/sink instances.
Commit and rollback semantics must match the InMemory behavioral reference. `select_for_update`
may be used internally for critical coordination but lock primitives do not enter user API.

### Slice E — PostgreSQL qualification

A dedicated CI job runs on a real PostgreSQL service and proves fresh migration, exact repository
round-trips, rollback, audit/outbox/idempotency atomicity, stale revision rejection and critical
posting/closing and reversal concurrency behavior.

## Packaging

Core remains dependency-free: `pip install pyaccountingkit`.
Django adapter: `pip install "pyaccountingkit[django]"`.
LOT-23 uses the repository-qualified family `Django>=5.2,<6` and psycopg 3.

## Gates

```text
GA GAPI GP G3 G4
```

## Definition of Done

```text
[ ] core-only import succeeds without Django installed
[ ] django extra installs cleanly
[ ] Django app loads without importing through package root
[ ] fresh PostgreSQL migration green
[ ] repository contract green
[ ] UoW commit/rollback green
[ ] optimistic revision conflict green
[ ] audit/outbox/idempotency atomicity green
[ ] posting vs close race green
[ ] double reversal race green
[ ] no ORM object leaks through public API
[ ] adapter manifest declares contract v1
[ ] Production qualification is evidence-backed, never aspirational
[ ] Python 3.11/3.12/3.13 retained core qualification green
[ ] Ruff, strict mypy, package, pip-audit and Bandit green
```

## Explicit non-goals

- SQLAlchemy implementation (LOT-24);
- changes to accounting-domain semantics;
- authorization/RBAC;
- application-owned Django models outside the adapter;
- SQLite-only Production qualification.
