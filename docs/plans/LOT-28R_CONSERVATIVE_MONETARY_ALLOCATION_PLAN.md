# LOT-28R — Conservative Monetary Allocation

> **Remediation alias requested as LOT-28**
>
> The repository already owns a historical product LOT-28 (Reliability / Performance / Security).
> To preserve roadmap traceability, this remediation delivery is named **LOT-28R** while keeping
> the user-facing sequence “LOT-28 — Conservative Monetary Allocation”.
>
> **Finding:** F16
> **Remediation lot:** REM-06
> **Target:** 0.7.0rc2 — tranche 1
> **Baseline:** main@56e899bb3e2e3acf611191afc437d5394763acbe
> **Status:** IMPLEMENTING / QUALIFYING

## 1. Problem

The audited reporting paths multiply Money by each mapping allocation independently.
Because Money quantizes at construction, each contribution is rounded before the complete
allocation is known.

The adversarial example is:

~~~text
source = 0.01 EUR
allocation A = 50 %
allocation B = 50 %

old behavior:
0.01 * 0.5 -> 0.01
0.01 * 0.5 -> 0.01
sum         -> 0.02 EUR
~~~

This violates ADR-REP-014: calculation uses Decimal before presentation rounding.

## 2. Target invariant

For every executable allocation set:

~~~text
sum(final monetary contributions) == source Money
~~~

The invariant applies to financial-statement projection, comparative projection,
regulatory reporting, signed amounts, currencies with different minor-unit exponents,
and deterministic replay independent of input mapping order.

## 3. Design

~~~text
Money source
    ↓
Decimal raw contributions
    ↓
truncate toward zero at currency minor unit
    ↓
compute exact residual
    ↓
rank fractional remainders
    ↓
distribute residual minor units deterministically
    ↓
Money contributions
~~~

Tie-break rule:

~~~text
largest fractional remainder
then allocation key ascending
~~~

The stable mapping identifier is the allocation key.

## 4. Implementation scope

- src/pyaccountingkit/domain/reporting/monetary_allocation.py
- FinancialStatementEngine._project_source
- RegulatoryReportingService current and comparative projection paths
- unit and Hypothesis property qualification

## 5. Corrective tests

- 0.01 EUR × (0.5, 0.5)
- -0.01 EUR × (0.5, 0.5)
- one whole XAF distributed across three shares
- mapping-order independence
- financial-statement end-to-end conservation
- regulatory-report end-to-end conservation
- Hypothesis property over signed cent amounts and two-way partitions

## 6. Non-goals

LOT-28R does not change Money global construction semantics, F21 sign presentation,
REM-05 closing/opening semantics, or mapping publication/authorization lifecycle.

## 7. Exit criteria

~~~text
[ ] F16 corrective regression passes
[ ] financial projection conserves source amount
[ ] regulatory projection conserves source amount
[ ] comparative projection uses the same policy
[ ] positive / negative small amounts pass
[ ] XAF zero-decimal example passes
[ ] property test proves conservation across generated partitions
[ ] result independent from input mapping order
[ ] Ruff / Mypy / unit / property gates green
[ ] canonical PR CI green
[ ] F16 -> FIXED_UNVERIFIED after merge
~~~

VERIFIED remains reserved for exact-main-SHA evidence and REM-10.
