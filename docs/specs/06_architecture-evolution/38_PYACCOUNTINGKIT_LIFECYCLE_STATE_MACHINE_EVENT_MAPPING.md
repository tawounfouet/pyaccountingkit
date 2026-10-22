# 38_PYACCOUNTINGKIT_LIFECYCLE_STATE_MACHINE_EVENT_MAPPING.md

# PyAccountingKit — Lifecycle ↔ State Machine ↔ Event Mapping

> **Projet** : PyAccountingKit  
> **Document** : `38_PYACCOUNTINGKIT_LIFECYCLE_STATE_MACHINE_EVENT_MAPPING.md`  
> **Statut** : Spécification transverse — matrice de mapping lifecycle/state/event  
> **Date** : 22 octobre 2026  
> **Documents sources** :
> - `35_PYACCOUNTINGKIT_BUSINESS_LIFECYCLES_ARCHITECTURE.md`
> - `36_PYACCOUNTINGKIT_STATE_MACHINES_AND_TRANSITION_RULES.md`
> - `37_PYACCOUNTINGKIT_DOMAIN_EVENTS_COVERAGE_AND_EMISSION_RULES.md`
> - `25_PYACCOUNTINGKIT_DOMAIN_EVENTS_CAUSALITY_AND_EVENT_ENVELOPE.md`
> **Baseline runtime observée** : PyAccountingKit `0.7.0rc1`
> **Portée** :
> - mapping canonique lifecycle → transition → event ;
> - décision DomainEvent / Audit / Outbox / Integration ;
> - couverture des objets métier principaux ;
> - règles de cohérence et qualification ;
> - préparation directe de `LOT-40`.  
> **Hors scope volontaire** :
> - implémentation runtime ;
> - choix de broker ;
> - Event Sourcing ;
> - orchestration distribuée ;
> - sérialisation finale des IntegrationEvents.

---

# 1. Objet

Cette spécification répond à la question finale de la série `35 → 38` :

> **Pour chaque objet métier PyAccountingKit, comment relier son lifecycle, ses transitions légales, les faits métier significatifs et leur exposition éventuelle sous forme de DomainEvent, AuditEvent, OutboxRecord ou IntegrationEvent ?**

---

# 2. Chaîne canonique

```text
BUSINESS OBJECT
      ↓
LIFECYCLE
      ↓
STATE MACHINE
      ↓
LEGAL TRANSITION
      ↓
MEANINGFUL BUSINESS FACT?
      ↓
DOMAIN EVENT?
      ↓
AUDIT?
      ↓
OUTBOX?
      ↓
INTEGRATION EVENT?
```

---

# 3. Principe cardinal

La relation n’est jamais :

```text
state changed
=
event required
```

La relation correcte est :

```text
legal transition
+
meaningful business fact
=
event candidate
```

---

# 4. Deux règles fondamentales

```text
Transition without DomainEvent
is valid

DomainEvent without status change
is also valid
```

---

# 5. Transition sans DomainEvent

Exemple :

```text
ImportBatch
PARSED → NORMALIZED
```

Peut rester :

```text
APPLICATION_EVENT_ONLY
```

ou :

```text
NO_EVENT
```

---

# 6. DomainEvent sans changement de state

Exemple :

```text
Settlement
PARTIALLY_ALLOCATED
    ↓ allocate()
PARTIALLY_ALLOCATED
```

mais :

```text
SettlementAllocated
```

reste un fait métier pertinent.

---

# 7. Matrice de décision

Pour chaque transition/fait :

```text
1. Is transition legal?
2. Is the fact business-significant?
3. Does another domain/process care?
4. Must it be historically explainable?
5. Is it safe/necessary to expose?
```

---

# 8. Classification finale des outputs

Chaque ligne de mapping peut produire :

```text
DOMAIN_EVENT_REQUIRED
DOMAIN_EVENT_OPTIONAL
APPLICATION_EVENT_ONLY
AUDIT_ONLY
OPERATIONAL_ONLY
NO_EVENT
```

et séparément :

```text
AUDIT_MAPPING
OUTBOX_MAPPING
INTEGRATION_MAPPING
```

---

# 9. Event pipeline canonique

