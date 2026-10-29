# L03-01 — Organization Kernel and Temporal Memberships (R&D)

**Date:** 2026-10-29  
**Source baseline:** recent standalone `tawounfouet/pyaccountingkit`, main merge `acdee98ca2736d79e17174f510ac767defd90db8`.  
**Scope:** **L03 ORG-1 / first ORG-2 domain slice, R&D candidate only**.  
**Specification:** `11_COMPANY_CONFIGURATION_ORGANIZATION_AND_LEGAL_ENTITY_MODEL.md`, especially sections 2, 5, 6, 9, 10, 15, 17–19; `07_COMPANY_CONFIGURATION_DOMAIN_INVARIANTS_AND_BUSINESS_RULES.md` INV-ORG-01..04; global roadmap L03/G3. The supplied documents are **proposed target contracts**, not evidence of existing implementations.

## Implemented

- `Company` is an immutable, tenant-scoped **organizational scope** with explicit `STANDALONE/GROUP` kind, revision, canonical name, optional base currency, home country and guarded `DRAFT/ACTIVE/INACTIVE/ARCHIVED` state machine. No implied legal personality or normative propagation.
- `Establishment` has typed site id, explicit legal-entity parent, half-open effective dates, country, guarded status transitions and no automatic accounting book.
- `LegalIdentifier` includes `scheme/issuer/value/jurisdiction`, effective validity and source provenance; pure conflict policy rejects another entity's overlapping scoped registry claim, not a globally unique number.
- `OrganizationMembership` stores a stable membership id, company and legal entity ids, `ADMINISTRATIVE/OPERATIONAL` kind, explicit exclusivity, half-open validity, recorded knowledge instant, source provenance and immutable amendment revision. The membership **is not capital control**.
- Membership historical resolver requires explicit `effective_on` and `known_at`, chooses the latest revision known by that instant, rejects incomplete histories and overlapping exclusivity, and returns deterministic results. A backdated cessation can be queried as before/after its actual knowledge time.
- Referential guards `require_membership_parents` and `require_establishment_parent` require already loaded authoritative parents **in the same tenant**, but do **not** substitute for database FKs and authorization.
- Typed `EstablishmentId` and `MembershipId`, `InvalidOrganization`, `OrganizationConflict`, `AmbiguousOrganization`. Public exports remain in the pure Domain layer.

## Decisions / scoping (ORG-ADR)

| ADR | R&D slice convention | Still open for L03 |
|---|---|---|
| ORG-ADR-01 | Company represents an explicitly typed scope; legal person is separate | Full organization catalog / addresses |
| ORG-ADR-02 | Multiplicity possible; exclusivity evaluated per kind, tenant, entity, period | Runtime policies for transfer/overlapping records in PostgreSQL |
| ORG-ADR-03 | **NO decision on shared/dedicated AccountingBook** | Book/LegalEntity assignment semantics in L04 |
| ORG-ADR-04 | Legal IDs scoped by scheme/issuer/jurisdiction/effectivity with provenance | Actual external register verification / PostgreSQL exclusions |
| ORG-ADR-08 | Effective `date` and known-at timezone-aware UTC instant; immutable amendments | Full PostgreSQL bitemporal model and authoritative audit |
| ORG-ADR-09 | Sites are references, not new accounting entities | Site-level policy assignment rules |

## Negative / property proofs

- Same identity across versions, different tenant identity, stale revisions and illegal transitions.
- Site-parent mismatch, cross-tenant membership/parent mismatch, explicit company != entity's administrative baseline.
- Historical membership end recorded later: query at same effective date but earlier `known_at` returns original revision; later `known_at` uses amended revision.
- Missing or forged membership version history fails closed.
- Exclusive overlap rejected; half-open touching dates allowed; distinct nonexclusive membership kinds coexist.
- Registry collision in same issuer/scheme/jurisdiction and overlapping date rejected; different tenant or separated intervals permitted.
- Property-based generation on effective date boundaries.

## Not yet implemented — no G3 acceptance claim

1. ORG-2: authoritative legal-identifier registration, memberships persisted with durable append-only revision history, full backdated correction and forensic audit.
2. ORG-3: PostgreSQL `0015+` migration, FKs to real `Company` while maintaining the existing L02 bootstrap compatibility; scoped SQL roles/RLS and concurrency tests.
3. ORG-4: authenticated commands, durable UoW, idempotency, organization audit + transactional outbox and role authorization; registration/transfer/close lifecycle.
4. ORG-5: formal scenarios for mergers/cessions, establishment reassignment, hierarchy cycles if Company-to-Company relations introduced (none implemented here), legal entity succession, C10 consumer contracts.
5. L04: shared book assignment ADR and normative framework references. **No Ledger posting** or consolidation inference.

**G3 remains IN PROGRESS**, until the above target rules have explicitly been implemented/qualified or deferred by a scoped decision. No database migration and no production runtime role/grant changes in this increment.

## CI evidence

Exact-head Python CI Python 3.11/3.12 and Ruff must pass before claiming the L03-01 branch qualified. PostgreSQL and package workflows must remain green (no migration changes).
