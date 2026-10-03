# PyAccountingKit

PyAccountingKit is a Python toolkit for double-entry accounting built around a
framework-free domain model, hexagonal architecture, deterministic replay and
strict accounting invariants.

The project is designed to support several accounting and regulatory contexts
without coupling the accounting core to Django, SQLAlchemy, FastAPI or a
specific regulatory dataset.

## Status

PyAccountingKit **0.7.0** is the LOT-27 stable promotion candidate. It is not released while G5 external controls remain open.

LOT-26 turns the frozen LOT-25 CFA FRA behavioral baseline into an executable
migration boundary. The temporary `CFAFRACompatibilityAdapter` lets the Django
consumer move service-by-service to `AccountingApplication` while keeping
mutations single-writer and allowing selected reads to shadow both engines.

LOT-27 replaces broad regulatory support claims with capability-scoped qualification records.
`REGULATORY_COMPATIBILITY_MATRIX.json` is now generated from explicit profiles for PCG 2026,
France Non-Profit 2026, SYSCOHADA 2017, OHADA EBNL 2023 and CEMAC PCEMF 2010. Unsupported or
review-required capabilities remain fail-closed rather than being inferred from dataset presence.

The `0.7.0a2` slice gives `fr-nonprofit:2026` a production-qualified effective-plan
provider. PyAccountingKit consumes the upstream resolved 901-account plan directly instead of
replaying PCG plus 116 overlay deltas. Those deltas remain readable as source-backed audit and
explanation evidence only. Effective-plan snapshots are deterministic and replayable; reporting
account mappings remain `REVIEW_REQUIRED` and non-executable.

The `0.7.0a3` slice production-qualifies the reviewed OHADA EBNL 2023 structure
without collapsing source ambiguity. The 1,145-node graph preserves two explicit class-9 scopes
and the duplicated source code `4555` as two occurrence identities. A dedicated OHADA relation
provider exposes only source-declared standard-family edges and a fail-closed negative-constraint
runtime. In particular, EBNL 2023 and PCEMF 2010 cannot be inferred to inherit from SYSCOHADA
2017, and no relation becomes auto-inferable unless the corpus explicitly allows it.

The `0.7.0b1` slice adds a reviewed EBNL/SYSCOHADA structural crosswalk runtime. Structural candidates remain non-executable even when codes and normalized labels match. PCEMF/SYSCOHADA crosswalk support remains explicitly `NOT_ASSERTED`: no PCEMF crosswalk dataset is bundled, and the existing negative-relation guard forbids manufacturing inheritance or mappings from absence of evidence.

The `0.7.0b2` slice production-qualifies provider-backed reporting structures for PCG 2026, France Non-Profit 2026 and SYSCOHADA 2017. Exact snapshot coordinates and source line identities are preserved without inventing reporting semantics: missing node and value categories remain explicitly `UNSPECIFIED`. Reporting account mappings stay `REVIEW_REQUIRED` and non-executable, OHADA EBNL 2023 reporting remains `DISCOVERED` because its line-level transcription is not exhaustive, and `EXPORTS` is not promoted without provider-backed evidence.

The `0.7.0b3` slice hardens the path to `0.7.0rc1` without promoting any additional regulatory capability. Release-candidate evidence is versioned and fail-closed, `release/0.7*` skips the CFA FRA LOT-26 jobs and requires the dedicated LOT-27 GR/G4 path, active documentation is checked against package metadata, and `SNAPSHOT_SCHEMA_MANIFEST.json` makes public snapshot-shape drift executable evidence. The existing sealed release bundle manifest remains the publication qualification artifact.

The `0.7.0rc1` candidate freezes the `b3` regulatory capability set and exercises the dedicated `release/0.7*` GR/G4 path. It does not promote EBNL reporting, reporting-account mappings, crosswalk candidates, concept bindings or exports beyond their reviewed beta statuses, and it does not use deferred LOT-26 live CFA FRA evidence as a release prerequisite.

`0.7.0rc1` is GR/G4-qualified. The `0.7.0` stable promotion candidate is deliberately fail-closed: `release/0.7.0` must pass `scripts/validate_stable_gate.py`, and stable publication remains blocked while main-branch protection or GitHub release immutability is not positively attested. No `0.7.0` stable claim, tag or publication is made by this state.

LOT-25 remains the behavioral oracle baseline and executes normalized golden parity for:

```text
posting / validated-before-posted lifecycle
reversal / original REVERSED state
French FEC ingestion and lineage
ledger / trial-balance variants
income statement / balance sheet / cash flow
```

The golden baseline is runtime-independent, checksummed and fail-closed on
unregistered differences. CFA FRA remains evidence for migration behavior, not
a runtime dependency and not a regulatory source of truth.

