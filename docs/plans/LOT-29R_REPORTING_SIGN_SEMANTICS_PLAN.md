# LOT-29R — Reporting Sign Semantics

> **Remediation alias requested as LOT-29**
>
> The repository already owns a historical product LOT-29 for API / schema freeze work.
> This remediation delivery therefore uses **LOT-29R** to preserve the existing roadmap identity.
>
> **Finding:** F21
> **Remediation lot:** REM-06
> **Target:** 0.7.0rc2 — tranche 1
> **Baseline:** main@8d410d595c582e822fdccbfda5be711d8f64464c
> **Status:** IMPLEMENTING / QUALIFYING

## 1. Problem

Financial statement evaluation currently resolves child lines first and those child lines may
already have their presentation sign convention applied. Aggregate and formula lines then call
the same presentation operation again on their computed result.

That makes a second sign transformation representable in the model and violates the intended
separation between ledger-signed balances and report presentation.

## 2. Source invariant

The reporting architecture states that a presentation line may invert a sign without changing
the ledger-signed balance.

LOT-29R makes that boundary executable:

~~~text
ledger signed Money
    ↓
mapped DETAIL line
    ↓
apply presentation sign exactly once
    ↓
presented statement value
    ↓
SUBTOTAL / TOTAL / FORMULA
aggregate already-presented values
    ↓
no second sign transformation
    ↓
ReportSnapshot
    ↓
Financial Analysis consumes snapshot amount as-is
~~~

## 3. Executable rules

### Rule SIGN-01

Non-natural sign conventions are valid only on mapped DETAIL lines.

Allowed on DETAIL:

~~~text
NATURAL
DEBIT_POSITIVE
CREDIT_POSITIVE
ABSOLUTE
~~~

Computed lines are constrained to:

~~~text
NATURAL
~~~

### Rule SIGN-02

SUBTOTAL and TOTAL sum already-presented child values and never call presentation sign logic.

### Rule SIGN-03

FORMULA evaluates already-presented dependencies and never applies an additional sign convention.

### Rule SIGN-04

Financial Analysis consumes immutable ReportSnapshot amounts directly and does not reinterpret
or reapply statement sign conventions.

## 4. Why this preserves compatibility

Repository-wide inspection before implementation found every existing non-natural
StatementSignConvention usage on DETAIL lines only.

Therefore the new validation turns an implicit invariant into a fail-closed contract without
invalidating an existing legitimate statement definition.

## 5. Corrective tests

Required evidence:

- aggregate lines reject CREDIT_POSITIVE or other non-natural conventions;
- formula lines reject non-natural conventions;
- CREDIT_POSITIVE still converts a negative ledger-signed detail amount into a positive
  presented amount;
- Financial Analysis consumes the presented ReportSnapshot amount unchanged;
- existing balance-sheet controls remain green;
- CFA FRA golden statement parity remains green;
- regulatory reporting remains green.

## 6. Non-goals

LOT-29R does not change:

- ledger debit/credit semantics;
- AccountBalanceLine signed-balance convention;
- monetary allocation from LOT-28R / F16;
- regulatory mapping semantics;
- analytical formulas;
- closing/opening behavior from REM-05.

## 7. Exit criteria

~~~text
[ ] computed lines cannot carry a non-natural sign convention
[ ] engine applies presentation sign only to DETAIL values
[ ] aggregate and formula lines cannot re-sign their inputs
[ ] Financial Analysis consumes ReportSnapshot values unchanged
[ ] existing reporting golden tests green
[ ] Python 3.11 / 3.12 / 3.13 green
[ ] Django/PostgreSQL green
[ ] SQLAlchemy/PostgreSQL green
[ ] Security green
[ ] Canonical CI gate green
[ ] F21 -> FIXED_UNVERIFIED after merge
[ ] REM-06 implementation_status -> COMPLETE after merge
~~~

VERIFIED remains reserved for exact-main-SHA evidence and REM-10 transverse qualification.
