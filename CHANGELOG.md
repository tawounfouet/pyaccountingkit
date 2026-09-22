# Changelog

All notable changes to pyaccountingkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0rc1] - 2026-09-23

### Release Candidate
- Qualifies LOT-21 through LOT-24 together with no new accounting-domain capability.
- Requires the framework-neutral public API and adapter contract v1 evidence.
- Requires both Django/PostgreSQL 16 and SQLAlchemy/PostgreSQL 16 Production gates.
- Retains stable 0.4 subledger/financial-analysis and stable 0.3 import/reporting/replay
  qualification.
- Adds version-specific fail-closed RC evidence to `scripts/qualify_release.py`.
- Makes the deterministic public API manifest explicitly release-aware for prerelease,
  release-candidate and pre-1.0 stable states.

### Exit Criterion
- Stable `0.5.0` promotion may contain release metadata/documentation changes only, unless
  this RC exposes a genuine defect.


## [0.5.0b2] - 2026-09-23

### Added
- LOT-24 SQLAlchemy 2.x / PostgreSQL Production adapter with canonical schema parity to the
  Django adapter.
- `SessionUnitOfWork` and `SQLAlchemyUnitOfWorkFactory` implementing adapter contract v1.
- SQLAlchemy repositories for journals, accounting periods and journal entries plus
  transactional audit, idempotency and outbox sinks.
- Packaged Alembic migration lineage with fresh `0001_initial` qualification.
- Declarative metadata-to-migrated-database coherence check.
- Canonical SQLAlchemy/PostgreSQL 16 CI gate covering repository round-trip, commit/rollback,
  optimistic conflicts, idempotency races, double reversal and posting-vs-close serialization.
- Published `sqlalchemy` optional extra with SQLAlchemy, Alembic and psycopg.

### Changed
- Canonical CI now requires both Django/PostgreSQL and SQLAlchemy/PostgreSQL Production gates.
- Reversal self-referential PostgreSQL foreign keys are deferred inside the SQLAlchemy schema so
  the existing atomic reversal contract can update the source entry and insert its reversal in
  one transaction.
- Adapter contract evidence now declares both `django_postgresql` and
  `sqlalchemy_postgresql` Production-qualified on contract v1.

### Boundaries
- LOT-24 introduces no accounting-domain semantics and no SQLAlchemy-specific public DTOs.
- ORM objects remain confined to adapter modules.
- Stable `0.5.0` still requires transverse LOT-21 through LOT-24 release qualification.

## [0.5.0b1] - 2026-09-23

### Added
- LOT-23 Django/PostgreSQL Production adapter with migrations, repositories and
  `DjangoUnitOfWork`.
- PostgreSQL 16 qualification for fresh migrations, repository round-trips, rollback,
  audit/outbox/idempotency atomicity, optimistic conflicts and critical concurrency races.
- Published `django` optional extra.

### Changed
- Adapter contract evidence declares `django_postgresql` Production-qualified on contract v1.
- Canonical CI includes the real Django/PostgreSQL gate.


## [0.5.0a2] - 2026-09-18

### Added
- LOT-22 versioned adapter-author extension API under `pyaccountingkit.public.protocols`.
- Adapter contract v1 via `AdapterContractVersion`, `ADAPTER_CONTRACT_VERSION` and explicit
  supported-version declarations.
- Public extension contracts for Unit of Work factories, accounting-reference providers,
  regulatory renderers and regulatory exporters.
- Immutable runtime capability discovery that checks optional Django/SQLAlchemy availability
  without importing either framework and reports packaged `py.typed` support.
- Typed `AdapterContractMismatchError` and `OptionalDependencyMissingError`.
- Deterministic generators with `--check` for `PUBLIC_API_MANIFEST.json`,
  `PUBLIC_ERROR_CODES.json` and `ADAPTER_CONTRACT_MANIFEST.json`.
- Canonical Quality gates that fail closed on generated-manifest drift.

### Changed
- Root compatibility manifests are promoted to `0.5.0a2`.
- `PUBLIC_API_MANIFEST.json` now inventories root user exports, the broader public package and
  the separate extension API.
- `ADAPTER_CONTRACT_MANIFEST.json` now publishes current/supported contract version,
  extension points and the explicit absence of Production-qualified ORM adapters.
