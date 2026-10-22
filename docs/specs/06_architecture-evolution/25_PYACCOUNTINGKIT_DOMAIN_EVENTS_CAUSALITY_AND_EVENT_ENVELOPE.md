# 25_PYACCOUNTINGKIT_DOMAIN_EVENTS_CAUSALITY_AND_EVENT_ENVELOPE.md

# PyAccountingKit — Domain Events, Causality & Event Envelope

> **Projet** : PyAccountingKit  
> **Document** : `25_PYACCOUNTINGKIT_DOMAIN_EVENTS_CAUSALITY_AND_EVENT_ENVELOPE.md`  
> **Statut** : Spécification d'architecture événementielle  
> **Version documentaire** : 1.0  
> **Date** : 22 octobre 2026  
> **Baseline observée** : PyAccountingKit `0.7.0rc1`  
> **Langue** : Français  

---

# 1. Objet du document

Ce document définit le modèle cible des **Domain Events** de PyAccountingKit ainsi que les règles de :

```text
identity
correlation
causation
versioning
serialization
audit
outbox
publication
replay
compatibility
```

Il complète les spécifications existantes relatives :

```text
au modèle de domaine
au posting
à l'audit et à la traçabilité
à la persistance et au Unit of Work
à la public API
aux Architecture Fitness Functions
```

L'objectif principal est de répondre à une question simple :

> **Comment représenter et propager les événements métier de manière cohérente, traçable, versionnée et transactionnellement sûre ?**

---

# 2. Baseline actuelle observée

Le dépôt actuel contient déjà plusieurs briques importantes.

## 2.1 `AuditEvent`

Le code contient actuellement un objet :

```text
AuditEvent
```

avec notamment :

```text
event_type
entity_id
actor_id
occurred_at
payload
```

Cet objet représente une entrée de journal d'audit sérialisable.

---

## 2.2 `OutboxRecord`

Le port outbox expose actuellement :

```text
OutboxRecord
```

avec notamment :

```text
event_type
entity_id
payload
idempotency_key
```

Il est bufferisé dans le `UnitOfWork` et rendu visible au commit.

---

## 2.3 Unit of Work

Le `UnitOfWorkProtocol` regroupe actuellement :

```text
repositories
audit
idempotency
outbox
clock
```

La propriété essentielle est :

```text
business mutation
+
audit
+
idempotency
+
outbox
=
one transaction
```

---

## 2.4 Posting / Reversal

Les orchestrateurs de posting et de reversal produisent déjà :

```text
AuditEvent
OutboxRecord
```

pour des transitions telles que :

```text
ENTRY_POSTED
ENTRY_REVERSED
```

---

## 2.5 Baseline documentaire

La documentation prévoit déjà :

```text
Domain Events
EventId
CorrelationId
event_schema_version
```

mais la codebase actuelle ne possède pas encore une enveloppe canonique homogène couvrant tous ces concepts.

---

# 3. Écart principal

Le modèle actuel répartit la sémantique événementielle entre :

```text
AuditEvent
OutboxRecord
domain event concepts documented
```

mais sans enveloppe commune complète.

Le principal manque identifié est :

```text
CausationId
```

Aucun `CausationId` n'est actuellement présent dans la codebase observée.

La conséquence est qu'une chaîne :

```text
InvoiceIssued
→ ReceivableRecognized
→ JournalEntryPosted
→ SettlementAllocated
```

peut être corrélée conceptuellement, mais sa relation de cause directe n'est pas encore représentée de manière canonique.

---

# 4. Objectifs

Le modèle cible doit permettre :

1. d'identifier chaque événement ;
2. de relier les événements appartenant à une même opération métier ;
3. d'identifier la cause directe d'un événement ;
4. de versionner le schéma ;
5. de distinguer événement métier, audit et message de transport ;
6. de publier via outbox sans duplication métier ;
7. de supporter l'idempotence ;
8. de reconstruire une chaîne causale ;
9. d'assurer la compatibilité avec les consommateurs ;
10. d'éviter de transformer l'outbox en modèle de domaine.

---

# 5. Principe fondamental

La séparation cible est :

```text
DomainEvent
    !=
AuditEvent
    !=
OutboxRecord
    !=
TechnicalLog
```

Même si ces objets peuvent partager certaines métadonnées.

---

# 6. `DomainEvent`

Un `DomainEvent` décrit :

> **un fait métier qui s'est produit dans le domaine.**

Exemples :

```text
JournalEntryValidated
JournalEntryPosted
JournalEntryReversed
AccountingPeriodOpened
AccountingPeriodClosed
SettlementAllocated
ReconciliationConfirmed
FinancialStatementPublished
```

Un DomainEvent est formulé au passé.

---

# 7. `AuditEvent`

Un `AuditEvent` décrit :

> **la trace durable et explicable d'une action ou mutation.**

Il répond typiquement à :

```text
Who?
What?
When?
On what object?
With which context?
```

Un AuditEvent peut contenir :

```text
actor
before/after
reason
object reference
business operation
```

Il peut être produit à partir d'un DomainEvent, mais n'est pas le DomainEvent lui-même.

---

# 8. `OutboxRecord`

Un `OutboxRecord` est :

> **une représentation transactionnelle destinée à une publication différée.**

Il répond à des contraintes d'intégration :

```text
atomic commit
retry
delivery
transport
serialization
```

Il ne doit pas devenir la classe métier canonique de l'événement.

---

# 9. `TechnicalLog`

Un log technique représente :

```text
diagnostic
debug
latency
exception
infrastructure state
```

Exemple :

```text
POST /entries completed in 42 ms
```

Ce n'est pas un DomainEvent.

---

# 10. Event Envelope cible

La cible recommandée est une enveloppe canonique commune.

```text
DomainEventEnvelope
|
+-- event_id
+-- event_type
+-- event_schema_version
+-- occurred_at
+-- correlation_id
+-- causation_id?
+-- aggregate_type
+-- aggregate_id
+-- accounting_entity_id?
+-- actor_context?
+-- source
+-- payload
+-- metadata
```

---

# 11. `EventId`

Chaque événement possède un identifiant stable et unique.

Exemple :

```text
evt_01H...
```

ou un typed identifier équivalent.

Propriété :

```text
one event
=
one EventId
```

---

# 12. `CorrelationId`

