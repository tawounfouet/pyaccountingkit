# LOT-24 — SQLAlchemy/PostgreSQL Adapter Implementation Plan

**Target:** `0.5.0b2`  
**Baseline:** qualified LOT-23 / `0.5.0b1` at `23c5fd3f4535eae266c19707aa228473bdb66176`

## Objective

Implement the second Production PostgreSQL persistence adapter with SQLAlchemy 2.x while
preserving the same domain, public API, adapter contract v1 and physical accounting schema
already qualified by LOT-23.

LOT-24 is the final implementation lot before transverse qualification of the complete
`0.5.0` line.

## Architecture

```text
pyaccountingkit.adapters.sqlalchemy
├── tables.py
├── mappers.py
├── repositories.py
├── unit_of_work.py
└── migrations/
    ├── env.py
    └── versions/
        └── 0001_initial.py
```

The SQLAlchemy adapter uses Declarative 2.0 and a Session-based UnitOfWork. ORM state never
crosses the adapter boundary.

## Schema parity

The SQLAlchemy adapter owns the same canonical PostgreSQL tables as the Django adapter:

- `pyak_journal`;
- `pyak_accounting_period`;
- `pyak_journal_entry`;
- `pyak_journal_line`;
- `pyak_audit_event`;
- `pyak_idempotency`;
- `pyak_outbox`.

This is intentional schema parity, not a second accounting model.

## Repository and transaction contracts

Implement the same ports and behaviors qualified in LOT-23:

- journal, period and journal-entry repositories;
- audit sink;
- idempotency store;
- transactional outbox publisher;
- optimistic revision updates;
- row locking for mutable entries and periods;
- atomic commit / rollback through a SQLAlchemy Session.

Critical aggregate reads use PostgreSQL `FOR UPDATE` inside the UnitOfWork. Idempotency
claims use a nested transaction/savepoint so duplicate claims fail closed without poisoning
the enclosing accounting transaction.

## Alembic

LOT-24 owns an Alembic migration lineage with a fresh `0001_initial` migration.
CI must prove both:

- `alembic upgrade head` succeeds against empty PostgreSQL 16;
- migration metadata and SQLAlchemy Declarative metadata remain coherent.

## Packaging

Core remains ORM-free:

```bash
pip install pyaccountingkit
```

SQLAlchemy adapter:

```bash
pip install "pyaccountingkit[sqlalchemy]"
```

The extra contains SQLAlchemy 2.x, Alembic and psycopg 3.

## Production qualification

A dedicated PostgreSQL 16 CI job must prove:

- published `.[sqlalchemy]` extra installs cleanly;
- fresh Alembic migration;
- exact repository/domain round-trips;
- UnitOfWork commit and rollback;
- audit/outbox/idempotency atomicity;
- optimistic revision conflicts;
- concurrent idempotency claims;
- double-reversal serialization;
- posting-vs-close serialization;
- no ORM leakage through public API.

## Definition of Done

```text
[ ] core-only wheel import remains ORM-free
[ ] sqlalchemy extra installs cleanly
[ ] Declarative metadata represents canonical PostgreSQL schema
[ ] fresh Alembic migration green
[ ] repository contract green
[ ] Session UnitOfWork commit/rollback green
[ ] optimistic revision conflict green
[ ] audit/outbox/idempotency atomicity green
[ ] posting-vs-close race green
[ ] double reversal race green
[ ] no SQLAlchemy ORM object leaks through public API
[ ] adapter contract manifest declares SQLAlchemy Production qualification
[ ] Django Production qualification remains green
[ ] Python 3.11/3.12/3.13 retained qualification green
[ ] Ruff, strict mypy, package, pip-audit and Bandit green
```

## Explicit non-goals

- changes to domain accounting semantics;
- changes to public DTOs or façade semantics;
- a SQLAlchemy-specific domain model;
- authorization/RBAC;
- release `0.5.0` stable promotion before transverse qualification of LOT-21 through LOT-24.
