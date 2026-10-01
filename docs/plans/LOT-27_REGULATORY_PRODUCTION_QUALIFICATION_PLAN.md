# LOT-27 — Regulatory Production Qualification

**Target line:** `0.7.0`  
**Current slice:** `0.7.0a1` — capability-scoped qualification foundation  
**Upstream regulatory corpus:** `regulatory-accounting-data-framework 0.7.1`

## Objective

Turn regulatory support from broad framework-level claims into explicit, auditable qualification
records per standard and per capability.

A standard is never globally `SUPPORTED=true`. Each capability is qualified independently.

## Capability model

```text
STRUCTURE
EFFECTIVE_PLAN
OVERLAYS
RELATIONS
CROSSWALKS
NEGATIVE_CONSTRAINTS
CONCEPTS
CONCEPT_BINDINGS
REPORTING_STRUCTURE
REPORTING_ACCOUNT_MAPPINGS
POLICIES
EXPORTS
SNAPSHOTS
```

Each `RegulatoryCapabilityQualification` records:

```text
standard_ref
capability_code
provider_version
dataset_release
framework_version
status
evidence_refs
executable
human_review_required
auto_inference_allowed
test_suite
golden_refs
reviewer
qualified_at
notes
```

## Status taxonomy

```text
NOT_ASSERTED
DISCOVERED
INGESTIBLE
VALIDATED
CANDIDATE
REVIEW_REQUIRED
EXECUTABLE
PRODUCTION_QUALIFIED
FORBIDDEN_INFERENCE
```

## 0.7.0a1 scope

The first slice establishes five explicit profiles:

- `fr-pcg:2026`;
- `fr-nonprofit:2026`;
- `ohada-syscohada:2017`;
- `ohada-ebnl:2023`;
- `cemac-pcemf:2010`.

Only already demonstrated PyAccountingKit structure/snapshot capabilities for PCG and SYSCOHADA
are promoted to `PRODUCTION_QUALIFIED`.

The slice intentionally keeps:

- Non-Profit automatic reporting mappings at `REVIEW_REQUIRED`;
- EBNL/SYSCOHADA structural crosswalks at `REVIEW_REQUIRED`;
- EBNL and PCEMF inheritance inference explicitly forbidden;
- missing PCEMF structure support at `NOT_ASSERTED`;
- missing concept bindings at `NOT_ASSERTED`.

## Generated compatibility matrix

`REGULATORY_COMPATIBILITY_MATRIX.json` is generated deterministically from the canonical
qualification profiles.

```bash
python scripts/generate_regulatory_compatibility_matrix.py --check
```

Any handwritten drift fails release qualification.

## Golden safety

The LOT-27 golden suite verifies:

- PCG and SYSCOHADA structure/snapshot production qualification;
- Non-Profit effective-plan statistics;
- `account_hints_executable=false`;
- `human_validation_required=true`;
- OHADA negative inheritance constraints;
- zero automatic concept bindings;
- absence of global `SUPPORTED` claims.

## Deferred slices

### 0.7.0a2

- production provider support for `fr-nonprofit:2026`;
- effective-plan adapter contract;
- overlay provenance contract;
- snapshot qualification for Non-Profit.

### 0.7.0a3

- EBNL provider structure qualification;
- OHADA relation provider;
- negative-constraint runtime contract.

### 0.7.0b1

- reviewed crosswalk model;
- EBNL/SYSCOHADA and PCEMF/SYSCOHADA safety;
- candidate vs executable mapping boundary.

### 0.7.0b2

- reporting-structure production qualification;
- mapping-review evidence;
- export capability qualification where actually supported.

### 0.7.0rc1

- full GR/G4/G5 qualification;
- compatibility matrix final review;
- zero unsupported capability promotion.

## Relationship with LOT-26

LOT-26 remains externally incomplete because its canonical live CFA FRA consumer binding and live
cutover evidence are deferred. LOT-27 development proceeds in parallel by explicit user decision.

This does **not** retroactively declare `0.6.0` stable and does not fabricate LOT-26 evidence.
