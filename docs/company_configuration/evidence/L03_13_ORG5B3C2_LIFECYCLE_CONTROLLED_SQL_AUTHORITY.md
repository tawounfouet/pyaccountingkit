# L03-13 — ORG-5b3c2 Controlled Lifecycle SQL Authority

**R&D candidate** — parent [PR #50](https://github.com/tawounfouet/pyaccountingkit/pull/50); tracking [issue #51](https://github.com/tawounfouet/pyaccountingkit/issues/51), [#42](https://github.com/tawounfouet/pyaccountingkit/issues/42), [#36](https://github.com/tawounfouet/pyaccountingkit/issues/36).

## 1. Security gap and narrowly defined scope

ORG-5b3c1 revoked ordinary SQL INSERT for Company, Establishment and LegalIdentifier registration and restricted registration evidence via owner-managed SQL login authority. The same ordinary runtime login still held direct SQL INSERT on **Company lifecycle revisions**, **Establishment lifecycle revisions**, and their three shared lifecycle request/audit/outbox tables. Consistency-verified evidence at COMMIT under migration 0019 could be forged by this single login.

ORG-5b3c2 closes this **lifecycle** SQL authority gap. It does not yet close the separate MembershipId-native membership evidence gap or independently authenticate human `actor_id` attribution.

## 2. Added database controls

Additive migration `0024_org_lifecycle_controlled_sql_authority.sql` leaves the SHA256 of migrations `0001..0023` unchanged.

- Owner-managed `organization_lifecycle_command_issuers(login_role, tenant_id, enabled)`; `PUBLIC` has no rights. Issuer granted by deployer, bound to one tenant per original `session_user`, never by an app-set custom GUC or an `actor_id` claim.
- `require_org_lifecycle_issuer(tenant_id)` and immediate row-level insert guards for both revision tables and all three lifecycle evidence tables, fail-closed with SQLSTATE `42501`. These guards still apply if runtime INSERT privileges were accidentally restored.
- A single controlled function `transition_organization_controlled(...)` with pinned `search_path`, schema-qualified tables, `SECURITY DEFINER` and **revoked PUBLIC EXECUTE**. A dedicated SQL issuer credential receives only explicit EXECUTE plus SELECT permissions needed for command reads and deferred checks; it **cannot directly INSERT any lifecycle table**.
- Every controlled command takes the per-tenant advisory transaction lock, reads current status and revision as a guard against stale optimistic state, inserts the revision, audit, Outbox and idempotency request in one transaction.
- The historic 0017 transition, timestamp and optimistic version guards, 0018 archive/membership serializing guard, and 0019 deferred COMMIT evidence constraints remain active and independently enforce valid transitions and proof consistency.

## 3. Python Unit of Work

`PostgresOrganizationLifecycleUnitOfWork` still supports typed same-tenant reads, idempotent lookup and DDD status transitions. Its append methods now **stage** typed revision/evidence instead of direct SQL inserting them. `commit()` calls the controlled SQL function, then the inherited transaction commit/pre-commit fault hook. A missing or mismatching evidence record fails without committing. The `OrganizationLifecycleService` still depends on the same UnitOfWork port (DIP): the composition root must provide the independent issuer DSN instead of a regular runtime DSN.

**The SQL principal binding authenticates the dedicated database issuer session, NOT the claimed human actor.** Production applications must keep issuer credentials outside compromised ordinary API worker reach, and attach an independently trusted IAM authentication/authorization mechanism before claiming human provenance. CI roles here are ephemeral examples only.

## 4. Exact-head qualification required

- Python 3.11 / 3.12 and Ruff on repository.
- PostgreSQL 16 integration: both DDD lifecycle positive paths, idempotent same-command replay, stale revision failure, injected pre-COMMIT rollback, concurrent transitions, archival guard against current/future memberships, tenant RLS isolation, immutable snapshots.
- Negative SQL tests: ordinary runtime has no direct lifecycle INSERT, no function EXECUTE and no SET ROLE path; independent issuer only has EXECUTE + SELECT; revocation and tenant mismatch reject a controlled call.
- FND-C04 transactional migrations: fresh, 0013→0024, checksum drift, failure rollback, concurrent migration, dump/restore.
- FND-C06: 24 exact SQL migration checksums in source/sdist/wheel, isolated Python installation. No stable release/version advancement.

## 5. Residual risk and rollout

- **ORG-5b3c3** remains for direct MembershipId-native membership revisions and request/audit/outbox.
- Schema-owner/superuser compromise, independent human IAM attestation and audit immutability outside PostgreSQL are not proven by this CI.
- A deployment must separately provision independent `cc_org_lifecycle_writer_*`-equivalent identities and their tenant bindings, then revoke legacy runtime lifecycle INSERT privileges. Incomplete provisioning refuses new lifecycle commands (fail closed).
- Do not merge the stacked L03 PRs or close G3 until exact-main security and production-aligned cutover checks are completed.
