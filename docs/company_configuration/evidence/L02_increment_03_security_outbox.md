# L02-03 - Denial audit and durable Outbox dispatch (candidate)

**Status:** implemented candidate awaiting exact-SHA CI; **not** G2 approval.

## Changes

- `0002_delivery_and_denials.sql` adds tenant-scoped mutable delivery state separately from immutable `outbox_events`, plus append-only `authorization_denials`.
- `PostgresOutboxDispatcher` claims due events with `FOR UPDATE SKIP LOCKED`, atomic lease tokens, bounded exponential backoff, terminal dead-letter state, safe error class logging and per-tenant configuration.
- `PostgresDenialAudit` records an already verified principal's denied operation in a separate transaction, using the principal's tenant rather than a user-requested foreign tenant. `LegalEntityService(denial_audit=...)` is opt-in to preserve backward compatibility with the existing L02 test adapter.
- A dispatcher-only SQL role reads the immutable event stream and mutates only the delivery state. A runtime SQL role inserts denial evidence.
- Integration tests cover publish/retry/dead-letter/recovery/crash duplicates/concurrency/tenant filtering/denial persistence and fail-closed audit failure.

## Guarantees and limitations

- Delivery is **at-least-once**, not exactly once. A crash after publishing but before acknowledgement may deliver the same immutable `event_id` twice. Consumers must enforce idempotent effects transactionally.
- Outbox delivery does **not** mean C10 is qualified; no real event broker or downstream consumer contract is implemented.
- The source event table remains logically append-only (not WORM). The `outbox_delivery` table is intentionally mutable and should not be confused with immutable accounting evidence.
- `app.tenant_id` is caller-modifiable by a compromised SQL client. RLS here is a cooperative defense in depth only, **not** independent adversarial tenant isolation. End-to-end production IAM, full object authorization, impersonation controls and separate DB-role security review remain gate blockers.
- Denial logging is **opt-in** at this stage; the production composition root must require a sink and the trusted authentication boundary must separately audit unauthenticated requests. No promise of complete security auditing.
- Backpressure, consumer durability, publisher timeouts, dead-letter replay governance, concurrency/load qualification, migration restore/rollback and external monitoring remain outstanding.

## Verification

Run local unit suite: `PYTHONPATH=src python -m pytest -q tests/unit`.
CI database proof: PostgreSQL 16 Python 3.11/3.12, `tests/integration/company_configuration`, with test runtime and dispatcher roles, and Ruff. Record the exact SHA after the workflow succeeds. G0/G1/G2 remain unsigned.