```text
Command
   ↓
Domain Guard
   ↓
Legal Transition
   ↓
New Immutable State
   ↓
Domain Event(s)
   ↓
Application Layer
   ├──→ AuditEvent
   ├──→ OutboxRecord
   └──→ IntegrationEvent
```

---

# 10. Règle de propriété

Le bounded context propriétaire de la transition possède :

```text
canonical event semantics
```

Les consumers :

```text
do not redefine source semantics
```

---

# 11. JournalEntry — mapping canonique

Lifecycle :

```text
DRAFT
  ↓
VALIDATED
  ↓
POSTED
  ↓
REVERSED
```

---

# 12. JournalEntry mapping table

| From | Command | To | Meaningful fact | DomainEvent | Audit | Outbox | Integration |
|---|---|---|---|---|---|---|---|
| DRAFT | validate | VALIDATED | entry validated | optional | yes | optional | optional |
| VALIDATED | post | POSTED | accounting entry posted | required | yes | yes | yes |
| POSTED | reverse | REVERSED | posted entry reversed | required | yes | yes | yes |

---

# 13. JournalEntryValidated

```text
DomainEvent:
JournalEntryValidated
```

Classification :

```text
OPTIONAL
```

---

# 14. JournalEntryPosted

```text
DomainEvent:
JournalEntryPosted
```

Classification :

```text
REQUIRED
```

Audit :

```text
YES
```

Outbox :

```text
YES
```

Integration :

```text
YES
```

---

# 15. JournalEntryReversed

```text
DomainEvent:
JournalEntryReversed
```

Classification :

```text
REQUIRED
```

---

# 16. AccountingPeriod — mapping canonique

Lifecycle :

```text
OPEN
REVIEW
LOCKED
CLOSING
CLOSED
```

---

# 17. AccountingPeriod mapping

| From | Command | To | Event | DomainEvent | Audit | Outbox |
|---|---|---|---|---|---|---|
| OPEN | start_review | REVIEW | PeriodReviewStarted | optional | yes | optional |
| OPEN | lock | LOCKED | PeriodLocked | optional | yes | optional |
| OPEN/REVIEW | start_closing | CLOSING | PeriodClosingStarted | required if posting semantics change | yes | yes |
| CLOSING | close | CLOSED | PeriodClosed | required | yes | yes |
| CLOSED | reopen | OPEN/REVIEW | PeriodReopened | required | yes | yes |

---

# 18. PeriodClosed significance

```text
PeriodClosed
```

doit être considéré comme :

```text
major business boundary
```

---

# 19. PeriodReopened significance

```text
PeriodReopened
```

est critique car il peut rendre :

```text
snapshots stale
reports outdated
downstream manifests invalid
```

---

# 20. ClosingRun — mapping canonique

Lifecycle cible :

```text
REQUESTED
VALIDATING
BLOCKED
READY
CLOSING
FAILED
SEALED
```

---

# 21. ClosingRun mapping

| From | Command | To | Event | Classification |
|---|---|---|---|---|
| REQUESTED | validate | VALIDATING | ClosingValidationStarted | application-only |
| VALIDATING | controls_fail | BLOCKED | ClosingBlocked | optional |
| VALIDATING | controls_pass | READY | ClosingReady | application-only |
| READY | execute | CLOSING | ClosingStarted | required/optional depending semantics |
| CLOSING | failure | FAILED | ClosingFailed | app/operational |
| CLOSING | seal | SEALED | ClosingSealed | required |

---

# 22. ClosingSealed

```text
DomainEvent:
ClosingSealed
```

Classification :

```text
REQUIRED
```

Audit :

```text
YES
```

Outbox :

```text
YES
```

---

# 23. AccountingImportBatch — mapping canonique

Lifecycle :

```text
CREATED
ACQUIRED
PARSED
NORMALIZED
MAPPED
VALIDATED
READY
IMPORTING
COMPLETED
COMPLETED_WITH_WARNINGS
FAILED
CANCELLED
```

---

# 24. Import mapping principle

Ne pas produire :

```text
one DomainEvent per technical stage
```

---

# 25. Import mapping

