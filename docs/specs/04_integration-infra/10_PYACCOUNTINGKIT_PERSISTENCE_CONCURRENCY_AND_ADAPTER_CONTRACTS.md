# 10 - PyAccountingKit - Persistence, concurrence et contrats d'adapters

> **Projet** : PyAccountingKit  
> **Document** : `10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md`  
> **Documents parents** :
> - `00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`
> - `01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`
> - `02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`
> - `03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md`
> - `04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md`
> - `05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md`
> - `06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md`
> - `07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md`
> - `08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md`
> - `09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md`
> **Statut** : P0.11 - Architecture de persistence, concurrence et contrats d'adapters  
> **Langue** : Français  
> **Objet** : Définir les repositories, le `UnitOfWork`, les frontières transactionnelles, les garanties d'atomicité, l'optimistic locking, le pessimistic locking, l'idempotence, les contraintes d'unicité, l'outbox transactionnelle, les read models et les contrats communs permettant d'implémenter PyAccountingKit avec Django ORM, SQLAlchemy ou des adapters InMemory sans contaminer le domaine.

---

# 1. Résumé exécutif

PyAccountingKit adopte une architecture hexagonale stricte :

```text
adapters
    ↓
application
    ↓
domain
```

Le domaine comptable ne connaît pas :

```text
Django ORM

SQLAlchemy

PostgreSQL

SQLite

MySQL

Redis

transaction.atomic

select_for_update

Session

with_for_update
```

Il exprime uniquement les garanties dont il a besoin :

```text
repository semantics

transaction boundaries

atomic commit

optimistic concurrency

pessimistic lock capability

idempotency

append-only persistence

unique constraints

consistent reads

outbox capability

query projections
```

L'infrastructure traduit ensuite ces contrats vers la technologie choisie.

Architecture cible :

```text
DOMAIN
    |
    +--> Repository Ports
    +--> UnitOfWork Port
    +--> Lock / Revision semantics
    +--> Idempotency semantics
    |
    v
APPLICATION
    |
    +--> Transaction orchestration
    |
    v
ADAPTERS
    |
    +--> Django ORM
    +--> SQLAlchemy
    +--> InMemory
    +--> future adapters
```

Le principe central est :

```text
Business transaction
    !=
database API

Concurrency requirement
    !=
specific locking syntax

Repository contract
    !=
ORM model

Aggregate
    !=
database row
```

---

# 2. Référence fonctionnelle CFA FRA

La référence CFA FRA utilise déjà plusieurs garanties de persistence importantes.

Pour les imports transactionnels, elle utilise :

```text
transaction.atomic

select_for_update
```

et prévoit :

```text
ROLLBACK complet
```

si une étape échoue.

Cette approche est cohérente avec les exigences de PyAccountingKit :

```text
no partial accounting mutation

no duplicate transition

critical state locked or revision-checked

audit and business mutation coordinated
```

PyAccountingKit conserve ces garanties mais les extrait de Django.

---

# 3. Objectifs

Le présent document doit permettre de :

1. définir des repository ports stables ;
2. définir un `UnitOfWork` générique ;
3. séparer aggregate persistence et query/read models ;
4. définir les frontières transactionnelles ;
5. garantir les mutations critiques atomiques ;
6. gérer optimistic locking ;
7. supporter pessimistic locking lorsque nécessaire ;
8. gérer idempotence ;
9. éviter les doubles postings et doubles reversals ;
10. éviter les doubles clôtures ;
11. protéger les séquences de numérotation ;
12. protéger la génération de comptes ;
13. garantir l'append-only de l'audit ;
14. définir les contrats d'outbox ;
15. définir les contrats Django ;
16. définir les contrats SQLAlchemy ;
17. définir un adapter InMemory de référence ;
18. fournir une contract test suite commune ;
19. documenter les capabilities et différences acceptables ;
20. préserver l'indépendance du domaine.

---

# 4. Non-objectifs

Ce document ne définit pas :

```text
le modèle SQL final complet

les migrations exactes Django

les migrations Alembic exactes

la topologie de production

le tuning PostgreSQL détaillé

le sharding

la réplication multi-région

le distributed transaction coordinator

un Event Store obligatoire
```

Ces sujets peuvent être traités dans des documents d'implémentation ultérieurs.

---

# 5. Principes d'architecture

## P-PERS-001 - Le domaine ne dépend d'aucun ORM

Interdit :

```python
from django.db import models
```

dans :

```text
domain/
application/
```

---

## P-PERS-002 - Les repositories sont des ports

```text
domain/application
    depend on
repository protocols
```

Les implementations sont dans :

```text
adapters/
```

---

## P-PERS-003 - Un aggregate est persisté comme une unité logique

Exemples :

```text
JournalEntry
CompanyAccount
AccountingPeriod
ClosingRun
ControlRun
```

---

## P-PERS-004 - Une transaction métier explicite est orchestrée par l'application

```text
Application Service
    |
    v
UnitOfWork
```

---

## P-PERS-005 - Le UnitOfWork est la frontière de commit

Les repositories ne doivent pas appeler :

```text
commit()
```

individuellement.

---

## P-PERS-006 - Les read models peuvent être optimisés séparément

```text
query ports
```

peuvent utiliser :

```text
joins

window functions

materialized views

CTEs

denormalized projections
```

sans exposer cette complexité au domaine.

---

# 6. Write-side vs Read-side

PyAccountingKit suit un CQRS-lite.

```text
WRITE SIDE
    aggregates
    repositories
    UnitOfWork

READ SIDE
    query ports
    projections
    optimized SQL
```

---

# 7. Pourquoi ne pas faire tous les reads via les repositories

Un repository :

```text
reconstruit un aggregate
```

Une query :

```text
répond à une question
```

Exemple :

```text
JournalEntryRepository.get(entry_id)
```

vs :

```text
GeneralLedgerQuery.query(...)
```

Le second ne doit pas hydrater 100 000 aggregates.

---

# 8. Repository contract

Un repository doit exposer le minimum nécessaire.

Exemple :

```python
class JournalEntryRepository(Protocol):
    def get(
        self,
        entry_id: JournalEntryId,
    ) -> JournalEntry:
        ...

    def add(
        self,
        entry: JournalEntry,
    ) -> None:
        ...

    def save(
        self,
        entry: JournalEntry,
        *,
        expected_revision: int | None = None,
    ) -> None:
        ...
```

---

# 9. `get()` vs `find()`

Convention recommandée :

```text
get()
    -> object or NotFoundError

find()
    -> object | None
```

---

# 10. Pas de `get_or_create()` générique dans le domaine

`get_or_create()` mélange souvent :

```text
query

business decision

persistence mutation
```

Préférer un Application Service explicite.

---

# 11. Repository et business queries

Interdit :

```python
repository.find_all_balanced_entries_for_month_end()
```

si cela encode une logique métier de reporting.

Utiliser un query/service approprié.

---

# 12. `UnitOfWork`

Port central :

```python
class UnitOfWork(Protocol):

    entries: JournalEntryRepository
    accounts: CompanyAccountRepository
    periods: AccountingPeriodRepository
    journals: JournalRepository
    audit: AuditRepository
    outbox: OutboxRepository

    def __enter__(self) -> "UnitOfWork":
        ...

    def __exit__(self, exc_type, exc, tb) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
```

---

# 13. Pourquoi le UoW expose des repositories

Cela permet :

```text
one transaction

multiple aggregates / records

one commit
```

---

# 14. Scope du UnitOfWork

Un UnitOfWork correspond généralement à :

```text
une command applicative
```

Exemples :

```text
PostEntry

ReverseEntry

CloseAccountingPeriod

ReopenAccountingPeriod

CreateCompanyAccount

ImportAccountingBatch
```

---

# 15. UnitOfWork court

Un UoW transactionnel doit rester :

```text
short-lived
```

Ne pas conserver une transaction DB ouverte pendant :

```text
appel HTTP externe long

validation humaine

workflow de plusieurs minutes

Celery wait

file upload
```

---

# 16. Long-running workflows

Un workflow long utilise :

```text
durable process state

multiple short transactions
```

Exemple :

```text
ClosingRun
```

---

# 17. Atomicité

Définition :

```text
all required state changes succeed

or

none of them becomes visible
```

---

# 18. Posting atomic boundary

```text
load JournalEntry

lock / revision check

revalidate critical invariants

assign posting sequence / number if required

transition VALIDATED -> POSTED

persist

append audit

append outbox event

commit
```

---

# 19. Failure posting

Interdit :

```text
entry POSTED
but audit missing
```

si l'audit est classé critique.

---

# 20. Reversal atomic boundary

```text
lock original

assert POSTED

assert not already reversed

create reversal entry

validate reversal

post reversal

mark original REVERSED

append audit

append outbox

commit
```

---

# 21. Failure reversal

Interdit :

```text
reversal entry posted
but original still POSTED with no reversal relation
```

ou :

```text
original marked REVERSED
but reversal missing
```

---

# 22. Close final atomic boundary

Le workflow de close peut être long.

La transition finale doit rester courte :

```text
lock period

check expected close revision

re-evaluate critical gate state

transition CLOSING -> CLOSED

append audit/outbox

commit
```

---

# 23. Import atomic boundary

Un import peut choisir :

```text
ALL_OR_NOTHING
```

ou :

```text
PER_ENTRY
```

selon l'adapter et le contrat.

Pour un import comptable présenté comme un batch indivisible :

```text
ALL_OR_NOTHING
```

est recommandé.

---

# 24. `TransactionMode`

```text
ALL_OR_NOTHING

PER_ITEM

CHUNKED_ATOMIC
```

---

# 25. Chunking

Pour gros volumes :

```text
CHUNKED_ATOMIC
```

peut être nécessaire.

Le contrat doit alors exposer que :

```text
the whole import is not one DB transaction
```

et utiliser un state machine d'import pour garantir la reprise.

---

# 26. Isolation

Le domaine ne doit pas imposer une isolation SQL précise.

Il exprime :

```text
consistency requirements
```

---

# 27. `ConsistencyRequirement`

Proposition :

```text
READ_COMMITTED_OK

REPEATABLE_READ_REQUIRED

SERIALIZABLE_REQUIRED

LOCKED_AGGREGATE_REQUIRED

OPTIMISTIC_VERSION_REQUIRED
```

---

# 28. P0 recommendation

Pour la plupart des commands :

```text
READ COMMITTED
+
explicit row locks / revision checks
```

est une cible raisonnable.

La configuration réelle appartient aux adapters.

---

# 29. Optimistic locking

Chaque aggregate mutable critique peut porter :

```text
revision
```

---

# 30. `Revision`

```text
Revision
|
+-- value: int
```

---

# 31. Update contract

```text
save(
    aggregate,
    expected_revision=n
)
```

doit vérifier :

```text
stored_revision == n
```

---

# 32. Succès optimistic

```text
UPDATE ...
SET revision = revision + 1
WHERE id = ?
AND revision = ?
```

Rows affected :

```text
1
```

---

# 33. Conflit optimistic

Rows affected :

```text
0
```

