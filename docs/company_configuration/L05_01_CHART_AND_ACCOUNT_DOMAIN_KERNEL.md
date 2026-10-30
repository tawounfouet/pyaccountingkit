# L05-01 — Chart of Accounts & Account Domain Kernel (R&D)

**Date:** 2026-10-30  
**Status:** `L05_01_ISOLATED_DOMAIN_RND_CANDIDATE`, pending exact-head qualification; **NOT an approved chart, posted account, or C10 API**.  
**Source revision:** `13_COMPANY_CONFIGURATION_CHART_OF_ACCOUNTS_AND_ACCOUNT_MAPPING.md`, v1.0, 2026-10-29, `TARGET / PROPOSED` (especially §0–7, §11, §14, §19, §21).  
**Base:** isolated `main` commit `acdee98ca2736d79e17174f510ac767defd90db8`; **not stacked** on draft L04 #74–#81.  
**Gates:** G0/G1/G2 `PENDING_REVIEW`; L03 G3 `HOLD_SECURITY`; [issue #71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN; G4/G5 not approved.

## 1. Business boundary

A `CompanyChart` is a company's operational chart of accounts; `CompanyAccount` is an account with a stable identity and a business code. The *proposed* target has versioned chart/account changes, hierarchies, mappings and BookChartBindings. Here we intentionally implement only the **domain kernel for unpublished chart and account drafts**, without assuming an approved transactional aggregate or physical chart ownership.

The target source explicitly distinguishes:
- **Normative Layer**: owns official reference content; Company Configuration stores only versioned pointers and intentions.
- **Company Configuration**: chart/account codes, candidate identity, scope and configuration rules.
- **Runtime Resolution / C10-Q05**: authoritative **published** account eligibility; **not implemented**.
- **Accounting Projection / Execution / Ledger**: select accounts, approve posting plans and write ledger entries; **never delegated to ChartDomain**.
- **Reporting**: reporting hierarchy and aggregation, separate from posting.

Never infer that IFRS imposes a universal mandatory chart of accounts. This R&D model does not implement PCG/SYSCOHADA normative catalog editions, account nature tables, booking authorization or actual company–entity membership.

## 2. Decisions still OPEN

`ADR-COA-01` — chart ownership: entity/book/shared with dated binding. Current `ConfigurationScope` is a **claimed entity-level R&D intent**, not approved ownership of a chart and not an Organization fact. No book ID is accepted at this boundary; BookChartBinding belongs to a later slice. This is **reversible R&D modeling**, not a universal ownership policy.

`ADR-COA-02` — account aggregate boundary: account as independent aggregate vs chart child. In L05-01, two frozen types are used to test identity and local policies; this is *not* a persistence / transaction or Aggregate Root decision.

`ADR-COA-03` — versions: chart/account `revision` represents a **candidate change counter**, not a published `CompanyChartVersion`, signed snapshot or immutable audit event.

`ADR-COA-04` — hierarchy: single tree vs reporting views is pending; no hierarchy graph or edge is implemented yet (proposed L05-02).

`ADR-COA-07` — normative account link mandatory/optional remains pending; `AccountClassificationCode` is an **opaque internal label** with shape validation, never evidence of a normative legal account class.

`ADR-COA-05/06/08/09/10` — mapping providers, resolution priority, coverage, publication and temporal persistence remain open. No mapping engine or SQL table is introduced.

## 3. Domain concepts and types

```text
CompanyChartDraft
  ├── CompanyChartId     opaque UUID identity, never ChartCode
  ├── ConfigurationScope tenant/company/legal entity intent; book_id=None
  ├── ChartCode          provisional uppercase ASCII namespace
  ├── label              trimmed human label
  ├── EffectiveInterval  business dates [start, end)
  ├── source_ref         unverified provenance pointer
  └── revision           positive draft counter, no audit/publishing

CompanyAccountDraft
  ├── CompanyAccountId          opaque stable UUID identity
  ├── CompanyChartId            explicit chart identity (no FK SQL proof)
  ├── ConfigurationScope        equal to intended chart scope
  ├── AccountCode               opaque **string**, zeroes preserved
  ├── label                     trimmed human label
  ├── AccountClassificationCode opaque INTERNAL classification code
  ├── postable                  unverified draft *shape* flag
  ├── EffectiveInterval         business dates [start, end)
  ├── source_ref / revision     local metadata, not approved evidence
  └── rename / propose_postability → NEW DRAFT REVISION ONLY
```

**Code policy** is deliberately conservative and provisional:
- `ChartCode`: `[A-Z][A-Z0-9_-]{0,31}`.
- `AccountCode`: `[A-Za-z0-9][A-Za-z0-9._/-]{0,63}`, stored without conversion, normalization or numeric coercion. It accepts illustrative `00123`, `6.001`, `A/01`; it does not assert any of these is normatively valid for a jurisdiction.
- `AccountClassificationCode`: `[A-Z][A-Z0-9_-]{0,47}` opaque code. No derivation of a statutory account nature from code prefixes.

Future jurisdiction-specific syntax must come from an independently approved policy, not a global hardcoded PCG/IFRS/SYSCOHADA rule.

## 4. Domain invariants implemented (subset of §11, not full coverage)

| L05-RND | Source | Rule and negative proof |
|---|---|---|
| 01 | COA-INV-01 | Chart/account IDs typed and stable; names/codes not used as UUID identities |
| 02 | COA-INV-02 | Duplicate account codes rejected **inside exact chart & scope** when validity overlaps |
| 03 | COA-INV-03 | Leading zeroes preserved literally as text |
| 04 | COA-INV-05 **partial** | False `postable` shape or out-of-date account refused by local prerequisite; *not* Ledger eligibility |
| 05 | COA-INV-17 **partial** | Account effective interval fully contained in chart interval, half-open |
| 06 | Chart naming proposal | Chart codes unique within same claimed entity scope and intersecting dates |
| 07 | ADR-COA-01/02 guard | Book-level scope rejected, cross-chart/entity/tenant ID reassignment rejected |
| 08 | Draft revision proposal | CAS-style expected revision and nonempty reason on renames/shape changes |
| 09 | CQRS / publication boundary | No post/publish/activate, no normative verification, no SQL/HTTP/imported IAM |
| 10 | Defensive contracts | Wrong identifier, catalog type, interval, label/classification and boolean rejected |

These policies operate over **immutable in-memory tuples**, with **no cross-process race/uniqueness guarantee**. Equality/hash of draft entities reflects stable typed identity in tenant scope, not field/revision equality; compare attributes to inspect candidate revisions.

A positive `require_postable_candidate(as_of)` only verifies a necessary R&D flag and candidate-effective window. It must **never** be interpreted as `GetAccountEligibility` C10-Q05, authorization of a journal line, enabled book/calendar or a live permissions check.

## 5. DDD / software design learning convention

- **DDD Entities (draft)**: `CompanyChartDraft`, `CompanyAccountDraft` have opaque stable identities and candidate revision counters. Frozen values prevent accidental mutation but don't establish append-only storage.
- **Value Objects**: `ChartCode`, `AccountCode`, `AccountClassificationCode`, `EffectiveInterval` and typed IDs validate shapes and preserve semantics.
- **Aggregate boundary ADR**: chart/account separately modeled, while the DB/UoW ownership and aggregate-granularity decision remains open (ADR-COA-02).
- **Pure domain policy / SoC**: `require_unique_chart_code`, `require_unique_account_code`, `require_account_belongs_to_chart` are deterministic, infrastructure-agnostic candidate validators.
- **Optimistic Concurrency Pattern**: expected revision checked on candidate mutations. No durable CAS or audit transaction is implemented.
- **Fail-closed**: rejects ambiguous duplicate codes, invalid scopes or missing typed fields. No fallback to default or generic accounts.
- **Hexagonal** and **CQRS** remain future application boundaries; this **domain-only** slice defines no ports, command service, database or C10 surface.

## 6. Deliberately not implemented; following cuts

| Target | Planned later work | Blocking decision |
|---|---|---|
| AccountHierarchyEdge, cycle/parent count | L05-02 pure graph policy | ADR-COA-04 hierarchy views |
| Account status lifecycle, nonpostable summary | L05-02 local effective/status rules | Real account eligibility remains C10 |
| CompanyChartVersion + BookChartBinding | L05-03 bitemporal candidate only | ADR-COA-01/03, no publication |
| MappingSet / AccountMapping | L05-04 conditional/typed preview only | ADR-COA-05/06/08 |
| Published charts / signed outbox / SQL FK+exclusion | G3/G4/G5-approved implementation | #71, IAM, governance |
| C10-Q05 GetAccountEligibility | Runtime consumer-qualified published DTO | Normative/Chart/Book/Calendar/Policy |
| Accounting journaling | Projection/Execution/Ledger | Not Company Configuration |

## 7. Qualification

- [x] Main-derived isolated pure domain model and typed IDs.
- [x] Full negative tests for scopes, temporal uniqueness, revision, code zeroes and postability.
- [x] No migration, privileged IAM code path, C10 or posting.
- [ ] Exact-head Python 3.11/3.12 + Ruff, Foundation PG16/recovery and 14 SQL migration package parity.
- [ ] Independent DDD/Accounting/Legal ADR signoff and ownership/aggregate decisions.

**Exit label before CI:** `L05_01_CHART_ACCOUNT_DOMAIN_RND_CANDIDATE`. Not a claim of chart publication, verified IFRS/PCG/SYSCOHADA rules, L05 G5 approval or main merge.