`CorrelationId` relie tous les événements participant à une même opération métier ou workflow.

Exemple :

```text
Issue Invoice
      │
      ├── InvoiceIssued
      ├── ReceivableRecognized
      ├── JournalEntryCreated
      └── JournalEntryPosted
```

Tous partagent :

```text
CorrelationId = corr_123
```

---

# 13. `CausationId`

`CausationId` indique :

> **l'événement ou la commande ayant directement causé l'événement courant.**

Exemple :

```text
Command: IssueInvoice
        ↓
InvoiceIssued
        ↓
ReceivableRecognized
        ↓
JournalEntryPosted
```

On peut obtenir :

```text
InvoiceIssued.causation_id
    = command id

ReceivableRecognized.causation_id
    = InvoiceIssued.event_id

JournalEntryPosted.causation_id
    = ReceivableRecognized.event_id
```

---

# 14. Correlation vs Causation

```text
CorrelationId
    = same business journey

CausationId
    = direct parent in the causal chain
```

Ils ne doivent pas être confondus.

---

# 15. Graphe causal

Exemple :

```text
Business Operation
     corr-001
        │
        ▼
InvoiceIssued
event-001
        │
        ▼
ReceivableRecognized
event-002
        │
        ▼
JournalEntryPosted
event-003
```

Avec :

```text
event-002.causation_id = event-001
event-003.causation_id = event-002
```

---

# 16. Root causation

Le premier événement d'une chaîne peut avoir :

```text
causation_id = CommandId
```

ou :

```text
causation_id = None
```

selon le contrat retenu.

La recommandation est de supporter les deux via un type :

```text
CausationRef
```

capable de référencer :

```text
CommandId
EventId
ExternalMessageId
```

---

# 17. CommandId

Il est utile de distinguer :

```text
CommandId
```

de :

```text
CorrelationId
```

Une même corrélation peut contenir plusieurs commandes.

---

# 18. BusinessOperationId

PyAccountingKit peut également conserver :

```text
BusinessOperationId
```

pour regrouper une opération métier durable.

Relation possible :

```text
BusinessOperationId
    1
    ↓
many Commands
    ↓
many Domain Events
```

---

# 19. Event type

Le `event_type` est un code machine stable.

Exemples :

```text
journal_entry.validated
journal_entry.posted
journal_entry.reversed
accounting_period.closed
settlement.allocated
```

Éviter les codes dépendant d'un libellé UI.

---

# 20. Naming convention

Convention recommandée :

```text
<aggregate_or_context>.<past_tense_fact>
```

Exemples :

```text
journal_entry.posted
settlement.allocated
reconciliation.completed
financial_statement.published
```

---

# 21. Versioning

Chaque schéma d'événement public ou persisté doit exposer :

```text
event_schema_version
```

Exemple :

```text
journal_entry.posted
schema_version = 1
```

---

# 22. Package version != event schema version

Ces deux versions sont distinctes.

```text
PyAccountingKit package version
    !=
event schema version
```

Un événement peut rester :

```text
schema_version = 1
```

à travers plusieurs releases du package.

---

# 23. Breaking event change

Exemples de changements breaking :

```text
remove required field
rename semantic field
change meaning of amount
change identity semantics
change timestamp semantics
```

Dans ce cas :

```text
event_schema_version += 1
```

---

# 24. Non-breaking change

Une modification peut être non-breaking si :

```text
new optional field
new metadata
new non-required extension
```

selon le contrat de compatibilité.

---

# 25. Immutability

Un DomainEvent est immutable.

Une fois créé :

```text
event_id
event_type
payload
occurred_at
correlation_id
causation_id
```

ne changent pas.

---

# 26. Event time

Il faut distinguer :

```text
occurred_at
recorded_at
published_at
```

---

# 27. `occurred_at`

Moment métier auquel l'événement est considéré comme survenu.

---

# 28. `recorded_at`

Moment où le système a persisté l'événement ou l'a converti en outbox.

---

# 29. `published_at`

Moment de publication externe.

Ces timestamps ne sont pas interchangeables.

---

# 30. Clock

Toute création déterministe d'événement utilise :

```text
ClockProtocol
```

et non :

```python
datetime.now()
```

appelé arbitrairement dans le domaine.

---

# 31. Aggregate identity

L'enveloppe doit exposer :

```text
aggregate_type
aggregate_id
```

Exemple :

```text
aggregate_type = "JournalEntry"
aggregate_id = "entry:123"
```

---

# 32. Accounting entity scope

Lorsque pertinent :

```text
accounting_entity_id
```

doit être présent pour :

```text
tenant isolation
audit
routing
partitioning
consumer filtering
```

---

# 33. Actor context

Le DomainEvent ne doit pas nécessairement contenir un acteur humain.

Mais l'enveloppe peut exposer un contexte optionnel :

```text
ActorContext
```

---

# 34. `ActorContext`

Peut contenir :

```text
actor_id
actor_type
source
delegation
```

Exemples :

```text
USER
SYSTEM
SERVICE
JOB
IMPORT
```

---

# 35. Event source

Champ possible :

```text
source
```

Exemples :

```text
pyaccountingkit
external_import
consumer_app
migration
scheduled_job
```

---

# 36. Payload

Le payload contient les données métier propres à l'événement.

Exemple :

```json
{
  "entry_id": "entry:123",
  "journal_id": "journal:sales",
  "period_id": "period:2026-10",
  "total_debit": "1200.00",
  "currency": "EUR"
}
```

---

# 37. Payload minimal

Le payload ne doit pas recopier tout l'agrégat.

Préférer :

```text
event-specific facts
```

à :

```text
full object dump
```

---

# 38. No ORM payload

Interdit :

```text
Django model serialization
SQLAlchemy object dump
```

dans un DomainEvent public.

---

# 39. Money serialization

Montants :

```text
Decimal string
+
currency code
```

Exemple :

```json
{
  "amount": "100.00",
  "currency": "EUR"
}
```

Pas de float.

---

# 40. Dates

Les dates et timestamps sont sérialisés en ISO 8601.

---

# 41. Metadata

`metadata` reste réservé à des informations techniques ou extensibles.

Il ne doit pas remplacer les champs structurants.

---

# 42. Exemple d'enveloppe