=

```text
ConcurrencyConflictError
```

---

# 34. Quels aggregates doivent avoir revision

P0 recommandé :

```text
JournalEntry

CompanyAccount

CompanyChartOfAccounts

AccountingPeriod

ClosingRun

ControlRun

AccountingPolicySet
```

selon leurs mutations.

---

# 35. Immutables

Pas besoin d'optimistic update normal pour :

```text
AuditEvent

PolicyExecutionTrace finalisée

AccountingReferenceSnapshot

ReportSnapshot

finalized ControlResult
```

car ils sont append-only / immutable.

---

# 36. Pessimistic locking

Requis lorsque :

```text
deux transactions concurrentes pourraient toutes deux valider
une précondition avant mutation
```

---

# 37. Cas posting

Deux workers :

```text
A loads VALIDATED

B loads VALIDATED
```

Sans protection :

```text
A posts
B posts
```

---

# 38. Solutions acceptables

```text
optimistic revision

or

pessimistic row lock

or

atomic conditional update
```

Le contrat exige le résultat, pas la technique.

---

# 39. `LockMode`

Concept d'adapter :

```text
NONE

OPTIMISTIC

FOR_UPDATE

FOR_UPDATE_NOWAIT

FOR_UPDATE_SKIP_LOCKED
```

Ces noms ne doivent pas fuiter dans le domain public API.

---

# 40. `AggregateLockPort`

Optionnel :

```python
class AggregateLockPort(Protocol):
    def lock(
        self,
        ref: AggregateRef,
    ) -> None:
        ...
```

Recommandation :

```text
ne pas l'utiliser directement dans le domaine
```

mais dans les repositories/UoW adapters.

---

# 41. Locking contract du repository

Un repository peut exposer :

```python
def get_for_update(
    self,
    entry_id: JournalEntryId,
) -> JournalEntry:
    ...
```

mais cela rend le port plus infrastructure-oriented.

Alternative préférée :

```text
UnitOfWork capabilities
+
application command semantics
```

---

# 42. Recommandation P0

Deux patterns autorisés :

```text
Pattern A:
    optimistic concurrency by revision

Pattern B:
    repository-specific `get_locked()` port
```

Mais chaque aggregate doit choisir un contrat stable.

---

# 43. `LockingRepository`

Si nécessaire :

```python
class LockingJournalEntryRepository(
    JournalEntryRepository,
    Protocol,
):
    def get_locked(
        self,
        entry_id: JournalEntryId,
    ) -> JournalEntry:
        ...
```

---

# 44. Capability

Un adapter déclare :

```text
supports_pessimistic_locking
```

---

# 45. `PersistenceCapabilities`

```text
PersistenceCapabilities
|
+-- transactions
+-- optimistic_locking
+-- pessimistic_locking
+-- savepoints
+-- deferrable_constraints
+-- advisory_locks
+-- transactional_outbox
+-- bulk_insert
+-- bulk_update
+-- window_functions
+-- json_columns
+-- partial_indexes
```

---

# 46. Pourquoi déclarer les capabilities

Un adapter InMemory ne fournit pas nécessairement :

```text
real database locking
```

mais doit simuler les semantics contractuelles utiles aux tests.

---

# 47. Idempotence

Idempotence répond à :

```text
si la même command est reçue deux fois,
est-elle exécutée deux fois ?
```

---

# 48. `IdempotencyKey`

```text
IdempotencyKey
|
+-- value
```

---

# 49. `IdempotencyStore`

Port :

```python
class IdempotencyStore(Protocol):
    def get(
        self,
        scope: IdempotencyScope,
        key: IdempotencyKey,
    ) -> IdempotencyRecord | None:
        ...

    def reserve(
        self,
        record: IdempotencyRecord,
    ) -> None:
        ...

    def complete(
        self,
        scope: IdempotencyScope,
        key: IdempotencyKey,
        result_ref: ObjectRef,
    ) -> None:
        ...
```

---

# 50. `IdempotencyScope`

```text
command_type

entity_id

resource_id?
```

---

# 51. Payload fingerprint

Même key + même payload :

```text
return existing result
```

Même key + payload différent :

```text
IdempotencyConflictError
```

---

# 52. `IdempotencyRecord`

```text
IdempotencyRecord
|
+-- scope
+-- key
+-- payload_hash
+-- status
+-- result_ref?
+-- created_at
+-- completed_at?
```

---

# 53. `IdempotencyStatus`

```text
RESERVED

COMPLETED

FAILED_RETRYABLE

FAILED_FINAL
```

---

# 54. Posting idempotence

Scope :

```text
POST_ENTRY

entity

entry_id
```

---

# 55. Reversal idempotence

Scope :

```text
REVERSE_ENTRY

entity

original_entry_id
```

---

# 56. Import idempotence

Peut inclure :

```text
source checksum

entity

fiscal year

adapter-specific source key
```

---

# 57. Closing idempotence

Scope :

```text
CLOSE_PERIOD

period_id

close_revision / ClosingRunId
```

---

# 58. Opening balance idempotence

Scope :

```text
source close revision

target fiscal year

opening policy version
```

---

# 59. Idempotency store et transaction

Lorsque possible :

```text
reserve/complete
```

est dans la même transaction que la mutation métier.

---

# 60. Race sur idempotency key

Deux requests identiques simultanées :

```text
one reserves

one observes existing reservation / waits / conflicts
```

---

# 61. Unique constraints

La base doit être la dernière ligne de défense.

---

# 62. Principle

```text
application check
+
database unique constraint
```

et non seulement :

```text
if not exists
```

---

# 63. Company account code uniqueness

```text
UNIQUE(chart_id, canonical_code)
```

---

# 64. Full reversal uniqueness

Pour P0 full reversal :

```text
UNIQUE(reversal_of)
```

pour les reversal entries actives.

---

# 65. Policy active scope uniqueness

Il peut être nécessaire de garantir :

```text
one active applicable policy binding
```

dans certains scopes.

La résolution métier reste responsable des overlaps temporels.

---

# 66. Entry numbering uniqueness

Dépend de `EntryNumberingPolicy`.

Exemple :

```text
UNIQUE(entity_id, journal_id, fiscal_year_id, entry_number)
```

---

# 67. Snapshot immutability

Un snapshot finalisé ne doit pas être updateable par le repository public.

---

# 68. Append-only repositories

Types :

```text
AuditEvent

PolicyExecutionTrace finalized

ControlResult finalized

historical snapshots
```

---

# 69. `AppendOnlyRepository`

```python
class AppendOnlyRepository(Protocol):
    def append(self, item) -> None:
        ...

    def get(self, item_id):
        ...
```

Pas de :

```text
save existing

update

delete
```

---

# 70. Audit repository

```text
append only
```

doit être protégé aussi par l'adapter.

---

# 71. Soft-delete

A éviter sur les objets comptables postés.

---

# 72. Deactivation

Pour :

```text
accounts

journals

charts
```

utiliser :

```text
active / retired status
```

plutôt qu'un delete.

---

# 73. Hard delete

Peut être autorisé pour :

```text
unpersisted / unused drafts
```

selon policy.

---

# 74. Repository delete method

Ne pas exposer un :

```text
delete()
```

générique sur tous les repositories.

---

# 75. Explicit deletion port

Si nécessaire :

```text
delete_unused_draft(...)
```

dans une application command.

---

# 76. Query consistency

Les queries doivent documenter :

```text
strong

read-your-writes

eventually consistent
```

---

# 77. `QueryConsistency`

```text
STRONG

READ_YOUR_WRITES

EVENTUAL
```

---

# 78. Journal query

Pour un écran immédiatement après posting :

```text
READ_YOUR_WRITES
```

est généralement attendu.

---

# 79. Materialized projection

Peut être :

```text
EVENTUAL
```

si explicitement documenté.

---

# 80. `ProjectionFreshness`

```text
CURRENT

LAGGING

STALE

UNKNOWN
```

---

# 81. Watermark

Une projection asynchrone doit exposer :

```text
last_posting_sequence
```

ou équivalent.

---

# 82. Transactional Outbox

But :

```text
commit business state

+

record event for later publication
```

dans la même transaction.

---

# 83. `OutboxMessage`

```text
OutboxMessage
|
+-- id
+-- event_type
+-- payload
+-- occurred_at
+-- correlation_id
+-- aggregate_ref
+-- status
+-- retry_count
```

---

# 84. Outbox status

```text
PENDING

PUBLISHED

FAILED
```

---

# 85. `OutboxRepository`

```python
class OutboxRepository(Protocol):
    def append(
        self,
        message: OutboxMessage,
    ) -> None:
        ...
```

---

# 86. No network call inside transaction

Eviter :

```text
commit DB
while synchronously calling Kafka / webhook / API
```

---

# 87. Correct pattern

```text
DB transaction:
    state
    audit
    outbox

commit

publisher:
    reads outbox
    publishes
```

---

# 88. Audit et outbox

Deux options :

```text
Audit in same DB transaction

or

Audit event emitted via reliable outbox
```

Pour P0 :

```text
same transactional store
```

est recommandé pour l'audit critique.

---

# 89. Savepoints

Les adapters peuvent supporter :

```text
savepoint
```

mais l'application ne doit pas en dépendre sauf cas explicite.

---

# 90. Nested UnitOfWork

Interdit par défaut :

```text
UoW inside active UoW
```

si la sémantique n'est pas claire.

---

# 91. Recommandation

Une command applicative possède :

```text
one owning UnitOfWork
```

Les services appelés n'ouvrent pas une nouvelle transaction.

---

# 92. Transaction propagation

Enum future :

```text
REQUIRED

REQUIRES_NEW

NONE
```

Non nécessaire P0.

---

# 93. Repository identity map

Un UoW peut maintenir une identity map pour garantir :

```text
same aggregate id
    ->
same in-memory object instance
```

dans une transaction.

---

# 94. Obligatoire ?

Non.

Mais le comportement ne doit pas produire deux versions contradictoires du même aggregate dans le même UoW.

---

# 95. ORM identity map

SQLAlchemy fournit naturellement une Session identity map.

Django ORM non.

L'adapter Django doit donc s'appuyer sur :

```text
transaction discipline

explicit load semantics
```

---

# 96. Aggregate hydration

Le repository reconstruit :

```text
domain aggregate
```

depuis :

```text
ORM model(s)
```

---

# 97. ORM model != domain model

Le domaine peut utiliser :

```text
frozen value objects

enums

methods

invariants
```

sans que le modèle ORM ait exactement la même forme.

---

# 98. Data Mapper

Pattern recommandé :

```text
ORM Model
    |
    v
Domain Mapper
    |
    v
Aggregate
```

---

# 99. Active Record

Django est Active Record-like.

PyAccountingKit doit l'encapsuler derrière :

```text
repository adapter
```

pour éviter :

```text
entry_model.post()
```

comme coeur métier.

---

# 100. SQLAlchemy

SQLAlchemy peut aussi mapper directement des domain objects.

Mais P0 recommande :

```text
mapping explicite
```

pour préserver les frontières.

