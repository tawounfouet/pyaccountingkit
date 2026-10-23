# Release 0.7.0 — Stable Promotion Plan

## Objective

Promote the fully qualified **`0.7.0rc2` REM-10 remediation line** to stable `0.7.0` with
**zero new regulatory capability and zero new business behavior after the RC2 freeze**.

RC2 baseline:

~~~text
PR                 #94
RC branch head     c44fdaa579674a36430aadec2245380550b8c0ed
RC merge on main   0364b966fb57df97f4e8a2166b52ec99eaae0f20
CI                 39886182878 PASS
Security           39886182869 PASS
Canonical CI gate  PASS
REM-10 RC job       PASS
REM-10 decision     QUALIFIED_RC2
Findings            30 VERIFIED / 0 OPEN
~~~

The audit baseline was `0.7.0rc1`. RC2 contains the remediation implementation accumulated through
REM-01..REM-09 and its transverse REM-10 qualification. The **stable promotion from RC2 onward**
must be metadata/release-governance only.

## Promotion invariants

From the qualified RC2 baseline to stable:

- no domain or adapter implementation changes;
- no new accounting behavior;
- no new persistence schema or migration;
- no new public API behavior beyond stable release metadata;
- the five reviewed LOT-27 regulatory profiles remain the complete profile set;
- reporting account mappings remain `REVIEW_REQUIRED` and non-executable;
- OHADA EBNL reporting remains `DISCOVERED` and non-executable;
- EBNL/SYSCOHADA crosswalk candidates remain review-only;
- PCEMF crosswalks remain `NOT_ASSERTED`;
- no automatic semantic inference is enabled;
- exports are not promoted without provider-backed evidence;
- LOT-26 CFA FRA external live evidence remains separate and must not be synthesized from CI names;
- the 30 REM findings remain VERIFIED under their exact RC2 qualification evidence.

Any runtime or accounting change after RC2 invalidates the metadata-only stable promotion assumption
and requires a new candidate qualification.

## G5 contract

Stable promotion requires all of the following on the exact stable candidate SHA:

~~~text
G4 green
30 remediation findings VERIFIED
0 applicable P1 OPEN
0 BLOCKER
0 CRITICAL
no critical flaky tests
release notes complete
migration impact reviewed
public API manifest stable
regulatory matrix published
snapshot schema manifest published
Django/PostgreSQL exact-SHA green
SQLAlchemy/PostgreSQL exact-SHA green
stable release qualification green
Security green
Canonical CI green
artifact checksums generated
tag immutable
publication smoke green
~~~

The executable pre-tag gate remains:

~~~text
python scripts/validate_stable_gate.py
~~~

A version bump alone is never sufficient.

## Current external controls

The external-control state must be **re-read from canonical machine-readable records and, where
required, live GitHub administration evidence** before a stable branch is prepared.

Historically, the G5 blockers included:

~~~text
MAIN_BRANCH_PROTECTION_UNENFORCED
IMMUTABLE_RELEASES_UNVERIFIED
~~~

This document does not declare either blocker closed.

The next stable-promotion step is to inspect:

- `docs/audits/LOT_00_REMEDIATION_STATUS.json`;
- `docs/audits/G5_EXTERNAL_CONTROLS.json`;
- live GitHub protection/ruleset state where the connector has sufficient administration access;
- release immutability state through the repository's authenticated administration tooling.

Documentation alone cannot satisfy an external control.

No stable tag, PyPI publication or GitHub Release may be claimed while a required G5 external
control remains open.

## Migration impact

### RC1 → RC2

Not metadata-only.

RC2 includes audit remediation changes, including persistence/runtime fixes such as persistent
subledgers and closing/opening hardening. Those changes were qualified as part of REM-10.

### RC2 → stable 0.7.0

Migration impact target: **none**.

The stable promotion must change release identity and publication metadata only relative to the
qualified `0.7.0rc2` baseline. No additional ORM migration, Alembic migration, runtime API,
regulatory mapping promotion or provider behavior is permitted without creating a new qualified
candidate.

## Stable candidate procedure

Only after the external G5 controls are demonstrably closed:

1. create `release/0.7.0` from the qualified line;
2. change release identity from `0.7.0rc2` to `0.7.0`;
3. regenerate all versioned manifests deterministically;
4. update active release documentation and stable release notes;
5. run the dedicated stable G5 validator;
6. run the full Python 3.11/3.12/3.13 matrix;
7. run Django/PostgreSQL and SQLAlchemy/PostgreSQL against the exact stable candidate SHA;
8. run the stable release qualification job and Canonical CI gate;
9. merge only if Security and all required gates are green;
10. requalify the exact `main` merge SHA before tagging.

## Publication boundary

After the exact stable `main` commit is qualified:

1. create the exact tag `v0.7.0` on that qualified commit;
2. release preflight verifies tag/version/main ancestry;
3. build one wheel/sdist pair;
4. seal SHA-256 checksums and `RELEASE_QUALIFICATION_MANIFEST.json`;
5. publish the exact bundle to PyPI using the configured trusted-publishing path;
6. install `pyaccountingkit==0.7.0` from PyPI in the publication-smoke job;
7. publish the exact GitHub Release assets;
8. verify release immutability;
9. retain the immutable qualification evidence.

## Stop-the-line conditions

Stable promotion stops if any of these occurs:

- G5 external control still OPEN;
- stable validator non-zero;
- any remediation finding regresses from VERIFIED;
- stable candidate differs semantically from RC2;
- required PostgreSQL job skipped;
- PostgreSQL evidence SHA differs from stable candidate SHA;
- migration/model divergence;
- public manifest drift not explained by the stable version transition;
- Security failure;
- Canonical CI failure;
- publication bundle digest mismatch;
- release immutability cannot be verified.

## Exit criterion

`0.7.0` is stable only when:

~~~text
exact stable commit qualified
+ Security green
+ G5 green
+ Canonical CI green
+ immutable tag/release integrity
+ PyPI publication smoke green
~~~

Until all five boundaries are proven, the correct project state is:

~~~text
0.7.0rc2 QUALIFIED
0.7.0 stable NOT YET RELEASED
~~~
