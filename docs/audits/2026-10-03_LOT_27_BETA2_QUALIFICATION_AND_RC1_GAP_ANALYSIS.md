# LOT-27 — 0.7.0b2 Qualification and 0.7.0rc1 Gap Analysis

**Date:** 2026-10-03  
**Repository:** `tawounfouet/pyaccountingkit`  
**Qualified beta:** `0.7.0b2`  
**Current main after documentation reconciliation:** `f96b332e45f165c4d2af6d22e1ac97330d527eda`

## 1. Qualified implementation

PR #63 (`feat: qualify LOT-27 reporting structures (0.7.0b2)`) was qualified on exact
head `327eec75622b05ad23b466f5ad48945f5b160a18`.

Evidence from GitHub Actions:

- CI #554: SUCCESS;
- Security #557: SUCCESS;
- Canonical CI gate: SUCCESS;
- Python 3.11 / 3.12 / 3.13: SUCCESS;
- package qualification: SUCCESS;
- Django/PostgreSQL qualification: SUCCESS;
- SQLAlchemy/PostgreSQL qualification: SUCCESS;
- Quality gates: SUCCESS;
- Regulatory capability qualification: SUCCESS.

PR #63 was squash-merged as
`fc2c4608bfb8632773ce3852a317ce08446d603e`.

PR #64 then reconciled the active README and implementation-plan index with the qualified beta.
It was qualified on `e88c4dd79795e23f5f4f912f5353ad28a0ef1289`:

- CI #556: SUCCESS;
- Security #559: SUCCESS;
- Canonical CI gate: SUCCESS.

PR #64 was squash-merged as
`f96b332e45f165c4d2af6d22e1ac97330d527eda`.

The GitHub connector used for this qualification exposes PR-triggered workflow runs. It does not
surface push-triggered post-merge runs for a commit, so no additional post-merge CI claim is made.
The merged `main` content was instead re-read directly and checked for version/profile coherence.

## 2. 0.7.0b2 regulatory boundary

The beta production-qualifies provider-backed reporting **structure** only where the upstream
corpus contains materialized source lines.

| Standard | Reporting structure | Account mappings | Other relevant boundary |
| --- | --- | --- | --- |
| PCG 2026 | `PRODUCTION_QUALIFIED` | `REVIEW_REQUIRED` | concepts remain non-executable where bindings are absent |
| France Non-Profit 2026 | `PRODUCTION_QUALIFIED` | `REVIEW_REQUIRED` | 33 account-hint lines remain review-only |
| SYSCOHADA 2017 | `PRODUCTION_QUALIFIED` | `REVIEW_REQUIRED` | source line identities preserved |
| OHADA EBNL 2023 | `DISCOVERED` | not promoted | source explicitly lacks exhaustive line transcription |
| CEMAC PCEMF 2010 | not asserted | not asserted | no reporting provider fabricated |

`EXPORTS` remains unpromoted because no provider-backed regulatory export proof has been
qualified.

## 3. Corrections made during beta qualification

The qualification loop corrected defects before merge rather than converting them into evidence:

- repaired a malformed literal newline in the qualification baseline;
- removed an artificial future qualification timestamp;
- replaced a misleading canonical-CI reviewer claim with reporting-specific qualification metadata;
- removed label-based inference of reporting node semantics;
- introduced explicit `UNSPECIFIED` node/value categories where the source does not define them;
- removed synthetic line identifiers;
- preserved exact PCG statement identities;
- preserved exact SYSCOHADA `line_id` identities where source reference codes are not unique;
- handled SYSCOHADA notes using their actual source list/`note_id` representation;
- aligned the top-level compatibility-matrix version and active manifests to `0.7.0b2`;
- added the reporting provider to the adapter contract manifest;
- added explicit golden and CI coverage for provider-backed reporting structures.

## 4. Fail-closed guarantees retained

The beta does **not** infer support from dataset presence.

- EBNL reporting remains non-executable.
- Reporting mappings remain `REVIEW_REQUIRED`.
- Crosswalk candidates remain non-executable.
- PCEMF/SYSCOHADA crosswalk support remains `NOT_ASSERTED`.
- Missing concept bindings stay unresolved.
- Negative OHADA inheritance constraints remain enforced.
- No code equality or normalized-label equality becomes semantic equivalence.
- No regulatory export capability is claimed without provider-backed proof.

## 5. Actual gap to 0.7.0rc1

The current beta is green, but the repository does not yet have a truthful dedicated
`0.7.0rc1` release path.

### 5.1 Release-candidate evidence registry

`scripts/qualify_release.py` registers version-specific RC evidence only through
`0.6.0rc1`. An unknown RC version currently falls back to an empty evidence tuple.

**Required correction:** register explicit `0.7.0rc1` evidence and fail closed for unknown RC
versions.

### 5.2 Release workflow coupling

The current `release-qualification` workflow is selected for every `release/*` branch but its
preconditions are CFA FRA / LOT-26 live-consumer and retirement checks.

**Required correction:** split release-line qualification so that:

- `release/0.6` retains its CFA FRA live gates;
- `release/0.7` qualifies LOT-27 through regulatory GR/G4 evidence;
- deferred LOT-26 external evidence does not block LOT-27;
- no fake CFA FRA live evidence is generated to satisfy a 0.7 release.

### 5.3 G4 evidence still to make explicit

The canonical CI already exercises the full Python matrix, real PostgreSQL adapters,
migration/concurrency suites, golden/replay suites, manifests and package verification.

The sealed release pipeline already produces and re-verifies
`RELEASE_QUALIFICATION_MANIFEST.json`; no second committed manifest is required.

The beta-3 hardening therefore makes the remaining pre-RC evidence executable:

- active documentation/version and local-link validation;
- deterministic snapshot-schema compatibility manifest;
- explicit regulatory GR validation;
- a dedicated `release/0.7*` qualification path that reaches the existing release machinery
  without requiring LOT-26 CFA FRA live evidence.

### 5.4 GR

The RC path must prove, not merely document:

- reference identities preserved;
- source snapshot checksums preserved;
- negative constraints preserved;
- candidate != executable;
- human-review flags preserved;
- no code-equality semantic inference.

## 6. Gate interpretation

For LOT-27:

```text
0.7.0b2
   ↓
GR + G4
   ↓
0.7.0rc1
   ↓
G5
   ↓
0.7.0 stable
```

G5 is a **stable-release gate** and must not be claimed by `0.7.0rc1`.

## 7. Relationship with LOT-26

LOT-26 live CFA FRA external evidence remains explicitly deferred. This audit does not claim that
`0.6.0` is stable and does not manufacture live consumer/cutover proof.

LOT-27 may continue independently because its regulatory qualification evidence is provider-backed
and separately gated.

## 8. Next implementation slice

The next real slice is **`0.7.0b3 — RC Gate Hardening`**:

1. fail-closed RC version registration;
2. explicit `0.7.0rc1` evidence contract;
3. separate `release/0.7` qualification job;
4. executable GR qualification;
5. remaining G4 evidence automation;
6. complete CI qualification before any RC version promotion.

No new regulatory capability should be promoted merely to make the matrix look fuller.
