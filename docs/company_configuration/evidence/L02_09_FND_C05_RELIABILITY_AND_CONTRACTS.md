# FND-C05 — Reliability and Contracts qualification

**Date:** 2026-10-29  
**Repository:** `tawounfouet/pyaccountingkit` recent standalone Foundation (L00–L02).  
**Basis:** [FND-C04 PR #29](https://github.com/tawounfouet/pyaccountingkit/pull/29); this is a narrowly scoped improvement, not Ledger posting, external C10 contract or a certified delivery guarantee.  
**Status:** Automated CI-qualified implementation candidate; **G2 acceptance pending**.

## 1. Risks observed in concrete code

1. **Expired lease ACK:** `PostgresOutboxDispatcher._complete` checked the unique lease token but did not compare the lease expiry to the clock. If a slow worker resumed after its lease expired and nobody had reclaimed the record, that stale worker could still mark it delivered.
2. **Exhausted crash budget:** the dispatcher retried abandoned claims after their lease expired, even when attempts had reached the configured `max_attempts`. The crash-after-publish case could be retried without a terminal bound.
3. **Full SQL connection passed to Inbox handler:** `PostgresInboxConsumer.process` handed a raw `psycopg.Connection` to the handler, allowing an accidental `commit()` to escape receipt/projection atomicity. The documentation said the handler MUST NOT commit, but the interface did not enforce it.
4. **Architecture regression risk:** application/domain boundaries were not comprehensively exercised as explicit automated dependency tests. Existing tests checked a limited domain framework-import list.

## 2. Changes (no SQL migration required)

- **Outbox token AND lease fencing:** only the current, **unexpired** lease can acknowledge/fail the delivery. A stale completion raises `DeliveryLeaseLost` rather than falsely reporting success. This uses the same trusted clock as claim time; production clocks need operational synchronization controls.
- **Bounded delivery attempts:** expired claims at the attempt limit become `dead_letter_at` with classified error `LEASE_EXPIRED` and cleared lease metadata. Claim queries exclude exhausted items. The returned `DispatchResult.dead_lettered` includes these terminalized expired leases; immutable `outbox_events` and audit records remain unchanged. Publication remains **at least once**, not exactly once; ambiguous post-publish ACK failure may legitimately result in a DEAD item requiring incident review.
- **Inbox transaction-bound port:** replace handler access to `psycopg.Connection` with an `InboxSqlSession` command-only facade, exposing only `execute()`. Reject obvious transaction/DDL and multiple SQL statements. Handler exceptions roll back receipt and projection together. **This is a contract guard for trusted Python code, not a secure SQL or Python sandbox.** Handlers are still reviewed for semantic safety.
- **DDD / Hexagonal tests:** explicit checks that `domain` and `application` have no imports from `infrastructure` or external frameworks, consistent with Dependency Inversion.

## 3. Negative test matrix

| Scenario | Invariant |
|---|---|
| Slow publisher completes after own lease expiry, no other worker has reclaimed | Completion denied; new worker can retry with identical immutable event ID |
| Crash after broker publish on final attempt, lease expires | No sixth/infinite replay; item DEAD with `LEASE_EXPIRED`, audit/outbox source unchanged |
| Handler performs projection write then calls `connection.commit()` | No exposed `commit`, transactional rollback of receipt and projection |
| Handler attempts `connection.execute('COMMIT', ())` | Transactional control statement rejected before SQL, side effects rolled back |
| Handler writes and raises | Receipt + projection both rolled back, upstream accounting audit/outbox unaffected |
| Normal trusted handler | Exactly one projection within SQL transaction per producer/consumer/event; duplicate replay returns duplicate |
| Accidental upstream import in Domain/Application | Dependency tests reject infrastructure/framework imports |

## 4. Explicit limitations and remaining acceptance

- No **C10 schema/consumer compatibility** certificate, external broker replay guarantee, producer signature/authentication, external delivery provider, billing or Ledger posting.
- A crash after external publish may cause duplicates. Inbox deduplication is **per scoped SQL consumer database**, not globally exactly-once.
- A handler may perform arbitrary work outside the supplied SQL transaction if it is untrusted or has its own external dependencies. The facade is not a security sandbox; production handlers require code review and a restricted independent DB role.
- Outbox delivery error classification omits raw exception messages to limit credential leakage, but centralized operational logs still require independent secrets review.
- No production load/SLO/reconciliation/chaos benchmark or independent security reviewer signature. Continue G0/G1/G2 review and FND-C06 main integration.
- Prior FND-C03 IAM approval writer and FND-C04 SQL restore remain separate security/DR gates.

## 5. Proof of implementation

Implementation checkpoint `703331ae70352ea0577af749fb0cc0f09964a32b`:
- [Python CI #40953593880](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40953593880): **SUCCESS** — 289 passed, 19 skipped on each of Python 3.11/3.12; Ruff success.
- [PostgreSQL integration #40953593986](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40953593986): **SUCCESS** — 133 passed on each of Python 3.11/3.12; Ruff success.
- [FND-C04 migration qualification #40953594056](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40953594056): **SUCCESS** — 6 passed on each Python version, includes actual `pg_dump` / `pg_restore`; Ruff success.

The new integration tests include 4 additional PostgreSQL scenarios (lease expiry, exhausted lease, two manual-commit attack attempts with rollback, handler failure). The new 2 unit tests verify DDD/Hexagonal dependency direction; Python CI skips PostgreSQL-only modules by design. All three workflow conclusions were verified against the exact code/documentation snapshot above. A subsequent evidence-only commit must receive its own CI qualification.

**Gate:** FND-C05 implementation candidate, **G2 not approved**.
