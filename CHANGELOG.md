# Changelog

All notable changes to pyaccountingkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.0b1] - 2026-10-02

### Added
- Reviewed EBNL 2023 / SYSCOHADA 2017 structural crosswalk candidate model.
- Canonical filesystem provider for the source-backed structural-delta dataset.
- Explicit candidate status taxonomy and source-occurrence provenance.
- Fail-closed boundary between reviewed structural candidates and executable `StandardCrosswalk`.

### Safety
- Same-code and same-normalized-label candidates remain non-semantic and non-executable.
- Automatic crosswalk approval, inheritance assertion and code-equality semantic inference remain disabled.
- PCEMF/SYSCOHADA crosswalk support remains `NOT_ASSERTED`; no missing dataset is synthesized.
- Existing PCEMF negative constraints continue to forbid inheritance inference.
- LOT-26 live CFA FRA evidence remains intentionally deferred.

## [0.7.0a3] - 2026-10-02

### Added
- `OHADA_EBNL` standard type and explicit `class_scope` reference-node type.
- `EBNLFilesystemReferenceAdapter` over the reviewed 1,145-node OHADA EBNL 2023 graph.
- `StandardRelation`, `StandardRelationRegister` and source-backed relation evidence model.
- `ForbiddenStandardRelation` and typed fail-closed inference guards.
- `OHADAStandardRelationFilesystemAdapter` for the canonical OHADA family relation dataset.
- Public additive `StandardRelationProviderProtocol`.
- `StandardRelationService` delegation through the public references namespace.
- Golden qualification for EBNL class-9 scopes, duplicate source code `4555`, OHADA family
  relations and negative constraints.

### Qualified in this slice
- `ohada-ebnl:2023 / STRUCTURE`: `PRODUCTION_QUALIFIED`.
- `ohada-ebnl:2023 / SNAPSHOTS`: `PRODUCTION_QUALIFIED`.
- OHADA family `RELATIONS` for SYSCOHADA, EBNL and PCEMF:
  `PRODUCTION_QUALIFIED`.
- EBNL/PCEMF inheritance guards remain `FORBIDDEN_INFERENCE` with runtime enforcement.

### Safety
- The duplicated EBNL code `4555` is never collapsed or guessed by code lookup.
- `class_scope` nodes are preserved explicitly for the two class-9 scopes.
- `non-forbidden` never means `auto-inferable`.
- EBNL/SYSCOHADA crosswalk evidence remains `REVIEW_REQUIRED`.
- PCEMF structure remains `NOT_ASSERTED`.
- EBNL reporting remains outside production qualification.

## [0.7.0a2] - 2026-10-02

### Added
- Provider-resolved `EffectiveAccountPlan`, `EffectiveReferenceAccount` and provenance model.
- Read-only `ReferenceOverlay` / `ReferenceOverlayEntry` audit model.
- `NonProfitFilesystemReferenceAdapter` for the upstream France Non-Profit 2026 corpus.
- Deterministic, replayable `EffectivePlanSnapshot`.
- Public additive `EffectivePlanReferenceProviderProtocol`.
- `EffectivePlanReferenceService` delegation through `AccountingApplication.references`.
- Golden qualification over the real 901-account effective plan and 116-entry overlay.

### Qualified in this slice
- `fr-nonprofit:2026 / EFFECTIVE_PLAN`: `PRODUCTION_QUALIFIED`.
- `fr-nonprofit:2026 / SNAPSHOTS`: `PRODUCTION_QUALIFIED`.
- `fr-nonprofit:2026 / OVERLAYS`: remains `VALIDATED` and non-executable.

### Safety
- PyAccountingKit consumes the resolved effective plan directly; it never rebuilds it by replaying
  PCG plus overlay entries.
- Overlay entries are provenance/audit evidence and expose no implicit `apply` path.
- Non-Profit reporting account mappings remain `REVIEW_REQUIRED` and non-executable.
- LOT-26 live CFA FRA publication/binding remains intentionally deferred.

## [0.7.0a1] - 2026-10-01

### Added
- Capability-scoped regulatory qualification model and support-level derivation.
- `RegulatoryFrameworkIntegrationProfile` and auditable
  `RegulatoryCapabilityQualification` records.
- Canonical profiles for PCG 2026, France Non-Profit 2026, SYSCOHADA 2017, OHADA EBNL 2023
  and CEMAC PCEMF 2010.
