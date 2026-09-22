# Release 0.5.0 — Stable Promotion Plan

## Objective

Promote the fully qualified `0.5.0rc1` line to stable `0.5.0` with **no new business
functionality and no adapter implementation changes**.

Baseline RC: `35c43763d7098a1bdb29f695d43aaca16b73e2ce`.

## Included lots

```text
LOT-21  Public API Facade
LOT-22  Extension API / Adapter Contract v1 / Deterministic Manifests
LOT-23  Django/PostgreSQL Production Adapter
LOT-24  SQLAlchemy/PostgreSQL Production Adapter
```

## Promotion invariants

- no file under `src/pyaccountingkit/domain/` changes;
- no Django/SQLAlchemy implementation code changes;
- release-only qualification assertions may be generalized from RC to the stable version;
- adapter contract remains version `1`;
- both Production adapters remain declared and independently PostgreSQL-qualified;
- public package root remains ORM-neutral;
- deterministic manifests differ from RC only by stable release metadata;
- all stable 0.3/0.4 evidence inherited by 0.5 remains green;
- the release workflow and Security gates remain unchanged.

## Stable release evidence

Stable promotion requires:

- Quality / Ruff / strict mypy green;
- Python 3.11 / 3.12 / 3.13 green;
- wheel and sdist qualification green;
- Django/PostgreSQL 16 Production gate green;
- SQLAlchemy/PostgreSQL 16 Production gate green;
- Extended release qualification green;
- Canonical CI gate green;
- dependency audit and Bandit green;
- exact manifest regeneration checks green.

## Public compatibility position

`0.5.0` is a stable pre-1.0 milestone, not the final 1.0 API freeze.

Stable guarantees at this line include:

- coherent `AccountingApplication` facade;
- framework-neutral public DTO boundary;
- adapter contract v1;
- deterministic public/error/adapter manifests;
- Production-qualified Django/PostgreSQL and SQLAlchemy/PostgreSQL adapters;
- no ORM leakage through the public API.

The broader Python API remains pre-1.0 until LOT-29/LOT-30.

## Exit criterion

Merge only when every canonical and security gate is green on the exact stable PR head.
After merge, reproduce the same gates on the exact `main` squash commit.

No feature work is allowed in this promotion.
