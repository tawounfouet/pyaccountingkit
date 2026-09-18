# PyAccountingKit

PyAccountingKit is a Python toolkit for double-entry accounting built around a
framework-free domain model, hexagonal architecture, deterministic replay and
strict accounting invariants.

The project is designed to support several accounting and regulatory contexts
without coupling the accounting core to Django, SQLAlchemy, FastAPI or a
specific regulatory dataset.

## Status

PyAccountingKit is under active pre-1.0 development. The current package line is
`0.5.0a1`, the LOT-21 Public API Facade alpha built on the stable `0.4.0`
Subledgers & Financial Analysis baseline.

The public Python API is **not yet frozen**. LOT-21 introduces the first coherent,
framework-neutral user boundary without changing the accounting semantics already qualified
through LOT-20.

The primary entry point is:

```python
from pyaccountingkit import AccountingApplication, CommandContext, Money
```

`AccountingApplication` exposes the following namespaces:

```text
references
charts
entries
ledger
closing
controls
imports
statements
reporting
analysis
subledgers
```

The LOT-21 boundary uses explicit commands/queries, immutable stdlib DTOs,
machine-readable public errors, cursor-first pagination and a frozen
`CommandContext`. Public results are checked so Django/SQLAlchemy-derived objects cannot
cross the facade. The root package imports without requiring either ORM.

LOT-21 does **not** introduce Django/PostgreSQL or SQLAlchemy/PostgreSQL persistence, expose
ORM sessions/transactions, or freeze adapter-author contracts. Those remain LOT-22 through
LOT-24 work. Missing composed operations fail closed with a typed
`PublicOperationUnavailableError`.

The stable `0.4.0` business qualification remains mandatory underneath this facade:
settlement allocation/concurrency, exact subledger/GL reconciliation, financial-analysis
golden/replay, Corporate Finance boundary protection and the retained `0.3.x`
imports/reporting qualification continue to run unchanged.

The package remains pre-1.0. LOT-22 / `0.5.0a2` will formalize the extension API,
deterministic manifests and compatibility contracts after LOT-21 is qualified.

## Core guarantees

The following rules are intentional domain constraints, not implementation
accidents:

- monetary arithmetic uses `Decimal`; business code must never introduce
  binary floating-point arithmetic;
- every accounting operation is scoped to exactly one `AccountingEntity`;
  cross-entity chart, journal, period, policy, mapping, account or subledger
  usage must fail closed;
- a journal line with both debit and credit equal to zero is invalid and must
  never be made constructible merely to satisfy an old test fixture;
- journal entries and journal-entry proposals must be balanced before posting;
- posted entries are immutable; corrections use reversal/adjustment entries;
- policy resolution is fail-closed when required runtime context is missing or
  ambiguous;
- current policy execution requires the policy set to be active, effective for
  the accounting date, entity-compatible and reference/snapshot-compatible;
- historical replay is an explicit execution mode and must remain deterministic;
- company-account resolution is entity-, accounting-date- and chart-version
  aware;
- policy-generated proposals reach the ledger through
  `ProposalPostingOrchestrator`; policies never post directly;
- posting mutations, audit records, outbox events and idempotency state belong
  to the same transactional unit of work;
- the in-memory reference UoW uses isolated transaction-local state and rejects
  stale competing writes instead of restoring a global snapshot over another
  transaction's commit;
- generic imports preserve source evidence and raw records, and never infer
  adapter-specific semantics in the generic domain;
- import account/journal mappings are explicit and fail closed: unknown targets
  are never silently created or guessed;
- import plans pin source, adapter, mapping and chart versions and must reject
  execution when those coordinates become stale;
- import execution delegates to `PostingOrchestrator`; the import bounded
  context must never become a second posting engine;
- FEC source rows remain traceable to their file, line number and row checksum;
- `CompAuxNum` remains an auxiliary identifier and is never universally
  concatenated with `CompteNum`;
- FEC duplicate candidates are reported, not silently deleted;
- FEC `Debit` / `Credit` are normalized in the configured accounting currency;
  `Montantdevise` / `Idevise` remain preserved source evidence;
- the same FEC source identity cannot create duplicate ledger effects merely
  because it was acquired under a different batch identifier;
- financial statements are read-side projections from a verified
  `TrialBalance`; they never post, reverse or otherwise mutate the ledger;
- statement definitions, mapping sets and report snapshots are versioned or
  checksummed so historical results can be reproduced explicitly;
- candidate or review-required account mappings are never executable as active
  statement mappings;
