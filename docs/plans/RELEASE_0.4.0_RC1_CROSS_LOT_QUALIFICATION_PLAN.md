# Release 0.4.0rc1 — Cross-Lot Qualification Plan

## 1. Objective

`0.4.0rc1` is the release-candidate qualification of the complete `0.4.x` line.
It adds no new accounting or financial-analysis capability. Its purpose is to prove that
LOT-18, LOT-19 and LOT-20 remain correct when qualified together on top of the stable
`0.3.0` imports/reporting baseline.

Canonical release chain:

```text
LOT-18 Subledger Foundations
        |
        v
Receivable / Payable
        |
        v
DueItem
        |
        v
LOT-19 Settlement
        |
        v
SettlementAllocation
        |
        v
OpenItem
        |
        +--> AgingSnapshot
        |
        +--> Subledger / normalized GL reconciliation

ReportSnapshot
        |
        v
LOT-20 FinancialAnalysisEngine
        |
        +--> SIG / EBE / EBITDA / CAF
        +--> FRNG / BFRE / BFRHE / BFR / Net Treasury
        +--> ratios
        +--> trends / diagnostics
        |
        v
AnalysisSnapshot
        |
        v
Deterministic replay
```

## 2. Baseline

- Base release: `0.4.0b1`
- Base merge: `b05e11d8353d770a4fadaa23120ed461d1a97c8e`
- Branch: `release/0.4.0-rc1`
- Target version: `0.4.0rc1`
- Stable target after qualification: `0.4.0`

No LOT-21 Public API Facade work belongs in this branch.

## 3. Release invariants

### R1 — No new business capability

The RC may add qualification tests, release tooling and release metadata only.
Production-domain code changes are allowed only if qualification exposes a genuine defect.

### R2 — Subledger never becomes a second ledger

Receivable/payable state, due items, settlements, allocations, open items and aging remain
auxiliary accounting projections. Allocation never creates a second posting path.

### R3 — Settlement allocation remains fail-closed

Over-allocation, duplicate/double allocation through stale state and competing allocation
revisions must continue to be rejected before an inconsistent state can be accepted.

### R4 — Subledger/GL reconciliation remains exact

Open-item balances must reconcile exactly to an explicitly normalized control-account balance.
Entity, subledger, currency and control-account coordinates remain explicit.

### R5 — Financial analysis remains read-only

`ReportSnapshot -> FinancialAnalysisEngine -> AnalysisSnapshot` never mutates accounting or
reporting truth. Missing required inputs remain `INDETERMINATE`; undefined denominators remain
`UNDEFINED`.

### R6 — Replay remains semantic and deterministic

Pinned analytical inputs and definitions reproduce the same analytical checksum and
`AnalysisSnapshot` checksum even when technical snapshot IDs or generation timestamps differ.
Trend projection is deterministic independently of input observation order.

### R7 — Corporate Finance boundary remains closed

NPV/VAN, IRR/TRI, WACC, DCF, valuation and related prospective Corporate Finance concepts remain
outside the Financial Analysis core.

### R8 — Stable 0.3 qualification remains green

The existing `tests/integration/test_0_3_import_reporting_pipeline.py` and
`tests/replay/test_0_3_release_pipeline_replay.py` continue to run in the canonical test matrix.
The RC must not weaken import, reporting, regulatory, replay or posting guarantees from 0.3.

## 4. Required executable evidence

The `0.4.0rc1` release-candidate contract requires these concrete evidence files:

```text
tests/integration/test_0_4_subledger_financial_analysis_pipeline.py
tests/property/test_subledger_settlement_properties.py
tests/concurrency/test_subledger_allocation_concurrency.py
tests/golden/test_subledger_settlement_golden.py
tests/golden/test_financial_analysis_golden.py
tests/replay/test_0_4_release_pipeline_replay.py
tests/contract/test_corporate_finance_boundary.py
tests/integration/test_0_3_import_reporting_pipeline.py
tests/replay/test_0_3_release_pipeline_replay.py
```

The release qualifier must fail closed if required RC evidence is missing.

## 5. Qualification scenario

### Phase A — 0.4 cross-lot integration

The integration scenario must prove both AR and AP paths:

1. create an accounting-effective Receivable/Payable;
2. create a DueItem;
3. create an accounting-effective Settlement;
4. allocate only part of the settlement/item;
5. project the remaining exposure to OpenItem;
6. project the same exposure into Aging;
7. reconcile the resulting open balance exactly to the explicit normalized GL balance.

In the same release-level scenario, run the LOT-20 golden analysis path and prove:

- EBE and EBITDA remain distinct values;
- CAF is calculated;
- FRNG/BFR/Net Treasury reconcile;
- ratios remain available;
- an `AnalysisSnapshot` is sealed;
- running analysis does not mutate subledger state.

### Phase B — Replay qualification

Run fresh equivalent executions and prove:

- Aging checksum is deterministic;
- reconciliation result is identical and matched;
- financial-analysis result checksum is deterministic;
- `AnalysisSnapshot` checksum is deterministic while technical IDs/timestamps may differ;
- trend checksum is deterministic even if equivalent observations are supplied in another order.

### Phase C — RC gate contract

Strengthen `scripts/qualify_release.py --release-candidate` to require version-specific evidence
for `0.4.0rc1` in addition to non-empty integration/golden/replay/concurrency suites.

### Phase D — Release metadata

Align:

- `pyproject.toml`;
- `PUBLIC_API_MANIFEST.json`;
- `PUBLIC_ERROR_CODES.json`;
- `ADAPTER_CONTRACT_MANIFEST.json`;
- `REGULATORY_COMPATIBILITY_MATRIX.json`;
- `README.md`;
- `CHANGELOG.md`.

## 6. Required qualification matrix

```text
[ ] repository hygiene
[ ] architecture safety
[ ] manifest coherence
[ ] CI workflow contract
[ ] Ruff lint
[ ] Ruff format
[ ] strict mypy
[ ] wheel/sdist package verification
[ ] unit suite
[ ] property suite
[ ] contract suite
[ ] integration suite
[ ] golden suite
[ ] replay suite
[ ] concurrency suite
[ ] Python 3.11 CI
[ ] Python 3.12 CI
[ ] Python 3.13 CI
[ ] Security dependency audit
[ ] Security static analysis
```

## 7. Exit criterion

`0.4.0rc1` is qualified when the complete LOT-18/19/20 line can be executed and replayed through
its release evidence without adding business functionality, without weakening the stable 0.3
baseline, and with canonical CI, package and Security gates green.

After this RC is merged and remains green, the stable `0.4.0` promotion must contain zero new
business code: only version/manifests/changelog/release-note alignment and final qualification.
