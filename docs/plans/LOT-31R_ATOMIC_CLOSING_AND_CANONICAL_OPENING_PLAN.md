# LOT-31R — Atomic Closing & Canonical Opening

> Remediation alias requested as LOT-31.
>
> The repository already owns a historical product LOT-31, so this remediation delivery uses
> **LOT-31R**.
>
> **Findings:** F07, F08, F09
> **Remediation lot:** REM-05
> **Target:** 0.7.0rc2 — tranche 2
> **Baseline:** main@456abddb5c008ad456527227adf7f9183e346f99
> **Status:** IMPLEMENTING / QUALIFYING

## 1. Objective

Close the remaining REM-05 atomicity gaps:

- F07: opening entries must use canonical posting;
- F08: closing evidence must commit atomically with accounting state;
- F09: relevant read dependencies must participate in conflict detection.

## 2. Canonical opening path

~~~text
POST_CLOSING trial balance
    ↓
stable AccountId preserved
    ↓
OpeningEntryBuilder
    ↓
VALIDATED EntryType.OPENING
    ↓
PostingOrchestrator.post_in_uow(...)
    ↓
same posting rules as every other accounting entry
~~~

Opening generation may no longer manufacture a POSTED entry directly or rebuild account identity
from the business code.

## 3. Atomic closing proof

The transaction contains all of:

~~~text
period transition
opening posting when requested
durable ClosingRun append
CLOSING_SEALED audit event
CLOSING_SEALED outbox record
commit
~~~

Any failure before commit rolls all of them back.

ClosingRunBook remains a post-commit in-process cache only. It is not the durable accounting proof.

## 4. Fresh balance in the same UoW

The POST_CLOSING balance used for final validation is rebuilt inside the closing UoW:

~~~text
open UoW
  read period
  read posted entries
  validate fresh balance
  transition period
  post opening
  persist proof
commit
~~~

This makes the read set part of the transaction boundary.

## 5. In-memory read dependency conflicts

The reference adapter records read dependencies for:

- individual entries;
- posted-entry collections by period;
- posted-entry collections by journal;
- periods;
- journals;
- reversals;
- execution traces;
- closing runs.

At commit it compares the shared store with the baseline. A concurrent posting into a period that
was used to compute closing evidence therefore raises RevisionConflictError.

## 6. PostgreSQL parity

Django and SQLAlchemy both expose ClosingRunRepository through UnitOfWork and persist a sealed
closing run in table `pyak_closing_run`.

Migration baselines:

~~~text
Django      0005_closing_run
SQLAlchemy  0005_closing_run
~~~

## 7. Corrective evidence

F07:
- opening builder returns VALIDATED, never POSTED;
- AccountId is preserved;
- missing stable AccountId fails closed;
- opening is posted through PostingOrchestrator inside the closing UoW;
- cross-entity opening rolls back the entire close.

F08:
- ClosingRun is durable and append-only;
- period transition, opening, ClosingRun, audit and outbox share one transaction;
- simulated commit failure leaves no period close, opening or proof;
- Django/PostgreSQL and SQLAlchemy/PostgreSQL qualify durable ClosingRun rollback.

F09:
- read-only period entry collection detects a concurrent posting;
- close-vs-post race after fresh balance read fails with RevisionConflictError;
- failed close leaves period OPEN and emits no closing proof.

## 8. Exit criteria

~~~text
[ ] F07 corrective tests green
[ ] F08 atomic rollback tests green
[ ] F09 phantom/read dependency tests green
[ ] Django migration 0005 green
[ ] SQLAlchemy migration 0005 green
[ ] adapter contract manifest coherent
[ ] Python 3.11 / 3.12 / 3.13 green
[ ] Django/PostgreSQL green
[ ] SQLAlchemy/PostgreSQL green
[ ] Security green
[ ] Canonical CI gate green
[ ] F07/F08/F09 -> FIXED_UNVERIFIED after merge
[ ] REM-05 implementation_status -> COMPLETE after merge
~~~

VERIFIED remains reserved for exact-main-SHA evidence and REM-10.