- financial-statement formulas use a restricted data-only DSL; arbitrary Python
  execution is forbidden and dependency cycles fail closed;
- company-account identity is preserved separately from presentation account
  code across Trial Balance and statement mapping boundaries;
- published report snapshots are immutable, seal their accounting `as_of` date
  and can be detected as stale when their source Trial Balance checksum changes;
- regulatory reporting accepts published `ReportSnapshot` inputs only and never
  becomes an alternative ledger or posting path;
- regulatory reference models resolve from exact snapshot/framework/edition/model
  coordinates; implicit `latest` resolution is not a valid replay contract;
- regulatory candidate mappings, review-required mappings and reference account
  hints cannot execute silently as validated mappings;
- human-validation requirements declared by the reference model must survive
  projection into the regulatory report;
- regulatory renderers serialize a precomputed `RegulatoryReport`; they must not
  recalculate accounting or reinterpret ledger data;
- regulatory report, validation, export artifact and evidence checksums form an
  explicit replayable evidence chain;
- reference upgrades compare sealed model coordinates, preserve history and
  escalate risky structural/mapping changes to human review rather than silently
  rewriting prior execution semantics;
- a subledger is not a General Ledger and never becomes an alternate posting
  engine;
- `SubledgerParty` is not `CompanyAccount`, and `AuxiliaryReference` is not an
  implicitly concatenated account code;
- `OpenItem` is an auxiliary projection from a `DueItem`, not a
  `JournalEntryLine` alias;
- operational item state and accounting-effect state are independent;
- a receivable/payable becomes accounting-effective only through an explicit
  `PostedAccountingReference` to a genuinely posted entry;
- due schedules are entity/currency consistent and must reconcile exactly to
  the receivable/payable original amount;
- revision-zero due items start fully open; settlement changes use immutable
  `allocate()` / `restore()` transitions and optimistic revision guards;
- settlement allocation is distinct from settlement accounting: allocation
  changes auxiliary open amounts but never posts another GL entry;
- settlement reversal restores every active allocation before marking the
  settlement reversed and requires a distinct posted reversal reference;
- matching candidates are non-executable; only explicitly validated
  `AccountingMatch` objects can represent accounting matching, and partial
  matching must carry the exact residual explicitly;
- payment-term allocations are Decimal-based, sum exactly to one and assign
  rounding residue deterministically to the final due-date rule;
- aging policies declare their date basis and define a gap-free, non-overlapping
  partition; aging never performs impairment or provision calculations;
- subledger reconciliation consumes an explicitly normalized GL control-account
  balance and never infers account semantics from national code prefixes;
- write-off intent requires explicit accounting-policy/proposal evidence and
  never silently removes a residual balance;
- control accounts resolve explicitly by entity, subledger, accounting date and
  optional party/currency dimensions, using the applicable versioned company
  chart; zero or ambiguous bindings fail closed;
- financial analysis is a read-only bounded context over sealed accounting/reporting
  facts and never posts, reverses or mutates accounting truth;
- analytical definitions are versioned/effective-dated and dependency cycles fail closed;
- missing required analytical input is `INDETERMINATE`; mathematically undefined ratios are
  `UNDEFINED` and never silently become zero, NaN or Infinity;
- EBE and EBITDA remain separate explicit definitions; SIG/CAF/ratio semantics are never guessed
  from national account-code prefixes;
- functional-balance and working-capital analysis preserves explicit FRNG/BFRE/BFRHE/BFR/Net
  Treasury identities and reconciliation evidence;
- `CalculationTrace` and `AnalysisSnapshot` seal semantic checksums so identical pinned inputs
  replay deterministically while technical IDs/timestamps may differ;
- Corporate Finance concepts including NPV/IRR/WACC/DCF/valuation, stochastic simulation and
  financing optimization remain outside the PyAccountingKit analysis core;
- strict release qualification requires non-empty integration, golden, replay
  and concurrency suites and cannot skip package or accounting tests.

When a new invariant invalidates an old fixture, **fix the fixture or generator;
do not weaken the invariant**.

## Architecture

Dependency direction is intentionally strict:

```text
adapters  ───────► application ───────► domain
   │                    │                  │
   └──────────────► ports ◄────────────────┘
                         │
                        core
```

Main areas:

- `src/pyaccountingkit/core/` — primitives such as money, currency, clock,
  identifiers, revisions, idempotency and entity-scope guards;
- `src/pyaccountingkit/domain/` — pure accounting model, policies, imports,
  subledgers and financial/regulatory reporting projections;