- The normal `pyaccountingkit` package root remains focused on LOT-21 consumer primitives;
  adapter-author contracts are not added to that root surface.

### Boundaries
- No Django/PostgreSQL or SQLAlchemy/PostgreSQL production adapter is implemented in LOT-22.
- No accounting-domain semantics are changed.
- Full public API freeze remains a later pre-1.0 hardening milestone.


## [0.5.0a1] - 2026-09-18

### Added
- LOT-21 `AccountingApplication` as the first framework-neutral public composition root.
- Explicit public namespaces for references, charts, entries, ledger, closing, controls,
  imports, financial statements, regulatory reporting, financial analysis and subledgers.
- Nested subledger user API for partners, receivables, payables, settlements and matching.
- Frozen `CommandContext` carrying actor, correlation/request identifiers, idempotency key and
  read-only metadata without performing authentication.
- Frozen cursor-first `Page[T]` / `Cursor` pagination primitives.
- Immutable stdlib DTOs for journal entries, trial balances and financial statements.
- Machine-readable public error boundary with explicit unavailable-operation, validation and
  framework-boundary violation codes.
- GAPI tests proving the root package imports without Django/SQLAlchemy and rejecting
  framework-derived objects from returned public object graphs.

### Changed
- Package-root consumer imports now expose `AccountingApplication`, `CommandContext`,
  `Money`, `Currency` and `CurrencyCode`.
- Existing 0.4 accounting, subledger and financial-analysis semantics remain unchanged beneath
  the public facade.
- Root manifests are aligned to `0.5.0a1`; the API remains explicitly pre-1.0 and unfrozen.

### Boundaries
- LOT-21 does not provide Django/PostgreSQL or SQLAlchemy/PostgreSQL production adapters.
- LOT-21 does not expose ORM sessions, QuerySets, transactions or lock primitives.
- Public extension protocols, deterministic manifest generation and compatibility contracts
  remain LOT-22 scope.


## [0.4.0] - 2026-09-18

### Stable promotion
- Promotes the fully qualified `0.4.0rc1` behavior to stable `0.4.0` with no new
  business-domain functionality.
- LOT-18 Subledger Foundations, LOT-19 Settlements/Allocations/Matching/Aging and LOT-20
  Financial Analysis are now qualified together as the stable 0.4 release line.
- Receivable and payable flows remain qualified through DueItem, settlement allocation,
  OpenItem projection, deterministic Aging and exact normalized GL reconciliation.
- Settlement allocation property invariants and stale competing-allocation rejection remain
  canonical release evidence.
- Financial Analysis remains read-only and qualified for distinct EBE/EBITDA, CAF,
  FRNG/BFR/Net Treasury, historical ratios, deterministic trends and replayable
  `AnalysisSnapshot` evidence.
- The Corporate Finance boundary guard and the complete stable 0.3.x import/reporting
  integration/replay baseline remain green release gates.

### Qualification
- Canonical tests pass on Python 3.11, 3.12 and 3.13.
- Repository hygiene, architecture validation, manifest coherence, Ruff lint/format and strict
  mypy remain green.
- Wheel/sdist package verification remains green.
- Dependency audit and Bandit static security analysis remain green.
- Public Python API status remains pre-1.0 and intentionally unfrozen; LOT-21 starts the
  dedicated Public API Facade work in `0.5.0a1`.


## [0.4.0rc1] - 2026-09-18

### Added
- Release-level cross-lot integration proving both receivable and payable flows through
  `DueItem -> Settlement -> Allocation -> OpenItem -> Aging -> normalized GL reconciliation`.
- Release-level replay qualification proving deterministic analytical result,
  `AnalysisSnapshot` and trend checksums.
- Version-specific release-candidate evidence contract for `0.4.0rc1`.

### Changed
- Release metadata is promoted from `0.4.0b1` to `0.4.0rc1` without adding new business
  functionality.
- `scripts/qualify_release.py --release-candidate` now requires the concrete 0.4 evidence
  files for settlement property/concurrency, subledger reconciliation golden, analysis golden,
  analysis/trend replay, Corporate Finance boundary protection, and the retained 0.3
  integration/replay baseline.

### Qualification
- Receivable and Payable open balances remain exact after partial settlement allocation and
  reconcile to explicit normalized control-account balances.
