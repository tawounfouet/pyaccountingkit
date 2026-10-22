# 37_PYACCOUNTINGKIT_DOMAIN_EVENTS_COVERAGE_AND_EMISSION_RULES.md

# PyAccountingKit — Domain Events Coverage & Emission Rules

> **Projet** : PyAccountingKit  
> **Document** : `37_PYACCOUNTINGKIT_DOMAIN_EVENTS_COVERAGE_AND_EMISSION_RULES.md`  
> **Statut** : Spécification transverse — couverture des Domain Events et règles d’émission  
> **Date** : 22 octobre 2026  
> **Baseline de modélisation** :
> - `35_PYACCOUNTINGKIT_BUSINESS_LIFECYCLES_ARCHITECTURE.md`
> - `36_PYACCOUNTINGKIT_STATE_MACHINES_AND_TRANSITION_RULES.md`
> **Baseline runtime observée** : PyAccountingKit `0.7.0rc1`  
> **Portée** :
> - classification des faits métier ;
> - couverture des Domain Events ;
> - règles d’émission ;
> - séparation Domain / Audit / Application / Integration / Operational events ;
> - règles de mapping vers audit et outbox ;
> - règles de granularité et de versioning.  
> **Hors scope volontaire** :
> - Event Sourcing ;
> - broker/message bus ;
> - orchestration distribuée ;
> - schéma détaillé de l’Event Envelope, traité par la spec `25` ;
> - mapping exhaustif transition → event, traité par `38`.  
> **Document suivant prévu** :
> - `38_PYACCOUNTINGKIT_LIFECYCLE_STATE_MACHINE_EVENT_MAPPING.md`

---

# 1. Objet

Cette spécification répond à :

> **Quels faits métier PyAccountingKit doivent devenir des Domain Events, quand doivent-ils être émis, et lesquels ne doivent surtout pas devenir des événements ?**

Les documents précédents ont établi :

```text
35
What objects have a lifecycle?

36
What transitions are legal?
```

Le présent document établit :

```text
37
Which meaningful business facts deserve an event?
```

---

# 2. Principe cardinal

Un Domain Event représente :

```text
a meaningful business fact
that has already happened
```

Il ne représente pas :

```text
a command
a request
a validation attempt
a technical log
a database mutation
a generic state change
```

---

# 3. Règle de base

```text
Meaningful business fact
+
stable business semantics
+
potential downstream relevance
=
DomainEvent candidate
```

---

# 4. Anti-règle

```text
Business object exists
=
must emit events
```

est faux.

PyAccountingKit ne doit pas produire d’événements pour chaque :

```text
object creation
field update
calculation
line addition
validation helper
repository call
```

---

# 5. Event ≠ State

Un changement d’état peut produire un event.

Mais ce n’est pas automatique.

Exemple :

```text
ImportBatch
PARSED → NORMALIZED
```

peut rester un détail de processus sans Domain Event public.

---

# 6. Event sans changement d’état

Un Domain Event peut exister même si le status ne change pas.

Exemple :

```text
Settlement
PARTIALLY_ALLOCATED
    ↓ allocate 100
PARTIALLY_ALLOCATED
```

mais :

```text
SettlementAllocated
```

reste un fait métier significatif.

---

# 7. Event ≠ Command

Command :

```text
PostEntry
```

Event :

```text
JournalEntryPosted
```

---

# 8. Event ≠ AuditEvent

`AuditEvent` répond à :

```text
who did what
when
for compliance / traceability
```

`DomainEvent` répond à :

```text
what meaningful business fact occurred
```

---

# 9. Event ≠ IntegrationEvent

`DomainEvent` est interne au modèle métier.

`IntegrationEvent` est un contrat destiné à :

```text
another system
another bounded context
external consumer
```

Ils peuvent être liés, mais ne sont pas identiques.

---

# 10. Event ≠ OperationalEvent

Operational events :

```text
worker restarted
retry scheduled
outbox dispatched
database unavailable
```

ne sont pas des Domain Events comptables.

---

# 11. Event ≠ Log

Un log :

```text
debug/info/warning/error
```

n’est pas un Domain Event.

---

# 12. Taxonomie canonique

PyAccountingKit distingue :

```text
DOMAIN_EVENT_REQUIRED
DOMAIN_EVENT_OPTIONAL
APPLICATION_EVENT_ONLY
INTEGRATION_EVENT_ONLY
AUDIT_ONLY
OPERATIONAL_ONLY
NO_EVENT
```

