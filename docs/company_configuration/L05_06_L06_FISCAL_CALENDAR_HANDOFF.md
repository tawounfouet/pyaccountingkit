# L05-06 → L06 — Fiscal Calendar & Period Management R&D Handoff

**Date:** 2026-10-31  
**Status:** `L06_DOMAIN_BOOTSTRAP_PROPOSED_NOT_STARTED`; NOT a production posting-permission or C10-Q04 implementation.  
**Canonical source:** uploaded `14_COMPANY_CONFIGURATION_FISCAL_CALENDAR_AND_PERIOD_MANAGEMENT.md` §2–12, §16, §20–21. Also `10_COMPANY_CONFIGURATION_INTEGRATION_CONTRACTS.md` for C10-Q04, `18` temporal snapshots and `17` governance.  
**Security baseline:** G0/G1/G2 `PENDING_REVIEW`, G3 `HOLD_SECURITY`, [issue #71](https://github.com/tawounfouet/pyaccountingkit/issues/71) OPEN, G4/G5 unapproved. L05 PRs #82–#86 are drafts/unmerged; this handoff must not depend on L04 published books.

## 1. Precise domain and ownership boundary

The target `14` §5 separates:
- `FiscalCalendar`: candidate calendar identity, code, description, jurisdiction pointer and status;
- `CalendarAssignment`: dated binding to exact `book_id + calendar_version_id`;
- `FiscalYear`: bounded exercise identity/code and nonoverlap;
- `AccountingPeriod`: period code, ordinal, effective interval, **kind** and governed status;
- `AdjustmentPeriod`: explicitly targeted special period with independently approved posting rules;
- `PeriodLock`: orthogonal restriction, possibly narrower than book (journal/source/operation);
- `PeriodTransition`: immutable state-change history, actor, reason and time;
- `ReopeningAuthorization`: bounded, approved, expiring exception;
- `CalendarVersion`: immutable **published** configuration version — **NOT implemented or approved in R&D**.

**Critical separation:** Calendar/Period configuration does not produce a JournalEntry; Runtime may preview a period status, but **Execution and the authoritative Calendar guard must serialize with Ledger COMMIT**. The real `C10-Q04 GetPeriodStatus` and close-vs-posting safety are **NOT** justified by local `is_open` flags.

## 2. Proposed L06-01 safe domain kernel (pure R&D only)

```text
FiscalCalendarDraft (id, scope-intent, code, label, jurisdiction_ref, revision)
  └── FiscalYearDraft (id, calendar_id, code, [start,end), source_ref)
       ├── AccountingPeriodDraft[] (id, year_id, code, ordinal, kind=ORDINARY)
       └── AdjustmentPeriodDraft[] (explicit kind/target, no implicit fallback)

CalendarCode / FiscalYearCode / PeriodCode     typed strings, not numbers
FiscalCalendarId / FiscalYearId / PeriodId    opaque typed UUID identities
EffectiveInterval                             [start,end) business dates
validate_period_structure                     pure, nonoverlap, bounds, gaps policy
```

**No domain setters for `OPEN/CLOSED`, no posting guard, no SQL.** CAL source §6 permits **unusual length exercises** only with an explicit policy. Do **not** globally assume calendar year, 12 Gregorian months, automatic fiscal year Jan→Dec, PCG/IFRS/SYSCOHADA policy defaults, all fiscal years being exactly 365/366 days, or universally 12 periods.

### Initial L06-01 acceptance tests (not implemented here)

| R&D test | Source | Expected |
|---|---|---|
| L06-RND-01 | CAL-INV-01, CAL-SC-01 | Explicit valid calendar/year and 12 monthly ordinary periods **in a test fixture only** |
| L06-RND-02 | CAL-INV-02, CAL-SC-03 | Overlapping ordinary periods refused |
| L06-RND-03 | CAL-SC-04 | Gap refused **only when exact coverage is an explicitly selected policy** |
| L06-RND-04 | CAL-SC-02 | Non-January fiscal years structurally supported without asserting legal validity |
| L06-RND-05 | CAL-INV-11, CAL-SC-14 | Special adjustment period never automatically selected as ordinary |
| L06-RND-06 | CAL-INV-03/09, CAL-SC-18/19 | Missing, double or out-of-year business-date selection refused; no fallback |
| L06-RND-07 | CAL-INV-08, CAL-SC-12/13 | Replay only from available **candidate** version + known-at; no latest substitution |
| L06-RND-08 | CAL-INV-04/10, CAL-SC-07/08/09 | No optimistic `can_post()` API promising actual permission |
| L06-RND-09 | CAL-INV-05/06/12 | No unsigned reopening, lock mutation, live IAM or audit closure |
| L06-RND-10 | Entire L05 handoff | SQL migrations/package parity, no import dependence on draft L04 book providers |

### Caution: structural validity versus operational permission

An interval validation and unique period resolution prove **only a structural candidate**. Even if a source status is `OPEN` in a historical `known_at` read, a fresh Ledger write needs the **current, independently authoritative** period status, every relevant lock and a commit-time concurrency guard. Replay of an old state **must not produce a new posting**.

## 3. Later L06 iterations (proposed R&D only)

| Proposed increment | Scope | Explicit stop |
|---|---|---|
| L06-01 | Calendar/Year/Period draft VOs; overlap, exact coverage optional, special periods | No live status or SQL writer |
| L06-02 | Candidate `CalendarAssignment`, deterministic version/year/period preview with `as_of/known_at` | No publication or book validity proof |
| L06-03 | Period-status/lock **read-only** candidate model and fail-closed preview | No C10 or posting rights |
| L06-04 | Versioned diagnostic replay and negative qualification, transition proposals | No signed publisher or recorded legal actor |
| Later gate-qualified | Durable state transitions, approved lock exceptions, real audit/outbox, C10-Q04 | Requires independent Security/Accounting signoff |
| Production posting guard | Close-vs-posting atomic order/fencing and verification at COMMIT | **Blocked until race tests + G3 security proof** |

The source §21 labels these candidate domain lots `CAL-L1..CAL-L7`; the L06 engineering numbers are **local project roadmap proposal**, not a claim of source approvals.

## 4. Canonical CAL ADRs, all open (source §20)

| ADR | Decision | Mandatory review |
|---|---|---|
| ADR-CAL-01 | Calendrier partagé ou par book | Accounting / Organization |
| ADR-CAL-02 | Agrégat définition vs état | DDD / Persistence |
| ADR-CAL-03 | Périodes d'ajustement : modèle et sélection | Accounting / Normative |
| ADR-CAL-04 | Granularité des locks | Runtime / Security |
| ADR-CAL-05 | États SOFT_CLOSED / CLOSED / ARCHIVED | Accounting / Governance |
| ADR-CAL-06 | Réouverture et dérogation | Governance / Audit |
| ADR-CAL-07 | Service autoritatif de clôture et posting guard (`ADR-CC-007`) | Execution / Ledger |
| ADR-CAL-08 | Sérialisation/fencing et race TOCTOU | Data / Security |
| ADR-CAL-09 | Bitemporalité des périodes et snapshots | Data / Runtime |
| ADR-CAL-10 | Règles calendrier par référentiel/juridiction | Accounting / Normative |

These roles are suggested reviewers, not signed owners. **No ADR is ratified by this file.**

## 5. Important technical risk: check-then-commit is unsafe

The source §10 explicitly illustrates that between `GetPeriodStatus` and `JournalEntry` COMMIT, a concurrent close operation can make an earlier `OPEN` observation stale. A naïve network `check()` followed by SQL `insert()` **does not prevent posting into a newly closed period**.

A valid future implementation must prove a real serial order using a same-DB transaction with an appropriate lock, or a fencing token verified atomically on write, or another independently qualified protocol. It must test the **actual race between ClosePeriod and CommitPosting** and demonstrate that exactly the permitted operations commit. This security/consistency guarantee **cannot be completed** in the R&D draft, nor is it covered by the green Foundation migration suite.

## 6. What must be demonstrably true before production

- Independent, signed real IAM/actor command and issuer authorization with atomic COMMIT guarantee (blocker #71).
- Approved Calendar ownership, book association, period status and special-period policies.
- Explicit `expected_version` on transitions, separated duties for reopening, audit + transactional outbox.
- Durable immutable published CalendarVersion, unambiguous calendar/book binding and historical replay.
- Operational source-of-truth locks, denial on missing/contradictory data, no stale-read bypass.
- C10-Q04 contract compatibility and consumer tests.
- Concurrency and restart/fencing tests against real persistence for close-vs-posting.
- Legal/Accounting/Architecture/Security ADR approvals and G3/G4/G5 pass; **none is implied by current PRs**.

**Next concrete PR:** `L06-01 Fiscal Calendar, Fiscal Year & Accounting Period Domain Kernel (R&D)`, from isolated `main` when practical, with typed IDs and pure validation only. Do **not** create SQL, call Ledger or claim "period postable" in that first cut.