```json
{
  "event_id": "evt_01K...",
  "event_type": "journal_entry.posted",
  "event_schema_version": 1,
  "occurred_at": "2026-10-22T10:12:30+02:00",
  "correlation_id": "corr_01K...",
  "causation_id": "evt_01J...",
  "aggregate_type": "JournalEntry",
  "aggregate_id": "entry:123",
  "accounting_entity_id": "entity:42",
  "source": "pyaccountingkit",
  "payload": {
    "period_id": "period:2026-10",
    "journal_id": "journal:sales"
  },
  "metadata": {}
}
```

---

# 43. Domain Event catalogue

Le catalogue cible doit être explicite et versionné.

---

# 44. Journal & Posting events

```text
JournalEntryCreated
JournalEntryLineAdded
JournalEntryValidated
JournalEntryPostingRejected
JournalEntryPosted
JournalEntryReversed
```

Tous ne doivent pas forcément être publics.

---

# 45. Period events

```text
AccountingPeriodOpened
AccountingPeriodSoftClosed
AccountingPeriodClosed
AccountingPeriodReopened
```

---

# 46. Chart events

```text
CompanyChartCreated
CompanyAccountCreated
CompanyAccountActivated
CompanyAccountClosed
ReferenceBindingChanged
```

---

# 47. Policy events

```text
AccountingPolicySetCreated
AccountingPolicySetActivated
AccountingPolicySetSuperseded
PolicyEvaluated
```

---

# 48. Subledger events

```text
ReceivableRecognized
PayableRecognized
SettlementRecorded
SettlementAllocated
SettlementReversed
```

---

# 49. Reconciliation events

```text
ReconciliationRunStarted
MatchCandidateGenerated
ReconciliationMatchConfirmed
ReconciliationDifferenceRecorded
ReconciliationCompleted
```

---

# 50. Reporting events

```textFinancialStatementBuilt
FinancialStatementValidated
FinancialStatementPublished
RegulatoryExportProduced
```

---

# 51. Analysis events

Read-side events potentiels :

```text
FinancialAnalysisRunCompleted
AnalysisSnapshotPublished
```

Ils ne doivent pas être confondus avec des mutations comptables.

---

# 52. Consolidation events

```text
ConsolidationRunStarted
ConsolidationAdjustmentRecorded
ConsolidationEliminationRecorded
ConsolidationSnapshotPublished
```

---

# 53. Semantic layer events

```text
SemanticModelActivated
SemanticSnapshotGenerated
SemanticDatasetPublished
```

Ces événements sont analytiques, pas comptables.

---

# 54. Public vs internal events

Chaque événement doit avoir une visibilité.

```text
INTERNAL
PUBLIC
INTEGRATION
```

---

# 55. Internal event

Peut évoluer plus librement.

Exemple :

```text
InternalBalanceCacheInvalidated
```

Il ne doit pas être publié comme contrat public.

---

# 56. Public event

Un événement public est un contrat consommable par un intégrateur.

Il nécessite :

```text
schema version
compatibility rules
documentation
contract tests
```

---

# 57. Integration event

Un Integration Event est une projection transportable d'un DomainEvent.

Exemple :

```text
DomainEvent
    JournalEntryPosted
        ↓ translate
IntegrationEvent
    accounting.entry.posted.v1
```

---

# 58. Domain Event != Integration Event

Le domaine ne doit pas être contraint par :

```text
Kafka
Azure Service Bus
SNS
webhook shape
```

L'adapter d'intégration traduit.

---

# 59. Outbox mapping

Chaîne cible :

```text
DomainEvent
      ↓
Application Orchestrator
      ↓
Outbox Mapper
      ↓
OutboxRecord
      ↓
commit
      ↓
Outbox Dispatcher
      ↓
Integration Event
```

---

# 60. Atomicity

L'OutboxRecord est persisté dans la même transaction que :

```text
business state
audit
idempotency
```

La publication externe se fait après commit.

---

# 61. No publish-before-commit

Interdit :

```text
publish external event
then commit database
```

car une erreur de commit pourrait produire un événement externe pour une mutation inexistante.

---

# 62. Outbox idempotency

L'outbox doit pouvoir identifier de manière stable le message.

Approche possible :

```text
idempotency_key = EventId
```

ou clé dérivée stable.

---

# 63. Delivery semantics

Le framework doit supposer au minimum :

```text
at-least-once delivery
```

pour les transports courants.

Un consommateur doit donc être idempotent.

---

# 64. Exactly-once

PyAccountingKit ne doit pas promettre :

```text
exactly-once distributed delivery
```

sans mécanisme explicite.

---

# 65. Consumer idempotency

Le consumer doit pouvoir stocker :

```text
processed EventId
```

ou une clé de déduplication équivalente.

---

# 66. Event ordering

Le système ne doit pas supposer un ordre global total.

Il peut garantir un ordre local par agrégat lorsque l'adapter le permet.

---

# 67. Aggregate revision

Il peut être utile d'ajouter :

```text
aggregate_revision
```

à l'enveloppe.

Cela permet :

```text
event ordering
optimistic consistency
consumer validation
```

---

# 68. Event sequence

Option possible :

```text
aggregate_sequence
```

Exemple :

```text
JournalEntry revision 1
JournalEntry revision 2
```

---

# 69. Global sequence

Un `global_sequence` peut exister dans un adapter persistant, mais ne doit pas devenir un invariant du domaine si tous les adapters ne peuvent pas le garantir.

---

# 70. Causality across processes

Lorsqu'un événement externe déclenche une commande :

```text
incoming message.event_id
```

devient :

```text
causation_id
```

de la nouvelle commande ou du nouvel événement.

---

# 71. Correlation propagation

Une corrélation existante est propagée.

Exemple :

```text
Message A
correlation_id = C1
      ↓
Command B
correlation_id = C1
      ↓
Event C
correlation_id = C1
```

---

# 72. New correlation

Si aucune corrélation n'existe :

```text
Application Service
```

génère un nouveau `CorrelationId`.

---

# 73. Command Context

Un objet cible peut être :

```text
CommandContext
|
+-- command_id
+-- correlation_id
+-- causation_id?
+-- actor_context
+-- idempotency_key?
+-- requested_at
```

---

# 74. EventFactory

Une factory peut centraliser la création d'enveloppes.

Exemple :

```python
class DomainEventFactory:
    def create(...):
        ...
```

Elle reçoit :

```text
Clock
IdFactory
CommandContext
```