---

# 13. DOMAIN_EVENT_REQUIRED

Utiliser quand le fait :

```text
changes accounting/business meaning
affects lifecycle
must be explainable historically
may trigger independent reaction
has durable semantic value
```

---

# 14. DOMAIN_EVENT_OPTIONAL

Utiliser quand le fait est utile pour :

```text
observability
projection
consumer extension
```

mais n’est pas nécessaire pour préserver le modèle métier.

---

# 15. APPLICATION_EVENT_ONLY

Utiliser pour :

```text
use-case progression
internal orchestration
non-domain milestone
```

Exemple possible :

```text
ImportBatchNormalized
```

---

# 16. INTEGRATION_EVENT_ONLY

Utiliser quand un message externe existe sans nécessiter un événement interne de domaine distinct.

Cas rare, à justifier.

---

# 17. AUDIT_ONLY

Utiliser quand il faut conserver :

```text
actor
operation
before/after metadata
```

sans créer de fait métier réutilisable.

---

# 18. OPERATIONAL_ONLY

Utiliser pour :

```text
retry
lease
dispatch
health
timeout
worker failure
```

---

# 19. NO_EVENT

Choix par défaut pour :

```text
Value Objects
pure computations
read-model construction
internal helper transitions
derived state
```

---

# 20. Canonical decision tree

```text
Did a meaningful business fact happen?
        │
        ├── NO → NO_EVENT
        │
        └── YES
              ↓
Does it belong to the domain model?
        │
        ├── NO → APPLICATION / OPERATIONAL / AUDIT
        │
        └── YES
              ↓
Is it durable and independently meaningful?
        │
        ├── NO → optional / audit-only
        │
        └── YES
              ↓
DOMAIN_EVENT_REQUIRED
```

---

# 21. Naming rule

Domain Events sont nommés au passé.

Préférer :

```text
JournalEntryPosted
PeriodClosed
SettlementAllocated
PolicySetActivated
ReportSnapshotPublished
```

Éviter :

```text
PostJournalEntry
ClosePeriod
AllocateSettlement
PublishReport
```

---

# 22. Event name semantics

Le nom doit exprimer :

```text
business fact
```

et non :

```text
technical action
```

---

# 23. Aggregate identity

Chaque Domain Event doit pouvoir identifier :

```text
aggregate_type
aggregate_id
```

et, si pertinent :

```text
accounting_entity_id
```

---

# 24. Entity scope

Pour les événements comptables :

```text
entity scope
```

doit être explicite ou dérivable sans ambiguïté.

---

# 25. Event time

`occurred_at` représente :

```text
business occurrence time
```

pas nécessairement :

```text
dispatch time
```

---

# 26. Correlation

`correlation_id` relie :

```text
a business request
or workflow
```

à plusieurs événements.

---

# 27. Causation

`causation_id` relie :

```text
this event
```

à :

```text
the event/command that caused it
```

selon la spec `25`.

---

# 28. Event schema version

Chaque event stable doit porter :

```text
event_schema_version
```

ou un mécanisme équivalent dans l’envelope.

---

# 29. Payload rule

Le payload doit contenir :

```text
minimum meaningful business facts
```

et non une sérialisation complète de l’aggregate.

---

# 30. No aggregate dumping

Interdit par défaut :

```text
payload = aggregate.__dict__
```

---

# 31. Payload immutability

Le payload doit être :

```text
deeply immutable
or canonically serialized
```

avant persistence/publication.

---

# 32. Event identity

Un Domain Event doit avoir :

```text
event_id
```

stable et unique.

---

# 33. Emission rule

L’event est produit seulement après :

```text
transition guards pass
new business state determined
```

---

# 34. Event is a fact, not a promise

Éviter :

```text
JournalEntryWillBePosted
```

comme Domain Event.

Préférer :

```text
JournalEntryPosted
```

après succès métier.

---

# 35. Transactional rule

Pour une mutation comptable critique :

```text
state persistence
+
DomainEvent persistence/outbox intent
+
audit evidence
```

doivent partager une boundary transactionnelle cohérente.

---

# 36. No ghost event

Interdit :

```text
event published
but accounting state rolled back
```

---

# 37. No silent business transition

Pour les transitions critiques couvertes par REQUIRED :

```text
business state changed
but event missing
```

doit être détectable par tests.