- Existing over-allocation and stale-revision concurrency guards remain mandatory evidence.
- Analysis golden evidence keeps EBE distinct from EBITDA, computes CAF and reconciles
  FRNG/BFR/Net Treasury and ratios into a sealed `AnalysisSnapshot`.
- Replay proves identical pinned analytical semantics reproduce the same analysis and snapshot
  checksums while technical IDs/timestamps may differ; trend ordering is deterministic.
- The existing 0.3 FEC/import/reporting/regulatory integration and replay tests remain in the
  canonical suite.
- Python 3.11/3.12/3.13, Ruff, strict mypy, package verification and Security remain required
  release gates.


## [0.4.0b1] - 2026-09-18

### Added
- LOT-20 deterministic, read-only Financial Analysis bounded context consuming sealed
  `ReportSnapshot` / verified analytical source evidence without mutating accounting truth.
- Versioned `FinancialIndicatorDefinition`, `FinancialRatioDefinition` and
  `AnalysisDefinitionSet` with effective dates, lifecycle status and acyclic dependency
  validation.
- Restricted analytical formula DSL covering additive/subtractive/multiplicative/divisive,
  aggregate, sign, absolute, min/max and explicit coalescing operations without arbitrary
  Python execution.
- Explicit analytical result semantics: `CALCULATED`, `NOT_APPLICABLE`, `UNDEFINED`,
  `INDETERMINATE` and `ERROR`; missing required input and mathematical undefinedness are
  never silently converted to zero.
- Definition-driven SIG examples including distinct EBE and EBITDA definitions plus CAF.
- Explicit `FunctionalBalanceDefinition` and deterministic FRNG, BFRE, BFRHE, BFR and Net
  Treasury derivation with reconciliation against cash assets less cash liabilities.
- Versioned historical ratios, deterministic multi-period trends and explicit policy-driven
  diagnostics without hard-coded universal judgments.
- Immutable checksummed `CalculationTrace` and `AnalysisSnapshot` evidence whose semantic
  checksum excludes technical snapshot IDs and generation timestamps.
- Executable Corporate Finance boundary guard preventing NPV/IRR/WACC/DCF/valuation and related
  investment/financing concepts from entering the accounting analysis core.
- Stable financial-analysis error taxonomy for invalid/stale sources, definitions, dependency
  cycles, unsupported operations, functional-balance errors and invalid snapshots.

### Changed
- The 0.4 line now exposes financial analysis as a separate read-side bounded context alongside
  LOT-18/19 subledgers; it does not become a posting, ledger, reporting or regulatory mutation
  path.
- Analytical source freshness fails closed for current publication while explicit historical
  replay may consume pinned stale/superseded evidence.
- PCG and SYSCOHADA compatibility metadata records LOT-20 as generic analytical mechanics only;
  no statutory-template, legal-filing, tax-filing or regulator-submission claim is broadened.

### Qualification
- Canonical unit/property/contract/integration/golden/replay/concurrency suites pass on Python
  3.11, 3.12 and 3.13.
- Golden analysis qualifies ReportSnapshot -> Gross Margin / EBE / EBITDA / CAF -> functional
  balance -> FRNG / BFR / Net Treasury -> historical ratios -> AnalysisSnapshot.
- Property qualification proves ratio outputs never emit NaN/Infinity and working-capital
  identities reconcile across generated inputs.
- Replay qualification proves identical pinned semantic inputs reproduce the same analytical
  result and AnalysisSnapshot checksum even when technical snapshot IDs/timestamps differ.
- Corporate Finance vocabulary guard, Ruff, canonical formatting, strict mypy, package build,
  dependency audit and static security analysis are release gates.

## [0.4.0a2] - 2026-09-16

### Added
- LOT-19 operational subledger mechanics with immutable `Settlement` and
  `SettlementAllocation` evidence distinct from General Ledger posting.
- Partial/full and many-to-many settlement allocation with optimistic revision guards on both
  settlements and due items.
- Traceable settlement reversal that restores all active allocations and requires a distinct
  posted accounting reversal reference.
- Explicit `MatchingCandidate` versus validated `AccountingMatch`; candidates never execute
  silently and partial matching requires an exact declared residual.
- Deterministic `PaymentTerm` / `DueDateRule` schedule generation with Decimal allocations and
  final-rule rounding residue.
- Explicit `AgingPolicy`, gap-free bucket partitions and deterministic checksummed
  `AgingSnapshot` projections.
