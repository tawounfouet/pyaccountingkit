# 02 — CFA FRA Golden Scenario Inventory

Oracle tree: `07d4880534d2e2239e19fd4ef4139de70b56773a`.

## Scenario catalog

| ID | Category | Oracle evidence | Expected parity | LOT-25 status |
|---|---|---|---|---|
| CFA-POST-001 | posting | Sprint 3 workflow test | DRAFT→VALIDATED→POSTED, exact 1000/1000 balance | executable |
| CFA-POST-002 | posting rejection | Sprint 3 workflow test | DRAFT→POSTED rejected, state unchanged | executable |
| CFA-REV-001 | reversal | Sprint 3 workflow test | inverse lines, reversal POSTED, original REVERSED | executable |
| CFA-FEC-001 | FEC parser | Sprint 4 | 18-column parsing, encoding fallback, raw preservation | executable |
| CFA-FEC-002 | FEC validation | Sprint 4 | blocking findings vs duplicate/currency warnings | executable |
| CFA-FEC-003 | FEC grouping | Sprint 4 | JAN special grouping; journal/date/number grouping | executable |
| CFA-FEC-004 | FEC totals | Sprint 4 | per-entry and global debit=credit | executable |
| CFA-FEC-005 | FEC lineage | Sprint 4 | raw line→journal line traceability preserved | executable |
| CFA-LED-001 | journal | Sprint 5 | only posted/reversed accounting contributes | executable |
| CFA-LED-002 | general ledger | Sprint 5 | deterministic movement order + opening/running/final balance | executable |
| CFA-TB-001 | trial balance | Sprint 5 | BEFORE_ADJUSTMENTS semantics | executable |
| CFA-TB-002 | trial balance | Sprint 5 | ADJUSTED semantics | executable |
| CFA-TB-003 | trial balance | Sprint 5 | POST_CLOSING semantics | executable |
| CFA-STMT-001 | income statement | Sprint 6 | revenue-expense=net result | executable |
| CFA-STMT-002 | balance sheet | Sprint 6 | assets=liabilities+equity including current result | executable |
| CFA-STMT-003 | cash flow | Sprint 6 | opening + CFO + CFI + CFF + unclassified = theoretical close | executable |
| CFA-STMT-004 | mapping coverage | Sprint 6 | non-zero unmapped accounts are visible | executable |
| CFA-ANA-001 | ratios | Sprint 6 | NET_MARGIN / ROA / CURRENT_RATIO etc. | executable |
| CFA-REG-001 | regulatory mapping | Sprint 7 | deterministic exact/metadata/role mapping priority | evidence only for LOT-25 |
| CFA-REG-002 | report snapshot | Sprint 7 | JSON-serialisable trace + SHA-256 exports | evidence only; certification LOT-27 |
| CFA-CTRL-001 | controls | Sprint 7 | unmapped required lines, balance and cash controls | executable where fixture exists |
| CFA-CLOSE-001 | closing | Sprint 8 target | blockers / closing entry / post-close / opening | **gap: no complete executable oracle** |

## First committed fixture pack

LOT-25 starts with three normalized fixture families that can be grounded directly in the
bundled oracle documentation/tests without running the legacy code at PyAccountingKit runtime.

### CFA-POST-001 / CFA-REV-001

Oracle values:

```text
organization currency: XAF
journal: JOD
posting date: 2025-01-15
cash 57110000      Dr 1000
capital 10110000   Cr 1000
```

Reversal date: `2025-01-20`.

Normalized expected semantics:

- validated state before posting;
- posted state after posting;
- exact debit=credit=1000;
- reversal line amounts swapped;
- original state becomes REVERSED;
- reversal is POSTED and links to original.

The literal legacy `REV-` numbering convention is excluded from semantic parity.

### CFA-TB-001..003

Oracle Sprint 5 example:

```text
Opening:
Cash      Dr 1 000
Capital   Cr 1 000

Normal:
Rent      Dr   200
Cash      Cr   200

Adjusting:
Rent      Dr    50
Accrued   Cr    50

Closing:
Capital   Dr   250
Rent      Cr   250
```

Expected balances:

```text
BEFORE_ADJUSTMENTS
Cash       Dr 800
Rent       Dr 200
Capital    Cr 1000

ADJUSTED
Cash       Dr 800
Rent       Dr 250
Capital    Cr 1000
Accrued    Cr 50

POST_CLOSING
Cash       Dr 800
Capital    Cr 750
Accrued    Cr 50
Rent       0
```

### CFA-FEC baseline

The normalized fixture schema must preserve the 18 FEC columns, source line number, row hash,
normalized entry key, findings, debit/credit totals and lineage. Initial assets will use
synthetic but oracle-conformant lines; real production data is neither required nor committed.

## Golden update discipline

A fixture update is acceptable only when one of these is true:

1. the bundled oracle snapshot changes intentionally;
2. a documented intentional divergence is approved;
3. a fixture itself is proven incorrect.

Every semantic change requires review because golden assets are release evidence.
