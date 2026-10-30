# L04-01 — Accounting Books Domain Kernel (isolated R&D)

**Date:** 2026-10-30  
**Repository:** `tawounfouet/pyaccountingkit`  
**Scope:** domain-only, standalone from *current main* `acdee98ca2736d79e17174f510ac767defd90db8`  
**Milestone:** L04-01 — an immutable **AccountingBookDraft** proposal + pure conflict policy + unit tests  
**Decision:** `RND_DOMAIN_PROTOTYPE` — **not L04 approved, not a released Accounting Book, no compliant posting, no SQL migration**.

## 1. Inherited context and hard gates

- L03's consolidated review candidate is [draft PR #73](https://github.com/tawounfouet/pyaccountingkit/pull/73), **NOT merged**; G0/G1/G2 are `PENDING_REVIEW`.
- [G3 #36](https://github.com/tawounfouet/pyaccountingkit/issues/36) and security [#71](https://github.com/tawounfouet/pyaccountingkit/issues/71) remain OPEN, **HOLD_SECURITY**. Seven L03 SQL organization writes do **not** prove a non-bypassable signed command ↔ independent IAM decision / current epoch at COMMIT.
- The S1 [draft PR #72](https://github.com/tawounfouet/pyaccountingkit/pull/72) adds a **separate** blocked-write migration `0030`; it is not on `main` or this L04 branch.
- No new G3 micro-issue, SQL `0030` collision, or migration is introduced by L04-01. This prototype must not invoke L03 SQL issuers or depend upon the pending L03 application services.
- There is no approved L04 requirement/specification file in the inspected repository. This document is a **bounded design proposal**, not a reconstruction of a previously approved L04 model.

## 2. Product objective

Represent the **intent to configure an accounting book** with its own stable identity, organization perimeter, currency, versioned accounting framework reference and period of applicability, without asserting that the organization is authorized to own it or that any standard has been complied with.

An `AccountingBookDraft` is not a General Ledger: no entries, balances, postings, currency conversions, closing, publishing or accounting-period events exist in L04-01. It cannot transition to ACTIVE.

### What is normative, and what is merely referenced?

- **French PCG:** ANC publishes dated versions, including a 2026 consolidated PCG and a dated plan of accounts. This R&D prototype *does not* ingest or certify their content.
- **OHADA:** AUDCIF 2017 and revised SYSCOHADA include a general chart of accounts and a consolidated/combined framework. This prototype does not determine legal applicability to a tenant.
- **IFRS:** standards address recognition, measurement, presentation and disclosures; `ReferenceFrameworkRef("IFRS", "2026")` is **not** a universally defined IFRS chart of accounts, an accounting-policy engine, or a claim of IFRS compliance.
- The examples `FR-PCG`, `IFRS`, `OHADA-SYSCOHADA` are **local placeholder reference codes**; **not approved canonical registry codes**.

Official references checked on 2026-10-30:

- ANC, 2026 PCG: https://www.anc.gouv.fr/plan-comptable-general-0
- ANC, dated collections and consolidated versions: https://www.anc.gouv.fr/normes-comptables-francaises/recueils-des-normes-comptables
- OHADA, AUDCIF and revised SYSCOHADA: https://www.ohada.org/acte-uniforme-relatif-au-droit-comptable-et-a-linformation-financiere-audcif/
- IFRS Foundation, standards: https://www.ifrs.org/issued-standards/
- IFRS Foundation, IAS 1 overview: https://www.ifrs.org/issued-standards/list-of-standards/ias-1-presentation-of-financial-statements/

## 3. DDD language and objects

```text
Tenant
 └── CompanyId                     explicit perimeter, NOT ownership proof
      └── LegalEntityId            explicit entity, NOT membership proof
           └── AccountingBookDraft
                ├── AccountingBookId             identity (not code)
                ├── BookCode                     local name / value object
                ├── CurrencyCode                 3-letter shape only
                ├── ReferenceFrameworkRef        code + explicit version
                ├── EffectiveInterval            [start, end) business dates
                ├── source_ref                    provenance pointer, not evidence
                └── revision                      optimistic candidate version
```

### Domain design conventions

- **DDD Aggregate / Entity identity:** immutable `AccountingBookDraft`; equality/hash by `(tenant_id, AccountingBookId)`, distinct from code and revision. L04-01 does not claim that the draft has been persisted.
- **Value Objects:** `BookCode` and inherited `AccountingBookId`, `CurrencyCode`, `ReferenceFrameworkRef`, `EffectiveInterval`. The provisional `BookCode` convention is uppercase ASCII, first character a letter, max 32 characters. This needs an ADR before a public API or import pipeline.
- **SoC and DIP:** imports only the domain shared layer; no SQL/HTTP/IAM/gateway/ORM dependency.
- **Immutability / candidate changes:** `rename` and `reframe` enforce explicit `expected_revision`, nonblank reason and changed payload. They return another candidate; they **do not** persist a signed audit or grant use.
- **Pure policy:** `require_unique_book_code(candidate, existing_tuple)` rejects overlapping effective periods with the same code **within the identical tenant/company/entity scope**. It ignores the same stable BookId's old revision. Actual DB uniqueness and concurrency are **not** protected until a future persistence lot.
- **No implicit defaults:** tenant/company/entity/book IDs, currency, framework/version, source provenance and effective dates are required. There is no implicit current date, company or norm.
- **Fail closed:** invalid types, missing identities, revision mismatch, untrimmed labels and overlapping names in one perimeter raise domain exceptions.

### Deliberate non-invariants

- A declared `ConfigurationScope` **does not prove** that a Company legally owns or belongs to a Legal Entity, or that the actor may create a book.
- Two books may coexist for one entity under different codes. Primary/secondary books and multi-book mappings are **not yet decided**.
- A reference to PCG, IFRS or OHADA is **not** legal, accounting, regulatory or taxation validation.
- The pure duplicate-code check is **not** a guarantee under concurrent requests.
- The reason argument is validated but **not durably recorded**; audit/outbox/workflows are not present.
- Renaming and re-framing do not indicate material changes to existing posted data, because none exists at this stage.

## 4. Invariants (L04-INV)

| ID | Invariant | Evidence |
|---|---|---|
| L04-INV-01 | Stable typed BookId, explicit tenant/company/entity/book scope matching the ID | unit tests |
| L04-INV-02 | `BookCode` canonical local syntax and nonblank label | unit tests |
| L04-INV-03 | explicit currency and versioned framework reference; no legal assertion | unit tests |
| L04-INV-04 | half-open `EffectiveInterval`, no implicit `now` | inherited shared tests + new overlaps tests |
| L04-INV-05 | candidate amendments require exact positive revision and reason | unit tests |
| L04-INV-06 | overlapping codes rejected in same company/entity/tenant perimeter | unit tests |
| L04-INV-07 | book draft never activates or posts entries | API surface / unit test |
| L04-INV-08 | no inbound infrastructure or security bypass dependency | architecture tests |

## 5. ADRs and unresolved product decisions

| ADR | Question | Default for L04-01 |
|---|---|---|
| L04-ADR-01 | One `AccountingBook` belongs to a Company, Legal Entity or group? How are sharing and dedicated books modeled? | **Do not infer**; explicit pair in claimed scope only |
| L04-ADR-02 | What distinguishes statutory, management, adjustment or consolidation books? | **Undecided**; do not add a guessed enum |
| L04-ADR-03 | Which reference authorities, versions, legal jurisdictions and applicability tests govern PCG/IFRS/OHADA? | typed pointer, external registry future |
| L04-ADR-04 | Can the book's currency, legal scope or accounting framework be amended after activation? | No activation in this milestone |
| L04-ADR-05 | Global/local code uniqueness, validity overlap, cross-period mapping? | local pure candidate policy only |
| L04-ADR-06 | How do chart of accounts, fiscal calendars, policies and assignment map to books? | L05–L07 or separate approved scope |
| L04-ADR-07 | How do we establish actor authentication and authoritative company membership? | require G3 #71 correction before persistence |
| L04-ADR-08 | What is the canonically signed configuration snapshot and read-model interface for L09/L10? | deferred |

## 6. Qualification and acceptance

**L04-01 eligible acceptance** requires:
1. Unit tests on Python 3.11 / 3.12 and Ruff green.
2. Existing Foundation CI remains green.
3. No new SQL migration, DDL, REST route, IAM credential, activation, posting or stable release claim.
4. Explicit reviewer acceptance of the draft-only R&D boundary and of ADRs left open.
5. All G0/G1/G2/G3 states left unchanged.

**Not eligible:** `G3_GO`, `L04_PRODUCTION_READY`, `IFRS_COMPLIANT`, `OHADA_COMPLIANT`, `PCG_CERTIFIED`, ledger posting, a public package release.

## 7. Implementation plan

- [x] L04-01 Domain Model + pure collision check and tests (source candidate).
- [ ] Verify CI exact head; record SHA and test counts.
- [ ] Independent review and non-binding ADR decisions.
- [ ] L04-02 explicit use-case/port design, read-only at first.
- [ ] L04-03 persistence and authorization **only after** #71 / G3 safeguards and controlled integration.
- [ ] L05 Chart of Accounts, L06 calendars, L07 accounting policies by separately validated requirements.

**Outcome sought:** begin producing accounting domain value without treating a security HOLD as permission to write to PostgreSQL.
