# L02-04 - PostgreSQL Transactional Inbox and Consumer-Side Effects

**Date:** 2026-10-29  
**Status:** IMPLEMENTATION CANDIDATE - G0/G1/G2 NOT APPROVED.  
**Dependencies:** PR #7 (L02-03), PR #6 (L02-02), PR #4 (L02-01), PR #3 (L00/L01).

## 1. Why the Inbox belongs in the technical kernel

`10_COMPANY_CONFIGURATION_INTEGRATION_CONTRACTS.md` section 7 requires Inbox deduplication by `(producer, event_id)` with event-schema version handling. Production events are **at-least-once**; replay can occur after an Outbox publish succeeds but acknowledgement fails. The current proposal uses an extended key `(tenant_id, consumer_id, producer_id, event_id)` to isolate multiple consumers and tenants without losing producer identity.

**Boundary:** This increment consumes the existing **internal `OutboxEnvelope`** and applies a *demonstration counter projection*. This is neither a C10 public event contract nor an implementation of `Runtime Resolution`, Ledger posting or authoritative accounting statements. It does not turn the historical `legal_entity.create/rename` events into published Company Configuration facts.

## 2. Delivered files

- `0003_consumer_inbox.sql`: append-only `inbox_receipts` with unique identity, SHA-256 payload fingerprint, event schema, and timestamp; separate mutable `inbox_projection_counts` demonstration read model.
- `inbox.py`: `PostgresInboxConsumer`, `TransactionalEventHandler` port, `CountingProjectionHandler` demonstration, typed duplicate/mismatch/schema failures.
- `scripts/setup_postgres_ci.py`: disposable, separate, restricted Inbox SQL role, **without permission to read producer Outbox, Ledger or audit**.
- `.github/workflows/postgres-integration.yml`: dedicated Inbox DSN in PostgreSQL CI; Python 3.11/3.12.
- `tests/integration/company_configuration/test_inbox_consumer.py`: PostgreSQL proof cases.

## 3. Transaction and correctness rules

1. The composition root supplies fixed tenant, consumer and producer IDs. These values are **trusted configuration**, never derived unverified from inbound JSON.
2. Validate event identity, aware timestamp, tenant and supported schema version *before connecting*.
3. Set tenant context for the transaction and issue `INSERT ... ON CONFLICT DO NOTHING` against the Inbox uniqueness key.
4. If a receipt already exists, compare the canonical event SHA-256. Matching content is a duplicate (no side effect); mismatched content is a **fail-closed identity collision**.
5. For a new event, call the trusted SQL handler **with the same database connection**. The Inbox receipt and consumer-side SQL effect commit or roll back together.
6. Concurrent duplicate inserts are serialized by PostgreSQL's unique-key conflict handling. This is a guarantee about *database effects inside the same transaction*, **not** exactly-once broker delivery or other external effects.

## 4. Acceptance tests (initial proposal)

- Successful consumption and deduplicated replay: exactly one Inbox receipt and one read-model effect.
- Outbox post-publish/pre-ack crash, followed by redelivery: same event ID; still one effect.
- Handler failure after a staged SQL effect: full rollback; later retry succeeds.
- Reuse of producer/event identity with different content: explicit digest conflict; no mutation.
- Unsupported schema and cross-tenant event: fail-closed before writes.
- Distinct producers or consumers sharing the event UUID: distinct deduplication keys.
- Concurrent duplicates: one apply and one duplicate receipt, with no lost effects.
- Least-privilege runtime role cannot read source audit or mutate Inbox evidence.
- **Adversarial regression proving that tenant GUC spoofing remains possible** with a shared role; this is a blocking negative security finding, not an authorization success.
- SHA-256 migration checksum stability and Python CI on the exact commit.

## 5. Critical limitations and G2 blockers

- A SQL role that can set `app.tenant_id` can impersonate a different tenant. The tested RLS policies are **not** sufficient for hostile-client tenant separation. An independent tenant-bound database identity/proxy and a non-spoofable authorization rule require ADR, negative attack tests and security sign-off.
- `TransactionalEventHandler` is **trusted code**; it must not call `commit()` or change tenants. Untrusted handlers, external HTTP calls and broker acknowledgement cannot be guaranteed by this transaction.
- No authenticated producer signature, verified broker identity, C10 schema registry, Runtime Resolution projections, content-hash verification via C10, consumer contract E2E or distributed transaction guarantee.
- No schema backward compatibility matrix, inbox TTL/retention rule, replay tooling, dead-letter quarantine remediation, operational metrics or N/N-1 migration proof.
- This is *per-effect SQL exactly-once within one database transaction* under stated assumptions, **not exactly-once event delivery**.

## 6. Reproduction / evidence

After applying migrations as an administrator, provision CI-only roles with `python scripts/setup_postgres_ci.py`; then run:

```bash
python -m pytest -q tests/integration/company_configuration -rs
python -m ruff check src tests scripts
```

**Exact-SHA CI result:** PENDING. Never mark tests, G2, production isolation or C10 qualified solely from code submission.