LOT-25 also materializes the canonical journal `EntryType` vocabulary
(`OPENING`, `NORMAL`, `ADJUSTING`, `CLOSING`, `REVERSAL`) through the
domain and both PostgreSQL persistence adapters. Normal posting now requires a
`VALIDATED` entry; trusted already-posted history remains an explicit import
mode rather than a generic posting bypass.

The stable **0.5.0** public facade, adapter contract v1 and the independently
Production-qualified Django/PostgreSQL and SQLAlchemy/PostgreSQL adapters remain
the compatibility baseline. **0.7.0rc1 is still pre-1.0**. LOT-27 regulatory production
qualification is now being developed in parallel while the external CFA FRA live-consumer work
required to close LOT-26 remains intentionally deferred. This does not declare `0.6.0` stable.

The LOT-26 migration contract forbids mutation dual-write. Each accounting
mutation selects either the legacy CFA FRA engine or PyAccountingKit. Selected
read operations may dual-run for comparison while returning only the configured
primary result. `LegacyIdentityMap` keeps historical IDs and source provenance
traceable during the transition.

The `0.6.0b21` L26-C slice verifies externally executed legacy retirement without
turning PyAccountingKit into a consumer-repository mutation tool. Verification rebuilds
the exact b20 retirement plan from the current inventory and MIG-13 readiness, requires
the reviewed plan fingerprint to remain unchanged, requires one checksummed post-cutover
observation for each of the 39 inventoried components, and checks the expected state for
every retirement/rewire/preservation action. The execution evidence must identify a live
consumer revision distinct from the frozen oracle tree. A successful verification emits
a deterministic receipt; it never deletes or rewrites consumer or oracle files.

The `0.6.0b22` slice seals those guarantees into an explicit L26-C completion gate.
Completion revalidates the current target-only MIG-13 readiness, the reviewed retirement
plan and the b21 execution evidence together. Only a still-current, blocker-free plan with
verified post-retirement observations can produce `status=COMPLETE` and
`ready_for_0_6_rc1=true`. The completion proof fingerprints the inventory, readiness,
plan, execution receipt and live consumer revision. Canonical live completion remains
unavailable until the real CFA FRA external evidence and retirement observations exist.

The `0.6.0b23` slice connects that completion contract to the actual release gate.
`0.6.0rc1` now has versioned mandatory evidence, including all three live cutover artifacts
and the reviewed plan/execution/completion chain. A `release/*` workflow rebuilds canonical
MIG-13 readiness from the real CI and PostgreSQL-adapter results, requires no blockers,
revalidates the live retirement completion and compares the regenerated proof with the committed
canonical proof before `qualify_release.py --release-candidate` is allowed to run. Isolated
READY fixtures can therefore qualify the mechanism on normal development branches but can no
longer qualify the 0.6 release candidate itself.

The `0.6.0b24` slice removes the remaining ambiguity around the external consumer itself.
`CONSUMER_BINDING.json` now records an explicit `BOUND` or `UNBOUND` repository identity.
A bound consumer identifies the canonical GitHub `owner/name`, repository URL, default branch,
exact 40-character revision SHA, environment, observation time and producer. Normal beta CI
accepts an explicit `UNBOUND` state without pretending the repository is known. The
`0.6.0rc1` gate requires a production `BOUND` state and requires its revision to equal the
revision sealed by the retirement completion proof.

The `0.6.0b25` slice makes the next external step reproducible. Git history shows that the
historic Sprint-7 application was imported directly into this repository as the behavioral
oracle and no separate canonical GitHub consumer origin is recorded. The new standalone bootstrap
therefore copies that immutable oracle into a separate destination, verifies the exact oracle tree
SHA, adds the compatible PyAccountingKit dependency, fixes the already-proven namespaced login
redirect defect, and writes a deterministic provenance manifest. The bootstrap never mutates the
oracle, publishes a GitHub repository, binds `CONSUMER_BINDING.json`, or promotes cutover
evidence automatically.

The `0.6.0b26` slice closes the publication-to-binding gap. A standalone consumer can be
bound only through a reviewed plan/apply handoff that inspects a clean top-level Git repository,
verifies its GitHub `origin`, default branch and exact HEAD revision, revalidates the embedded
bootstrap provenance against the frozen oracle, and seals both bootstrap and publication SHA-256
fingerprints into the binding. Binding schema v2 therefore makes the publication provenance
part of the canonical repository identity instead of an out-of-band assumption.

The `0.6.0b27` slice makes that binding evolvable without weakening identity. Once a live
consumer is BOUND, its revision may advance only to a new descendant commit in the same GitHub
repository, on the same default branch and environment, with the same bootstrap provenance.
Advancement is again plan/apply reviewed and fails closed on rollback, divergent history,
repository substitution, provenance drift or post-review changes.

