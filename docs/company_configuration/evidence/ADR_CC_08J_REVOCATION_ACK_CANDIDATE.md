# ADR-CC-08J - Signed IAM Revocation Delivery / PostgreSQL-local ACK

**Decision status: PROPOSED.** No independent security or architecture signoff.

## Context

The SQL-local authorization fence serializes role DDL and database-side revocation, but it cannot observe revocations in a separate IdP until an independent delivery channel carries them into PostgreSQL. Moreover, "received" is not equivalent to "prevented" when the role DDL already consumed the fence.

## Proposed decision

Use an independent bounded-life Ed25519 signed revocation event and dedicated trusted delivery process. Validate the signature/claims with a separately pinned revocation issuer. The worker connects with a dedicated low-privilege SQL login, applies one database transaction under the target fence lock, records an append-only idempotency receipt and returns an unambiguous status. Only then may the worker ACK delivery to the external IAM. Retry after network errors is safe for exact repeated event ID/scope/digest.

Do not treat a `TOO_LATE` receipt as prevention, or a mere delivery attempt as proof of revocation. Classify it as an incident requiring independent follow-up. Original DDL evidence stays immutable.

## Alternatives rejected

- ACK the IAM event before SQL commit: can lose revocations on worker failure.
- Mark an existing CONSUMED fence as successfully revoked: false operational assurance.
- Use only memory deduplication or trusted client `jti`: retries/worker restarts are not provably idempotent.
- Give the ordinary SQL DDL or audit role access to the revocation endpoint: weakens capability separation.
- Automatically retry an already-consumed SQL role modification: unsafe and outside revocation semantics.

## Remaining decisions / acceptance

Independent external provider adapter, signed webhook/stream with acknowledged offsets, operator and approver identity lifecycle, revocation priority/SLO, actual workload secret segregation, anti-replay token binding, TLS, schema-owner/WORM custody, restore & chaos tests and production incident runbook. The SQL procedure itself is not a cryptographic verifier. Independent review, ADR approval and G0/G1/G2 decisions remain necessary.
