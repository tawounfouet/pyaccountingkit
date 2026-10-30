# L03 — ORG-5b2a Registration Commit Evidence

**Date:** 2026-10-30  
**Status:** R&D candidate, **ORG-5b/G3 not closed**.  
**PR:** [#44](https://github.com/tawounfouet/pyaccountingkit/pull/44), stacked on [#43](https://github.com/tawounfouet/pyaccountingkit/pull/43).  
**Tracker:** [#42](https://github.com/tawounfouet/pyaccountingkit/issues/42) and [#36](https://github.com/tawounfouet/pyaccountingkit/issues/36).

## 1. Gap and bounded decision

Migrations 0015/0016 and ORG-4b already implement tenant-scoped legal registry and an Application Service that commits a registration, an idempotency receipt, audit and organization-specific outbox in one transaction. Those are application-path proofs; the same runtime SQL role could previously commit a direct INSERT into any of the three organization registration tables without corresponding evidence.

**ORG-5b2a** moves the *evidence presence and consistency requirement* into PostgreSQL for organization registrations. It does **not** establish trusted human actor provenance. The new rule applies to:

- `organizational_companies` — `organization.company.register`, target `COMPANY`.
- `organizational_establishments` — `organization.establishment.register`, target `ESTABLISHMENT`.
- `organizational_legal_identifiers` — `organization.legal_identifier.register`, target `LEGAL_IDENTIFIER`.

Membership revisions are explicitly excluded from this migration; the L02 outbox identifies a `LegalEntityId` and its `revision` rather than a membership-specific identity/revision. That contract needs an explicit new evidence representation before SQL commit enforcement.

## 2. Additive migration 0020

`0020_org_registration_commit_evidence_guard.sql` creates one PostgreSQL `DEFERRABLE INITIALLY DEFERRED CONSTRAINT TRIGGER` on each of the three registration tables, sharing a narrowly scoped function.

At COMMIT, each newly inserted business object must match a row in `organization_command_requests` joined by its exact `audit_id` and `event_id` to `organization_command_audit` and `organization_command_outbox`. It verifies the same tenant, target UUID and kind, action, revision=1, actor, correlation, associated company/legal entity (including NULL where not applicable), audit old/new revision, event schema version, and audit/outbox recorded timestamp.

A missing, partial or inconsistent chain yields SQLSTATE `23514`, failing the **whole transaction**, not merely a log entry. All migrations 0001–0019 remain immutable. The migration/package inventory advances to **20**.

This invariant intentionally does not re-derive cryptographic request digest authenticity nor verify external legal registry records. It depends on the RLS-scoped, append-only evidentiary tables created in 0016.

## 3. Test compatibility and direct-SQL negative scenarios

Legacy ORG-2/ORG-3 tests used a low-level `PostgresOrganizationRepository` to seed raw organization rows. Such unaudited seed paths must now fail under regular runtime roles; leaving the tests unchanged would falsely treat unaudited direct SQL as acceptable.

A **test-only** `tests/integration/company_configuration/org_test_seed.py` helper now creates fixtures using the same single-transaction `PostgresOrganizationRegistrationUnitOfWork` as normal registration commands, plus test-labeled evidence. The helper is **never imported by production modules** and is not a production IAM authority. Existing tests for membership history can continue exercising their separate, not-yet-covered SQL paths.

New integration tests must demonstrate:
1. Runtime direct Company INSERT without evidence → commit fails with no business/evidence rows.
2. Runtime direct Establishment INSERT (existing legal parent) without evidence → commit fails.
3. Runtime direct LegalIdentifier INSERT (existing legal parent) without evidence → commit fails.
4. Runtime direct Company INSERT with only an idempotency request, no linked audit/outbox → commit fails.
5. Existing ORG-4b application commands retain positive insertion, idempotent replay, tenant isolation, rollback and concurrency proofs.

## 4. Explicit remaining security debt (ORG-5b2b/5b3)

- Direct runtime credentials **can still forge the complete matching request/audit/outbox chain**. This migration guarantees internal consistency, not independent signature authority. To prevent forged evidence, split runtime read/write permissions and expose only independently authorized, audited database entrypoints or equivalent verified mechanisms.
- Membership insertions and revisions still lack `MembershipId`-specific matching audit/Outbox at the database commit boundary (**ORG-5b2b**).
- Legacy L02 `legal_entities` parent deletion/truncation is only protected by scoped insert guard for some L03 tables; FK/lifecycle cutover unresolved.
- Real identity issuance/revocation, privileged audits, C10 publisher signatures, PITR/RPO/RTO and production deployment remain outside R&D qualification.

**Conclusion intended:** `ORG-5b2a = R&D CI-qualified` only after all four workflows pass on the final SHA, with `ORG-5b = IN_PROGRESS` and `G3 = IN_PROGRESS`. No stable publication implied (`0.0.0` placeholder).
