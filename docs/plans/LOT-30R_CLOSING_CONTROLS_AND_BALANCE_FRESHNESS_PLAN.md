# LOT-30R — Closing Controls & Balance Freshness

> **Remediation alias requested as LOT-30**
>
> The repository already owns a historical product LOT-30. This remediation delivery therefore
> uses **LOT-30R** to preserve roadmap identity.
>
> **Findings:** F05, F06
> **Remediation lot:** REM-05
> **Target:** 0.7.0rc2 — tranche 2
> **Baseline:** main@f431127c8ff390c3ad1cd86ea4b77d7ad35a3fc4
> **Status:** IMPLEMENTING / QUALIFYING

## 1. Objective

Make the pre-close decision fail-closed before REM-05 proceeds to canonical opening posting,
atomic proof persistence, and concurrency.

LOT-30R covers two invariants:

~~~text
F05
required blocking controls must exist and PASS

F06
closing balance evidence must be current, scoped and POST_CLOSING
~~~

## 2. F05 — control gate

A closing gate defines an explicit set of blocking control codes.

For every required code, closing now requires exactly one selected ControlRun:

~~~text
required control
    ↓
present exactly once
    ↓
same period as close
    ↓
outcome == PASS
    ↓
eligible
~~~

The following states block:

~~~text
MISSING
FAIL
ERROR
FOREIGN_PERIOD
AMBIGUOUS_DUPLICATE
~~~

Non-blocking controls do not affect the gate.

## 3. F06 — balance evidence

The caller-provided balance is not trusted as current merely because it is a valid TrialBalance.

Closing requires:

~~~text
supplied TrialBalance
    ├── period == target period
    ├── snapshot == POST_CLOSING
    ├── accounting_entity_id pinned
    └── entity == target period entity

fresh canonical TrialBalance
    ├── recomputed through configured provider
    ├── period == target period
    ├── snapshot == POST_CLOSING
    ├── entity == target period entity
    └── checksum == supplied checksum
~~~

A checksum mismatch is stale evidence and blocks closing.

## 4. Freshness boundary

LOT-30R proves freshness at the pre-close validation boundary.

It does **not** yet claim that no posting can race between the fresh read and the final commit.
That read-dependency conflict window is explicitly owned by F09 / LOT-31R.

This separation is intentional:

~~~text
LOT-30R / F06
fresh proof at validation boundary

LOT-31R / F09
read dependency participates in transaction conflict detection
~~~

## 5. Provider contract

ClosingOrchestrator accepts a canonical TrialBalance provider.

For production composition, the intended implementation is TrialBalanceQuery.balance_for or an
adapter-neutral equivalent with the same semantics.

If no provider is configured, closing fails closed.

## 6. Corrective tests

F05:

- missing required control blocks;
- FAIL blocks;
- ERROR blocks;
- required control from another period blocks;
- duplicate/ambiguous required evidence blocks;
- non-blocking failures are ignored when required controls pass.

F06:

- wrong period balance blocks;
- foreign entity balance blocks;
- non-POST_CLOSING balance blocks;
- stale checksum blocks;
- canonical provider is exercised by the existing end-to-end close scenario.

## 7. Non-goals

LOT-30R does not implement:

- F07 canonical posting of opening entries;
- F08 atomic persistence of closing proof with accounting transition;
- F09 read-resource optimistic conflict tracking;
- REM-07 publication safety.

## 8. Exit criteria

~~~text
[ ] missing blocking control => reject
[ ] ERROR blocking control => reject
[ ] wrong-period control => reject
[ ] supplied balance period/entity/snapshot validated
[ ] fresh canonical balance loaded
[ ] stale checksum => reject
[ ] current canonical balance => close allowed
[ ] existing closing behavior remains green
[ ] Python 3.11 / 3.12 / 3.13 green
[ ] Django/PostgreSQL green
[ ] SQLAlchemy/PostgreSQL green
[ ] Security green
[ ] Canonical CI gate green
[ ] F05/F06 -> FIXED_UNVERIFIED after merge
~~~

VERIFIED remains reserved for exact-main-SHA evidence and REM-10 transverse qualification.