---

# 101. Django adapter - structure

```text
src/pyaccountingkit/adapters/django/
|
+-- models/
|   +-- journal.py
|   +-- entry.py
|   +-- account.py
|   +-- period.py
|   +-- audit.py
|   +-- outbox.py
|
+-- repositories/
|   +-- journal.py
|   +-- entry.py
|   +-- account.py
|   +-- period.py
|   +-- control.py
|
+-- queries/
|   +-- journal.py
|   +-- ledger.py
|   +-- trial_balance.py
|
+-- uow.py
+-- mappers/
+-- idempotency.py
+-- capabilities.py
```

---

# 102. Django UnitOfWork

Concept :

```python
class DjangoUnitOfWork:
    def __enter__(self):
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        return self

    def commit(self):
        self._committed = True

    def __exit__(self, exc_type, exc, tb):
        ...
```

Le code concret doit être écrit avec soin pour respecter les semantics Django.

---

# 103. Django transaction ownership

L'adapter doit éviter :

```text
implicit autocommit assumptions
```

pendant une command critique.

---

# 104. `transaction.atomic`

Responsabilité adapter :

```text
open transaction

rollback on error

commit on success
```

---

# 105. `select_for_update`

Utilisable pour :

```text
posting

reversal

period close

idempotency reservation

sequences
```

---

# 106. Django lock query

Exemple adapter :

```python
EntryModel.objects.select_for_update().get(pk=entry_id)
```

Ce détail ne sort jamais de l'adapter.

---

# 107. Django optimistic revision

Update conditionnel :

```python
updated = (
    EntryModel.objects
    .filter(
        pk=entry.id,
        revision=expected_revision,
    )
    .update(
        ...,
        revision=expected_revision + 1,
    )
)
```

Si :

```text
updated == 0
```

alors :

```text
ConcurrencyConflictError
```

---

# 108. Django mapping

```text
EntryModel
    +
LineModel
    ->
JournalEntry
```

---

# 109. Prefetch

Hydration :

```text
select_related

prefetch_related
```

pour éviter :

```text
N+1 queries
```

---

# 110. Django query adapter - Ledger

Peut utiliser :

```text
QuerySet

annotate

Sum

Window

RowNumber

Subquery

CTE extension if chosen
```

mais retourne :

```text
domain/application DTOs
```

pas des QuerySets publics.

---

# 111. Django bulk operations

Autorisé pour :

```text
imports

projection rebuilds

findings
```

Attention :

```text
bulk_create
```

ne doit pas contourner les invariants métier.

---

# 112. Django model signals

A éviter comme mécanisme principal de logique comptable.

---

# 113. Pourquoi

Les signals :

```text
cachent la transaction

rendent l'ordre difficile à raisonner

compliquent les tests

peuvent produire des effets inattendus
```

---

# 114. Usage acceptable des signals

Éventuellement pour :

```text
technical cache invalidation
```

mais pas pour :

```text
posting

audit critique

reversal
```

---

# 115. Django `save()` overrides

Même recommandation.

Pas de coeur comptable dans :

```python
Model.save()
```

---

# 116. Django constraints

Utiliser :

```text
UniqueConstraint

CheckConstraint
```

lorsque la règle est strictement persistence-safe.

---

# 117. Check constraints possibles

```text
debit >= 0

credit >= 0

NOT(debit > 0 AND credit > 0)
```

en défense supplémentaire.

---

# 118. Mais DB constraint != seule validation métier

L'application doit produire des erreurs métier compréhensibles avant que possible.

---

# 119. SQLAlchemy adapter - structure

```text
src/pyaccountingkit/adapters/sqlalchemy/
|
+-- tables/
+-- mappings/
+-- repositories/
+-- queries/
+-- uow.py
+-- idempotency.py
+-- outbox.py
+-- capabilities.py
```

---

# 120. SQLAlchemy UnitOfWork

```python
class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def __enter__(self):
        self.session = self._session_factory()
        self.entries = SqlAlchemyJournalEntryRepository(self.session)
        ...
        return self

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()

    def __exit__(self, exc_type, exc, tb):
        ...
```

---

# 121. SQLAlchemy `Session`

La Session appartient au UoW.

---

# 122. `with_for_update`

Utilisable dans repository adapter :

```python
select(EntryTable)
.where(...)
.with_for_update()
```

---

# 123. SQLAlchemy optimistic locking

Options :

```text
version_id_col

or

explicit conditional UPDATE
```

Le contrat observable doit rester identique à Django.

---

# 124. SQLAlchemy mapping strategies

Deux options :

```text
imperative mapping to domain entities

or

persistence models + explicit mapper
```

---

# 125. P0 recommendation

Utiliser :

```text
persistence models / tables
+
explicit domain mapper
```

pour cohérence avec Django adapter.

---

# 126. SQLAlchemy flush

`flush()` :

```text
is not commit
```

L'application ne doit pas considérer une mutation flushée comme définitivement commitée.

---

# 127. Generated IDs

Si l'ID est généré côté domaine :

```text
IdFactory
```

alors :

```text
flush
```

n'est pas requis pour obtenir l'identité métier.

---

# 128. Recommandation IDs

Utiliser des IDs applicatifs :

```text
UUID / ULID / domain-specific
```

plutôt que dépendre des auto-increment DB IDs dans le domaine.

---

# 129. Database sequence

Peut rester utilisée pour :

```text
technical posting_sequence

entry numbering policy
```

si explicitement adapter/policy-driven.

---

# 130. InMemory adapter

But :

```text
unit tests

domain examples

property tests

fast contract tests
```

---

# 131. InMemory repositories

Doivent simuler :

```text
get

add

save

revision check

unique constraints
```

---

# 132. InMemory UnitOfWork

Doit simuler rollback.

---

# 133. Pourquoi simuler rollback

Sans rollback :

```text
unit tests pass
```

mais ne reproduisent pas les semantics de production.

---

# 134. Strategy InMemory

Au début du UoW :

```text
copy state
```

Au rollback :

```text
restore snapshot
```

pour des datasets de test raisonnables.

---

# 135. InMemory concurrency

Ne peut pas reproduire toutes les races DB.

---

# 136. Contract

Il doit toutefois reproduire :

```text
expected revision conflict
```

---

# 137. Tests de vraie concurrence

Doivent être exécutés contre :

```text
real transactional database
```

au minimum pour les adapters SQL.

---

# 138. PostgreSQL comme reference DB

P0 peut prendre PostgreSQL comme base principale de qualification des adapters SQL.

---

# 139. SQLite

SQLite peut être utilisé pour certains tests rapides.

Mais il ne doit pas être utilisé comme preuve de :

```text
select_for_update behavior

production concurrency

PostgreSQL constraints semantics
```

---

# 140. Adapter contract test suite

Principe :

```text
same tests
run against
every adapter
```

---

# 141. `RepositoryContractTests`

Exemples :

```text
get unknown -> NotFound

add then get -> same semantic aggregate

save with expected revision succeeds

save with stale revision fails

unique code collision fails

append-only item cannot update
```

---

# 142. `UnitOfWorkContractTests`

```text
commit persists

exception rolls back

explicit rollback rolls back

repositories share same transaction

audit is rolled back with business mutation
```

---

# 143. `PostingConcurrencyContractTests`

Deux concurrent attempts :

```text
exactly one transition succeeds
```

---

# 144. `ReversalConcurrencyContractTests`

Deux reversals simultanées :

```text
exactly one full reversal is created
```

---

# 145. `ClosingConcurrencyContractTests`

Deux close commands :

```text
one close revision
```

---

# 146. `IdempotencyContractTests`

```text
same key same payload -> same result

same key different payload -> conflict

concurrent same key -> one reservation
```

---

# 147. `OutboxContractTests`

```text
business commit + outbox persist atomically

business rollback -> no outbox

published event can be marked published
```

---

# 148. `AuditContractTests`

```text
append only

same transaction as critical mutation

entity scoped

stable ordering
```

---

# 149. `QueryContractTests`

Read adapters doivent respecter :

```text
same accounting semantics
```

même si SQL différent.

---

# 150. Ledger contract

```text
opening balance

running balance

closing balance

ordering

reversal inclusion
```

doivent être identiques Django/SQLAlchemy/InMemory.

---

# 151. Trial Balance contract

```text
same source lines
same variant policy
=
same totals
```

---

# 152. Contract fixtures

Utiliser :

```text
shared golden fixtures
```

---

# 153. Golden scenario

Exemple commun :

```text
opening entry

normal entry

adjusting entry

reversal

closing entry
```

---

# 154. Mapper contract

ORM -> domain -> ORM doit préserver :

```text
identity

Decimal values

enums

dates

revision

source refs

metadata
```

---

# 155. Decimal persistence

DB recommandé :

```text
NUMERIC / DECIMAL
```

Jamais :

```text
FLOAT / REAL
```

pour les montants comptables.

---

# 156. Decimal scale

Le schema persistence peut avoir :

```text
precision

scale
```

selon policy/configuration.

---

# 157. Multi-currency

Ne pas supposer :

```text
2 decimals for every currency
```

---

# 158. Currency amount schema

Peut stocker :

```text
amount

currency_code
```

et éventuellement :

```text
functional_amount
```

dans les extensions multi-devise.

---

# 159. Date types

```text
business dates
    -> DATE

timestamps
    -> timezone-aware TIMESTAMP
```

---

# 160. Timezone

Audit / created_at / posted_at :

```text
timezone-aware
```

---

# 161. JSON metadata

Les metadata flexibles peuvent utiliser :

```text
JSON / JSONB
```

dans les adapters compatibles.

---

# 162. JSON is not an excuse

Les champs structurants ne doivent pas être enfouis dans :

```text
metadata JSON
```

uniquement pour éviter un schema.

---

# 163. Enumerations

Deux stratégies :

```text
database enum

string field with application validation
```

Le contract métier ne dépend pas du choix.

---

# 164. Schema migrations

L'évolution DB doit préserver :

```text
historical meaning

IDs

revision semantics

audit immutability
```

---

# 165. Zero-downtime future

Non requis P0.

Mais éviter les migrations qui :

```text
rewrite massive tables
```

sans stratégie.

---

# 166. Repository exceptions

Les adapters convertissent leurs exceptions techniques.

---

# 167. Exception translation

Exemples :

```text
IntegrityError
    ->
UniqueConstraintViolation

OperationalError
    ->
PersistenceUnavailableError

StaleDataError
    ->
ConcurrencyConflictError
```

---

# 168. Domaine ne reçoit pas `IntegrityError`

Le public application API doit exposer des erreurs stables.

---

# 169. Error taxonomy

```text
PersistenceError
|
+-- AggregateNotFoundError
+-- PersistenceUnavailableError
+-- PersistenceIntegrityError
+-- UniqueConstraintViolation
+-- ForeignReferenceViolation
+-- AppendOnlyViolation
+-- TransactionError
+-- TransactionRollbackError
+-- ConcurrencyConflictError
+-- LockAcquisitionError
+-- LockTimeoutError
+-- IdempotencyConflictError
+-- IdempotencyReservationError
+-- OutboxPersistenceError
```