---

# 38. Event collection pattern

PyAccountingKit peut produire conceptuellement :

```text
TransitionResult(
    state,
    domain_events
)
```

plutôt qu’une queue mutable cachée dans tous les aggregates.

---

# 39. Aggregate event queue

Pattern :

```text
aggregate._events
pull_events()
```

n’est pas interdit.

Mais il n’est pas choisi par défaut.

---

# 40. Preferred direction

Étant donné les objets immutables de PyAccountingKit :

```text
domain operation
    ↓
new immutable state
+
explicit events
```

est préférable lorsque raisonnable.

---

# 41. Application mapping

L’application orchestre :

```text
DomainEvent
    ├──→ AuditEvent
    ├──→ OutboxRecord
    ├──→ Projection update
    └──→ IntegrationEvent
```

selon le contrat.

---

# 42. Domain must not know Outbox

Le domaine ne dépend pas de :

```text
OutboxRecord
broker
Kafka
RabbitMQ
database table
```

---

# 43. Domain must not know Audit storage

Le domaine peut exprimer un fait métier.

L’application/infrastructure décide :

```text
how audit is stored
```

---

# 44. JournalEntry coverage

Objet :

```text
JournalEntry
```

Couverture cible :

```text
JournalEntryValidated
JournalEntryPosted
JournalEntryReversed
```

---

# 45. JournalEntryValidated

Classification :

```text
DOMAIN_EVENT_OPTIONAL
```

Justification :

```text
meaningful lifecycle milestone
but may remain local if no consumer requires it
```

---

# 46. JournalEntryPosted

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

Justification :

```text
accounting effect becomes authoritative
historical boundary
downstream ledger/reporting relevance
```

---

# 47. JournalEntryReversed

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

Justification :

```text
economic correction fact
original + reversal relationship
downstream balance impact
```

---

# 48. JournalLine events

Par défaut :

```text
NO_EVENT
```

Éviter :

```text
JournalLineAdded
JournalLineChanged
```

comme événements de domaine publics.

---

# 49. AccountingPeriod coverage

Candidats :

```text
PeriodReviewStarted
PeriodLocked
PeriodClosingStarted
PeriodClosed
PeriodReopened
```

---

# 50. PeriodClosed

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 51. PeriodClosingStarted

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

si le début de clôture change réellement :

```text
posting eligibility
or concurrency semantics
```

Sinon :

```text
APPLICATION_EVENT_ONLY
```

---

# 52. PeriodLocked

Classification :

```text
DOMAIN_EVENT_OPTIONAL
```

selon consommation.

---

# 53. PeriodReopened

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

Justification :

```text
downstream snapshots may become stale
replay/provenance implications
```

---

# 54. ClosingRun coverage

Candidats :

```text
ClosingRequested
ClosingBlocked
ClosingStarted
ClosingFailed
ClosingSealed
```

---

# 55. ClosingSealed

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 56. ClosingBlocked

Classification :

```text
DOMAIN_EVENT_OPTIONAL
```

ou :

```text
APPLICATION_EVENT_ONLY
```

si aucun état métier durable n’est créé.

---

# 57. ClosingFailed

Classification dépend de la cause.

```text
business failure
→ Domain/Application event candidate

technical failure
→ Operational event
```

---

# 58. AccountingImportBatch coverage

Le batch possède beaucoup de transitions.

Ne pas produire automatiquement :

```text
one Domain Event per status
```

---

# 59. ImportBatchCreated

Classification :

```text
APPLICATION_EVENT_ONLY
```

par défaut.

---

# 60. ImportBatchParsed

Classification :

```text
APPLICATION_EVENT_ONLY
```

---

# 61. ImportBatchValidated

Classification :

```text
DOMAIN_EVENT_OPTIONAL
```

si validation possède une valeur métier durable.

---

# 62. ImportBatchCompleted

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

si le batch représente :

```text
committed accounting import outcome
```

---

# 63. ImportBatchFailed

Classification :

```text
APPLICATION_EVENT_ONLY
```

ou :

```textOPERATIONAL_ONLY
```

selon cause.

---

# 64. ImportBatchCancelled

Classification :

```text
DOMAIN_EVENT_OPTIONAL
```

si l’annulation est une décision métier durable.

---

# 65. Settlement coverage

Candidats :

```text
SettlementCreated
SettlementPosted
SettlementAllocated
SettlementFullyAllocated
SettlementAllocationRestored
SettlementReversed
```

