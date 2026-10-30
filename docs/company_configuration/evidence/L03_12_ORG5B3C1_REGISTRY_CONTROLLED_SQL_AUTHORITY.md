# L03-12 — ORG-5b3c1: controlled Establishment and LegalIdentifier SQL authority

**R&D increment.** Parent: PR #49 (ORG-5b3b Company). Migration: `0023_org_registry_controlled_registration.sql`. Tracking: issues #42, #48, #36. Historical migrations `0001..0022` unchanged.

## Problem and trust boundary

The direct tenant-bound `cc_runtime_*` PostgreSQL login still had `INSERT` permissions for `organizational_establishments`, `organizational_legal_identifiers` and shared registration request/audit/outbox evidence after ORG-5b3b. Deferred COMMIT proof checks only completeness and consistency. A forged but coherent set would pass if the same SQL login could insert all records.

This increment introduces a **separate registry issuer** for establishment and legal-identifier registration. There is still **no independently attested human identity**. The new SQL issuer role can submit a caller-specified `actor_id`; only independently provisioned credentials plus external IAM control can make that claim trustworthy.

## Database write contract

- `organization_registry_command_issuers` is owner-managed and binds original `session_user` to exactly one tenant with an explicit `enabled` switch. No ordinary runtime writes or issuer writes to this table.
- `require_org_registry_issuer` denies mismatched/unbound/revoked identities, with `42501` (not a caller-controlled session GUC).
- Immediate insert triggers on `organizational_establishments`, `organizational_legal_identifiers`, and the **two new target_kind subsets** of the shared `organization_command_requests/audit/outbox` tables deny direct API runtime insertions even where compatibility grants remain.
- `register_establishment_controlled` and `register_legal_identifier_controlled` are owner-defined SECURITY DEFINER SQL commands, each with pinned `search_path`, schema-qualified objects, and `PUBLIC EXECUTE` revoked. Both perform tenant-bound issuer validation and the tenant advisory lock.
- Within one local transaction they write target row, organization audit record, organization Outbox event, and immutable idempotency request. The historical deferred registration evidence guard in migration `0020` remains in force at COMMIT.
- CI-only `cc_org_registry_writer_a/b`: own tenant binding, `NOINHERIT NOBYPASSRLS NOCREATEROLE`, scoped `SELECT` on request/audit/outbox for evidence checks, `EXECUTE` on two SQL commands, **no direct INSERT**. `cc_runtime_a/b` have domain `INSERT` explicitly revoked and cannot call either SQL command.

## Python composition

`OrganizationRegistrationService` accepts an explicit `registry_uow_factory`, kept separate from `company_uow_factory`. `PostgresOrganizationRegistrationUnitOfWork` stages a typed Establishment or LegalIdentifier and matching native evidence, then executes the one controlled SQL statement at commit. Existing business validation, idempotent replay, tenant binding and rollback apply to the same SQL transaction.

This does **not** make direct SQL writer credentials safe to share with an ordinary runtime process. The repository's CI-only credentials are illustrative and must never be reused in production.

## Qualification gates

Require exact-head CI on Python 3.11 and 3.12 for Python/Ruff, live PostgreSQL, migration/recovery (fresh / 0013→0023 / dump-restore) and packaging (23 SHA256-identical SQL migrations in source/wheel/sdist). Regression/adversarial tests must demonstrate:

1. Authorized Establishment and LegalIdentifier registration succeeds with a coherent immutable request, audit and Outbox; replay/rollback/collision, parent existence and concurrency still hold.
2. Ordinary runtime cannot `INSERT` targets or their evidence; cannot `EXECUTE` functions or `SET ROLE` into the issuer.
3. Registry issuer has `EXECUTE` but not arbitrary domain/evidence `INSERT` or access to Company issuer commands.
4. Cross-tenant and revoked issuer use fails closed; failed statements persist no forged rows.

## Explicit exclusions

- Lifecycle revisions (Company/Establishment) and MembershipId-native affiliation writes still have broad runtime grants and need ORG-5b3c2/c3.
- L02 LegalEntity remains independent; no migration to its evidence tables is made here.
- A compromised registry issuer can still assert an arbitrary human actor. R&D SQL login separation is **not** a production IAM authentication proof, HSM signature, independent append-only audit storage, or non-repudiation.
- Schema-owner/superuser compromise and production credential distribution are outside this PR; do not close ORG-5b or G3 or claim a stable release.
