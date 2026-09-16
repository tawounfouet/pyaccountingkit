# Release 0.3.0rc1 — Cross-Lot Qualification Plan

## 1. Objective

`0.3.0rc1` is not a new accounting feature lot. It is the release-candidate qualification of the complete `0.3.x` value chain delivered by LOT-14 through LOT-17 on top of the already-qualified ledger, reference, chart and policy foundations.

The release candidate must demonstrate that independently qualified components compose correctly without introducing a second accounting source of truth, bypassing posting invariants, losing source lineage, weakening entity isolation or breaking deterministic replay.

Canonical release chain:

```text
FEC / SourceArtifact
        |
        v
FECAdapter
  parse -> normalize -> validate -> group
        |
        v
ImportPlan
        |
        v
ImportExecutionService
        |
        v
PostingOrchestrator
        |
        v
Posted Ledger
        |
        v
TrialBalance
        |
        v
FinancialStatementEngine
        |
        v
ReportSnapshot (PUBLISHED)
        |
        v
RegulatoryReportingProfile
+ ReferenceReportingModel
+ validated RegulatoryMappingSet
        |
        v
RegulatoryReport
        |
        v
RegulatoryValidation
        |
        v
RegulatoryExportArtifact
        |
        v
ReportEvidenceBundle
        |
        v
Deterministic replay qualification
```

## 2. Baseline

- Base release: `0.3.0b2`
- Base merge: `8b9ff70869043177115f6814de62c87beb95e19b`
- Branch: `release/0.3.0-rc1`
- Target version: `0.3.0rc1`
- Roadmap stable gate: Release `0.3.0 — Imports & Reporting`

No LOT-18 / `0.4.x` domain work belongs in this branch.

## 3. Release invariants

### R1 — One accounting source of truth

Imports may produce `JournalEntry` objects only through the canonical import plan and `PostingOrchestrator`. Financial and regulatory reporting are projections only and must never post, reverse or mutate ledger data.

### R2 — Source evidence remains connected to ledger effects

The FEC source checksum, raw records, normalized source-entry identity and deterministic import entry IDs must remain sufficient to demonstrate that the same source cannot silently create duplicate accounting effects.

### R3 — AccountingEntity isolation is end-to-end

Entity identity must remain coherent across import plan, journal/period/chart, posted ledger, Trial Balance, financial mappings/snapshot and regulatory profile/mappings.

### R4 — Version/snapshot coordinates are explicit

The integrated path must pin the relevant chart, statement definition, statement mapping, report snapshot, regulatory profile, reference model and regulatory mapping coordinates. No implicit `latest` resolution is acceptable in replay-sensitive paths.

### R5 — Candidate metadata never becomes executable implicitly

Candidate financial mappings, regulatory candidate mappings and reference account hints remain non-executable until an explicit validated transition/provenance exists.

### R6 — Replay is content-deterministic

Given the same accounting source and pinned semantic coordinates, the accounting/reporting content checksums must replay identically. Technical timestamps or generated evidence IDs must not alter semantic report/export checksums where the contract defines content determinism.

### R7 — Failure must remain fail-closed

A stale import plan, wrong entity, non-effective definition/profile, mismatched snapshot, unmapped blocking reporting node or non-executable mapping must fail rather than be guessed or silently repaired.

## 4. Qualification gaps to close

The `0.3.0b2` baseline already has strong unit/property/contract/golden/replay/concurrency coverage, but `tests/integration/` contains no executable integration scenario. Therefore the release candidate must add a real cross-lot integration gate instead of declaring Integration `NOT APPLICABLE`.

The RC work is intentionally test- and release-focused. Production-domain changes are allowed only if the integrated scenario exposes a genuine contract defect.

## 5. Implementation phases

### Phase A — Cross-lot integration scenario

Add an executable integration test using real production components wherever an in-memory production adapter exists.

Minimum scenario:

1. construct a deterministic two-line FEC source artifact;
2. parse and normalize through `FECAdapter`;
3. verify source evidence and FEC validation;
4. construct the reviewed `ImportPlan` from normalized source identity and explicit account/journal mappings;
5. execute through `ImportExecutionService` and the real `PostingOrchestrator`/in-memory UoW;
6. verify one posted accounting effect and idempotent replay behavior;
7. build the Trial Balance from posted ledger state;
8. project a versioned Balance Sheet through `FinancialStatementEngine`;
9. publish/seal a `ReportSnapshot`;
10. project the snapshot through LOT-17 regulatory reporting;
11. validate and render the regulatory report;
12. seal the evidence bundle;
13. assert entity, source, version and checksum lineage at each boundary.