| Transition | Fact | Classification |
|---|---|---|
| CREATED → ACQUIRED | artifact acquired | application-only |
| ACQUIRED → PARSED | parsed | application-only |
| PARSED → NORMALIZED | normalized | application-only |
| NORMALIZED → MAPPED | mapped | application-only |
| MAPPED → VALIDATED | validated | optional |
| VALIDATED → READY | ready | application-only |
| READY → IMPORTING | started | application-only |
| IMPORTING → COMPLETED | accounting import committed | required |
| IMPORTING → COMPLETED_WITH_WARNINGS | accounting import committed with warnings | required |
| any cancellable → CANCELLED | import cancelled | optional |
| IMPORTING → FAILED | import failed | app/operational |

---

# 26. ImportBatchCompleted

```text
DomainEvent:
ImportBatchCompleted
```

Classification :

```text
REQUIRED
```

si :

```text
accounting effects committed
```

---

# 27. Settlement — double machine

Operational :

```text
OPEN
PARTIALLY_ALLOCATED
FULLY_ALLOCATED
REVERSED
```

Accounting :

```text
PENDING
POSTED
REVERSED
```

---

# 28. Settlement mapping principle

Le mapping doit considérer :

```text
both state dimensions
```

---

# 29. SettlementPosted

Transition :

```text
Accounting
PENDING → POSTED
```

Event :

```text
SettlementPosted
```

Classification :

```text
REQUIRED
```

---

# 30. SettlementAllocated

Transition possible :

```text
OPEN → PARTIALLY_ALLOCATED
PARTIALLY_ALLOCATED → PARTIALLY_ALLOCATED
PARTIALLY_ALLOCATED → FULLY_ALLOCATED
```

Event :

```text
SettlementAllocated
```

Classification :

```text
REQUIRED
```

---

# 31. SettlementFullyAllocated

Event :

```text
SettlementFullyAllocated
```

Classification :

```text
OPTIONAL/REQUIRED
```

selon si le milestone a une valeur autonome.

---

# 32. SettlementReversed

Operational :

```text
* → REVERSED
```

Accounting :

```text
POSTED → REVERSED
```

Event :

```text
SettlementReversed
```

Classification :

```text
REQUIRED
```

---

# 33. SettlementAllocation

Lifecycle :

```text
ACTIVE → REVERSED
```

---

# 34. Allocation event duplication rule

Choisir entre :

```text
SettlementAllocated
```

et :

```text
SettlementAllocationCreated
```

comme fait canonique principal.

Éviter les deux si aucune valeur sémantique distincte.

---

# 35. DueItem — mapping

Lifecycle dérivé.

Transitions :

```text
allocate
restore
```

Par défaut :

```text
NO direct DomainEvent
```

---

# 36. DueItemSettled

Peut devenir :

```text
OPTIONAL
```

uniquement si le domaine consomme explicitement ce milestone.

---

# 37. PolicySet — mapping canonique

Lifecycle :

```text
DRAFT
ACTIVE
SUPERSEDED
RETIRED
```

---

# 38. PolicySet mapping

| Transition | DomainEvent | Classification |
|---|---|---|
| DRAFT → ACTIVE | PolicySetActivated | required |
| ACTIVE → SUPERSEDED | PolicySetSuperseded | required |
| ACTIVE → RETIRED | PolicySetRetired | required |

---

# 39. CompanyChartVersion — mapping canonique

Lifecycle :

```text
DRAFT
ACTIVE
SUPERSEDED
ARCHIVED
```

---

# 40. CompanyChartVersion mapping

| Transition | Event | Classification |
|---|---|---|
| plan draft | CompanyChartVersionPlanned | optional |
| DRAFT → ACTIVE | CompanyChartVersionActivated | required |
| ACTIVE → SUPERSEDED | CompanyChartVersionSuperseded | required |
| SUPERSEDED → ARCHIVED | CompanyChartVersionArchived | optional |

---

# 41. RegulatoryAccountBinding — mapping

Lifecycle :

```text
CANDIDATE
ACTIVE
RETIRED
```

---

# 42. Binding mapping

| Transition | Event | Classification |
|---|---|---|
| create candidate | RegulatoryBindingCandidateCreated | optional |
| CANDIDATE → ACTIVE | RegulatoryBindingActivated | required |
| ACTIVE → RETIRED | RegulatoryBindingRetired | required |

