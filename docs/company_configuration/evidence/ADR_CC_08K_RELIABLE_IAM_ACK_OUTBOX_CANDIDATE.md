# ADR-CC-08K - HTTPS IAM Revocation Connector and Durable ACK Outbox

**Status: PROPOSED, pending architecture and security review.**

## Context

L02-07j can persist a revocation without reliably dispatching its remote acknowledgement if the process fails between SQL commit and the upstream HTTP request. Retrying the entire signed event is not guaranteed without a real source redelivery contract.

## Proposed decision

1. Persist an ACK outbox row as part of the **same PostgreSQL transaction** that inserts a durable signed revocation receipt, with an AFTER INSERT trigger and a checksum-verified forward-only migration.
2. Use a **separate restricted SQL delivery identity** with only claim/complete/fail capabilities. Workers obtain lease tokens through `SKIP LOCKED`, then attempt upstream ACK outside the SQL transaction and subsequently mark delivery. Retry with capped backoff, bounded attempts, stale lease fencing and a DEAD state.
3. Require a provider endpoint to accept **event UUID based idempotency**, because success followed by local confirmation failure inevitably causes at-least-once network delivery.
4. Separate signing/verification (`SignedIamRevocationProcessor.ingest`) from ACK dispatch. Retain the old `process` wrapper temporarily for compatibility, marking it outside the durable topology.
5. Expose a provider-neutral HTTPS read/ACK contract with a deployment-pinned HTTPS origin, no redirects, bounded payload sizes, standard CA and hostname validation, and no client-controlled URL components.

## Deliberate exclusions

A live vendor IAM/PAM connector, remote token-bound workload identity, auth policy decisions, no-network-isolation claims, provider-side idempotency proof, automatic permanent-incident re-drive, external WORM, owner-credential deprivileging and signed gate approvals remain separate work. A provider without the documented API needs an explicit adapter; do not treat this generic contract as supporting arbitrary IAM products.

## Revisit criteria

Live provider sandbox tests, independent security review, documented provider HTTP semantics, acknowledged revocation SLO, failure metrics/alerting, DLQ review/re-drive with two-person approval, owner-secret isolation, restore/failover and G0/G1/G2 decisions.
