# L06-07 — Multi-Book Candidate Replay, Coverage & R&D Qualification

**As of:** 2026-10-31  
**Status:** `L06_07_MULTIBOOK_RND_CANDIDATE` pending exact-HEAD CI. **NOT** `CAL-L7` live E2E completed, nor `G6_GO`.  
**Stack:** [L06-06 draft PR #93](https://github.com/tawounfouet/pyaccountingkit/pull/93) @ `0c87bc0be811e65a483564bf45cc63481bee4d8c` → #92 → #91 → #90 → #89 → #88 → unchanged `main@acdee98ca2736d79e17174f510ac767defd90db8`; no unmerged L03/L04/L05 dependency.  
**Canonical source:** `14_COMPANY_CONFIGURATION_FISCAL_CALENDAR_AND_PERIOD_MANAGEMENT.md` §4 multi-book, §9 four dates, §10 COMMIT anti-TOCTOU, §12 CAL-INV-01..12, §16 CAL-SC-01..20, §17 (unit/property-based/integration/concurrence/E2E/replay strategy), §20 ADR-CAL-01..10, §21 CAL-L7. Also `10` C10-Q04, `12` books/frameworks, `17` governance, `18` historical snapshots, `19` signed authority and `20` persistence.
**Machine-readable matrix:** [L06_07_CAL_INVARIANTS_AND_SCENARIOS_COVERAGE.json](L06_07_CAL_INVARIANTS_AND_SCENARIOS_COVERAGE.json), 12 invariants + 20 scenarios, explicit statuses `CANDIDATE_PARTIAL` versus `NOT_IMPLEMENTED_LIVE` and 10 OPEN ADRs.

## 1. Architectural question and provisional choice

Source §4 explicitly permits two books within one entity to have different accounting periods and closure dates. A shared calendar is allowed only through an explicit versioned book/calendar assignment; it must not implicitly share status or lock operations across books. **ADR-CAL-01 remains OPEN**. Source CAL-SC-05 wants independent PCG and IFRS configurations but **full normative compatibility requires expert validation** not offered here.

```text
        Same claimed tenant/company/legal entity (NOT independently verified)
                                  |
                  +---------------+---------------+
                  |                               |
             Book A (PCG_RND)                Book B (IFRS_RND)
                  |                               |
      explicit typed book scope         explicit typed book scope
                  |                               |
    [assignment V1, V2 as known]        [assignment V3]
                  |                               |
    Jan–Dec FY / P01 P02             Apr–Mar FY / H01 H02
       as_of 2027-02-15                as_of 2027-02-15
        |              |                         |
   known_at=Feb   known_at=Mar             both known_at dates
        |              |                         |
    original P02     restated P01              H02, unchanged
    OPEN observed    CLOSED observed           OPEN + source lock
        |              |                         |
       +--------------+-------------------------+
                                  |
           qualify_multibook_candidate_replay(...)  [pure]
                                  |
                  MultiBookReplayCandidateReport
       exact calendar receipt + period control diagnostic + strict
       L06-05 UNTRUSTED_CANDIDATE_SIMULATION wire for every book/date
       deterministic local SHA-256; replay revalidation; no posting authority
       six never-approved LIVE gates; NO G6 GO
```

These labels are test-only **unverified framework names**, not a real approved PCG or IFRS accounting book. There is no Ledger, C10-Q04 provider, posting, SQL store or live IAM anywhere in the L06-07 implementation.

## 2. Domain/application objects and invariants

`BookCandidateFixture` holds exactly one typed book scope, candidate `CalendarVersionCandidate`s, explicit `BookCalendarAssignmentCandidate`s, period state observations, scoped locks and unexecuted declarations. It validates the **entire local catalog**, including inactive/future records: no foreign tenant/company/entity/book; no orphan state/lock/transition period or version; unique calendar version identities, assignment IDs and direct version/calendar references. Multiple books can point to the **same exact version** when separate assignments are explicit.

`BookReplayQueryCandidate` requires exact book scope, `posting_date: date` and aware `known_at: datetime`; no optional knowledge fallback and no implicit period change.

`qualify_multibook_candidate_replay(fixtures, queries, completeness)` requires at least two book fixture catalogs for one claimed entity and **at least one replay query per book**, rejects duplicate books, duplicated assignment ID across books, foreign/unregistered requested scope, duplicate book/date/normalized UTC knowledge cutoffs, and catalog types other than immutable tuples. It resolves *the complete source catalog* with L06-02 exact version as-of/known-at, L06-03 one period-specific observed status and locks, and L06-05 strictly non-authorizing simulated C10 wire.

`BookReplayCandidateEvidence` pins the original calendar receipt, exact period controls and response. It verifies the nested digests and L06-05 wire round trip. `MultiBookReplayCandidateReport` sorts independent query evidence deterministically by book ID/date/UTC knowledge, stores all evidence and a canonical SHA-256 local checksum, and recomputes full evidence on verification (so a modified input catalog or invented result cannot be silently accepted).

**Design concepts (Software Design & Learning):** DDD typed identity, Value Object, immutable candidate aggregate, Composite Query / CQRS, Hexagonal read-only port composition, dependency-safe reuse, fail-closed scoped reads, snapshot/replay and deterministic evidence manifests. The report is a **self-consistency receipt only**; a Python object could be mutated and rehashed by a hostile same-process actor. This is not a cryptographic signature, signed audit or durable snapshot.

## 3. Bitemporal and multi-book scenarios

A single requested business date `2027-02-15` demonstrates four historical candidate readings:

| Claimed book | Historical cutoff | Exact pinned candidate | Period | Observed (unverified) restriction |
|---|---|---|---|---|
| PCG_RND | `2027-02-01T00:00Z` | Version V1 valid in old knowledge | P02 | OPEN, no locks observed |
| PCG_RND | `2027-03-01T00:00Z` | Corrected version V2 | P01 | CLOSED observation |
| IFRS_RND | `2027-02-01T00:00Z` | Own Apr–Mar V3 | H02 | OPEN, scoped SOURCE_LOCK observation |
| IFRS_RND | `2027-03-01T00:00Z` | Same V3 | H02 | OPEN, same scoped lock |

The February original-known P02 receipt remains reproducible after the March restatement. IFRS book configuration is independent and remains on H02. A scoped lock on IFRS must never leak into the PCG book; nor does one book's CLOSED observation imply another's close. The source §4 allows actual shared calendar definitions through **explicit** assignments; a dedicated test illustrates two books referencing the same version **without sharing control observations**.

If a book has no assignment or its exact historical version is unavailable, qualification **fails** rather than selecting another book, period or latest version. A replay with one book omitted also fails as incomplete evidence. A malformed record (including an inactive foreign-source lock) invalidates the full fixture.

## 4. Evidence is not the source CAL-L7 acceptance gate

The canonical source §17 demands **real SQL/FK/migration/rollback**, actual transactionally committed publication and Outbox, a certified `GetPeriodStatus`, real simultaneous close/post races, real Revenue/AR/Purchasing/AP/FixedAssets/Payroll integration and signed historical snapshots. **These do not follow from passing candidate R&D Python tests.**

The `MultiBookReplayCandidateReport` exposes six **permanently unproven** production dependencies:

1. `VERIFIED_ACCOUNTING_BOOK_AND_NORMATIVE_FRAMEWORK`
2. `APPROVED_PUBLISHED_CALENDAR_AND_AUDIT`
3. `AUTHORITATIVE_C10_Q04_AND_LOCKS`
4. `SIGNED_SQL_ACTOR_AND_ISSUER`
5. `REAL_CLOSE_POST_COMMIT_FENCING`
6. `REAL_MULTIBOOK_E2E_AND_MIGRATION_RECOVERY`

This does not contradict that *existing Foundation migrations* are regularly tested in GitHub Actions. Those tests cover the earlier 14 SQL migrations and isolated packaging; they **do not implement or qualify L06 live schema migrations or SQL period-state fencing**. The report fields are always `live_e2e_qualified=false`, `migration_to_production_qualified=false`, `published=false`, `posting_authorized=false`.

### Gap matrix summary and guardrail

All **12 CAL-INV** and **20 CAL-SC** are recorded in the JSON traceability matrix. Partial R&D validation of structural rules, bitemporal candidate replay and explicit book scope does not mean source production acceptance. **CAL-INV-04/05/06/07/10/12, CAL-SC-06/07/08/09/10/11/15/16/17/20** remain **NOT IMPLEMENTED LIVE**. Partial cases are only structural candidate tests.

**Issue [#71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN**, G3 `HOLD_SECURITY`; G0/G1/G2 `PENDING_REVIEW`, G4/G5/G6 `NOT_APPROVED`, ADR-CAL-01..10 **OPEN**. The status `CANDIDATE_PARTIAL` is **not** a review approval or a legal/accounting compliance finding.

## 5. Test design, architecture guarantees, release limits

Test module `tests/unit/company_configuration/test_l06_07_multibook_replay_qualification.py` includes:
- Two named PCG/IFRS **candidate** books with separate calendars; mixed fiscal-year boundaries and business-date coverage.
- Original-known vs restated calendar, period and state; unchanged other book/lock; replay order/timezone determinism.
- Explicit shared calendar version with separate book assignments, no state or lock sharing.
- No fallback for missing historical version/assignment or book with missing binding.
- Mixed tenant/company/legal entity, foreign-book and orphan entries, duplicate book/assignment/query keys including timezone-equivalent replay.
- Evidence/digest tampering, forged G6 state, unverified lock completeness and never-postable C10 simulation.
- A 365-date test of a candidate year under L06-01 coverage invariants, **not a property-based randomized proof**.
- Architectural denial of SQL/HTTP/live Ledger provider.

The PR intentionally does **not** create a database migration, Ledger journal, live C10, publisher, production chart/book and policy, authorization token, signed actor/issuer, or a production E2E harness. The 14 existing Foundation SQL migrations are checked **only by existing workflows**, not by this new pure module.

## 6. Acceptance and handoff

- [x] Multi-book candidate scope isolation and explicitly versioned calendar assignments.
- [x] Original/restated exact history replay with stable per-book evidence.
- [x] Strict nonauthoritative L06-05 consumer round trip and refusal of posting.
- [x] Immutable candidate report and 12-invariant/20-scenario gap matrix.
- [x] Negative scope, ambiguity, reference integrity, missing history and forged evidence tests.
- [ ] Exact-head Python 3.11/3.12 + Ruff, Foundation PG/recovery, wheel/sdist 14 SHA256 migration parity.
- [ ] Actual CAL-L7 production E2E, published calendar, authorized journals, signed IAM/SQL issuer, atomic close/post COMMIT, target L06 schema migrations and approvals — **NOT IMPLEMENTED**.

**Engineering conclusion:** the *seven-piece L06 R&D candidate stack* can be internally technically qualified if exact-HEAD CI passes; it **cannot** close the production L06 (G6) milestone or replace security issue #71 resolution.

**Next safe direction:** L06 R&D final consolidation/architecture ADR decision register and prepare L07 — Accounting Policies & RuleSets in isolated candidate form, while separately prioritizing production gate #71 and deciding ADR-CAL-07/08 before any live posting.
