# Release 0.5.0rc1 — Cross-Lot Public API & Production Adapters Qualification

## Objective

`0.5.0rc1` qualifies the complete `0.5.x` line across LOT-21, LOT-22, LOT-23 and LOT-24.
It adds no accounting-domain capability.

```text
LOT-21 Public API Facade
        ↓
LOT-22 Extension API / Adapter Contract v1
       / \
      /   \
LOT-23   LOT-24
Django   SQLAlchemy
  \       /
   \     /
    PostgreSQL 16
        ↓
cross-lot qualification
        ↓
0.5.0rc1
```

Baseline: `0.5.0b2` at `a3e307089a100249caff3bde0c7cc41aa1c28e7d`.

## Release invariants

1. No new business-domain semantics.
2. Package root remains ORM-neutral.
3. Public facade never returns Django/SQLAlchemy objects.
4. Adapter contract remains version `1`.
5. Both Production adapters implement equivalent transaction semantics.
6. Both adapters preserve exact immutable domain round-trips.
7. Critical races remain fail-closed: stale revision, duplicate idempotency, double reversal,
   posting-vs-close.
8. Django migrations and SQLAlchemy Alembic metadata remain coherent with their real
   PostgreSQL 16 schemas.
9. Deterministic compatibility manifests remain reproducible.
10. Stable 0.4 subledger/financial-analysis and stable 0.3 import/reporting evidence remains green.

## Required evidence

```text
tests/integration/test_0_5_public_production_adapter_pipeline.py
tests/contract/test_public_api_boundary.py
tests/contract/test_extension_api_contracts.py
tests/integration/test_django_postgresql_adapter.py
tests/concurrency/test_django_postgresql_concurrency.py
tests/integration/test_sqlalchemy_postgresql_adapter.py
tests/concurrency/test_sqlalchemy_postgresql_concurrency.py
tests/integration/test_0_4_subledger_financial_analysis_pipeline.py
tests/replay/test_0_4_release_pipeline_replay.py
tests/contract/test_corporate_finance_boundary.py
tests/integration/test_0_3_import_reporting_pipeline.py
tests/replay/test_0_3_release_pipeline_replay.py
```

The release qualifier fails closed if any required evidence file disappears.

## Cross-adapter qualification

The canonical CI must require simultaneously:

- Python 3.11 / 3.12 / 3.13;
- deterministic Quality gates;
- package wheel/sdist verification;
- Django/PostgreSQL 16 migration + behavior + concurrency;
- SQLAlchemy/PostgreSQL 16 Alembic + metadata + behavior + concurrency;
- dependency audit;
- Bandit;
- Canonical CI aggregation.

The two Production adapter suites deliberately exercise the same semantic invariants:
exact round-trip, atomic rollback, audit/outbox/idempotency atomicity, stale revision rejection,
one-winner idempotency, double-reversal serialization and posting-vs-close serialization.

## Exit criterion

The RC may be merged only when all required evidence and all canonical jobs are green on the
same SHA. Promotion to stable `0.5.0` must then contain no new business code.