---

# 170. Retryable errors

Classification :

```text
RETRYABLE

NON_RETRYABLE
```

---

# 171. Retryable examples

```text
lock timeout

deadlock

transient connection failure
```

---

# 172. Non-retryable examples

```text
duplicate business code

invalid state

idempotency payload conflict
```

---

# 173. Retry policy

Le domaine ne retry pas les DB operations.

L'Application / runtime adapter peut appliquer :

```text
bounded retry
```

---

# 174. Deadlock

Un adapter SQL doit être prêt à :

```text
rollback

retry whole transaction
```

si policy runtime le permet.

---

# 175. Important

Ne jamais retry seulement :

```text
half of a business transaction
```

---

# 176. Lock ordering

Pour réduire les deadlocks :

```text
lock aggregates in deterministic order
```

---

# 177. Exemple multi-account lock

Si une opération doit verrouiller plusieurs comptes :

```text
sort by account_id
```

avant acquisition.

---

# 178. Posting locks

Le posting ne nécessite généralement pas de verrouiller tous les comptes si :

```text
account state is read-only enough
```

mais période/journal/account status races doivent être maîtrisées.

---

# 179. Account deactivation race

Scénario :

```text
A posts to active account

B deactivates account
```

La policy de cohérence doit déterminer le résultat autorisé.

---

# 180. P0 strategy

Le posting charge :

```text
account state
```

dans la même transaction.

La désactivation utilise aussi une transaction/revision.

---

# 181. Period closing race

Scénario :

```text
A posts entry

B closes period
```

---

# 182. Required guarantee

Interdit :

```text
entry committed after period is officially closed
```

sans policy d'exception.

---

# 183. Lock strategy

Recommandation :

```text
posting locks period row
```

ou utilise une condition atomique garantissant :

```text
period remains posting-enabled
```

jusqu'au commit.

---

# 184. Close strategy

Close locks period.

---

# 185. Lock compatibility

Posting et Close doivent donc se sérialiser via :

```text
same period concurrency primitive
```

---

# 186. Critical aggregate lock matrix

| Operation | Entry | Period | Original Reversal | Sequence | Idempotency |
|---|---:|---:|---:|---:|---:|
| Validate | revision | maybe read | - | - | optional |
| Post | lock/revision | **lock/read protected** | - | maybe | recommended |
| Reverse | **lock** | **lock/read protected** | **lock original** | maybe | recommended |
| Close | - | **lock** | - | - | recommended |
| Reopen | - | **lock** | - | - | recommended |
| Generate account code | - | - | - | **lock/unique** | optional |
| Import | batch lock | periods | - | sequences | **required** |

---

# 187. Entry numbering concurrency

Deux postings peuvent demander le prochain numéro.

---

# 188. Mauvais pattern

```text
MAX(entry_number) + 1
```

sans lock.

---

# 189. `EntryNumberSequencePort`

```python
class EntryNumberSequencePort(Protocol):
    def next(
        self,
        scope: EntryNumberScope,
    ) -> EntryNumber:
        ...
```

---

# 190. Implementations

```text
database sequence

locked counter row

advisory lock + counter

external sequence service
```

---

# 191. Gapless numbering

Ne pas promettre :

```text
gapless
```

sauf exigence explicite.

---

# 192. Pourquoi

Transaction rollback peut créer des trous selon le mécanisme.

---

# 193. Gapless policy

Si requise :

```text
EntryNumberingPolicy
```

doit le déclarer.

L'adapter doit fournir une implementation qualifiée.

---

# 194. `SequenceCapabilities`

```text
monotonic

unique

gapless

scoped

transactional
```

---

# 195. Account code generation concurrency

Même principe.

Le code généré doit être protégé par :

```text
unique constraint
```

même si une sequence est utilisée.

---

# 196. Advisory locks

PostgreSQL permet :

```text
advisory locks
```

comme optimization.

Ils ne doivent pas être requis par le domaine.

---

# 197. Deferrable constraints

Peuvent aider certaines migrations.

Non requises P0.

---

# 198. Foreign keys

Les adapters SQL doivent utiliser des FK quand cela reflète une relation locale forte.

---

# 199. External references

Pour :

```text
ReferenceAccountId external

ArtifactRef external
```

une FK DB peut ne pas être possible.

Utiliser :

```text
validated Value Object
+
snapshot
```

---

# 200. Repository batching

Interfaces spécialisées possibles :

```text
get_many()

add_many()
```

pour imports et validation.

---

# 201. `get_many`

Doit :

```text
preserve all requested identities
```

et signaler les IDs manquants clairement.

---

# 202. Avoid generic bulk save

Un :

```text
save_all(anything)
```

affaiblit les contrats.

---

# 203. Bulk import adapter

Peut utiliser :

```text
bulk_create
COPY
executemany
```

si les invariants ont été prévalidés.

---

# 204. COPY PostgreSQL

P1 optimization possible.

Pas dans le contract P0.

---

# 205. Query ports

Exemples :

```text
AccountingJournalQuery

GeneralLedgerQuery

TrialBalanceQuery

AuditQuery

ControlSummaryQuery

TraceQuery
```

---

# 206. Query DTOs

Doivent être :

```text
framework-neutral
```

---

# 207. Pas de QuerySet public

Interdit :

```python
return EntryModel.objects.filter(...)
```

dans API publique.

---

# 208. Pas de SQLAlchemy Result public

Même principe.

---

# 209. Pagination contract

```text
Page[T]
|
+-- items
+-- page
+-- page_size
+-- total?
+-- next_cursor?
```

---

# 210. Offset vs cursor

Adapters peuvent choisir.

Pour ledger à gros volume :

```text
cursor/keyset pagination
```

peut être préférable.

---

# 211. Running balance pagination

Le query adapter doit préserver :

```text
opening balance at page boundary
```

---

# 212. Snapshot transaction for query

Une grosse projection peut nécessiter :

```text
consistent snapshot read
```

pour éviter des totals incohérents pendant des postings concurrents.

---

# 213. Trial Balance generation

Options :

```text
transaction isolation snapshot

source watermark

materialized snapshot
```

---

# 214. Publication-quality reports

Doivent idéalement utiliser :

```text
TrialBalanceSnapshot
```

ou source watermark fixé.

---

# 215. Read replicas

P1.

Si utilisées :

```text
replica lag
```

doit être pris en compte pour les queries exigeant fraîcheur.

---

# 216. Query routing

Pas dans le core.

Adapter/runtime concern.

---

# 217. Cache

Le cache ne devient jamais source canonique.

---

# 218. Cache keys

Doivent inclure :

```text
entity

query parameters

projection version

watermark / revision
```

---

# 219. Cache invalidation

Peut être event-driven.

---

# 220. No cache in write validation

Pour les états critiques :

```text
period open

account active

entry revision
```

utiliser une source transactionnellement fiable.

---

# 221. Audit persistence

Pour les actions critiques :

```text
same transaction
```

est recommandé.

---

# 222. Audit append constraints

SQL adapter peut empêcher :

```text
UPDATE

DELETE
```

via :

```text
permissions

trigger

application-level repository
```

P0 minimum :

```text
repository contract + tests
```

---

# 223. WORM future

P1 hardening.

---

# 224. Artifact Store transactions

Object storage n'est pas transactionnel avec DB.

---

# 225. Upload pattern

Pour un artefact :

```text
upload immutable artifact

compute checksum

persist artifact ref in DB
```

ou :

```text
persist pending artifact state

upload

finalize
```

selon failure model.

---

# 226. Orphan artifact

Il faut pouvoir détecter / nettoyer :

```text
uploaded artifact not referenced
```

---

# 227. Missing artifact

Un contrôle :

```text
EVIDENCE_ARTIFACT_MISSING
```

peut signaler :

```text
DB ref but object absent
```

---

# 228. Two-phase commit

Non requis.

Ne pas introduire un distributed transaction manager pour P0.

---

# 229. Saga / compensating action

Pour les ressources externes :

```text
explicit workflow
```

plutôt que 2PC.

---

# 230. Transaction lifecycle events

Le domaine n'émet pas :

```text
TRANSACTION_COMMITTED
```

comme event métier.

---

# 231. After-commit hooks

L'adapter peut exécuter :

```text
publish outbox

invalidate cache
```

après commit.

---

# 232. Domain event collection

Les aggregates peuvent collecter :

```text
pending domain events
```

---

# 233. UoW extracts events

Avant commit :

```text
collect events

append outbox

commit
```

---

# 234. Clear events

Après persistance/outbox :

```text
mark collected
```

selon implementation.

---

# 235. Duplicate domain events

La logique d'idempotence/outbox doit éviter la double publication métier.

---

# 236. Outbox deduplication key

Possible :

```text
domain_event_id
```

unique.

---

# 237. Event ID

Chaque DomainEvent peut avoir :

```text
event_id
```

généré à la source.

---

# 238. Outbox ordering

Pour un aggregate :

```text
aggregate revision
```

peut servir à préserver l'ordre.

---

# 239. Global ordering

Non garanti P0.

---

# 240. Migrations de persistence

Chaque adapter peut avoir son propre système :

```text
Django migrations

Alembic
```

---

# 241. Domain migrations

Un changement de modèle métier peut nécessiter :

```text
data migration
```

distincte de :

```text
schema migration
```

---

# 242. Migration audit

Les migrations comptables sensibles doivent être :

```text
versioned

scripted

tested

audited
```

---

# 243. Backfill revision

Si on ajoute `revision` à un système existant :

```text
initialize deterministic value
```

et qualifier les anciennes données.

---

# 244. Historical snapshots

Ne jamais recalculer silencieusement un snapshot historique pendant migration.

---

# 245. Data validation after migration

Exécuter :

```text
control suite
```

post migration.

---

# 246. ORM adapter version

Un adapter peut avoir sa propre version :

```text
adapter_schema_version
```

---

# 247. Compatibility matrix

```text
PyAccountingKit version

Django adapter version

SQLAlchemy adapter version

database version
```

sera documentée dans release strategy.

---

# 248. Django support

Le framework ne doit pas obliger Django à être installé pour utiliser le core.

---

# 249. Optional dependency

Exemple :

```text
pyaccountingkit[django]
```

ou module interne conditionnel.

---

# 250. SQLAlchemy support

Même principe :

```text
pyaccountingkit[sqlalchemy]
```

si packaging par extras retenu.

---

# 251. Core install

```text
pip install pyaccountingkit
```

ne devrait pas tirer :

```text
Django

SQLAlchemy
```

si non requis.

---

# 252. Adapter import boundaries

Interdit :

```text
domain imports adapters.django
```

---

# 253. Dependency direction

```text
adapters.django
    ->
application
    ->
domain
```

---

# 254. Application composition root

Une application configure :

```text
UnitOfWork factory

repositories

query adapters

reference provider

clock

audit

runtime version
```

---

# 255. Composition example

```python
accounting = AccountingApplication(
    uow_factory=django_uow_factory,
    journal_query=django_journal_query,
    ledger_query=django_ledger_query,
    reference_provider=reference_provider,
)
```