---

# 43. StatementMappingSet — mapping

Lifecycle :

```text
DRAFT
REVIEW_REQUIRED
VALIDATED
ACTIVE
SUPERSEDED
ARCHIVED
```

---

# 44. StatementMappingSet mapping

| Transition | Event | Classification |
|---|---|---|
| DRAFT → REVIEW_REQUIRED | StatementMappingReviewRequired | optional |
| DRAFT/REVIEW_REQUIRED → VALIDATED | StatementMappingSetValidated | optional |
| VALIDATED → ACTIVE | StatementMappingSetActivated | required |
| ACTIVE → SUPERSEDED | StatementMappingSetSuperseded | required |
| SUPERSEDED → ARCHIVED | StatementMappingSetArchived | optional |

---

# 45. RegulatoryMappingSet — mapping

Même structure que :

```text
StatementMappingSet
```

avec :

```text
RegulatoryMappingSetActivated
RegulatoryMappingSetSuperseded
```

comme REQUIRED.

---

# 46. RegulatoryReportingProfile — mapping

Lifecycle :

```text
DRAFT
REVIEW_REQUIRED
VALIDATED
ACTIVE
SUPERSEDED
ARCHIVED
```

---

# 47. RegulatoryProfile mapping

| Transition | Event | Classification |
|---|---|---|
| DRAFT → VALIDATED | RegulatoryProfileValidated | optional |
| VALIDATED → ACTIVE | RegulatoryProfileActivated | required |
| ACTIVE → SUPERSEDED | RegulatoryProfileSuperseded | required |
| SUPERSEDED → ARCHIVED | RegulatoryProfileArchived | optional |

---

# 48. ReportSnapshot — mapping canonique

Lifecycle :

```text
DRAFT
VALIDATED
PUBLISHED
SUPERSEDED
```

---

# 49. ReportSnapshot mapping

| Transition | Event | Classification | Audit | Outbox |
|---|---|---|---|---|
| create DRAFT | ReportSnapshotCreated | no/app-only | optional | no |
| DRAFT → VALIDATED | ReportSnapshotValidated | optional | yes | optional |
| VALIDATED → PUBLISHED | ReportSnapshotPublished | required | yes | yes |
| PUBLISHED → SUPERSEDED | ReportSnapshotSuperseded | required | yes | yes |

---

# 50. Report publication invariant

Interdit :

```text
DRAFT → PUBLISHED
```

Donc :

```text
ReportSnapshotPublished
```

ne peut jamais être produit depuis un DRAFT non validé.

---

# 51. ReportSnapshot stale mapping

`CURRENT/STALE` est généralement :

```text
derived
```

Donc :

```text
ReportSnapshotBecameStale
```

est :

```text
NO_EVENT
```

par défaut.

---

# 52. FinancialIndicatorDefinition — mapping

Lifecycle :

```text
DRAFT
VALIDATED
ACTIVE
DEPRECATED
SUPERSEDED
```

---

# 53. IndicatorDefinition mapping

| Transition | Event | Classification |
|---|---|---|
| DRAFT → VALIDATED | IndicatorDefinitionValidated | optional |
| VALIDATED → ACTIVE | IndicatorDefinitionActivated | required if authoritative |
| ACTIVE → DEPRECATED | IndicatorDefinitionDeprecated | optional |
| ACTIVE → SUPERSEDED | IndicatorDefinitionSuperseded | required |

---

# 54. FinancialIndicatorValue

Status :

```text
CALCULATED
NOT_APPLICABLE
UNDEFINED
INDETERMINATE
ERROR
```

Mapping :

```text
NO_EVENT
```

par défaut.

---

# 55. FinancialDiagnostic

Result semantics only.

Mapping :

```text
NO_EVENT
```

---

# 56. MatchingCandidate

Pattern :

```text
candidate → validated AccountingMatch
```

---

# 57. Match mapping

| Fact | Event | Classification |
|---|---|---|
| match candidate generated | none/application-only | no domain event |
| match validated | AccountingMatchValidated | required |
| match reversed | AccountingMatchReversed | required |

---

# 58. ReconciliationRun — mapping futur

