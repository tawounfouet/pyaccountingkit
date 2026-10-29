# L02-07j - Signed IAM Revocation Delivery & Durable Acknowledgement

**Status:** implementation candidate, PostgreSQL 16 CI qualification pending. **Not connected to a production IAM**. No G0, G1 or G2 approval.

## Problem

L02-07i can verify signed operator and approver evidence, but an external IAM revocation is not automatically propagated to the PostgreSQL fence. A local SQL row lock cannot prevent execution unless an authorized revocation is actually delivered to the same database and acknowledged. A second hazard is falsely reporting **revocation enforced** after the operation has already consumed its fence.

## Delivered boundaries

1. Dedicated Ed25519/EdDSA **revocation** trust root distinct from operator/approval roots. Exact compact JWS claims: issuer, audience, kind, effective revoker, tenant, request UUID, approval reference, target SQL login, rotate/revoke operation, bounded issued/not-before/expiry and revocation timestamp. The token's UUID `jti` is a durable delivery identity; never use the signed token itself as proof that remote IAM is current.
2. `SignedIAMRevocationAcknowledger.apply(signed_event)` verifies the signed proof **before any SQL**, then connects as the dedicated `cc_iam_revocation` login and calls the owner-controlled PostgreSQL revocation/ACK function. No token or password is written to SQL, only SHA-256 evidence digest and canonical scope metadata. Its `repr` redacts the DSN.
3. Migration `0011_iam_revocation_ack.sql` adds an owner-only append-only receipt table and a narrow `SECURITY DEFINER` function with protected `search_path`. The function takes the same fence row lock as `cp_execute_fence()`; a successful local revocation and its receipt commit in **one SQL transaction**. One delivery ID can be retried idempotently with exact same scope and digest; conflicting replay is rejected.
4. Receipts have **three distinct statuses**: `APPLIED` (this delivery changed ACTIVE to REVOKED), `ALREADY_REVOKED` (the SQL fence was already revoked), `TOO_LATE` (the fence was already CONSUMED). Only `APPLIED` is marked `enforced=True`; a remote acknowledgement must not describe `TOO_LATE` as prevention.
5. `IAMRevocationSynchronizer` defines bounded polling and an **at-least-once** external event/ack contract. External ACK is sent **after SQL commit**. If it fails, the caller receives `IAMRevocationAckPending` and must retry, using the same signed delivery identity; the SQL receipt is idempotent.
6. CI creates an **independent** low-privilege SQL login `cc_iam_revocation`, with only EXECUTE on the revocation function. It has no direct access to fences, audit receipts or PostgreSQL role DDL. Runtime, Inbox, dispatch and SQL DDL operator do not get this grant.

## Verification scope

- Pure unit tests: signed event validation, wrong kind/issuer/audience, bad signer, bad actor/approval/target, dedicated DB login, bounded poll, remote ACK outage and retry, and exact receipt `enforced` semantics.
- PostgreSQL 16 adversarial tests: active fence to REVOKED with append-only receipt, duplicate delivery, impossible DDL replay, late revocation after CONSUMED, ALREADY_REVOKED, cross-tenant/approval rejection and capability separation.
- Exact CI SHA/workflow links to be appended only after successful jobs.

## Unresolved P0 / G2 requirements

- **No production IdP/revocation webhook adapter or signed feed is connected.** The signing keys and event source in CI are test fixtures. A production trusted transport must support authenticated issuer discovery, provider delivery offsets, durable resend and ACK semantics. The coordinator's source is a port, not an actual remote HTTP provider.
- The delegated `cc_iam_revocation` role can submit claimed event fields directly to the SQL function if its credential is compromised. PostgreSQL does **not** validate Ed25519: the signature is verified in the separately controlled Python delivery process. Strong workload identity, network egress/ingress restrictions and code review must prevent bypass.
- An IAM policy revoke not yet delivered to PostgreSQL can still race a DDL. The effective security guarantee begins only when the revocation database transaction commits. The remote provider must distinguish `APPLIED`, `ALREADY_REVOKED` and `TOO_LATE` and reconcile the latter through incident management.
- No transactional atomicity across remote IAM, backend drain, SQL role DDL, separate privileged-operation outcome audit or remote ACK. Network outage, restore, failover and multi-tenant load exercises remain missing.
- Schema owner/superuser and legacy direct PostgreSQL role operator remain privileged bypasses if their secrets leak. No real workload attestation, PAM/vault/TLS/WORM evidence, signed security ADR or formal G0/G1/G2 acceptance. **No merge or stable release claimed.**
