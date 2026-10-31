# L05-05 — Conditional Mapping, Specialized Provider Intent & Coverage Diagnostics

**Date:** 2026-10-31  
**Status:** `L05_05_CONDITIONAL_MAPPING_RND_CANDIDATE` (exact-HEAD CI pending).  
**Parent:** draft [L05-04 PR #85](https://github.com/tawounfouet/pyaccountingkit/pull/85) @ `25fea2b6831ffd1fa927dc831923648d65dd3275`, stacked on #84→#83→#82→main. **Not dependent on unmerged L04.**  
**Target basis:** `13_COMPANY_CONFIGURATION_CHART_OF_ACCOUNTS_AND_ACCOUNT_MAPPING.md` §8.1–8.3, §10–13, §19, §21–22 (COA-INV-09/10/11/13/15/17; COA-S09/10 and ADR-COA-05/06/08).  
**Governance:** G0/G1/G2 `PENDING_REVIEW`, G3 `HOLD_SECURITY`, [issue #71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN, G4/G5 not approved. No SQL, publishing, C10 or posting.

## 1. Source requirements and explicitly narrower prototype

The target states that account mapping is a **declarative, typed, dated and verifiable correspondence**, never a journal, amount transformation or universal normative equivalence. §8.2 calls for deterministic **typed predicates, without arbitrary code execution**, explicit priorities and mapping set provenance. §8.1 authorizes simple 1:1/N:1 correspondences but says **1:N requires a discriminator or an external allocation rule**; this prototype **cannot implement** monetary allocation, even when a declared provider exists. §8.1 also distinguishes `Unmapped` from formally approved exceptions or coverage reports.

This R&D increment delivers three separate **unpublished** capabilities: conditions, a **non-executing descriptor** of a specialized provider requirement, and a read-only structural mapping coverage report. **None** produces C10 `ResolveAccountMapping` / `GetMappingCoverage`, determines real account eligibility, or certifies chart/mapping publication.

## 2. DDD model and ports

```text
                  MappingSetVersionCandidate (L05-04)
                   /                  |               \
        ConditionProfile          ProviderIntent    CoverageException
            (same set)              (same set)        (proposed only)
               |                        |                   |
MappingRuleCondition             SpecializedMappingProviderContract
  - mapping_id                   - provider_code/version/capability
  - source_ref                   - typed input/output schema codes
  - predicates: AND[]            - ONE_TO_MANY_ALLOCATION (descriptor)
       MappingPredicate          - no call/execute/invoke/amount
       key: ACTIVITY/SEGMENT/...                |
       operator: EQUALS/ONE_OF                 V
       expected: canonical strings   MAPPING_REQUIRES_PROVIDER
               |                        (always refuse)
     + typed MappingFact context
               |
       resolve_conditional_mapping_candidate
       - as_of and known_at
       - complete explicit rule declarations
       - no missing data fallback
       - no multiple matches unless unique opt-in R&D top priority
               |
       ConditionalMappingCandidateResolution (one target, digest)

       preview_mapping_coverage_candidate
          -> MappingCoverageCandidateReport
           DIRECT_CANDIDATE / CONDITIONAL_NEEDS_FACTS /
           PROVIDER_REQUIRED / AMBIGUOUS / UNMAPPED /
           EXCEPTION_DECLARED
           full account list + evidence digest + immutable receipt
```

**DDD / Value Objects:** enumerated fact keys/operators, typed string canonical fact values, mapping identities inherited from L05-04, immutable candidate profile, provider requirement and exception.  
**Hexagonal/CQRS:** `MappingDiagnosticsCandidateService` uses `MappingDiagnosticsCandidateReader` and `AuthorizationPort`; the process-only `MemoryMappingDiagnosticsCandidates` does not certify legal membership, IAM or source validity. Separate *fake* permissions `chart.mapping.condition.candidate.preview` and `chart.mapping.coverage.candidate.preview` prevent accidental action conflation.  
**Domain Service / SoC / DIP:** resolution, requirements and coverage are pure functions, not database or Ledger adapters. No arbitrary Python predicates, expression AST, `eval`, remote tools or unsafe callbacks.

## 3. Explicit condition semantics — restrictive R&D profile

- `MappingFactKey`: `ACTIVITY`, `BUSINESS_UNIT`, `COST_CENTER`, `SEGMENT`; `MappingFact` has canonical uppercase ASCII value.
- `MappingPredicate`: `EQUALS(one)` or `ONE_OF(nonempty distinct tuple)`. A `MappingRuleCondition` can have **at most one predicate for each key**, evaluated as conjunction (AND).
- A mapping rule with **zero predicates** is an **explicitly recorded unconditional rule**; never synthesized for missing declarations. The profile covers **every** rule in the exact `MappingSetVersionCandidate`, once each.
- The resolution requires **every fact that a potentially applicable source rule needs**; missing facts trigger `MissingMappingFact`, not false-match or unconditional fallback.
- Any number of conditions can match. Under `REQUIRE_UNIQUE`, multiple matches reject; under explicitly opted-in `EXPLICIT_PRIORITY_RND`, only one uniquely highest rank may win; tied maxima reject. This policy is *not* the officially published ADR-COA-06 algorithm.
- No `OR`, negation, regex predicate, source-supplied Python expression, arbitrary code or normative classification evaluation. These are deliberate YAGNI / safety boundaries, not an assertion that the production contract needs only these operations.

## 4. Specialized provider **requirement**, not implementation

`SpecializedMappingProviderContract` is a **typed versioned descriptor** only: provider code+version, `ProviderCapability`, input/output schema IDs. `MappingProviderRequirementCandidate` pins the exact mapping set and charts, one source account, **at least two distinct target AccountIds**, effective and knowledge intervals, an unverified source pointer and SHA-256 manifest. All account IDs must exist in pinned candidate chart versions, and the provider period fits their validity.

A direct mapping overlapping this source's provider-intent period is rejected. The only exposed `require_specialized_provider_candidate` returns **no value** and **always raises** `MappingProviderRequired` for a matching 1:N request. A nonmatching, out-of-time or tampered intent is refused. **No callable, allocation, percentage, currency conversion, Money, journal output, webhook or provider execution exists.** An actual 1:N capability later requires ADR-COA-05, a signed provider/Projection contract and separate independent accounting tests.

## 5. Structural coverage — not approved mapping completeness

At an explicit `as_of` and aware `known_at`, `preview_mapping_coverage_candidate` enumerates **every effective source chart account** in the pinned candidate set. It does not silently omit unmapped accounts.

| Disposition | Meaning in R&D | Can this authorize posting? |
|---|---|---|
| `DIRECT_CANDIDATE` | Unconditional unique rule or unique test-only top rank | **No** |
| `CONDITIONAL_NEEDS_FACTS` | Rule contains predicates, context not evaluated | **No** |
| `PROVIDER_REQUIRED` | Separate explicit non-executed 1:N requirement | **No** |
| `AMBIGUOUS` | Multiple incompatible source rules | **No** |
| `UNMAPPED` | Zero active source rule and no other intent | **No** |
| `EXCEPTION_DECLARED` | Local dated, reasoned exception proposal only | **No** |

An exception is **not approved coverage**. Overlapping exceptions, providers or direct mappings for the same account are refused rather than masked. The report's `has_unresolved` is diagnostic, **not** a production readiness or compliance gate. Accounts marked `DIRECT_CANDIDATE` are still unverified for normative/reference/status/period eligibility.

## 6. Temporal/digest contracts and trust limitations

- All candidate inputs are pinned to a complete **L05-04** `MappingSetVersionCandidate`. Business intervals are half-open, knowledge intervals contain timezone-aware datetimes.
- Canonical JSON/UTF-8 `sha256:` digest, with sorted mapping rules, predicates, fact context, provider targets and source coverage rows. The condition profile pins the L05-04 set digest and its exact identity. Coverage report also pins a hash of profiles, provider intents and exception declarations.
- All preview results and providers expose `verify_integrity()` for local deterministic self-consistency. Hashes are **not signed**, not externally anchored, and do not prove publisher, content correctness or durable auditing. A malicious in-process writer able to recompute all digests can forge the data.
- L05-05 does **not** add bitemporal SQL persistence, independent credential issuers, published snapshots or C10 consumer schemas. Real signed source/actor command and IAM-at-COMMIT blocker #71 remains open.

## 7. Negative proof and open ADRs

| Test focus | Fail-closed behavior |
|---|---|
| Missing/uncanonical/duplicate facts | Explicit exception; no uncontrolled default |
| Duplicate rule declarations or non-typed predicates | Reject profile at construction |
| Two matches, missing rank or equal highest priority | Ambiguity rejection |
| Original-known versus restated conditional rules | Distinct, digest-pinned candidate resolutions |
| 1:N with one/duplicate/missing target | Reject provider-intent construction |
| Requested provider present | Typed `MAPPING_REQUIRES_PROVIDER` refusal, no execution |
| Provider overlaps direct mapping | Refuse overlapping intents |
| Unmapped source, conditional needing facts, conflicting set | Full diagnostics, no false completeness |
| Exception overlaps mapped source or duplicated | Reject |
| Foreign scope, forged principal, missing separate test grant | Reject, no SQL/real authorization |
| Tampered profile, mapping, provider or receipt | Digest verification fails |
| Wheel/sdist migration lineage | Exactly original 14 historical SQL migrations, no new DDL |

**ADR-COA-05** (1:N provider policy), **ADR-COA-06** (scope specificity and precedence), **ADR-COA-08** (mandatory/partial mapping coverage), **ADR-COA-09/10** (governed publication/temporal persistence) remain **OPEN**. R&D code cannot sign them. Domain/accounting/security/consumer qualification and issue #71 still block promotion.

## 8. Qualification checklist and roadmap

- [x] Typed declarative AND/ONE_OF conditions, complete pinned rule catalog, deterministic context handling.
- [x] Nonexecuting specialized 1:N provider requirement with refusal.
- [x] Full source-account structural coverage and explicitly unresolved exceptions.
- [x] Read-only fake-gated query service and memory reader.
- [x] Adversarial tests and documentation.
- [ ] Exact-head Python 3.11/3.12+Ruff, PostgreSQL Foundation, migration recovery and packaged SQL parity.
- [ ] Approved cardinality, conditional precedence, providers, chart eligibility, security and G5.

**Next R&D slice (proposed):** L05-06 — diagnostic/conflict-proof and L05 R&D consolidation with canonical ADR register and L06 fiscal-calendar handoff. **No main merge, signed publication, SQL writer or G5_GO** is implied by this document.