Lifecycle cible :

```text
PLANNED
RUNNING
REVIEW_REQUIRED
COMPLETED
FAILED
CANCELLED
SUPERSEDED
```

---

# 59. ReconciliationRun events

```text
ReconciliationStarted
ReconciliationCompleted
ReconciliationSuperseded
```

avec :

```text
ReconciliationCompleted
=
REQUIRED
```

---

# 60. ConsolidationRun — mapping futur

Lifecycle cible :

```text
PLANNED
COLLECTING
VALIDATING
ELIMINATING
READY_TO_PUBLISH
PUBLISHEDFAILED
REOPENED
```

---

# 61. Consolidation events

```text
ConsolidationStarted
PackageAccepted
EliminationPosted
ConsolidationValidated
ConsolidationPublished
ConsolidationReopened
```

---

# 62. ConsolidationPublished

Classification :

```text
REQUIRED
```

---

# 63. ExternalEffect — mapping futur

Lifecycle :

```text
PLANNED
IN_PROGRESS
SUCCEEDED
FAILED_RETRYABLE
FAILED_FINAL
UNCERTAIN
RECONCILING
MANUAL_REVIEW
```

---

# 64. ExternalEffect mapping

Ces faits appartiennent principalement à :

```text
application/operational layer
```

et ne sont pas nécessairement des DomainEvents comptables.

---

# 65. ExternalEffectBecameUncertain

Classification :

```text
APPLICATION_EVENT_ONLY
or
OPERATIONAL_ONLY
```

---

# 66. ExternalEffectSucceeded

Peut produire :

```text
IntegrationEvent
```

selon le use case.

---

# 67. Cross-cutting matrix

| Object | Lifecycle | State Machine | Required Domain Events? |
|---|---:|---:|---:|
| JournalEntry | yes | yes | yes |
| AccountingPeriod | yes | yes | yes |
| ClosingRun | yes | yes | yes |
| ImportBatch | yes | yes | selective |
| Settlement | yes | yes | yes |
| SettlementAllocation | yes | simple | selective |
| DueItem | derived | no | no by default |
| PolicySet | yes | simple | yes |
| CompanyChartVersion | yes | simple | yes |
| RegulatoryBinding | yes | simple | yes |
| StatementMappingSet | yes | yes/simple | yes on activation |
| RegulatoryMappingSet | yes | yes/simple | yes on activation |
| RegulatoryProfile | yes | yes/simple | yes on activation |
| ReportSnapshot | yes | yes | yes |
| IndicatorDefinition | yes | simple | selective |
| IndicatorValue | no | no | no |
| FinancialDiagnostic | no | no | no |
| MatchingCandidate | transformation | no | no |
| AccountingMatch | yes | simple | yes |
| ReconciliationRun | future | yes | yes |
| ConsolidationRun | future | yes | yes |
| ExternalEffect | future | yes | mostly app/operational |

---

# 68. Event emission matrix — canonical columns

Artifact cible :

```text
LIFECYCLE_STATE_EVENT_MATRIX.md
```

Colonnes :

```text
context
object
lifecycle_class
from_state
command
guard
to_state
meaningful_fact
domain_event_classification
domain_event_name
audit
outbox
integration
concurrency
test_id
```

---

# 69. Audit mapping rule

Transition critique :

```text
DomainEvent REQUIRED
```

implique généralement :

```text
Audit = YES
```

mais pas toujours strictement.

---

# 70. Outbox mapping rule

Outbox est nécessaire quand :

```text
fact must survive commit
and be consumed asynchronously
```

---

# 71. Integration mapping rule

IntegrationEvent seulement si :

```text
external/public consumer contract exists
```

---

# 72. No automatic integration mapping

```text
DomainEvent
!=
automatically public message
```

---

# 73. State/event atomicity

Pour les transitions critiques :

```text
new state
+
outbox intent
```

doivent être transactionnellement cohérents.

---

# 74. Audit atomicity

Audit critique doit partager :

```text
same UoW
```

si le contrat exige qu’il soit inséparable du fait métier.

---

# 75. Mapping F14

Payloads :

```text
AuditEvent
OutboxRecord
DomainEvent
```

