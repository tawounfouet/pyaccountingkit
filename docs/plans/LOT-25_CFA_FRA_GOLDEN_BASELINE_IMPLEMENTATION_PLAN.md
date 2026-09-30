# LOT-25 — CFA FRA Golden Baseline & Parity Qualification

Target: `0.6.0a1`

Baseline: stable `0.5.0` at `0d3e513957d87154d1ada2875c4c832cb51c1dbc`.

## Purpose

LOT-25 freezes CFA FRA Sprint 7 as a behavioral oracle and converts its accounting behavior
into normalized, deterministic golden evidence. It does **not** yet introduce the LOT-26
Strangler compatibility adapter and does not make CFA FRA a runtime dependency.

Oracle snapshot:

- path: `resources/cfa_fra_django_mvp_sprint_7/`;
- tree SHA: `07d4880534d2e2239e19fd4ef4139de70b56773a`;
- manifest version: `0.8.0`;
- implemented source sprints: 0 through 7.

## Scope

The roadmap requires consolidated parity evidence for:

- normalized golden fixtures;
- posting;
- reversal;
- FEC import;
- journal / general ledger / trial-balance variants;
- financial statements;
- controls;
- closing;
- analysis scenarios where the Sprint 6 oracle is authoritative.

## Explicit boundaries

- No import from `resources/cfa_fra_django_mvp_sprint_7` at package runtime.
- No Django model is copied into the domain.
- No MVP convention is promoted to a universal invariant without an existing PyAccountingKit rule.
- No dual-write mutation.
- Regulatory framework certification remains LOT-27.
- Consumer conversion and legacy retirement remain LOT-26.
- The Sprint 7 snapshot does not yet implement the planned Sprint 8 closing package; closing
  evidence in LOT-25 must therefore distinguish executable oracle behavior from documented-only
  expectations.

## Deliverables

1. `docs/plans/cfa_fra/01_CFA_FRA_COMPONENT_INVENTORY.md`
2. `docs/plans/cfa_fra/02_CFA_FRA_GOLDEN_SCENARIO_INVENTORY.md`
3. `docs/plans/cfa_fra/03_CFA_FRA_BEHAVIORAL_BASELINE.md`
4. framework-neutral golden fixture model under `pyaccountingkit.integrations.cfa_fra`;
5. deterministic fixture checksum and exact parity comparison;
6. versioned JSON golden assets under `tests/golden/cfa_fra/fixtures/`;
7. executable LOT-25 golden tests;
8. explicit intentional-divergence registry support;
9. `0.6.0a1` release metadata after qualification.

## Initial fixture set

The first executable baseline must cover behavior already present in the bundled oracle:

- strict DRAFT → VALIDATED → POSTED workflow;
- direct DRAFT → POSTED rejection;
- reversal creates a posted inverse entry and marks the original REVERSED;
- FEC raw preservation / checksums / blocking-vs-warning semantics;
- FEC grouping and exact balance totals;
- BEFORE_ADJUSTMENTS / ADJUSTED / POST_CLOSING balance semantics;
- statement equations and drill-down semantics.

## Parity semantics

Parity is semantic, not implementation-level.

Equivalent values may have different internal IDs or framework objects. A golden observation
therefore compares only normalized fields explicitly declared by its fixture schema.

Monetary data is serialized as decimal strings. Binary floats are rejected from fixture
payloads.

## Intentional divergence protocol

Every accepted mismatch must carry:

- stable divergence ID;
- category: `BUG_FIX`, `GENERALIZATION`, `REGULATORY_CORRECTION`,
  `PORTABILITY_CHANGE`, `SAFETY_HARDENING` or `API_REDESIGN`;
- oracle behavior;
- PyAccountingKit behavior;
- rationale;
- migration impact;
- ADR/reference.

Unregistered mismatches fail the golden test.

## Gates

- GC
- GI
- GS
- CFA golden suite
- ordinary Quality / Python 3.11-3.13 / package / Security gates retained.

## Exit criteria

- [ ] oracle identity pinned;
- [ ] component inventory complete for Sprint 0..7 accounting-relevant modules;
- [ ] golden scenario inventory complete and prioritized;
- [ ] behavioral baseline records known MVP conventions and non-universal rules;
- [ ] deterministic fixture model implemented;
- [ ] at least posting/reversal, FEC and ledger golden scenarios executable;
- [ ] no undocumented parity mismatch;
- [ ] no runtime import of the legacy resource;
- [ ] Python 3.11 / 3.12 / 3.13 green;
- [ ] Ruff / strict mypy / package / Security green.