---

# 75. No hidden global context

Éviter :

```text
thread-local magic
implicit global correlation
```

Le contexte doit être injecté explicitement lorsque nécessaire.

---

# 76. Async future compatibility

Le design doit pouvoir fonctionner avec :

```text
sync API today
async consumers tomorrow
```

sans changer le contrat événementiel.

---

# 77. Audit mapping

Une mutation critique peut produire :

```text
DomainEvent
```

et :

```text
AuditEvent
```

dans la même transaction.

---

# 78. Exemple

```text
DomainEvent
    journal_entry.posted

AuditEvent
    actor X posted entry Y at time Z
```

Le premier décrit le fait métier.

Le second décrit la trace contrôlée.

---

# 79. Audit enrichment

AuditEvent peut contenir plus d'informations que le DomainEvent :

```text
actor IP
reason
approval
before/after
source application
```

selon policy.

---

# 80. Domain payload minimization

Les données sensibles ne doivent pas être propagées par défaut dans les événements.

Exemples à éviter :

```text
bank raw payload
personal data
full document content
credentials
tokens
```

---

# 81. Event privacy classification

Une métadonnée possible :

```text
data_classification
```

Exemples :

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
```

---

# 82. Tenant isolation

L'enveloppe doit permettre de filtrer un événement par :

```text
tenant / accounting entity
```

sans lire le payload.

---

# 83. No cross-tenant dispatch

Un dispatcher ne doit pas publier un événement d'une entité vers un canal d'un autre tenant par mauvaise résolution de routing.

---

# 84. Serialization contract

Un événement public doit être sérialisé de manière déterministe.

Recommandations :

```text
JSON object
stable field names
ISO dates
Decimal as string
sorted canonical encoding for checksums if needed
```

---

# 85. Canonical checksum

Pour certains artefacts critiques, on peut calculer :

```text
event_checksum
```

sur une sérialisation canonique.

Ce checksum ne doit pas inclure des champs de transport mutables comme :

```text
published_at
delivery_attempt
```

---

# 86. Event Manifest

Artifact recommandé :

```text
DOMAIN_EVENT_MANIFEST.json
```

---

# 87. Contenu du manifest

Exemple :

```json
{
  "contract_version": "1",
  "events": [
    {
      "event_type": "journal_entry.posted",
      "schema_version": 1,
      "visibility": "PUBLIC",
      "owner": "ledger",
      "payload_schema": "..."
    }
  ]
}
```

---

# 88. Pourquoi un manifest

Il permet :

```text
schema diff
compatibility gate
documentation
consumer validation
release evidence
```

---

# 89. Event Schema Registry

Le framework peut fournir un registry instance-scoped.

```text
EventSchemaRegistry
```

Il contient :

```text
event type
schema version
serializer
deserializer
visibility
owner
```

---

# 90. No global mutable registry

Éviter une registry modifiable globalement à l'import.

---

# 91. Schema compatibility

Chaque nouvelle release doit comparer :

```text
previous event manifest
vs
current event manifest
```

---

# 92. Release gate

Après gel d'un événement public :

```text
breaking change without schema bump
=
release failure
```

---

# 93. Unknown event version

Un consumer recevant une version inconnue doit :

```text
reject
dead-letter
or route to explicit compatibility handler
```

mais ne doit pas interpréter silencieusement le payload comme une ancienne version.

---

# 94. Upcasting

Un adapter peut fournir :

```text
v1 event
→ upcast
→ v2 internal representation
```

si la transformation est déterministe et documentée.

---

# 95. Downcasting

Le downcasting vers une ancienne version publique doit rester exceptionnel.

---

# 96. Replay

Le replay doit être défini explicitement.

Trois concepts distincts :

```text
event replay
command replay
state reconstruction
```

---

# 97. Event replay

Rejouer un Integration Event vers un consumer ne doit pas réexécuter aveuglément un effet économique non idempotent.

---

# 98. Command replay

Une commande rejouée doit conserver son :

```text
idempotency_key
```

si son identité métier n'a pas changé.

---

# 99. Event sourcing

PyAccountingKit n'est pas automatiquement un système event-sourced.

La présence de Domain Events ne signifie pas :

```text
aggregate state = replay of all events
```

---

# 100. Source of truth

La source de vérité actuelle reste :

```text
canonical persisted domain state
```

et les événements servent :

```text
traceability
integration
orchestration
audit support
```

sauf ADR futur explicitant un éventuel event sourcing.

---

# 101. Event storage

Un `DomainEventStore` persistant peut être introduit pour certains besoins, mais ne doit pas être confondu avec l'outbox.

---

# 102. EventStore vs Outbox

```text
EventStore
    = durable domain history

Outbox
    = reliable publication queue
```

Ce sont deux responsabilités distinctes.

---

# 103. Baseline migration

Le système actuel utilise :

```text
AuditEvent
OutboxRecord
```

sans `CausationId`.

La migration doit être progressive.

---

# 104. Phase 1 — Typed IDs

Introduire :

```text
EventId
CorrelationId
CausationId
CommandId
```

dans `core` ou shared primitives.

---

# 105. Phase 2 — Event Envelope

Introduire :

```text
DomainEventEnvelope
```

sans casser immédiatement :

```text
AuditEvent
OutboxRecord
```

---

# 106. Phase 3 — Outbox enrichment

Étendre `OutboxRecord` pour transporter :

```text
event_id
event_schema_version
correlation_id
causation_id
occurred_at
```

ou encapsuler directement une projection de l'enveloppe.

---

# 107. Phase 4 — Audit linkage

Permettre à `AuditEvent` de référencer :

```text
domain_event_id
correlation_id
```

lorsque pertinent.

---

# 108. Phase 5 — Manifest

Créer :

```text
DOMAIN_EVENT_MANIFEST.json
```

---

# 109. Phase 6 — Public event contracts

Ne déclarer publics que les événements réellement nécessaires.

---

# 110. Backward compatibility

Pendant la migration, les anciens champs :

```text
event_type
entity_id
payload
idempotency_key
```

doivent rester disponibles tant que la compatibilité n'est pas officiellement rompue.

---

# 111. Recommended target classes

Conceptuellement :

```python
@dataclass(frozen=True, slots=True)
class DomainEventEnvelope:
    event_id: EventId
    event_type: str
    event_schema_version: int
    occurred_at: datetime
    correlation_id: CorrelationId
    causation_id: CausationId | None
    aggregate_type: str
    aggregate_id: str
    accounting_entity_id: str | None
    payload: Mapping[str, object]
    metadata: Mapping[str, object]
