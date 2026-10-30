# L03 / ORG-5b2b — Membership-native transactional evidence

**Date:** 2026-10-30  
**Scope:** PyAccountingKit Company Configuration, standalone R&D only.  
**PR:** [#46](https://github.com/tawounfouet/pyaccountingkit/pull/46), stacked after [ORG-5b2a #44](https://github.com/tawounfouet/pyaccountingkit/pull/44).  
**Issues:** [#45](https://github.com/tawounfouet/pyaccountingkit/issues/45) and umbrella [#42](https://github.com/tawounfouet/pyaccountingkit/issues/42).  
**Status:** incremental candidate; no stable release or G3 production gate claim.

## 1. Why the legacy evidence was insufficient

ORG-4a initially reused the L02 `ChangeReceipt` and `audit_records`/`outbox_events` infrastructure. Their `entity_id` is a **LegalEntityId** and their `revision` originated in the legal entity event context. A legal person can have several independent membership identities and historical membership revisions. Joining on a LegalEntityId and revision would be ambiguous and could wrongly accept unrelated evidence.

The solution is a dedicated typed membership stream. It does **not** make membership imply ownership, equity participation, consolidation, or autonomous books.

## 2. Application and DDD contract

- `MembershipChangeReceipt` exposes `membership_id: MembershipId`, `company_id: CompanyId`, `legal_entity_id: LegalEntityId`, `revision`, `correlation_id`, `audit_id`, and `event_id`. The target is **the membership**, not the legal entity.
- `MembershipTransactionEvidence` binds the immutable membership revision to its actor/action/idempotency key/digest/reason and receipt. It validates matching identifiers and revision, with `assign` only for revision 1 and `end` for subsequent revisions.
- `OrganizationMembershipService` retains explicit `AuthorizationPort`, `TrustedPrincipal`, tenant/company/legal scope, UTC Clock, business-effective dates, idempotency and optimistic revision guards. Its request lookup and evidence write now use membership-specific methods on the existing transaction-bound `PostgresUnitOfWork`, leaving unrelated L02 LegalEntity operations intact.
- The repository appends the membership revision and the UoW appends **all three evidence rows** before a single COMMIT. Crash or rejected SQL constraints roll the whole transaction back. Replay returns the original typed membership receipt without a new write.

## 3. PostgreSQL 0021 (additive)

Migration `0021_org_membership_commit_evidence.sql` adds:

| Table | Semantics |
|---|---|
| `organization_membership_requests` | Unique tenant/actor/action/request key; digest, original immutable receipt, unique tenant/membership/revision |
| `organization_membership_audit` | Verified-by-application actor and reason, typed membership/legal/company, revision before/after, effective interval, source and recorded instant |
| `organization_membership_outbox` | Membership target ID, revision, kind, exclusivity, effective interval, provenance, recorded instant, correlation, schema version |

These tables use authenticated SQL `session_user` tenant RLS and append-only triggers. Only scoped `SELECT/INSERT` rights are granted to disposable CI runtime roles.

The **deferred constraint trigger** on `organizational_membership_revisions` checks, at COMMIT, that the specific `(tenant_id,membership_id,revision)` matches a request, audit and outbox joined on the request's original `audit_id` and `event_id`. Tenant, action, company/legal identity, temporal interval, source, kind/exclusivity and recorded timestamp must all agree. A missing or inconsistent chain rejects the transaction with SQLSTATE `23514`.

Migrations `0001..0020` remain unmodified. Packaging and recovery inventory advances to **21**.

## 4. Positive and negative qualification scope

- Positive: assign → revision 1, end → revision 2, same-tenant historical as-known reads, exact idempotent replay, stale revision rejection, cross-tenant authorization denial, concurrent duplicate request, transaction failure rollback.
- Positive: events contain `membership_id` and explicit company/legal references; the event revision is **not** the legal entity revision.
- Negative: raw SQL valid-looking new membership without evidence → fails at COMMIT.
- Negative: raw SQL valid-looking amendment without evidence → fails at COMMIT, original evidence remains.
- Negative: raw SQL with only a matching request but no audit/outbox → fails at COMMIT.
- Existing ORG-3 SQL fixtures now use the **CI-only** seeded evidence writer (in `tests/`); none of its test-role shortcuts are shipped as production code. Existing direct SQL constraint tests still exercise invalid hierarchy and overlapping exclusive memberships.

## 5. Security and operational limits

**Evidence presence and consistency are not evidence authenticity.** A compromised runtime SQL role still has direct INSERT rights on the three evidence tables, and could fabricate an internally consistent chain. A fully trusted writer requires independently scoped privileges and verified external actor claims. That work remains **ORG-5b3**, not a claim in this PR.

Also open: physical legal parent FK and lifecycle cutover, temporal corporate succession, real C10 event protocol and publisher acknowledgements, independently provisioned IAM, privileged operations and disaster recovery. The R&D package remains `0.0.0` placeholder, not published.

## 6. Qualification policy

Record exact final HEAD SHA and four green workflows for Python 3.11/3.12: Python/Ruff, PostgreSQL, migration recovery and isolated wheel/sdist verification. Do not promote draft until the final head is actually qualified. G3 remains **IN PROGRESS**.