doivent être immuables/canonisés.

---

# 76. Mapping F22

`ReportSnapshotPublished` ne peut apparaître que si :

```text
VALIDATED → PUBLISHED
```

a été validée.

---

# 77. Mapping F11

La séquence événementielle ne doit pas être dupliquée sous :

```text
same idempotency key
different payload
```

---

# 78. Mapping A03

Un :

```text
ProposalPosted
```

event peut exister.

Mais il ne remplace pas :

```text
durable proposal→entry trace
```

---

# 79. Event sequence examples

JournalEntry :

```text
JournalEntryValidated?
    ↓
JournalEntryPosted
    ↓
JournalEntryReversed
```

---

# 80. Closing sequence

```text
PeriodClosingStarted
    ↓
ClosingSealed
    ↓
PeriodClosed
```

selon ownership final.

---

# 81. Ownership ambiguity rule

Éviter que :

```text
ClosingRun
```

et :

```text
AccountingPeriod
```

émettent deux événements synonymes pour le même fait.

---

# 82. Canonical semantic split

Exemple :

```text
ClosingSealed
=
closing process evidence complete

PeriodClosed
=
period business state now closed
```

Les deux peuvent être légitimes car ils n’expriment pas exactement le même fait.

---

# 83. Event sequence and causality

Exemple :

```text
ClosingSealed
causes
PeriodClosed
```

peut utiliser :

```text
causation_id
```

---

# 84. Correlation chain

Exemple :

```text
ClosePeriod command
    ↓
ClosingSealed
    ↓
PeriodClosed
    ↓
ReportSnapshotBecameStale? (derived/no event by default)
```

avec :

```text
same correlation_id
```

---

# 85. Mapping to spec 25

La spec `25` définit :

```text
event_id
event_type
event_schema_version
occurred_at
correlation_id
causation_id
aggregate_type
aggregate_id
accounting_entity_id
actor_context
source
payload
metadata
```

Le présent document décide :

```text
when such envelope is deserved
```

---

# 86. Domain event payload boundaries

Example `JournalEntryPosted` :

```text
entry_id
entity_id
journal_id
period_id
entry_type
currency
total_debit
total_credit
chart_version
reference_snapshot
```

sans :

```text
full aggregate dump
```

---

# 87. SettlementAllocated payload

Minimum :

```text
settlement_id
entity_id
allocation_amount
remaining_open_amount
currency
revision
```

---

# 88. PeriodClosed payload

Minimum :

```text
period_id
entity_id
closing_run_id
trial_balance_checksum
closed_at
```

---

# 89. ReportSnapshotPublished payload

Minimum :

```text
snapshot_id
entity_id
report_type
period_id
checksum
definition_version
mapping_version
published_at
```

---

# 90. Event sequencing and revision

Lorsque pertinent :

```text
aggregate_revision
```

peut aider :

```text
ordering
deduplication
conflict detection
```

---

# 91. No mutable nested references

Event payload ne doit pas contenir :

```text
mutable dict/list alias
```

susceptible de changer après émission.

---

# 92. Cross-adapter semantic parity

Même transition métier doit produire :

```text
same DomainEvent type
same semantic payload
same ordering constraints
```

sur :

```text
InMemory
Django/PostgreSQL
SQLAlchemy/PostgreSQL
```

---

# 93. Infrastructure metadata differences

Peuvent différer :

```text
database transaction id
adapter trace id
storage row id
```

sans affecter la sémantique du DomainEvent.

---

# 94. Transition/event test pair

Chaque transition critique doit avoir :

```text
transition test
+
event test
```

---

# 95. Negative test

Exemple :

```text
DRAFT → POSTED forbidden
```

doit garantir :

```text
no JournalEntryPosted
```

---

# 96. Rollback test

Si commit échoue :

```text
no committed business state
no visible outbox event
```

---

# 97. Replay test

Le replay d’un event ne doit pas :

```text
re-emit blindly
```

un nouvel événement avec nouvelle identité sans règle explicite.

---

# 98. Duplicate delivery test

Integration consumers doivent tolérer :

```text
same event_id twice
```

---

# 99. Event publication test

Outbox dispatch ne doit pas altérer :

```text
event payload
```