```

---

# 112. Payload typing

Pour les événements critiques, préférer :

```text
typed payload
```

à :

```text
Mapping[str, object]
```

Exemple :

```python
@dataclass(frozen=True)
class JournalEntryPostedPayload:
    entry_id: EntryId
    journal_id: JournalId
    period_id: PeriodId
```

---

# 113. Envelope + typed payload

Concept :

```python
DomainEventEnvelope[JournalEntryPostedPayload]
```

si la stratégie de typing retenue le permet.

---

# 114. Public serialization

Le type Python interne peut être riche.

La sérialisation publique reste :

```text
JSON-compatible
stable
versioned
```

---

# 115. Command → Domain Event

Exemple :

```text
PostJournalEntryCommand
        ↓
Posting Application Service
        ↓
PostingService
        ↓
JournalEntryPosted
```

---

# 116. Domain Service responsibility

Le Domain Service décide :

```text
is transition valid?
what new state?
```

Il ne décide pas :

```text
Kafka topic
outbox table
HTTP webhook
```

---

# 117. Application responsibility

L'application orchestre :

```text
load aggregate
call domain
persist aggregate
record audit
stage outbox
commit
```

---

# 118. Adapter responsibility

L'adapter gère :

```text
database
transport
serialization
retry infrastructure
```

---

# 119. Example posting transaction

```text
BEGIN
  claim idempotency key
  load entry
  validate transition
  save posted entry
  record AuditEvent
  stage OutboxRecord
COMMIT
```

Après commit :

```text
dispatcher
→ publish integration event
```

---
# 120. Failure before commit

Résultat :

```text
no business mutation
no outbox visibility
no external publish
```

---

# 121. Failure after commit but before publish

L'outbox reste disponible.

Le dispatcher peut réessayer.

---

# 122. Duplicate publish

Le consumer utilise :

```text
EventId
```

ou une clé idempotente pour dédupliquer.

---

# 123. Event ordering conflict

Si un consumer reçoit :

```text
revision 7
before revision 6
```

il doit pouvoir :

```text
buffer
reject
or reconcile
```

selon son contrat.

---

# 124. Uncertainty

Un état :

```text
publish outcome unknown
```

n'est pas nécessairement :

```text
business event failed
```

Le domaine comptable a peut-être déjà commité.

Il faut réconcilier l'outbox/transport.

---

# 125. Domain event failure semantics

Une erreur de transport après commit ne doit pas annuler rétroactivement :

```text
JournalEntryPosted
```

dans le domaine.

---

# 126. Eventual consistency

Les consommateurs d'événements externes doivent accepter :

```text
eventual consistency
```

lorsque le modèle l'exige.

---

# 127. Strong consistency boundary

La cohérence forte reste dans le :

```text
UnitOfWork
```

pas entre tous les systèmes distribués.

---

# 128. Observability

Chaque event processing log doit pouvoir inclure :

```text
event_id
correlation_id
causation_id
event_type
aggregate_id
```

sans recopier les données sensibles du payload.

---

# 129. Distributed tracing

Un adapter peut mapper :

```text
correlation_id
```

vers un contexte de tracing, mais ces identités ne doivent pas être confondues.

```text
CorrelationId
!=
TraceId
```

---

# 130. TraceId

`TraceId` est technique.

`CorrelationId` est métier/application.

Un mapping est possible, pas une équivalence obligatoire.

---

# 131. Event lineage

La causalité permet de reconstruire :

```text
who caused what
```

Exemple :

```text
PaymentImported
  ↓
SettlementRecorded
  ↓
SettlementAllocated
  ↓
ReceivableSettled
```

---

# 132. Event lineage query

Une future API peut permettre :

```python
accounting.events.trace(event_id)
```

retournant :

```text
ancestors
descendants
correlation
```

sans exposer le store physique.

---

# 133. Audit query

Une API distincte peut permettre :

```python
accounting.audit.for_object(...)
```

La séparation demeure.

---

# 134. Event privacy

La query event ne doit pas contourner les règles d'autorisation.

---

# 135. Event retention

La rétention dépend du type d'événement.

Exemples :

```text
public integration event
audit event
temporary internal event
```

peuvent avoir des policies différentes.

---

# 136. Audit retention

Les AuditEvents peuvent avoir une rétention réglementaire plus longue que certains Integration Events.

---

# 137. Deletion

Un événement financier critique ne doit pas être supprimé physiquement sans policy explicite.

Préférer :

```text
retention lifecycle
archive
legal hold
```

---

# 138. PII

Si le payload contient une donnée personnelle :

```text
minimize
tokenize
reference by ID
```

plutôt que recopier une fiche entière.

---

# 139. Event security

La couche transport peut ajouter :

```text
signature
encryption
transport headers
```

sans modifier le DomainEvent canonique.

---

# 140. Signature

Une signature cryptographique éventuelle appartient au :

```text
integration envelope
```

ou à l'artifact de preuve.

---

# 141. Event checksum

Un checksum peut soutenir :

```text
tamper detection
evidence
replay verification
```

mais ne remplace pas une signature.

---

# 142. Golden event scenarios

Créer des scénarios de qualification.

---

# 143. Golden scenario — posting

```text
Post command
      ↓
JournalEntryPosted
      ↓
AuditEvent
      ↓
OutboxRecord
      ↓
consumer
```

Vérifier :

```text
same correlation
correct causation
one EventId
one business effect
```

---

# 144. Golden scenario — reversal

```text
JournalEntryPosted
      ↓
Reverse command
      ↓
JournalEntryReversed
      ↓
reversal entry
```

Vérifier la causalité et la non-modification destructive de l'historique.

---

# 145. Golden scenario — settlement

```text
PaymentRecorded
      ↓
SettlementAllocated
      ↓
ReceivableSettled
```

---

# 146. Golden scenario — period close

```text
ClosingStarted
      ↓
ClosingAdjustmentsPosted
      ↓
ControlsPassed
      ↓