---

# 256. Adapter selection

Le core n'utilise pas :

```text
if django
elif sqlalchemy
```

---

# 257. Capability validation

Au startup :

```text
required capability
vs
adapter capability
```

peut être vérifiée.

---

# 258. Example

Si une configuration exige :

```text
gapless transactional numbering
```

mais adapter ne le supporte pas :

```text
ConfigurationCapabilityError
```

---

# 259. `AdapterCapabilities`

```text
AdapterCapabilities
|
+-- persistence
+-- queries
+-- sequence
+-- artifacts
```

---

# 260. Capability negotiation

P1.

P0 peut valider quelques flags essentiels.

---

# 261. Minimal adapter requirements P0

```text
transactions

optimistic concurrency

unique constraints semantics

append-only audit semantics

query contracts
```

---

# 262. Pessimistic locking optional?

Pour SQL production :

```text
strongly recommended
```

mais le core doit pouvoir fonctionner avec optimistic locking si correctement implémenté.

---

# 263. Adapter quality levels

Proposition :

```text
REFERENCE

PRODUCTION

TEST_ONLY

EXPERIMENTAL
```

---

# 264. InMemory

```text
TEST_ONLY / REFERENCE
```

---

# 265. Django/PostgreSQL

Peut viser :

```text
PRODUCTION
```

---

# 266. SQLAlchemy/PostgreSQL

Peut viser :

```text
PRODUCTION
```

---

# 267. Adapter certification

Un adapter est déclaré `PRODUCTION` seulement si :

```text
contract suite

concurrency suite

integration suite

rollback suite

migration tests
```

passent.

---

# 268. Database-specific qualification

Un adapter SQLAlchemy peut être :

```text
PRODUCTION on PostgreSQL
EXPERIMENTAL on SQLite
```

---

# 269. `AdapterQualification`

```text
adapter

database

version

test_suite_version

status

qualified_at
```

---

# 270. Transaction test - rollback

Scénario :

```text
create entry

append audit

raise error before commit
```

Expected :

```text
entry absent

audit absent
```

---

# 271. Transaction test - posting

Deux concurrent transactions :

```text
both load same VALIDATED entry
```

Expected :

```text
one POSTED

one conflict
```

---

# 272. Transaction test - period close race

```text
posting starts

closing starts
```

Expected:

```text
serialized outcome
```

Pas :

```text
entry committed into closed period
```

---

# 273. Transaction test - reversal race

Expected :

```text
one reversal only
```

---

# 274. Transaction test - sequence race

Expected :

```text
unique entry numbers
```

---

# 275. Transaction test - account code collision

Expected :

```text
one account created

one collision error
```

---

# 276. Transaction test - idempotency race

Expected :

```text
one side effect
```

---

# 277. Transaction test - audit failure

Expected :

```text
critical mutation rollback
```

---

# 278. Transaction test - outbox failure

Si outbox fait partie du commit critique :

```text
rollback mutation
```

---

# 279. Query test - consistent trial balance

Pendant concurrent posting :

```text
snapshot query
```

doit retourner une vue cohérente selon son contract.

---

# 280. Performance baseline

Repositories doivent éviter :

```text
N+1
```

sur les hot paths.

---

# 281. Posting performance

Un posting avec N lignes doit faire :

```text
batch account state lookup
```

et non :

```text
N account queries
```

---

# 282. Ledger indexes

Index recommandés :

```text
entity_id

accounting_date

account_id

status

entry_type

posting_sequence
```

---

# 283. Composite indexes

Exemples :

```text
(entity_id, accounting_date, status)

(entity_id, account_id, accounting_date)

(entity_id, period_id, status)
```

---

# 284. Audit indexes

```text
(entity_id, occurred_at)

(entity_id, action, occurred_at)

(object_type, object_id)

correlation_id
```

---

# 285. Control indexes

```text
(entity_id, status, completed_at)

control_code

period_id
```

---

# 286. Idempotency indexes

```text
UNIQUE(scope, key)
```

---

# 287. Outbox indexes

```text
(status, occurred_at)
```

---

# 288. Partitioning

P1 for large datasets.

Candidates :

```text
audit

journal lines

outbox

control findings
```

---

# 289. Archiving

P1.

---

# 290. Serialization schema

Repositories peuvent stocker certains Value Objects en colonnes ou JSON.

Le mapping doit être explicite et testé.

---

# 291. Metadata evolution

Les metadata doivent être :

```text
backward compatible
```

ou migrées.

---

# 292. Domain object reconstruction

Si une ancienne row utilise une ancienne enum :

```text
migration
```

doit être définie.

---

# 293. Unknown enum value

Ne pas mapper silencieusement vers :

```text
UNKNOWN
```

si cela masque une incompatibilité critique.

---

# 294. `UnsupportedStoredValueError`

Préférable pour les états critiques.

---

# 295. Read compatibility

Pour metadata non critique, un fallback peut être acceptable.

---

# 296. Repository lifecycle

Repositories n'ont pas de singleton global mutable.

---

# 297. Thread safety

Les UoW / sessions sont :

```text
request/job scoped
```

pas partagés entre threads.

---

# 298. Async support

P1.

Le port initial peut être synchrone.

Une API async pourra nécessiter des protocols séparés.

---

# 299. Ne pas mélanger sync/async

Interdit :

```text
async repository under sync UoW
```

sans composition claire.

---

# 300. Background workers

Chaque task ouvre son propre :

```text
UnitOfWork
```

---

# 301. Worker retries

Doivent respecter :

```text
idempotency
```

---

# 302. Celery

Celery est une integration de runtime.

Le core ne dépend pas de Celery.

---

# 303. API request transaction

Ne pas englober tout le cycle HTTP si unnecessary.

Application command :

```text
opens short UoW
```

---

# 304. Read-only UoW

Option :

```text
ReadOnlyUnitOfWork
```

pas indispensable P0.

---

# 305. Query session

Les read adapters peuvent gérer leur propre connection/session courte.

---

# 306. Connection lifecycle

Responsabilité adapter.

---

# 307. Pooling

Responsabilité runtime.

---

# 308. Repository naming

Privilégier :

```text
JournalEntryRepository
```

et non :

```text
JournalEntryDAO
```

pour cohérence DDD.

---

# 309. Query naming

Privilégier :

```text
TrialBalanceQuery
```

et non :

```text
TrialBalanceRepository
```

---

# 310. Persistence service anti-pattern

Eviter un :

```text
GenericPersistenceService.save(anything)
```

---

# 311. Generic repository anti-pattern

Eviter :

```python
Repository[T]
```

avec :

```text
create/read/update/delete
```

universel.

---

# 312. Pourquoi

Chaque aggregate a :

```text
different semantics

different allowable mutations

different lock requirements
```

---

# 313. Transaction decorator anti-pattern

Un decorator :

```text
@transactional
```

peut être utilisé au niveau application.

Mais il ne doit pas cacher les boundaries au point qu'elles deviennent impossibles à raisonner.

---

# 314. Domain service transaction anti-pattern

Interdit :

```python
class PostingService:
    @transaction.atomic
    ...
```

---

# 315. ORM leakage anti-pattern

Interdit :

```python
def service(entry: EntryModel):
    ...
```

---

# 316. Lazy loading anti-pattern

Le domaine ne doit pas déclencher une query DB en accédant :

```text
entry.lines
```

---

# 317. Hydrated aggregate

Quand un aggregate entre dans le domaine :

```text
required state is loaded
```

---

# 318. Partial aggregate

Si nécessaire, utiliser :

```text
specific read model
```

pas un aggregate incomplet dangereux.

---

# 319. UnitOfWork hidden commit anti-pattern

Repository `save()` ne commit pas.

---

# 320. Autocommit anti-pattern

Une critical command ne doit pas faire :

```text
save object A

autocommit

save object B

autocommit
```

---

# 321. Business exception rollback

Toute exception métier avant commit :

```text
rollback
```

---

# 322. Post-commit exception

Un échec après commit ne peut plus rollback.

Il doit être traité via :

```text
outbox/retry/compensation
```

---

# 323. Before-commit validation

Tout ce qui peut échouer avant mutation externe doit être évalué avant commit lorsque possible.

---

# 324. External side effects

Exemples :

```text
email

webhook

message broker

object storage publication
```

ne doivent pas être mélangés naïvement à la DB transaction.

---

# 325. `AfterCommitAction`

Abstraction future possible.

---

# 326. Audit within same DB

P0 recommandé.

---

# 327. Outbox publisher

Service d'infrastructure :

```text
poll pending

publish

mark published
```

---

# 328. At-least-once delivery

Outbox fournit généralement :

```text
at-least-once
```

---

# 329. Consumer idempotence

Les consommateurs externes doivent être idempotents via :

```text
event_id
```

---

# 330. Exactly-once

Ne pas promettre :

```text
exactly once end-to-end
```

sans architecture spécialisée.

---

# 331. Read model rebuild

Un read model peut être :

```text
dropped

recreated
```

depuis canonical source.

---

# 332. Projection repository

Ne pas mélanger :

```text
write repository
```

avec :

```text
projection store
```

---

# 333. `ProjectionStore`

Port future :

```python
class ProjectionStore(Protocol):
    def replace(...):
        ...
    def checkpoint(...):
        ...
```

---

# 334. P0

Les queries peuvent être calculées directement.

---

# 335. Snapshot persistence

Snapshots publiés :

```text
immutable rows / artifacts
```

---

# 336. Snapshot relation

```text
snapshot_id

source watermark

checksum

created_at
```

---

# 337. Historical query

Doit pouvoir demander :

```text
snapshot X
```

sans recalculer avec une policy actuelle.

---

# 338. Schema-level immutability

Adapter peut utiliser :

```text
immutable table permissions

trigger
```

P1 hardening.

---

# 339. Soft locking UI

Un lock UI :

```text
"Thomas edits entry"
```

n'est pas une garantie transactionnelle.

---

# 340. Business concurrency

Toujours protégée au niveau persistence.

---

# 341. Retry UX

Une ConcurrencyConflict doit permettre à l'application :

```text
reload

show conflict

retry with user intent
```

---

# 342. Automatic retry

Approprié seulement pour commandes :

```text
deterministic

idempotent

no human merge needed
```

---

# 343. Optimistic merge

Non recommandé pour :

```text
JournalEntry POSTED state
```

---

# 344. Draft editing concurrency

Pour `DRAFT`, une application peut proposer :

```text
optimistic revision conflict
```

et merge UI.

---

# 345. Posted entry concurrency

Une fois POSTED :

```text
immutable
```

donc aucun merge.

---

# 346. CompanyAccount editing

Label changes peuvent utiliser optimistic locking.

---

# 347. PolicySet activation race

Deux versions ne doivent pas devenir actives simultanément si scope conflictuel.

---

# 348. Strategy

```text
transaction

lock policy scope

validate overlaps

activate
```

---

# 349. ClosingRun stage race

Deux workers ne doivent pas terminer le même stage deux fois.

