# L04-04 — Reference Framework Bindings & Deterministic Draft Preview

**Date:** 2026-10-30  
**Status:** `L04_04_RND_PREVIEW_CANDIDATE` — no approved ADR, publication, normative certification or production capability.  
**Parent:** [L04-03 PR #76](https://github.com/tawounfouet/pyaccountingkit/pull/76) @ `63097571afbebd1206d0c0f78a74864320e61186`.  
**Existing gates:** G0/G1/G2 `PENDING_REVIEW`, G3 `HOLD_SECURITY`, [#71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN. No SQL migration, #71 bypass path, privileged issuer or runtime posting.

## 1. Business motivation and sources

The `12_COMPANY_CONFIGURATION_ACCOUNTING_BOOKS_AND_REFERENCE_FRAMEWORKS.md` target specification proposes a separate `ReferenceFrameworkBinding` keyed to an `AccountingBook`, with a versioned `ReferenceFrameworkRef`, an explicit effective interval and ultimately a configuration-version identity. Its §5.2 and §7 require **one applicable framework per scope/instant, unless a policy explicitly authorizes otherwise**, plus Normative Layer compatibility checks before a released book. §10 requires valid time and knowledge time as distinct axes.

The `07_COMPANY_CONFIGURATION_DOMAIN_INVARIANTS_AND_BUSINESS_RULES.md` proposed `INV-BOOK-01`, `CFG-02`, `CFG-06` and `CFG-07` demand normative availability, no ambiguous selection and reproducible published configuration. `10_COMPANY_CONFIGURATION_INTEGRATION_CONTRACTS.md` and `18_COMPANY_CONFIGURATION_VERSIONING_TEMPORALITY_AND_SNAPSHOTS.md` reserve authoritative C10 reads, publication identity, provenance and `known_at` for later work. These are **target requirements**, not presently qualified production contracts.

The candidate implementation below is intentionally narrower. It does not make an `IFRS` plan of accounts, assert a French PCG/SYSCOHADA legal status, decide entity jurisdiction or determine permissible accounting policies. PCG/IFRS/SYSCOHADA codes in tests are only explicit **reference placeholders**. IFRS is not a universal mandatory chart of accounts.

## 2. DDD and hexagonal design

```text
ReferenceFrameworkBindingCandidate
  ├── FrameworkBindingId          stable identity, distinct from BookId
  ├── ConfigurationScope          exact tenant/company/entity/book intent
  ├── BookAssignmentPurpose       explicit use, provisional code
  ├── ReferenceFrameworkRef       normative code + explicit edition/version
  ├── EffectiveInterval           date [start, end)
  └── source_ref                  provenance pointer; NOT signed evidence

PreviewBookFrameworkBinding(scope, purpose, as_of)
  -> BookFrameworkPreviewService
     -> BookDraftAuthorization       action book.framework.preview
     -> CompanyEntityMembership     scoped fake until authoritative contract
     -> BookDraftUnitOfWork          read-only
        -> BookDraftRepository       existing L04-02
        -> BookAssignmentCandidateReader (L04-03 read-only)
           -> preview_applicable_book_drafts() (must explicitly assign target)
        -> BookFrameworkCandidateReader (new Protocol)
           -> preview_reference_framework_binding() (pure domain)
        -> NormativeFrameworkAvailability.require_available(ref, as_of)
           [MANDATORY Protocol; local explicit deny-first fixture]
     -> BookFrameworkPreview        NON-AUTHORITATIVE R&D result
```

`BookFrameworkPreview` names and types its own provenance fields (`binding_id`, `book_scope`, `purpose`, `as_of`, `framework`), but **is neither a signed snapshot, nor an approved business configuration, nor a permission to post**.

### Implementation files

- `domain/shared/identifiers.py`: new `FrameworkBindingId` type.
- `domain/accounting_books/framework_bindings.py`: immutable candidate; `InvalidFrameworkBinding`, `FrameworkBindingMissing`, `FrameworkBindingAmbiguous`, `FrameworkUnavailable`; pure selection.
- `application/accounting_book_frameworks.py`: typed query, read-only port, required external normative availability port and scoped composition.
- `infrastructure/accounting_book_frameworks_memory.py`: immutable test catalog + allowlisted availability periods. This is **NOT** a Normative provider.
- `tests/unit/company_configuration/test_l04_04_framework_binding_preview.py`: positive, negative and adversarial cases.
- `domain/accounting_books/__init__.py`: public R&D domain exports.

## 3. Fail-closed invariants

| ID | Rule | Refusal scenario |
|---|---|---|
| L04-RFB-01 | Typed `FrameworkBindingId` distinct from BookId | wrong identity class |
| L04-RFB-02 | Book-level scope, purpose, versioned reference, interval and source required | missing/bare/untrimmed fields |
| L04-RFB-03 | Candidate cannot claim another tenant/company/entity/book | foreign catalog, malicious adapter |
| L04-RFB-04 | Binding's interval must fit within the draft book's interval | earlier, later or unbounded end |
| L04-RFB-05 | Same book/purpose/date must select at most one binding | overlapping active bindings |
| L04-RFB-06 | Binding identity must not be duplicated in supplied catalog | same ID on disjoint intervals |
| L04-RFB-07 | Date must be `date`, not `datetime`; intervals half-open | boundary tests |
| L04-RFB-08 | No purpose fallback / default version / available book inference | missing purpose or binding |
| L04-RFB-09 | Book must be explicitly assigned for same purpose and `as_of` | missing/mismatched assignment |
| L04-RFB-10 | External availability contract required; test fake defaults to deny | unknown, wrong-version, expired ref |
| L04-RFB-11 | Actor + company membership explicitly checked before reads | wrong tenant, action revoked, no membership |
| L04-RFB-12 | No writes, SQL migrations, publication, Ledger, or C10 asserted | architecture negative tests |

**Important limitation of L04-01:** `AccountingBookDraft` currently carries exactly one `ReferenceFrameworkRef` field. L04-04 therefore **requires a binding to equal that reference**. A future book-version/knowledge-time model must supersede this temporary constraint to support real in-place reference transitions across years, without changing published history. This is not a statement that framework versions can never change.

## 4. Boundary cases and exact semantics

- Two bindings with the same purpose and overlapping applicability on the queried date => `FRAMEWORK_BINDING_AMBIGUOUS`.
- Two bindings with the same purpose but adjacent half-open intervals => select exact boundary.
- A same-book binding for a different purpose is not a fallback.
- A missing BookAssignment, including an assignment for another purpose => reject.
- A binding referencing a different version than the `AccountingBookDraft.framework` => reject (until versioned book change model).
- A Normative availability fake not explicitly allowlisting the **exact reference and date** => `FRAMEWORK_UNAVAILABLE`.
- An unknown book, foreign scope, catalog leak, duplicate binding ID or orphan reference => explicit failure, never silent drop.
- Multiple explicitly assigned books per entity remain compatible with L04-03, but this query addresses **one book at a time**, not the entire group reporting basis.
- Dates are business dates. `known_at` is **not** implemented and no historical replay or current authorization is implied.

## 5. Unresolved ADRs / release blockers

1. `BOOK-ADR-01`: mono-entity vs shareable book remains unapproved. Draft preview prohibits cross-entity reference reuse by default.
2. `BOOK-ADR-03`: normative code authority/provider, revision identities, jurisdictions, regimes, effective applicability, digest, policy compatibility and availability SLA remain to be designed and independently reviewed.
3. Framework transitions / effective+knowledge time: replace the L04-01 single-ref draft constraint with separately approved immutable book versions and framework histories; keep published snapshots unchanged.
4. `BOOK-ADR-02`: purposes/types and primary/group/adjustment policy still undecided; `BookAssignmentPurpose` is not a normative enum.
5. Normative provider adapter: the local test fake is **not** a reference authority, even when explicit test allowlists are green.
6. No SQL enforcement, signed IAM-to-command proof at COMMIT, publication/audit/outbox, legal ownership attestation or production C10.
7. `G3_HOLD_SECURITY` under #71 and unsigned G0/G1/G2 remains binding; never infer authorization from R&D CI.

## 6. Qualification and roadmap exit

- [x] Domain binding candidate + typed identities, pure deterministic effective-date selection.
- [x] Read-only authorization/assignment/normative availability composition.
- [x] Explicit typed test memory fixtures; no SQL migrations.
- [x] Negative tests for ambiguity, scope, missing bindings, normative default-deny.
- [ ] Python 3.11/3.12 + Ruff exact-head GitHub Actions.
- [ ] PostgreSQL 16 and FND-C04 recovery regressions.
- [ ] Wheel/sdist SQL lineage unchanged.
- [ ] Independent BOOK-ADR-01/03 business and normative review; G3/#71 closure before authorizing any publisher/SQL writer.

**Decision:** `L04_04_RND_PREVIEW_CANDIDATE`, not `G4_GO`, `GO_PRODUCTION`, `IFRS_COMPLIANT`, `PCG_CERTIFIED` or `SYSCOHADA_CERTIFIED`. Next safe work item: source-of-authority design for framework registry and `known_at`-aware draft replay, still without privileged SQL mutations.
