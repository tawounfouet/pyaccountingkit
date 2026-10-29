# L02-07e - PostgreSQL-local Privileged Authorization Fencing

**Status:** proposed candidate, without G0/G1/G2 or production security approval. Prior migrations 0001-0007 retain their checksums.

## Narrow guarantee

A row lock on one owner-controlled fence serializes PostgreSQL-local revocation and role DDL. The execution transaction commits ALTER ROLE, the fence CONSUMED state and the append-only CONSUMED evidence together. If SQL revocation commits first, the DDL is rejected. If DDL commits first, a subsequent revoke cannot undo it.

This guarantee holds **only for revocations propagated to PostgreSQL**, not for a remote IAM policy change that has not been delivered.

## Components and tests

- Application grant service uses trusted identity, current permission and independently verified approval ports; binds one exact request/tenant/login/operation/operator/checker/expiration.
- Privileged PostgreSQL adapter issues/revokes/consumes fences with row locks and DB clock. Exclusive ACTIVE fence per target; no replay, foreign scope or expired execution.
- Migration 0008 adds owner-only fence state and append-only ISSUED/REVOKED/CONSUMED journal. Runtime, dispatcher and Inbox are not granted access.
- Unit tests: valid approval, SoD, scope mismatch, policy denial, expiration, rejected unverified transport.
- PostgreSQL tests: SQL rotation/revocation, replay, wrong actor/approval, permission denial, row-lock race and rollback of ALTER ROLE if evidence insertion fails.

## Limitations and pending review

- A SQL row lock cannot atomically fence a **separate IAM provider**. External revocations must be propagated, acknowledged and independently tested.
- The old direct PostgreSQL role operator still exists for compatibility and would bypass these checks if exposed with an admin DSN. A separate deployed control plane, network restrictions, PAM/IdP and credential custody are **not implemented**.
- PostgreSQL owner-only append-only is not WORM. Post-commit backend drain and separate privileged-operation outcome audit are outside the DDL transaction.
- Password-bearing ALTER ROLE statements can appear in DB logs. Vault, validated TLS, log controls, recovery, load and security pen test remain pending.
- G0/G1/G2 and ADR approval require independent sign-off. No stable release, C10 or Ledger posting claim.

Attach exact SHA and Actions evidence only after workflows are green.