---

# 66. SettlementPosted

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 67. SettlementAllocated

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

si l’allocation est un fait métier exploitable indépendamment.

---

# 68. SettlementFullyAllocated

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

si ce milestone déclenche :

```text
closing of open receivable/payable
downstream status
notification
```

Sinon `SettlementAllocated` peut suffire avec solde zéro.

---

# 69. SettlementAllocationRestored

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

si la restauration annule une allocation historique.

---

# 70. SettlementReversed

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 71. DueItem coverage

`DueItem` a un lifecycle dérivé.

Par défaut :

```text
no direct state-change event
```

---

# 72. DueItemSettled

Peut être :

```text
DOMAIN_EVENT_OPTIONAL
```

si un consumer métier en a besoin.

Sinon l’événement de l’aggregate parent suffit.

---

# 73. SettlementAllocation coverage

Candidats :

```text
SettlementAllocationCreated
SettlementAllocationReversed
```

---

# 74. AllocationCreated

Classification :

```text
DOMAIN_EVENT_OPTIONAL
```

si `SettlementAllocated` porte déjà le fait métier.

Éviter les doublons sémantiques.

---

# 75. AllocationReversed

Même règle :

```text
choose one canonical semantic level
```

---

# 76. PolicySet coverage

Candidats :

```text
PolicySetActivated
PolicySetSuperseded
PolicySetRetired
```

---

# 77. PolicySetActivated

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

si l’activation affecte :

```text
future accounting decisions
```

---

# 78. PolicySetSuperseded

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 79. PolicySetRetired

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 80. CompanyChart coverage

Candidats :

```text
CompanyChartVersionPlanned
CompanyChartVersionActivated
CompanyChartVersionSuperseded
CompanyChartVersionArchived
```

---

# 81. ChartVersionPlanned

Classification :

```text
DOMAIN_EVENT_OPTIONAL
```

---

# 82. ChartVersionActivated

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 83. ChartVersionSuperseded

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 84. RegulatoryAccountBinding coverage

Candidats :

```text
RegulatoryBindingCandidateCreated
RegulatoryBindingActivated
RegulatoryBindingRetired
```

---

# 85. CandidateCreated

Classification :

```text
DOMAIN_EVENT_OPTIONAL
```

---

# 86. BindingActivated

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

car :

```text
mapping becomes executable
```

---

# 87. BindingRetired

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 88. StatementMappingSet coverage

Candidats :

```text
StatementMappingSetValidated
StatementMappingSetActivated
StatementMappingSetSuperseded
StatementMappingSetArchived
```

---

# 89. MappingSetActivated

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 90. MappingSetSuperseded

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 91. RegulatoryMappingSet coverage

Même logique que StatementMappingSet.

Les événements d’activation/supersession sont :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 92. RegulatoryReportingProfile coverage

Candidats :

```text
RegulatoryProfileValidated
RegulatoryProfileActivated
RegulatoryProfileSuperseded
RegulatoryProfileArchived
```

---

# 93. RegulatoryProfileActivated

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 94. ReportSnapshot coverage

Candidats :

```text
ReportSnapshotCreated
ReportSnapshotValidated
ReportSnapshotPublished
ReportSnapshotSuperseded
ReportSnapshotBecameStale
```

---

# 95. ReportSnapshotCreated

Classification :

```text
NO_EVENT
```

ou :

```text
APPLICATION_EVENT_ONLY
```

par défaut.

---

# 96. ReportSnapshotValidated

Classification :

```text
DOMAIN_EVENT_OPTIONAL
```

---

# 97. ReportSnapshotPublished

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 98. ReportSnapshotSuperseded

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 99. ReportSnapshotBecameStale

Attention.

`STALE` peut être :

```text
derived from source checksum
```

Donc événement seulement si :

```text
staleness becomes a durable business fact
```

Sinon :

```text
NO_EVENT
```

---

# 100. FinancialIndicatorDefinition coverage

Candidats :

```text
IndicatorDefinitionValidated
IndicatorDefinitionActivated
IndicatorDefinitionDeprecated
IndicatorDefinitionSuperseded
```

---

# 101. IndicatorDefinitionActivated

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

si l’activation change les calculs autoritatifs.

---

# 102. FinancialIndicatorValue coverage

Par défaut :

```text
NO_EVENT
```

pour :