- Deterministic generation of `REGULATORY_COMPATIBILITY_MATRIX.json`.
- Dedicated LOT-27 golden qualification gate.

### Qualified in this slice
- PCG 2026 structure and snapshots: `PRODUCTION_QUALIFIED`.
- SYSCOHADA 2017 structure and snapshots: `PRODUCTION_QUALIFIED`.

### Safety
- Non-Profit reporting account mappings remain `REVIEW_REQUIRED`.
- EBNL/SYSCOHADA structural crosswalk evidence does not imply semantic equivalence.
- EBNL and PCEMF inheritance inference is explicitly forbidden by current corpus constraints.
- Missing PCEMF structure and missing concept bindings remain `NOT_ASSERTED`.
- LOT-26 live CFA FRA evidence is still deferred; this alpha does not declare `0.6.0` stable.

## [0.6.0b27] - 2026-10-01

### Added
- Reviewed `BOUND(old revision) -> BOUND(new revision)` consumer binding advancement.
- Explicit Git ancestry proof requiring the previously bound revision to be an ancestor of the
  observed revision.
- Stable repository, canonical URL, default branch, environment and bootstrap-provenance checks
  across revision advancement.
- Side-effect-free advancement planning and stale-state-safe apply.
- Dedicated CI proof covering publication, initial binding, descendant consumer commit and
  canonical re-attestation.

### Safety
- Revision rollback and divergent-history rebinding fail closed.
- A no-op advancement to the currently bound SHA is rejected.
- Repository substitution, branch changes, environment drift and bootstrap provenance drift are
  rejected.
- Binding mutation still requires explicit `--write`.
- The bootstrap baseline remains `pyaccountingkit>=0.6.0b26,<0.7`; b27 does not invalidate a
  consumer seed already published from the qualified b26 bootstrap.

## [0.6.0b26] - 2026-10-01

### Added
- Verified standalone-consumer publication inspection over a real Git working tree.
- GitHub origin normalization for HTTPS and SSH remotes.
- Clean-worktree, top-level repository, default-branch and exact HEAD revision checks.
- Bootstrap provenance revalidation against the immutable Sprint-7 oracle and current bootstrap
  requirement.
- Side-effect-free publication `plan` followed by stale-state-safe `apply`.
- Binding schema `cfa_fra_live_consumer_binding/v2` with mandatory
  `bootstrap_sha256` and `publication_sha256`.
- Canonical CI proof of bootstrap -> Git publication -> reviewed binding promotion.

### Safety
- Publication planning requires canonical state `UNBOUND`.
- A repository change after review invalidates the plan.
- A canonical binding change after review invalidates the plan.
- Dry-run remains the default for apply; canonical mutation requires explicit `--write`.
- The isolated CI publication is qualification evidence only and never changes the canonical
  live binding.

## [0.6.0b25] - 2026-10-01

### Added
- Deterministic standalone CFA FRA consumer bootstrap from the immutable Sprint-7 oracle.
- Exact Git-tree verification before bootstrap materialization.
- `ConsumerBootstrapPlan`, `ConsumerBootstrapResult` and provenance manifest.
- Repository command `bootstrap_cfa_fra_live_consumer.py` with dry-run by default and explicit
  `--write` / `--overwrite`.
- Automatic seed-only addition of `pyaccountingkit>=0.6.0b25,<0.7`.
- Seed-only correction of the already-qualified login redirect defect from `dashboard` to
  `analytics:dashboard`.
- Canonical `CONSUMER_BOOTSTRAP.json` safety contract and dedicated CI qualification.
- RC validation that the bootstrap is sourced from the frozen oracle and cannot auto-publish,
  auto-bind or auto-promote cutover evidence.

### Safety
- No file under `resources/cfa_fra_django_mvp_sprint_7/` is modified.
- Bootstrap output remains `UNBOUND_UNTIL_PUBLISHED` and `NOT_STARTED` for cutover.
- Creating a standalone seed is not treated as live E2E, identity migration, regulatory cutover
  or retirement evidence.
- A real GitHub repository identity and revision are still required before `0.6.0rc1`.

## [0.6.0b24] - 2026-10-01

### Added
- Canonical CFA FRA live-consumer repository binding schema.
- Explicit `BOUND` / `UNBOUND` repository identity state.
- Repository binding validation for canonical GitHub `owner/name`, URL, branch, exact commit SHA,
  environment, observation time and producer.
