# L05-03 — Candidate Chart Versions, Bitemporal BookChartBindings & Read Receipts

**Date:** 2026-10-31  
**Status:** `L05_03_RND_CANDIDATE_NOT_PUBLISHED`; exact-head CI pending.  
**Base:** [L05-02 draft PR #83](https://github.com/tawounfouet/pyaccountingkit/pull/83), head `6ff7cf7300c42e58547a845555fb1c0ab8b23836`. PR #82 derives from `main@acdee98c` and imports **no unmerged L04 PR**.  
**Source basis:** `13_COMPANY_CONFIGURATION_CHART_OF_ACCOUNTS_AND_ACCOUNT_MAPPING.md` §2, §4, §6, §10–13, §19, §21–22; `18_COMPANY_CONFIGURATION_VERSIONING_TEMPORALITY_AND_SNAPSHOTS.md` §2–8. The source describes **published** `CompanyChartVersion` and authoritative runtime resolution, neither of which exists here.  
**Release gates:** G0/G1/G2 `PENDING_REVIEW`; G3 `HOLD_SECURITY`; [#71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN; G4/G5 unapproved.

## 1. Domain distinction

The target `CompanyChartVersion` is an **approved/published immutable chart version**; in L05-03 the concrete Python object is named **`CompanyChartVersionCandidate`** on purpose. It is a frozen R&D proposal containing the chart draft, accounts, hierarchy-edge candidates and account-status proposals from L05-01/02. It is **not** a publishable or externally valid `ConfigurationVersion`. The source's `BookChartBinding` is represented only by **`BookChartBindingCandidate`**, an explicit claim to link a book ID to one exact chart-candidate version ID.

```text
CompanyChartDraft ─────┐
CompanyAccountDraft[] ─┤
HierarchyEdge[] ───────┼─> CompanyChartVersionCandidate
AccountStatus[] ───────┤      id · effective [a,b) · knowledge [t0,t1)
FrameworkRef(claim) ───┘      canonical full-content SHA-256
                                 │
BookChartBindingCandidate        │
 book_scope (tenant/company/entity/book_id)
 purpose (provisional typed BookChartPurpose)
 chart_id + exact chart_version_id
 framework claim, effective + knowledge
          │                      │
          └───── exact match ────┘
                       │
       preview_book_chart_candidate(as_of,known_at)
                       │
       BookChartCandidateReadReceipt
       SHA256(chart digest + binding + date + source)
       UNPUBLISHED_RND_PREVIEW, not C10/eligibility
```

**Bounded R&D policy:** a candidate version and the requesting binding each carry an explicit **versioned** `ReferenceFrameworkRef`, and exact equality is required. This is **not** verification of normative/legal compatibility, which is owned by the independently authenticated Normative Layer. This conservative prototype does **not settle ADR-COA-07**, under which a normative pointer could be optional in some target contexts. It simply refuses to infer a default or latest edition.

**Book scope ownership:** there is no L04 book entity available on the isolated L05 branch. `AccountingBookId` in `ConfigurationScope` is a typed but **unverified external book intention**, not evidence of Organization membership, approved BookAssignment or published Book. `BookChartPurpose` is a local value object deliberately independent of L04's draft `BookAssignmentPurpose`.

## 2. Domain contracts and deterministic hashing

**Value Objects / entities**:
- `CompanyChartCandidateVersionId` and `BookChartBindingCandidateId`: typed stable identities distinct from chart/book/account IDs and real published ConfigurationVersionId.
- `CompanyChartVersionCandidate`: frozen Python candidate with exact Chart/Account/Hierarchy/Status contents; fully validates the chart/account hierarchy and statuses (IDs, scope, temporal containment, absence of overlapping statuses) before sealing a checksum.
- `BookChartBindingCandidate`: typed book scope, purpose, chart identity, pinned version ID, explicit business `EffectiveInterval`, aware `KnowledgeInterval`, claimed framework pointer and source-ref.
- `BookChartCandidateReadReceipt`: immutable R&D resolution result with exact candidate version ID, digest, binding ID, as-of/known-at, framework claims and provenance.

**Canonical profile `l05-rnd-candidate-v1`:** sorted UTF-8 JSON with `sort_keys=True`, `ensure_ascii=False`, `separators=(',', ':')`, `allow_nan=False`; stable canonical UUIDs; business dates ISO `YYYY-MM-DD`; knowledge instants UTC with `Z` and microseconds. Arrays of accounts/edges/statuses sorted by typed entity ID. **Digest: `sha256:<64 lowercase hex>`**. The digest is a **self-consistency checksum**, **not** independent proof of source authenticity, signatures, nonrepudiation, approved contents or regulated retention.

`verify_integrity()` recomputes a manifest's digest and rejects changes. Frozen Python dataclasses are not cryptographic immutability; content and hashes may both be replaced by a malicious in-process caller. A credible publication later needs approved canonical schema, append-only durability, authenticated proof, independent approvals, signed issuer records and atomic outbox.

## 3. Two time axes and deterministic refusal

The pure `preview_book_chart_candidate` requires exact `book_scope`, `BookChartPurpose`, `as_of: date`, timezone-aware `known_at: datetime`, immutable tuples of bindings and chart candidates. It:

1. Refuses untyped input or any foreign-book binding — never silently filtering a malicious read catalog.
2. Refuses repeated binding IDs, no current binding or **multiple active bindings** for the book/purpose/business date/knowledge instant (COA-INV-08 candidate).
3. Requires the selected binding's **exact chart version ID** to exist in the supplied scoped catalog, refuses duplicate chart version IDs, foreign chart scope or failed digest even for nonselected catalog entries; **no fallback to latest**.
4. Validates exact chart ID, tenant/company/entity, purpose, binding effective interval fully contained in chart version, both knowledge windows, as-of in effective window and **exact equality of declared framework code+edition**.
5. Returns a version-pinned receipt with provenance/checksum. No runtime account eligibility, fiscal-calendar check or postable period is inferred.

**Bitemporal synthetic example, not a claim about real PCG:**
- `as_of=2026-02-15, known_at=2026-02-01`: old chart version V1 and book binding B1, both known Jan→Mar.
- `as_of=2026-02-15, known_at=2026-03-01`: revised chart V2 and binding B2, both known since Mar.
- The same business date yields **two distinguishable, reproducible receipts**. A future V2 never backfills the original known-at resolution.

The source `13` §10 also distinguishes actual `posting_time`, which remains outside this feature.

## 4. Hexagonal/CQRS R&D composition

```text
PreviewBookChartCandidate
     scope, purpose, as_of, known_at
                │
     BookChartCandidatePreviewService
         ├─ Verified principal TYPE check + tenant equality
         ├─ AuthorizationPort.require("chart.binding.candidate.preview")
         ├─ BookChartBindingsReader (Protocol)
         ├─ ChartCandidateVersionsReader (Protocol)
         └─ preview_book_chart_candidate (pure policy)
                │
     BookChartCandidateReadReceipt
```

`MemoryBookChartBindings` and `MemoryChartCandidateVersions` are process-only read fixtures and cannot certify account, book or chart ownership. A Python `TrustedPrincipal` value can be constructed by a test caller; it **does not verify** signed IAM or establish a real legal relationship. The service grants no posting/approval privileges, contains no SQL/HTTP/ledger client, and never exposes a live C10 endpoint.

**Patterns:** DDD typed Entities and Value Objects, immutable composite snapshot (candidate), Domain Policy, Hexagonal Ports/Adapters, CQRS read-only service, Dependency Inversion, optimistic no-latest fallback, strict scope boundaries, fail-closed temporal resolution, explicit R&D content-digest envelope.

## 5. Negative / acceptance contract

| ID | Source invariant | Prototype criterion |
|---|---|---|
| L05-V-01 | COA-INV-01/02/03 | Chart version seals exact account codes/IDs, labels, status and hierarchy; leading zeroes preserved |
| L05-V-02 | COA-INV-06/07 | Candidate version construction rechecks hierarchy cycles/multiple parents |
| L05-V-03 | COA-INV-08 | Two effective book bindings for one purpose/date/knowledge = ambiguous |
| L05-V-04 | COA-INV-12 partial | Candidate version frozen; manifest mismatch detected, **no publication** |
| L05-V-05 | COA-INV-13 partial | Candidate read receipt pins binding/version/dates/source/digest |
| L05-V-06 | COA-INV-16 partial | Exact declared framework pointers must match; **no normative certification** |
| L05-V-07 | COA-INV-17 | Binding validity contained in referenced chart candidate validity |
| L05-V-08 | TMP-10/11/12/14/15 partial | Known-at, as-of, correction replay, ambiguity and missing version fail closed |
| L05-V-09 | Scope security | Foreign tenant/company/entity/book bindings and foreign chart versions rejected |
| L05-V-10 | Tamper integrity | Mutated chart, account, version digest or binding receipt detected |
| L05-V-11 | Hexagonal | Default-deny fake grant, cross-tenant actor and malicious reader denied |
| L05-V-12 | Production safety | No SQL DDL, migration, publication, Ledger, C10 account eligibility or signed authority |

## 6. Decisions and blockers

- **ADR-COA-01:** chart belongs to entity/book/shared with binding — open; exact entity scope is a conservative local R&D intent.
- **ADR-COA-02:** chart/account aggregate granularity and transaction — open; composite candidate does not impose persisted aggregate architecture.
- **ADR-COA-03:** snapshots complete vs revisions/manifests — open; one self-contained prototype does not settle persistence strategy.
- **ADR-COA-07:** normative reference mandatory by framework — open; this prototype explicitly requires claim equality and refuses absent claims.
- **ADR-COA-09/10:** approval/atomic publication, bitemporal tables, retention/real evidence — open.
- **BOOK-ADR-01/03:** legal Book sharing and multi-book strategies — still open upstream. No importing unmerged L04 contracts.
- **SEC #71 / G3:** live independently signed IAM actor-command pair at SQL COMMIT still unproven; no SQL writes allowed.
- **L05-04 mapping:** not implemented. Book-chart binding cannot create implicit mappings, allocated amounts, extra posting, account eligibility or reconciliation.

## 7. Qualification and next milestone

- [x] Typed IDs, immutable versioned composite and dated book binding candidates.
- [x] Pure bitemporal exact-version resolution and SHA-256 candidate receipt.
- [x] Read-only Protocol ports and immutable memory fixtures, deny-first fake authorization.
- [x] Negative tests for duplicated/missing bindings, corrections, scope, time, framework mismatch and tampering.
- [ ] Exact-HEAD Python 3.11/3.12 + Ruff, PostgreSQL Foundation regression, recovery and source/wheel/sdist migration parity.
- [ ] Independent Accounting, Chart, Normative, Governance and Security ADR signoff; G3/G4/G5 not approved.

**Engineering label before CI:** `L05_03_CHART_VERSION_BINDING_RND_CANDIDATE`. Next safe R&D scope: **L05-04 MappingSet / AccountMapping candidates**, beginning with 1:1 and N:1 deterministic mapping resolution, never implicit 1:N allocation or Ledger posting.
