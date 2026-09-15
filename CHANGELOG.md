# Changelog

All notable changes to pyaccountingkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0a1] - 2026-09-15

### Added
- Source-format-neutral Generic Accounting Import Engine foundation (LOT-14).
- Immutable `SourceArtifact` with SHA-256 evidence and scoped source fingerprinting.
- Immutable `RawImportRecord` preservation with deterministic row checksums.
- Generic `NormalizedImportRecord`, `SourceEntryKey` and deterministic entry grouping.
- Explicit fail-closed account and journal mapping decisions without silent creation.
- `AccountingImportBatch` lifecycle with guarded state transitions and execution modes.
- Typed `ImportIssue` / `ImportValidationReport` structures.
- Deterministic checksummed `ImportPlan`, stale-plan rejection and import checkpoints.
- Source-neutral parser, normalizer and period-resolution ports.
- Dry-run and import execution service delegating accounting mutations to the canonical
  `PostingOrchestrator`.

### Changed
- Import-specific errors now have stable machine-readable codes in the public error manifest.
- Adapter contract metadata documents the generic import extension boundary.
- Regulatory compatibility metadata explicitly separates the generic import core from the
  future FEC adapter in LOT-15.

### Security
- Import source identity uses SHA-256 evidence; no format-specific source data is interpreted
  as trusted accounting semantics by the generic core.

## [0.2.0b2] - 2026-09-15

### Added
- Canonical `AccountingEntity` isolation guard and cross-entity adversarial tests.
- Versioned `CompanyChartResolverProtocol` and `AccountRoleResolverProtocol`.
- `ProposalPostingOrchestrator` as the canonical policy/proposal-to-ledger path.
- Immutable `AccountingExecutionTrace` pinning proposal, policy, chart and snapshot coordinates.
- Replay qualification for policy versions and historical chart resolution.
- Competing Unit-of-Work concurrency qualification and idempotency conflict coverage.
- Full qualification mode covering golden, replay and concurrency suites when applicable.

### Changed
- Posting now resolves the operational company chart by entity and accounting date.
- Posting audit, outbox and idempotency state share the accounting Unit of Work.
- In-memory transactions use detached working state and delta merge instead of global snapshot restore.
- `JournalEntryProposal` is balanced and single-currency by construction.
- Policy-set execution distinguishes current execution from explicit historical replay.
- CI qualifies unit, property, contract, golden, replay and concurrency suites on Python 3.11, 3.12 and 3.13.
- Release manifests now describe beta API status, stable error codes, adapter contracts and regulatory qualification scope.

### Fixed
- Missing policy applicability context no longer matches silently.
- Cross-entity chart/account, journal/period and policy-context combinations fail closed.
- Zero/zero journal lines are rejected at construction.
- Non-posted reversals raise `EntryNotPostedError` rather than lookup errors.
- Account-role resolution no longer ignores entity/date/chart version.
- Measurement adjustments enforce `delta == new_amount - previous_amount`.
- Straight-line depreciation enforces residual, cumulative, period and final-allocation bounds.
- Security gate findings from predictable random IDs, runtime assertions and the targeted Bandit false positive were resolved.

## [0.2.0b1] - 2026-09-15

### Added
- Accounting policy sets, applicability, resolution and recognition foundations (LOT-12).
- Measurement, depreciation, impairment, inventory, accrual/provision foundations and journal-entry proposals (LOT-13).

## [0.2.0a1] - 2026-09-15

### Added
- Versioned regulatory reference and company-chart foundations, including reference snapshots and regulatory bindings.

## [0.1.0] - 2026-09-15

### Added
- Double-entry accounting core: money, entities, periods, journals, company accounts, journal entries, persistence ports, posting/reversal, reporting, controls, audit and closing foundations.

## [0.0.1] - 2026-09-15

### Added
- Initial project scaffolding.