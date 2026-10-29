# FND-C05 — Outbox/Inbox Reliability, Audit and Architecture Contracts

**Date:** 2026-10-29  
**Repository:** [tawounfouet/pyaccountingkit](https://github.com/tawounfouet/pyaccountingkit) (standalone recent development only).  
**PR:** [#30 — Reliability & Contracts](https://github.com/tawounfouet/pyaccountingkit/pull/30), child of #29 / #28 / #27.  
**Status:** exact-SHA technical CI proof, **not independent G2 security/release approval**.  
**Implementation checkpoint:** `eb9c9f9f62bef37418c42308058ea386e57804a1`.

## 1. Concrete defects closed

### D1 — Expired lease could be acknowledged without a competing worker

Previous `PostgresOutboxDispatcher._complete` checked `lease_token`, undelivered and non-DEAD status, **but not that `lease_until` was still in the future**. The stale worker retained a valid token after lease expiration until another worker claimed the same event. It could then mark a delivery successful outside its lease window.

**Fix:** add `lease_until > now` to the guarded UPDATE, using the already configured aware dispatcher clock. An expired completion raises `DeliveryLeaseLost`, does not mutate delivery state, and remains eligible for a new lease when budget is available.

### D2 — Crash on final attempt could exceed max_attempts

Previous `_claim` did not filter `attempts < max_attempts`. If a worker crashed before `_complete` on its last attempt, the lease expired but the next dispatcher could increment attempts again and republish beyond the configured budget.

**Fix:** in the **same PostgreSQL claim transaction**, first mark exhausted expired/unleased records as DEAD, recording bounded `last_error='LEASE_EXPIRED'` and clearing lease metadata; then claim only `attempts < max_attempts`. This does not modify source outbox events or immutable audit evidence.

This is a deliberately **bounded at-least-once policy**, not exactly-once producer delivery. A crash after external publish may cause the last event to be DEAD even though the external side effect occurred; operators must inspect and reconcile deliveries and consumer receipts before any recovery. Do not replay blindly.

## 2. Formal contracts and test evidence

| Contract | Test evidence / existing defense |
|---|---|
| No stale ACK after lease expiration, even before another worker takes over | `test_expired_delivery_lease_cannot_ack_even_without_competing_worker` |
| No publish beyond final attempt after crash; immutable source event remains | `test_final_attempt_crash_is_dead_lettered_without_extra_publish` |
| Valid unexpired final lease remains legitimate | `test_expired_last_lease_not_dead_lettered_until_it_actually_expires` |
| Already exhausted and unleased event fails shut | `test_exhausted_unleased_attempt_cannot_be_reclaimed` |
| Inbox receipt and projection are durable across separate consumer instances | `test_replay_from_new_consumer_instance_preserves_committed_projection` |
| Identical event time expressed in another timezone hashes identically | `test_event_replay_digest_is_timezone_instant_invariant` |
| Same producer/event identity with changed revision does not mutate projection | `test_same_event_identity_with_altered_revision_fails_closed` |
| Domain does not import application or infrastructure; application does not import infrastructure, SQL or network | `test_domain_does_not_depend_on_application_or_infrastructure`, `test_application_ports_do_not_depend_on_infrastructure_adapters` |
| Publisher success then ACK crash and repeat delivery | Existing `test_outbox_crash_after_inbox_commit_replays_without_double_effect` |
| Handler failure rolls back SQL Inbox receipt and side effects | Existing `test_failed_handler_rolls_back_receipt_and_partial_projection` |
| Parallel Inbox duplicates produce one SQL projection effect | Existing `test_parallel_duplicate_delivery_has_one_sql_side_effect` |
| Tenant/role spoof attempts and denial audit write failure fail closed | Existing L02-05/L02-03 tests, rerun with full PostgreSQL CI |

### Exact-code CI checkpoint

- [Python CI #40952960350](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40952960350): **SUCCESS**, Python 3.11 and 3.12, **289 passed / 18 skipped** per version, Ruff green.
- [PostgreSQL CI #40952960223](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40952960223): **SUCCESS**, PostgreSQL 16 on Python 3.11 and 3.12, **136 passed** per version, Ruff green.
- [FND-C04 Migration & Recovery CI #40952960377](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40952960377): **SUCCESS**, PostgreSQL 16 on Python 3.11 and 3.12, **6 passed** per version, Ruff green.
- Final docs/head commit has its own exact-head CI; do not assume prior checkpoint proves an untested later edit.

## 3. DDD, Hexagonal and CQRS ownership

- **Domain** contains immutable identities, value objects and aggregate invariants; no infrastructure or application imports.
- **Application** coordinates use cases, Unit of Work, commands and authorization/audit interfaces; no dependency on concrete SQL/IAM adapters.
- **Infrastructure** implements transactional SQL UoW, leased Outbox dispatcher, idempotent Inbox and denial audit.
- **CQRS/EDA** remains an implementation candidate: the Inbox's `CountingProjectionHandler` is an illustrative projection, not a validated C10 published contract or general Ledger consumer.
- Source `outbox_events` and `audit_records` are append-only; delivery and projection state are separately mutable. Producer delivery is **at-least-once**, with consumer-local deduplication only for `(tenant,consumer,producer,event)` inside the PostgreSQL transaction.

## 4. Residual limits before G2

1. **Clock fidelity:** dispatcher clock is injectable and aware, but production hosts/workloads must use independently monitored and synchronized clocks, and workers must not arbitrarily change lease/retry/max-attempt configuration between deployments without a controlled policy.
2. **Transport trust:** the sample Inbox trusts the configured producer and handler; no real broker authentication, C10 signed schema/version registry or independent consumer service E2E has been demonstrated.
3. **Handler isolation:** a trusted handler must use the supplied DB transaction without committing separately or triggering nontransactional external effects; arbitrary handler code cannot be made exactly-once by this adapter.
4. **DLQ governance:** when the final attempt's outcome is unknown, DEAD requires operator investigation and bounded manual recovery. No universal replay of financial postings or automatic inference of external delivery success.
5. **Security:** SQL recovery ticket split in FND-C03 is CI-qualified but separate IAM writer workloads/vault, signed live approval source, stolen-writer threat and production tenant/IAM review remain open.
6. **Ops and DR:** FND-C04 proved isolated logical dump/restore, not production PITR, RPO/RTO, credential/role restoration or live rolling upgrade.
7. **Review:** independent architecture/security review and written G0/G1/G2 decisions, controlled integration into the recent repo's `main` and exact post-merge CI remain pending.

**Gate decision: FND-C05 code-level reliability/architecture proofs qualified by CI; G2 NOT APPROVED.** No stable release or real external service interoperability is claimed.
