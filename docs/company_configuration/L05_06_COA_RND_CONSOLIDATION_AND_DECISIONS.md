# L05-06 — Chart of Accounts R&D Consolidation, Traceability & ADR Review

**Date:** 2026-10-31  
**Engineering status:** `L05_06_CONSOLIDATION_RND_CANDIDATE`; exact-HEAD CI pending.  
**Branch basis:** draft [L05-05 PR #86](https://github.com/tawounfouet/pyaccountingkit/pull/86), head `191a9429239b88a064029cfb1869d8c16ac77be4`, stacked via #85/#84/#83/#82 on `main@acdee98ca2736d79e17174f510ac767defd90db8`. **Not stacked on unmerged L04.**  
**Canonical source:** `13_COMPANY_CONFIGURATION_CHART_OF_ACCOUNTS_AND_ACCOUNT_MAPPING.md` §11 (18 local invariants), §19 (20 qualification scenarios), §20 (source traceability), §21 (10 ADRs), §22 (P0–P6 roadmap). Complementary source `14` fiscal calendar, `10` C10 integration, `17` governance, `18` temporal history.  
**Machine-readable audit:** [`L05_06_COA_RND_EVIDENCE_AND_ADR_REGISTER.json`](L05_06_COA_RND_EVIDENCE_AND_ADR_REGISTER.json).

## 1. What was actually delivered, not what is approved

| Slice | Draft PR / qualified SHA | Implemented R&D boundary | Proof boundary |
|---|---|---|---|
| L05-01 | #82 / `bc89639c` | Typed Chart/Account draft IDs and codes, scope, intervals, candidate optimistic revision | In-memory validation; no published account |
| L05-02 | #83 / `6ff7cf73` | Dated named hierarchy views, cycle/parent conflicts, status and bookability candidates | No Ledger eligibility; `ADR-COA-04` OPEN |
| L05-03 | #84 / `33a0ef64` | Exact candidate chart-version bundle, bitemporal claimed BookChartBinding, checksum receipt | No authoritative book, Normative Layer, chart publication or signed C10 |
| L05-04 | #85 / `25fea2b6` | Candidate MappingSet 1:1 and N:1, explicit test-only priority, resolution receipt | No financial amount/aggregation, approved rank or runtime mapping provider |
| L05-05 | #86 / `191a9429` | Declarative AND/EQUALS/ONE_OF, nonexecuting 1:N provider *requirement*, candidate coverage diagnostics | No actual provider invocation, 1:N allocation or completeness approval |

These five slices live in **unmerged DRAFT PRs**. Green tests on draft heads are technical evidence only; the source `13` was written as `TARGET / PROPOSED`. In particular, the baseline `main` contains no L05-01–05 domain additions yet, and the combined stack must not be described as shipped or stable.

**Last exact-HEAD parent #86 qualification:** Python 3.11/3.12 each **520 passed, 19 skipped**; PostgreSQL each **134 passed**; migration recovery each **6 passed**; standalone package/wheel/sdist all 14 historical SQL artifacts SHA256 identical, Ruff passed in each workflow. Runs: Python [#41173301148](https://github.com/tawounfouet/pyaccountingkit/actions/runs/41173301148), PG [#41173301152](https://github.com/tawounfouet/pyaccountingkit/actions/runs/41173301152), recovery [#41173301138](https://github.com/tawounfouet/pyaccountingkit/actions/runs/41173301138), package [#41173301161](https://github.com/tawounfouet/pyaccountingkit/actions/runs/41173301161). **L05-06 requires its own CI evidence after this document/test commit.**

## 2. Why the matrix reports partial results

The canonical source `13` defines **18 `COA-INV` invariants** and **20 `COA-S` scenarios**. The accompanying JSON explicitly tracks every ID and one of two evidence labels:

- `RND_LOCAL_PARTIAL`: a local pure-candidate property/test exists; **the source's production invariant or scenario has not been proven**.
- `NOT_IMPLEMENTED`: no corresponding production proof or relevant capability is available in this L05 stack. **No test success is implied.**

This is deliberately not a percentage-complete certificate, a checkmark on `COA-S`, a regulatory compliance claim, or an authorized exception.

### Main open correctness gaps

| Canonical ID(s) | What R&D checks | What is actually missing |
|---|---|---|
| COA-INV-01/02/03 | Typed identities and account-code preservation, local temporal uniqueness | Durable concurrent uniqueness, published/versioned data and serialization DTO contracts |
| COA-INV-04/05 | Local nonpostable/leaf/active status candidates | A **published applicable chart**, verified C10-Q05, book and period eligibility, Ledger execution guard |
| COA-INV-06/07 | Temporal in-memory cycle and parent cardinality | Published hierarchy, governed views, concurrent publication constraints |
| COA-INV-08 | Candidate book/chart binding disambiguation | Independently governed book existence, published chart versions, SQL/authority checks |
| COA-INV-09/10/11 | Pinned account IDs, mapping resolution and nonexecuting provider intent | Approved coverage, runtime C10 mapping, mandatory completeness, specialized allocation provider |
| COA-INV-12/13/14 | Candidate checksum/replay; **no publication/archive** | Signed durable immutable publication, historic retirement/retention |
| COA-INV-15/16 | Claimed framework pointer equality, no amount/post in domain | Multi-book E2E, normative truth, double-post prevention and real chart–book framework compatibility |
| COA-INV-17 | Local `EffectiveInterval` and `KnowledgeInterval` containment | Durable exclusion constraints, simultaneous writers and signed bitemporal corrections |
| COA-INV-18 | Fake test grants for read previews | Signed independent IAM decisions, real audit chain, dual-control and COMMIT authority |

Scenario-specific examples:
- `COA-S06` (atomic publication), `COA-S16` (concurrent published versions), `COA-S20` (real multi-book projections) are **NOT_IMPLEMENTED**.
- `COA-S07` (two overlapping chart bindings) and `COA-S12` (history replay) have only **candidate-level negative tests**, not real published/committed E2E.
- `COA-S10` returns a **typed provider-required refusal**; no allocation is executed.
- `COA-S14/S15` demand actual PCG/IFRS/SYSCOHADA multi-book integration; synthetic framework code pointers are **not** normative evidence.
- `COA-S17` requires denied unauthorized access **and an audit**. The existing test fakes only exercise denial and do not supply independent live audit proof.

The register and its drift tests are therefore *proof inventory controls*, not a replacement for review by an Accounting, Architecture, Legal, Security or Runtime authority.

## 3. Canonical ADR mapping, all OPEN

**Use the source §21 identifiers verbatim. No historical renaming, reassignment, implicit sign-off or invented decision:**

| Source ADR | Canonical decision | Current status |
|---|---|---|
| ADR-COA-01 | Propriété du chart (entity/book/shared binding) | OPEN |
| ADR-COA-02 | Granularité des agrégats | OPEN |
| ADR-COA-03 | Stratégie de versionnement | OPEN |
| ADR-COA-04 | Hiérarchie, arbre ou vues multiples | OPEN |
| ADR-COA-05 | Mapping 1:N et provider spécialisé | OPEN |
| ADR-COA-06 | Priorité / spécificité des mappings | OPEN |
| ADR-COA-07 | Références normatives obligatoires ou facultatives | OPEN |
| ADR-COA-08 | Couverture totale ou partielle déclarée | OPEN |
| ADR-COA-09 | Gouvernance publication indépendante / manifeste global | OPEN |
| ADR-COA-10 | Persistance temporelle | OPEN |

The JSON provides **proposed reviewer roles**, not accepted ownership or signatures. Local prototype choices — entity scope, named views, conservative no-parent posting, always-explicit framework claim, highest unique test priority, full-content SHA-256 — **do not settle these ADRs**.

## 4. Strict execution / security / scope boundaries

- Company Configuration supplies **proposed chart/account/mapping configuration**, never debits/credits, amounts, account balance computation, journal/posting APIs, nor automatic N:1 aggregation or 1:N financial allocation.
- Candidate `BookChartBinding` and `CompanyChartVersionCandidate` do not establish a published book, a verified legal entity, normative compatibility or the current open/locked period.
- `content_digest = SHA256(...)` supports internal reproducibility, not independent signatures or nonrepudiation. A writable process can forge contents **and** recompute digests.
- No newly introduced SQL migration, privileged issuer, COMMIT-atomic IAM, signed audit/outbox, released package, or authoritative C10 `GetAccountEligibility`.
- Source §22 P0–P6 is a **target plan**, not a delivery log. L05-01–05 provide only parts of P0–P4 as isolated R&D; P5–P6 **are not reached**. Tests do not close publication/production phase gates.
- G0/G1/G2 = `PENDING_REVIEW`; G3 = `HOLD_SECURITY`, [issue #71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN; G4/G5 = `NOT_APPROVED`. No main merge.
- Status remains **DRAFT / R&D TECHNICAL**, not production-ready, accounting-compliant or certified.

## 5. Executable evidence guard

The new `tests/unit/company_configuration/test_l05_06_coa_evidence_register.py` verifies the machine register's **exact five proof slices**, source-canonical 18+20 ID coverage, ten ADRs, all signatures absent, contradictory GO claims absent, the existence of referenced local test files, documented L06 handoff, and isolation/no SQL issuer in L05 modules. These tests validate **the accuracy of the inventory metadata and architecture source boundary**, not the external legal or signed approval status.

## 6. Next cut: L06 Fiscal Calendar & Period Management

The detailed next-domain handoff is in [`L05_06_L06_FISCAL_CALENDAR_HANDOFF.md`](L05_06_L06_FISCAL_CALENDAR_HANDOFF.md). Its source of truth is uploaded `14_COMPANY_CONFIGURATION_FISCAL_CALENDAR_AND_PERIOD_MANAGEMENT.md`, especially §5–12, §16, §20–21. **L06-01 domain kernel is not implemented by L05-06**.

Proposed safe progression: L06-01 typed Calendar/Year/Period VOs and *structural* invariants → L06-02 assignment/replay candidates → L06-03 status/lock *preview* → L06 governance ADR consolidation. No posting capability, signed publication or real fiscal-period COMMIT guard until proven under G3/security.

### L05-06 exit criteria

- [x] Real L05-01–05 source/spec/test inventory and baseline qualified SHA.
- [x] All 18 source invariants and 20 acceptance scenarios classified without false proof.
- [x] All 10 source §21 ADRs copied with honest OPEN signatures.
- [x] L06 handoff and special-period/TOCTOU blockers explicit.
- [x] Executable drift checks for inventory and nonproduction boundaries.
- [ ] Exact-HEAD L05-06 Python 3.11/3.12 + Ruff + PG/recovery + packaged SQL parity.
- [ ] Independent accounting/governance/security review and authorized G3/G4/G5 release; **not** part of this work.
