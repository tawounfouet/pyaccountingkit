# L03-14 — ORG-5b3c3 MembershipId-Native Controlled SQL Authority

**R&D increment; not production IAM qualification.** Depends on [PR #52](https://github.com/tawounfouet/pyaccountingkit/pull/52); tracked in [issue #53](https://github.com/tawounfouet/pyaccountingkit/issues/53), [#48](https://github.com/tawounfouet/pyaccountingkit/issues/48), [#42](https://github.com/tawounfouet/pyaccountingkit/issues/42), [G3 #36](https://github.com/tawounfouet/pyaccountingkit/issues/36).

## Security gap

Migrations 0015 and 0021 protected membership append-only temporal semantics and **COMMIT-time evidence consistency**. But the ordinary tenant-bound runtime SQL role could still insert an entire coherent fabricated set of:
1. `organizational_membership_revisions`;
2. `organization_membership_requests`;
3. `organization_membership_audit`;
4. `organization_membership_outbox`.

RLS cannot establish human authorization for arbitrary same-tenant writes. ORG-5b3c3 removes that direct runtime SQL privilege and introduces an independently provisioned issuer.

## Additive PostgreSQL migration 0025

`0025_org_membership_controlled_sql_authority.sql` adds:

- The owner-managed `organization_membership_command_issuers` role-to-tenant table, with `enabled` revocation. The authority check uses **`session_user`**, not an actor string or client-set GUC, and matches `bound_tenant()`.
- Immediate INSERT triggers on all **four** membership tables and their evidence, denying even regranted ordinary runtime SQL permissions unless the separately bound issuer login is enabled.
- `register_membership_revision_controlled(...)`: narrowly scoped `SECURITY DEFINER` function with pinned search path, qualified relations, `PUBLIC EXECUTE` revoked, explicit tenant-bound issuer check, tenant lock, optimistic revision check, and one database transaction.
- The SQL command appends the native `membership_id`-typed revision plus request/audit/Outbox. 0015 parent/overlap/recorded-time revision validation, 0018 company archive/affiliation concurrency and 0021 deferred COMMIT-time evidence all remain enforced.

**Immutable migration history:** 0001–0024 byte-for-byte unchanged. Inventory expanded to 25 scripts.

## Hexagonal adapter / port decisions

The L02 `PostgresUnitOfWork` and `PostgresOrganizationMembershipRepository` remain unchanged for legal entity operations and reads. A distinct `PostgresOrganizationMembershipUnitOfWork` (dedicated issuer DSN only) adapts the existing `OrganizationMembershipService` protocol. The companion `PostgresControlledMembershipRepository` stages typed member revisions and their native evidence. At commit, one controlled SQL function performs four writes atomically, then the UoW's existing precommit hook, rollback and transaction commit execute.

The application-layer DDD authorization port, exact replay digest semantics, stale-revision failure, effective versus recorded-time model, explicit `MembershipId`, and transaction boundaries remain unchanged.

Tests and CI-only seeding use `CC_PG_ORG_MEMBERSHIP_WRITER_DSN` or `_B` for the matching tenant, never ordinary `CC_PG_DSN` or `_B`. Test roles are NOINHERIT/NOBYPASSRLS and only receive evidence/domain SELECT plus command EXECUTE, with zero direct INSERT.

## Required exact-head proof

- Authorized assign/end positive flow, evidence identity, exact replay, conflicting key, stale version and no duplicate revision.
- Concurrent identical requests and conflicting affiliations, temporal overlap, optimistic revision and monotonic recorded_at.
- Archived-company active/future membership refusal and cross-tenant isolation.
- Pre-COMMIT injected crash rolls back all four records.
- Ordinary runtime and foreign issuer cannot EXECUTE controlled command; cannot directly insert domain row or any evidence; cannot SET ROLE into issuer; disabled issuer cannot submit a command; cross-tenant actor claim fails; failed attempts persist no rows.
- Python 3.11 and 3.12, Ruff, PostgreSQL 16, migration/recovery and source/wheel/sdist 25 SQL SHA256 parity.

## Residual security limits and future cutover

The membership issuer role **can still supply an arbitrary human `actor_id`** and possesses the ability to submit authoritatively attributed membership changes. The CI SQL role separation demonstrates a *database issuer authority boundary*, **not** independently authenticated human provenance, credential isolation in deployed infrastructure, tamper-proof audit outside the DB, or safety under schema-owner/superuser compromise. The actual production deployment must keep issuer credentials out of ordinary API worker reach and provide independent IAM verification plus action-authorization/revocation before any human audit authenticity claim.

Beyond this cutover, G3 remains open for consolidation of the stacked L03 PRs, production-realistic cutover evidence and remaining organizational integrity decisions. No stable release, merge or production security certification is claimed.