- `src/pyaccountingkit/application/` — use cases and transactional/read-side
  orchestration;
- `src/pyaccountingkit/ports/` — repository, unit-of-work, chart-resolution,
  account-role/control-account-resolution, import, regulatory-model and renderer
  contracts;
- `src/pyaccountingkit/adapters/` — in-memory, source and presentation adapters,
  including the French FEC adapter and canonical regulatory JSON renderer;
- `docs/` — specifications, ADRs, plans and roadmap; architectural decisions
  are documentation-driven.

The canonical automated-accounting path is:

```text
AccountingEntity + AccountingDate
        │
        ├──────────────────────────────┐
        ▼                              ▼
AccountingPolicySet               CompanyChart
        │                              │
        ▼                              ▼
Policy resolution              CompanyChartVersion
        │                              │
        ▼                              ▼
Recognition / Measurement     AccountRole resolution
        │                              │
        └─────────────┐        ┌───────┘
                      ▼        ▼
               JournalEntryProposal
                      │
                      ▼
          ProposalPostingOrchestrator
                      │
                      ▼
                 JournalEntry
                      │
                      ▼
              PostingOrchestrator
                      │
       Entry + Audit + Outbox + Idempotency
                      │
                      ▼
                    COMMIT
```

LOT-14 provides the source-neutral ingestion path and LOT-15 specializes its
adapter edge for French FEC files without bypassing the ledger engine:

```text
FEC bytes
   │
   ▼
FECParser ──► SourceArtifact + RawImportRecord
   │
   ▼
FECNormalizer
   │
   ▼
NormalizedImportRecord
   │
   ├──► FEC controls / discovery
   │
   ▼
Mapping + Grouping + Validation
   │
   ▼
ImportPlan ─────► Dry Run (no mutation)
   │
   ▼
JournalEntry
   │
   ▼
PostingOrchestrator / post_many
   │
   ▼
FEC reconciliation
```

LOT-16 and LOT-17 form a separate read-side projection chain. It starts from the
verified Trial Balance and never writes back to the accounting engine:

```text
Posted Ledger
      │
      ▼
TrialBalance / TrialBalanceSnapshot
      │
      ├──────────────► StatementMappingSet
      │                       │
      │                       ▼
      └──────────────► FinancialStatementDefinition
                              │
                              ▼
                   FinancialStatementEngine
                              │
                   ┌──────────┼──────────┐
                   ▼          ▼          ▼
                Lines      Controls   Drill-down
                   │          │          │
                   └──────────┴──────────┘
                              │
                              ▼
                    ReportSnapshot (published)
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
RegulatoryReportingProfile  ReferenceReportingModel  RegulatoryMappingSet
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
                      RegulatoryReport
                              │
                              ▼
                    RegulatoryValidation
                              │
                              ▼
                    RegulatoryRenderer
                              │
                              ▼
                 RegulatoryExportArtifact
                              │
                              ▼
                    ReportEvidenceBundle
```

`0.3.0` qualifies the composed PCG/FEC path across both chains:

```text
FEC / SourceArtifact
      │
      ▼
FECAdapter → ImportPlan → PostingOrchestrator
      │
      ▼
Posted Ledger → TrialBalance
      │
      ▼
FinancialStatementEngine → ReportSnapshot
      │
      ▼
RegulatoryReport → Validation → Export → Evidence
      │
      ▼
Deterministic replay
```

LOT-18 establishes the distinct operational-accounting boundary, and LOT-19
adds settlement operations without replacing the GL:

```text
Receivable / Payable ──────► DueItem ──────► OpenItem
        │                      ▲                 │
        │                      │                 │
        │             SettlementAllocation      │
        │                      ▲                 │
        │                      │                 │
        └──────────────── Settlement ────────────┘
                              │
                 PostedAccountingReference
                              │
                              ▼
                    JournalEntry (POSTED)

MatchingCandidate ── explicit validation ──► AccountingMatch
PaymentTerm ────────────────────────────────► deterministic DueItems
Open DueItems ── AgingPolicy ───────────────► AgingSnapshot
OpenItems + ResolvedControlAccount
        + normalized GL balance ────────────► SubledgerReconciliation
```

The execution trace pins proposal checksum, policy versions, regulatory
snapshots, company-chart version and resolved accounts so historical replay is
explicit rather than inferred from current configuration. Financial report
snapshots similarly pin their Trial Balance, statement-definition and
mapping-set checksums. LOT-17 extends that evidence chain by pinning the
regulatory profile, exact reference model, regulatory mappings, validation and
export payload. LOT-18/19 reuse the same version-aware chart authority for
control accounts rather than introducing a separate account-resolution source
of truth.

