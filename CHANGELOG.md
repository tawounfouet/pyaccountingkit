# Changelog

All notable changes to pyaccountingkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-09-16

### Stable release
- Promotes the fully qualified `0.3.0rc1` imports/reporting behavior without adding new
  accounting, import, reporting or regulatory semantics.
- Freezes the `0.3.x` milestone around the composed source-to-evidence path:
  FEC source evidence -> explicit `ImportPlan` -> canonical `PostingOrchestrator` -> posted
  ledger -> `TrialBalance` -> financial statements -> published `ReportSnapshot` -> regulatory
  projection -> validation -> canonical export -> checksummed evidence.
- Retains mandatory cross-lot integration, golden, replay and concurrency qualification in the
  canonical Python 3.11 / 3.12 / 3.13 CI matrix.
- Keeps package stability separate from public API freeze: the Python API remains pre-1.0 and
  intentionally unfrozen.

### Qualification
- FEC contract, rollback, idempotency and concurrency gates remain green.
- Financial-statement golden qualification remains green.
- Regulatory mapping safety and exact-snapshot execution remain green.
- Source-to-evidence report replay remains deterministic.
- Package wheel/sdist verification, dependency audit and Bandit static analysis remain required
  stable-release gates.
- Stable `0.3.0` preserves the same compatibility boundary as the RC: PCG/FEC cross-lot software
  mechanics are qualified, while exhaustive statutory templates, DGFiP filing certification,
  legal certification and regulator-submission compliance are not claimed. SYSCOHADA remains
  qualified through LOT-17 XOF golden/replay scenarios rather than the PCG/FEC ingestion path.

## [0.3.0rc1] - 2026-09-16

### Added
- Executable cross-lot integration qualification from immutable French FEC source evidence
  through `FECAdapter`, explicit `ImportPlan`, canonical `PostingOrchestrator`, posted ledger,
  `TrialBalance`, `FinancialStatementEngine`, published `ReportSnapshot`, regulatory projection,
  validation, canonical JSON export and `ReportEvidenceBundle`.
- Shared release-0.3 qualification pipeline used by integration and replay tests so the same
  production components are exercised across both gates.
- Source-to-evidence replay qualification proving stable semantic identities/checksums across
  fresh executions while allowing technical timestamps and generated export/evidence IDs to
  differ.
- Same-store replay qualification proving the same reviewed import source does not create a
  second posted accounting effect or duplicate posting audit event.
- Explicit `--release-candidate` mode in `scripts/qualify_release.py`.

### Changed
- Canonical CI now executes `tests/integration` together with unit, property, contract, golden,
  replay and concurrency suites on Python 3.11, 3.12 and 3.13.
- The executable CI contract now fails if cross-lot integration is removed from the canonical
  matrix.
- Release-candidate qualification fails closed when integration, golden, replay or concurrency
  suites are empty and forbids skipping tests or package verification.
- Root manifests and documentation are aligned to the `0.3.0rc1` package baseline.
- The regulatory compatibility matrix distinguishes the PCG/FEC source-to-evidence RC
  qualification from SYSCOHADA LOT-17 golden/replay qualification.

### Qualification
- The composed FEC → ledger → Trial Balance → financial statements → regulatory reporting →
  evidence path passes the canonical CI matrix on Python 3.11, 3.12 and 3.13.
- Package qualification and Security gates are required before promotion of the release
  candidate.
- The RC proves composition and deterministic replay of the existing 0.3.x capabilities; it
  does not introduce LOT-18/0.4.x domain scope or a second posting engine.
- The PCG/FEC scenario qualifies software mechanics and evidence lineage only. It does not claim
  exhaustive statutory templates, DGFiP filing certification, legal certification or
  regulator-submission compliance.

## [0.3.0b2] - 2026-09-16

### Added
- Regulatory Reporting read-side (LOT-17) built exclusively from published immutable
  `ReportSnapshot` inputs; no regulatory component writes back to the ledger.
- Versioned/effective-dated `RegulatoryReportingProfile` pinning framework, jurisdiction,
  edition, reference snapshot id/checksum, financial-statement definitions, mapping set and
  export definitions.
- `ReferenceReportingModel` with deterministic hierarchy, official reporting nodes and
  explicitly non-executable account hints requiring human validation where declared.
- Exact-coordinate `ReferenceReportingModelProviderProtocol` and in-memory reference adapter;
  snapshot/framework/edition/model lookup fails closed instead of resolving an implicit
  `latest` model.
- Versioned `RegulatoryMappingSet` and `RegulatoryStatementMapping` lifecycle with explicit
  provenance, allocation and candidate/review/validated states.
- Immutable `RegulatoryReport` and deterministic `RegulatoryValidationReport` including
  blocking rules for unmapped required nodes, human-review preservation and reference-hint
  execution safety.
- `RegulatoryExportDefinition`, canonical JSON renderer, checksummed export artifact and
  checksummed `ReportEvidenceBundle` sealing the report, validation and export chain.
