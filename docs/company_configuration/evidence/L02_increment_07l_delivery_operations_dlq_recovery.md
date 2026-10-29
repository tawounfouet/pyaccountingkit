# L02-07l - IAM Delivery Operations, Metrics & Controlled DLQ Re-drive

**Status:** implementation candidate; no approved G0/G1/G2, ADR or production deployment.

## Motivation

L02-07k stores SQL ACK delivery state durably with PENDING/IN_FLIGHT/RETRY/DELIVERED/DEAD, a bounded lease and five attempts. However, DEAD lacked a controlled recovery path, and there was no bounded operational runner or low-privilege aggregate telemetry. This increment adds these features without treating a re-drive as evidence that the underlying SQL role mutation was prevented. ALREADY_CONSUMED stays an incident condition.

## Architecture / capability separation

- `cc_iam_delivery`: existing dedicated SQL role. Granted **only an additional aggregate metrics function** `cp_iam_ack_metrics()`; no new raw table grants or DEAD-letter access.
- `cc_iam_recovery`: **new** non-superuser/non-CREATEROLE/non-BYPASSRLS login (CI-only provisioning), with only `cp_list_dead_iam_acks(text,integer)` and `cp_redrive_dead_iam_ack(...)` EXECUTE. Neither the web/runtime nor IAM revocation, delivery or control-plane SQL roles get these privileges. No PostgreSQL role DDL.
- Migration `0013_iam_ack_operations_and_redrive.sql` extends the outbox with `redrive_count` (maximum 2) and an owner-only append-only `privileged_iam_ack_redrive_decisions` table. The SQL re-drive function row-locks the **DEAD** item; records the effective actor, independent checker, incident evidence, reason and attempt number; then resets its delivery state to `RETRY` **in the same transaction**. Replayed approvals, cross-tenant scopes, active items and over-limit re-drives are rejected.
- `IamAckRecoveryService` is the application security gate: a **trusted** AuthN port, current tenant/action policy, independently verified approval bound to the exact event/request/tenant/evidence/reason, two distinct effective actors, TTL and a second policy/approval recheck immediately before SQL mutation. SQL roles by themselves cannot cryptographically authenticate these identity strings, so the recovery DB credential must reside only in a separately secured control plane.
- `IamAckOperationsRunner.tick()` executes a bounded worker batch, reads aggregate metrics and requires synchronous telemetry publication. It exposes `alert_dead` for any DEAD row and `alert_backlog` for old nonterminal items. The optional `delivery_runner` foreground CLI runs one cycle (`--once`) or a supervised polling loop with bounded batch/period; **no service is deployed by this PR**.

## Operating contract

- Run the delivery process under only `CC_PG_IAM_DELIVERY_DSN`, with a separately issued IAM HTTPS credential. Do **not** mount `CC_PG_ADMIN_DSN` or `CC_PG_IAM_RECOVERY_DSN` into this process.
- A production supervisor must restart on failure, monitor metric age/DEAD counts, enforce concurrency and configure independent alert sinks and retention. The JSON console sink contains **only aggregate counters**, never event identifiers, passwords, DSNs or bearer tokens.
- For a DEAD row: inspect with tenant-bound verified identity and current permission, investigate the upstream error and any `ALREADY_CONSUMED` incident, obtain a fresh independent approval and immutable evidence reference, then re-drive. Audit the decision and SQL transition atomically. The provider MUST deduplicate on event UUID (`Idempotency-Key`); local re-drive is at-least-once, not global exactly-once.
- Any failure to persist the decision leaves DEAD unchanged and blocks automatic recovery. No automatic DEAD re-drive, no resetting the two-redrive counter, and no claim of incident closure.

## Tests and negative constraints

- Pure unit: tenant authorization, independent SoD, expiry, exact event/request/evidence scope, approval changes, second-grant revocation, bounded inspection and monitoring failure visibility.
- PostgreSQL 16: privilege separation, tenant-scoped list, dead-only redrive, append-only evidence, duplicate-approval refusal, second re-drive with new approval, third re-drive denied, concurrent decision conflict, aggregate-only metric access.
- Existing outbox `FOR UPDATE SKIP LOCKED` delivery and lease-expiry tests continue to qualify the base path.

## Explicit non-guarantees / G2 blockers

No real IAM provider or approved signed re-drive approval adapter has been integrated; the ports are demonstrated with fakes. No cloud scheduler, managed supervisor, alert delivery channel, real TLS/mTLS workload isolation, vault/PAM, immutable external WORM, provider-side idempotency certification, owner-DSN elimination or backup/restore proof. A holder of `cc_iam_recovery` can submit claimed identities unless the production deployment isolates the credential and external authorization is enforced. No signed ADR/independent penetration review, no G0/G1/G2 or stable release.

Exact-SHA CI evidence will be appended only after the new head succeeds.
