# L04-08 — Accounting Books R&D Consolidation & Architecture Decision Register

**Project:** PyAccountingKit / Company Configuration / Accounting Books  
**Date:** 2026-10-30  
**Decision:** `L04_RND_SLICES_TECHNICALLY_QUALIFIED` + `L04_GLOBAL_GATE_NOT_APPROVED`  
**Machine-readable source:** [L04_08_ADR_REGISTER.json](L04_08_ADR_REGISTER.json)  
**Current upstream evidence:** draft PRs [#74](https://github.com/tawounfouet/pyaccountingkit/pull/74) → [#80](https://github.com/tawounfouet/pyaccountingkit/pull/80); **none merged to `main`**.  
**Security:** G0/G1/G2 `PENDING_REVIEW`, G3 `HOLD_SECURITY`, [#71](https://github.com/tawounfouet/pyaccountingkit/issues/71) **OPEN**. G4 has **not** been approved.

## 1. Purpose, scope, truth sources

This document is a **cross-slice technical review**, not a decision record signed by accounting/legal/security authorities and not an implementation approval. It reconciles:

1. **Actual code, tests and pull requests** in the L04-07 exact HEAD `2d0b2e67592e4aa90ec58c73c0a3336cf9d0ce81`.
2. The uploaded target specifications `12_COMPANY_CONFIGURATION_ACCOUNTING_BOOKS_AND_REFERENCE_FRAMEWORKS.md` (book boundaries, glossary and **BOOK-ADR-01..10**), `18_COMPANY_CONFIGURATION_VERSIONING_TEMPORALITY_AND_SNAPSHOTS.md` (**TMP-ADR-01..10**), `13_COMPANY_CONFIGURATION_CHART_OF_ACCOUNTS_AND_ACCOUNT_MAPPING.md` (L05 chart/mapping contracts), `10_COMPANY_CONFIGURATION_INTEGRATION_CONTRACTS.md` (C10), `07_COMPANY_CONFIGURATION_DOMAIN_INVARIANTS_AND_BUSINESS_RULES.md`, `17_COMPANY_CONFIGURATION_CONFIGURATION_LIFECYCLE_AND_GOVERNANCE.md`, `19_COMPANY_CONFIGURATION_SECURITY_AUTHORIZATION_AND_AUDIT_MODEL.md`, and `COMPANY_CONFIGURATION_IMPLEMENTATION_ROADMAP.md`.
3. Exact HEAD CI logs and independent governance blockers. **A green draft PR cannot establish an accepted accounting requirement or real-world compliance.**

The source specifications are **proposed target artifacts** and sometimes use different labels or mappings. Where code is narrower than a source target, this dossier states the gap instead of treating the code as normative proof.

## 2. Actual implementation inventory (one slice = one draft PR)

| Slice | Real implementation and test evidence | R&D qualification only | Production gap |
|---|---|---|---|
| L04-01 / PR #74 | Immutable `AccountingBookDraft`, `BookCode`, typed scope, framework pointer, candidate revision, local uniqueness | Python+PG regressions green | No publishing, book ownership proof, legal membership |
| L04-02 / PR #75 | Commands/queries, Repository and UoW Protocols, transactional **single-process** memory fake, denial tests | 363 Python tests/py | No real authentication, SQL atomicity, audit/outbox |
| L04-03 / PR #76 | Dated `BookAssignmentCandidate` and purpose-bound scope preview; proposed mono-entity guard | 388 Python tests/py | BOOK-ADR-01 unapproved; no authoritative assignment |
| L04-04 / PR #77 | Dated `ReferenceFrameworkBindingCandidate`, normative availability Protocol and local default-deny fake | 409 Python tests/py | No official framework provider/legal compatibility |
| L04-05 / PR #78 | Time-separated **unverified source declarations**, `as_of`/`known_at` claim preview | 436 Python tests/py | Not a certified registry; only normative claim bitemporal in this slice |
| L04-06 / PR #79 | Full candidate version with book/assignment/binding and both times; canonical SHA-256 candidate snapshot | 463 Python tests/py | No published configuration, signatures, durable history |
| L04-07 / PR #80 | Five-slot candidate dependencies, fail-closed date/scope completeness and SHA-256 read receipt | **492 Python tests/py**; 134 PG + 6 recovery/py | No real Chart/Calendar/Policy/RuleSet/Dimension authority, no C10 |

`/py` denotes **per Python version (3.11 and 3.12)**; these numbers are totals of the branch suite, *not* unique tests newly contributed by each slice. Tests are not additive across columns. Exact HEAD L04-07: [Python #41138391942](https://github.com/tawounfouet/pyaccountingkit/actions/runs/41138391942), [PG16 #41138391966](https://github.com/tawounfouet/pyaccountingkit/actions/runs/41138391966), [Recovery #41138391951](https://github.com/tawounfouet/pyaccountingkit/actions/runs/41138391951), [Artifacts #41138391990](https://github.com/tawounfouet/pyaccountingkit/actions/runs/41138391990): **all four success**, 14 original source/wheel/sdist SQL migrations unchanged. Version remains `0.0.0` placeholder and **unpublished**.

These results refer to the **stacked draft branch**, not the current `main`; the stack is contingent on parent draft PRs #74–#79. Failing later CI must override any earlier technical qualification.

## 3. Domain dependency graph (implemented R&D, not deployed)

```text
External Normative Layer [no official adapter]
              │
              ▼
Unverified NormativeReferenceStatement (L04-05, source claims)
              │
AccountingBookDraft (L04-01)     BookAssignmentCandidate (L04-03)
             \                         /
              \                       /
            ReferenceFrameworkBindingCandidate (L04-04)
                           │
                CandidateVersion (L04-06)
                 [effective + known_at]
                           │
               CandidateSnapshotDigest (L04-06)
                           │
          CHART / CALENDAR / POLICY / RULESET / DIMENSION (L04-07)
                   [source-declared references ONLY]
                           │
             CandidateReadReceiptDigest (L04-07)
                           │
                 NON-AUTHORITATIVE R&D
                           X
    Not connected to published C10 / RuntimePostingContext / Ledger
```

**DDD / Hexagonal** is applied in bounded form: pure domain objects and policies, typed query/command services, Protocol ports, process-local fakes. **CQRS** is used for draft mutations/queries; no final event-sourced or versioned publication architecture is claimed. **Fail-closed** is local simulation: tests cover missing/foreign/ambiguous candidate data but do not establish a non-bypassable SQL authorization boundary. Source owners of truth remain Organization, Normative Layer, Calendar/Chart/Policy systems as specified.

## 4. ADR identification corrections — must not silently rewrite sources

The canonical IDs of `12_...` §20 are authoritative for **names**, even while their decisions are open.

| Canonical ID | Correct question in source | Incorrect earlier usage to retire |
|---|---|---|
| **BOOK-ADR-01** | Can a book be shared among legal entities? | None; mono-entity preview is **not** signoff |
| **BOOK-ADR-02** | Reference held directly on book or by dated binding? | Treating the temporary direct field + binding as a final approved design |
| **BOOK-ADR-03** | **Multi-books**: parallel / adjustment / hybrid? | Mislabeling it as **normative registry authority** in some L04-04/L04-05 notes |
| **BOOK-ADR-07** | Normative reference: mutable alias or pinned version? | Calling this a certification or source-issuer approval |
| **BOOK-ADR-09** | Published snapshot design: embedded / references / hybrid? | Treating the L04-06 checksum as a signed publication proof |

For normative **source-of-authority**, this dossier uses the **new provisional local ID** `L04-NORM-AUTH-01` rather than hijacking BOOK-ADR-03. This new ID is **not** alleged to exist in the original §20. For the fixed five-slot dependency cardinality issue, it uses `L04-DEP-CARD-01`. Temporal decisions use the real `TMP-ADR-01..10` in `18_...` §18. See machine-readable full register for **24** pending/blocking decisions.

The files L04-04/05 retain their historical notes as implementation artifacts; this consolidation provides an explicit erratum, **not** an undocumented retroactive rewrite of those PR commits.

## 5. Verification matrix: established / simulated / missing

| Concern | What is proven by tests | Still missing for a release gate |
|---|---|---|
| Tenant/book scope | Local exact scope rejection, no implicit tenant | Non-bypassable SQL RLS + verified actor and tenant at COMMIT |
| Company membership | Fake explicit allowlist revocable | Independent authenticated legal relationship/version |
| Book code conflicts | Pure overlap check and locked local UoW | Durable multi-process SQL exclusion / concurrency |
| Assignment and framework | Explicit dated reference candidates, ambiguous reject | Normative legal/jurisdictional applicability; approved sharing |
| Bitemporal replay | Candidate business+knowledge windows; synthetic corrections | Published immutable history, independent writer/audit evidence |
| Dependency completeness | Exactly 5 declared-available, version-pinned **R&D slots** | L05/L06/L07/L08 real content; multi-binding policy, account and period eligibility |
| Canonical SHA-256 | Consistency of local sealed manifests; tamper tests | Trusted external signatures, canonicalization ADR, retention |
| Read receipts | Deterministic candidate receipt | Signed published C10 schema and consumer compatibility |
| Availability testing | Default-deny local test double | Trusted normative and dependency provider contracts |
| CI packaging | 14 existing migrations retained, wheel imports | Production release approval and end-to-end live evidence |

**What the checks do *not* prove:** source authenticity, legally correct framework codes, PCG/IFRS/OHADA compliance, jurisdiction rules, regulatory retention, Ledger posting, audited authorization-at-SQL-COMMIT, approval/SoD, durable publication, consumer C10 readiness, or G4 signoff.

## 6. Decision ownership / review order

1. **SEC-G3-71** (Security/IAM/DBA): issue #71 — independent signed actor command paired to live IAM decision **at SQL COMMIT**. **Hard blocker** for any SQL write or G3/G4 live gate.
2. **BOOK-ADR-01/02/03/04/07** (Accounting/Architecture/Normative): ownership, version binding, multi-books, code namespace, normative version semantics.
3. **L04-NORM-AUTH-01** (Normative/Legal/Security): accredited source, issuer authenticity, jurisdiction and versioned evidence (independent of BOOK-ADR-03).
4. **TMP-ADR-01..10**, especially 02–04 and 07 (Architecture/Governance): publication units, bitemporal corrections, signed canonical profile and replay.
5. **L04-DEP-CARD-01** (Accounting/L05-L08 owners): real optional/required/multi-valued chart/calendar/policy/dimensions.
6. **L04-C10-CONTRACT-01** (Runtime/Consumer): published read DTO, version/schema, revocation and cache policy, receipts.

The `proposed_owner_role` field is a **review role suggestion**, not proof that a person/team accepted ownership. Every ADR remains `OPEN_UNAPPROVED`, except the hard blocker `SEC-G3-71` with `BLOCKED_HOLD_SECURITY`; `signed_decision_ref` remains null.

## 7. Gate interpretation and promotion path

```text
             PR #74 -> #75 -> #76 -> #77 -> #78 -> #79 -> #80
                          DRAFT / R&D-only
                                |
                         L04-08 consolidation
                                |
                   Documentation + test proof
                                |
                    [STOP: G3 HOLD_SECURITY]
                                X
     No merge main, no G4_GO, no SQL writer, no published C10
```

For formal G4 qualification, require at least: signed relevant book ADRs; independent normative legal/version compatibility and source authority; approved L03 ownership/membership; real security proof resolving #71; durable conflict-free persistence and signed publication; outbox/audit linkage; negative isolation and concurrency tests; downstream C10 integration/consumer qualification. The full G4 scope is broader than these prototype tests.

## 8. Next cut: isolated L05 — Chart of Accounts & Account Mapping

**Proposed next R&D slice:** L05-01 `Chart/Account Domain Kernel` only, on a **separate branch from `main`** or explicitly acknowledged stacked isolated base. No SQL writer, no reliance on `BookDependencyRef(CHART)` as a published chart, no use of `L04` draft book as a production owner.

Before L05 chart authoring, consult `13_COMPANY_CONFIGURATION_CHART_OF_ACCOUNTS_AND_ACCOUNT_MAPPING.md` §2, §4–7, §11, §21–22; build `CompanyChart`, `CompanyAccount`, `AccountCode`, `AccountHierarchyEdge`, `BookChartBinding`, `MappingSet` in **incremental** scope. Design the account identity/code distinction and account nature/bookability independently of IFRS chart universality.

The handoff must explicitly distinguish chart configuration from Ledger effects and from account eligibility at posting. See [L04_08_L05_CHART_OF_ACCOUNTS_HANDOFF.md](L04_08_L05_CHART_OF_ACCOUNTS_HANDOFF.md).

## 9. L04-08 exit checklist (bounded)

- [x] Verify all seven L04 slices' source, tests, draft PRs and CI evidence against exact branch state.
- [x] Reconcile the canonical ADR IDs with `12` and `18`; document `BOOK-ADR-03` correction.
- [x] Versioned machine-readable register with no invented signoffs.
- [x] Document security and normative/provider blockers, fake-versus-authoritative contracts.
- [x] Produce L05 handoff and executable registry drift tests.
- [ ] Exact HEAD Python 3.11/3.12 + Ruff and Foundation regression (post PR open).
- [ ] Signed domain/architecture/security review; G3 resolution; G4 authorization (**not in this scope**).

**Decision type:** `L04_08_RND_CONSOLIDATION_CANDIDATE` until CI. Do not interpret this as L04 G4 closure, deployment, package release or live production qualification.
