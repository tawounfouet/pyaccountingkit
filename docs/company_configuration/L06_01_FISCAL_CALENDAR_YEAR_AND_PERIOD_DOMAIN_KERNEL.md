# L06-01 — Fiscal Calendar, Fiscal Year & Accounting Period Domain Kernel (R&D)

**Date:** 2026-10-31  
**Status:** `L06_01_FISCAL_CALENDAR_RND_CANDIDATE` pending exact-head qualification. **NOT a fiscal calendar publication, C10-Q04 endpoint, or postability contract.**  
**Source-of-truth:** `14_COMPANY_CONFIGURATION_FISCAL_CALENDAR_AND_PERIOD_MANAGEMENT.md` §5.1–5.3 (candidate entities/VOs), §6 (exercises, ordinary and adjustment periods), §9–10 (four dates, posting TOCTOU), §12 (CAL-INV-01..12), §16 (CAL-SC-01..20), §20–21 (ADR-CAL-01..10 and CAL-L1..L7).  
**Roadmap mapping:** `COMPANY_CONFIGURATION_IMPLEMENTATION_ROADMAP.md` §6 → **L06 / G6**; this isolated slice is only a **partial prototype of source CAL-L1**. It does not close CAL-L2..CAL-L7, G6, or the source's publication prerequisites.  
**Baseline:** isolated from unchanged `main@acdee98ca2736d79e17174f510ac767defd90db8`, **NOT stacked on unmerged L03/L04/L05 drafts** (e.g. #73/#81/#87). L05-06 R&D handoff: [PR #87](https://github.com/tawounfouet/pyaccountingkit/pull/87).  
**Gates:** G0/G1/G2 `PENDING_REVIEW`, G3 `HOLD_SECURITY` for [issue #71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN, G4/G5/G6 `NOT_APPROVED`. No merge or stable release.

## 1. Business scope, anti-assumptions

A **FiscalCalendar** defines a structural calendar for a claimed entity-level scope; it does not authorize a journal. A **FiscalYear** is a bounded date interval and may begin on any month/day. **AccountingPeriod** candidates are typed `ORDINARY` vs `ADJUSTMENT`. A book might use a shared calendar or its own calendar only through an **explicit versioned CalendarAssignment in later work**; source `ADR-CAL-01` remains OPEN.

Do not assume 12 periods, Jan–Dec fiscal years, 365/366-day legal constraints, ISO weekly calendars, authorized PCG/IFRS/SYSCOHADA conventions, or a status `OPEN`. Both contiguous coverage and allowed gaps are **explicit local structural policies**; neither proves legal validity in a particular jurisdiction. The source permits, subject to policy, 12, 13, 4-4-5 and irregular fiscal years. No 4-4-5 generator or normative length validator is implemented.

## 2. Pure DDD model

```text
FiscalCalendarDraft              (unpublished entity candidate)
 ├── FiscalCalendarId             typed UUID, never CalendarCode
 ├── ConfigurationScope           explicit tenant/company/legal entity intent
 │                                  book_id MUST be None; no book rights implied
 ├── CalendarCode                  canonical provisional uppercase ASCII
 ├── label / jurisdiction_ref     opaque unverified reference, never normative signoff
 ├── EffectiveInterval            date [start,end); end may be open for calendar
 └── source_ref                   unverified provenance

FiscalYearDraft                  (unpublished candidate entity)
 ├── FiscalYearId                 typed UUID, distinct from code
 ├── FiscalCalendarId             exact calendar relation, not real SQL FK
 ├── ConfigurationScope           must match calendar scope
 ├── FiscalYearCode               literal string, no numeric conversion
 ├── EffectiveInterval            FINITE [start,end)
 └── source_ref

AccountingPeriodDraft            (unpublished candidate entity)
 ├── AccountingPeriodId           typed UUID
 ├── FiscalYearId / CalendarId    exact relations
 ├── PeriodCode                   literal string incl. leading zeroes
 ├── PeriodKind                   ORDINARY | ADJUSTMENT
 ├── EffectiveInterval            FINITE [start,end) inside year
 ├── ORDINARY: ordinal>0          unique/chronological within a year
 ├── ADJUSTMENT: ordinal=None     explicit adjustment_target_id required
 └── source_ref                   not signed

CalendarCoveragePolicy           REQUIRE_CONTIGUOUS | ALLOW_GAPS
validate_fiscal_structure(...)   pure complete-catalog validation
preview_ordinary_period_candidate(... as_of)
preview_adjustment_period_candidate(... as_of, adjustment_period_id)
      → FiscalPeriodCandidatePreview (structural only, no status/eligibility)
```

**DDD/design concepts:** Typed Identity, Value Object (`CalendarCode`, `FiscalYearCode`, `PeriodCode`, `EffectiveInterval`), draft Entity with stable identity semantics, pure Domain Policy, fail-closed preview, Separation of Concerns (SoC), YAGNI. There is **no Repository/UoW, SQL, command service, C10, live IAM, or temporal publisher**. Current source-level invariant checks do not establish database transactions or source authenticity.

## 3. Local structural invariants and refusal rules

| L06-01 rule | Source link | Executable R&D behavior |
|---|---|---|
| R01 | CAL-INV-01 | Half-open typed business intervals; finite fiscal years and periods; explicit calendar/year scope |
| R02 | CAL-INV-02 | Reject intersecting `ORDINARY` periods anywhere in the supplied candidate catalog (including future periods) |
| R03 | CAL-INV-03 **partial** | Exactly one applicable **calendar-year candidate** and ordinary period on date; **no book assignment or C10** |
| R04 | CAL-SC-04 | `REQUIRE_CONTIGUOUS` rejects start/end gaps and internal gaps; `ALLOW_GAPS` accepts them structurally, but previews refuse dates in gaps |
| R05 | §6.1/6.2 | Fiscal years need not be Jan–Dec; ordinary count is configurable, no forced 12 |
| R06 | CAL-INV-11 **partial** | Adjustment candidates must have exact typed target ID referencing overlapping ordinary period in same fiscal year; **never selected implicitly** |
| R07 | CAL-INV-09 **partial** | Missing year, missing ordinary period, wrong explicit adjustment ID/date: fail closed, no next/latest/ordinary-to-special fallback |
| R08 | §6 and multi-tenant | No orphan period, cross-chart/tenant/company/entity relation, repeated identities/codes, or duplicate ordinary ordinal |
| R09 | Source anti-posting | No `PeriodStatus`, `OPEN`, lock, reopen, posting guard, C10-Q04, Ledger or publication method |
| R10 | Type contracts | Reject untyped IDs/codes/catalogs/dates/coverage policy and prohibited book-level ownership |

An **adjustment relation must overlap its explicitly targeted ordinary period** as a provisional R&D coherence constraint; the source leaves the full specialized scope/posting-rule policy to **ADR-CAL-03**. This local choice is *not* a universal legal requirement for end-of-year adjustment periods. Special periods with the same date interval as ordinary periods do not introduce extra ordinary-date candidates.

The `validate_fiscal_structure` policy verifies every supplied year and period **before** previewing a date, so an invalid future schedule cannot be hidden by asking for a current date. This is a bounded in-memory check only. Atomic uniqueness under concurrent database writes and signed temporal versions remain unimplemented.

## 4. Explicit gaps and limits

**Target source `CAL-INV-04..08/10/12` remains unimplemented**:
- `CAL-INV-04`: no actual posting status/lock eligibility; no real `GetPeriodStatus`.
- `CAL-INV-05`: no version-checked, authorized period transition.
- `CAL-INV-06`: no approved/audited reopening.
- `CAL-INV-07`: no published immutable CalendarVersion.
- `CAL-INV-08`: no pinned version/`known_at` historical replay (L06-02+).
- `CAL-INV-10`: no atomic close-vs-posting protection.
- `CAL-INV-12`: no lock change audit.
- `CAL-INV-03` only checks one candidate within this **unbooked** calendar; full per-book/date uniqueness is deferred to CalendarAssignment.

### Critical TOCTOU / security STOP

Source §10 notes that a period can become `CLOSED` after a read returns `OPEN` but before a journal COMMIT. Neither a structural preview nor a later read-only status check can authorize posting. Any **future** production path needs independently approved period authority, verified signed actor/issuer SQL authorization, atomic close-vs-posting fencing/serialization and adversarial real transaction race tests. **Security blocker #71 is not mitigated** here.

## 5. Source scenarios / test scope

- **CAL-SC-01:** 12 monthly periods illustrated in a test, *not enforced globally*.
- **CAL-SC-02:** non-January year boundary supported as a structure (normative compatibility not verified).
- **CAL-SC-03:** overlapping ordinary periods denied, even in the future.
- **CAL-SC-04:** missing coverage rejected only under explicitly selected continuous policy.
- **CAL-SC-14:** adjustment selected only with explicit typed ID; *not* an approval or permission test.
- **CAL-SC-18:** out-of-year date rejected with typed missing-period error.
- **CAL-SC-19:** book-without-assignment is **not implemented**; this L06-01 slice has no Book entity or assignment.
- **CAL-SC-05..09, 10..13, 15..17, 20** remain only future source requirements, with no live result claims.

Test file: `tests/unit/company_configuration/test_l06_01_fiscal_calendar_domain.py` — pure positive and adversarial cases for typed IDs and codes, 12 periods and two non-Jan periods, business boundaries, contiguous/partial coverage, overlaps, repeated IDs, scopes, adjustment targeting, immutable objects and no SQL/post method.

## 6. Canonical ADRs still OPEN (source §20)

| ADR | Open question |
|---|---|
| ADR-CAL-01 | Calendrier partagé ou par book |
| ADR-CAL-02 | Agrégats définition vs état |
| ADR-CAL-03 | Ajustement : modèle et sélection |
| ADR-CAL-04 | Granularité des locks |
| ADR-CAL-05 | États SOFT_CLOSED / CLOSED / ARCHIVED |
| ADR-CAL-06 | Réouverture et dérogation |
| ADR-CAL-07 | Service autoritatif de clôture / posting guard |
| ADR-CAL-08 | Sérialisation/fencing contre race TOCTOU |
| ADR-CAL-09 | Temporalité et snapshots |
| ADR-CAL-10 | Règles calendaires par référentiel/juridiction |

No ADR is signed, approved or replaced by this implementation. Proposed codes, explicit adjustment targeting and entity-level scope are **reversible R&D constraints**.

## 7. Roadmap from here

| Proposed cut | Exact deliverable | Hard stop |
|---|---|---|
| **L06-01 / CAL-L1 (this PR)** | Typed IDs, calendar/year/period drafts, complete structural validation and previews | No runtime status, book ownership, SQL |
| L06-02 / CAL-L2 R&D | Pinned CalendarVersionCandidate and dated BookCalendarAssignmentCandidate, `as_of/known_at` replay | No published version or legal book membership |
| L06-03 / CAL-L3 R&D | Proposed status, locks, transition *read* and refusal previews | No durable state writer or posting right |
| L06-04 / CAL-L4 target | Governed published versions, audit, outbox and approved transitions | Needs G3/G6 and qualified persistence |
| L06-05 / CAL-L5 target | C10-Q04 exact published status DTO and consumer tests | No fake provider |
| L06-06 / CAL-L6 target | Atomic guard against real concurrent close/commit | Real fencing & #71 required |
| L06-07 / CAL-L7 target | Multi-book E2E, historical replay, migration/restore qualification | Gate G6/production decision required |

### Acceptance checklist (R&D only)

- [x] `FiscalCalendarId`, `FiscalYearId`, `AccountingPeriodId` opaque typed IDs.
- [x] Frozen calendar/year/period drafts and explicit structural `CalendarCoveragePolicy`.
- [x] Fail-closed full-catalog validation and explicit special-period preview.
- [x] Negative unit tests and isolated main-derived branch, zero SQL.
- [ ] Exact-head CI: Python 3.11/3.12 + Ruff, PostgreSQL Foundation/recovery, 14 SQL migration parity.
- [ ] Independent Accounting, Normative, Architecture, Security sign-off; **not included**.

**Exit label before CI:** `L06_01_FISCAL_CALENDAR_DOMAIN_RND_CANDIDATE`, never `G6_GO`, `C10_Q04_READY` or `ACCOUNTING_PERIOD_POSTABLE`.
