# L02-07k - HTTPS IAM Connector and Durable ACK Outbox

**Status: code candidate only. Draft stacked PR; G0/G1/G2 not approved.**

## Problem addressed

L02-07j performs PostgreSQL revocation before sending an upstream ACK, but a crash between commit and HTTP ACK could leave an unsent receipt until the upstream provider redelivered its event. L02-07k places every committed IAM revocation receipt in a **transactionally enqueued SQL ACK outbox**, allowing a dedicated worker to resume without receiving the event again.

## Contract

- HTTPS origin supplied by a trusted deployer. Standard-library HTTPS transport verifies CA and hostname; redirects are disabled. Service credential is explicit and redacted from repr; response data are length-limited. No provider-specific native API or production credential is bundled.
- `GET /v1/revocations/{event_uuid}` returns an Ed25519-signed compact JWS with `Content-Type: application/jose`. The existing pinned JWS verifier validates the signed contents and scope. **Fetching over HTTPS alone does not confer IAM authority.**
- `POST /v1/revocations/{event_uuid}/acknowledgements` accepts `event_id`, `request_id`, `tenant_id`, `disposition`. The worker supplies `Idempotency-Key: {event_uuid}` and the upstream provider contract MUST deduplicate it. A 2xx response indicates delivery accepted, **not** that the remote IAM globally prevented an earlier role change.
- New `SignedIamRevocationProcessor.ingest(event_uuid)` verifies the signed event and writes the SQL revocation record **without calling remote ACK**. Legacy `process()` still directly ACKs for compatibility but **must not** be used by the durable worker topology; no claim of removal of every old call site.
- Migration `0012_iam_ack_outbox.sql`: owner-only ACK outbox table, an AFTER INSERT trigger on the append-only L02-07j receipt table, and backward-compatible backfill of pre-existing receipts. SQL commit of the original revocation and enqueue is atomic.
- Dedicated `cc_iam_delivery` SQL login: only SQL EXECUTE on `cp_claim_iam_ack`, `cp_complete_iam_ack` and `cp_fail_iam_ack`. No DDL, IAM apply/revoke function, privileged audit or direct outbox table access.
- `PostgresIamAckOutbox`: atomic claims with `FOR UPDATE SKIP LOCKED`, 30-second lease, lease tokens, retry schedule, maximum 5 attempts, stale lease rejection and `DEAD` classification.
- `IamAckDeliveryWorker`: bounded per-batch retry; no user-visible raw HTTP exception or credential persisted as failure reason. After remote ACK, marks DELIVERED; if SQL confirmation fails, lease expiry permits same event-key retry. **End-to-end delivery is at-least-once**, not exactly once.

## Negative cases and evidence

Unit: HTTPS required; redirects, non-JWS or oversized HTTP response refused; Authorization header not included in repr; POST has event-scoped idempotency key; failed network delivery never marked DELIVERED; bounded batch and DEAD accounting.

PostgreSQL 16: original receipt and ACK row commit together; failed SQL transaction produces neither; delivery lease/receipt confirmed; 5 failed ACKs transition to DEAD; stale lease token cannot complete; runtime/control-plane/audit/apply roles cannot invoke delivery functions; the delivery role has no raw table/DDL privilege; competing claims do not duplicate ACK ownership.

## Remaining blockers

1. **No live provider**: This is a concrete HTTPS protocol adapter exercised against fake transport. No vendor-specific provider endpoint, live API key, JWKS rotation or upstream delivery/receipt attestation has been qualified.
2. **No continuous worker deployment**: Workload scheduling, metrics, operational alerts and DLQ incident resolution/re-drive require a real platform/service. A persisted DEAD record must be surfaced to the incident team, not automatically replayed.
3. **No remote atomicity**: The SQL receipt may be committed after the original DDL became CONSUMED. `ALREADY_CONSUMED` remains an incident requiring review, not an IAM prevention success.
4. **No complete privileged isolation**: PostgreSQL owner, superuser and low-level raw role operator still bypass restricted service composition if privileged credentials leak; no production IAM/PAM mTLS, vault or independently signed WORM audit.
5. **Gates**: G0, G1, G2 and candidate ADR-CC-08K remain unsigned; no stable release or production security qualification.

The CI SHA, workflow IDs and counts must be appended **only after exact-head tests pass**.
