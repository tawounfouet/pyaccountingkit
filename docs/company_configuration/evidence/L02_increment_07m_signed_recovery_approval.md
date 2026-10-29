# L02-07m - Signed Manual Recovery Approval & Fail-Closed Recovery Composition

**Status: implementation candidate. Not a production IAM integration, an approved ADR or a signed G0/G1/G2 gate.**

## Motivation and scope

L02-07l provided a SQL owner-controlled, append-only, two-person manual DEAD-letter re-drive, but its application `RecoveryApprovalPort` had only fake implementations. The SQL function accepts actor and checker strings furnished by the authorized SQL caller; it does not verify a remote approval. L02-07m provides a concrete pinned Ed25519 signed approval adapter and a SQL-capability-validated composition without changing SQL migration 0013 or altering the previous role grants.

## Implementation

- `SignedRecoveryApprovalVerifier` reads the compact signed proof only from `TrustedApprovalEvidenceSource` (independent source), verifies Ed25519 (`alg=EdDSA`) using the **dedicated** `kind=recovery_approval`, the expected issuer/audience/kid, canonical timestamps and exactly enumerated claims. Never accepts a client-supplied unsigned approval object.
- Scope includes **approval reference, event UUID, request UUID, tenant ID, immutable incident evidence reference, reason code, independent checker ID, signed issued_at/expires_at**. The proof cannot outlive the outer JWS envelope. Algorithm swaps, unknown keys, modified payload, foreign scope, expiry and self-approval fail closed.
- `SignedOperatorIdentity` authenticates the actual recovery operator through a distinct pinned signer; the unchanged `IamAckRecoveryService` verifies fresh policy and approval **twice** before calling SQL and rejects same-actor checkers. A later approval change cancels the operation.
- `SignedRecoverySettings.from_environment()` rejects privileged owner/runtime/delivery/control-plane DSNs in its input, requires a **remote PostgreSQL TLS `verify-full`** endpoint with the `cc_iam_recovery` login, and enforces separate operator and checker trust roots. No automatic environment or network access occurs at construction.
- `build_signed_restricted_recovery_service()` additionally opens the DB connection and checks the authenticated `session_user`, the absence of owner/role privileges, lack of table read and fence execution/ACK delivery grants, and the narrow recovery procedure grant. It composes the live SQL repository only after these checks.

## Tests and negative constraints

- Pure Python: independent valid signature, foreign event/request/tenant/evidence/reason, wrong JWS signer/algorithm, expiry and envelope mismatch, self-approval, source unavailable, changed approval between the two reads, revoked current policy, forbidden privileged DSNs, missing TLS and shared signing roots.
- PostgreSQL 16: signed operator + independent signed checker for an actual `DEAD` -> `RETRY` recovery and immutable SQL journal entry; forged signer denies before SQL; dedicated recovery login allowed and owner/delivery credentials denied by live SQL capability validation.
- No new SQL migration or privilege grant in this slice. Existing `0013` remains the durable unique approval and two-re-drive enforcement.

## Residual G2 blockers

1. The independent approval source in tests is in-memory and both signing keys are generated only for tests. **No production IdP/PAM/approval system is connected.** `TrustedApprovalEvidenceSource` is still a port, not an attested network connector.
2. A stolen `cc_iam_recovery` SQL credential can bypass the Python approval verifier and call the security-definer function with fabricated identities/approvals. **Actual workload/network/credential isolation, approval attestation at the SQL boundary, and independent custody are unproven.**
3. JWS verifier does not provide online revocation, mTLS proof-of-possession, durable JWT ID replay prevention, JWKS rotation, or external WORM attestations. SQL unique approval reference and max-two redrives provide only database-local controls.
4. A successful ACK re-drive is **not** evidence that SQL role DDL was prevented, a `DEAD` incident was closed, or an `ALREADY_CONSUMED` event was remediated.
5. The delivery process still needs independently deployed supervision, metrics/alerts, secrets/TLS/logging, provider idempotence verification, failover/restore and G0/G1/G2 security/architecture sign-offs. Draft PR remains unmerged, no stable release.

**Exact implementation SHA and CI workflow results:** append only after observing completed success for Python 3.11/3.12 and PostgreSQL 16.