---

# 350. Stage revision

```text
ClosingRun.revision
```

ou `stage_version`.

---

# 351. ControlRun finalization race

Même principe.

---

# 352. Distributed worker claim

P1 peut utiliser :

```text
SKIP LOCKED
```

pour worker queue DB.

Pas requis core.

---

# 353. Lease

Alternative :

```text
lease token
```

hors P0.

---

# 354. `select_for_update(skip_locked=True)`

Reste un détail Django/PostgreSQL.

---

# 355. Savepoint tests

Pas obligatoire contract suite P0.

---

# 356. Isolation tests

Production adapter doit au minimum qualifier :

```text
posting vs close race

double reversal

idempotency race
```

---

# 357. Fault injection

Tests utiles :

```text
fail after aggregate save

fail after audit append

fail before outbox append

deadlock simulation
```

---

# 358. Expected results

Aucune partial state.

---

# 359. Migration test

```text
upgrade schema

run accounting control suite

verify snapshots/checksums unchanged where expected
```

---

# 360. Database fixture strategy

Contract tests utilisent :

```text
fresh transaction / schema
```

---

# 361. Rollback-based test isolation

Django :

```text
transactional test case / pytest-django
```

SQLAlchemy :

```text
session rollback / savepoint
```

---

# 362. Integration DB

Au moins un job CI avec :

```text
real PostgreSQL
```

---

# 363. No SQLite-only CI

Un adapter production PostgreSQL ne peut pas être qualifié uniquement sur SQLite.

---

# 364. Containerized qualification

Recommandation :

```text
PostgreSQL container
```

dans CI.

---

# 365. Adapter contract version

La suite de contrats possède :

```text
AdapterContractVersion
```

---

# 366. Breaking contract

Modifier une semantic repository/UoW peut être :

```text
breaking change
```

même si l'API Python ne change pas.

---

# 367. Public API stability

Les protocols de ports importants doivent être traités comme :

```text
semi-public extension API
```

si les utilisateurs écrivent leurs propres adapters.

---

# 368. Adapter author guide

Un futur document devrait fournir :

```text
how to build custom adapter
```

---

# 369. `AdapterContractManifest`

```text
adapter_name

adapter_version

contract_version

capabilities

database_support
```

---

# 370. Django model schema proposal

Non normatif :

```text
AccountingEntityModel

CompanyChartModel

CompanyAccountModel

JournalModel

AccountingPeriodModel

JournalEntryModel

JournalEntryLineModel

AuditEventModel

OutboxMessageModel

IdempotencyRecordModel

ControlRunModel

ControlFindingModel
```

---

# 371. JournalEntry persistence shape

```text
JournalEntryModel
|
+-- id
+-- entity_id
+-- journal_id
+-- period_id
+-- status
+-- revision
+-- entry_number
+-- accounting_date
+-- posted_at
+-- posting_sequence
+-- reversal_of_id?
```

---

# 372. JournalLine shape

```text
JournalEntryLineModel
|
+-- id
+-- entry_id
+-- line_number
+-- account_id
+-- debit
+-- credit
+-- source_line_reference?
+-- metadata
```

---

# 373. Constraints line

```text
debit >= 0

credit >= 0

not both > 0
```

---

# 374. Entry balance DB constraint

Difficile à exprimer comme simple row constraint car :

```text
aggregate sum across lines
```

La validation métier reste nécessaire.

---

# 375. Trigger?

Ne pas exiger un DB trigger pour l'équilibre.

---

# 376. Reason

Le PostingService doit rester portable.

---

# 377. Defensive consistency control

`ENTRY_BALANCED` peut détecter une corruption DB ultérieure.

---

# 378. Reversal FK

```text
reversal_of_id
```

référence l'entry originale.

---

# 379. Unique reversal

P0 :

```text
unique full reversal relation
```

---

# 380. Circular reversal

Interdit :

```text
entry reverses itself
```

et :

```text
A reversal_of B
B reversal_of A
```

---

# 381. DB support

Check/self FK plus validation applicative.

---

# 382. Period schema

```text
status

close_revision
```

---

# 383. Close revision condition

Conditional update :

```text
WHERE close_revision = expected
AND status = CLOSING
```

---

# 384. Idempotency schema

```text
scope

key

payload_hash

status

result_ref

UNIQUE(scope, key)
```

---

# 385. Audit schema

```text
audit_sequence

event_id

entity_id

action

object_type

object_id

occurred_at

actor

correlation_id

payload
```

---

# 386. Outbox schema

```text
event_id UNIQUE

status

occurred_at

published_at

retry_count

payload
```

---

# 387. Data size

Audit/change payloads doivent être limités.

---

# 388. Large evidence

Stocker dans ArtifactStore et conserver :

```text
ArtifactRef
```

---

# 389. Binary files

Ne pas stocker un PDF complet dans :

```text
AuditEvent JSON
```

---

# 390. Encryption at rest

Responsabilité infrastructure.

---

# 391. Column encryption

P1 si données sensibles.

---

# 392. Repository authorization

Repositories ne font pas RBAC métier.

Application Layer valide l'accès.

---

# 393. Entity scoping

Mais les repositories/query adapters doivent exiger :

```text
entity_id
```

lorsque requis pour éviter fuite cross-entity.

---

# 394. Defense in depth

Adapter peut appliquer :

```text
query filters

row-level security
```

---

# 395. PostgreSQL RLS

Optional hardening P1.

---

# 396. Test cross-entity

```text
repository/query cannot return entity B object through entity A scope
```

---

# 397. Global IDs

Même avec UUID global :

```text
entity scope
```

reste contrôlé.

---

# 398. Transaction context metadata

Le UoW peut porter :

```text
correlation_id

actor_context
```

pour audit.

---

# 399. `UnitOfWorkContext`

```text
UnitOfWorkContext
|
+-- actor
+-- correlation_id
+-- request_id?
+-- command_id
```

---

# 400. Audit factory

```text
AuditEventFactory
```

peut utiliser ce contexte.

---

# 401. Clock consistency

Dans une command :

```text
one logical now
```

peut être injecté pour cohérence.

---

# 402. DB clock vs application clock

Le domaine utilise :

```text
Clock
```

Le DB peut enregistrer ses propres technical timestamps, mais ils ne doivent pas remplacer les timestamps métier définis par l'application.

---

# 403. Time ordering

`posting_sequence` complète les timestamps pour l'ordre ledger.

---

# 404. Sequence portability

Chaque adapter doit reproduire :

```text
unique stable ordering
```

même sans PostgreSQL sequence.

---

# 405. Monotonic sequence

P0 exige :

```text
unique and sortable
```

dans un scope d'entité ou global défini.

---

# 406. Global vs entity sequence

A définir par `LedgerProjectionDefinition`.

---

# 407. Rebuild

Posting sequence doit rester stable après reconstruction.

---

# 408. Entry import historical ordering

Une importation peut contenir des dates historiques.

`posting_sequence` reflète :

```text
order of acceptance into current engine
```

pas nécessairement l'ordre économique.

---

# 409. Ledger ordering

Utilise :

```text
accounting_date

posting_sequence

line_number
```

---

# 410. Upsert

A éviter sur les aggregates comptables.

---

# 411. Why

`upsert` masque :

```text
create vs update

revision conflicts

audit semantics
```

---

# 412. Upsert acceptable

Pour :

```text
technical cache

projection checkpoint
```

---

# 413. Snapshot replace

Projection rebuild peut utiliser :

```text
replace snapshot
```

si le snapshot n'est pas publié.

---

# 414. Published snapshot

Immutable.

---

# 415. Soft uniqueness over time

Exemple binding réglementaire :

```text
one active binding for purpose at date
```

peut nécessiter :

```text
exclusion constraint
```

PostgreSQL ou validation transactionnelle.

---

# 416. Portable implementation

Le domaine utilise :

```text
overlap validation
```

et l'adapter peut renforcer par contrainte DB.

---

# 417. Time ranges

DB peut utiliser :

```text
daterange
```

PostgreSQL.

Pas requis portability.

---

# 418. Bulk control findings

Stocker hors aggregate ControlRun si volumineux.

---

# 419. ControlRun summary

Persisté dans row principale.

---

# 420. Streaming write

P1 pour findings massifs.

---

# 421. SQLAlchemy eager loading

Configurer :

```text
selectinload / joinedload
```

selon aggregate.

---

# 422. Django prefetch

Même objectif.

---

# 423. ORM-specific tuning

Ne doit pas modifier les semantics.

---

# 424. Query count tests

Possible :

```text
assert bounded query count
```

sur hot paths.

---

# 425. Transaction duration metrics

Observabilité :

```text
transaction_duration

lock_wait_duration

deadlock_count

concurrency_conflicts

idempotency_hits
```

---

# 426. Repository metrics

```text
repository_get_duration

repository_save_duration
```

optionnel.

---

# 427. Slow transaction alert

Runtime concern.

---

# 428. Lock timeout

Configurer pour éviter des waits infinis.

---

# 429. `LockTimeoutError`

Traduit vers une erreur stable.

---

# 430. NOWAIT

Utilisable pour UX :

```text
resource currently locked
```

---

# 431. SKIP LOCKED

Utilisable worker queues.

Pas pour posting interactif normal si cela ferait ignorer silencieusement l'aggregate.

---

# 432. Deadlock logging

Log :

```text
command

aggregate ids

correlation id
```

sans données sensibles.

---

# 433. Retry count observability

Important pour détecter contention.

---

# 434. High contention

Possible sur :

```text
entry numbering counter

period close

large shared journals
```

---

# 435. Mitigation

```text
scoped counters

UUID business IDs

short transactions

deterministic lock order
```

---

# 436. Sequence scope

Numérotation par journal/exercice réduit contention vs global counter.

---

# 437. No premature sharding

P0 reste monolithic persistence compatible.

---

# 438. Modular monolith

Architecture recommandée :

```text
one database
logical module boundaries
```

---

# 439. Future microservices

Ports permettent extraction ultérieure.

Mais ne pas optimiser P0 pour distributed transactions.

---

# 440. Transaction semantics if split later

Nécessiterait :

```text
sagas

outbox/inbox

eventual consistency
```

hors P0.

---

# 441. `InboxMessage`

P1 pour consumers idempotents.

---

# 442. Repository factories

Composition root crée :

```text
UoWFactory
```

plutôt que repositories globals.

---

# 443. `UnitOfWorkFactory`

```python
class UnitOfWorkFactory(Protocol):
    def __call__(
        self,
        context: UnitOfWorkContext,
    ) -> UnitOfWork:
        ...
```

---

# 444. Test clock

InMemory adapter utilise :

```text
FrozenClock
```

---

# 445. Test IDs

```text
DeterministicIdFactory
```

---

# 446. Deterministic tests

Facilitent :

```text
golden snapshots
```

---

# 447. Repository fake vs mock

Préférer :

```text
InMemory fake
```

pour les tests métier.

Mocks uniquement pour interactions ciblées.

---

# 448. Why

Fakes valident mieux :

```text
repository semantics

rollback

revision
```

