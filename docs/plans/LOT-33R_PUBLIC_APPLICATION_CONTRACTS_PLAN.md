# LOT-33R — Public Application Contracts

> **Remediation alias requested as LOT-33**
>
> The product roadmap already owns a historical LOT-33. This remediation delivery therefore uses
> **LOT-33R**.
>
> **Findings:** F17, A02
> **Remediation lot:** REM-08
> **Target:** 0.7.0rc2 — tranche 4
> **Baseline:** main@332bb6ea9c3c9dee2469cd6139abdf5a5253b7fc
> **Status:** IMPLEMENTING / QUALIFYING

## 1. Objective

Make the public facade an executable, adapter-neutral boundary rather than a loose method router.

~~~text
Public caller
    ↓
registered operation contract
    ↓
immutable request envelope
    ↓
deep framework-neutrality check
    ↓
application service
    ↓
central error translation
    ↓
deep framework-neutrality check
    ↓
public response
~~~

This closes:

- **F17** — wrapped ORM/framework values can cross the current neutrality guard;
- **A02** — operational contracts are incomplete and error translation is not centralized.

## 2. F17 — deep framework-neutrality

The public boundary must reject Django/SQLAlchemy objects when they appear as:

~~~text
direct result
mapping value/key
sequence member
set member
dataclass field
plain object __dict__ attribute
__slots__ attribute
wrapped framework class
input parameter
~~~

Lazy iterators are rejected because their contents cannot be validated without consuming them
after the public boundary has already been crossed.

The guard remains dependency-neutral: Django and SQLAlchemy are never imported.

## 3. A02 — executable public operation contracts

Every explicit facade operation is registered in one immutable catalog:

~~~text
PUBLIC_OPERATION_CONTRACTS
~~~

Each contract pins:

~~~text
namespace
operation
COMMAND | QUERY
request_type
response_contract
context_policy
boundary_error_codes
~~~

If a facade method invokes an operation that is absent from the catalog, execution fails closed.

The catalog covers:

~~~text
references
charts
entries
ledger
closing
controls
imports
statements
reporting
analysis
subledgers
subledgers.partners
subledgers.receivables
subledgers.payables
subledgers.settlements
subledgers.matching
~~~

## 4. Request boundary

All calls are normalized into an immutable:

~~~text
PublicOperationRequest
├── parameters: read-only Mapping
└── context: CommandContext | None
~~~

The entire request graph is checked for framework leakage before the application service is called.

This prevents an ORM object from entering through a keyword argument even when the service itself
would accept it.

## 5. Response boundary

Every result is recursively checked after application execution.

The scan is cycle-safe and covers ordinary Python wrappers, not only dataclasses and containers.

## 6. Central error translation

One policy applies to every public namespace:

~~~text
canonical AccountingError
    → preserve typed accounting error and stable code

PyAccountingKit public error
    → preserve

Django/SQLAlchemy exception
    → PublicInfrastructureError
       code = PUBLIC_INFRASTRUCTURE_FAILURE
       no raw database/framework message exposed

unknown exception
    → re-raise unchanged
~~~

Unknown programming errors are deliberately not hidden.

## 7. Public manifest

REM-08 adds public exports for:

~~~text
PUBLIC_OPERATION_CONTRACTS
PublicOperationContract
PublicOperationRequest
PublicOperationKind
PublicContextPolicy
public_operation_contract
PublicInfrastructureError
~~~

The public API and error-code manifests must remain deterministic.

## 8. Corrective tests

F17:

- direct ORM value rejected;
- ORM value wrapped through ordinary __dict__ rejected;
- ORM value wrapped through __slots__ rejected;
- framework object in public input rejected before service invocation;
- framework class leakage rejected;
- recursive/cyclic wrappers do not bypass the guard.

A02:

- every public facade method has exactly one registered operation contract;
- request envelope is immutable;
- every contract classifies COMMAND or QUERY;
- missing service/operation remains fail-closed;
- framework exception is translated centrally;
- raw DB/framework detail is not exposed;
- canonical accounting errors preserve their stable code;
- unknown exceptions are not hidden.

## 9. Exit criteria

~~~text
[ ] wrapped ORM leakage rejected
[ ] ORM input rejected before application invocation
[ ] all facade operations registered exactly once
[ ] contract catalog immutable
[ ] request envelope immutable
[ ] infrastructure error translation centralized
[ ] canonical domain errors preserved
[ ] unknown exceptions not hidden
[ ] PUBLIC_API_MANIFEST deterministic
[ ] PUBLIC_ERROR_CODES deterministic
[ ] core-only import remains Django/SQLAlchemy free
[ ] Python 3.11 / 3.12 / 3.13 green
[ ] Django/PostgreSQL green
[ ] SQLAlchemy/PostgreSQL green
[ ] Security green
[ ] Canonical CI gate green
[ ] F17/A02 -> FIXED_UNVERIFIED after merge
[ ] REM-08 implementation_status -> COMPLETE after merge
~~~

VERIFIED remains reserved for exact-main-SHA evidence and REM-10 transverse qualification.
