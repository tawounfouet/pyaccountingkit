# LOT-20 — Financial Analysis — Implementation Plan

> Target line: `0.4.0b1 -> 0.4.0`
>
> Baseline: merged LOT-19 / `0.4.0a2` (`53dbdf63ea30f9b9699a665d05b5c50644ef25e2`)

## Objective

Implement a deterministic, read-only financial-analysis bounded context that consumes sealed accounting/reporting facts and produces versioned analytical outputs without mutating accounting truth.

```text
ReportSnapshot / TrialBalance
        |
        v
FinancialAnalysisSource
        |
        v
AnalysisDefinitionSet
        |
        +--> FinancialIndicatorDefinition
        +--> FinancialRatioDefinition
        +--> FunctionalBalanceDefinition
        |
        v
FinancialAnalysisEngine
        |
        +--> SIG / EBE / EBITDA / CAF
        +--> FRNG / BFRE / BFRHE / BFR / Net Treasury
        +--> historical ratios
        +--> trends
        +--> diagnostics
        |
        v
CalculationTrace
        |
        v
AnalysisSnapshot
```

## Non-negotiable boundaries

- Financial analysis is read-only.
- `AnalysisSnapshot` is derived evidence, never accounting truth.
- `ReportSnapshot` / `TrialBalance` inputs are never mutated.
- Missing required input => `INDETERMINATE`.
- Mathematically undefined ratio/denominator => `UNDEFINED`, never silent zero, Infinity or NaN.
- `EBE` and `EBITDA` are separate versioned definitions.
- Indicator/ratio semantics are definition-driven, not inferred from account-number prefixes.
- Published analysis rejects stale source by default unless historical replay is explicit.
- No arbitrary `eval()` / executable code in formulas.
- NPV/VAN, IRR/TRI, WACC, DCF, valuation, forecast cash flows, market multiples, scenario/Monte-Carlo and financing optimization remain outside the core.

## Scope

### 1. Source model

Implement:

- `FinancialAnalysisSourceType`
- `FinancialAnalysisSourceFreshness`
- immutable `FinancialAnalysisSource`
- adapters/factories for `ReportSnapshot` and verified `TrialBalance`
- source checksum and entity/currency/period provenance

### 2. Definitions

Implement:

- `FinancialIndicatorDefinition`
- `FinancialRatioDefinition`
- `AnalysisDefinitionSet`
- definition lifecycle/status
- units/categories
- indicator dependencies
- versioned deterministic formulas
- dependency graph validation / cycle rejection

Initial deterministic DSL:

```text
ADD
SUBTRACT
MULTIPLY
DIVIDE
SUM
NEGATE
ABS
MIN
MAX
COALESCE
IF_DEFINED
```

No arbitrary Python execution.

### 3. Value semantics

Implement explicit analytical outcomes:

```text
CALCULATED
NOT_APPLICABLE
UNDEFINED
INDETERMINATE
ERROR
```

The result model must preserve:

- definition id/version
- value/unit
- dependency values
- source refs
- status
- calculation trace

### 4. Financial analysis engine

Implement a pure deterministic engine able to calculate:

- SIG chains
- EBE
- EBITDA as a distinct definition
- CAF (definition-driven; additive/subtractive/custom semantics remain explicit)
- functional balance
- FRNG
- BFRE
- BFRHE
- BFR
- Net Treasury
- accounting-based historical ratios

The engine consumes values supplied through explicit source bindings. It never guesses business semantics from account codes.

### 5. Ratios

Implement:

- versioned ratio definitions
- numerator/denominator references
- scale (`1`, `100`, `360`, `365`, custom Decimal)
- day-count policy metadata where applicable
- zero denominator policy, defaulting to `UNDEFINED`
- missing required numerator/denominator => `INDETERMINATE`

### 6. Functional balance and working capital

Implement an explicit `FunctionalBalanceDefinition` and derived result.

Qualification identities include:

```text
FRNG = Stable Resources - Stable Uses
BFRE = Operating Current Assets - Operating Current Liabilities
BFRHE = Non-operating Current Assets - Non-operating Current Liabilities
BFR = BFRE + BFRHE
Net Treasury = FRNG - BFR
Net Treasury = Cash Assets - Cash Liabilities
```

If both Net Treasury methods are configured, reconciliation must be explicit.