The `0.6.0b9` migration bridge adds MIG-11 reference-authority replacement:
`effective_plan` must delegate to `AccountingApplication.references` and may
neither fall back to nor dual-run against CFA FRA's local `FrameworkAccount`
tables. The legacy-retirement gate now requires explicit
`regulatory_authority_replaced` evidence in addition to parity, production
adapters, consumer E2E and identity traceability. The frozen Sprint-7 consumer
still reads `FrameworkAccount` directly, so this milestone provides the target
bridge and retirement guard without falsely claiming consumer cutover.

The bundled Sprint 7 oracle explicitly schedules its Regulatory Controls &
Closing Package for Sprint 8. LOT-25 therefore records the missing executable
legacy closing oracle as a checksummed evidence gap rather than claiming parity
for behavior that is not present in the source snapshot.

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


The `0.6.0b10` cutover profile adds `MigrationRouting.target_only()` and
`build_target_only_consumer_bridge(...)`. This final-mode bridge accepts no
legacy service dependencies, exposes no shadow dual-run and routes every migrated
accounting operation to PyAccountingKit. It is the structural profile required
before MIG-13 can retire duplicate engine code; external consumer evidence must
still be green before that retirement is allowed.


The `0.6.0b11` milestone makes MIG-13 readiness a canonical CI decision.
The new retirement-readiness gate runs only after the Python qualification matrix,
both PostgreSQL adapters and CFA FRA consumer evidence. It combines those exact-run
results with the target-only routing profile and explicit external evidence for
legacy identity migration and regulatory-authority cutover.

The current expected retirement blockers are intentionally explicit:
`evidence:consumer-e2e`, `evidence:legacy-identities` and
`evidence:regulatory-authority`. A change to that blocker set fails CI until the
retirement evidence manifest is reviewed, preventing silent or accidental legacy
engine deletion.


The `0.6.0b12` milestone makes the legacy-retirement scope machine-readable.
The frozen Sprint-7 source is classified into duplicate engine code to retire,
Django consumer endpoints to rewire, persistence/provenance to migrate, consumer
concerns to keep, and frozen tests to retain as behavioral oracle evidence.

The inventory always applies to **live consumer equivalents**, never to the
bundled oracle itself. Canonical CI validates the inventory before MIG-13
readiness is evaluated, so missing or contradictory retirement scope blocks
the retirement decision.


The `0.6.0b13` milestone upgrades live cutover proof from editable booleans
to an attestable evidence contract. External PASS evidence for legacy identity
migration or regulatory-authority replacement must carry an artifact reference,
a lowercase SHA-256 digest, an explicit UTC observation timestamp and a producer.
BLOCKED evidence must carry a reason and cannot masquerade as an attested proof.

Canonical CI validates this contract before MIG-13 readiness runs. The current
records remain BLOCKED because no live-consumer artifacts have yet been supplied;
therefore the existing retirement blockers remain intentionally unchanged.


The `0.6.0b14` milestone closes the trust gap between a declared external
`PASS` and a retirement-ready proof. PASS records must now reference a real file
materialized beneath `tests/consumer/cfa_fra/live_evidence/`; canonical CI resolves
that path safely, rejects traversal, reads the actual bytes and compares their
SHA-256 with the manifest attestation.

The MIG-13 retirement job no longer derives `identities_traceable` or
`regulatory_authority_replaced` directly from manifest status. Those booleans are
outputs of the cutover-evidence verification job. The current records remain
BLOCKED, so no live artifact is fabricated and the existing retirement blockers
remain unchanged.


The `0.6.0b15` milestone adds a controlled promotion path for live cutover
evidence. Operators no longer hand-edit a SHA-256 into the retirement manifest.
`scripts/promote_cfa_fra_cutover_evidence.py` starts from an artifact already
materialized beneath the configured evidence root, computes its digest from the
actual bytes, builds and re-verifies the `PASS` attestation, removes only the
matching retirement blocker and prints the candidate manifest.

The command is a dry-run by default. Persisting the promotion requires explicit
`--write`, uses an atomic file replacement and refuses to overwrite an evidence
record that is already `PASS`.


The `0.6.0b16` milestone adds semantic schemas for the two live-cutover artifacts.
A matching SHA-256 is no longer enough. Legacy-identity evidence must prove a complete
CFA_FRA_LEGACY -> PYACCOUNTINGKIT mapping with zero unresolved identities; regulatory
authority evidence must prove target-only routing, disabled local `FrameworkAccount`
authority, non-authoritative local seed commands, delegated `effective_plan` resolution and
sample provider-backed reference resolutions.