AccountingPeriodClosed
```

---

# 147. Contract tests

Tester :

```text
event type stable
schema version stable
required fields
serialization
deserialization
correlation propagation
causation propagation
idempotency
```

---

# 148. Property tests

Exemples :

```text
event serialize → deserialize = equivalent event
```

```text
EventId remains unchanged
```

---

# 149. Outbox tests

Scénarios :

```text
rollback → no visible outbox
commit → outbox visible
retry → no duplicate business mutation
```

---

# 150. Consumer tests

Un consumer doit être testé avec :

```text
duplicate event
unknown version
out-of-order event
missing optional field
```

---

# 151. Architecture Fitness Functions

Règles proposées :

```text
AFF-EVENT-001
domain events do not import transport SDKs

AFF-EVENT-002
public event schemas are versioned

AFF-EVENT-003
AuditEvent != DomainEvent

AFF-EVENT-004
OutboxRecord != DomainEvent

AFF-EVENT-005
domain event core does not depend on adapters
```

---

# 152. Public API

La public API ne doit pas exposer tous les DomainEvents automatiquement.

Seuls les événements explicitement déclarés publics sont contractuels.

---

# 153. Event API possible

Future surface :

```text
accounting.events
```

avec :

```text
list_public_schemas
deserialize
validate
```

mais pas nécessairement accès au store.

---

# 154. Event subscription

Un mécanisme de subscription in-process peut être ajouté mais doit rester optionnel.

---

# 155. No hidden side effects

Un handler in-process ne doit pas lancer automatiquement une mutation financière critique sans transaction/orchestration explicite.

---

# 156. Handler categories

```text
DOMAIN_HANDLER
APPLICATION_HANDLER
INTEGRATION_HANDLER
PROJECTION_HANDLER
```

---

# 157. Projection handler

Peut mettre à jour :

```text
read model
cache
semantic projection
```

mais pas contourner le write model.

---

# 158. Integration handler

Traduit vers :

```text
email
webhook
queue
external service
```

via adapters.

---

# 159. Failure isolation

Un handler downstream non critique ne doit pas casser un business commit déjà validé.

---

# 160. Synchronous handlers

Les handlers synchrones dans la transaction doivent être réservés aux invariants nécessitant une cohérence forte.

---

# 161. Asynchronous handlers

Préférables pour :

```text
notifications
analytics refresh
external integration
```

---

# 162. Event storming alignment

Le catalogue d'événements doit refléter le langage ubiquitaire.

Éviter :

```text
EntityUpdated
RecordChanged
DataSaved
```

pour des faits métier importants.

Préférer :

```text
AccountingPeriodClosed
JournalEntryPosted
SettlementAllocated
```

---

# 163. Generic event anti-pattern

Interdit comme unique contrat :

```text
ObjectChanged
```

avec un payload opaque.

---

# 164. Event explosion

Inversement, ne pas créer un événement pour chaque mutation technique.

Exemple inutile :

```text
JournalEntryDescriptionFieldChanged
```

sauf besoin métier explicite.

---

# 165. Business significance rule

Un DomainEvent est justifié s'il représente un fait :

```text
significant to domain
useful for downstream behavior
useful for audit/traceability
or required for integration
```

---

# 166. Event ownership

Chaque event type possède un owner.

Exemple :

```text
journal_entry.posted
owner = ledger
```

---

# 167. Consumer ownership

Un consumer ne peut pas redéfinir le sens de l'événement.

Il peut uniquement :

```text
interpret according to contract
```

---

# 168. Cross-context integration

Les bounded contexts communiquent préférablement via :

```text
public contracts
queries
events
```

plutôt que par imports internes.

---

# 169. Event choreography

La choreography est acceptable pour des réactions downstream simples.

---

# 170. Orchestration

Pour un workflow financier critique multi-étapes, une orchestration explicite peut être préférable afin d'éviter une chaîne opaque de handlers.

---

# 171. Saga

Le terme `Saga` ne doit être introduit que si :

```text
long-running distributed business process
+
compensation semantics
```

existent réellement.

---

# 172. Compensation

Une compensation n'est pas nécessairement un rollback.

En comptabilité :

```text
reversal
```

est souvent une nouvelle opération compensatoire.

---

# 173. Event naming for reversal

Éviter :

```text
JournalEntryDeleted
```

pour une contrepassation.

Préférer :

```text
JournalEntryReversed
```

---

# 174. Accounting immutability

Les événements doivent refléter la nature append-oriented du domaine.

---

# 175. Event timeline

Exemple :

```text
JournalEntryCreated
JournalEntryValidated
JournalEntryPosted
JournalEntryReversed
```

et non :

```text
JournalEntryStatusChanged
JournalEntryStatusChanged
JournalEntryStatusChanged
```

---

# 176. Determinism

À contexte identique, la création d'un événement doit être déterministe sauf pour :

```text
EventId
timestamp
```

qui sont fournis par des dépendances explicites.

---

# 177. Testing clock

Les tests utilisent :

```text
FrozenClock
```

pour stabiliser `occurred_at`.

---

# 178. Testing id factory

Une future :

```text
DeterministicEventIdFactory
```

peut simplifier les golden tests.

---

# 179. Event fixture

Le testing toolkit peut fournir :

```text
event_builder
event_assertions
fake_outbox
```

---

# 180. Documentation generation

Le `DOMAIN_EVENT_MANIFEST` peut générer automatiquement :

```text
event catalogue docs
consumer schemas
compatibility report
```

---

# 181. JSON Schema

Les événements publics peuvent disposer d'un :

```text
JSON Schema
```

par version.

---

# 182. Schema location

Exemple :

```text
schemas/events/
├── journal_entry.posted.v1.json
├── journal_entry.reversed.v1.json
└── accounting_period.closed.v1.json
```

---

# 183. Avro / Protobuf

Ils peuvent être supportés par adapters futurs.

Ils ne deviennent pas une dépendance core.

---

# 184. Content type

L'integration envelope peut déclarer :

```text
content_type
```

sans modifier le DomainEvent.

---

# 185. Topic naming

Les noms de topics/queues restent configuration adapter-specific.

Le domain event ne connaît pas :

```text
kafka topic
azure topic
sns topic
```

---

# 186. Routing key

Même principe :

```text
routing
```

est une responsabilité d'intégration.

---

# 187. Webhooks

Un webhook peut être un consumer des Integration Events.

---

# 188. Webhook retries

Les retries de webhook ne doivent pas générer un nouveau DomainEvent.

---

# 189. Idempotency chain

Il faut distinguer :

```text
command idempotency
event identity
delivery attempt identity
```

---

# 190. Delivery attempt

Chaque tentative de publication peut avoir :

```text
delivery_attempt_id
```

mais cet identifiant n'est pas l'EventId.

---

# 191. Dead-letter

Un adapter peut supporter :

```text
dead-letter queue
```

pour les événements non livrables.

---

# 192. Dead-letter != business failure

Un événement en DLQ peut représenter une mutation métier déjà commise.

---

# 193. Recovery

La recovery consiste à restaurer la livraison, pas à répéter aveuglément la mutation source.

---

# 194. Monitoring

Métriques possibles :

```text
outbox_pending
outbox_publish_latency
outbox_retry_count
event_consumer_failures
event_schema_rejections
```

---

# 195. Alerting

Alertes recommandées :

```text
outbox backlog growing
repeated poison event
unknown schema version
cross-tenant routing anomaly
```

---

# 196. Event retention metadata

Artifact :

```text
retention_policy
```

peut être attaché au manifest, sans faire partie du payload.

---

# 197. Event confidentiality metadata

Même logique pour :

```text
classification
```

---

# 198. Evidence

Un Evidence Bundle de release peut inclure :

```text
DOMAIN_EVENT_MANIFEST.json
event schema checksums
compatibility diff
contract test results
```

---
# 199. Proposed package topology

Dans la topologie actuelle :

```text
pyaccountingkit/
├── core/
│   └── event_ids.py
├── domain/
│   └── events/
├── application/
│   └── eventing/
├── ports/
│   └── outbox.py
└── adapters/
    └── eventing/
