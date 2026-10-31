# L05-04 — MappingSet & AccountMapping Candidate Resolution

**Date:** 2026-10-31  
**Status:** `L05_04_MAPPING_SET_RND_CANDIDATE`; exact-head CI qualification pending.  
**Base:** [L05-03 PR #84](https://github.com/tawounfouet/pyaccountingkit/pull/84), SHA `33a0ef64040138649c3213280754d06dd2345e07`; indirectly stacked on main-derived #83 and #82, **not dependent on unmerged L04 code**.  
**Source:** `13_COMPANY_CONFIGURATION_CHART_OF_ACCOUNTS_AND_ACCOUNT_MAPPING.md`, especially §4, §8, §10–13, §19, §21–22, together with the `18` temporal spec.  
**Gate truth:** G0/G1/G2 `PENDING_REVIEW`; G3 `HOLD_SECURITY`; [#71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN; G4/G5 **NOT APPROVED**. Zero SQL changes, no main merge.

## 1. Why mappings belong to Company Configuration, not Ledger

The source defines an `AccountMapping` as a **declarative, typed, dated and verifiable correspondence**, and not a journal entry, amount transformation or universal normative equivalence. `MappingSet` groups mappings under a versioned policy and provenance. Runtime can resolve the applicable *published* mapping; Projection/Execution alone decide subsequent accounting processing. **This L05-04 implementation only prototypes unapproved candidates.**

Target mapping cardinalities:
- **1:1:** one local source account maps to one target account, if scope/time/version constraints match.
- **N:1:** multiple distinct source accounts may refer to the same target account for logical reporting or aggregation; **no amounts are aggregated by this domain**.
- **1:N:** one source to multiple targets requires a deterministic discriminator or an externally approved specialized allocation provider. **No such provider or monetary allocation exists in this PR.**
- **N:M:** excluded pending separate specialized contracts.
- **Unmapped/Identity:** no assumed fallback to a generic account or automatic identity; missing mandatory mapping is refused.

## 2. Provisional decisions (ADRs not approved)

`ADR-COA-05`: 1:N provider model remains OPEN. The R&D enum exposes **only** `DIRECT_ONE_TO_ONE` and `AGGREGATE_MANY_TO_ONE`. A set with competing mappings from one source can be resolved to only **one** target with an explicitly opted-in candidate policy, but no split, allocation, arbitrary Python predicate or monetary amount may be introduced.

`ADR-COA-06`: priority/specificity remains OPEN. The versioned candidate set explicitly chooses **one of**:
- `REQUIRE_UNIQUE`: default fail-closed profile; multiple active mappings for the source are an error; priorities forbidden.
- `EXPLICIT_PRIORITY_RND`: every rule must have a nonnegative integer rank. The highest rank is selected **only when strictly unique**. Tied highest rank fails closed. This is a *testable local hypothesis*, not the official published precedence policy; no automatic fallback to rank, UUID, insertion order or most recent.

`ADR-COA-08`: total versus declared partial coverage remains OPEN. L05-04 only implements an explicit **missing-mapping refusal for the requested source**. A future global chart coverage report remains necessary before publication.

`ADR-COA-01/03/07/09/10`: chart ownership, versioning, normative refs, publication and temporal persistence are not approved. For isolation, the prototype requires source and target chart versions under **the same explicit entity-level scope**. Cross-entity mappings need a separately agreed typed scope and relationship authorization; this R&D profile denies them.

## 3. Domain model (DDD and CQRS)

```text
CompanyChartVersionCandidate (L05-03) ─────────┐
  source chart + accounts (literal AccountCode) │
                                               │
CompanyChartVersionCandidate (L05-03) ─────────┤
  target chart + accounts                      │
                                               ▼
                                MappingSetVersionCandidate
                                  MappingSetCandidateVersionId
                                  same entity scope
                                  exact source + target chart version IDs
                                  MappingPrecedencePolicy
                                  EffectiveInterval / KnowledgeInterval
                                  immutable AccountMappingCandidate[]
                                  source_ref + canonical SHA-256
                                               │
                    ┌──────────────────────────┘
                    ▼
    AccountMappingCandidate
       AccountMappingCandidateId
       MappingSetCandidateVersionId
       exact source/target chart version IDs
       one source AccountId → one target AccountId
       MappingKind (direct / N:1)
       optional explicit candidate priority
       effective validity, source_ref
                    │
                    ▼
    resolve_account_mapping_candidate
      source_account_id + scope + as_of + known_at
      exactly one effective and known MappingSetVersionCandidate
      zero matching rules → MISSING
      two or more matching rules → AMBIGUOUS unless unique top rank policy
                    │
                    ▼
    AccountMappingCandidateResolution (SHA-256 receipt)
      ONE selected mapping and target AccountId
      exact mapping set ID+digest; as_of, known_at; source_ref
      status = UNPUBLISHED_RND_MAPPING_RESOLUTION

    No Money, no allocation, no account eligibility, no posting
```

The **read-only application service** `AccountMappingCandidateResolutionService` composes a `MappingSetCandidateReader` port, explicit `AuthorizationPort.require` action `chart.mapping.candidate.resolve`, tenant equality and `TrustedPrincipal` shape check. `MemoryMappingSetCandidates` is a **process-local fake**, not a certified account registry, published rule provider or legal ownership proof.

**Patterns**: DDD entities/VOs, immutable composite candidate, pure domain policy, Hexagonal Ports/Adapters, CQRS query, DIP, explicit temporal and scoping invariants, fail-closed deterministic selection and exact source lineage.

## 4. Canonical digest / temporal contract

`SCHEMA = "l05-rnd-mapping-v1"`. SHA-256 over explicitly enumerated UTF-8 JSON fields sorted by key, `ensure_ascii=False`, `separators=(',', ':')`, `allow_nan=False`. Mappings are **sorted by typed UUID** in the full-content manifest, so input catalog order has no influence.

The set manifest pins:
- Exact `MappingSetCandidateVersionId`, full entity scope and `source_ref`.
- **Both exact chart candidate version IDs and their existing full-content digests**, plus the immutable mapping rule manifests (source and target account IDs, kind, scope, priority, period and provenance).
- Explicit business `[from,to)` and aware knowledge `[known_from,known_to)` windows, and explicit candidate precedence policy.

The resolution manifest pins set ID and digest, the selected mapping identity, its provenance, source and target account IDs, mapping kind, original business date and UTC-normalized knowledge instant. `verify_integrity()` checks nested chart digests and mapping-set and resolution checksums.

**Checksum is not a signature or evidence of legal content.** A caller with write access to an in-process object and its digest can recompute both; a real published mapping set needs durable immutable storage, approved canonical version, verified signer and independent governance.

**Bitemporal replay example:** `as_of=2026-02-15`, with `known_at=2026-02-01` chooses an older candidate set mapping A→X, while `known_at=2026-03-01` chooses an amended candidate set A→Y. The original read is unchanged. No latest fallback or hidden current-chart lookup is allowed.

## 5. Executable constraints / test evidence

| ID | Source | R&D invariant and expected denial |
|---|---|---|
| L05-M-01 | COA-INV-09 | Referenced source and target accounts **exist in exact pinned chart versions** |
| L05-M-02 | COA-INV-10 | 0 mapping = `MAPPING_MISSING`; >1 without policy or tied rank = `MAPPING_AMBIGUOUS` |
| L05-M-03 | COA-INV-11 | Enum excludes 1:N; return one target ID only; no amount/posting operation |
| L05-M-04 | COA-INV-15 | N:1 explicit kind; never implicit double-posting or amount aggregation |
| L05-M-05 | COA-INV-13/17 | Stable typed IDs, same entity scope, effective intervals contained in both charts/accounts |
| L05-M-06 | TMP-10/11/15 partial | Original-known/restated cutoffs select distinct dated mapping sets |
| L05-M-07 | ADR-COA-06 OPEN | `REQUIRE_UNIQUE` default; `EXPLICIT_PRIORITY_RND` opt-in with strict no-tie rule |
| L05-M-08 | Scope isolation | Foreign/cross-entity catalog, untyped/duplicate set identities rejected |
| L05-M-09 | Digest | Manifest ordering reproducible, source+target chart/version digests pinned and mutations detected |
| L05-M-10 | Security | Read-only fake-gated query, no IAM/SQL/HTTP/outbox/ledger publication |
| L05-M-11 | Scope precedence | No scope-specificity or conditional predicate implemented; **not** passed as published compatibility |
| L05-M-12 | Coverage | Unmapped source rejected locally, no implied full coverage/publication guarantee |

Other cases in the test file: malformed priority (bool, negative, string), status/version mismatches, adjacent half-open periods, multiple concurrent set versions, re-used IDs, foreign reader, no default maps.

**Unimplemented target checks:** verified source/target **eligibility** at the requested published versions; real normative classification; book binding authorization; actual fiscal period open/lock; mandatory mapping coverage; conditional specificity and source dimensions; 1:N and N:M provider contracts; external mapping publication and signed read receipt. These are not proven by positive local candidate resolution.

## 6. Boundaries and next cut

**Architecturally forbidden here:** writes to Ledger, amount allocation, account reclassification by implicit code prefix, automatic chart substitution, direct SQL writes, privileged actor IAM creation, binding to unmerged L04 books, issue #71 mitigation by fakes, claim of `C10-ResolveAccountMapping` compatibility.

**Next proposed R&D cut:** L05-05 — conditional mapping / explicit provider capability contracts + candidate conflict diagnostics and coverage reporting. For 1:N, require specialized **nonexecuting** provider contracts and decision artifacts before any code permits multi-target financial semantics. A separate future governance integration will need ADR approvals and #71/G3 closure.

- [x] Typed candidate mappings and mapping set versions.
- [x] Pure 1:1 and N:1 mapping rules; no 1:N allocation.
- [x] Explicit local precedence policy with fail-closed ambiguity.
- [x] Bitemporal original-known / restated query and deterministic digest receipts.
- [x] Read-only hexagonal ports/fixture and adversarial tests.
- [ ] Exact-HEAD Python 3.11/3.12 + Ruff and Foundation PG/recovery/package-parity CI.
- [ ] Independent Accounting/Projection/Normative/Security review of ADR-COA-05/06/08 and production eligibility contracts.

**Do not promote L05-04 to G5_GO or production because CI is green.**
