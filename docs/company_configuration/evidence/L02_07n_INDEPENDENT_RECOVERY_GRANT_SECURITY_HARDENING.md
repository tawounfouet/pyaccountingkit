# FND-C03 / L02-07n — Independent one-use SQL recovery grants

**State:** development candidate / G2 NOT APPROVED / not a live IAM integration.  
**Scope:** only recent `tawounfouet/pyaccountingkit`.  
**Parent:** standalone Foundation consolidation PR #27, with migrations 0001–0013 immutable.  
**Finding:** a holder of `cc_iam_recovery` could call SQL `cp_redrive_dead_iam_ack` directly with fabricated actor/checker/approval claims, skipping Python's Ed25519 verifier.

## Security goal

Compromise of **only the `cc_iam_recovery` credential** must no longer reactivate an IAM ACK queue item without a separately granted, short-lived SQL capability. An explicit, nondelegated `cc_iam_approval_writer` login is required for independently validated issuance; the recovery login has no grant issuance, DDL, audit write or protected-table rights.

## Implementation (migration 0014)

1. Append-only `privileged_iam_ack_recovery_grants` table, unique approval reference and `(event_id,redrive_number)`. Each grant pins **event, request, tenant, actor, independent approver, approval ref, evidence ref, reason, exactly next redrive number and expiration**. No unscoped wildcard grants.
2. Dedicated `cp_grant_iam_ack_redrive` SECURITY DEFINER procedure: strict `session_user = cc_iam_approval_writer`, exact-scope DEAD row, max 5-minute TTL, serialized on queue row lock. No broad table write privilege granted to the writer.
3. Replace only the executable body of `cp_redrive_dead_iam_ack` via CREATE OR REPLACE (preserve its signature, not the historic migration file). It requires `session_user = cc_iam_recovery`, a matching **unexpired** grant, the next redrive number and a row lock. An append-only `privileged_iam_ack_recovery_consumptions` event is inserted **in the same transaction** as the previously existing decision evidence and DEAD → RETRY mutation. Atomic rollback also rolls back grant consumption.
4. The Python recovery SQL capability check refuses a login that can issue independent grants.
5. An **independent** writer adapter accepts typed verified actor and recovered approval values, checks equality and validity, then uses the dedicated SQL grant issuer. The Application-level `IamAckRecoveryApprovalIssuer` verifies the actor, action-specific current grant, exact signed approval and SoD, and rechecks permission, approval and time **immediately before** writing. It must be composed with authoritative signed-approval/current-grant providers in a physically separate workload. The normal recovery service is **not** given approval-writer credentials; it fails closed when no grant exists.
6. CI provisions a dedicated writer role. Direct SQL credential-bypass, replay, tamper, cross-role, expiry bounds and concurrent re-drive tests verify restrictions.

## Threat model: exact security claim

| Attack/Failure | Expected invariant |
|---|---|
| Stolen recovery SQL credential alone; fabricated actor/reviewer/approval | **DENY**, no grant, no DEAD → RETRY, no decision |
| Recovery login calling grant issuer | **DENY** (SQL privilege + session identity) |
| Approval writer directly calling redrive | **DENY** (SQL privilege + session identity) |
| Approval valid for other event/tenant/actor/checker/reason | **DENY** despite a valid SQL grant for a different exact scope |
| Approval replay | **DENY** (unique consumption and monotonic redrive count) |
| Concurrent consumers of one approval | At most one successful queue transition |
| SQL failure after grant lookup but before commit | Atomic rollback: no orphaned consumed grant or decision |
| Grant issuer's expired or overlong TTL | **DENY** |
| Owner/superuser takeover or colluding compromise of *both* independently operated SQL roles | **OUT OF SCOPE for this increment** |

## Remaining G2 blockers / constraints

- **Crucial:** SQL does **not** verify Ed25519 signatures. Its trust anchor is an independent SQL approval-writer role, which therefore **must be operated by a separate service** performing signature checks, fresh IAM/approval/revocation checks, independent actor/SoD and durable audit before calling the writer. A `VerifiedRedriveApproval` Python dataclass is NOT proof of signer or authority. CI fakes the producer under explicit test-only trust. No production approval writer is deployed.
- The same application must **not** receive both `cc_iam_approval_writer` and `cc_iam_recovery` secrets. Credentials in the CI YAML are test-only.
- The threat that the writer service itself is compromised, the signing keys are stolen, grant issuance becomes stale due to remote IAM revocation or an admin/superuser bypasses roles is **not closed**. A 5-minute upper bound limits but does not eliminate stale authorizations; require production revocation propagation, isolated workload/network, vault, monitoring and independently audited approvals before production qualification.
- No external IdP connector, signed key management, migration rollback or disaster recovery rehearsal; these remain for later FND-C03/FND-C04 gates.
- Retained completed grants/decisions are immutable and durable; a separate retention and independent audit policy is still necessary.
- Do not modify the checksum of 0013. Test 0014 on empty and upgrade paths. All G0/G1/G2 gate decisions remain unsigned.

## Evidence

- Commit / Python CI / PostgreSQL CI: to be filled from exact-head GitHub Actions after candidate PR runs.
- Final gate: fail closed until independent security review verifies correct operational composition and separation of secrets.
