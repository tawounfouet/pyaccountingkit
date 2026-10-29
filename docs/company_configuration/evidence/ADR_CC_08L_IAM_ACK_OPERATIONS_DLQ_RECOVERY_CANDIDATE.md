# ADR-CC-08L - Privileged IAM ACK Delivery Operations and DLQ Recovery

**Status: PROPOSED.** Green automated tests do not approve this architecture or G2.

## Candidate decision

Use a foreground, externally supervised worker with bounded polling and non-sensitive aggregate telemetry, and a **separate recovery SQL capability** for manual re-drive of `DEAD` ACKs. Recovery must be authorized by the current tenant policy, independently approved by a distinct effective person, scoped to one event/request and incident evidence, and recorded in an append-only decision row atomically with the SQL transition. Limit the number of manual re-drives to two; forbid replaying approval references. Retain event-ID idempotency across retries.

## Security and failure rationale

- A delivery worker must never receive the recovery or schema-owner credential. The recovery role has no ability to execute role DDL, apply IAM revocation, complete ACK delivery, or directly update the outbox.
- Redrive decisions MUST be append-only, and the journal insertion plus state transition MUST be one transaction. Failed audit writes must not reactivate DEAD work.
- The caller-provided actor/approval strings are independently verified **only in the application port**. The SQL routine does not verify IAM signatures. This is therefore a candidate service-level isolation boundary, not database-proven nonrepudiation.
- HTTP duplicates after a crash are expected and require provider-side idempotent acceptance; no exactly-once claim is made. ALREADY_CONSUMED represents post-DDL incident exposure, not successful prevention.
- Aggregated metrics are readable by the delivery account, but scoped incident details are not.

## Rejected options

- Automatically reset every DEAD item on a timer: bypasses human incident investigation and may flood a provider with permanent rejections.
- Let the delivery login perform recovery: would erase separation of duties and enable immediate re-drive after five failures.
- Unlimited retries or erased attempt history: prevents bounded operational escalation.
- Report healthy state when metrics/telemetry fail: conceals a security-sensitive backlog.

## Approval dependencies

Separate network/workload deployments and secret provisioning; a real independently verified recovery approval; operator/approver identity binding; external alert pipeline and supervised scheduler; provider idempotency and IAM integration; approval of incident runbooks, independent SQL/security review, G0/G1/G2. Until accepted, keep the PR draft and unmerged.
