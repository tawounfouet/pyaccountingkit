# 03 — CFA FRA Behavioral Baseline

## Baseline identity

```text
oracle: CFA FRA Django MVP Sprint 7
resource tree SHA: 07d4880534d2e2239e19fd4ef4139de70b56773a
manifest version: 0.8.0
capture purpose: LOT-25 / 0.6.0a1
```

This document records behavior to preserve or consciously diverge from. It is not a statement
that every CFA FRA MVP convention is universally correct.

## Accounting workflow

Canonical oracle workflow:

```text
DRAFT -> VALIDATED -> POSTED -> REVERSED
```

Baseline rules:

- posted/reversed entries are immutable;
- closed periods reject validation/posting;
- at least two lines are required;
- debit and credit totals must be exactly equal;
- a zero-total entry is invalid;
- direct DRAFT→POSTED is rejected;
- audit evidence exists for create, validate, post and reverse.

PyAccountingKit already implements the same core lifecycle semantically. Identity values,
timestamps and presentation strings are excluded from exact parity unless explicitly pinned.

## Reversal

Baseline:

- only POSTED entries may be reversed;
- a second reversal is rejected;
- reversal period must be OPEN and entity-consistent;
- reversal posting date must belong to the selected period;
- every line swaps debit and credit;
- reversal is itself validated and posted;
- original becomes REVERSED;
- original/reversal linkage remains traceable.

Intentional non-portable oracle convention:

```text
REV-<entry_number>
```

PyAccountingKit keeps reversal semantics but does not require this literal numbering rule.

## FEC ingestion

Baseline source contract is the French 18-column FEC text shape.

Evidence guarantees:

- original file metadata and SHA-256;
- raw row preservation;
- row-level SHA-256;
- source line number;
- no silent row drop;
- blocking validation findings remain distinct from warnings;
- duplicate row hash is a warning, not automatic economic deduplication;
- every normalized entry and the full source are balanced;
- mapping is explicit before executable import;
- final import is atomic;
- failure rolls back all ledger effects;
- ledger lines retain source lineage.

Known intentional generalizations in PyAccountingKit:

- source grouping is strategy-driven rather than hard-coded globally;
- `JOD -> ADJUSTING` is not universal;
- trusted already-posted history is represented explicitly rather than becoming a generic
  direct-post bypass;
- account/journal creation cannot silently become a normative mapping decision.

## Ledger and balance

Only posted accounting contributes. REVERSED originals remain in the historical ledger and
are economically offset by their posted reversal.

Movement ordering must be deterministic.

The oracle's signed balance convention is:

```text
signed_balance = debit - credit
```

Presentation:

```text
signed >= 0 -> debit balance
signed < 0  -> credit balance = abs(signed)
```

Trial-balance variants:

| Variant | Included entry types |
|---|---|
| BEFORE_ADJUSTMENTS | OPENING, NORMAL, REVERSAL |
| ADJUSTED | OPENING, NORMAL, ADJUSTING, REVERSAL |
| POST_CLOSING | OPENING, NORMAL, ADJUSTING, CLOSING, REVERSAL |

Zero-balance accounts may be hidden in presentation, but their accounting contribution must
not disappear from source evidence.

## Financial statements

Sprint 6 is an executable functional oracle for a non-regulatory internal presentation model:

```text
CFA_FRA_MVP
```

Behavior to preserve where mapped to PyAccountingKit:

- income statement uses NORMAL + ADJUSTING + REVERSAL and excludes OPENING/CLOSING;
- balance sheet uses OPENING + NORMAL + ADJUSTING + REVERSAL;
- current-period result is included so assets equal liabilities+equity;
- cash flow prioritizes explicit `cash_flow_tag`, then optional inference;
- cash reconciliation gap is visible, never silently discarded;
- mapping coverage exposes non-zero unmapped accounts;
- drill-down reaches contributing accounts, ledger movements and source entries;
- N/N-1 comparison is deterministic when a prior period is available.

The code-based category inference from Sprint 6 is migration assistance, not regulatory truth.

## Ratios

Sprint 6 exposes:

```text
NET_MARGIN
ROA
CURRENT_RATIO
DEBT_TO_ASSETS
EQUITY_RATIO
CFO_TO_REVENUE
ASSET_TURNOVER
```

These are analytical, not regulatory. LOT-25 uses them only as golden behavior where equivalent
definitions exist in PyAccountingKit's versioned analysis definitions.

## Regulatory output boundary

Sprint 7 adds deterministic mapping, snapshots and export integrity, but explicitly does not
hard-code an official SYSCOHADA/IFRS nomenclature.

Therefore:

- traceability and deterministic snapshot/export behavior may inform LOT-25 evidence;
- regulatory production claims are prohibited until LOT-27 qualification.

## Controls

At minimum the oracle makes visible:

- non-zero source statement lines without target mapping;
- required target lines without mapping;
- balance equation failure;
- cash reconciliation failure.

Warnings do not become silent success.

## Closing baseline gap

The bundled Sprint 7 resource contains closing models and an intended closing domain, but its
README explicitly identifies **Sprint 8 — Regulatory Controls & Closing Package** as the next
step. The LOT-25 baseline therefore records closing as a coverage gap instead of fabricating
legacy behavior.

PyAccountingKit's own closing engine remains qualified independently; CFA FRA closing parity
will become executable only from a trustworthy legacy fixture/source.

## Intentional divergence categories

Allowed categories are:

```text
BUG_FIX
GENERALIZATION
REGULATORY_CORRECTION
PORTABILITY_CHANGE
SAFETY_HARDENING
API_REDESIGN
```

No divergence is accepted merely because PyAccountingKit returns a different value. It must be
registered with evidence and migration impact.

## Baseline conclusion

CFA FRA is the oracle for **behavioral evidence**, not implementation reuse and not regulatory
authority.

```text
Keep the behavior.
Rewrite the implementation.
Preserve the evidence.
Never dual-write accounting mutations.
Never hide a divergence.
```
