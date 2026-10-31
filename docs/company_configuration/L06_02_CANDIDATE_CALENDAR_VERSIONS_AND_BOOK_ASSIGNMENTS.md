# L06-02 — Calendar Version Candidates, Book Assignments & Bitemporal Previews

**Date:** 2026-10-31  
**Status:** `L06_02_CALENDAR_ASSIGNMENT_RND_CANDIDATE` pending CI. **Never a published `CalendarVersion`, a legal `AccountingBook`, C10-Q04 `GetPeriodStatus`, fiscal close or permission to post.**  
**Parent:** draft [L06-01 PR #88](https://github.com/tawounfouet/pyaccountingkit/pull/88) @ `3003192495d0ff25e9b7a0dc3f6267157cd3a6a9`, base isolated `main@acdee98c`. No unmerged L03/L04/L05 imports.  
**Source of truth:** `14_COMPANY_CONFIGURATION_FISCAL_CALENDAR_AND_PERIOD_MANAGEMENT.md` §§4–6 (CalendarAssignment and calendar version), §9 (four dates), §10 (close-vs-posting), §11 (C10-Q04 **target only**), §12 `CAL-INV-01..12`, §16 `CAL-SC-01..20`, §20 `ADR-CAL-01..10` and §21 `CAL-L2`. Bitemporal replay source: `18_COMPANY_CONFIGURATION_VERSIONING_TEMPORALITY_AND_SNAPSHOTS.md`.

## 1. Domain boundaries and explicitly provisional choice

The target `CalendarAssignment(book_id,calendar_version_id,valid_from/to)` must be unique by **book + business date**. Historical reads must preserve the version known at `known_at`. Source §4 explicitly permits shared calendars via a binding but leaves ownership/cardinalities to **ADR-CAL-01 (OPEN)**.

This R&D prototype requires:
- One claimed **entity-level** `FiscalCalendarDraft` with `book_id=None`, and one typed **book-level** `ConfigurationScope` in each assignment; exact tenant/company/legal-entity equality. A book UUID alone is **not** verified legal book membership or an L04 published book.
- `CalendarCandidateVersionId` and `BookCalendarAssignmentCandidateId` as distinct typed UUIDs. A `CalendarVersionCandidate` contains the **entire immutable-in-Python** L06-01 calendar structure, full year/period roster, an explicit contiguous/gaps policy, effective `[start,end)`, knowledge `[recorded_from,recorded_to)` and source reference.
- A `BookCalendarAssignmentCandidate` holds exact calendar ID and **exact candidate version ID**, its own business/knowledge validity and provenance. **No fallback** to latest/versionless calendar. Multiple active book assignments are ambiguous.
- A read-only `BookCalendarCandidateReadReceipt` pins the exact assignment/version, full version digest, selected ordinary or explicitly requested adjustment period, source, `as_of`, `known_at` and a deterministic local checksum. It is **not** a signed/authoritative period state receipt.

```text
 FiscalCalendarDraft + FiscalYearDraft[] + AccountingPeriodDraft[]
         │                   │
 CalendarCoveragePolicy       │
         └──────────┬────────┘
                    v
           CalendarVersionCandidate
             CalendarCandidateVersionId
             effective, knowledge, source_ref
             full-content canonical SHA-256 digest
                    ^
                    │ exact version pin
           BookCalendarAssignmentCandidate
             book scope + typed book_id (unverified)
             CalendarId + CalendarCandidateVersionId
             effective, knowledge, source_ref
                    │
                    v
 preview_book_calendar_candidate(book_scope, as_of, known_at,
                                 assignments, versions, adjustment_id?)
                    │ fail-closed
                    v
      BookCalendarCandidateReadReceipt
          period ID + kind + code + year ID
          assignment ID + exact version ID + digest
          dates, book scope, canonical local checksum
          UNPUBLISHED_STRUCTURAL_PERIOD_PREVIEW
```

**Patterns (Software Design & Learning):** DDD typed Identity/Value Object and candidate aggregate, immutable snapshot **prototype**, Domain Policy, Hexagonal Ports/Adapters, CQRS read-only Query Service, Dependency Inversion, separation of business/knowledge time, explicit provenance, strict fail-closed handling. No live database repository or posting UoW.

## 2. Canonical deterministic manifest

`SCHEMA = "l06-rnd-calendar-v1"`. The version manifest enumerates (not hashes only) calendar ID, scope/code/label/jurisdiction/source/effective interval, all years and all ordinary/adjustment periods, ordinal/target code/kind/effective interval and all source refs, explicit coverage policy, candidate version identity and effective/knowledge intervals.

Full-content canonicalization: sorted accounts **not applicable**; **years and periods sorted by typed UUID**; JSON `sort_keys=True`, `ensure_ascii=False`, `separators=(',',':')`, `allow_nan=False`; dates ISO, `known_at` normalized to UTC with 6 decimal digits and `Z`. `sha256:<64 lowercase hex>` recorded on candidate version and receipt.

`verify_integrity()` recomputes local checksums and validates the full nested period roster; it refuses a mutated period or receipt, but the hash is an **in-process consistency check, NOT independent signature or legal/non-repudiation proof**. Frozen Python dataclasses cannot prevent direct `object.__setattr__` changes by an in-process attacker, who could also forge checksums.

## 3. Bitemporal resolution contract

`preview_book_calendar_candidate` requires:
1. Typed `book_scope` with book UUID, `as_of: date` (not datetime), aware `known_at: datetime`; immutable tuples of typed assignment candidates and versions.
2. Reject **any** foreign-book assignment (even a non-active one), repeated assignment identities, absent applicable assignment or two simultaneously active assignments.
3. Reject foreign-entity calendar candidates, repeated candidate version IDs and tampered candidate versions; search **only** the version named on the selected assignment, never latest.
4. Reject assignment/calendar ID mismatch, validity not contained by the version, unavailable version at `known_at`, or as-of outside its validity.
5. Reuse L06-01 `preview_ordinary_period_candidate`, **never selecting adjustment implicitly**, or `preview_adjustment_period_candidate` only if the query provides exact typed adjustment period ID.
6. Return a reproducible structural receipt; **no** `PeriodStatus`, locks, live posting check, `known_at` authorization or C10-Q04.

**Historical replay example (synthetic):**
- `as_of = 2027-02-15, known_at = 2027-02-01` selects version V1: P01 ends Feb 1, P02 applies.
- `as_of = 2027-02-15, known_at = 2027-03-01` selects corrected V2: P01 now ends Mar 1, P01 applies.
- Old V1 and B1 knowledge interval ends at March boundary; new V2/B2 begins there. Both receipts remain independently reproducible; **no history overwriting** and no new journal is issued.

**Half-open boundaries** are checked at both business dates and knowledge instants. Source §9 differentiates business event date, posting date, recorded/published instant and executed/commit instant. This prototype represents only an explicit *requested business date* and *known-at instant*. It does **not** equate them to event-time or SQL commit-time truth.

## 4. Read-only application, adapters and security

```text
PreviewBookCalendarCandidate
  book_scope · as_of · known_at · adjustment_period_id?
          │
BookCalendarCandidatePreviewService
  - type-check TrustedPrincipal (not real verified identity)
  - tenant equality
  - AuthorizationPort.require("calendar.assignment.candidate.preview")
  - BookCalendarAssignmentsReader / CalendarCandidateVersionsReader
          │
   pure domain resolver
          │
BookCalendarCandidateReadReceipt
```

`MemoryCalendarCandidateVersions` and `MemoryBookCalendarAssignments` are immutable-tuple, scope-filtered **test fixtures** only. Malicious-reader tests verify the pure domain rejects a leaked foreign assignment or foreign calendar; a simple in-memory fake grant cannot prove real IAM or dual control. No SQL, persisted ledger, Outbox, signed audit or real C10 contract.

## 5. Negative acceptance and source gap matrix

| Local test area | Source target | What is actually proven |
|---|---|---|
| Exact version, date, book | CAL-INV-03 partial; CAL-SC-05 partial | One candidate assignment for exact book/time; **not** verified Book/Normative Layer |
| Temporal replay | CAL-INV-08 partial, CAL-SC-12 | Original vs amended structural version at explicit known-at; no published snapshot |
| Missing history | CAL-INV-09 partial, CAL-SC-13 | Typed missing exact-version refusal, never latest fallback |
| No calendar assigned | CAL-SC-19 partial | Explicit error for unassigned candidate book |
| Future assignment / known-at | §9 temporal principles | No backfilling of future knowledge |
| Overlap / repeated IDs | CAL-INV-03 partial | Fail-closed on simultaneous assignment and duplicate IDs |
| Period structure | CAL-INV-01/02 partial | Revalidates L06-01 entire nested calendar structure |
| Adjustment explicit | CAL-INV-11 partial, CAL-SC-14 | Requires exact ID **without** checking real adjustment authorization |
| Scope isolation | §4, CAL-SC-05 partial | Foreign book/company/entity/tenant candidates rejected |
| Candidate checksum | CAL-INV-07 partial | Detects in-process tamper; **no approved immutable publication** |
| No unsafe posting | CAL-INV-04/05/06/10/12 missing | No status, posting, locks, transitions, SQL or transactional authority |
| Non-calendar-year | CAL-SC-02 partial | Can model April–March candidate; normative compatibility not checked |

### Unresolved authority and governance

All `ADR-CAL-01..10` remain **OPEN**. In particular, shared-vs-owned calendar (01), special adjustment policy (03), historic version semantics (09), jurisdiction reference correctness (10), and authoritative period state + fencing against close/post race (07–08) are unapproved. **No permitted posting follows from resolving a structural candidate**; source §10 TOCTOU requires serialized/fenced checks at COMMIT, impossible to prove with these mocks.

Issue [#71](https://github.com/tawounfouet/pyaccountingkit/issues/71) remains OPEN: the **independently signed live actor/issuer decision at SQL COMMIT** is still missing. G0/G1/G2 `PENDING_REVIEW`; G3 `HOLD_SECURITY`; G4/G5/G6 **NOT APPROVED**. No SQL migration, new stable release, merge or source regulatory signoff.

## 6. Next milestone

- [x] Exact candidate CalendarVersion with full period/date manifest and sealed digest.
- [x] Exact dated BookCalendarAssignment candidate, unambiguous as-of/known-at resolution.
- [x] Explicit ordinary/adjustment period structural preview and bitemporal read receipts.
- [x] Read-only hexagonal service and scope-constrained memory fixtures.
- [x] Negative tests covering historical corrections, stale knowledge, fraud/tamper, overlaps, scope leaks, missing history, exception nonexecution.
- [ ] Exact-HEAD GitHub Python 3.11/3.12 + Ruff, Foundation PG/recovery and wheel/sdist migration parity.
- [ ] Independent Accounting/Architecture/Normative/Security publication approval and G6; **not claimed**.

**Next safe R&D slice:** L06-03 — candidate `PeriodStatus` and `PeriodLock` **read-only** diagnostic previews, without exposing `can_post`, `close_period`, `reopen`, or an optimistic C10 status result as Ledger permission.