- `validate_cfa_fra_consumer_binding.py` CLI and canonical CI job/output.
- `0.6.0rc1` requirement for a production BOUND consumer repository.
- Release correlation between the bound repository revision and the retirement completion revision.

### Safety
- The current canonical consumer remains explicitly `UNBOUND`; no repository is guessed.
- The frozen Sprint-7 oracle cannot be used as the live consumer revision.
- Beta CI may validate an UNBOUND state, but a release branch cannot promote `0.6.0rc1` while
  the consumer repository identity is unknown.
- AMIFOND remains a separate project that has adopted CFA-FRA patterns; it is not declared to be
  the LOT-26 live consumer without explicit evidence.

## [0.6.0b23] - 2026-10-01

### Added
- Versioned `0.6.0rc1` release-evidence contract.
- Mandatory live CFA FRA cutover artifacts for consumer E2E, legacy identities and regulatory
  authority.
- Mandatory reviewed live retirement plan, execution evidence and completion proof.
- Semantic RC validation of completion status, routing profile, live consumer revision,
  fingerprints and 39-component action counts.
- Release-branch CI revalidation of canonical MIG-13 readiness and L26-C completion before
  `qualify_release.py --release-candidate`.

### Safety
- Isolated READY fixtures remain valid for mechanism qualification but cannot satisfy the
  `0.6.0rc1` release gate.
- Release qualification fails while any canonical live cutover blocker remains.
- Release qualification regenerates the completion proof and requires exact equality with the
  committed canonical completion artifact.
- No unrelated GitHub repository is treated as the live CFA FRA consumer without an explicit,
  verifiable repository identity.

## [0.6.0b22] - 2026-10-01

### Added
- Final L26-C `LegacyRetirementCompletion` proof.
- `complete_legacy_retirement(...)` fail-closed completion gate.
- Deterministic completion fingerprint sealing inventory, readiness, plan, execution receipt
  and live consumer revision.
- Explicit `status=COMPLETE`, target-only routing and `ready_for_0_6_rc1=true` output.
- `qualify_cfa_fra_legacy_retirement_completion.py` CLI.
- Canonical CI gate qualifying the completion contract after b21 execution verification.

### Safety
- Completion revalidates current MIG-13 readiness and refuses non-target-only routing or blockers.
- The execution evidence is reverified rather than trusting a hand-constructed receipt.
- The frozen oracle revision remains forbidden as a retirement target.
- Canonical live CFA FRA completion is not claimed; isolated READY fixture evidence qualifies
  only the completion mechanism.

## [0.6.0b21] - 2026-10-01

### Added
- Fail-closed verification contract for externally executed L26-C legacy retirement.
- `LegacyRetirementObservedState`, execution observations and deterministic verified receipts.
- Exact-plan revalidation against the current inventory and MIG-13 readiness fingerprints.
- Per-component post-cutover state verification for all 39 retirement-plan items.
- `verify_cfa_fra_legacy_retirement_execution.py` CLI.
- Canonical CI gate qualifying execution verification against isolated READY evidence.

### Safety
- PyAccountingKit still performs no deletion or consumer-repository rewrite.
- Execution evidence must target a live consumer revision distinct from the frozen oracle tree.
- Every planned component must be observed exactly once with a checksummed evidence reference.
- Duplicate engines must be `RETIRED`, rewired endpoints `REWIRED`, persistence/oracle
  evidence `PRESERVED`, and consumer-owned concerns `PRESENT`.
- Canonical live CFA FRA evidence remains BLOCKED; synthetic CI observations only qualify the
  verification mechanism.

## [0.6.0b20] - 2026-10-01

### Added
- Deterministic `LegacyRetirementPlan` for the L26-C retirement phase.
- Explicit retirement dispositions and non-executing actions.
- Inventory and MIG-13 readiness fingerprints sealed into each plan.
- Fail-closed planner requiring target-only routing, `ready=true`, empty blocker sets and
  every retirement evidence gate green.
- `plan_cfa_fra_legacy_retirement.py` reviewable planner CLI.
- Canonical CI gate qualifying the complete 39-component plan against isolated READY evidence.

### Safety
- The planner performs no deletion, rewrite or consumer mutation.
- `FROZEN_ORACLE` inventory entries can only map to `PRESERVE_FROZEN_ORACLE`.
- Persistence components are preserved/migrated rather than treated as deletable engine code.
- The canonical live CFA FRA readiness remains blocked; fixture readiness is used only to prove
  planner behavior.

## [0.6.0b19] - 2026-09-30

