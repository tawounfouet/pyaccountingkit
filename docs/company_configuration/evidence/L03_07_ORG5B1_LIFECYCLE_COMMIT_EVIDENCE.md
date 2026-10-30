# L03 / ORG-5b1 — Lifecycle evidence required at SQL COMMIT (R&D)

**Date:** 2026-10-30  
**Status:** incremental PostgreSQL evidence enforcement; **not complete ORG-5b / G3**.  
**PR:** [#43](https://github.com/tawounfouet/pyaccountingkit/pull/43), stacked on [#41](https://github.com/tawounfouet/pyaccountingkit/pull/41).  
**Tracker:** [ORG-5b #42](https://github.com/tawounfouet/pyaccountingkit/issues/42).

## 1. Problem observed

The tenant-bound SQL runtime role already had `INSERT` rights on `organizational_company_revisions` and `organizational_establishment_revisions`. Earlier migrations 0017 and 0018 checked the allowed transition, contiguous revision, history and company/membership coupling. **A valid-looking direct SQL lifecycle revision could nevertheless be committed without application request, audit or outbox.**

The R&D command path did write those records atomically, but that is an **Application Service guarantee**, not a SQL-wide guarantee. This increment closes that specific evidence-presence gap for lifecycle revisions.

## 2. Additive migration 0019

`0019_org_lifecycle_commit_evidence_guard.sql` adds a PostgreSQL **DEFERRABLE INITIALLY DEFERRED CONSTRAINT TRIGGER** to both organization lifecycle revision tables.

At commit, the trigger requires the **same tenant, typed target ID, action, revision, prior/new status, actor, correlation and recorded timestamp** to be represented consistently across:

- `organization_lifecycle_requests` (idempotency request)
- `organization_lifecycle_audit` (actor, reason, transition)
- `organization_lifecycle_outbox` (event identity, transition)

The request must bind the **exact audit_id + event_id** in these tables; those records must match the actual inserted lifecycle revision. The previous status is resolved from the baseline row for revision 2, and from revision N−1 for later transitions. If any required evidence is absent/inconsistent, **SQLSTATE 23514** is raised when PostgreSQL attempts the commit and the transaction rolls back.

All SQL 0001–0018 source bytes remain unchanged. No schema backfill was performed. Read/RLS and source/wheel/sdist inventory now require **19 migrations**.

## 3. Explicit proof matrix

| Scenario | Expected outcome |
|---|---|
| Runtime role inserts valid Company `DRAFT→ACTIVE` directly without evidence | **COMMIT rejected**, zero new rows |
| Runtime role inserts valid Establishment `PLANNED→ACTIVE` directly without evidence | **COMMIT rejected**, zero new rows |
| Direct Company transition with audit and outbox but no idempotency request | **COMMIT rejected**, all staged records rolled back |
| Direct Company transition with request and audit, but mismatching outbox state | **COMMIT rejected**, all staged records rolled back |
| Authorized `OrganizationLifecycleService` command + replay | **COMMIT succeeds**, exactly one revision + request + audit + event |

The new SQL triggers test presence and internal consistency; existing R&D tests still cover domain state machine, optimistic revision, tenant RLS, archive/membership race, rollback, and explicit prior business dates.

## 4. Security boundary and remaining ORG-5b work

**This does NOT establish independent actor authentication or authorized evidence provenance.** Runtime roles can currently directly `INSERT` into request/audit/outbox tables, so a compromised tenant credential could fabricate all matching records. These triggers close the *silent bare lifecycle INSERT* gap, **not** malicious fabrication of the entire evidence chain.

There are also open insertion paths for Company/Establishment/LegalIdentifier registration and organization memberships that are **not** covered by this lifecycle-specific deferred check. A future additive migration and least-privileged write contract need to remove direct credentials' ability to forge attestations. Distinct audited, scoped SQL write entrypoints and independently trustworthy actor provenance require explicit design and live negative qualification.

Other G3 scope remains open: L02 legal-entity parent lifecycle/FK cutover, temporal succession/merger golden cases, C10 external event authenticity/publisher, production IAM and PITR/restore testing. No stable release or production qualification is asserted.

## 5. Patterns and design

**DDD**: business transitions from immutable Domain aggregates; **Application Service + Hexagonal Port**: actor authorization and UoW orchestration; **Transactional Outbox / Idempotency Receipt**: durable evidence; **PostgreSQL Deferred Constraint Trigger**: database-level transaction invariant; **Fail Closed**: abort on evidence mismatch; **CQRS**: explicit command path vs projection. The SQL guard protects the legacy Application Service from silent direct lifecycle writes without changing its public command contract.

## 6. CI checkpoint

Record and verify the final PR head's Python 3.11 and 3.12 Python/Ruff, PostgreSQL, migration recovery, and wheel/sdist workflows; intermediary commit runs alone are not final-head evidence. Package version remains `0.0.0` development placeholder.