---

# 100. State machine test linkage

Recommended naming :

```text
SM-ENTRY-POST-001
EVT-ENTRY-POST-001
OUTBOX-ENTRY-POST-001
```

---

# 101. Golden scenario linkage

Example :

```text
GOLD-ENTRY-POST-001
```

peut vérifier :

```text
state
audit
event
outbox
```

dans un seul scénario.

---

# 102. Race linkage

Example :

```text
RACE-PERIOD-CLOSE-001
```

doit vérifier :

```text
only one legal state outcome
only expected event sequence
```

---

# 103. Architecture fitness rules

```text
AFF-MAP-001
No REQUIRED event without corresponding legal transition/fact.

AFF-MAP-002
No forbidden transition may emit a REQUIRED event.

AFF-MAP-003
Adapters may not invent domain-event semantics.

AFF-MAP-004
Required event payloads must be immutable.

AFF-MAP-005
Outbox representation must preserve event identity.

AFF-MAP-006
IntegrationEvent mappings must be explicit.

AFF-MAP-007
Derived lifecycle changes do not emit DomainEvents by default.

AFF-MAP-008
Transition and event tests must remain linked for critical aggregates.
```

---

# 104. ADR proposals

| ADR | Décision |
|---|---|
| ADR-MAP-001 | Lifecycle, state machine et event restent trois concepts distincts |
| ADR-MAP-002 | Un changement d’état n’implique pas automatiquement un DomainEvent |
| ADR-MAP-003 | Un DomainEvent peut exister sans changement de status |
| ADR-MAP-004 | Les REQUIRED events ont un semantic owner unique |
| ADR-MAP-005 | Audit/Outbox/Integration sont des mappings, pas le DomainEvent lui-même |
| ADR-MAP-006 | Les transitions interdites ne peuvent produire aucun event métier |
| ADR-MAP-007 | Les lifecycles dérivés restent silencieux par défaut |
| ADR-MAP-008 | La publication de report exige VALIDATED → PUBLISHED |
| ADR-MAP-009 | Les événements de closing et period doivent avoir des sémantiques non redondantes |
| ADR-MAP-010 | Les event mappings sont qualifiés cross-adapter |
| ADR-MAP-011 | La causality est utilisée pour relier les faits successifs |
| ADR-MAP-012 | Les event payloads ne sérialisent pas les aggregates complets |
| ADR-MAP-013 | DomainEvent et IntegrationEvent restent découplés |
| ADR-MAP-014 | Les transitions critiques sont atomiques avec leur outbox intent |
| ADR-MAP-015 | Les mappings évoluent avec versioning explicite |

---

# 105. Implementation target structure

Proposition :

```text
src/pyaccountingkit/
    domain/
        events/
            base.py
            ledger.py
            periods.py
            closing.py
            imports.py
            subledgers.py
            references.py
            reporting.py
            reconciliation.py
            consolidation.py

    application/
        event_mapping/
            audit.py
            outbox.py
            integration.py
```

À adapter selon la future migration Domain-First.

---

# 106. Alternative context-local structure

Préférée à terme :

```text
ledger/
    domain/
        events.py

closing/
    domain/
        events.py

subledgers/
    domain/
        events.py
```

---

# 107. Shared kernel rule

Le shared kernel ne doit contenir que :

```text
DomainEvent base contracts
EventId
CorrelationId
CausationId
```

pas les événements métier concrets.

---

# 108. Domain event registry

Artifact recommandé :

```text
DOMAIN_EVENT_REGISTRY.md
```

ou manifest machine-readable.

---

# 109. Registry fields

```text
event_type
schema_version
context
aggregate_type
classification
source_transition
audit_mapping
outbox_mapping
integration_mapping
status
```

---

# 110. Lifecycle-state-event matrix

Artifact final recommandé :

```text
LIFECYCLE_STATE_EVENT_MATRIX.md
```

---

# 111. Machine-readable version

Option :

```text
LIFECYCLE_STATE_EVENT_MATRIX.json
```

pour architecture/test tooling.

---

# 112. Event contract manifest

LOT-40 pourra produire :

```text
DOMAIN_EVENT_MANIFEST.json
```

---

# 113. Public vs internal events