### Added
- Live consumer E2E cutover schema `cfa_fra_consumer_e2e_cutover/v1`.
- Typed `ConsumerE2ECutoverArtifact`.
- First-class `consumer_e2e` support in generation, verification, promotion and reviewed
  cutover pipeline planning/application.
- Consumer E2E source fixture covering all ten mandatory retirement scenarios.
- Schema, generation, promotion and pipeline qualification tests for live consumer evidence.

### Changed
- Retirement evidence advances to schema v5 with three external records:
  `consumer_e2e`, `legacy_identities` and `regulatory_authority`.
- A live consumer E2E PASS requires exactly one PASS result for every mandatory scenario and a
  canonical SHA-256 provenance checksum for every scenario.
- MIG-13 retirement now consumes the verified live `consumer_e2e_green` output from the
  cutover-evidence job.
- The bundled Sprint-7 consumer evidence remains a canonical non-regression gate but no longer
  acts as the live retirement signal.
- The isolated cutover pipeline CI gate now proves all three external evidence promotions.

### Safety
- The canonical consumer E2E record remains BLOCKED until real live evidence is supplied.
- No Sprint-7 blocker is hidden or rewritten; the frozen baseline continues to report its
  login, controls and closing gaps.
- No live evidence is fabricated and the canonical MIG-13 decision remains blocked.

## [0.6.0b18] - 2026-09-30

### Added
- Reviewable cutover-evidence pipeline plan schema v1.
- `plan_cutover_evidence_pipeline(...)` for side-effect-free generation, validation and
  promotion simulation.
- `apply_cutover_evidence_pipeline(...)` for stale-safe application of a reviewed plan.
- `run_cfa_fra_cutover_evidence_pipeline.py` with separate `plan` and `apply` commands.
- Semantic retirement-manifest fingerprinting independent of pretty-print formatting.
- Canonical CI gate executing identity and regulatory plan/apply transitions on isolated
  fixture evidence.

### Safety
- Planning never mutates durable evidence or the retirement manifest.
- Apply rejects a manifest changed after planning.
- Apply refuses implicit artifact overwrite.
- Artifact SHA-256, removed blocker and the full promoted manifest must match the reviewed
  plan exactly.
- Generation fixtures and pipeline fixtures never alter canonical CFA FRA live evidence.
- The canonical live blocker set remains unchanged.

## [0.6.0b17] - 2026-09-30

### Added
- Deterministic legacy-identity cutover artifact generator.
- Deterministic regulatory-authority cutover artifact generator.
- `RegulatoryAuthorityObservation` as the framework-neutral observed-state input.
- Controlled `generate_cfa_fra_cutover_artifact.py` CLI.
- Dry-run generation by default with explicit `--write` and `--overwrite` controls.
- Source-observation fixtures and API/CLI qualification tests.

### Safety
- Identity generation requires an independently supplied expected legacy population count and
  fails when the migrated identity snapshot is incomplete.
- Regulatory generation requires target-only routing, PyAccountingKit provider authority,
  disabled local authority, delegated effective-plan resolution and sampled provider-backed
  references.
- Generated artifacts are semantically parsed before atomic materialization.
- Source observations are not automatically promoted to PASS and canonical live evidence
  remains BLOCKED until real consumer evidence is supplied.

## [0.6.0b16] - 2026-09-30

### Added
- Semantic schema `cfa_fra_legacy_identity_migration/v1`.
- Semantic schema `cfa_fra_regulatory_authority_cutover/v1`.
- Typed parsers for legacy identity migration and regulatory authority cutover artifacts.
- Artifact-level checks for:
  - complete identity coverage with zero unresolved records;
  - unique legacy identity mappings;
  - CFA_FRA_LEGACY -> PYACCOUNTINGKIT system binding;
  - target-only regulatory routing;
  - disabled local `FrameworkAccount` authority;
  - non-authoritative local regulatory seed commands;
  - delegated `effective_plan`;
  - non-empty provider-backed sample resolutions;
  - PyAccountingKit as the target reference provider.
- Retirement evidence schema v4 with explicit content-schema policy.

### Changed
- Cryptographically valid PASS artifacts are now also semantically validated.
- Evidence promotion rejects schema-invalid artifacts and artifacts produced for a different
  consumer.
- MIG-13 can consume external proof booleans only after both SHA-256 and business-schema
  verification succeed.

### Safety
- Arbitrary JSON with a valid digest cannot satisfy a live-cutover proof.
- The canonical BLOCKED evidence remains unchanged; no live evidence is fabricated.