```text
IndicatorCalculated
RatioCalculated
MetricCalculated
```

---

# 103. Computation events

Si besoin d’observabilité :

```text
APPLICATION_EVENT_ONLY
```

---

# 104. Diagnostic coverage

`FinancialDiagnostic` est un résultat.

Par défaut :

```text
NO_EVENT
```

---

# 105. MatchingCandidate coverage

Candidate calculation :

```text
NO_EVENT
```

ou :

```text
APPLICATION_EVENT_ONLY
```

---

# 106. AccountingMatch coverage

Candidats :

```text
AccountingMatchValidated
AccountingMatchReversed
```

---

# 107. MatchValidated

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

si le match devient une preuve métier autoritative.

---

# 108. ReconciliationRun coverage future

Candidats :

```text
ReconciliationStarted
ReconciliationCompleted
ReconciliationBlocked
ReconciliationFailed
ReconciliationSuperseded
```

---

# 109. ReconciliationCompleted

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 110. ConsolidationRun coverage future

Candidats :

```text
ConsolidationStarted
PackageAccepted
EliminationPosted
ConsolidationValidated
ConsolidationPublished
ConsolidationReopened
```

---

# 111. ConsolidationPublished

Classification :

```text
DOMAIN_EVENT_REQUIRED
```

---

# 112. ExternalEffect coverage future

`ExternalEffect` appartient surtout à `LOT-44`.

Candidats :

```text
ExternalEffectStarted
ExternalEffectSucceeded
ExternalEffectBecameUncertain
ExternalEffectReconciled
ExternalEffectFailedFinal
```

---

# 113. ExternalEffectBecameUncertain

Classification :

```text
APPLICATION / OPERATIONAL EVENT
```

par défaut.

Il ne s’agit pas forcément d’un Domain Event comptable.

---

# 114. ExternalEffectSucceeded

Peut devenir :

```text
INTEGRATION_EVENT
```

selon la frontière concernée.

---

# 115. Event granularity rule

Préférer :

```text
one meaningful event
```

plutôt que :

```text
five technical micro-events
```

pour une seule transition métier.

---

# 116. Event duplication rule

Éviter simultanément :

```text
SettlementAllocated
DueItemOpenAmountChanged
AllocationCreated
SettlementStatusChanged
```

si tous décrivent le même fait.

---

# 117. Canonical semantic owner

Pour chaque fait, définir :

```text
one canonical event owner
```

---

# 118. Event ownership

L’événement appartient au bounded context qui possède le fait.

Exemple :

```text
JournalEntryPosted
→ Ledger/Journals domain
```

pas :

```text
Reporting
```

---

# 119. Event propagation

Un autre context peut produire ensuite :

```text
its own event
```

à partir de sa réaction.

---

# 120. No cross-context event mutation

Un consumer ne modifie jamais l’événement source.

---

# 121. Event ordering

L’ordering global n’est pas garanti par défaut.

Lorsque nécessaire, utiliser :

```text
aggregate identity
sequence/revision
occurred_at
```

ou stratégie définie dans la spec `25`.

---

# 122. Per-aggregate ordering

Pour certains aggregates :

```text
JournalEntry
Settlement
Period
```

un ordre cohérent par aggregate peut être nécessaire.

---

# 123. Event idempotency

Un même Domain Event ne doit pas produire deux effets aval irréversibles.

Consumers doivent être :

```text
idempotent
```

ou protégés.

---

# 124. At-least-once assumption

Avec outbox :

```text
duplicate delivery
```

doit être considérée possible.

---

# 125. Exactly-once claim

Interdit comme promesse globale sans preuve.

---

# 126. Event persistence

Options :

```text
transactional outbox record
event store
audit projection
```

PyAccountingKit cible actuellement :

```text
transactional outbox
```

pas Event Store complet.

---

# 127. Domain Event retention

Un Domain Event n’est pas nécessairement :

```text
forever retained as source of truth
```

La policy de retention dépend de :

```text
audit
integration
replay
regulatory needs
```

---

# 128. Event replay

Rejouer des Domain Events n’implique pas reconstruire l’aggregate.

Replay peut servir à :

```text
rebuild projection
republish integration
verify causality
```

---

# 129. Event schema evolution

Règles :

```text
additive changes preferred
breaking change => new schema version
old events remain interpretable where required
```

---

# 130. No silent payload reinterpretation

Une ancienne version d’event ne doit pas changer de signification.

---

