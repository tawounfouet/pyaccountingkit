# L03 — ORG-4c: Company and Establishment lifecycle transitions

**Date:** 2026-10-29  
**Scope:** standalone PyAccountingKit R&D, Company Configuration. **Not G3 completion or production security certification.**  
**Pull request:** [#40](https://github.com/tawounfouet/pyaccountingkit/pull/40), stacked on [#39](https://github.com/tawounfouet/pyaccountingkit/pull/39), [#38](https://github.com/tawounfouet/pyaccountingkit/pull/38), [#37](https://github.com/tawounfouet/pyaccountingkit/pull/37) and [#35](https://github.com/tawounfouet/pyaccountingkit/pull/35).  
**Specification:** `11_COMPANY_CONFIGURATION_ORGANIZATION_AND_LEGAL_ENTITY_MODEL.md` §5.1 and §5.3 and `07_COMPANY_CONFIGURATION_DOMAIN_INVARIANTS_AND_BUSINESS_RULES.md` (target model; these are not claims of full implementation).

## What is implemented

- Typed `TransitionCompany` and `TransitionEstablishment` commands use a canonical tenant, typed entity ID, target state, expected revision, reason, provenance, request key and correlation ID.
- Domain aggregate state machines from L03-01 are enforced by the Application Service with **optimistic version checking**, no direct cross-scope loading.
- A verified `TrustedPrincipal` with matching tenant and a separately supplied `OrganizationRegistrationAuthorizationPort` grant is required before touching persistence; no implicit role authorization.
- `PostgresOrganizationLifecycleUnitOfWork` reuses the coarse tenant advisory lock and transaction discipline of the ORG-4b registration UoW but does **not** reuse L02 legal-entity or 0016 registration receipts.
- New additive migration **0017**, previous migrations 0001–0016 untouched:
  - `organizational_company_revisions` and `organizational_establishment_revisions` contain append-only state/knowledge revisions from version 2 onward.
  - Baseline Company/Establishment table rows remain revision 1 with original status. Latest status is reconstructed by querying the highest revision in the appropriate new table.
  - Database insert triggers check parent identity, expected contiguous revision, strictly increasing `recorded_at` for subsequent changes, and allowed transitions.
  - `organization_lifecycle_requests`, `organization_lifecycle_audit`, `organization_lifecycle_outbox` store immutable typed target identity and transition evidence; RLS is based on the authenticated PostgreSQL `session_user` tenant binding. Runtime CI roles receive `SELECT, INSERT` only.
  - All writes use one SQL transaction; a simulated failure before commit leaves **zero revision/audit/outbox/idempotency rows**.
- Idempotency payload digest includes target kind/id, expected revision, target status, reason, provenance and correlation; exact replay returns the original receipt. A changed payload with the same key fails closed.
- Two concurrent identical requests serialize under the tenant transaction advisory lock.

## Proven boundaries

- The state history is **recorded-time only**. Establishment `valid_from`/`valid_to` are *not* automatically changed by operational closure; an effective-time lifecycle policy remains an explicit decision.
- Company archival does **not** yet make claims about orphaned/open memberships. An additional membership-aware archive guard must be designed and qualified for ORG-5.
- 0017 intentionally avoids an FK from revisions to baseline Company/Establishment because existing L03/L02 migration recovery fixtures need the original `TRUNCATE` behavior. Its insert trigger validates the parent, but a privileged schema-owner truncation can still cause orphan records. This is a documented migration-cutover limitation, **not equivalent to a hard FK**.
- Application paths guarantee atomic evidence, but current R&D runtime role has direct `INSERT` on revision tables. A hostile user holding that credential could bypass the Application Service audit/outbox path; sealing this via dedicated least-privileged SQL functions/roles and proving complete audited-write enforcement remains a **security hardening task** before production.
- C10 external event schema, actual broker delivery, organization merge/cession workflows, Site termination/reassignment and credential lifecycle are outside this PR.
- Neither production authentication nor actual RPO/RTO/PITR qualification is implied. Stable publication remains unqualified; package version is `0.0.0`.

## CI at code checkpoint

On code checkpoint `7815ae05edb5c5da9ffd39e8c0da98862f2a138b`, all GitHub Actions completed **SUCCESS** under Python **3.11 and 3.12**:

| Check | Per-version result | Run |
|---|---|---|
| Python + Ruff | **323 passed, 23 skipped** | [#40968566392](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40968566392) |
| PostgreSQL + Ruff | **163 passed** | [#40968566443](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40968566443) |
| Migration / rollback / restore | **6 passed** | [#40968566621](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40968566621) |
| wheel/sdist/isolated import | **17 exact SQL migrations** | [#40968566521](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40968566521) |

This table is a frozen checkpoint. Any later documentation or code commit must be checked again on its **exact head** before claiming final PR qualification.

**G3 remains IN PROGRESS.** Next: ORG-5 end-to-end scenario qualification and explicit resolution of lifecycle/archival versus active membership, physical parent integrity, and audited-write SQL privileges.
