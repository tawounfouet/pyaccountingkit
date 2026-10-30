# L03 ORG-4b — Registration Commands and Organization-native Evidence

**Status:** R&D increment. Do not claim complete ORG-4, G3, stable release or production readiness.  
**Lineage:** [#35 Domain](https://github.com/tawounfouet/pyaccountingkit/pull/35) → [#37 Persistence](https://github.com/tawounfouet/pyaccountingkit/pull/37) → [#38 Membership Commands](https://github.com/tawounfouet/pyaccountingkit/pull/38) → [#39 Registration Commands](https://github.com/tawounfouet/pyaccountingkit/pull/39).  
**Reference:** `11_COMPANY_CONFIGURATION_ORGANIZATION_AND_LEGAL_ENTITY_MODEL.md`, `08_COMPANY_CONFIGURATION_COMMANDS_QUERIES_AND_USE_CASES.md`, `07_COMPANY_CONFIGURATION_DOMAIN_INVARIANTS_AND_BUSINESS_RULES.md` — target specifications. Implementation details below describe current R&D code, not full target compliance.

## Model / ports / DDD boundaries

- `RegisterCompany` accepts an existing, immutable typed `Company` aggregate with `CompanyId`. It intentionally requires **no invented LegalEntityId** because a company scope is not automatically a legal person.
- `RegisterEstablishment` accepts a typed `Establishment` whose `LegalEntityId` is checked by the 0015 tenant-aware parent trigger.
- `RegisterLegalIdentifier` accepts explicit stable identifier UUID and typed `LegalIdentifier` including registry issuer, jurisdiction, effective validity and source.
- `OrganizationRegistrationService` is an Application Service using Protocol ports, a trusted principal, explicit tenant-level AuthorizationPort, clock and digest-based idempotence. This is **not** a public HTTP authorization implementation: in production the authentication/IAM policy must be independently integrated and more granular scoping may be required.
- `PostgresOrganizationRegistrationUnitOfWork` uses authenticated PostgreSQL `session_user` tenant-bound role and a single coarse `cc:tenant:{tenant}` transaction advisory lock (same namespace as L02), one database connection for all four durable writes.
- Immutable `OrganizationRegistrationReceipt` identifies a **target_kind + target_id** (Company, Establishment, LegalIdentifier), never falsely labels the target as a LegalEntity.

## SQL migration 0016

Migration `0016_organization_command_evidence.sql` is **additive**, with earlier SQL 0001–0015 unchanged:

| Table | Purpose |
|---|---|
| `organization_command_requests` | Unique `(tenant, actor, action, request_key)`, digest, immutable original receipt |
| `organization_command_audit` | Original verified actor and reason, target kind/id, optional company/legal references, UTC instant |
| `organization_command_outbox` | Internal event envelope with explicit organization target kind/id, correlation and schema version |

All tables are tenant-RLS-bound and forbid UPDATE/DELETE. Runtime CI roles receive SELECT + INSERT, not UPDATE/DELETE. **The Outbox is not yet a qualified C10 publisher/consumer contract**: delivery worker, broker identity, ordering, tenant attestations and incident metrics are future L10 work. The SQL owner and role provisioning remain privileged trusted dependencies, not part of R&D security certification.

## Required behavior / positive and negative proofs

1. Company registration succeeds with **zero legal entity rows**, creates target, receipt, audit and internal outbox in one transaction; audit legal entity reference remains NULL.
2. Exact duplicate command returns the original immutable receipt without writing new rows; same request key but changed content fails.
3. Establishment registration requires a matching authoritative tenant legal parent; orphan insert fails and leaves **no evidence**.
4. Registry identity collision conflicts via existing 0015 SQL trigger; no receipt/audit/outbox is emitted for the rejected registration.
5. Invalid/cross-tenant principal or missing grant rejects before any database mutation.
6. Injected crash before commit rolls back target + three evidence rows.
7. Concurrent identical requests serialize and produce one success record plus idempotent replay of the same receipt.
8. Foreign/unbound login cannot view organization outbox rows because of tenant RLS. Runtime SQL cannot mutate committed audit records.
9. Migration recovery still checks 0013→0016, gap/drift, rollback and isolated PG dump/restore; source/wheel/sdist parity requires exactly 16 SQL scripts.

## Explicit follow-up

- **ORG-4c**: approved lifecycle and revisions for Company and Establishment; harden legal registry revocation/correction workflow; replace 0015 parent trigger with a reviewed lifecycle-safe FK/constraint and adjust legacy L02 cleanup.
- **ORG-5**: end-to-end G3 golden scenarios, audit event schema, hostile tenancy/permissions and failure injection beyond current R&D unit integration scope.
- **C10/L10**: external producer/consumer contract and real delivery workers.
- **Production**: IAM credential issuance/rotation, separate approval authorities, PITR/RPO/RTO, external registry validation. No production-ready claim or stable publication; version remains `0.0.0`.

## CI evidence

Each CI run must be linked for **the final PR #39 head SHA**. Historical runs for intermediary commits do not certify subsequent changes; review the PR checks for exact SHA qualification.
