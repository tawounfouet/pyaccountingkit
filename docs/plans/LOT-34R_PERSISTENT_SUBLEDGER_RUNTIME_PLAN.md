# LOT-34R — Persistent Subledger Runtime

> **Remediation alias requested as LOT-34**
>
> The product roadmap already owns a historical LOT-34. This remediation delivery therefore uses
> **LOT-34R**.
>
> **Finding:** A01
> **Remediation lot:** REM-09
> **Target:** 0.7.0rc2 — tranche 5
> **Baseline:** main@792e7285f165fe05e3bad2ff4e6669f70669a272
> **Scope decision:** IN RELEASE SCOPE
> **Status:** IMPLEMENTING / QUALIFYING

## 1. Scope decision

A01 was marked CONDITIONAL. The repository already exposes subledger capabilities through:

- the stable public `AccountingApplication.subledgers` facade;
- historical 0.4 stable delivery claims;
- LOT-18/19 golden, property, concurrency and replay evidence;
- current roadmap and public API manifests.

Removing the capability from 0.7 would require retracting these public/release claims. REM-09 therefore
takes the only coherent remaining path:

~~~text
A01 included in 0.7
    ↓
implement + qualify persistent chain
~~~

## 2. Gap

The domain is implemented, but the runtime chain is not:

~~~text
Subledger domain                       ✅
In-memory domain tests                 ✅
Public facade                          ✅

application/subledgers                 ❌ nearly empty
SubledgerRepositoryProtocol            ❌
InMemory persistent UoW binding        ❌
Django/PostgreSQL repository           ❌
SQLAlchemy/PostgreSQL repository       ❌
atomic GL + subledger application flow ❌
~~~

## 3. Target architecture

~~~text
AccountingApplication.subledgers
        ↓
PersistentSubledgerApplicationService
        ↓
UnitOfWork
  ├── entries / periods / journals
  └── subledgers
        ↓
InMemory | Django/PostgreSQL | SQLAlchemy/PostgreSQL
~~~

Mutating flows:

~~~text
Recognize Receivable / Payable
    validated JournalEntry
        ↓
PostingOrchestrator.post_in_uow
        ↓
POSTED GL entry
        ↓
PostedAccountingReference
        ↓
OPEN accounting-effective subledger item
        ↓
same UoW commit
~~~

~~~text
Record Settlement
    validated settlement JournalEntry
        ↓
canonical posting in same UoW
        ↓
accounting-effective Settlement
        ↓
same UoW commit
~~~

~~~text
Allocate
    lock Settlement + source item
        ↓
SettlementAllocationService
        ↓
save settlement + due item + allocation
        ↓
one commit
~~~

~~~text
Reverse Settlement
    GL reversal in same UoW
        ↓
SettlementReversalService
        ↓
restore active allocations
        ↓
restore due-item open amounts
        ↓
mark settlement REVERSED
        ↓
persist reversal evidence
        ↓
one commit
~~~

## 4. Persistence contract

Add one typed `SubledgerRepositoryProtocol` covering:

- parties;
- receivables;
- payables;
- settlements;
- settlement allocations;
- settlement reversal evidence;
- validated accounting matches.

A generic persistence record may be used internally by adapters, but callers only see typed domain
methods.

Persistent records pin:

~~~text
record kind
record id
entity id
subledger id
record revision
canonical JSON payload
~~~

## 5. Adapter parity

The same repository semantics are required on:

~~~text
InMemory
Django/PostgreSQL
SQLAlchemy/PostgreSQL
~~~

Production reads participating in a mutation use row locking. Domain revisions remain authoritative
for settlement/due-item concurrency; adapter record revisions prevent blind overwrite.

## 6. Application service

The service exposed to `SubledgersAPI` must provide:

~~~text
partners.create/get/list
receivables.recognize/get/list_open
payables.recognize/get/list_open
settlements.record/allocate/reverse
matching.suggest/validate
reconcile
aging
~~~

It reuses existing domain services and the canonical posting/reversal engines.

No second posting engine is permitted.

## 7. Corrective tests

Required:

- recognition posts GL and persists subledger state atomically;
- failed subledger persistence rolls back GL posting;
- allocation persists settlement + due-item revision + allocation atomically;
- competing stale allocation fails;
- settlement reversal restores due items and GL in one transaction;
- Django/PostgreSQL repository round-trip;
- SQLAlchemy/PostgreSQL repository round-trip;
- rollback leaves no partial subledger state;
- adapter semantic parity;
- public facade can consume the persistent application service without ORM leakage.

## 8. Migration

Django and SQLAlchemy share the same logical table:

~~~text
pyak_subledger_record
~~~

No ORM object may cross the repository/application/public boundary.

## 9. Exit criteria

~~~text
[ ] A01 explicitly in 0.7 release scope
[ ] typed SubledgerRepositoryProtocol
[ ] UnitOfWork exposes subledgers repository
[ ] InMemory parity
[ ] Django/PostgreSQL parity
[ ] SQLAlchemy/PostgreSQL parity
[ ] application service operational
[ ] posting + recognition atomic
[ ] settlement posting atomic
[ ] allocation atomic
[ ] settlement reversal + GL atomic
[ ] matching persistence
[ ] aging/reconciliation over persistent state
[ ] migration coherence green
[ ] Python 3.11/3.12/3.13 green
[ ] Django/PostgreSQL green
[ ] SQLAlchemy/PostgreSQL green
[ ] Security green
[ ] Canonical CI gate green
[ ] A01 -> FIXED_UNVERIFIED after merge
[ ] REM-09 implementation -> COMPLETE after merge
~~~

`VERIFIED` remains reserved for exact-main-SHA evidence and REM-10 transverse qualification.