# 131. Event deprecation

Un event peut être :

```text
deprecated
```

mais les consumers historiques doivent disposer d’une migration ou compatibilité explicite.

---

# 132. Audit mapping

Exemple :

```text
JournalEntryPosted
    ↓
AuditEvent(
    actor,
    entity,
    timestamp,
    entry id,
    amounts
)
```

---

# 133. Audit is richer on actor

Le Domain Event ne doit pas nécessairement porter :

```text
full user identity
IP
user agent
authorization details
```

Ces données appartiennent à l’audit/application context si nécessaire.

---

# 134. Outbox mapping

Exemple :

```text
JournalEntryPosted
    ↓
OutboxRecord
```

avec :

```text
event_id
event_type
schema version
entity
payload
idempotency key
```

selon la spec `25/30`.

---

# 135. Integration mapping

Un Domain Event interne peut devenir :

```text
AccountingEntryPostedV1
```

comme IntegrationEvent plus stable et moins couplé.

---

# 136. Internal vs external event names

Exemple :

```text
Domain:
JournalEntryPosted

Integration:
AccountingEntryPostedV1
```

Ils ne doivent pas être supposés identiques.

---

# 137. Event security

Ne jamais inclure par défaut :

```text
credentials
secrets
raw bank details
full personal data
sensitive source payloads
```

---

# 138. Event minimization

Le payload suit :

```text
minimum necessary
```

---

# 139. PII rule

Si PII nécessaire :

```text
explicitly classified
documented
protected
```

---

# 140. Event and GDPR

Les events ne doivent pas devenir une archive incontrôlée de données personnelles.

---
# 141. Event failure rule

L’échec d’émission après commit local doit être géré par :

```text
outbox
retry
recovery
```

pas par rollback impossible du fait métier déjà commis.

---

# 142. Transactional outbox rationale

```text
business commit
+
outbox intent
```

doivent être atomiques.

---

# 143. Outbox != Domain Event

`OutboxRecord` est :

```text
delivery representation
```

pas :

```text
the business fact itself
```

---

# 144. Audit finding F14 alignment

Les payloads audit/outbox doivent être :

```text
deeply immutable
```

pour éviter la corruption a posteriori.

---

# 145. A03 alignment

La trace :

```text
proposal
→ posted entry
```

doit être persistée durablement dans la même boundary applicable.

Un event peut aider la traçabilité, mais ne remplace pas :

```text
durable relation
```

si cette relation est une donnée métier requise.

---

# 146. F11 alignment

L’idempotency doit protéger :

```text
same semantic command
```

pas seulement :

```text
same string key
```

Les events aval doivent hériter d’une identité stable.

---

# 147. F22 alignment

Un :

```text
ReportSnapshotPublished
```

ne peut être émis que si :

```text
publication transition was legal
```

---

# 148. Event coverage matrix

Artifact recommandé :

```text
DOMAIN_EVENT_COVERAGE_MATRIX.md
```

Colonnes :

```text
context
object
business fact
classification
canonical event name
aggregate id
entity scope
audit mapping
outbox mapping
integration mapping
schema version
qualification status
```

---

# 149. Coverage qualification statuses

```text
NOT_APPLICABLE
IDENTIFIED
MODELED
IMPLEMENTED
QUALIFIED
DEPRECATED
```

---

# 150. Event maturity model

```text
EV0 — NO_COVERAGE
EV1 — EVENT_IDENTIFIED
EV2 — EVENT_MODELED
EV3 — AUDIT_OUTBOX_MAPPED
EV4 — CROSS_ADAPTER_QUALIFIED
EV5 — VERSIONED_INTEGRATION_CONTRACT
```

---

# 151. Initial event priority

P0 :

```text
JournalEntryPosted
JournalEntryReversed
PeriodClosed
PeriodReopened
ClosingSealed
SettlementPosted
SettlementAllocated
SettlementReversed
ReportSnapshotPublished
PolicySetActivated
CompanyChartVersionActivated
```

---

# 152. P1 event candidates

```text
JournalEntryValidated
PeriodLocked
ImportBatchCompleted
MappingSetActivated
RegulatoryProfileActivated
MatchValidated
```

---

# 153. Low-priority / optional

```text
ImportBatchParsed
IndicatorCalculated
DiagnosticGenerated
MappingCandidateCreated
ChartVersionPlanned
```

---

# 154. Event test taxonomy

