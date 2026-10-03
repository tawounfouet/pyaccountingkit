# Release 0.7.0 — Stable Promotion Plan

## Objective

Promote the fully qualified `0.7.0rc1` LOT-27 line to stable `0.7.0` with **zero new regulatory capability and zero new business behavior**.

RC baseline:

```text
PR                 #68
RC head            bb90fd840031aeb8b8d488e3a79d9506f7edfb9b
RC merge on main   e7c686527d8d90cdfa4dca8b454617747893e00a
CI                 #570 PASS
Security           #573 PASS
Canonical CI gate  PASS
LOT-27 RC job       PASS
```

## Promotion invariants

- no domain or adapter implementation changes;
- the five reviewed LOT-27 regulatory profiles remain the complete profile set;
- reporting account mappings remain `REVIEW_REQUIRED` and non-executable;
- OHADA EBNL reporting remains `DISCOVERED` and non-executable;
- EBNL/SYSCOHADA crosswalk candidates remain review-only;
- PCEMF crosswalks remain `NOT_ASSERTED`;
- no automatic semantic inference is enabled;
- exports are not promoted without provider-backed evidence;
- LOT-26 live CFA FRA evidence remains deferred and is not rewritten as green evidence;
- public API stability changes only from release-candidate metadata to stable pre-1.0 metadata.

## G5 contract

Stable promotion requires all of the following on the exact stable PR head:

```text
G4 green
0 BLOCKER
0 CRITICAL
no critical flaky tests
release notes complete
migration guide complete where applicable
public API manifest stable
regulatory matrix published
snapshot schema manifest published
artifact checksums generated
tag immutable
publication smoke green
```

The executable pre-tag gate is `python scripts/validate_stable_gate.py`.

## Current external blockers

At the RC merge baseline, LOT-00 still records:

```text
MAIN_BRANCH_PROTECTION_UNENFORCED = OPEN
overall_status = BLOCKED_EXTERNAL_CONTROL
```

Therefore the stable validator **must return non-zero** until GitHub main-branch protection (or an equivalent ruleset) has been enabled and the canonical LOT-00 status has been re-attested.

No stable tag, PyPI publication or GitHub Release may be claimed while that blocker is open.

G5 also records `IMMUTABLE_RELEASES_UNVERIFIED = OPEN` until GitHub release immutability is enabled and observed before `v0.7.0` is created. This control is intentionally separate because release immutability applies only to future releases.

## Migration impact

Migration impact: none.

The stable promotion changes release identity and publication metadata only. There is no new runtime API, persistence migration, regulatory mapping promotion or provider behavior relative to the qualified `0.7.0rc1` baseline.

## Publication boundary

After the stable PR is green and merged:

1. create the exact tag `v0.7.0` on the qualified `main` commit;
2. release preflight verifies tag/version/main ancestry;
3. build one wheel/sdist pair;
4. seal SHA-256 checksums and `RELEASE_QUALIFICATION_MANIFEST.json`;
5. publish the exact bundle to PyPI;
6. install `pyaccountingkit==0.7.0` from PyPI in the publication-smoke job;
7. publish the exact GitHub Release assets;
8. verify release immutability before G5 is considered fully closed.

## Exit criterion

`0.7.0` is stable only when the exact stable commit has green canonical/security/stable gates and the publication workflow has completed with checksums, immutable release integrity and publication smoke evidence.

A version bump alone is never sufficient.
