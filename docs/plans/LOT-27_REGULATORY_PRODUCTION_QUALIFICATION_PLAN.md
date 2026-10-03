# LOT-27 — Regulatory Production Qualification

**Target line:** `0.7.0`  
**Current slice:** `0.7.0rc1` — regulatory GR/G4 release candidate  
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

## 0.7.0a2 scope

The second slice productionizes `fr-nonprofit:2026` without duplicating the upstream
regulatory resolution algorithm.

The provider consumes the already-resolved upstream effective plan directly:

```text
fr-pcg:2026
      +
official Art. 320-2 extension
      ↓ resolved upstream
fr-nonprofit:2026 effective plan
      ↓ consumed directly
PyAccountingKit
```

Qualified evidence:

- 901 effective accounts/groups;
- 785 inherited accounts/groups;
- 43 source-backed overrides;
- 73 source-backed additions;
- 116 overlay entries retained for provenance and explanation;
- deterministic replayable effective-plan snapshots;
- public additive `EffectivePlanReferenceProviderProtocol`.

Capability status after this slice:

```text
EFFECTIVE_PLAN              PRODUCTION_QUALIFIED / executable
SNAPSHOTS                   PRODUCTION_QUALIFIED / executable
OVERLAYS                    VALIDATED / non-executable
REPORTING_STRUCTURE         VALIDATED
REPORTING_ACCOUNT_MAPPINGS  REVIEW_REQUIRED / non-executable
```

The overlay is **not** a runtime plan-building mechanism. PyAccountingKit never rebuilds the
effective plan by replaying PCG plus overlay entries when the resolved plan exists.

## 0.7.0a3 scope

The third slice productionizes the OHADA EBNL 2023 structural graph and standard-family relation
runtime without inventing semantic inheritance or account equivalence.

Qualified structural evidence:

- 1,145 graph nodes;
- 9 root classes;
- 2 explicit class-9 scopes;
- 84 groups;
- 1,050 account occurrence nodes;
- 1,049 unique account codes;
- duplicate source code `4555` preserved as `occ01` and `occ02`;
- deterministic replayable structural snapshots.

The standard-relation runtime consumes the canonical OHADA relation dataset directly:

```text
explicit relation edge
      ↓
queryable relation provider
      ↓
auto_inference_allowed flag

negative constraint
      ↓
fail-closed runtime guard
```

No absence of prohibition is treated as permission to infer. Automatic inference requires an
explicit relation whose `auto_inference_allowed` flag is true. The current OHADA corpus sets that
flag to false for every relation.

Capability status after this slice:

```text
ohada-ebnl:2023
  STRUCTURE             PRODUCTION_QUALIFIED
  SNAPSHOTS             PRODUCTION_QUALIFIED
  RELATIONS             PRODUCTION_QUALIFIED
  NEGATIVE_CONSTRAINTS  FORBIDDEN_INFERENCE / runtime-enforced
  CROSSWALKS            REVIEW_REQUIRED
  REPORTING_STRUCTURE   DISCOVERED

ohada-syscohada:2017
  RELATIONS             PRODUCTION_QUALIFIED

cemac-pcemf:2010
  RELATIONS             PRODUCTION_QUALIFIED
  NEGATIVE_CONSTRAINTS  FORBIDDEN_INFERENCE / runtime-enforced
  STRUCTURE             NOT_ASSERTED
  CROSSWALKS            NOT_ASSERTED
```

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

## 0.7.0b1 scope

The beta slice makes the reviewed EBNL/SYSCOHADA structural delta queryable while keeping every
candidate outside the executable mapping path. Code equality and normalized-label equality are
evidence for review only, never semantic equivalence.

PCEMF/SYSCOHADA safety is intentionally asymmetric: the bundled corpus contains no PCEMF
crosswalk dataset, so `CROSSWALKS` remains `NOT_ASSERTED`. Existing source-backed negative
constraints forbid PCEMF→SYSCOHADA inheritance inference. Missing evidence is never converted
into a candidate or executable mapping.

## Beta and release-candidate slices

### 0.7.0b2 — implemented

The beta-2 slice production-qualifies provider-backed reporting structure where the bundled
regulatory corpus contains fully materialized line-level models:

- PCG 2026: 4 templates / 158 lines;
- SYSCOHADA 2017: balance 48, income 34, cash-flow 23 and notes 46 lines;
- France Non-Profit 2026: 4 templates / 160 lines, including 33 lines carrying review-only
  account hints.

The filesystem provider implements the existing exact-coordinate
`ReferenceReportingModelProviderProtocol`. Dataset bytes pin the reference snapshot checksum.
Account hints and PCG mapping expressions are preserved only as review evidence and are never
made executable.

OHADA EBNL 2023 remains non-executable for `REPORTING_STRUCTURE`: the source dataset explicitly
marks its statement models as visually bound but not exhaustively transcribed at line level.

`REPORTING_ACCOUNT_MAPPINGS` remains `REVIEW_REQUIRED`. `EXPORTS` remains unpromoted until
provider-backed regulatory export evidence exists.

### 0.7.0b3 — implemented

The beta-3 slice does not expand regulatory support. It makes the release-candidate boundary
executable and fail-closed:

- `0.7.0rc1` has an explicit versioned evidence contract;
- an unregistered RC version fails qualification instead of falling back to zero evidence;
- `release/0.7*` skips LOT-26 CFA FRA jobs and requires the dedicated LOT-27 release path;
- `release/0.6*` retains its bound-consumer and live-retirement gates;
- `scripts/validate_regulatory_gate.py` executes GR invariants against the committed matrix;
- `scripts/validate_documentation.py` checks active release documentation and local links;
- `SNAPSHOT_SCHEMA_MANIFEST.json` records deterministic public snapshot/dataclass and enum shape;
- the existing sealed `RELEASE_QUALIFICATION_MANIFEST.json` remains the publication artifact.

No status in `REGULATORY_COMPATIBILITY_MATRIX.json` is promoted by this slice.

### 0.7.0rc1 — qualification candidate

The release candidate must qualify **GR + G4** on the `0.7` release line. `G5` is
reserved for the final stable `0.7.0` promotion and must not be claimed by the RC.

RC qualification contract:

- execute the dedicated `release/0.7*` path on this exact `0.7.0rc1` checkout;
- require GR and G4 to remain green on the exact RC commit;
- keep the compatibility matrix capability set identical to the qualified `b3` baseline;
- require the sealed release-bundle qualification manifest at publication time;
- promote zero unsupported capability.

Only after `0.7.0rc1` satisfies G4 can the stable `0.7.0` line proceed to G5.

## Relationship with LOT-26

LOT-26 remains externally incomplete because its canonical live CFA FRA consumer binding and live
cutover evidence are deferred. LOT-27 development proceeds in parallel by explicit user decision.

This does **not** retroactively declare `0.6.0` stable and does not fabricate LOT-26 evidence.
