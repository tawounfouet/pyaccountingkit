# REM-10 / LOT-35R — 0.7.0rc2 Transverse Qualification

> **Remediation delivery alias:** LOT-35R
>
> The product roadmap already owns a historical LOT-35. This remediation qualification slice
> therefore uses **LOT-35R**.
>
> **Remediation lot:** REM-10
> **Candidate:** 0.7.0rc2
> **Baseline:** main@125ee19d92f0c926db108582ee2ae95cd1644299
> **Findings:** F01..F27 + A01..A03
> **Initial status:** QUALIFYING

## 1. Purpose

REM-10 is not a new accounting feature lot.

Its purpose is to prove, on one exact candidate SHA, that every applicable finding corrected during
REM-01..REM-09 remains closed when the full package is exercised together.

The release decision remains fail-closed.

## 2. Candidate invariant

~~~text
test evidence SHA
    =
Django/PostgreSQL qualified SHA
    =
SQLAlchemy/PostgreSQL qualified SHA
    =
release-candidate checkout SHA
    =
candidate SHA
~~~

Evidence from a previous remediation PR is useful history but is not sufficient for REM-10.

## 3. Candidate identity

~~~text
version  0.7.0rc2
branch   release/0.7.0rc2
target   main
~~~

The RC2 metadata transition does not promote new regulatory capabilities.

It packages the remediation overlay already merged through REM-09 and adds the qualification
contract required to prove it transversely.

## 4. Required evidence

REM-10 requires all of:

~~~text
repository hygiene
architecture safety
manifest coherence
public API manifest generation
public error manifest generation
adapter contract manifest generation
regulatory compatibility matrix generation
snapshot schema generation
CI workflow contract
documentation contract
regulatory gate
resource governance
LOT-00 status
REM-10 remediation registry gate
Ruff lint
Ruff format
strict mypy
package build / wheel / sdist verification

unit
property
contract
integration
golden
replay
concurrency

Django/PostgreSQL 16
SQLAlchemy/PostgreSQL 16
fresh migrations
migration/model coherence

exact candidate SHA
canonical CI gate
security workflow
~~~

## 5. Remediation registry gate

The RC2 candidate must fail closed unless the canonical registry proves:

- exactly 30 audit findings are present;
- current remediation phase is REM-10;
- no finding is OPEN, IN_PROGRESS or BLOCKED;
- no release-scope finding remains CONDITIONAL;
- every finding has a 40-hex fix SHA;
- every finding has at least one corrective test;
- every finding has qualification evidence;
- every applicable finding is FIXED_UNVERIFIED or VERIFIED;
- A01 is explicitly IN_SCOPE;
- REM-09 implementation is COMPLETE;
- REM-10 is QUALIFYING or DONE.

This gate does not itself change a finding to VERIFIED.

## 6. PostgreSQL exact-SHA contract

The CI production-adapter jobs must emit their qualified SHA.

The REM-10 RC qualification job must receive:

~~~text
PYAK_RELEASE_DJANGO_POSTGRESQL_SHA
PYAK_RELEASE_SQLALCHEMY_POSTGRESQL_SHA
~~~

and both must equal the exact checkout SHA used by the RC qualification.

A missing or mismatched value is a hard failure.

## 7. CFA FRA boundary

The existing LOT-26 CFA FRA jobs remain intentionally excluded from the 0.7 RC branch.

REM-10 must not reinterpret isolated CI fixtures as new external live evidence.

This RC qualification concerns the PyAccountingKit 0.7 remediation candidate and its declared
regulatory GR/G4 path.

## 8. Versioned evidence contract

0.7.0rc2 must be registered explicitly in scripts/qualify_release.py.

At minimum its evidence contract includes:

- the existing 0.7 regulatory evidence;
- the remediation status registry;
- this REM-10 qualification plan;
- the REM-10 registry validator.

An unregistered RC version must continue to fail closed.

## 9. Promotion states

Before exact candidate qualification:

~~~text
30 FIXED_UNVERIFIED
0 OPEN
0 VERIFIED
~~~

After exact candidate qualification succeeds, the registry may be updated to VERIFIED only with
the exact candidate evidence recorded.

No status may be promoted from PR CI alone if the promoted candidate SHA differs.

## 10. Release decision

REM-10 may produce one of:

~~~text
QUALIFIED_RC2
BLOCKED
~~~

Stable 0.7.0 is not implied by a qualified RC2.

Stable promotion still requires the independent G5 stable gate and all external controls required
by that gate.

## 11. Stop-the-line conditions

Any of the following blocks RC2:

- any corrective suite failure;
- required PostgreSQL test skipped or unavailable;
- PostgreSQL evidence SHA mismatch;
- migration/model divergence;
- public manifest drift;
- cross-adapter semantic divergence;
- replay/golden mismatch;
- security failure;
- remediation registry inconsistency;
- Canonical CI gate failure.

## 12. Exit criteria

~~~text
[ ] 0.7.0rc2 version identity coherent
[ ] root manifests regenerated for 0.7.0rc2
[ ] active documentation coherent
[ ] versioned RC2 evidence contract registered
[ ] REM-10 registry validator implemented and tested
[ ] Django/PostgreSQL emits exact SHA
[ ] SQLAlchemy/PostgreSQL emits exact SHA
[ ] RC qualification consumes both exact SHA outputs
[ ] Security PASS on candidate
[ ] Quality PASS on candidate
[ ] Python 3.11 PASS
[ ] Python 3.12 PASS
[ ] Python 3.13 PASS
[ ] Django/PostgreSQL PASS
[ ] SQLAlchemy/PostgreSQL PASS
[ ] package qualification PASS
[ ] regulatory qualification PASS
[ ] REM-10 release-candidate qualification PASS
[ ] Canonical CI gate PASS
[ ] exact-main-SHA requalification PASS after merge
[ ] only then promote findings to VERIFIED
~~~

0.7.0 stable remains a separate release decision after REM-10.