Canonical verification and evidence promotion both enforce these schemas, and promoted
artifacts must name the same consumer as the retirement manifest.


The `0.6.0b17` milestone adds deterministic producers for the semantic cutover artifacts
introduced in b16. Identity evidence is generated from a `LegacyIdentityStoreProtocol`
snapshot plus an independently supplied expected legacy-record count; generation fails when
the snapshot is incomplete. Regulatory-authority evidence is generated from an observed
target-only routing state, provider identity, local-authority flags and sampled provider-backed
reference resolutions.

`scripts/generate_cfa_fra_cutover_artifact.py` consumes structured observation snapshots,
prints a candidate artifact in dry-run mode, and materializes it only with explicit `--write`.
Existing artifacts are not replaced unless `--overwrite` is also supplied. Generated bytes
are parsed again with the b16 semantic schema before atomic replacement.


The `0.6.0b18` milestone composes generation, semantic verification and promotion into a
reviewable two-step pipeline. `plan` generates the candidate artifact in an isolated staging
root, verifies its schema, simulates promotion and serializes a plan containing the exact
artifact SHA-256, source-manifest fingerprint, attestation metadata, blocker removal and
candidate retirement manifest.

`apply` accepts that serialized plan only. It refuses stale manifests, implicit artifact
overwrite, digest drift, blocker drift or any promotion result that differs from the reviewed
candidate manifest. The artifact is materialized first and the retirement manifest is updated
atomically afterwards; if manifest persistence fails, the evidence remains unpromoted rather
than silently authorizing retirement.

Canonical CI executes the complete plan/apply pipeline on isolated fixture evidence for both
legacy identities and regulatory authority, while the real CFA FRA evidence remains BLOCKED.


The `0.6.0b19` milestone makes live consumer E2E a first-class MIG-13 cutover artifact.
`cfa_fra_consumer_e2e_cutover/v1` requires exactly one PASS for each of the ten mandatory
consumer scenarios: login, organization context, FEC import, journal, ledger, balance,
financial statements, controls, closing and exports. Every scenario carries a canonical
`sha256:<64 lowercase hex>` provenance checksum.

The bundled Sprint-7 consumer still runs in canonical CI as a frozen non-regression baseline,
but its known login/controls/closing gaps no longer define the retirement signal. MIG-13 now
consumes `consumer_e2e_green` from the same cryptographically verified live cutover evidence
boundary as identity traceability and regulatory-authority replacement.

The generic generation, promotion and reviewed plan/apply pipeline accept `consumer_e2e` as
a third evidence key. Canonical live consumer evidence remains BLOCKED until a real artifact is
supplied; the isolated fixture pipeline proves that all three external blockers can be cleared
without modifying canonical live evidence.


The `0.6.0b20` milestone makes L26-C retirement planning executable without making
retirement itself automatic. A deterministic plan can be built only from a MIG-13 readiness
report with `ready=true`, target-only routing, no calculated or expected blockers, and all
five evidence gates green.

The plan fingerprints both the retirement inventory and the readiness report, then maps every
inventory component to one non-executing action:

- duplicate accounting engines -> `RETIRE_DUPLICATE_ENGINE`;
- Django endpoints -> `VERIFY_CONSUMER_REWIRED`;
- historical state -> `PRESERVE_OR_MIGRATE_PERSISTENCE`;
- consumer-owned concerns -> `KEEP_CONSUMER_CONCERN`;
- frozen Sprint-7 evidence -> `PRESERVE_FROZEN_ORACLE`.

The planner never mutates the bundled oracle and never executes deletion. Canonical CI
qualifies the planner only against isolated MIG-13-ready fixture evidence; the real live
retirement state remains blocked until genuine CFA FRA proofs are supplied.


## Resource and licensing governance

The root MIT license applies to the PyAccountingKit project material to the extent described by
`LICENSE`. It must not be read as silently relicensing third-party, regulatory or practitioner
source documents stored as repository evidence.

The current resource snapshots are governed by:

```text
RESOURCE_GOVERNANCE.json
THIRD_PARTY_NOTICES.md
resources/README.md
```

Both the CFA FRA behavioral oracle and the regulatory accounting data snapshot are repository
evidence only: they are not mandatory runtime dependencies and are forbidden from the
PyAccountingKit wheel. The regulatory bundle intentionally carries a
`MIXED_OR_UNASSERTED_REVIEW_REQUIRED` rights status because its embedded source documents do not
declare one uniform license.

Any change below a governed `resources/<bundle>/` directory must update the bundle fingerprint
and provenance/rights review in the same pull request.

Validation:

```bash
python scripts/validate_resource_governance.py
```