- `SubledgerReconciliationService` comparing open-item balances with an explicitly normalized
  GL control-account balance while preserving chart/version/reference-snapshot traceability.
- Fail-closed `WriteOffAuthorization` / `WriteOffRequest` boundary requiring policy/proposal
  evidence instead of silently absorbing residuals.
- Stable LOT-19 settlement, allocation, matching, payment-term, aging, reconciliation and
  write-off error codes.

### Changed
- `DueItem` now supports immutable `allocate()` / `restore()` transitions and revision tracking;
  revision-zero items still must start fully open.
- `Receivable` / `Payable` expose current open balance and immutable due-item replacement while
  preserving original-amount reconciliation.
- Control-account resolution from LOT-18 is reused as the single account authority for
  subledger reconciliation; no national account-prefix heuristic is introduced.
- Regulatory compatibility metadata records LOT-19 only as generic operational subledger
  mechanics and does not broaden PCG/SYSCOHADA regulatory claims.

### Qualification
- Unit qualification covers partial/full allocation, many-to-many allocation, settlement
  reversal, payment-term rounding, explicit matching validation, aging, reconciliation,
  write-off authorization and cross-entity rejection.
- Property tests prove open-plus-allocated balance identities and payment-term amount
  reconciliation over broad generated amount ranges.
- Concurrency tests reject stale settlement/due-item revisions before mutation.
- Golden qualification covers a 1,200 EUR receivable, 500 EUR settlement, 700 EUR remaining
  exposure, deterministic aging and exact reconciliation to a normalized 700 EUR GL balance;
  overpayment remains explicit as unapplied settlement value.
- Allocation remains an auxiliary-state transition and never creates a second GL posting path;
  aging remains distinct from impairment and LOT-20 DSO/DPO analysis remains out of scope.

## [0.4.0a1] - 2026-09-16

### Added
- LOT-18 Subledger Foundations with explicit `SubledgerDefinition` and entity-scoped
  `Subledger` instances.
- `SubledgerParty`, `PartyRef` and `AuxiliaryReference` primitives that remain distinct from
  `CompanyAccount` identity and never imply account-code concatenation.
- Explicit auxiliary modes `SUBLEDGER`, `EXTENDED_ACCOUNT_CODE` and `HYBRID` without hardcoded
  national account-number conventions.
- `Receivable` and `Payable` aggregate roots with immutable due schedules, operational status
  and separate accounting-effect status.
- `DueItem` with strict positive-money, entity, parent and currency invariants; LOT-18 items
  start fully open.
- `OpenItem` projection derived from accounting-effective due items and deliberately distinct
  from `JournalEntryLine`.
- `PostedAccountingReference` linking subledger items to genuinely posted `JournalEntry`
  effects without turning the subledger into a second ledger.
- Effective-dated `AuxiliaryAccountingPolicy` with explicit lifecycle and optional mandatory
  auxiliary-reference requirement.
- Effective-dated `ControlAccountBinding`, `ControlAccountResolverProtocol` and
  `InMemoryControlAccountResolver`.
- Stable subledger error codes covering invalid configuration/items, due items, accounting
  links, missing/ambiguous control accounts and auxiliary-policy execution.

### Changed
- Control-account resolution now reuses `CompanyChartResolverProtocol` so the applicable
  entity/date chart version remains the single authority for company-account resolution.
- Resolved control accounts preserve binding, chart, chart-version and reference-snapshot
  traceability.
- The regulatory compatibility matrix records LOT-18 only as a generic subledger foundation;
  existing PCG/SYSCOHADA regulatory qualification claims are not broadened.

### Qualification
- `sum(due_item.original_amount) == receivable/payable.original_amount` is enforced and covered
  by unit and property-based tests.
- Cross-entity due items and accounting references fail closed.
- Operational `OPEN` state does not imply a posted accounting effect; accounting-effective
  items require an explicit posted-entry reference.
- `OpenItem` creation is rejected before its parent is accounting-effective.
- Control-account resolution qualifies most-specific context selection, exact effective-date
  boundaries, absence/ambiguity, cross-entity isolation and missing/inactive/non-postable
  accounts in the applicable chart version.
- Settlement, allocation, matching/lettering, aging, write-offs and subledger reconciliation
  are intentionally deferred to LOT-19+ and are not claimed by this alpha milestone.

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
