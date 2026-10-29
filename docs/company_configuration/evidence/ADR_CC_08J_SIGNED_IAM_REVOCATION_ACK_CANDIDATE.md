# ADR-CC-08J - Signed IAM revocation receipts and pre-issuance fencing

**Status: PROPOSED.** Technical candidate only. No formal security or architecture approval.

## Context

L02-07e to L02-07i established local PostgreSQL fences, dedicated DDL/audit roles and pinned signed identity/approval evidence. They do not make an IAM revocation atomic with local SQL. In particular, the old `cp_revoke_fence` requires an existing fence, leaving a gap for revocation arriving before fence issuance.

## Decision candidate

Introduce a third independent SQL capability, `cc_iam_revocation`, which can execute only `cp_ack_iam_revocation`. Consume independently sourced and verified Ed25519-signed revocation events; atomically persist a per-request tombstone plus the local observed outcome before acknowledgement is returned to the upstream provider. Deny future issuance via owner-installed BEFORE INSERT trigger, serializing with revocation acknowledgement using a transaction-level advisory lock keyed by request UUID. Active fences are row-locked and revoked; consumed fences are marked `ALREADY_CONSUMED` **without claiming prevention**. Remote ACK failures must carry the committed local result for idempotent retry, and failed SQL mutations must never ACK remotely.

## Rejected alternatives

- Only revoke existing ACTIVE fence: cannot close revoke-before-issuance.
- ACK the remote IAM event before SQL commit: falsely reports protection that might not exist.
- Convert `ALREADY_CONSUMED` to `REVOKED`: falsifies SQL execution history.
- Accept event scope/approval from an API caller without a cryptographically trusted source: enables forged revocations.
- Declare transaction-level advisory lock a distributed IAM lease: no cross-system atomicity exists.

## Residual risks / acceptance criteria

- Live IAM event source and robust independent signature/key-rotation policy; event JTI storage and remote ACK semantics verified with actual provider API.
- Separate production receiver identity and DB credentials, physical network policy, mTLS, independent audit, tamper evidence, failover/replay/retention and monitoring.
- Verify rotation/provider policies and revocation ordering across a real network outage and prolonged latency; build an operational runbook for `ALREADY_CONSUMED`.
- Signed G0/G1/G2 and independent review of SQL `SECURITY DEFINER`, transaction locks and privilege grants before any production merge or stable release.