The scenario should use a deliberately small synthetic accounting example. It is a composition test, not a claim that the fixture is an official statutory filing template.

### Phase B — End-to-end replay scenario

Add replay qualification proving that two fresh executions of the same source and pinned semantic coordinates produce the same relevant identities/checksums:

- deterministic imported journal-entry ID;
- Trial Balance checksum;
- financial report result/snapshot semantic checksum;
- regulatory report checksum;
- regulatory validation checksum;
- export payload checksum;
- evidence semantic checksum according to the LOT-17 contract.

Also verify same-store import replay does not duplicate the posted accounting effect.

### Phase C — Release-candidate gate contract

Strengthen `scripts/qualify_release.py` so a release-candidate qualification cannot silently pass with a missing integration suite.

Introduce an explicit release-candidate mode (preferred: `--release-candidate`) that:

- runs all core gates;
- runs `tests/integration`, `tests/golden`, `tests/replay`, and `tests/concurrency`;
- treats a missing/empty required suite as a qualification failure;
- prints the canonical version and mode in the final report.

`--full` may remain useful for general development and can retain its current conditional behavior if backward compatibility is desirable.

CI remains the canonical Python 3.11/3.12/3.13 matrix. The release-candidate mode is an additional explicit local/release gate, not a duplicate CI implementation.

### Phase D — Release metadata

After all functional gates are green:

- bump `pyproject.toml` to `0.3.0rc1`;
- align `PUBLIC_API_MANIFEST.json`;
- align `PUBLIC_ERROR_CODES.json` if new codes were actually required;
- align `ADAPTER_CONTRACT_MANIFEST.json`;
- align `REGULATORY_COMPATIBILITY_MATRIX.json`;
- add `0.3.0rc1` changelog/release qualification notes;
- update README status and qualification command;
- keep public API stability explicitly pre-1.0 / release-candidate, not stable by implication.

## 6. Non-goals

The following are explicitly out of scope for this release candidate:

- LOT-18 subledger domain objects;
- accounts receivable/payable;
- production SQL/database adapters not already delivered;
- new regulatory frameworks;
- claiming legal certification of PCG, SYSCOHADA or FEC authority submissions;
- creating an alternative posting path for import convenience;
- changing core accounting semantics solely to simplify the integration test.

## 7. Required qualification matrix

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
[ ] integration suite (mandatory for RC)
[ ] golden suite
[ ] replay suite
[ ] concurrency suite
[ ] Python 3.11 CI
[ ] Python 3.12 CI
[ ] Python 3.13 CI
[ ] Security dependency audit
[ ] Security static analysis
```

## 8. Release 0.3.0 roadmap gates mapped to evidence

Roadmap requirement: `FEC contract/golden/rollback/idempotency/concurrency green`.

Evidence target:
- existing FEC unit/contract tests;
- cross-lot real import integration;
- existing posting rollback/concurrency suites;
- same-source deterministic import ID and replay assertion.

Roadmap requirement: `statement golden suite green`.

Evidence target:
- LOT-16 financial statement deterministic/golden behavior;
- cross-lot Balance Sheet projection from the imported ledger state.

Roadmap requirement: `regulatory mapping safety green`.

Evidence target:
- LOT-17 candidate/reference-hint guards;
- PCG/SYSCOHADA golden scenarios;
- integrated validated mapping path.

Roadmap requirement: `report replay green`.

Evidence target:
- LOT-17 regulatory replay;
- new cross-lot replay from source/import through evidence.

## 9. Merge policy

The RC pull request remains Draft until:

1. the mandatory integration scenario exists;
2. cross-lot replay is green;
3. release-candidate qualifier is green;
4. canonical CI is green on Python 3.11, 3.12 and 3.13;
5. package qualification is green;
6. Security is green;
7. release metadata is coherent at `0.3.0rc1`.

Only then may the PR move to Ready and be squash-merged into `main`.

## 10. Exit criterion

`0.3.0rc1` is qualified when PyAccountingKit can demonstrate, with executable tests, that a source accounting artifact can enter through the import boundary, become canonical posted ledger state, drive financial and regulatory reporting, produce sealed evidence, and replay deterministically without bypassing accounting invariants or losing entity/version/snapshot lineage.