```

---

# 200. Domain-first topology future

Dans une future organisation par bounded context :

```text
ledger/
├── domain/
│   └── events.py
├── application/
│   └── handlers.py
└── ports/
```

et un shared minimal fournit :

```text
EventId
CorrelationId
CausationId
DomainEventEnvelope primitives
```

---

# 201. Minimal shared event primitives

Le shared kernel ne doit contenir que :

```text
EventId
CorrelationId
CausationId
EventSchemaVersion
base envelope
```

Pas :

```text
JournalEntryPosted
SettlementAllocated
```

qui appartiennent à leurs contexts.

---

# 202. Compatibility with existing AuditEvent

`AuditEvent` doit pouvoir évoluer sans être supprimé immédiatement.

Possibilité :

```text
AuditEvent
    + domain_event_id?
    + correlation_id?
```

---

# 203. Compatibility with existing OutboxRecord

`OutboxRecord` peut évoluer vers :

```text
OutboxRecord
    event_id
    event_type
    event_schema_version
    correlation_id
    causation_id
    occurred_at
    entity_id
    payload
    idempotency_key
```

---

# 204. Current naming migration

Les valeurs existantes :

```text
ENTRY_POSTED
ENTRY_REVERSED
```

peuvent être conservées temporairement.

La cible peut être :

```text
journal_entry.posted
journal_entry.reversed
```

La migration doit être versionnée.

---

# 205. No silent rename

Changer :

```text
ENTRY_POSTED
```

en :

```text
journal_entry.posted
```

sans compatibility mapping serait breaking pour un consumer existant.

---

# 206. Event aliases

Un adapter de compatibilité peut accepter temporairement :

```text
ENTRY_POSTED
```

comme alias de :

```text
journal_entry.posted
```

---

# 207. Deprecation

Cycle :

```text
ACTIVE
→ DEPRECATED
→ RETIRED
```

pour les public event schemas.

---

# 208. Migration evidence

Un test doit démontrer que :

```text
old consumer contract
```

reste fonctionnel pendant la fenêtre de compatibilité annoncée.

---

# 209. ADR proposées

| ADR | Décision |
|---|---|
| ADR-EVT-001 | DomainEvent, AuditEvent, OutboxRecord et TechnicalLog sont des concepts distincts |
| ADR-EVT-002 | Tout DomainEvent possède un EventId |
| ADR-EVT-003 | Toute opération corrélée possède un CorrelationId |
| ADR-EVT-004 | CausationId représente la cause directe |
| ADR-EVT-005 | CorrelationId et CausationId ne sont jamais synonymes |
| ADR-EVT-006 | Les événements publics sont versionnés avec event_schema_version |
| ADR-EVT-007 | Package version et event schema version sont distinctes |
| ADR-EVT-008 | Les DomainEvents sont immuables |
| ADR-EVT-009 | occurred_at, recorded_at et published_at restent distincts |
| ADR-EVT-010 | ClockProtocol fournit les temps métier |
| ADR-EVT-011 | Les payloads publics sont framework-neutral |
| ADR-EVT-012 | Money est sérialisé sans float |
| ADR-EVT-013 | Un DomainEvent ne contient pas un dump complet d'aggregate par défaut |
| ADR-EVT-014 | Public Event et Integration Event restent distincts |
| ADR-EVT-015 | Le transport ne contamine jamais le domaine |
| ADR-EVT-016 | L'outbox est atomique avec la mutation source |
| ADR-EVT-017 | Aucun événement externe n'est publié avant commit |
| ADR-EVT-018 | Les consumers doivent tolérer l'at-least-once |
| ADR-EVT-019 | EventId sert de clé naturelle de déduplication événementielle |
| ADR-EVT-020 | PyAccountingKit ne promet pas exactly-once distribué |
| ADR-EVT-021 | Aucun ordre global d'événements n'est supposé |
| ADR-EVT-022 | L'ordre par aggregate peut être renforcé via revision/sequence |
| ADR-EVT-023 | La causalité est propagée entre processus |
| ADR-EVT-024 | La corrélation existante est propagée, sinon créée explicitement |
| ADR-EVT-025 | AuditEvent peut référencer un DomainEvent sans le remplacer |
| ADR-EVT-026 | OutboxRecord est une projection de publication, pas le modèle de domaine |
| ADR-EVT-027 | EventStore et Outbox sont des responsabilités distinctes |
| ADR-EVT-028 | La présence d'événements n'implique pas Event Sourcing |
| ADR-EVT-029 | Les événements publics apparaissent dans un manifest machine-readable |
| ADR-EVT-030 | Un breaking schema change nécessite une nouvelle version |
| ADR-EVT-031 | Une version inconnue échoue explicitement |
| ADR-EVT-032 | Les upcasters sont déterministes et versionnés |
| ADR-EVT-033 | Les données sensibles sont minimisées dans les payloads |
| ADR-EVT-034 | Tenant/entity scope est exposé hors payload lorsque nécessaire |
| ADR-EVT-035 | CorrelationId et TraceId sont distincts |
| ADR-EVT-036 | Les DomainEvents utilisent le langage ubiquitaire |
| ADR-EVT-037 | Les événements techniques génériques ne remplacent pas les événements métier |
| ADR-EVT-038 | Les handlers downstream ne contournent pas les write workflows |
| ADR-EVT-039 | Reversal est un nouvel effet métier, pas un delete |
| ADR-EVT-040 | Le manifest d'événements participe aux release gates |

---

# 210. Architecture Fitness Functions associées

```text
AFF-EVENT-001
Domain events must not import transport SDKs

