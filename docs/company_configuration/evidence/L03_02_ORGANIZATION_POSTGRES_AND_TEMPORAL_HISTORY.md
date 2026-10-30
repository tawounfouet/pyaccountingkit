# L03-02 — Organization PostgreSQL registry and temporal membership history

**Date:** 2026-10-29  
**Repository:** `tawounfouet/pyaccountingkit` (standalone R&D)  
**Lineage:** [L03-01 PR #35](https://github.com/tawounfouet/pyaccountingkit/pull/35) → [L03-02 PR #37](https://github.com/tawounfouet/pyaccountingkit/pull/37)  
**Scope:** ORG-2 / initial ORG-3 **development candidate**, not the full G3 acceptance.  
**Primary input:** `11_COMPANY_CONFIGURATION_ORGANIZATION_AND_LEGAL_ENTITY_MODEL.md` sections 2, 5, 7–11, 15 and 17–19 (target/proposed), with L02 persistence and security as the implemented compatibility baseline.

## Implementation and decisions

1. Additive immutable SQL migration `0015_organization_registry_and_memberships.sql`. All earlier `0001`–`0014` migration checksums remain unchanged; migration runner still rejects gaps, checksum drift or unknown applied history.
2. New tenant-scoped PostgreSQL tables:
   - `organizational_companies`: organization-scope identity and descriptive snapshot (not a legal entity).
   - `organizational_establishments`: site identity, legal-entity parent, date validity; **no implied book**.
   - `organizational_legal_identifiers`: scoped scheme, issuer, jurisdiction, value, business validity and provenance.
   - `organizational_membership_revisions`: immutable `(tenant_id, membership_id, revision)` history with recorded instants and business validity.
3. Tenant RLS uses `company_configuration.bound_tenant()` based on authenticated PostgreSQL `session_user`; runtime roles have only scoped SELECT and INSERT in R&D CI. UPDATE and DELETE are also blocked by triggers. No public table grants.
4. Foreign key `(tenant_id,company_id)` for membership → new `organizational_companies`. For references to legacy L02 `legal_entities`, trusted same-tenant parent trigger checks exist **instead of a physical FK** in this incremental migration. This intentionally avoids modifying legacy L02 TRUNCATE and bootstrap behavior; it is a **temporary integrity limitation** before a dedicated migration/cutover ADR. No general promise that deletion by privileged schema owners preserves parent integrity.
5. Scoped transaction advisory locks serialize overlapping legal identifier claims and exclusive membership insertions, including concurrent direct SQL writes. SQL append-only trigger rejects skipped revision numbers, retrograde `recorded_at`, reparenting and changes to membership kind or exclusivity.
6. `PostgresOrganizationRepository` exposes typed write methods and explicit two-dimensional membership read `effective_on` + `known_at`. Read resolution composes the pure L03 policy; it neither chooses a book nor infers control or consolidation.

## Qualified CI evidence (implementation SHA before this document)

At PR #37 checkpoint `e5224a2b358604f9aaf7d4211990f134348edb42`, all four workflows returned **SUCCESS** on Python **3.11 and 3.12**:

| Pipeline | Result per version | Run |
|---|---|---|
| Python CI | **315 passed, 20 skipped** (PG tests skipped by design in Python-only runner); Ruff passed | [#40963433060](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40963433060) |
| PostgreSQL integration | **141 passed** including 7 new ORG-3 tests; Ruff passed | [#40963433027](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40963433027) |
| Migration / restore | **6 passed**, fresh `0001→0015`, upgrade `0013→0015`, rollback/checksum/concurrency and schema dump-restore | [#40963433017](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40963433017) |
| Source/wheel/sdist | **15 byte-identical SQL migrations**, isolated wheel installation | [#40963433009](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40963433009) |

Document-only commits after this qualification must be re-verified on their **exact head** before claiming final-head CI.

## Limitations and next tasks

- **ORG-3 hardening:** replace temporary SQL parent guard with reviewed FK-based parent lifecycle or protected deletion/truncation contract; expand tenant isolation and concurrency tests for site and registry under pool/retry and hostile direct SQL.
- **ORG-4 application commands:** authenticated actor, policy authorization, idempotency, multi-object atomic UoW, append-only business audit and Outbox in same transaction. This repository currently implements independent low-level SQL methods, not those complete business commands.
- **ORG-5 G3 scope:** mergers, cessions, reparenting via new membership identities, legal registry evidence verification, real-world effective/known date corrections and operational cutover. Defer full status/revision persistence for Company/Establishment until command designs are fixed.
- **L04:** book assignment and shared-vs-dedicated book ADR **OPEN**; no hard mono-entity FK added.
- **Production:** no production-ready IAM, tenant credential issuance, PITR/RPO/RTO or external registry authenticity claim.

**G3 state = IN PROGRESS**, despite the automated SQL qualifications. PR #37 is an incremental, additive development candidate.
