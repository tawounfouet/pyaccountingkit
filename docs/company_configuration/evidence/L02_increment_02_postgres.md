# L02 - Increment 02: PostgreSQL transactions and isolation

**Status:** IMPLEMENTATION CANDIDATE / NOT A G2 SIGN-OFF. Date: 2026-10-29.

## Implementation contract

- A separately installed `[postgres]` extra (`psycopg[binary]` for the proof) is optional for library users.
- Migration `0001_initial.sql` creates `legal_entities`, `idempotency_requests`, `audit_records`, `outbox_events`. Checksums are recorded in `schema_migrations` and drift is rejected. Transactional migrations must run under an explicitly provided schema owner DSN and deployment control.
- `PostgresUnitOfWork` sets the transaction-local tenant context and serializes mutations within one tenant using an advisory transaction lock. Domain and application code do not import psycopg.
- Row-level security is `FORCE`-enabled on the four domain tables. A separate, non-superuser, non-`BYPASSRLS` connection must be used for application traffic. The CI script provisions this **only for ephemeral tests**; never reuse sample credentials.
- The SQL repository performs fully scoped reads and compare-and-swap revision updates. Changes, request receipt, audit and pending outbox event commit or roll back together in the same database transaction.
- Audit and outbox SQL triggers reject UPDATE/DELETE. Runtime role does not have DELETE/TRUNCATE privileges. This is append-only logical protection, not certified WORM; privileged DBA/superuser can bypass controls.
- An outbox *record* is not an event *delivery*. No dispatcher, Kafka, subscriber, C10 schema or end-to-end consumer proof is included.

## Expected validation

CI `PostgreSQL integration (L02 candidate)` runs PostgreSQL 16 on Python 3.11 and 3.12. It must prove: migrations/checksum; create/rename persistence; exactly-once idempotency receipt replay on new connections; rollback under injection; revision conflict and concurrency; RLS default deny and tenant separation; company-scoped application access; append-only audit. **Verified (implementation SHA `fb207bc1570b5efb19a4bf8d34629f430cab26f2`)**: [GitHub Actions PostgreSQL integration run #40841545574](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40841545574) completed successfully on Python 3.11 (**9 passed in 1.18s**) and Python 3.12 (**9 passed in 0.87s**), with Ruff green. The separate [Python CI run #40841545498](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40841545498) also passed. No approved G2 gate follows from these runs.

## Residual blockers / design review

1. G0/G1 and ADR-CC-03 (database), ADR-CC-05 (atomicity), ADR-CC-08 (authorization/SoD) remain unapproved. PostgreSQL is a **candidate**, not a formally approved production choice.
2. RLS on `tenant_id` alone is not proof of entity/book level authorization; application owner and IAM integration are still necessary. End-user identity is not validated by this adapter.
3. No denied-decision durable audit, user revocation race guarantee, RLS security role review, stable C10 contracts, snapshot or outbox retry/dispatch yet.
4. A coarse tenant advisory lock may harm throughput and is not a substitute for load tests, deadlock review or more granular concurrency strategy.
5. Migration rollback/restore and compatibility N/N-1 are not tested; standalone PostgreSQL HA and permissions have not been qualified.

**No gate is passed without independently reviewed, exact-SHA evidence.**

## RLS security caveat (blocking before production)

A runtime database role capable of executing SQL can set a custom `app.tenant_id` session variable itself. Thus tenant RLS based on `current_setting()` does **not**, in isolation, protect against a compromised or malicious runtime DB connection. Its value is additional protection against accidental omissions of tenant predicates **when the application and connection are trusted**. A privileged, independently enforced tenant-bound authorization strategy (e.g. separately authorized DB roles or a trusted proxy) requires ADR, tests and security review before G2 approval. Do not label this proof `production tenant isolation`.