## [0.6.0b15] - 2026-09-30

### Added
- Controlled live-cutover evidence promotion API.
- `attest_external_cutover_artifact(...)` computes the SHA-256 from real artifact bytes.
- `promote_cfa_fra_cutover_evidence.py` for promoting one external proof from BLOCKED to PASS.
- Dry-run by default, with explicit `--write` required for manifest mutation.
- Atomic manifest replacement on write.
- Promotion tests covering digest derivation, blocker removal, missing artifacts, duplicate
  promotion, dry-run behavior and explicit persistence.

### Safety
- Operators never supply the SHA-256 manually during promotion.
- An already-PASS proof cannot be overwritten by the promotion path.
- Promotion removes only the blocker bound to the promoted evidence key.
- The generated PASS is immediately re-verified against the artifact bytes before it can be
  returned or written.

## [0.6.0b14] - 2026-09-30

### Added
- Cryptographic verification for live CFA FRA cutover evidence artifacts.
- Safe repository-local artifact resolution with path-traversal rejection.
- Streaming SHA-256 verification against the exact bytes of every `PASS` artifact.
- Canonical live-evidence materialization root under
  `tests/consumer/cfa_fra/live_evidence/`.
- Verified cutover CI outputs for:
  - legacy identity traceability;
  - regulatory-authority replacement.

### Changed
- Retirement evidence schema advances to v3 with an explicit artifact policy.
- MIG-13 readiness consumes verified cutover job outputs instead of trusting manifest
  `PASS` status directly.

### Safety
- Missing artifacts, checksum mismatch, absolute paths and `..` traversal fail closed.
- BLOCKED records continue to require no fabricated artifact.
- Current MIG-13 blockers remain consumer E2E, legacy identities and regulatory authority.

## [0.6.0b13] - 2026-09-30

### Added
- Attestable live-cutover evidence model for external CFA FRA migration proofs.
- `PASS` evidence requires:
  - artifact reference;
  - lowercase SHA-256 digest;
  - UTC ISO-8601 observation timestamp;
  - producer identity.
- `BLOCKED` evidence requires an explicit reason and remains non-green.
- Retirement evidence manifest schema v2 replacing editable external boolean flags.
- Dedicated `CFA FRA live cutover evidence` CI job required before MIG-13 readiness.

### Changed
- MIG-13 readiness now derives identity-traceability and regulatory-authority booleans from
  validated evidence records instead of reading booleans directly from JSON.

### Safety
- Current external records remain `BLOCKED`; this release does not fabricate live cutover
  evidence.
- A passing external record without provenance metadata or a valid SHA-256 fails closed.
- The blocker list must stay coherent with the attested evidence state.

## [0.6.0b12] - 2026-09-30

### Added
- Machine-readable CFA FRA legacy-retirement inventory bound to the frozen Sprint-7 oracle.
- Explicit retirement dispositions:
  - `RETIRE_ENGINE`;
  - `REWIRE_CONSUMER`;
  - `MIGRATE_PERSISTENCE`;
  - `KEEP_CONSUMER`;
  - `FROZEN_ORACLE`.
- Canonical retirement-inventory validator checking source anchors, duplicate paths, category
  invariants and coverage of critical accounting engine/read/persistence surfaces.
- Dedicated `CFA FRA retirement inventory` CI job, required before MIG-13 readiness.

### Safety
- The inventory never authorizes mutation of the bundled Sprint-7 oracle.
- Retirement dispositions apply only to live-consumer equivalents.
- Django views/forms cannot be classified as engine code for deletion.
- Historical persistence is explicitly migration/archival work, not deletion-by-default.
- Frozen parity and consumer tests remain oracle evidence after live legacy retirement.

## [0.6.0b11] - 2026-09-30

### Added
- Machine-readable MIG-13 retirement evidence manifest for the CFA FRA consumer.
- `qualify_cfa_fra_retirement.py` combining exact CI results with
  `MigrationRouting.target_only()` and external cutover evidence.
- Canonical `CFA FRA retirement readiness` CI job chained after:
  - the Python qualification matrix;
  - Django/PostgreSQL qualification;
  - SQLAlchemy/PostgreSQL qualification;
  - CFA FRA consumer evidence.
- Consumer-evidence job output exposing its actual `consumer_e2e_green` state to downstream
  retirement qualification.

