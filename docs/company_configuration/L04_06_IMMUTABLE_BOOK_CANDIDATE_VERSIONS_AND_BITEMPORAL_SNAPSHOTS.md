# L04-06 — Immutable Book Configuration Candidate Versions & Bitemporal Snapshots

**Date:** 2026-10-30  
**Repository:** `tawounfouet/pyaccountingkit`  
**Status:** `PROPOSED_RND_CANDIDATE_ONLY` — not a publication, approved C10, normative attestation or posting authorization.  
**Parent:** [L04-05 draft PR #78](https://github.com/tawounfouet/pyaccountingkit/pull/78), exact base `170546c507226775942bc2c9783998ffee68c9d4`.  
**Gates:** G0/G1/G2 `PENDING_REVIEW`, G3 `HOLD_SECURITY`, [#71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN, no main merge.

## 1. Product motivation, source traceability and exclusions

The **proposed** specifications `18_COMPANY_CONFIGURATION_VERSIONING_TEMPORALITY_AND_SNAPSHOTS.md` and `17_COMPANY_CONFIGURATION_CONFIGURATION_LIFECYCLE_AND_GOVERNANCE.md` distinguish immutable published versions from mutable drafts; two time axes; deterministic scopes; canonical content digest; independently validated approvals; atomic publication and outbox; reproducible historical queries. The `12_COMPANY_CONFIGURATION_ACCOUNTING_BOOKS_AND_REFERENCE_FRAMEWORKS.md` proposal distinguishes Books, BookAssignments and ReferenceFrameworkBindings from the accounting ledger, and Normative Layer as the owner of reference standards.

L04-01 through L04-05 already produced **unpublished** models, a read-only assignment/framework candidate preview, and bitemporal **unverified normative source claims**. L04-06 introduces a versioned candidate *bundle* so **the Book/Assignment/Binding triple itself can be resolved as originally known or restated**. It does not claim these candidates have passed governance or become an authoritative published configuration.

**Zero:** SQL migrations; direct privileged L03 issuers; IAM tokens/real signed authorization; publication transactions; approval/SoD; outbox events; real Normative Layer; chart/calendars/policies/dimensions; C10 runtime, posting, Ledger writes or certified IFRS/PCG/OHADA compliance.

## 2. DDD language and hexagonal layering

```text
BookConfigurationCandidateVersion (frozen, identity = BookCandidateVersionId)
  ├── AccountingBookDraft               (frozen book content and revision)
  ├── BookAssignmentCandidate           (book/tenant/company/entity/purpose)
  ├── ReferenceFrameworkBindingCandidate (versioned normative pointer)
  ├── BookAssignmentPurpose             (explicit use, not normative book type)
  ├── EffectiveInterval                 [business_from, business_to)
  ├── KnowledgeInterval                 [known_from, known_to) aware instants
  ├── source_ref                         (non-authoritative provenance pointer)
  └── content_digest                     (canonical JSON SHA-256)

select_book_candidate_version(scope, purpose, as_of, known_at, versions)
  -> exactly one version, or typed MISSING / AMBIGUOUS / INVALID
  -> verify every candidate's digest; reject foreign scope / reused version ID

BookCandidateSnapshotPreviewService
  ├── PreviewBookConfigurationSnapshot (scope/purpose/source/as_of/known_at)
  ├── BookDraftAuthorization.require      (fake-only grant in this R&D)
  ├── CompanyEntityMembership.require    (fake-only membership in this R&D)
  ├── BookCandidateVersionReader Protocol
  │    └── MemoryBookCandidateVersions (immutable fixture)
  └── NormativeReferenceClaimsReader Protocol (L04-05)
       └── MemoryNormativeReferenceClaims (unverified fixture)
    -> preview_normative_reference_history (L04-05 pure policy)
    -> BookConfigurationCandidateSnapshot (frozen, deterministic digest)
```

**Patterns used:**
- **DDD / Aggregate proposal:** a candidate version seals one coherent Book+Assignment+FrameworkBinding set; it does not become a giant aggregate for all Company Configuration.
- **Value Objects & immutable snapshot:** `EffectiveInterval`, `KnowledgeInterval`, typed IDs, source and digest; frozen dataclasses do not alone provide independent tamper-proof storage.
- **Hexagonal Ports / DIP / SoC:** the application depends on protocols; in-memory fixture implements reads and contains no Postgres/IAM client.
- **CQRS (read-only half):** a typed query, never an activation, `Publish` command or posted ledger read.
- **Bitemporal selection + fail-closed:** both requested dates are mandatory, and ambiguous candidates are rejected rather than ordered by `latest`.
- **Explicit integrity envelope:** deterministic hashes of canonical JSON; not a cryptographic signature, source trust, approval, authorization, or audit ledger.

## 3. Canonicalization R&D contract

`CANONICALIZATION_VERSION = "l04-rnd-1"`, `SHA-256` of `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)` encoded in UTF-8. Canonical fields are spelled out in source; no Python `hash()`, locale, implicit clock, nonfinite floats, unversioned `latest` or mutable arbitrary dictionaries. Typed UUIDs use lowercase canonical representations, dates `YYYY-MM-DD`, and timezone-aware knowledge instants are **normalized to UTC with microsecond resolution and Z suffix**.

The **candidate version digest** includes:
- exact candidate version ID;
- full tenant/company/legal-entity/book scope;
- book label, code, currency, framework code + edition, book revision, dates and source reference;
- assignment ID, purpose, dates, source reference;
- framework binding ID, purpose, exact normative pointer, dates, source reference;
- candidate effective and knowledge intervals, purpose, provenance.

The **candidate snapshot digest** includes version ID, version digest, selected normative statement ID/source/reference/provenance and the `as_of` + `known_at` pair, with a literal `NON_AUTHORITATIVE_RND_CANDIDATE` status. It is reproducible for identical inputs.

`verify_integrity()` recomputes the digest of each envelope; if a caller replaces bytes/attributes without rebuilding the sealed value, it raises `CANDIDATE_SNAPSHOT_DIGEST_MISMATCH`. **This is not tamper-proof against an attacker who can rewrite data and hashes**; that requires externally anchored signatures/append-only evidence and trusted key/authority governance.

## 4. Temporal and scope rules

| ID | Contract | Expected refusal |
|---|---|---|
| L04-BV-01 | Typed `BookCandidateVersionId` distinct from BookId / approved ConfigurationVersionId | invalid ID |
| L04-BV-02 | Exact Book, Assignment and FrameworkBinding share scope/purpose, reference and validity | foreign scope, mismatched purpose/reference |
| L04-BV-03 | Version effective interval contained by each component's business validity | out-of-range period |
| L04-BV-04 | Knowledge interval consists of timezone-aware instants; no naive datetimes | invalid cutoff |
| L04-BV-05 | Unique version IDs even when historical windows do not overlap | duplicate ID |
| L04-BV-06 | Exactly one candidate for scope+purpose+business date+knowledge instant | missing or ambiguous |
| L04-BV-07 | Every supplied candidate belongs to the requested exact book scope | malicious reader leak |
| L04-BV-08 | No post-cutoff book/assignment/binding change changes an original known-at result | restatement regression |
| L04-BV-09 | Exact normative source/reference also known at cutoff and declared available | missing, unavailable or foreign claim |
| L04-BV-10 | Deterministic canonical digest, UTC normalization, digest mismatch detection | mismatch tests |
| L04-BV-11 | Both reads require explicit action grant + Company membership | default deny / tenant mismatch |
| L04-BV-12 | Result never carries published, approval, ledger or posting authorization | public API negative tests |

**Restatement example (synthetic, not a real PCG event):**

```text
Business date: 2026-02-15

Book candidate V1: "Original"  | Knowledge [2026-01-01, 2026-03-01)
Book candidate V2: "Revised"   | Knowledge [2026-03-01, +inf)

Norm claim N1: available      | Knowledge [2026-01-01, 2026-03-01)
Norm claim N2: available      | Knowledge [2026-03-01, +inf)

as_of=2026-02-15, known_at=2026-02-01 -> V1, N1, original digest
as_of=2026-02-15, known_at=2026-03-01 -> V2, N2, different digest
```

No status transition or mutation of a publication is performed; both records are test fixtures describing distinct historical claims.

## 5. What L04-06 deliberately does **not** satisfy

**TMP-05/06/13/17/18/19** remain unproven:
- no independent identity + governance approval, signoff, separation of duties, authenticated Normative Layer, legal jurisdiction validation;
- no published immutable `ConfigurationVersion`, publication transaction, outbox atomics, event versioning, actual registry or durable append-only history;
- no authoritative `ConfigurationSnapshot` or contract C10 Q01/Q02/Q08 to Runtime Resolution;
- no fiscal/calendar/period lock, chart account eligibility, policy compatibility, executable posting permissions or ledger;
- no persistence uniqueness or isolation guarantee across processes/restarts, no signed canonical content, content-addressed immutable object storage, retention policy or production recovery validation;
- no certainty that a `TrustedPrincipal` Python instance came from signed IAM; memory authorization/membership fakes are not real security evidence.

The L04-06 candidate model is intentionally not named `PublishedBookConfigurationVersion` or `ConfigurationSnapshot`, because it would falsely imply authorization.

## 6. Open ADR and next delivery

- **BOOK-ADR-01:** whether Book ownership is dedicated, shared, or template-linked across legal entities.
- **BOOK-ADR-03:** real Normative Layer registry, legal applicability and signed provenance by reference/version/jurisdiction.
- **L04-TMP-ADR:** authoritative bitemporal persistence, supersession, knowledge closing vs append-only archival; canonical schema version / digest rules; snapshot and published version IDs.
- **L04-GOV-ADR:** approval roles and SoD; audit/outbox atomicity; actor permissions verified at COMMIT; #71 closure.
- **L04-C10-ADR:** consumer compatibility/read-receipts for published book and applicable frameworks; period/chart/policy dependencies.

### Qualification

- [x] Nonpublished candidate versions with explicit full component capture and two time axes.
- [x] SHA-256 canonical manifest, deterministic snapshot envelope, verification API.
- [x] Read-only query Protocol and immutable memory fixture with scope denial.
- [x] Negative tests for original vs restated, ambiguity, tampering, temporal bounds and access.
- [ ] Exact-head Python CI (3.11/3.12) + Ruff; PG16, migration recovery, wheel/sdist Foundation parity.
- [ ] Independent architecture/accounting/security approval of ADRs before publication, SQL changes or C10 implementation.

**Engineering label:** `L04_06_CANDIDATE_BITEMPORAL_SNAPSHOT_RND` until CI verification. Not `G3_GO`, `G4_GO`, `PRODUCTION_READY` or a stable package version.
