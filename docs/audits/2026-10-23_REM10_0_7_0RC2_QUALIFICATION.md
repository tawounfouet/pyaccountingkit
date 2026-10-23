# REM-10 — PyAccountingKit 0.7.0rc2 Transverse Qualification

> **Date:** 2026-10-23  
> **Candidate:** PyAccountingKit 0.7.0rc2  
> **Qualified main SHA:** `0364b966fb57df97f4e8a2166b52ec99eaae0f20`  
> **Remediation scope:** F01..F27 + A01..A03  
> **Decision:** QUALIFIED_RC2

---

## 1. Purpose

REM-10 closes the audit-remediation overlay by requalifying all applicable findings together on one
exact candidate SHA.

The qualification doctrine remains:

~~~text
corrective test
    ↓
implementation fix
    ↓
PR qualification
    ↓
merge
    ↓
exact-main-SHA transverse qualification
    ↓
VERIFIED
~~~

Historical PR evidence was not reused as sufficient proof for the final status transition.

---

## 2. Candidate identity

~~~text
version        0.7.0rc2
main SHA       0364b966fb57df97f4e8a2166b52ec99eaae0f20
PR             #94
release branch release/0.7.0rc2
PR head        c44fdaa579674a36430aadec2245380550b8c0ed
~~~

The merge commit is the candidate that controls the final remediation decision.

---

## 3. PR qualification evidence

The release-branch candidate passed:

~~~text
CI run          39885967699
Security run    39885967686

Quality                                 PASS
Python 3.11                             PASS
Python 3.12                             PASS
Python 3.13                             PASS
Django/PostgreSQL 16                    PASS
SQLAlchemy/PostgreSQL 16                PASS
Package qualification                   PASS
Regulatory capability qualification     PASS
REM-10 release-candidate qualification  PASS
Canonical CI gate                       PASS
Security                                PASS
~~~

The 0.7 RC branch intentionally skipped the LOT-26 CFA FRA jobs.

Those skipped jobs are not treated as remediation evidence.

---

## 4. Exact-main-SHA evidence

After merge, the exact candidate SHA was requalified independently.

~~~text
candidate SHA    0364b966fb57df97f4e8a2166b52ec99eaae0f20
CI run           39886182878
Security run     39886182869
~~~

Required gates on the exact candidate:

~~~text
Repository hygiene                       PASS
Architecture safety                      PASS
Manifest coherence                       PASS
Public API manifest generation           PASS
Public error manifest generation         PASS
Adapter contract manifest generation     PASS
Regulatory compatibility matrix          PASS
Snapshot schema manifest                 PASS
CI workflow contract                     PASS
Documentation contract                   PASS
Regulatory gate                          PASS
Resource governance                      PASS
LOT-00 remediation status                PASS
REM-10 remediation release gate          PASS
Ruff lint                                PASS
Ruff format                              PASS
Strict mypy                              PASS
Package qualification                    PASS

Unit / property / contract                PASS
Integration                              PASS
Golden                                   PASS
Replay                                   PASS
Concurrency                              PASS

Python 3.11                              PASS
Python 3.12                              PASS
Python 3.13                              PASS
Django/PostgreSQL 16                     PASS
SQLAlchemy/PostgreSQL 16                 PASS
Regulatory capability qualification      PASS
REM-10 0.7 release-candidate             PASS
Canonical CI gate                        PASS
Security                                 PASS
~~~

The Django and SQLAlchemy production adapter jobs emitted exact qualified SHAs and the REM-10
release-candidate qualifier required both values to equal the checkout SHA.

---

## 5. Remediation registry decision

State before REM-10 exact-SHA proof:

~~~text
30 FIXED_UNVERIFIED
0 OPEN
0 VERIFIED
~~~

State justified by this qualification:

~~~text
0 FIXED_UNVERIFIED
0 OPEN
30 VERIFIED
~~~

Every finding has:

- a remediation lot;
- a fix SHA;
- one or more corrective tests;
- qualification evidence;
- release scope explicitly resolved;
- REM-10 as the qualification lot.

A01 is explicitly IN_SCOPE and its persistent runtime chain is part of the qualified candidate.

---

## 6. Cross-adapter conclusion

No blocking semantic divergence was reported by the required qualification suites across:

~~~text
InMemory
Django/PostgreSQL
SQLAlchemy/PostgreSQL
~~~

The required persistence/concurrency suites executed against PostgreSQL 16 and were not accepted as
optional skips.

---

## 7. CFA FRA boundary

Some normal-main CI jobs carry CFA FRA names and completed successfully in the canonical workflow.

REM-10 does **not** reinterpret those jobs as new external live CFA FRA proof.

The explicit 0.7 RC branch correctly skipped the LOT-26 CFA FRA path, and the remediation decision
relies on the declared 0.7 GR/G4 and PyAccountingKit qualification contract.

No new external consumer repository, cutover, or live regulatory evidence is asserted by this audit.

---

## 8. Release decision

REM-10 decision:

~~~text
QUALIFIED_RC2
~~~

This means:

- the complete audit remediation overlay is implemented;
- all 30 findings are eligible for VERIFIED status;
- PyAccountingKit 0.7.0rc2 is the qualified remediation candidate.

It does **not** mean:

~~~text
0.7.0 stable released
PyPI publication completed
Git tag created
G5 external controls automatically closed
~~~

Stable promotion remains a separate decision and must pass the dedicated G5 stable gate.

---

## 9. Final remediation chain

~~~text
REM-00  DONE
REM-01  VERIFIED
REM-02  VERIFIED
REM-03  VERIFIED
REM-04  VERIFIED
REM-06  VERIFIED
REM-05  VERIFIED
REM-07  VERIFIED
REM-08  VERIFIED
REM-09  VERIFIED
REM-10  DONE
~~~

The audit overlay can therefore be considered closed at the RC2 qualification boundary.

---

## 10. Next release action

The next legitimate action is not another remediation lot.

It is:

~~~text
0.7.0rc2 qualified
        ↓
evaluate G5 stable controls
        ↓
prepare release/0.7.0
        ↓
stable exact-SHA qualification
        ↓
only if green: tag / publish 0.7.0
~~~