```text
UNIT-EVENT
CONTRACT-EVENT
GOLD-EVENT
REPLAY-EVENT
OUTBOX-EVENT
IDEMPOTENCY-EVENT
```

---

# 155. Unit event tests

Vérifier :

```text
meaningful fact emitted
correct event type
correct aggregate id
correct entity scope
minimal payload
```

---

# 156. No-event tests

Il faut aussi tester :

```text
invalid transition
→ no event

rolled-back transaction
→ no visible outbox event

pure calculation
→ no domain event
```

---

# 157. Golden event tests

Exemples :

```text
GOLD-EVT-ENTRY-001
GOLD-EVT-CLOSE-001
GOLD-EVT-SETTLEMENT-001
GOLD-EVT-REPORT-001
```

---

# 158. Cross-adapter event parity

Même business scenario :

```text
InMemory
Django/PostgreSQL
SQLAlchemy/PostgreSQL
```

doit produire :

```text
same semantic event sequence
```

hors metadata infrastructure-specific.

---

# 159. Event ordering tests

Pour aggregate critique :

```text
validate
post
reverse
```

doit donner un ordre cohérent si les trois events sont activés.

---

# 160. Duplicate delivery tests

Outbox consumers doivent tolérer :

```text
same event delivered twice
```

---

# 161. Event rollback tests

Si la transaction échoue :

```text
business state
audit
outbox
```

ne doivent pas diverger.

---

# 162. Event mapping rule

Un Domain Event peut mapper vers :

```text
0..1 AuditEvent
0..1 OutboxRecord
0..n IntegrationEvents
```

selon le use case.

---

# 163. Not every Domain Event must leave process

Un Domain Event peut rester :

```text
internal only
```

---

# 164. Not every AuditEvent needs DomainEvent

Exemple :

```text
user attempted forbidden action
```

peut être :

```text
AUDIT_ONLY
```

---

# 165. Not every OutboxRecord is DomainEvent

Exemple :

```text
technical artifact ready
```

peut être :

```text
APPLICATION/INTEGRATION
```

---

# 166. Event emission authority

Le domaine détermine :

```text
business fact occurred
```

L’application détermine :

```text
how it is persisted/routed
```

---

# 167. No ORM event generation

Interdit :

```text
post_save hook
creates DomainEvent
```

sans preuve que la transition métier correspondante a été validée.

---

# 168. No generic status changed event

Éviter :

```text
ObjectStatusChanged
```

comme événement canonique principal.

Préférer :

```text
PeriodClosed
PolicySetActivated
ReportSnapshotPublished
```

---

# 169. Exception

Un événement générique peut exister pour :

```text
telemetry
internal framework tooling
```

mais pas comme contrat métier principal.

---

# 170. Event payload references

Préférer :

```text
ids
version refs
checksums
semantic values
```

à :

```text
full nested object graphs
```

---

# 171. Event and reproducibility

LOT-41 pourra utiliser :

```text
event ids
manifest ids
snapshot ids
checksums
```

pour améliorer la provenance.

---

# 172. Event and state machine

`36` définit :

```text
what can happen
```

`37` définit :

```text
what is worth announcing
```

---

# 173. Event and lifecycle mapping

`38` reliera :

```text
object
state
transition
business fact
DomainEvent
AuditEvent
OutboxRecord
```

---

# 174. Event and LOT-40

LOT-40 implémentera notamment :

```text
DomainEvent
DomainEventEnvelope
EventId
CorrelationId
CausationId
schema version
event registry
mapping infrastructure
```

---

# 175. Event and LOT-42

LOT-42 qualifiera :

```text
event sequence
cross-adapter parity
race behavior
replay behavior
```

---

# 176. Event and LOT-44

LOT-44 ajoutera :

```text
outbox lifecycle
delivery uncertainty
recovery
reconciliation before retry
```

---

# 177. Architecture fitness functions

Propositions :

```text
AFF-EVT-001
Value Objects MUST NOT emit Domain Events by default.

AFF-EVT-002
Critical business transitions classified REQUIRED MUST emit exactly the canonical fact.

AFF-EVT-003
Adapters MUST NOT invent Domain Events.

AFF-EVT-004
Domain code MUST NOT depend on OutboxRecord.

AFF-EVT-005
DomainEvent payloads MUST be deeply immutable or canonically serialized.

AFF-EVT-006
Rolled-back transactions MUST NOT expose committed outbox messages.

AFF-EVT-007
Domain Events MUST use past-tense business names.

AFF-EVT-008
Generic ObjectStatusChanged MUST NOT replace canonical business events.

AFF-EVT-009
Required event sequences MUST be cross-adapter equivalent.

AFF-EVT-010
Event schema changes MUST be versioned.
```

