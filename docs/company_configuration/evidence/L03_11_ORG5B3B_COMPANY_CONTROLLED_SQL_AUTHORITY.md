# L03-11 — ORG-5b3b Controlled Company SQL Authority

**Status:** R&D candidate; not production IAM / actor provenance attestation.  
**Parent:** ORG-5b3a red-team proof (PR #47). **Implementation:** PR #49.  
**Tracking:** Issues #42, #48, #36.  
**Migration:** additive `0022_org_company_controlled_registration.sql`, preserving 0001..0021 byte-for-byte.

## 1. Problem and scope

The prior design verified an internally matching Company request + audit + outbox at
COMMIT but let an ordinary tenant runtime login directly write both the
domain object and that evidence. An adversary stealing the ordinary runtime
DSN could therefore forge an internally consistent audit chain. The previous
red-team proof explicitly demonstrated this in a rolled-back transaction.

ORG-5b3b isolates **Company registration only**. It is not a generic
organization write fix: Establishment, LegalIdentifier, Company/Establishment
lifecycle, Membership, L02 LegalEntity, production IAM, and privileged schema
administration remain separate cutover work.

## 2. Trust model

| Principal / resource | Company table INSERT | Company-typed evidence INSERT | controlled SQL command EXECUTE |
| --- | --- | --- | --- |
| `cc_runtime_a/b` | **Denied by SQL GRANT cutover** | **Denied by guarded write** | **Denied** |
| `cc_org_company_writer_a/b` | **Denied** | **Denied** | **Allowed, tenant-bound** |
| Schema-owner/deployer | Privileged | Privileged | Privileged |

The CI-only writer logins are independently provisioned, have
`NOINHERIT`, `NOBYPASSRLS`, `NOCREATEROLE` and one immutable tenant
binding per login. The ordinary API login cannot become an issuer with
`SET ROLE`. Production **must** independently provision and segregate the
trusted issuer credential. Providing both issuer and ordinary app DSNs to
one compromised process defeats this separation.

`organization_company_command_issuers` is owner-managed, not writable by
runtime or issuer. A SECURITY DEFINER trigger uses the original
`session_user`, the configured issuer-to-tenant binding, and
`bound_tenant()`. It prevents Company-typed writes to all three shared
organization evidence tables, even when the runtime's legacy INSERT grants
for Establishment / LegalIdentifier still exist.

## 3. Controlled SQL command

`company_configuration.register_company_controlled(...)` runs as a
SECURITY DEFINER with pinned `search_path`, all table references
schema-qualified, PUBLIC EXECUTE revoked and **explicit independent EXECUTE
grants**. It verifies tenant-to-login issuer authority, validates the
Company registration revision, and writes:

1. `organizational_companies`
2. `organization_command_audit`
3. `organization_command_outbox`
4. `organization_command_requests`

All four statements execute inside one PostgreSQL transaction. The existing
deferred evidence guard from migration `0020` still revalidates the
complete relationship at COMMIT. A failure rolls back all four rows. The
existing tenant advisory lock serializes idempotency lookup, first write and
concurrent commands within one tenant.

The Python `PostgresOrganizationRegistrationUnitOfWork` stages Company
and its evidence then calls this controlled SQL function on `commit()`.
It retains legacy direct SQL for Establishment and LegalIdentifier pending
their separate migration. An explicit `company_uow_factory` is injected
into `OrganizationRegistrationService`; there is no silent fallback to
an unrestricted admin DSN.

## 4. What is and is not proven

**Proved by intended CI acceptance:**
- Company request through independently provisioned issuer succeeds with
  one registration, one request receipt, one audit record, and one outbox event.
- Idempotent exact replay returns original receipt without duplicate
  evidence; changed command digest fails.
- Injected fault before commit rolls back the complete transaction.
- Normal runtime SQL DML and forged Company-typed evidence fail with
  `42501`; no Company SQL function EXECUTE privilege.
- The issuer itself lacks direct table INSERT, and ordinary runtime cannot
  escalate into it.
- Existing tenant RLS isolation is retained.

**Not proven or intentionally outside scope:**
- A human actor was authenticated by external IAM: `TrustedPrincipal`
  remains an application-level abstraction; the issuer SQL function receives
  an `actor_id` string. If the independent issuer service/credential is
  compromised, it may still assert an arbitrary actor.
- Cryptographic nonrepudiation or protected evidence outside the database.
- Generic least privilege of Establishment, LegalIdentifier, Membership
  and lifecycle; these remain in issue #42.
- A production deployment has actually isolated the issuer and runtime
  credentials (this repo only includes ephemeral CI role provisioning).
- Privileged database schema owner/superuser compromise.

## 5. Qualification and rollout

- Verify full Python 3.11 and 3.12, real PostgreSQL 16 tests, migration
  `0013→0022` recovery/dump-restore, and identical 22 SQL migrations in
  wheel/sdist, on **exact PR HEAD**, before review-ready.
- Run the negative red-team tests using *ordinary tenant login* without
  administrator privileges. Check no business/evidence rows persist after
  failures. Keep the distinct issuer login as an explicit dependency.
- The database migration creates guards and the SQL command, but does
  **not** dynamically create or grant credentials. The deployer must
  provision and bind external authorized issuer roles, then revoke old
  direct Company INSERT grants. CI does so in `scripts/setup_postgres_ci.py`.
- A deployment with the migration but **without provisioning an issuer**
  intentionally refuses new Company registrations (fail closed).
- Never merge the whole L03 stack before G3 exact-main qualification.

## 6. Follow-up ORG-5b3c

Apply the same trust-boundary design to Establishment, LegalIdentifier,
Company/Establishment lifecycle and MembershipId-native membership. Remove
the remaining domain/evidence runtime INSERT grants only after each use case
has a replacement authorized command boundary. Use explicit role
provisioning and credential rotation/revocation tests. Require a real
verified IAM or independently attested actor provider before claiming
individual actor attribution in production.
