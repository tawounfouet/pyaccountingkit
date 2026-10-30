# L04-05 — Normative Source Registry Contracts & Bitemporal Claims Preview

**Date:** 2026-10-30  
**Status:** `PROPOSED_RND_NON_AUTHORITATIVE` — not a certified registry, not published accounting configuration.  
**Stack:** [L04-04 PR #77](https://github.com/tawounfouet/pyaccountingkit/pull/77) at exact parent `ef0a6fb0c2c426fba15caa33bb00603a0bfec632`.  
**Gates:** G0/G1/G2 `PENDING_REVIEW`; L03 G3 `HOLD_SECURITY`; [issue #71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN.

## 1. Problem / spec traceability

Source specifications `12_COMPANY_CONFIGURATION_ACCOUNTING_BOOKS_AND_REFERENCE_FRAMEWORKS.md` and `18_COMPANY_CONFIGURATION_VERSIONING_TEMPORALITY_AND_SNAPSHOTS.md` distinguish:

- **Normative Layer** owns normative content and versions; **Company Configuration** may only hold references/bindings.
- **Business effective time (`as_of`)** is distinct from **knowledge/recorded time (`known_at`)**.
- An unavailable, ambiguous or incompatible reference is a **fail-closed** result.
- Historical replay must not silently use the latest version/knowledge.
- Full authoritative C10 selection ultimately requires an **approved published configuration, immutable snapshot, digest, scope and historical provenance**, not merely a reference found in a catalog.

The L04-04 `NormativeFrameworkAvailability.require_available(ref, as_of)` port was intentionally current-date only and backed only by a default-deny test fake. L04-05 builds a **separate, nonauthoritative historical-claim query**; it does **not** retroactively promote that fake into a normative service.

## 2. Bounded DDD model

```text
NormativeReferenceStatement (immutable test-source declaration)
  ├── NormativeStatementId (typed UUID; NOT a reference version ID)
  ├── NormativeSourceCode (explicit, shape-validated source)
  ├── ReferenceFrameworkRef (framework code + explicit version)
  ├── EffectiveInterval [business_date_start, business_date_end)
  ├── KnowledgeInterval [observed_at, superseded_at)
  ├── NormativeDeclaration (DECLARED_AVAILABLE / DECLARED_UNAVAILABLE)
  └── source_ref (pointer, NOT independently validated evidence)

preview_normative_reference_history(
     framework, source, as_of, known_at, statements
)
  ├── validate source/ref, dates, typed immutable statement tuple
  ├── reject foreign, duplicate and concurrent claims
  ├── select exactly one claim active on BOTH time axes
  ├── reject missing or declared-unavailable
  └── NormativeReferenceHistoricalPreview
       └── unverified source claim, NOT normative/legal certification
```

`KnowledgeInterval` uses the existing Foundation value object, with timezone-aware instants and comparisons on a UTC timeline. `EffectiveInterval` uses business `date` values, end exclusive. No implicit `now`, "latest" or provider fallback is allowed.

**Important:** this is an example of a historical *declaration*, not a verifiable official normative edition. No cryptographic signature validation, source content retrieval, external accreditation, normative rule validation, legal applicability or accounting policy certification is performed.

## 3. Application / Hexagonal design

```text
PreviewNormativeHistoryForBookDraft(
   book_scope, assignment_purpose, source, as_of, known_at
)
  -> BookNormativeHistoryPreviewService
     -> authorization.require(action="book.normative_history.preview")
     -> CompanyEntityMembership.require(book_scope)
     -> BookDraftUnitOfWork + BookDraftRepository (L04-02)
     -> BookAssignmentCandidateReader + pure selection (L04-03)
     -> BookFrameworkCandidateReader + pure selection (L04-04)
     -> NormativeReferenceClaimsReader (new Protocol)
        -> MemoryNormativeReferenceClaims (immutable test fixture)
     -> preview_normative_reference_history (new pure domain)
  -> BookNormativeHistoryPreview:
        - book_binding (current DRAFT candidate)
        - normative_claim (bitemporal source statement)
```

**Critical temporal boundary:** only `normative_claim` is bitemporal. Books, BookAssignments and FrameworkBindings are **current, unapproved draft candidates** and are **not** bitemporally versioned yet. Consequently, the composed query is **NOT full `GetApplicableBooks`, C10, historical configuration replay, or accounting eligibility**. A later L04 proposal must pin historical book/binding/assignment versions and configuration snapshots before claiming full replay.

The `TrustedPrincipal`, `MemoryBookAuthorization` and `MemoryCompanyEntityMembership` in the R&D path are **forgeable test doubles**, not external IAM or legal-relationship evidence. The service performs explicit action scope/tenant checks, but this does not close issue #71.

## 4. Selection invariants and executable refusal contracts

| ID | Contract | Evidence |
|---|---|---|
| L04-NH-01 | Typed normative source, statement ID, framework edition and provenance pointer | invalid type/value tests |
| L04-NH-02 | Business date distinct from offset-aware knowledge instant | datetime/naive rejection |
| L04-NH-03 | No knowledge after `known_at` may influence original preview | earlier-known/new correction tests |
| L04-NH-04 | No hidden fallback to latest edition/provider or source | foreign/source/version refusals |
| L04-NH-05 | Duplicate IDs or concurrent active declarations fail closed | ambiguous tests |
| L04-NH-06 | Half-open effective and knowledge boundaries; timezone semantics explicit | interval boundary / offset test |
| L04-NH-07 | Missing declaration or explicit negative declaration both fail | `MISSING`, `UNAVAILABLE` |
| L04-NH-08 | Book scope, purpose/date assignment and framework binding required | compositional tests |
| L04-NH-09 | Missing/revoked grant or membership; cross-tenant actor denied | adversarial tests |
| L04-NH-10 | No database writers, official registry adapters, C10 production, Ledger posting | code-level assertions |

### Example

A test source declares `FR-PCG@2026` unavailable for a business date in February, as known on 1 February. A later statement recorded 1 March describes that same business date as available. An R&D preview `as_of=2026-02-15, known_at=2026-02-01` **must not see** the correction and fails as declared-unavailable; `known_at=2026-03-01` can see the new statement. This does **not** claim a real PCG 2026 publication/correction occurred.

## 5. Open ADRs and authority / security blockers

- **BOOK-ADR-01:** legal-entity book ownership / N:M assignments remains proposed.
- **BOOK-ADR-03:** official Normative Layer provider(s), authenticated source identity, version codes, jurisdictions/variants, immutable content hashes and provider retention/SLA are unapproved.
- **L04-TMP-ADR:** immutable *published* versions of book/assignment/binding with both effective and knowledge intervals, restatements, deterministic replay receipts and C10 read boundary remain to design.
- **Trust:** source statements are untrusted caller-supplied Python objects; need verified source digests / signatures, policy and audit under approved provider contract.
- **Security:** G0/G1/G2 unsigned, L03 G3 `HOLD_SECURITY`, #71 open. No SQL DDL, IAM-to-command cryptographic pairing, audited authorization at COMMIT or outbox is added.
- **Regulatory:** naming `FR-PCG`, `IFRS`, `OHADA-SYSCOHADA` does not establish authority, legal applicability or adoption. IFRS are not a mandatory universal chart of accounts.

## 6. Acceptance and follow-up

- [x] New typed `NormativeStatementId` and immutable two-axis source statements.
- [x] Pure as-of/known-at selection with missing/ambiguous/unavailable refusal.
- [x] Read-only scoped service and immutable local fixture; no SQL migration.
- [x] Adversarial tests for race of knowledge versions, type, scope, absent source.
- [ ] Exact-head Python 3.11/3.12, Ruff, PostgreSQL and recovery regressions, wheel/sdist parity.
- [ ] Independent BOOK-ADR-03 and L04-TMP-ADR source authority decisions.
- [ ] After #71 / G3 and signed governance: authoritative verified registry adapter, immutable versioned book binding + C10 publication/query, outbox, evidence and historical reconstitution.

**Exit decision:** `L04_05_NORMATIVE_HISTORY_RND_CANDIDATE` until exact-head CI. A green prototype may not be merged/promoted as a production accounting capability.