### Safety
- A successful readiness job does not mean retirement is ready; it means the current
  readiness decision is internally coherent and its blocker set is explicit.
- Current MIG-13 blockers are `evidence:consumer-e2e`,
  `evidence:legacy-identities` and `evidence:regulatory-authority`.
- Any blocker added, removed or silently changed makes the readiness qualifier fail until
  the evidence manifest is reviewed.

## [0.6.0b10] - 2026-09-30

### Added
- `MigrationRouting.target_only()` as the explicit final CFA FRA cutover profile.
- `MigrationRouting.is_target_only()` to make absence of legacy and shadow routes
  directly testable.
- `build_target_only_consumer_bridge(...)`, which constructs the real CFA FRA consumer
  bridge without accepting any legacy accounting/import/reporting/statement service.

### Safety
- The target-only factory routes every migrated mutation and read to PyAccountingKit.
- No dual-run read is present in the final cutover profile.
- MIG-13 retirement remains blocked by the existing evidence gates until consumer E2E,
  identity traceability and regulatory-authority replacement are all proven.

## [0.6.0b9] - 2026-09-30

### Added
- Target-only CFA FRA `effective_plan` bridge delegating accounting-reference authority to
  `AccountingApplication.references.get_effective_plan`.
- Retirement evidence now includes an explicit `regulatory_authority_replaced` proof.
- `LegacyRetirementGate` emits `evidence:regulatory-authority` until that proof is green.

### Safety
- MIG-11 refuses fallback to CFA FRA's local `FrameworkAccount` authority.
- Reference-authority dual-run is rejected rather than comparing incompatible local ORM rows
  with canonical provider results.
- The frozen Sprint-7 consumer still uses local referential tables, so this beta does not claim
  final consumer replacement or retirement readiness.

## [0.6.0b8] - 2026-09-30

### Added
- Target-only CFA FRA closing consumer bridge delegating the single-writer mutation to
  `AccountingApplication.closing.close`.
- `ClosingTargetParametersFactory` for explicit control-run, trial-balance and optional
  opening-balance inputs while canonical period identity comes from the migration identity
  store.
- Fail-closed validation preventing `CommandContext` overrides, conflicting period identity
  and leakage of the legacy period object into the public closing boundary.

### Safety
- The bridge refuses legacy closing execution because Sprint 7 contains no executable closing
  service.
- Mutation dual-write remains structurally impossible through `MigrationRouting`.
- Gate Consumer keeps `closing` BLOCKED until the actual CFA FRA consumer delegates through
  this bridge and produces executable smoke/E2E evidence.

## [0.6.0b7] - 2026-09-30

### Added
- Target-only CFA FRA controls consumer bridge delegating to
  `AccountingApplication.controls.run`.
- `ControlTargetParametersFactory` for explicit control-set/scope mapping while canonical
  organization and fiscal-year identities come from the migration identity store.
- Fail-closed validation preventing `CommandContext` overrides, conflicting canonical IDs
  and leakage of legacy ORM objects into the public controls boundary.

### Safety
- The bridge refuses legacy controls execution because Sprint 7 contains no executable legacy
  controls service.
- Controls dual-run is rejected for the same reason; no comparison baseline is fabricated.
- Gate Consumer keeps `controls` BLOCKED until the actual CFA FRA consumer dashboard delegates
  through this bridge and produces executable smoke/E2E evidence.

## [0.6.0b6] - 2026-09-30

### Added
- Request-level CFA FRA login evidence executed against the frozen Sprint-7 Django application.
- The evidence runner migrates the snapshot's SQLite test database, creates a real user,
  GETs the configured `/login/` route, POSTs credentials through Django `LoginView`, and
  verifies the authenticated session.
- Login evidence is checksummed against the frozen URL configuration and login template.

### Findings
- Request-level authentication succeeds and creates a valid session when the request supplies
  an explicit safe `next` URL.
- The frozen default post-login flow is not release-ready: `LOGIN_REDIRECT_URL = "dashboard"`
  cannot be reversed because the actual route is namespaced as `analytics:dashboard`.
- Login therefore remains BLOCKED alongside controls and closing; the gap is now executable
  and precisely classified rather than inferred from missing tests.

### Boundary
- No file under `resources/cfa_fra_django_mvp_sprint_7/` is modified.
- Consumer E2E remains not-green until login redirect, controls and closing are resolved.

## [0.6.0b5] - 2026-09-30

### Added
- Canonical CI job executing the bundled CFA FRA Sprint-7 Django consumer test harness on
  Python 3.12 with its native SQLite test settings.
