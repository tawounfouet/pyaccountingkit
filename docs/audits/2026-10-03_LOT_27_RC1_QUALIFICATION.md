# LOT-27 — 0.7.0rc1 Qualification

> Date: 2026-10-03  
> Scope: GR + G4 release-candidate qualification  
> Stable G5 claim: **not made**

## Qualified identity

```text
release branch      release/0.7.0rc1
pull request        #68
qualified head      bb90fd840031aeb8b8d488e3a79d9506f7edfb9b
main merge          e7c686527d8d90cdfa4dca8b454617747893e00a
package version     0.7.0rc1
```

## GitHub qualification

```text
CI run              #570   PASS
Security run        #573   PASS
LOT-27 RC job              PASS
Canonical CI gate          PASS
```

The release-line scheduling proof is material:

- core Quality, Python 3.11/3.12/3.13, package, PostgreSQL adapters and regulatory qualification ran;
- LOT-27 release-candidate qualification ran and passed;
- LOT-26 extended release qualification was skipped;
- the twelve CFA FRA migration/retirement jobs were skipped on the `release/0.7*` line;
- no deferred CFA FRA live evidence was synthesized.

## GR / G4 evidence

The RC validated:

- deterministic regulatory compatibility matrix generation;
- deterministic snapshot-schema manifest generation;
- active documentation/version checks;
- source-backed and review-preserving regulatory constraints;
- fail-closed unknown-RC registration;
- integration, golden, replay and concurrency suites;
- package build verification;
- canonical CI aggregation.

## Frozen capability boundary

The RC did not promote unsupported semantics:

```text
PCG 2026 reporting structure             PRODUCTION_QUALIFIED
France Non-Profit reporting structure    PRODUCTION_QUALIFIED
SYSCOHADA 2017 reporting structure       PRODUCTION_QUALIFIED

reporting account mappings               REVIEW_REQUIRED
OHADA EBNL reporting structure           DISCOVERED
OHADA EBNL crosswalk                     REVIEW_REQUIRED
PCEMF crosswalk                          NOT_ASSERTED
automatic semantic inference             forbidden
```

## Remaining G5 blocker

The repository still records `MAIN_BRANCH_PROTECTION_UNENFORCED` as an open external control. Consequently this audit does **not** claim:

- `0.7.0` stable;
- stable tag creation;
- PyPI publication;
- GitHub Release publication;
- immutable-tag proof.

Those belong to G5 after the external control is actually closed.
