# L04-07 — Book Dependency Completeness & Candidate Read Receipts

**Date:** 2026-10-30  
**Milestone:** L04-07, independent R&D candidate stacked on [L04-06 PR #79](https://github.com/tawounfouet/pyaccountingkit/pull/79) @ `7ef6f7cbbb2727af0874e2347d8b5a7b8076ae59`.  
**Decision:** `L04_07_RND_CANDIDATE_ONLY`; NOT approved C10, NOT legal/operational book eligibility, NOT published.  
**Gates:** G0/G1/G2 `PENDING_REVIEW`, G3 `HOLD_SECURITY`, [security issue #71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN.

## 1. Traceability to uploaded target specifications

- `12_COMPANY_CONFIGURATION_ACCOUNTING_BOOKS_AND_REFERENCE_FRAMEWORKS.md` §5.2 defines `BookChartBinding`, `FiscalCalendarBinding`, `BookPolicyBinding`, `BookRulesetBinding`, `BookDimensionBinding`; its BOOK-05/06/07 demand no ambiguity, normative compatibility and valid applicable calendars.
- `13_COMPANY_CONFIGURATION_CHART_OF_ACCOUNTS_AND_ACCOUNT_MAPPING.md`: a BookChartBinding alone **does not establish individual account eligibility**; accounts/mappings/statuses/dimensions require distinct tests and versions.
- `14_COMPANY_CONFIGURATION_FISCAL_CALENDAR_AND_PERIOD_MANAGEMENT.md`: calendar linkage alone **does not prove a period is open or unlocked**; posting status is a separate authoritative, time-sensitive control.
- `07_COMPANY_CONFIGURATION_DOMAIN_INVARIANTS_AND_BUSINESS_RULES.md`: CFG-03/04/06/07/08 and INV-TMP-03 require complete, version-pinned and reproducible dependencies, without current-version fallback.
- `10_COMPANY_CONFIGURATION_INTEGRATION_CONTRACTS.md`: published C10 snapshots must cover chart, calendar, policies, rulesets, dimensions and normative metadata, with a verifiable immutable identity/digest. No internal read receipt is automatically a public C10 contract.
- `17`/ `18` governance and temporality: approvals, independent authority, signed publication, bitemporal versions and atomic outbox needed for a *real* snapshot; none is supplied by this R&D slice.

These docs specify **targets**; their references cannot prove current service implementation, legal status or independent approval.

## 2. Bounded engineering decision

L04-07 introduces a deliberately restrictive **fixed five-slot R&D dependency profile**:

| Prototype slot | Intended target | What the candidate actually attests |
|---|---|---|
| `CHART` | BookChartBinding / chart version | A source declared an explicit code + version |
| `CALENDAR` | FiscalCalendarBinding / calendar version | A source declared an explicit code + version |
| `POLICY` | BookPolicyBinding | One declared policy reference |
| `RULESET` | BookRulesetBinding | One declared ruleset reference |
| `DIMENSION` | BookDimensionBinding | One declared dimension-schema reference |

**This is NOT the final production cardinality policy.** Real books can use multiple policies/rulesets scoped by dimensions, priorities and purposes, and account mapping can be required depending on the operation. The one-slot-per-kind test profile is a conservative prerequisite check, not a legal conclusion about which dependencies are sufficient.

A *complete candidate* means **exactly one available source claim for each of these five slots at the requested effective and knowledge cutoffs, all pinned to the exact same unpublished candidate book version**. It does **not** mean that any external content actually exists, is published, is normatively compatible, has correct account statuses, yields valid policy precedence, or authorizes posting.

## 3. DDD / hexagonal architecture

```text
BookDependencyClaim (immutable)
  ├── BookDependencyClaimId (typed UUID)
  ├── BookCandidateVersionId (L04-06 unpublished version identity)
  ├── ConfigurationScope (exact tenant, Company, LegalEntity, Book)
  ├── BookDependencyKind (CHART/CALENDAR/POLICY/RULESET/DIMENSION)
  ├── BookDependencyRef (code + explicit version)
  ├── EffectiveInterval [business_from, business_to)
  ├── KnowledgeInterval [known_from, known_to)
  ├── BookDependencyDeclaration (DECLARED_AVAILABLE / DECLARED_UNAVAILABLE)
  └── source_ref (unverified provenance pointer)

PreviewBookDependencyReadReceipt
  └── PreviewBookConfigurationSnapshot (scope/purpose/source/as_of/known_at)
       └── BookDependencyReadReceiptService
            ├── BookDraftAuthorization (separate dependency and snapshot actions)
            ├── CompanyEntityMembership (test-only fake)
            ├── BookCandidateSnapshotPreviewService (L04-06 read only)
            └── BookDependencyCandidateReader Protocol
                 └── MemoryBookDependencyClaims (process-only fixture)
                      └── preview_book_dependency_completeness() (pure)
                           └── BookDependencyCandidateReadReceipt
                                 - exact BookConfigurationCandidateSnapshot
                                 - 5 sorted/versioned/dated source claims
                                 - canonical JSON SHA-256 receipt
```

- **DDD / Value Objects:** typed IDs, typed reference and immutable intervals; statement identity is separate from book version and account/chart itself.
- **Pure domain policy / SoC:** rejects incomplete/ambiguous/foreign catalogs without SQL or transport.
- **Hexagonal / DIP:** service depends on a read-only Protocol; memory fixture is *not* a certified dependency registry.
- **CQRS query half:** returns an untrusted *candidate* read receipt; never mutates a journal, book, source registry or published configuration.
- **Explicit data lineage:** receipt digest binds its snapshot SHA-256 and canonical complete claim manifest; this is not a trusted signature nor durable audit.

## 4. Executable invariants (L04-DEP)

| ID | Rule | Negative proof |
|---|---|---|
| L04-DEP-01 | Typed BookDependencyClaimId, BookCandidateVersionId, book scope | wrong IDs/types |
| L04-DEP-02 | Each reference has an explicit canonical code + edition | missing/uncanonical ref |
| L04-DEP-03 | Exact same candidate version ID and book scope | foreign tenant/entity/version |
| L04-DEP-04 | Every required kind has exactly one active claim | missing & duplicate kinds |
| L04-DEP-05 | Source declarations use both effective dates and aware knowledge instants | future effective/knowledge tests |
| L04-DEP-06 | Explicit DECLARED_UNAVAILABLE fails, no implicit substitutes | unavailable test |
| L04-DEP-07 | Repeated claim identity fails even if not active at the cutoff | duplicate test |
| L04-DEP-08 | Stable receipt ordering independent of reader input order | shuffled fixture test |
| L04-DEP-09 | Signed/approved book snapshot not asserted; content digest self-consistent | tamper tests |
| L04-DEP-10 | Both snapshot and dependency-read actions checked independently | revoked grant tests |
| L04-DEP-11 | Missing legal relationship or cross-tenant actor denies read | default-deny tests |
| L04-DEP-12 | No SQL, C10 publication, Ledger/posting or official registry imports | architecture tests |

## 5. Canonicalization contract (non-authoritative)

Profile `l04-dependency-rnd-1`, UTF-8 `json.dumps(..., sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)` + SHA-256. Each claim's manifest includes its ID, explicit version, full tenant/company/entity/book scope, type, code and version, business and UTC-normalized knowledge intervals, declaration and source pointer. The receipt also pins the L04-06 **candidate snapshot content digest**, candidate version ID, query business date, UTC knowledge instant and `NON_AUTHORITATIVE_RND_DEPENDENCY_PREVIEW` marker. Receipt digest is computed *excluding its own digest field*. `verify_integrity()` recomputes both the original candidate snapshot and receipt manifests.

**Not tamper-proof:** a caller who can replace content and recompute the digest can forge an equivalent receipt. No external signature, certified source, authenticated statement, append-only WORM storage, HSM, KMS, audit/outbox or verifier key is included.

## 6. Unresolved blockers / ADRs

- **BOOK-ADR-01:** book ownership/cardinality, legal membership, shared books.
- **BOOK-ADR-03:** normative framework authority, jurisdiction and exact recognized editions.
- **L05 COA:** chart/version authority, account hierarchy, eligibility and account-mapping policies; absence of individual account eligibility checks is deliberate.
- **L06 Fiscal Calendar:** actual fiscal period coverage, close/open/lock/reopening status and controlled posting authorization; merely declaring CALENDAR is insufficient.
- **L07 policies and dimensions:** real multi-binding priority/resolution, compatibility, business-specific mandatory/optional requirements, chart-to-dimension rules; one R&D slot does not settle cardinality.
- **C10:** independent immutable publication identity, snapshot schema & signed read receipts, consumer-driven contract tests, versioned event/read API.
- **Security:** G0/G1/G2 unsigned; L03 G3 `HOLD_SECURITY` and #71 open for independent IAM signed-command check at SQL COMMIT; all fake auth/membership remains non-authoritative.

## 7. Qualification / roadmap

- [x] Version-bound typed source dependency claims with business + knowledge dates.
- [x] Fail-closed five-slot candidate completeness and deterministic digest receipt.
- [x] Read-only service/reader fake, explicit double authorization checks.
- [x] Negative tests for missing, ambiguity, unavailable, time mismatch, source/cross-scope leakage, changed historical receipts and tampering.
- [ ] Exact-head GitHub CI Python 3.11/3.12, PostgreSQL Foundation, migration recovery and wheel/sdist parity.
- [ ] Independent domain/accounting/legal approval of slot/cardinality policy and L05/L06/L07 binding contracts.
- [ ] No approval or SQL work before resolution of #71/G3 and published-governance architecture.

**Status until CI:** `L04_07_RND_CANDIDATE`. Not `L04_GO`, `G4_GO`, `C10_READY`, `PERIOD_POSTABLE`, `ACCOUNT_ELIGIBLE` or compliance certified.