- Machine-readable consumer evidence matrix binding Gate Consumer scenarios to real upstream
  pytest files.
- Executable evidence for organization context, FEC import, journal workflow, ledger/balance,
  financial statements and regulatory exports.

### Qualification boundary
- Login remains BLOCKED because the frozen snapshot has user creation and `force_login`
  coverage but no dedicated request-level login-flow test.
- Controls remain BLOCKED because Sprint 7 exposes models/views but no executable controls
  service test.
- Closing remains BLOCKED because the executable Regulatory Controls & Closing Package is
  explicitly scheduled for Sprint 8.
- The consumer evidence CI job must pass, but `consumer_e2e_green` intentionally remains
  false while any of those blockers exists.

## [0.6.0b4] - 2026-09-30

### Added
- Executable CFA FRA consumer-cutover evidence for the ten mandatory Gate Consumer scenarios:
  login, organization context, FEC import, journal, ledger, balance, financial statements,
  controls, closing and exports.
- Deterministic `ConsumerQualificationDecision` distinguishing passed, failed, blocked and
  missing consumer scenarios.
- Fail-closed consumer evidence validation: duplicate scenarios are rejected and every
  non-passing result requires an explicit explanation.

### Safety
- `0.6.0b4` does not claim the external CFA FRA consumer is already green; it defines the
  evidence contract that the consumer smoke/E2E suite must satisfy.
- Legacy retirement can only consume a green consumer qualification after all ten scenarios
  have explicit PASS evidence.

## [0.6.0b3] - 2026-09-30

### Added
- CFA FRA financial-statement consumer conversion for the real Sprint-6 signatures:
  `build_income_statement`, `build_balance_sheet` and `build_cash_flow_statement`.
- `StatementTargetParametersFactory` requiring the consumer to supply explicit public
  statement inputs such as canonical entity identity, trial-balance source and mapping set.
- Fail-closed guards preventing the parameter factory from leaking legacy organization/fiscal
  year objects, overriding `CommandContext` or changing the requested statement kind.
- Read-side financial-statement dual-run using the same shadow-only observation model as ledger
  migration.

### Boundaries
- The bridge does not infer or fabricate a statement source or mapping set from Django ORM state.
- The consumer remains responsible for assembling those explicit target-side dependencies.
- The frozen CFA FRA Sprint-7 oracle remains unchanged.

## [0.6.0b2] - 2026-09-30

### Added
- `CFAFRADjangoConsumerBridge` preserving the real Sprint-7 CFA FRA service signatures for
  `post_journal_entry`, `reverse_journal_entry`, `execute_fec_import` and
  `trial_balance_rows` while delegating migrated operations to `AccountingApplication`.
- Duck-typed legacy object identity extraction with no Django runtime import.
- Explicit legacy-to-canonical identity translation through `LegacyIdentityStoreProtocol`.
- Consumer mapping failures that fail closed before any target-side mutation when a legacy
  identity has not been migrated.

### Changed
- The generic FEC compatibility route now follows the documented public import contract and
  delegates with `batch_id`.
- The trial-balance consumer bridge maps CFA FRA Organization/FiscalYear identities before
  invoking the public ledger namespace.
- The LOT-26 migration now reflects the actual historical CFA FRA service names and signatures,
  rather than only the normalized migration-map examples.

### Boundaries
- Frozen Sprint-7 oracle files remain unchanged.
- Django ORM objects never cross the PyAccountingKit public boundary.
- Financial-statement consumer conversion remains a later slice because the public statement
  contract requires explicit trial-balance source and mapping-set inputs; no translation is
  fabricated in this beta.

## [0.6.0b1] - 2026-09-30

### Added
- LOT-26 `CFAFRACompatibilityAdapter` as a temporary strangler facade from historical CFA FRA
  service signatures into the framework-neutral `AccountingApplication` public API.
- Per-operation migration routing with explicit `LEGACY` and `PYACCOUNTINGKIT` backends.
- Read-side dual-run observations for safe shadow comparison of trial balance, statements,
  controls and other selected queries.
- `LegacyIdentityStoreProtocol`, `LegacyIdentityMap` and immutable `LegacyIdentityLink`
  records preserving historical CFA FRA IDs, target IDs, source identity and optional checksum.
- Fail-closed `LegacyRetirementGate` requiring all routes to be migrated, dual-run to be
  disabled and parity/adapter/consumer/identity evidence to be green before legacy removal.

