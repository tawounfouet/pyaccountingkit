# ADR-CC-08D - Privileged Incident Decision and Control Plane

**Status: PROPOSED / NOT APPROVED**

## Context

A privileged SQL role operation writes an INTENT, executes DDL/terminates sessions, then separately writes terminal audit evidence. L02-07c detects orphaned INTENT and records an immutable manual review with observed outcome `UNKNOWN`. Inferring success or reissuing a role operation from that marker would be unsafe. A privileged incident control plane requires explicit action decisions with independent approval and a durable provenance trail.

## Candidate decision

1. Introduce a distinct incident decision workflow; its execution authority is confined to owner-only **audit INSERT**. It is **never** granted a PostgreSQL role mutation operation or exposed as a generic administrator endpoint.
2. Require trusted operator verification, current tenant and disposition grant, external exact-reference approval, evidence pointer and a timezone-bounded approval window. Apply effective actor SoD between original role actor, orphan reviewer, incident investigator and incident checker.
3. Persist one append-only disposition per reviewed UNKNOWN incident. Permit only `ESCALATED`, `REMEDIATION_REQUIRED` and `INVESTIGATION_DOCUMENTED`. Preserve `UNKNOWN` until independent evidence establishes a historical SQL result in a separate controlled process.
4. Denied verified operators are recorded through an independent owner-only denial journal; no credential material in either table.
5. Use PostgreSQL transaction, lock and unique constraint to prevent two reviewers making two disposition decisions about the same manual review.

## Alternatives rejected for this increment

- Auto-retry the privileged DDL when its INTENT lacks terminal evidence: not safe or necessarily idempotent.
- Treat current `pg_roles` state or an incident-disposition label as a definitive account of the historical mutation: not justified by the available evidence.
- Let an operator attest and approve their own incident disposition by switching roles: violates effective identity SoD.
- Place the owner DSN or IAM approval port in a general tenant request process: unauthorized privilege escalation risk.

## Acceptance gates still open

An independently operated IdP/IAM/approval service, cryptographic evidence provenance and independent retention, protected control-plane deployment, authorization locking or leased fencing, valid statement-log/TLS policy, cross-region DR, alerting and a signed ADR/security review are needed before G2 or production acceptance. **CI is necessary but insufficient.**