- Deterministic `ReferenceUpgradePlan` describing model changes, impacted mappings and
  human-review escalation without rewriting historical execution coordinates.
- PCG/EUR and SYSCOHADA/XOF regulatory golden scenarios plus end-to-end replay qualification.
- Stable regulatory reporting error codes and adapter-contract metadata.

### Changed
- `ReportSnapshot` now seals `as_of` in its checksum so effective-dated regulatory execution
  can be replayed against the exact historical accounting date.
- Regulatory compatibility metadata now distinguishes exact-snapshot regulatory reporting
  mechanics from any claim of statutory filing or authority-submission compliance.

### Qualification
- Regulatory report, validation, canonical export payload and evidence checksums replay
  deterministically from the same pinned inputs even when export timestamps and generated
  technical IDs differ.
- Candidate mappings and `REFERENCE_HINT` metadata cannot execute silently as validated
  mappings; human-validation requirements survive the projection boundary.
- PCG and SYSCOHADA golden scenarios are qualified as reference reporting projections, not as
  certification of exhaustive official templates, legal filing compliance or regulator
  submission readiness.
- CI qualifies unit, property, contract, golden, replay and concurrency suites on Python 3.11,
  3.12 and 3.13; package and Security gates are part of the release qualification.

## [0.3.0b1] - 2026-09-15

### Added
- Generic Financial Statements Engine (LOT-16) built strictly as a projection from verified
  `TrialBalance` snapshots.
- Versioned/effective-dated `FinancialStatementDefinition` and immutable
  `StatementLineDefinition` models.
- Restricted deterministic formula DSL with dependency-graph validation and cycle rejection.
- Versioned `StatementMappingSet` and explicit `StatementAccountMapping` lifecycle separating
  candidate/review mappings from executable validated mappings.
- Decimal one-to-many account allocation, balance-side mapping, comparatives and statement-line
  drill-down to source trial-balance contributions.
- Balance Sheet equation control and Cash Flow reconciliation control anchors.
- Immutable `ReportSnapshot` with definition, mapping and source checksums plus stale-source
  detection.
- Stable reporting error codes for invalid definitions, formula cycles, mappings, sources and
  failed controls.

### Changed
- Trial-balance snapshots may now pin `accounting_entity_id` and expose their actual currency.
- `TrialBalanceQuery` preserves stable company-account IDs separately from business account
  codes, strengthening `CompanyAccount -> TrialBalance -> StatementLine` lineage.
- Reporting execution fails closed on cross-entity sources/mappings, non-effective definitions,
  non-executable mappings and unmapped non-zero accounts unless explicitly configured otherwise.

### Qualification
- Financial statements remain read-side projections and introduce no ledger mutation path.
- Candidate mappings cannot execute as active mappings.
- Formula cycles are rejected before evaluation.
- Balance Sheet and Cash Flow controls, comparative projection, account identity, snapshot
  determinism and immutability are covered by LOT-16 qualification tests.
- This milestone does not claim statutory PCG/SYSCOHADA statement templates or regulatory
  exporter compliance; those remain LOT-17 scope.

## [0.3.0a2] - 2026-09-15

### Added
- Specialized French FEC adapter (LOT-15) over the source-neutral LOT-14 import contracts.
- Canonical 18-column FEC schema, strict parser and SHA-256 source-evidence verification.
- Lossless raw FEC line preservation including source line numbers and row checksums.
- FEC normalization using `JournalCode:EcritureNum` as source-entry identity.
- Preservation of `CompAuxNum` / `CompAuxLib`, `EcritureLet` / `DateLet`, document,
  validation-date and foreign-currency metadata without concatenating auxiliary identifiers to
  `CompteNum`.
- FEC-specific structural, amount, date, balance, currency and duplicate-candidate controls.
- FEC discovery report and post-import reconciliation report.
- Explicit trust guard for `TRUSTED_POSTED_HISTORY_IMPORT`.
- Import transaction modes: `ALL_OR_NOTHING`, `PER_ITEM` and `CHUNKED_ATOMIC`.
- Atomic `PostingOrchestrator.post_many()` path used by imports without introducing a second
  posting engine.

### Changed
- Generic parser contracts now receive source bytes explicitly alongside immutable
  `SourceArtifact` evidence.
- Imported entry IDs derive from stable source identity rather than transient batch identity,
  preventing duplicate ledger effects when the same source is acquired in another batch.
- FEC `Debit` / `Credit` always use the configured accounting currency; `Idevise` and
  `Montantdevise` remain source metadata and do not redefine the ledger currency.
- Adapter and regulatory manifests now expose the LOT-15 FEC qualification boundary.

### Qualification
- Multi-entry rollback is qualified against the in-memory transactional UoW.
- Duplicate-row detection is warning-only and never removes source records.
- Debit/credit source totals and imported totals are reconcilable through the FEC report model.

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
