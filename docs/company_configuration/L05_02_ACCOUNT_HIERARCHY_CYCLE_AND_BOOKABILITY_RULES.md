# L05-02 — Account Hierarchy, Temporal Cycle Validation & Bookability Candidates

**Date:** 2026-10-30  
**Status:** `L05_02_HIERARCHY_BOOKABILITY_RND_CANDIDATE` pending exact-HEAD CI.  
**Stack:** [L05-01 draft PR #82](https://github.com/tawounfouet/pyaccountingkit/pull/82) @ `bc89639cac777e37cd002c141f526b20e2c81d28`. L05-01 is directly based on the unchanged Foundation `main`; **no L04 draft dependency**.  
**Source:** `13_COMPANY_CONFIGURATION_CHART_OF_ACCOUNTS_AND_ACCOUNT_MAPPING.md` §5.1, §5.2, §7, §11, §12, §19, §21, and L05-01 draft spec.  
**Governance:** G0/G1/G2 `PENDING_REVIEW`, L03 G3 `HOLD_SECURITY`, [issue #71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN. No G4/G5 authorization, no posting.

## 1. Business interpretation of source

The target §7 requires: accounts of compatible chart/scope, no self-ancestry, **at most one active parent per child in a tree view/date**, distinct hierarchy views when multiple groupings are needed, and no cycle in a **published, versioned** hierarchy. COA-INV-06/07 are publication-time invariants. §5.2 defines:
- **postable account**: only one of the prerequisites for eventual JournalEntryLine use **after** checks by runtime and execution;
- **grouping account**: structures hierarchy, normally nonpostable unless an explicitly approved special policy;
- **suspended**: no new posting, historical readability maintained;
- **retired**: cannot be selected for new posting from its effective retirement date, but must remain historically referencable.

This implementation enforces **only local unpublished draft candidates**, not independently verified chart publications or normative account behavior. An account with `postable=True` plus `PROPOSED_ENABLED` and no children is not necessarily eligible for a journal line. Official PCG/SYSCOHADA conventions and IFRS reporting do not confer a universal chart-numbering rule.

## 2. DDD domain design and software design learning

```text
AccountHierarchyEdgeCandidate (frozen, source-ref, business interval)
  ├── AccountHierarchyEdgeId       stable edge identity (not account identity)
  ├── ConfigurationScope           explicit tenant / company / entity
  ├── CompanyChartId               exact chart
  ├── HierarchyViewCode            named proposed tree ("TREE", "GROUP"...)
  ├── CompanyAccountId             child
  ├── CompanyAccountId             parent
  ├── EffectiveInterval            [start, end), business dates only
  └── source_ref                   non-signed provenance pointer

validate_candidate_account_hierarchy(chart, accounts, edges)
  ├── typed immutable catalogs, unique account and edge IDs
  ├── exact chart/scope and code uniqueness; no orphan edges
  ├── edge validity wholly inside chart, parent and child validity
  ├── enumerate ALL graph-change dates, including future dates
  ├── per view/date: <= 1 active parent per child
  └── per view/date: iterative parent-chain cycle detection

preview_account_hierarchy(... view, as_of)
  └── AccountHierarchyCandidatePreview (sorted child-parent ID pairs)

AccountStatusCandidate (frozen, dated, scoped)
  ├── AccountStatusCandidateId
  ├── CompanyChartId + CompanyAccountId + ConfigurationScope
  ├── AccountStatusProposal
  │    DRAFT / PROPOSED_ENABLED / PROPOSED_SUSPENDED / PROPOSED_RETIRED
  ├── EffectiveInterval
  └── source_ref (unverified)

preview_account_bookability_candidate(...)
  ├── validate the entire hierarchy first
  ├── deny absent account / wrong scope / not effective
  ├── deny account.postable=False (local draft flag)
  ├── deny account acting as an active parent in ANY proposed view
  ├── require exactly one active status proposal at as_of
  ├── deny no status, duplicate IDs, overlapping statuses, foreign statuses
  ├── deny status != PROPOSED_ENABLED
  └── AccountBookabilityCandidatePreview (NON-AUTHORITATIVE)
```

**Patterns and principles:** DDD Entities and Value Objects, immutable candidate relations, domain-service pure graph policy, temporal `[from,to)` conflict validation, strict typed identities, fail-closed, separation of concerns / Dependency Inversion preparation (ports deferred to later slice), YAGNI (no premature generic graph DB or posting engine). Local graph validation uses an **iterative DFS-style parent-chain walk** rather than recursively traversing deep hierarchies.

## 3. Why the entire interval timeline is checked

Because the candidate graph is a finite set of half-open effective intervals, its active edge set changes only at the edge `start` and `end` dates. The validator checks the graph at **each such boundary**. Therefore a cycle scheduled to appear in July is refused even when someone previews the chart in January, while a pair of reverse edges in **adjacent, nonoverlapping** periods is permitted.

**Limit:** checking every boundary is a memory/CPU R&D implementation, not yet optimized for production-scale charts; publication will require benchmarking and enforceable concurrent persistence checks. It also does not implement historical `known_at` or signed immutable chart versions.

## 4. Executable local invariants

| ID | Source trace | R&D rule | Refusal |
|---|---|---|---|
| L05-H-01 | COA-INV-06 | No direct or indirect active ancestry cycle in any view/date | `HIERARCHY_CYCLE` |
| L05-H-02 | COA-INV-07 | No two active parents for same child, view and date | `HIERARCHY_MULTIPLE_PARENTS` |
| L05-H-03 | COA-INV-17 | Relation interval contained by chart + child + parent | `INVALID_ACCOUNT_HIERARCHY` |
| L05-H-04 | COA-INV-01/02 | Unique IDs/codes within the supplied account catalog | typed/dedicated domain errors |
| L05-H-05 | COA-INV-01 | Same chart, tenant, company and legal entity; exact endpoints exist | `INVALID_ACCOUNT_HIERARCHY` |
| L05-H-06 | §7 | Separate hierarchy views without covert fallback | deterministic per-view preview |
| L05-H-07 | COA-INV-05 partial | Nonpostable flag cannot yield local positive preview | `ACCOUNT_BOOKABILITY_CANDIDATE_DENIED` |
| L05-H-08 | §5.2 partial | Any active parent/grouping node denied by default | `ACCOUNT_BOOKABILITY_CANDIDATE_DENIED` |
| L05-H-09 | §5.2 partial | Suspended, retired, draft status proposal denied; no fallback | explicit denial |
| L05-H-10 | §5.2 | Status proposal must exist, be unique, typed and effective | `ACCOUNT_STATUS_CANDIDATE_MISSING/AMBIGUOUS` |
| L05-H-11 | §19 / COA-S04/S05 | Test graph cycles, summary nodes, negative cases | tests |
| L05-H-12 | Global CFG/SEC hold | No SQL, IAM, Normative adapter, Ledger or published C10 | static import + API tests |

**Local policy deliberately stricter than the open business policy:** a parent in *any* hierarchy view is considered a grouping node and denied even if `postable=True`. The source allows a future explicitly approved exception. Such a policy may be modeled only after Accounting and ADR-COA-04 decide which hierarchy views are normative for grouping vs reporting; this PR does not grant that exception.

**Not implemented:** full account status transitions, jurisdiction-dependent chart classification, mapped accounts, Ledger balance conventions, currency/dimension validation, period opens/locks, book/chart binding, publication, durable audit or C10-Q05.

## 5. Open architecture decisions and further steps

- **ADR-COA-04 (OPEN):** one canonical chart tree versus many named views. Named views here are a provisional conservative solution, not signoff.
- **ADR-COA-02 (OPEN):** aggregate ownership and publishing/concurrency boundary for independent account, edge and status objects.
- **ADR-COA-01/03 (OPEN):** chart ownership, immutable versioning and BookChartBinding; source data are unapproved.
- **ADR-COA-07 (OPEN):** when normative account references are required; external Normative Layer remains source of truth.
- **ADR-COA-09/10 (OPEN):** approval, audit, publication and bitemporal persistence; no `known_at` here.
- **Security #71 and G3 HOLD:** no non-bypassable independently signed actor/IAM pairing at SQL COMMIT; memory-domain rules cannot close this.
- Real bookability will require at minimum a **published chart version**, approved account status, exact book/chart binding, norm compatibility, open fiscal period, policies/dimensions and authenticated authorization. L05-02's positive result is **not** sufficient.

## 6. Qualification and roadmap

- [x] Typed hierarchy edges and view codes, full-timeline cycle/multi-parent validation.
- [x] Typed dated status proposals and fail-closed candidate leaf/postability preview.
- [x] Adversarial unit cases including temporal boundaries and cross-tenant leaks.
- [x] No SQL migration, publication, posting or privileged issuer.
- [ ] Exact-head Python 3.11/3.12 + Ruff, PG16 Foundation, recovery and FND-C06 package parity.
- [ ] Independent Accounting + Architecture + Security approval for graph/cardinality/status semantics.

**Exit before CI:** `L05_02_ACCOUNT_HIERARCHY_BOOKABILITY_RND_CANDIDATE`. Next safe R&D scope: L05-03 dated *candidate* CompanyChartVersions and BookChartBindings, without authoritative C10 or published chart/period eligibility. No main merge or release.