## Documentation

Start with:

- `docs/ROADMAP.md` for the lot sequence and release gates;
- `docs/plans/RELEASE_0.4.0_STABLE_PROMOTION_PLAN.md` for the current stable
  `0.4.0` promotion contract;
- `docs/plans/RELEASE_0.4.0_RC1_CROSS_LOT_QUALIFICATION_PLAN.md` for the preceding
  `0.4.0rc1` cross-lot qualification contract;
- `docs/plans/LOT-20_FINANCIAL_ANALYSIS_IMPLEMENTATION_PLAN.md` for the LOT-20
  `0.4.0b1` analytical implementation contract;
- `docs/plans/LOT-19_SETTLEMENTS_ALLOCATIONS_MATCHING_AGING_IMPLEMENTATION_PLAN.md`
  for the preceding `0.4.0a2` operational subledger contract;
- `docs/plans/LOT-18_SUBLEDGER_FOUNDATIONS_IMPLEMENTATION_PLAN.md` for the
  `0.4.0a1` subledger foundation contract;
- `docs/plans/RELEASE_0.3.0_STABLE_PROMOTION_PLAN.md` for the stable 0.3.0
  promotion contract;
- `docs/plans/` for milestone-specific implementation plans;
- `docs/specs/` for canonical requirements and ADRs;
- `AGENTS.md` for the mandatory coding-agent workflow and repository-specific
  guardrails;
- `CONTRIBUTING.md` for contribution and commit conventions.

## Installation

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Development workflow

Do not use GitHub Actions as the first place to discover local formatting,
typing or test failures. Before pushing a change, run the same gates locally.

```bash
# Apply canonical formatting first.
python -m ruff format src tests scripts

# Then verify static quality.
python -m ruff check src tests scripts
python -m ruff format --check src tests scripts
python -m mypy src

# Canonical CI accounting suites, including cross-lot integration.
python -m pytest \
  tests/unit tests/property tests/contract tests/integration \
  tests/golden tests/replay tests/concurrency \
  -v --tb=short

# Core qualification.
python scripts/qualify_release.py

# Extended development qualification: runs extended suites when present.
python scripts/qualify_release.py --full

# Strict release qualification: mandatory non-empty integration/golden/replay/
# concurrency suites plus package verification; tests/package cannot be skipped.
python scripts/qualify_release.py --release-candidate
```

For security parity with `.github/workflows/security.yml`:

```bash
python -m pip install pip-audit "bandit[toml]"
python -m pip_audit
python -m bandit -r src/ -c pyproject.toml
```

The CI test matrix qualifies supported Python versions independently. A change
is not ready merely because it passes on one interpreter.

## Change-safety checklist

Before committing or pushing a refactor:

1. Read the active plan/spec/ADR and the current package version in
   `pyproject.toml`; never assume an obsolete milestone.
2. If changing a constructor, protocol or orchestrator signature, search the
   whole repository and migrate **all** call sites, fixtures and tests in the
   same change.
3. If strengthening a domain invariant, update Hypothesis strategies and test
   builders so they generate valid objects unless the test explicitly checks
   rejection.
4. Prefer ports/resolvers at application boundaries. Do not bypass a versioned
   resolver by injecting a raw aggregate merely because an older test did so.
5. Keep entity, accounting date, chart version, policy version and reference
   snapshot traceability intact across application boundaries.
6. For imports, keep format-specific fields in adapters; generic import objects
   must remain source-neutral and every source record must be accounted for.
7. For FEC migrations, preserve raw lineage, auxiliary fields, lettering,
   duplicate evidence and source-to-ledger reconciliation; never manufacture a
   convenience account code by concatenating `CompteNum` and `CompAuxNum`.
8. For financial statements, preserve the Trial Balance as the source of truth,
   reject formula cycles, separate candidate mappings from active mappings and
   keep published report snapshots immutable.
9. For regulatory reporting, resolve exact reference coordinates, keep hints
   non-executable until explicitly validated, preserve human-review flags and
   ensure renderers only serialize precomputed reports.
10. For subledgers, keep settlement/allocation/matching/reconciliation as
    distinct concepts, preserve revision guards, never infer control accounts
    from national code prefixes and never hide residuals as implicit write-offs.
11. Run formatter, lint, typing, canonical tests, strict release qualification
    and relevant security checks before promoting a release.

The detailed coding-agent rules are maintained in `AGENTS.md`.

## License

MIT