Manifest peut distinguer :

```text
INTERNAL
INTEGRATION_EXPOSED
DEPRECATED
```

---

# 114. Versioning rule

Event schema breaking change :

```text
new schema version
```

pas :

```text
silent payload mutation
```

---

# 115. Deprecation rule

Ancien event peut être :

```text
deprecated
```

mais doit rester interprétable pendant la fenêtre de compatibilité.

---

# 116. Release mapping

LOT-40 :

```text
event model
event envelope
event registry
initial migrations
```

LOT-42 :

```text
golden/race/event parity
```

LOT-44 :

```text
outbox lifecycle/recovery
```

---

# 117. Remediation dependency mapping

```text
REM-03
→ JournalEntry lifecycle/idempotency

REM-04
→ immutable evidence/event payloads

REM-05
→ Period/Closing transitions

REM-06
→ checksums/semantic fidelity

REM-07
→ publication transitions

REM-09
→ persistent subledger lifecycles

REM-10
→ cross-adapter qualification
```

---

# 118. LOT-40 entry criteria

Avant implémentation large :

```text
REM-03 sufficiently stable
REM-04 sufficiently stable
REM-05 critical closing semantics resolved
REM-07 publication semantics resolved
```

---

# 119. LOT-40 first migration scope

Recommended :

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
```

---

# 120. Why not everything at once

Parce que :

```text
event semantics
must follow stable business semantics
```

---

# 121. Progressive migration

```text
P0 events
    ↓
cross-adapter qualification
    ↓
P1 events
    ↓
integration exposure
```

---

# 122. Definition of Done — mapping

```text
[ ] lifecycle identified
[ ] legal transition identified
[ ] meaningful fact identified
[ ] event classification decided
[ ] canonical event name decided
[ ] audit mapping decided
[ ] outbox mapping decided
[ ] integration mapping decided
[ ] payload boundary decided
[ ] tests linked
```
---

# 123. Definition of Done — critical mapping

```text
[ ] illegal transition emits no event
[ ] legal transition emits exact REQUIRED event
[ ] event identity stable
[ ] payload immutable
[ ] audit/outbox atomic as required
[ ] rollback safe
[ ] duplicate delivery safe
[ ] cross-adapter parity green
```

---

# 124. Non-goals

Ce document ne demande pas :

```text
event sourcing
global event bus
event per state
event per object
event per calculation
Kafka/Rabbit mandatory
generic state engine
```

---

# 125. Final canonical model

```text
BUSINESS OBJECT
      ↓
LIFECYCLE
      ↓
STATE MACHINE
      ↓
LEGAL TRANSITION
      ↓
MEANINGFUL BUSINESS FACT
      ↓
DOMAIN EVENT
      ↓
APPLICATION MAPPING
   ┌──────┼───────┐
   ▼      ▼       ▼
AUDIT   OUTBOX   INTEGRATION
```

---

# 126. Final distinction

```text
Lifecycle
=
how an object evolves

State Machine
=
what transitions are legal

Domain Event
=
what meaningful fact happened

Audit Event
=
who/when/why

Outbox
=
how committed intent is delivered safely

Integration Event
=
what external consumers are promised
```

---

# 127. Architecture sequence completed

La série de modélisation transverse devient :

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
DOMAIN EVENTS IMPLEMENTATION
```

---

# 128. Conclusion

Les quatre concepts sont maintenant séparés puis reliés proprement.

La règle de conception finale est :

> **Un objet possède d’abord un lifecycle métier. Ce lifecycle peut être gouverné par une machine à états. Une transition légale peut produire un fait métier significatif. Ce fait peut devenir un DomainEvent, qui sera ensuite éventuellement mappé vers audit, outbox et intégration. Aucun de ces niveaux ne doit être confondu avec les autres.**

En résumé :

```text
STATE MACHINE
decides what MAY happen

DOMAIN EVENT
describes what DID happen

AUDIT
records WHO/WHEN/WHY

OUTBOX
ensures SAFE DELIVERY

INTEGRATION EVENT
defines EXTERNAL CONTRACT
```

Cette spécification constitue donc le pont direct vers :

```text
LOT-40
Domain Events, Causality & Event Envelope
```