---

# 178. ADR proposals

| ADR | Décision |
|---|---|
| ADR-EVT-001 | Tous les objets métier n’émettent pas de Domain Events |
| ADR-EVT-002 | Les Domain Events représentent des faits métier au passé |
| ADR-EVT-003 | DomainEvent != AuditEvent |
| ADR-EVT-004 | DomainEvent != IntegrationEvent |
| ADR-EVT-005 | DomainEvent != OperationalEvent |
| ADR-EVT-006 | DomainEvent n’implique pas Event Sourcing |
| ADR-EVT-007 | Les Value Objects n’émettent pas d’events par défaut |
| ADR-EVT-008 | Le domaine ne dépend pas de l’outbox |
| ADR-EVT-009 | Les payloads restent minimaux |
| ADR-EVT-010 | Les payloads sont immuables |
| ADR-EVT-011 | Les events critiques sont transactionnellement cohérents avec l’état |
| ADR-EVT-012 | Un rollback ne publie aucun event visible |
| ADR-EVT-013 | Les consumers aval sont idempotents |
| ADR-EVT-014 | At-least-once est l’hypothèse de livraison |
| ADR-EVT-015 | Le semantic owner de l’event est unique |
| ADR-EVT-016 | Éviter les events redondants pour un même fait |
| ADR-EVT-017 | Les event schemas sont versionnés |
| ADR-EVT-018 | Les Domain Events peuvent rester internes |
| ADR-EVT-019 | L’event coverage est qualifié cross-adapter |
| ADR-EVT-020 | Le mapping transition/event est documenté dans la spec 38 |

---

# 179. Definition of Done — Event Coverage

```text
[ ] major lifecycle facts inventoried
[ ] each fact classified
[ ] canonical event names defined
[ ] semantic owner defined
[ ] aggregate identity defined
[ ] entity scope defined
[ ] payload boundary defined
[ ] audit mapping decided
[ ] outbox mapping decided
[ ] integration mapping decided
[ ] schema version strategy defined
```

---

# 180. Definition of Done — Required Domain Event

```text
[ ] business fact is stable
[ ] emitted only after valid domain transition
[ ] immutable payload
[ ] aggregate identity present
[ ] entity scope present where applicable
[ ] correlation/causation supported
[ ] transaction semantics defined
[ ] rollback behavior tested
[ ] duplicate delivery behavior tested
[ ] cross-adapter parity tested
```

---

# 181. Non-goals

Cette spec ne demande pas :

```text
event sourcing
Kafka dependency
broker mandatory
global event bus
event for every object
event for every status
event for every calculation
full aggregate serialization
```

---

# 182. Recommended next specification

La suite logique est :

```text
38_PYACCOUNTINGKIT_LIFECYCLE_STATE_MACHINE_EVENT_MAPPING.md
```

Elle produira la matrice finale :

```text
Business Object
    ↓
Lifecycle
    ↓
State Machine
    ↓
Transition
    ↓
Meaningful Fact
    ↓
Domain Event?
    ↓
Audit?
    ↓
Outbox?
    ↓
Integration?
```

---

# 183. Canonical architecture chain

```text
35
BUSINESS LIFECYCLES
    ↓
36
STATE MACHINES
    ↓
37
DOMAIN EVENT COVERAGE
    ↓
38
LIFECYCLE ↔ STATE ↔ EVENT MAPPING
    ↓
25
EVENT ENVELOPE / CAUSALITY
    ↓
LOT-40
IMPLEMENTATION
```

---

# 184. Final rule

La règle finale de PyAccountingKit devient :

> **Un Domain Event n’est émis que pour un fait métier suffisamment significatif pour mériter une identité, une sémantique stable et une traçabilité indépendante. Les transitions techniques, les calculs purs, les Value Objects et les changements dérivés restent silencieux par défaut.**

Et surtout :

```text
STATE MACHINE
decides what may happen

DOMAIN EVENT
describes what meaningful fact did happen

AUDIT
records who/when/why

OUTBOX
delivers the fact safely

INTEGRATION EVENT
exposes a stable external contract
```