### 7. Trends and diagnostics

Implement:

- period observations
- N/N-1 comparison
- multi-period trends
- deterministic direction (`UP`, `DOWN`, `STABLE`, `INDETERMINATE`)
- diagnostics based only on explicit versioned rules/policies

No universal hard-coded judgment such as `CURRENT_RATIO >= X => GOOD`.

### 8. AnalysisSnapshot and traceability

Implement immutable checksummed:

- `CalculationTrace`
- `AnalysisSnapshot`

Snapshot must pin at least:

- entity
- source type/ref/checksum/freshness
- definition-set id/version/checksum
- indicator/ratio result checksums
- as-of/period
- generated-at technical metadata separate from semantic checksum where appropriate

Replay of the same pinned semantic inputs must reproduce the same semantic checksum.

### 9. Corporate Finance boundary guard

Add an executable architecture/contract test rejecting core introduction of concepts such as:

```text
NPV / VAN
IRR / TRI
WACC
DCF
valuation
future cash-flow forecasting
market multiples
Monte Carlo
investment appraisal
financing optimization
```

The guard must target domain/API vocabulary intentionally and avoid false positives from documentation that explains the boundary.

## Error taxonomy

Add stable analysis errors for at least:

- invalid analysis source
- stale source
- invalid indicator/ratio definition
- dependency cycle
- invalid definition set
- unsupported analytical operation
- invalid functional balance
- invalid analysis snapshot

Mathematical undefinedness and missing business input are normally represented by value status, not exceptions.

## Qualification plan

### Unit

- source construction and provenance
- versioned definitions
- dependency-cycle rejection
- formula operations
- missing input -> `INDETERMINATE`
- division by zero -> `UNDEFINED`
- `EBE != EBITDA`
- functional-balance identities
- snapshot immutability/checksum

### Property

- ratio never emits NaN/Infinity
- working-capital identities hold across generated Decimal inputs
- deterministic formula/replay behavior

### Golden

At least one historical accounting-analysis scenario covering:

```text
ReportSnapshot
  -> SIG / EBE / EBITDA / CAF
  -> functional balance
  -> FRNG / BFR / Net Treasury
  -> ratios
  -> AnalysisSnapshot
```

### Replay

Same pinned accounting source + same definitions => same semantic result and snapshot checksum despite different technical generation times/IDs where allowed.

### Architecture

- no mutation path into ledger/reporting source
- no framework dependency in domain
- Corporate Finance boundary guard green

## Release progression

```text
0.4.0a1  LOT-18 Subledger Foundations
0.4.0a2  LOT-19 Settlements / Matching / Aging
0.4.0b1  LOT-20 Financial Analysis
0.4.0rc1 cross-lot 0.4 qualification
0.4.0    stable
```

## Definition of Done

- [x] analysis is read-only
- [x] source evidence is explicit and checksummed
- [x] definitions are versioned
- [x] dependency graph is acyclic
- [x] missing required input => `INDETERMINATE`
- [x] undefined denominator => `UNDEFINED`
- [x] no NaN / Infinity semantics
- [x] EBE and EBITDA remain separate definitions
- [x] SIG/CAF/working-capital mechanics are definition-driven
- [x] FRNG/BFR/Net Treasury controls green
- [x] historical ratios deterministic
- [x] trends replay deterministically
- [x] AnalysisSnapshot immutable/checksummed
- [x] Corporate Finance concepts remain outside core
- [x] unit/property/golden/replay/architecture qualification green
- [x] Ruff/format/mypy green
- [x] Python 3.11/3.12/3.13 green
- [x] package qualification green
- [x] Security green
- [x] manifests/docs/version aligned before merge

## Qualification evidence

Promotion candidate `0.4.0b1` is based on LOT-20 implementation commit
`c8199cda3d39666df4ff8a80709989cc72eae030` plus release-metadata alignment.

Pre-promotion qualification on that implementation commit:

- canonical Quality gates: green, including Ruff, Ruff format and strict mypy;
- Python 3.11 / 3.12 / 3.13 accounting qualification suites: green;
- package qualification: green;
- canonical CI gate: green;
- Security workflow: green;
- LOT-20 unit/property/golden/replay and Corporate Finance boundary guard: green.

The release-metadata commit must pass the same CI/Security gates before PR merge.
