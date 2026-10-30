# L04-03 — BOOK-ADR-01 / Book Ownership, Assignment & Preview

**Date:** 2026-10-30  
**Status:** `PROPOSED_RND_GUARDRAIL` — **not an approved ADR or gate**, not production.  
**Parent:** [L04-02 draft PR #75](https://github.com/tawounfouet/pyaccountingkit/pull/75) @ `44c063198aab95be6442eb081e54d36b320f75f1`.  
**Security:** G0/G1/G2 `PENDING_REVIEW`; G3 `HOLD_SECURITY`; [issue #71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN. Zero SQL migrations or calls to L03 controlled SQL issuer paths.

## 1. Traceability — stated target documents, not current code truth

- `06_COMPANY_CONFIGURATION_DOMAIN_RELATIONSHIPS_AND_ERD.md` describes candidate N:M LegalEntity ↔ AccountingBook through `BookAssignment`, explicitly **ADR OPEN**; the diagram is conceptual, not authorization to share the Ledger.
- `11_COMPANY_CONFIGURATION_ORGANIZATION_AND_LEGAL_ENTITY_MODEL.md` warns not to lock `AccountingBook.legal_entity_id` into the physical schema before the book-sharing decision.
- `12_COMPANY_CONFIGURATION_ACCOUNTING_BOOKS_AND_REFERENCE_FRAMEWORKS.md`, BOOK-ADR-01, recommends **mono-entity at posting initially** while retaining an extensible `BookAssignment` representation. It lists `BOOK_ASSIGNMENT_MISSING`, `BOOK_ASSIGNMENT_AMBIGUOUS` and the target `ListEligibleBooks` / `GetBookAssignments` names.
- `07_COMPANY_CONFIGURATION_DOMAIN_INVARIANTS_AND_BUSINESS_RULES.md` states INV-BOOK-02 dated explicit assignments, INV-BOOK-03 no unauthorized book, conditional INV-BOOK-04 unique primary, and CFG-06 no ambiguous configuration.
- `08_COMPANY_CONFIGURATION_COMMANDS_QUERIES_AND_USE_CASES.md` states CMD-05 `AssignBookToLegalEntity` as a **target** and specifies command authorization/audit; `10` C10-Q08 and `18` require **published identity and bitemporal `known_at`** for authoritative runtime selection.

The cited upstream docs are `PROPOSED`. No target business/legal approver has endorsed book sharing or assigned rights by implication.

## 2. ADR options and provisional technical decision

| Option | Benefit | Risk | Status |
|---|---|---|---|
| A — Book dedicated to one legal entity for posting | Strong accounting/legal isolation and separate GL identities | Need explicit separate books for other entities | **Recommended initial posting policy, subject to ADR signoff** |
| B — Shared book via dated N:M assignments | Reusable group arrangements, fewer logical books | Shared journals / tax/entity separation becomes ambiguous without deep ledger design | **Deferred / NOT permitted for posting** |
| C — Reusable configuration template, distinct concrete books by entity | Reuse without sharing an accounting ledger | Version lineage, copy semantics and template provenance to qualify | **Future separate modeling** |

**L04-03 implementation decision:** represent the dated link as a **separate `BookAssignmentCandidate`** with typed `BookAssignmentId`, book-level `ConfigurationScope`, purpose code, business interval and source pointer. For preview **only**, a candidate must resolve to a matching scoped `AccountingBookDraft` (tenant, Company, LegalEntity, BookId identical). This **does not resolve** the eventual `AccountingBook` ownership schema or prohibit an approved future N:M model. No irreversible schema constraint is introduced.

The L04-01 `AccountingBookDraft` still carries an entity-specific intent scope; it has not been remodeled as an approved shareable `AccountingBook`. Neither a group ownership relationship nor an authoritative legal membership is inferred.

## 3. Implemented contract and layering

```text
ListBookAssignmentCandidates(entity_scope)
PreviewAssignedBookDrafts(entity_scope, purpose, as_of)
         |
         v
  BookAssignmentPreviewService
    ├── TrustedPrincipal (TEST VALUE, not signed proof)
    ├── BookDraftAuthorization.require(... preview ...)
    ├── CompanyEntityMembership.require(...) [FAKE in R&D]
    ├── BookAssignmentCandidateReader [read-only Protocol]
    │    └── MemoryBookAssignmentCandidates [immutable local fixture]
    └── BookDraftUnitOfWork [L04-02 Protocol]
         └── BookDraftRepository.list_for_entity
                  |
                  v
         preview_applicable_book_drafts (pure policy)
           - explicit tenant/company/entity
           - explicit purpose, as_of date
           - reject unknown book IDs and leaked scopes
           - require candidate/book interval coverage
           - fail closed on duplicate ID / simultaneous assignment
           - stable sort by code + typed book ID
```

**Crucial naming:** `PreviewAssignedBookDrafts` is **NOT** `C10 GetApplicableBooks` and **NOT** the authoritative `ListEligibleBooks` API. It returns proposed draft books, without `known_at`, `published_at`, signed configuration version, snapshots, legal right to post, accounting period checks or normative eligibility. No posting consumer may use this result.

## 4. Domain invariants and review evidence

| ID | Rule | Negative proof |
|---|---|---|
| BOOK-ADR01-01 | Distinct `BookAssignmentId` vs `AccountingBookId` | typed identity test |
| BOOK-ADR01-02 | Scope, usage, business dates and provenance explicit | invalid types / datetime |
| BOOK-ADR01-03 | R&D preview assignment cannot cross Company/LegalEntity/Tenant/Book | foreign scope |
| BOOK-ADR01-04 | Assignment's entire interval falls inside draft book's validity | invalid interval |
| BOOK-ADR01-05 | Repeated assignment identity or overlapping same book/purpose invalid | duplicate / ambiguity |
| BOOK-ADR01-06 | Missing assignment, mismatched usage or date is **failure**, no default book | missing tests |
| BOOK-ADR01-07 | Unknown referenced book cannot silently disappear | orphan reference |
| BOOK-ADR01-08 | Multiple distinct books explicitly assigned are deterministically ordered | multi-book test |
| BOOK-ADR01-09 | Read-only test authorization + membership fail closed | wrong actor/tenant/revocation |
| BOOK-ADR01-10 | No mutation, active book, posting, SQL, authoritative C10 or live IAM | architecture smoke test |

## 5. Unresolved items / blocker register

1. **Physical ownership**: stable BookId and legal-entity assignment cardinality to decide with Accounting + Legal. No permanent `legal_entity_id NOT NULL` restriction adopted.
2. **Book kind / purpose**: `BookAssignmentPurpose` is a shape-validated code, NOT an official/statutory/group enum or a rights policy. Conditional primary uniqueness is undecided.
3. **Publication and replay**: `known_at`, `ConfigurationVersionId`, signed digest, historical corrections, provenance, approval, outbox, snapshot, C10 compatibility still unavailable.
4. **Security**: a `TrustedPrincipal` Python object and `MemoryCompanyEntityMembership.allow` are forgeable/local test doubles. Real independent signed-command/IAM validation and non-bypassable SQL check at COMMIT are unresolved issue #71.
5. **No backdoor by preview**: even if candidate preview selects a book, neither Execution nor Ledger may treat it as posting permission.
6. **Concurrency/retention**: fixture has no durable store, no cross-process SQL uniqueness/exclusion, no audit nor legally qualified retention.

## 6. Acceptance and next step

- [x] Typed candidate assignment and purpose reference; identity distinct from book.
- [x] Pure date/purpose preview with explicit missing, ambiguity and foreign-reference failures.
- [x] Read-only application protocol and immutable memory fixture.
- [x] Negative and isolation tests.
- [ ] Exact-head Python/Ruff, PG16 Foundation regression, migration recovery, wheel/sdist evidence.
- [ ] Independent BOOK-ADR-01 decision with accountable reviewer (**not recorded**).
- [ ] After #71 / G3, separately design authoritative `AssignBookToLegalEntity` with verified authorization at SQL COMMIT, approval, immutable evidence, temporal persistence and `known_at`.
- [ ] Only then derive C10-Q08 `GetApplicableBooks` on **published** versions and Bitemporal Resolution.

**Decision type:** provisional architectural policy for pure R&D, not `G4_GO` or `G3_GO`.
