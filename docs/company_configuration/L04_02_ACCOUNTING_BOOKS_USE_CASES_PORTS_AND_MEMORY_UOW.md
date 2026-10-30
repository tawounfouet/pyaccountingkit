# L04-02 — Accounting Books Use Cases, Ports & Memory UoW

**Date:** 2026-10-30  
**Stack:** draft PR #74 (`ef3496d5cf906e0b05a0fe2b05de4824437575b7`) → L04-02 draft candidate  
**Scope:** isolated `RND_IN_MEMORY_ONLY`, no SQL migration, no release, no publication/activation, no ledger posting  
**Gates unchanged:** G0/G1/G2 `PENDING_REVIEW`; G3 `HOLD_SECURITY`; #71 OPEN.

## 1. Rationale and boundaries

L04-01 establishes an immutable `AccountingBookDraft` and a pure effective-period/code conflict policy. L04-02 surrounds it with **application use cases and hexagonal ports** plus a deterministic **process-local fake**. Unlike a release-grade accounting-book service this prototype has no persisted command evidence, no trusted IAM session, no statutory framework eligibility assessment and no authorized Company ↔ LegalEntity graph. **There is no service or SQL invocation of L03's seven controlled organization writes**. The L03 #71 security bypass is neither solved nor relaxed.

This is **not** a persistence layer. The term `Repository` names the application-side storage **port**, and `MemoryBookRepository` is merely a test adapter. `UnitOfWork` stages local proposals under a single process mutex: no cross-process isolation, no durable transaction, no external events.

## 2. Hexagonal / DDD architecture

```text
TrustedPrincipal (external authenticator REQUIRED, test fake ONLY)
          │
          v
   BookDraftService
       ├── Typed commands:
       │    ProposeBookDraft / RenameBookDraft / ReframeBookDraft
       ├── Typed queries: GetBookDraft / ListBookDrafts
       ├── BookDraftAuthorization.require(principal, action, scope)
       ├── CompanyEntityMembership.require(scope)
       │                      (external source of authority REQUIRED)
       └── BookDraftUnitOfWork (port)
                └── BookDraftRepository (port)
                    ├── get / list_for_entity
                    └── save(expected_revision)
                               │
                     local test adaptation
                               v
                  MemoryBookUnitOfWork (RLock)
                     MemoryBookRepository
                       MemoryBookStore
                       - in-process state only
                       - copy-on-enter / commit
                       - revision check
                       - local code-overlap check
                       - no SQL, no audit/outbox

DOMAIN: AccountingBookDraft + BookCode + ReferenceFrameworkRef
```

Dependency rule (DIP): `domain` is pure; `application` depends only on domain and Protocol ports; `infrastructure/accounting_books_memory.py` implements ports. Not the reverse.

## 3. Commands and queries

| Name | Scope | Behavior | Durable? |
|---|---|---|---|
| `ProposeBookDraft(draft, reason)` | book-specific scope | access + membership then save revision 1 with expected 0 | No |
| `RenameBookDraft(scope, label, expected_revision, reason)` | exact book scope | load, domain amendment, compare-and-set | No |
| `ReframeBookDraft(scope, framework, expected_revision, reason)` | exact book scope | versioned framework pointer amendment | No |
| `GetBookDraft(scope)` | exact book scope | access + membership; fail closed on missing | No |
| `ListBookDrafts(scope)` | **entity-level scope** without book_id | list only same tenant/company/entity | No |

The book itself never has an `activate`, `post`, `publish`, `delete`, or `merge` method. The method names are scoped to drafts. Action strings are prototype-local names, not canonical IAM permissions. Reasons are validated but **not** stored in a durable audit record; do not claim provenance or idempotency.

## 4. Identity and security separation

- `TrustedPrincipal` is inherited from the Foundation and **must come from a trusted authenticator**. In this R&D module it is a forgeable Python value object and therefore **not** real proof of identity.
- `BookDraftAuthorization.require` must authorize each specific action/scoped principal; `MemoryBookAuthorization` is an explicit default-deny allowlist fake, **not** IAM.
- `CompanyEntityMembership.require` must independently prove entity/company relations; `MemoryCompanyEntityMembership` only knows pairs explicitly permitted by a test. A test `allow()` call **does not prove** legal ownership.
- `BookDraftService` verifies principal type and tenant match, then requires both ports before opening UoW; query and mutation both need authorization. A company scope string/UUID does not confer authority.
- The in-memory repository requires a matching book-level scope for reads, forbids changing a BookId's perimeter, and restricts list results to the exact entity perimeter. Local access to fake store/test principal is not a security boundary.
- No GUC, session/SQL login, external JWT signature verifier or live IAM source is introduced. **#71 stays OPEN.**

## 5. Invariants and negative scenarios

| ID | Contract | Evidence |
|---|---|---|
| L04-APP-01 | Missing principal, tenant mismatch, missing action, missing membership deny | unit tests |
| L04-APP-02 | An exact scope cannot read another company/entity's book | unit tests |
| L04-APP-03 | Lists return only same tenant/company/entity | unit tests |
| L04-APP-04 | Initial revision is 1 with `expected_revision=0`; amendments are CAS | unit tests |
| L04-APP-05 | Concurrent in-process stale revision: only one writer wins | unit tests |
| L04-APP-06 | Duplicate code with overlapping effective periods rejected | unit tests |
| L04-APP-07 | Failure before local commit discards staged writes | unit tests |
| L04-APP-08 | No implicit commit, no SQL/IAM/HTTP or L03 gateway dependency | code/tests |
| L04-APP-09 | Revoked test action/membership denies later reads | unit tests |
| L04-APP-10 | Versioned PCG/IFRS/SYSCOHADA references are pointers, not certification | L04-01 tests |

## 6. Known limitations and explicit non-goals

1. **R&D-only local writes:** Memory store is not durable. Callers with direct access to the fake can change their own process and bypass it. Authentication, token verification, key custody and authorization at COMMIT are **not** implemented.
2. **No domain approval:** L04 ownership/sharing (Company, LegalEntity, group), statutory/management/consolidation book types, temporal code uniqueness and default framework rules remain **open ADRs**.
3. **No finance engine:** no journal, debit/credit, chart of accounts, monetary precision, functional/reporting FX, fiscal periods, posting, reconciliation, balance trial or closing.
4. **No durable integrity:** no database uniqueness, optimistic concurrency across processes, idempotency, signed evidence, immutable audit/outbox, PITR/recovery or read-level regulatory retention.
5. **No implied legal compliance:** framework references alone do not validate PCG, OHADA, IFRS or jurisdictional eligibility.
6. **No CI-as-gate:** technical tests passing do not approve G0–G3, stable package publication or production.
7. **No blanket authorization port reuse:** Foundation `TrustedPrincipal` is an input contract, not a security credential; a future certified adapter must enforce external identity and membership.

## 7. Exit conditions & follow-up

- [x] Application commands/queries + Protocol ports.
- [x] Isolated in-process repository/UoW, explicit default-deny test stubs.
- [x] Unit tests including cross-tenant/actor/scope, overlap, two-writer race and rollback.
- [ ] Exact-head Python 3.11/3.12, Ruff, PostgreSQL Foundation regression, migration recovery and wheel/sdist CI.
- [ ] Independent domain/architecture reviewer and ADR-01 disposition, no automatic gate approval.
- [ ] L04-03 production-target persistence **only after** explicit G3/#71 resolution and safe approved integration strategy. No unreviewed SQL `0030+` reuse.

**Decision:** `L04_02_RND_CANDIDATE` until CI is independently observed. Engineering milestone qualification is **not** authority to merge or operate an accounting book.
