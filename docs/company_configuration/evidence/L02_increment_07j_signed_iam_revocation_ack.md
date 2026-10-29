# L02-07j - Signed IAM revocation and SQL acknowledgement

**Candidate, no G0/G1/G2 approval.** All prior migrations 0001-0010 are unchanged.

## Threat and safety boundary

A live IAM revocation delivered before the SQL fence exists must prohibit later issuance. An already ACTIVE fence must become REVOKED before a DDL attempt can acquire its lock. An already CONSUMED fence cannot be retroactively made safe; this is an incident requiring investigation. A network error after the SQL commit must not cause a false remote success claim.

## Implemented proof

- `SignedIamRevocationProcessor` consumes a **trusted independent** `TrustedIamRevocationSource.read(event_id)` with a pinned Ed25519 `revocation` signing root. Exact `jti`, request UUID, tenant, SQL login, role action, issuer, signing key, time validity, and bounded claim schema are enforced. Operator and approval signing keys are not accepted.
- The `PostgresIamRevocationRepository` requires a separate `cc_iam_revocation` SQL account and executes only the guarded `cp_ack_iam_revocation` function. No schema-owner DSN or raw table privileges.
- Migration `0011` adds an immutable, owner-only SQL revocation receipt journal; a BEFORE INSERT trigger for fences and the SQL ack function share a per-request transaction-level advisory lock. The trigger checks irrevocable tombstones; the ack function serializes SQL state changes and receipt insertion in one transaction. A duplicate **same** signed event is idempotent; a different event/scope for the same request is rejected.
- The SQL receipt is deliberately one of `TOMBSTONED` (no fence existed, future issuance denied), `REVOKED` (ACTIVE fence blocked), `ALREADY_REVOKED`, or `ALREADY_CONSUMED` (DDL had already committed; **not prevention**).
- A remote `source.acknowledge()` occurs **only after** committed SQL receipt. On remote ACK failure, `RemoteAcknowledgementIncomplete` carries the durable local receipt for idempotent retry. This is not two-phase commit and remote receipt delivery is not guaranteed by the code alone.

## Adversarial qualification

Pure tests: forged signature, key/issuer/kind confusion, noncanonical or expired signed claims, request-id substitution, replay and stable SQL disposition, SQL outage, remote ACK failure and retry.

PostgreSQL 16: revoke before issuance, revoke ACTIVE and replay, `ALREADY_CONSUMED` after actual DDL, wrong tenant/login/action, privilege isolation, and advisory-lock race protecting an unissued fence.

## Important exclusions

1. **No real IAM provider connection.** Tests use ephemeral Ed25519 keys and an in-memory trusted source; production source authentication, remote ACK protocol and retry scheduling are not implemented.
2. **No cross-system instantaneous revocation.** This design starts protecting requests **after PostgreSQL receives and commits** an authenticated event. External IAM delay and already consumed DDL remain risks.
3. **SQL receiver itself does not verify a JWS.** A compromised `cc_iam_revocation` login can submit fabricated claims to `cp_ack_iam_revocation`. Protection requires an isolated IAM receiver workload, distinct protected credentials and external source authentication.
4. **Owner/superuser remain trusted.** Owner DB primitives, migration credentials and older raw role operator remain bypasses if leaked.
5. **Operationally incomplete:** transport mTLS, outbox/retry/dead-letter for provider ACK, signed event custody, message ordering, JWKS rotation, PII review, owner-independent audit/WORM, password log policy, restore/DR/failover, and independently signed G0/G1/G2 decisions.

## Evidence

Exact implementation SHA and GitHub Actions links must be appended only after observed successful CI runs. The PR must remain draft and unmerged.