### Changed
- CFA FRA migration status moves from golden-baseline qualification to consumer conversion.
- Provider-backed `references.get_effective_plan` is the migration path away from local
  regulatory authority.
- Public API manifest wording now records the LOT-26 beta consumer-conversion boundary.

### Safety
- There is deliberately no mutation dual-write mode: posting, reversal, FEC execution and
  closing select exactly one backend.
- Unspecified routes remain on the legacy backend, preventing accidental cutover.
- Dual-run is read-only shadow evidence and never changes the configured primary result.
- Legacy engine retirement remains blocked until consumer parity and smoke/E2E gates are green.

## [0.6.0a1] - 2026-09-29

### Added
- LOT-25 checksummed CFA FRA Sprint 7 behavioral baseline with pinned oracle tree and manifest
  coordinates.
- Component inventory, golden scenario inventory and behavioral baseline required by the CFA FRA
  extraction/migration specification.
- Framework-neutral deterministic golden fixture model with exact Decimal-safe serialization,
  semantic checksums, fail-closed parity comparison and classified intentional divergences.
- Executable CFA FRA golden parity for posting/reversal, French FEC ingestion, the three
  trial-balance variants, income statement, balance sheet and cash flow.
- Canonical journal `EntryType` values: `OPENING`, `NORMAL`, `ADJUSTING`, `CLOSING`
  and `REVERSAL`, persisted by both Production PostgreSQL adapters.
- Django and Alembic migrations extending the stable 0.5 persistence schema with journal
  entry type.

### Changed
- Normal ledger posting now enforces `DRAFT -> VALIDATED -> POSTED`; direct ordinary
  `DRAFT -> POSTED` is rejected.
- Proposal and reviewed import execution explicitly validate materialized entries before the
  canonical `PostingOrchestrator` path.
- Reversal now marks the original journal entry `REVERSED` while preserving it in historical
  ledger queries so the original and posted reversal economically offset one another.
- Trial-balance queries now enforce the CFA FRA-preserved entry-type semantics for
  `BEFORE_ADJUSTMENTS`, `ADJUSTED` and `POST_CLOSING`.
- Public error evidence now includes `ENTRY_INVALID_STATE`.

### Boundaries
- CFA FRA is a migration behavioral oracle, not a runtime dependency or regulatory authority.
- The literal legacy `REV-` numbering convention and `JOD -> ADJUSTING` convention are not
  promoted to universal accounting invariants.
- LOT-27 remains responsible for regulatory Production qualification.
- The bundled Sprint 7 oracle does not contain the planned Sprint 8 Closing Package; LOT-25
  records that absence explicitly and does not fabricate executable closing parity.


## [0.5.0] - 2026-09-23

### Stable
- Promotes the fully qualified `0.5.0rc1` line with no new accounting-domain capability.
- Stabilizes the LOT-21 framework-neutral public facade and immutable public DTO boundary.
- Stabilizes LOT-22 adapter contract v1, typed extension protocols and deterministic manifests.
- Ships both Django/PostgreSQL and SQLAlchemy/PostgreSQL as independently Production-qualified
  optional adapters against PostgreSQL 16.
- Preserves the stable 0.4 subledger/financial-analysis and 0.3 import/reporting/replay evidence.
- Retains core-only installation and import without Django or SQLAlchemy.

### Compatibility
- `0.5.0` is a stable pre-1.0 milestone, not the final 1.0 public API freeze.
- Adapter contract v1 remains the compatibility boundary for Production adapter authors.
- The broader API freeze and 1.0 migration guarantees remain LOT-29/LOT-30 scope.


## [0.5.0] - 2026-09-23

### Stable Promotion
- Promotes the fully qualified `0.5.0rc1` behavior to stable `0.5.0` with no new business
  or adapter implementation changes.
- Stabilizes LOT-21 Public API Facade, LOT-22 extension API / adapter contract v1,
  LOT-23 Django/PostgreSQL and LOT-24 SQLAlchemy/PostgreSQL as one release line.
- Retains both real PostgreSQL 16 Production gates, deterministic manifest checks,
  Python 3.11/3.12/3.13 qualification, package verification and Security gates.
- Retains the stable 0.4 subledger/financial-analysis and stable 0.3
  import/reporting/replay evidence.
- Public API metadata is promoted from release-candidate to
  `pre-1.0-stable-release`; the broader 1.0 API freeze remains a later hardening milestone.


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