---

# 449. Adapter contract reusable package

Structure :

```text
tests/contracts/
|
+-- repositories/
+-- uow/
+-- idempotency/
+-- audit/
+-- outbox/
+-- queries/
+-- concurrency/
```

---

# 450. Adapter test harness

Chaque adapter fournit une fixture :

```text
adapter_harness
```

---

# 451. `AdapterHarness`

```text
uow_factory

db_reset

capabilities

parallel_executor

artifact_store
```

---

# 452. Conditional tests

Si capability :

```text
pessimistic_locking
```

alors exécuter la suite spécifique.

---

# 453. Required capability failures

Adapter `PRODUCTION` doit passer toutes les suites obligatoires.

---

# 454. Django test matrix

Recommandée :

```text
Django current supported versions

PostgreSQL supported versions
```

---

# 455. SQLAlchemy test matrix

```text
SQLAlchemy supported versions

PostgreSQL supported versions
```

---

# 456. InMemory test matrix

Toujours exécutée rapidement.

---

# 457. Packaging adapter

Possible :

```text
pyaccountingkit.adapters.django

pyaccountingkit.adapters.sqlalchemy
```

---

# 458. Adapter packages séparés ?

P0 :

```text
same repository/package
```

avec optional extras.

Séparation future si cycles de release différents.

---

# 459. Public extension contracts

Protocols essentiels :

```text
UnitOfWork

repositories

queries

IdempotencyStore

ArtifactStorePort
```

doivent être documentés comme extension points.

---

# 460. Semantic versioning

Breaking change d'un Protocol public :

```text
major/minor according to release policy
```

---

# 461. Contract stability

Une implementation custom doit pouvoir survivre à des upgrades mineurs raisonnables.

---

# 462. Default adapters

P0 peut livrer :

```text
InMemory

Django adapter
```

SQLAlchemy peut être livré simultanément ou dans une étape rapprochée selon effort.

Mais ce document spécifie les deux.

---

# 463. Why Django first

CFA FRA fournit déjà une référence Django.

---

# 464. Why SQLAlchemy

Permet :

```text
framework-neutral backend

FastAPI / CLI / workers

validation de l'hexagonal architecture
```

---

# 465. Doctrine de compatibilité

Un comportement métier doit passer :

```text
same contract tests
```

sous les deux adapters.

---

# 466. Example - Posting Django

```text
Application PostEntry

    -> DjangoUnitOfWork

        -> transaction.atomic

        -> lock Entry / Period

        -> PostingService

        -> repository.save

        -> audit.append

        -> outbox.append

        -> commit
```

---

# 467. Example - Posting SQLAlchemy

```text
Application PostEntry

    -> SqlAlchemyUnitOfWork

        -> Session transaction

        -> SELECT ... FOR UPDATE

        -> PostingService

        -> repository.save

        -> audit.append

        -> outbox.append

        -> commit
```

---

# 468. Same business result

```text
JournalEntry status = POSTED

revision incremented

audit exists

domain event persisted

no double posting
```

---

# 469. Example - concurrency conflict

Django :

```text
conditional UPDATE returns 0
```

SQLAlchemy :

```text
version mismatch / rowcount 0
```

Public error :

```text
ConcurrencyConflictError
```

---

# 470. Example - DB unique violation

Django :

```text
IntegrityError
```

SQLAlchemy :

```text
IntegrityError
```

Public error :

```text
AccountCodeDuplicateError
```

ou generic :

```text
UniqueConstraintViolation
```

selon layer.

---

# 471. Exception mapping layer

Adapter-specific exception translator :

```text
PersistenceExceptionTranslator
```

---

# 472. `PersistenceExceptionTranslator`

```text
db exception
    ->
stable PyAccountingKit exception
```

---

# 473. No exception string parsing if avoidable

Utiliser :

```text
constraint names

driver error codes
```

quand possible.

---

# 474. Constraint naming

Nommer les contraintes explicitement :

```text
uq_company_account_chart_code

uq_full_reversal_original

ck_journal_line_debit_credit
```

pour translation stable.

---

# 475. Constraint registry

Adapter peut mapper :

```text
constraint name -> domain error
```

---

# 476. Transactions and domain events

Domain events ne sont publiés extérieurement qu'après commit.

---

# 477. In-process subscribers

S'ils modifient le même transaction state :

```text
execute before commit
```

mais cela augmente coupling.

P0 recommande :

```text
Application orchestration
+
outbox for external reactions
```

---

# 478. Audit creation

Audit event construit avant commit et persisté avec aggregate.

---

# 479. `CommitResult`

Optionnel :

```text
committed aggregate refs

outbox ids

audit refs
```

Pas nécessaire public API P0.

---

# 480. Rollback on context manager exit

Si exception :

```text
rollback
```

automatique.

---

# 481. Missing commit

Deux philosophies :

```text
explicit commit required

auto commit on clean exit
```

---

# 482. Recommandation

Utiliser :

```text
explicit commit
```

pour rendre la mutation évidente.

---

# 483. UoW state

```text
ACTIVE

COMMITTED

ROLLED_BACK
```

---

# 484. Double commit

Doit être :

```text
error
```

ou idempotent interne documenté.

P0 recommandé :

```text
error
```

---

# 485. Save after commit

Interdit.

---

# 486. Repository use after UoW close

Interdit.

---

# 487. `UnitOfWorkClosedError`

Possible.

---

# 488. Session leaks

Contract test :

```text
connections/session closed on exit
```

---

# 489. Failure in __exit__

Doit préserver l'erreur originelle autant que possible.

---

# 490. Rollback failure

Log critical + `TransactionRollbackError`.

---

# 491. Integrity after rollback failure

Runtime peut marquer process unhealthy.

---

# 492. Health checks

Persistence adapter peut exposer :

```text
ping
```

hors domain.

---

# 493. `PersistenceHealthPort`

Optional runtime capability.

---

# 494. Ready check

Application peut vérifier :

```text
database reachable

migrations current
```

hors core.

---

# 495. Migration compatibility gate

Release deployment peut bloquer si :

```text
schema incompatible
```

---

# 496. Schema version table

Adapter peut maintenir :

```text
migration version
```

via framework native.

---

# 497. Data validation gate

Après migration, lancer :

```text
critical controls
```

---

# 498. Backup / restore

Infrastructure concern.

---

# 499. Restore qualification

P1 production readiness.

---

# 500. Transaction log / PITR

PostgreSQL operational concern.

---

# 501. Repository portability limit

Le contrat ne doit pas être tellement générique qu'il empêche les optimisations SQL.

---

# 502. Query ports are escape hatch

Les reads complexes vivent dans :

```text
query adapters
```

---

# 503. Write portability stronger than read portability

Le write-side doit être hautement portable.

Le read-side peut exploiter le DB choisi derrière un port stable.

---

# 504. No ORM abstraction framework

PyAccountingKit ne crée pas son propre ORM.

---

# 505. No SQL builder in domain

Même principe.

---

# 506. ADRs

| ID | Décision |
|---|---|
| ADR-PERS-001 | Le domaine ne dépend d'aucun ORM |
| ADR-PERS-002 | Les repositories sont des ports hexagonaux |
| ADR-PERS-003 | Les repositories write-side persistent des aggregates, pas des reporting queries |
| ADR-PERS-004 | Les queries complexes utilisent des query ports dédiés |
| ADR-PERS-005 | `UnitOfWork` constitue la frontière de transaction applicative |
| ADR-PERS-006 | Les repositories ne commitent jamais individuellement |
| ADR-PERS-007 | Les transactions longues sont remplacées par des workflows durables multi-étapes |
| ADR-PERS-008 | Posting et reversal sont atomiques |
| ADR-PERS-009 | Le close final est une transaction courte et atomique |
| ADR-PERS-010 | Optimistic locking utilise une `revision` explicite |
| ADR-PERS-011 | Pessimistic locking est une capability d'adapter |
| ADR-PERS-012 | Posting et Close doivent se sérialiser sur la période |
| ADR-PERS-013 | La base de données reste la dernière ligne de défense pour l'unicité |
| ADR-PERS-014 | L'idempotence utilise key + payload fingerprint |
| ADR-PERS-015 | Same idempotency key + different payload = conflict |
| ADR-PERS-016 | Les événements externes utilisent une Transactional Outbox |
| ADR-PERS-017 | P0 ne requiert pas de distributed transaction manager |
| ADR-PERS-018 | Audit critique et mutation métier doivent être transactionnellement coordonnés |
| ADR-PERS-019 | `AuditEvent` persistence est append-only |
| ADR-PERS-020 | Les montants comptables sont persistés en DECIMAL/NUMERIC, jamais FLOAT |
| ADR-PERS-021 | Les timestamps techniques sont timezone-aware |
| ADR-PERS-022 | ORM models et domain models restent distincts |
| ADR-PERS-023 | Django model signals ne portent pas la logique comptable centrale |
| ADR-PERS-024 | `Model.save()` ne porte pas Posting/Reversal |
| ADR-PERS-025 | Django adapter encapsule `transaction.atomic` et `select_for_update` |
| ADR-PERS-026 | SQLAlchemy adapter encapsule `Session` et `with_for_update` |
| ADR-PERS-027 | InMemory adapter doit simuler rollback et revision conflicts |
| ADR-PERS-028 | Les vraies races sont testées contre une DB transactionnelle réelle |
| ADR-PERS-029 | PostgreSQL est la DB de qualification de référence des adapters SQL P0 |
| ADR-PERS-030 | SQLite seul ne suffit pas pour certifier un adapter production |
| ADR-PERS-031 | Tous les adapters partagent une contract test suite |
| ADR-PERS-032 | Un adapter Production doit passer les suites de concurrence et rollback |
| ADR-PERS-033 | Les exceptions ORM/DB sont traduites vers des erreurs PyAccountingKit stables |
| ADR-PERS-034 | Les locks sont acquis dans un ordre déterministe lorsqu'il y en a plusieurs |
| ADR-PERS-035 | La numérotation n'est pas implémentée par `MAX()+1` non verrouillé |
| ADR-PERS-036 | Gapless numbering n'est pas promis sans policy explicite |
| ADR-PERS-037 | Les read models peuvent être eventually consistent si le contract l'annonce |
| ADR-PERS-038 | Les projections publiées doivent pouvoir être snapshotées / watermarked |
| ADR-PERS-039 | Les adapters sont configurés via un composition root |
| ADR-PERS-040 | Les dépendances Django/SQLAlchemy restent optionnelles au core |

---

# 507. Critères d'acceptation P0.11