AFF-EVENT-002
Public event schemas must declare a version

AFF-EVENT-003
AuditEvent and DomainEvent remain distinct

AFF-EVENT-004
OutboxRecord and DomainEvent remain distinct

AFF-EVENT-005
Event primitives do not depend on adapters

AFF-EVENT-006
Public schema changes require manifest compatibility check
```

---

# 211. Definition of Done — Event Envelope

```text
[ ] EventId defined
[ ] CorrelationId defined
[ ] CausationId defined
[ ] CommandId defined or explicitly rejected
[ ] DomainEventEnvelope defined
[ ] event_schema_version mandatory for public events
[ ] occurred_at semantics defined
[ ] aggregate reference defined
[ ] accounting entity scope defined
[ ] actor context policy defined
[ ] deterministic serialization defined
```

---

# 212. Definition of Done — Outbox integration

```text
[ ] OutboxRecord linked to EventId
[ ] correlation propagated
[ ] causation propagated
[ ] schema version persisted
[ ] rollback hides staged messages
[ ] commit exposes messages
[ ] duplicate dispatch is safe
[ ] delivery attempts do not change EventId
```

---

# 213. Definition of Done — Public events

```text
[ ] public event catalogue defined
[ ] internal/public distinction defined
[ ] DOMAIN_EVENT_MANIFEST generated
[ ] schema compatibility gate enabled
[ ] JSON schema or equivalent available
[ ] unknown versions fail explicitly
[ ] consumer contract tests exist
```

---

# 214. Initial implementation roadmap

## EVT-00 — Core typed identifiers

```text
EventId
CorrelationId
CausationId
CommandId
```

## EVT-01 — Canonical envelope

```text
DomainEventEnvelope
EventSchemaVersion
ActorContext
```

## EVT-02 — Posting events

```text
JournalEntryPosted
JournalEntryReversed
```

## EVT-03 — Outbox evolution

```text
EventId
Correlation
Causation
Schema version
```

## EVT-04 — Audit linkage

```text
domain_event_id
correlation_id
```

## EVT-05 — Manifest

```text
DOMAIN_EVENT_MANIFEST.json
```

## EVT-06 — Public schemas

```text
JSON Schema
compatibility tests
```

## EVT-07 — Cross-context propagation

```text
subledgers
reconciliation
closing
reporting
```

## EVT-08 — Consumer qualification

```text
duplicates
out-of-order
unknown version
retry
```

---

# 215. Priorités

| Lot | Priorité |
|---|---:|
| EVT-00 | P0 |
| EVT-01 | P0 |
| EVT-02 | P0 |
| EVT-03 | P0 |
| EVT-04 | P1 |
| EVT-05 | P1 |
| EVT-06 | P1 |
| EVT-07 | P2 |
| EVT-08 | P1 |

---

# 216. Exemple complet — Posting

```text
Command
PostJournalEntry
command_id = cmd-001
correlation_id = corr-001
causation_id = null
        │
        ▼
JournalEntryPosted
event_id = evt-001
correlation_id = corr-001
causation_id = cmd-001
        │
        ├── AuditEvent
        │     domain_event_id = evt-001
        │
        └── OutboxRecord
              event_id = evt-001
```

---

# 217. Exemple complet — Réaction downstream

```text
JournalEntryPosted
evt-001
corr-001
        │
        ▼
ProjectionHandler
        │
        ▼
TrialBalanceProjectionUpdated
evt-002
corr-001
causation_id = evt-001
```

Si ce second événement est seulement technique, il peut rester internal.

---

# 218. Exemple — Settlement

```text
PaymentRecorded
evt-A
corr-X
        │
        ▼
SettlementAllocated
evt-B
corr-X
cause = evt-A
        │
        ▼
ReceivableSettled
evt-C
corr-X
cause = evt-B
```

---

# 219. Exemple — Closing

```text
ClosePeriodCommand
        ↓
ClosingStarted
        ↓
ClosingAdjustmentPosted
        ↓
ClosingControlsPassed
        ↓
AccountingPeriodClosed
```

Tous les événements partagent le même `CorrelationId`.

Chaque événement référence sa cause directe.

---

# 220. Positionnement final

Le modèle événementiel cible devient :

```text
DOMAIN FACT
    ↓
DomainEvent
    ↓
Canonical Envelope
    ├── EventId
    ├── CorrelationId
    ├── CausationId
    ├── Schema Version
    └── Aggregate Context
          │
          ├── Audit Projection
          ├── Outbox Projection
          ├── Internal Handlers
          └── Integration Events
```

---

# 221. Conclusion

PyAccountingKit possède déjà une base solide :

```text
AuditEvent
OutboxRecord
UnitOfWork
idempotency
transactional publication
```

La prochaine étape n'est pas de remplacer ces briques.

Elle consiste à les relier autour d'un contrat événementiel canonique.

La cible est :

```text
one business fact
      ↓
one EventId
      ↓
one causal position
      ↓
one correlation context
      ↓
many controlled projections
```

Ainsi :

```text
DomainEvent
    describes the fact

AuditEvent
    explains the action

OutboxRecord
    ensures reliable publication

IntegrationEvent
    serves external consumers

TechnicalLog
    diagnoses the runtime
```

Le bénéfice attendu est une architecture où la chaîne :

```text
what happened
why it happened
what caused it
what it caused next
```

reste reconstruisible, versionnée et auditée sans coupler le domaine comptable à l'infrastructure de transport.