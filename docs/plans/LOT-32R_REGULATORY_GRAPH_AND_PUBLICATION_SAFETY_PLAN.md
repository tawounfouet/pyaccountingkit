# LOT-32R — Regulatory Graph & Publication Safety

> **Remediation alias requested as LOT-32**
>
> The product roadmap already owns a historical LOT-32. This remediation delivery therefore uses
> **LOT-32R**.
>
> **Findings:** F19, F22
> **Remediation lot:** REM-07
> **Target:** 0.7.0rc2 — tranche 3
> **Baseline:** main@b4519e5bdffe29941d2b4b74bd2e71fd720378bc
> **Status:** IMPLEMENTING / QUALIFYING

## 1. Objective

Make regulatory graph construction and report publication fail closed.

~~~text
F19
ReferenceHierarchy must be one coherent acyclic standard edition.

F22
A financial report with failed controls must never become PUBLISHED.
~~~

## 2. F19 — reference hierarchy safety

A ReferenceHierarchy is pinned by:

~~~text
standard_id
edition
~~~

Every contained ReferenceNode must carry those exact same coordinates.

Rejected structures:

~~~text
mixed standard
mixed edition
dangling parent
self-cycle
multi-node cycle
duplicate node id
~~~

Validation happens at aggregate construction so traversal methods never receive an invalid graph.

## 3. F22 — explicit report publication lifecycle

ReportSnapshot.from_result(...) creates DRAFT only.

The executable lifecycle is:

~~~text
FinancialStatementResult
        ↓
DRAFT
        ↓ validate(result)
all emitted controls == PASS
        ↓
VALIDATED
        ↓ publish()
PUBLISHED
        ↓ supersede()
SUPERSEDED
~~~

Forbidden transitions include:

~~~text
DRAFT -> PUBLISHED
DRAFT -> SUPERSEDED
VALIDATED -> VALIDATED
VALIDATED -> SUPERSEDED
PUBLISHED -> PUBLISHED
SUPERSEDED -> PUBLISHED
~~~

A result containing FAIL or NOT_APPLICABLE control evidence is not publishable through the
canonical lifecycle.

## 4. Replay and checksum semantics

Status remains part of the ReportSnapshot canonical checksum.

Each valid transition therefore returns a new immutable snapshot with a checksum matching the
new lifecycle state. Snapshot id and volatile creation timestamp remain excluded exactly as
before.

## 5. Compatibility

The reference 0.3 release pipeline is updated to:

~~~text
from_result(...)
    .validate(financial_result)
    .publish()
~~~

Downstream regulatory reporting still requires PUBLISHED and therefore consumes only snapshots
that passed the canonical publication path.

Direct fixture construction of immutable historical snapshots remains possible for replay/golden
tests; production creation through from_result is fail closed.

## 6. Scope note

The architecture document mentions a future WITHDRAWN status. The runtime enum currently exposes
DRAFT, VALIDATED, PUBLISHED and SUPERSEDED only. LOT-32R does not invent WITHDRAWN behavior.

## 7. Corrective tests

F19:

- mixed edition node rejected;
- self-cycle rejected;
- multi-node cycle rejected;
- dangling parent remains rejected;
- valid hierarchy traversal remains unchanged.

F22:

- from_result defaults to DRAFT;
- direct from_result(..., PUBLISHED) rejected;
- failed financial control blocks validation;
- DRAFT cannot publish;
- VALIDATED can publish;
- PUBLISHED can supersede;
- invalid repeat/backward transitions rejected;
- release 0.3 pipeline publishes through validation.

## 8. Exit criteria

~~~text
[ ] mixed-edition hierarchy rejected
[ ] self-cycle rejected
[ ] multi-node cycle rejected
[ ] failed controls cannot validate snapshot
[ ] DRAFT cannot publish directly
[ ] VALIDATED -> PUBLISHED only
[ ] PUBLISHED -> SUPERSEDED only
[ ] public error manifest coherent
[ ] reference/golden regulatory suites green
[ ] Python 3.11 / 3.12 / 3.13 green
[ ] Django/PostgreSQL green
[ ] SQLAlchemy/PostgreSQL green
[ ] Security green
[ ] Canonical CI gate green
[ ] F19/F22 -> FIXED_UNVERIFIED after merge
[ ] REM-07 implementation_status -> COMPLETE after merge
~~~

VERIFIED remains reserved for exact-main-SHA evidence and REM-10 transverse qualification.