```text
[ ] Repository ports sont spécifiés

[ ] Repository != Query est explicite

[ ] UnitOfWork est spécifié

[ ] repositories ne commitent pas individuellement

[ ] transaction boundaries Posting sont définies

[ ] transaction boundaries Reversal sont définies

[ ] transaction boundary final Close est définie

[ ] ALL_OR_NOTHING / PER_ITEM / CHUNKED_ATOMIC sont distingués

[ ] optimistic locking via revision est spécifié

[ ] ConcurrencyConflictError est défini

[ ] pessimistic locking capability est définie

[ ] posting vs close race est explicitement traitée

[ ] double reversal race est explicitement traitée

[ ] idempotency store est spécifié

[ ] payload fingerprint est spécifié

[ ] unique constraints principales sont documentées

[ ] audit append-only persistence est spécifiée

[ ] Transactional Outbox est spécifiée

[ ] external network call inside DB transaction est déconseillé

[ ] Django adapter architecture est spécifiée

[ ] transaction.atomic reste confiné à l'adapter Django

[ ] select_for_update reste confiné à l'adapter Django

[ ] Django optimistic conditional update est spécifié

[ ] Django signals ne portent pas le coeur comptable

[ ] SQLAlchemy adapter architecture est spécifiée

[ ] Session appartient au SQLAlchemy UoW

[ ] with_for_update reste confiné à l'adapter SQLAlchemy

[ ] SQLAlchemy optimistic locking est spécifié

[ ] InMemory adapter est spécifié

[ ] InMemory rollback simulation est requise

[ ] adapter contract test suite est définie

[ ] vraie concurrence PostgreSQL est testée

[ ] Decimal/NUMERIC persistence est exigée

[ ] ORM exceptions sont traduites

[ ] entry number concurrency est spécifiée

[ ] account code collision concurrency est spécifiée

[ ] outbox contract tests sont définis

[ ] query contracts journal/ledger/balance sont définis

[ ] adapter capabilities sont spécifiées

[ ] core n'exige ni Django ni SQLAlchemy
```

---

# 508. Ordre d'implémentation recommandé

## PERS-00 - Primitives

```text
Revision

IdempotencyKey

PersistenceCapabilities

QueryConsistency
```

---

## PERS-01 - Repository Ports

```text
JournalRepository

JournalEntryRepository

CompanyAccountRepository

AccountingPeriodRepository

ClosingRunRepository

AuditRepository
```

---

## PERS-02 - UnitOfWork

```text
UnitOfWork

UnitOfWorkFactory

UnitOfWorkContext
```

---

## PERS-03 - InMemory Adapter

```text
repositories

rollback

revision conflict

unique constraints
```

Il sert de référence comportementale rapide.

---

## PERS-04 - Idempotency

```text
IdempotencyStore

payload hash

reservation

completion
```

---

## PERS-05 - Outbox

```text
OutboxMessage

OutboxRepository

domain event collection
```

---

## PERS-06 - Django Adapter

```text
models

mappers

repositories

DjangoUnitOfWork

query adapters
```

---

## PERS-07 - Django Concurrency

```text
transaction.atomic

select_for_update

conditional revision updates

period close race tests
```

---

## PERS-08 - SQLAlchemy Adapter

```text
tables

mappers

repositories

Session UnitOfWork

query adapters
```

---

## PERS-09 - SQLAlchemy Concurrency

```text
with_for_update

version / conditional update

race tests
```

---

## PERS-10 - Contract Suite

```text
repository contracts

UoW contracts

idempotency

audit

outbox

queries

concurrency
```

---

# 509. Démonstrateur P0.11 - Posting portable

Scénario :

```text
1. Create same domain fixture

2. Run with InMemory adapter

3. Validate / Post entry

4. Assert:
      POSTED
      revision incremented
      audit created
      outbox created

5. Run same scenario with Django/PostgreSQL

6. Run same scenario with SQLAlchemy/PostgreSQL

7. Assert identical business result
```

---

# 510. Démonstrateur - double posting

```text
Entry E = VALIDATED revision 4

Worker A
    loads revision 4

Worker B
    loads revision 4

A posts
    revision 5

B posts
    expected revision 4
    -> ConcurrencyConflictError
```

Résultat :

```text
exactly one posting
```

---

# 511. Démonstrateur - pessimistic locking

Alternative :

```text
A locks E

B attempts lock

A posts and commits

B resumes

B reloads POSTED
    -> EntryAlreadyPostedError
```

---

# 512. Démonstrateur - posting vs close

```text
Period P = CLOSING-capable / OPEN for posting

Worker A:
    PostEntry

Worker B:
    ClosePeriod
```

Les deux utilisent la même protection de période.

Résultats autorisés :

```text
A commits first
then B closes

or

B closes first
then A fails ClosedPeriodError
```

Résultat interdit :

```text
B closes
then A still commits an ordinary entry
```

---

# 513. Démonstrateur - double reversal

```text
Original O = POSTED

A reverse(O)

B reverse(O)
```

Attendu :

```text
one reversal entry

one AlreadyReversed / concurrency failure
```

---

# 514. Démonstrateur - transaction rollback

```text
begin UoW

post entry

append audit

simulate exception before commit

rollback
```

Attendu :

```text
entry not POSTED

audit absent

outbox absent
```

---

# 515. Démonstrateur - idempotence

```text
request #1:
    key = K
    payload = H1
    -> success result R

request #2:
    key = K
    payload = H1
    -> return R

request #3:
    key = K
    payload = H2
    -> IdempotencyConflictError
```

---

# 516. Démonstrateur - account code race

```text
A generate 512001

B generate 512001
```

Unique DB constraint :

```text
one insert succeeds

one AccountCodeDuplicateError
```

---

# 517. Démonstrateur - adapter contracts

```text
run:
    RepositoryContractTests
    UnitOfWorkContractTests
    PostingConcurrencyContractTests
    ReversalConcurrencyContractTests
    IdempotencyContractTests
    AuditContractTests
    OutboxContractTests
    QueryContractTests

against:
    InMemory
    Django/PostgreSQL
    SQLAlchemy/PostgreSQL
```

---

# 518. Matrice des responsabilités

| Capacité | Domain | Application | Adapter |
|---|---:|---:|---:|
| Définir invariant | **oui** | non | non |
| Définir transaction boundary | non | **oui** | implémente |
| Commit/Rollback | non | demande | **oui** |
| Optimistic revision semantics | **oui** | utilise | **oui** |
| SQL row lock | non | non | **oui** |
| Idempotency key | domain primitive | **oui** | store |
| Unique DB constraint | non | non | **oui** |
| Audit event model | **oui** | crée/orchestre | persiste |
| Outbox event | oui/app | orchestre | persiste |
| Ledger SQL window | non | query contract | **oui** |

---

# 519. Matrice Django / SQLAlchemy / InMemory

| Capability | Django/PostgreSQL | SQLAlchemy/PostgreSQL | InMemory |
|---|---:|---:|---:|
| Transaction | `transaction.atomic` | `Session.begin/commit` | simulation |
| Pessimistic lock | `select_for_update` | `with_for_update` | simulation partielle |
| Optimistic revision | conditional update | version/conditional update | oui |
| Rollback | oui | oui | snapshot restore |
| Unique constraints | DB | DB | fake constraint |
| Outbox | table | table | list/store |
| Window query | Django ORM/SQL | SQLAlchemy SQL | Python |
| Production concurrency proof | oui | oui | non |

---

# 520. Frontière avec Testing Strategy

Le prochain document :

```text
11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md
```

devra reprendre :

```text
unit

property-based

contract

integration

concurrency

golden

migration

replay

adapter qualification
```

---

# 521. Frontière avec Imports

Le document Import/FEC détaillera :

```text
source transaction batch

chunking strategy

raw line persistence

idempotency

bulk performance
```

en réutilisant les contrats de ce document.

---

# 522. Frontière avec Public API

Le public API ne doit pas exposer :

```text
transaction.atomic

Session

QuerySet

DB connection
```

---

# 523. Frontière avec Release Strategy

La release strategy devra documenter :

```text
supported Django versions

supported SQLAlchemy versions

supported PostgreSQL versions

adapter contract versions
```

---

# 524. Risques principaux

## RISK-PERS-001 - ORM leakage

Réponse :

```text
repository + mapper
```

---

## RISK-PERS-002 - Transactions cachées

Réponse :

```text
UnitOfWork explicit
```

---

## RISK-PERS-003 - Double posting

Réponse :

```text
revision / row lock / conditional update
```

---

## RISK-PERS-004 - Posting dans période fermée par race

Réponse :

```text
serialize posting and close on period
```

---

## RISK-PERS-005 - Audit partiel

Réponse :

```text
same transaction or reliable outbox
```

---

## RISK-PERS-006 - Idempotence naïve

Réponse :

```text
key + payload fingerprint + unique reservation
```

---

## RISK-PERS-007 - Generic Repository anti-pattern

Réponse :

```text
aggregate-specific ports
```

---

## RISK-PERS-008 - SQLite gives false confidence

Réponse :

```text
PostgreSQL concurrency qualification
```

---

## RISK-PERS-009 - ORM signals execute business logic

Réponse :

```text
Application Services
```

---

## RISK-PERS-010 - Long DB transaction during Closing

Réponse :

```text
ClosingRun stages + short final transaction
```

---

## RISK-PERS-011 - Network call inside transaction

Réponse :

```text
Transactional Outbox
```

---

## RISK-PERS-012 - `MAX()+1` numbering race

Réponse :

```text
EntryNumberSequencePort
```

---

# 525. Conclusion

La persistence de PyAccountingKit doit être considérée comme une **infrastructure interchangeable qui garantit des semantics comptables non interchangeables**.

L'architecture cible est :

```text
DOMAIN
    |
    +--> Aggregates
    +--> Repository Ports
    +--> Revision / Idempotency primitives
    |
    v
APPLICATION
    |
    +--> UnitOfWork
    +--> transaction boundaries
    +--> audit/outbox orchestration
    |
    v
ADAPTERS
    |
    +--> InMemory
    |
    +--> Django ORM
    |      + transaction.atomic
    |      + select_for_update
    |
    +--> SQLAlchemy
           + Session
           + with_for_update
```

Les invariants majeurs sont :

```text
Repository != ORM

Aggregate != row

UnitOfWork owns commit

Repository never commits

Posting is atomic

Reversal is atomic

Close finalization is atomic

Concurrency conflicts are explicit

Database constraints defend uniqueness

Idempotency is payload-aware

Audit critical mutations are transactionally coordinated

Outbox isolates external side effects

Django and SQLAlchemy must produce identical business semantics

Real database concurrency must be tested
```

Le P0.11 ferme ainsi la spécification de l'infrastructure de persistence nécessaire pour commencer une implémentation multi-adapters sans contaminer le coeur comptable.

---

**Prochain document recommandé :**

```text
11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md
```


---

## Sources et références documentaires du projet

- 🏗️ [CFA FRA Django MVP Sprint 7 — Référence fonctionnelle](../../../resources/cfa_fra_django_mvp_sprint_7/)
- 📄 [CFA FRA — Document de conception](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md)

---

## Plans d'implémentation principaux

Ce document est couvert par les plans suivants :

- [PLAN-00 — Repository Bootstrap (0.0.1)](../../plans/PLAN-00_REPOSITORY_BOOTSTRAP_0.0.1.md)
- [PLAN-01 — Accounting Core (0.1.0)](../../plans/PLAN-01_ACCOUNTING_CORE_0.1.0.md)
