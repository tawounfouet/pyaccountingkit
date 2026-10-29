# L02-07c - Privileged intent reconciliation and approval revalidation

**Status**: implementation candidate, no G0/G1/G2 sign-off, no production IAM/IdP approval.

## Problem and security contract

L02-07b deliberately committed an `INTENT` before privileged PostgreSQL DDL and wrote the terminal `SUCCEEDED` / `FAILED` record in a separate transaction. A crash, network break, administrative session termination, or result-audit failure can therefore leave an orphan `INTENT`. An orphan intent **does not prove** that a credential was rotated, a role was revoked, or an operation failed. Nor should an automated reconciler repeat a rotation without a fresh independent approval and an explicit security incident process.

SEC-06 (two effective actors), SEC-10 (audit of critical mutations), SEC-15 (no secrets in evidence), default deny and protected append-only evidence from the company security model remain relevant. This is a narrowed technical proof, not an approved operational policy.

## Delivered contracts

- `PrivilegedReconciliationService` re-verifies a reviewer from a trusted external identity port, confirms their authenticated tenant and independently requires a current privileged-review grant from `ReconciliationPolicyPort`; never accepts an untrusted tenant from a request as the reviewer identity.
- `PostgresPrivilegedReviewRepository.mark_stale()` selects tenant-scoped, sufficiently old `INTENT` rows without any terminal outcome (`SUCCEEDED`, `FAILED`, `CANCELLED`) and without any earlier review. It records **owner-only append-only** review evidence with `OUTCOME_MISSING` and `observed_outcome=UNKNOWN`.
- The SQL transaction uses `FOR UPDATE OF i SKIP LOCKED` with a unique request ID; concurrent reviewers do not duplicate evidence for the same intent. A security reviewer may be asked to investigate it, but the adapter has **no privileged DDL and no automatic repair** function.
- Migration `0006_privileged_reconciliation.sql` adds an immutable review table and expands terminal outcomes to include `CANCELLED`, with an updated unique terminal index so the same request cannot be both cancelled and succeeded.
- `PrivilegedRoleService.execute` rechecks the current policy and current independently resolved approval **after the durable intent and immediately before issuing DDL**. A revoked/changed/expired approval or a lost policy grant records `CANCELLED` and does not call the role operator. These are tests of dynamic ports, not a real IAM and not an atomic external authorization lease.

## Verification matrix

- Unit: scoped/reverified review identity, explicit policy permission, cutoff and bounded batch, fail-closed identity and grant, dynamic approval revocation, policy revocation and expiry between initial and final checks, unchanged approval executes once.
- PostgreSQL 16: orphan intent becomes one manual review with UNKNOWN, recent intent ignored, terminal outcomes ignored, foreign tenant cannot be reviewed by the wrong identity, two competing reviewers produce one marker, owner-only append-only protection, late outcome does not retroactively change the review, and CANCELLED is mutually exclusive with another outcome.
- Tests run Python 3.11 and 3.12 with Ruff. Record exact SHA and links only **after** observing GitHub Actions success.

## Outstanding safety and implementation decisions

1. The owner DB role is trusted; a caller with the raw owner DSN bypasses this application review service. Production needs privileged-service isolation, actual IdP and authorization adapter, security logging, and strict admin credential custody.
2. Evidence is not a source of truth for the current PostgreSQL role state. `UNKNOWN` stays unknown even if a later terminal record arrives; a human, independently privileged workflow must inspect evidence and document the resulting remediation. This module intentionally does not classify, execute, or replay DDL.
3. The second policy/approval check **reduces** but does not eliminate TOCTOU: grants can be revoked after rechecking and before `ALTER ROLE`. Implement a properly leased/transactionally fenced IAM authorization protocol and test the revocation race before G2.
4. Admin role DDL, backend/session drain, committed intent and final audit are **not atomic**. Background automation/incident response, true reconciliation workflow and independent attestation are absent.
5. No signed ADR, real approval service, IAM, MFA, vault, deployment, backup/restore, failover, full C10 consumer qualification or stable release. G0/G1/G2 remain open.
