# 35_PYACCOUNTINGKIT_BUSINESS_LIFECYCLES_ARCHITECTURE.md

# PyAccountingKit — Business Lifecycles Architecture

> **Projet** : PyAccountingKit  
> **Document** : `35_PYACCOUNTINGKIT_BUSINESS_LIFECYCLES_ARCHITECTURE.md`  
> **Statut** : Spécification transverse — cycles de vie métier  
> **Date** : 22 octobre 2026  
> **Baseline observée** : PyAccountingKit `0.7.0rc1`  
> **Portée** : classification des objets métier selon leur cycle de vie  
> **Hors scope volontaire** :
> - formalisation complète des machines à états ;
> - catalogue complet des Domain Events ;
> - mapping transitions → events ;
> - Event Envelope / causality déjà traité par la spec `25`.  
> **Documents suivants prévus** :
> - `36_PYACCOUNTINGKIT_STATE_MACHINES_AND_TRANSITION_RULES.md`
> - `37_PYACCOUNTINGKIT_DOMAIN_EVENTS_COVERAGE_AND_EMISSION_RULES.md`
> - `38_PYACCOUNTINGKIT_LIFECYCLE_STATE_MACHINE_EVENT_MAPPING.md`

---

# 1. Objet

Cette spécification répond à une question simple mais structurante :

> **Quels objets PyAccountingKit possèdent réellement un cycle de vie métier ?**

Elle ne cherche pas encore à définir toutes les transitions.

Elle établit d'abord :

```text
Business Object
    ↓
What kind of object is it?
    ↓
Does it live through meaningful business stages?
    ↓
Is its state explicit, derived, descriptive, or absent?
```

L'objectif est d'éviter deux erreurs opposées :

```text
under-modeling
=
des cycles métier implicites dispersés dans le code
```

et :

```text
over-modeling
=
des statuts et state machines ajoutés à tous les objets
```

---

# 2. Principe cardinal

Tout objet métier n'a pas nécessairement un lifecycle.

La règle cible est :

```text
business identity
+
meaningful evolution over time
+
legal/illegal transitions
=
Lifecycle Candidate
```

À l'inverse :

```text
immutable value
computed projection
descriptive result
derived status
=
No explicit lifecycle by default
```

---

# 3. Lifecycle != Status

Un champ :

```text
status
```

ne prouve pas qu'un objet possède une machine à états.

Exemples :

```text
IndicatorValueStatus
    CALCULATED
    NOT_APPLICABLE
    UNDEFINED
    INDETERMINATE
    ERROR
```

décrit principalement :

```text
result semantics
```

et non nécessairement :

```text
object lifecycle
```

Même distinction pour :

```text
DiagnosticStatus
MATCHED / NOT_MATCHED / INDETERMINATE
```

---

# 4. Lifecycle != Event

Un lifecycle répond à :

```text
how an object evolves over time
```

Un event répond à :

```text
what meaningful fact happened
```

Les deux seront reliés ultérieurement dans le document `38`.

---

# 5. Lifecycle != Event Sourcing

PyAccountingKit ne devient pas Event Sourced parce qu'il formalise des lifecycles.

Le modèle reste :

```text
current aggregate state
+
repositories
+
UnitOfWork
```

avec éventuellement :

```text
Domain Events
```

comme faits métier.

---

# 6. Taxonomie canonique des lifecycles

Chaque objet est classé dans une des catégories suivantes :

```text
L0 — NO_LIFECYCLE
L1 — DERIVED_LIFECYCLE
L2 — SIMPLE_EXPLICIT_LIFECYCLE
L3 — STATE_MACHINE_CANDIDATE
L4 — PROCESS_LIFECYCLE
```

---

# 7. L0 — NO_LIFECYCLE

Objet sans évolution métier autonome.

Exemples :

```text
Money
Currency
AccountCode
EntryId
JournalLine
FinancialRatio result
StatementLine
```

Caractéristiques :

```text
immutable
replaceable by value
no independent identity lifecycle
no legal transition graph needed
```

---

# 8. L1 — DERIVED_LIFECYCLE

L'état métier peut être calculé à partir des données.

Exemple :

```text
DueItem
```

avec :

```text
open_amount == original_amount
    → OPEN

0 < open_amount < original_amount
    → PARTIALLY_SETTLED

open_amount == 0
    → SETTLED
```

Le lifecycle existe conceptuellement.

Mais ajouter un champ :

```text
status
```

créerait potentiellement une deuxième source de vérité.

---

# 9. L2 — SIMPLE_EXPLICIT_LIFECYCLE

Objet avec quelques états et transitions simples.

Exemples :

```text
AccountingPolicySet
CompanyChartVersion
SettlementAllocation
RegulatoryAccountBinding
```

Caractéristiques :

```text
small finite state set
few transition methods
no long-running process semantics
```

---

# 10. L3 — STATE_MACHINE_CANDIDATE

Aggregate ou entity avec :

```text
several states
transition guards
forbidden transitions
concurrency significance
terminal states
```

Exemples :

```text
JournalEntry
AccountingPeriod
Settlement
ReportSnapshot
```

---

# 11. L4 — PROCESS_LIFECYCLE

Processus métier ou technique long/étagé.

Exemples :

```text
AccountingImportBatch
ClosingRun
future ReconciliationRun
future ConsolidationRun
future ExternalEffect
```

Caractéristiques :

```text
multi-step workflow
failure paths
restart/recovery implications
cross-step evidence
```

---

# 12. Classification des objets PyAccountingKit

| Objet | Nature | Classe lifecycle cible |
|---|---|---|
| `Money` | Value Object | L0 |
| `Currency` | Value Object | L0 |
| `JournalLine` | Aggregate child | L0 |
| `JournalEntry` | Aggregate Root | L3 |
| `AccountingPeriod` | Entity/Aggregate | L3 |
| `ClosingRun` | Process aggregate | L4 |
| `AccountingImportBatch` | Process aggregate | L4 |
| `CompanyChartVersion` | Versioned entity | L2 |
| `CompanyChart` | Aggregate Root | L2/L3 |
| `AccountingPolicySet` | Aggregate Root | L2 |
| `RegulatoryAccountBinding` | Versioned mapping | L2 |
| `StatementMappingSet` | Versioned mapping set | L2/L3 |
| `RegulatoryMappingSet` | Versioned mapping set | L2/L3 |
| `RegulatoryReportingProfile` | Versioned config | L2/L3 |
| `Settlement` | Aggregate Root | L3 |
| `SettlementAllocation` | Entity | L2 |
| `DueItem` | Entity | L1 |
| `MatchingCandidate` | Candidate | L0/L1 |
| `AccountingMatch` | Evidence entity | L2 |
| `SubledgerReconciliation` | Result/projection | L0 |
| `ReportSnapshot` | Snapshot | L3 |
| `FinancialIndicatorDefinition` | Versioned definition | L2 |
| `FinancialIndicatorValue` | Computed result | L0 |
| `DiagnosticRule` | Versioned definition | L2 |
| `FinancialDiagnostic` | Computed result | L0 |
| `TrialBalanceSnapshot` | Snapshot | L0/L2 depending publication |
| `AnalysisSnapshot` | Snapshot | L2 if publication lifecycle exists |
| `ReferenceSnapshot` | Snapshot/version | L2/L3 |
| future `ReconciliationRun` | Process aggregate | L4 |
| future `ConsolidationRun` | Process aggregate | L4 |
| future `ExternalEffect` | Process aggregate | L4 |

---

# 13. JournalEntry lifecycle

Baseline observée :

```text
DRAFT
    ↓ validate()
VALIDATED
    ↓ post/freeze
POSTED
    ↓ reversal
REVERSED
```

Classification :

```text
L3 — STATE_MACHINE_CANDIDATE
```

---

# 14. Pourquoi JournalEntry a un vrai lifecycle

Parce que certaines transitions sont légales :

```text
DRAFT → VALIDATED
VALIDATED → POSTED
POSTED → REVERSED
```

et d'autres interdites :

```text
DRAFT → POSTED
POSTED → DRAFT
REVERSED → POSTED
```

Le statut ne sert donc pas uniquement à décrire.

Il protège des invariants.

---

# 15. JournalEntry lifecycle responsibilities

Le lifecycle doit porter :

```text
validation state
posting eligibility
immutability boundary
reversal eligibility
historical continuity
```

---

# 16. JournalEntry non-responsibilities

Il ne doit pas décider directement :

```text
database transaction
outbox dispatch
external integration
```

---

# 17. AccountingPeriod lifecycle

Baseline :

```text
OPEN
REVIEW
LOCKED
CLOSING
CLOSED
```

avec `can_transition_to()`.

Classification :

```text
L3
```

---

# 18. AccountingPeriod semantics

Le lifecycle protège notamment :

```text
posting allowed?
closing allowed?
reopening policy?
locking?
```

---

# 19. AccountingPeriod current graph

Baseline observée :

```text
OPEN
 ├──→ REVIEW
 ├──→ LOCKED
 └──→ CLOSING

REVIEW
 ├──→ OPEN
 └──→ CLOSING

LOCKED
 └──→ OPEN

CLOSING
 └──→ CLOSED

CLOSED
 └──→ no transition in current enum
```

Le besoin de :

```text
reopen
```

est cependant présent dans l'architecture globale.

Il devra être clarifié dans `36`.

---

# 20. ClosingRun lifecycle

Baseline observée :

```text
RUNNING
    ↓
SEALED
```

Classification cible :

```text
L4
```

La baseline est plus simple que le processus métier réel.

---

# 21. ClosingRun conceptual lifecycle

Le futur modèle pourra distinguer selon besoin :

```text
REQUESTED
VALIDATING
BLOCKED
CLOSING
SEALED
FAILED
REOPENED
```

Mais ces états ne doivent pas être introduits avant validation métier.

---

# 22. Important

Le document `35` ne décide pas encore que tous ces états seront implémentés.

Il indique seulement :

```text
ClosingRun has a true process lifecycle
```

La machine exacte appartient à `36`.

---

# 23. AccountingImportBatch lifecycle

C'est actuellement l'un des exemples les plus explicites.

```text
CREATED
    ↓
ACQUIRED
    ↓
PARSED
    ↓
NORMALIZED
    ↓
MAPPED
    ↓
VALIDATED
    ↓
READY
    ↓
IMPORTING
    ├──→ COMPLETED
    ├──→ COMPLETED_WITH_WARNINGS
    └──→ FAILED
```

avec possibilité de :

```text
CANCELLED
```

à plusieurs étapes.

Classification :

```text
L4
```

---

# 24. AccountingImportBatch maturity

Le code possède déjà :

```text
_ALLOWED
transition()
InvalidImportTransitionError
timestamps
terminal states
```

Il constitue une bonne référence pour `36`.

---

# 25. Settlement lifecycle

Baseline :

```text
OPEN
PARTIALLY_ALLOCATED
FULLY_ALLOCATED
REVERSED
```

Classification :

```text
L3
```

---

# 26. Settlement possède plusieurs dimensions d'état

Le même objet possède aussi :

```text
AccountingEffectStatus

PENDING
POSTED
REVERSED
```

Donc :

```text
operational lifecycle
×
accounting lifecycle
```

---

# 27. Orthogonal lifecycle dimensions

Le modèle cible ne doit pas forcément fusionner :

```text
SettlementStatus
+
AccountingEffectStatus
```

dans une énorme enum.

Préférer :

```text
OperationalState
×
AccountingState
```

si les deux dimensions ont une indépendance légitime.

---

# 28. Valid combination model

Une matrice de compatibilité peut être nécessaire.

Exemple :

| Operational | Accounting | Valid? |
|---|---|---:|
| OPEN | PENDING | ✅ |
| OPEN | POSTED | ✅ |
| PARTIALLY_ALLOCATED | POSTED | ✅ |
| FULLY_ALLOCATED | POSTED | ✅ |
| REVERSED | REVERSED | ✅ |
| REVERSED | PENDING | ❌ |
| FULLY_ALLOCATED | PENDING | ❌ |

---

# 29. SettlementAllocation lifecycle

Baseline :

```text
ACTIVE
    ↓ reversed()
REVERSED
```

Classification :

```text
L2
```

Simple mais réellement temporel.

---

# 30. DueItem lifecycle

Le code utilise :

```text
open_amount
revision
```

sans enum de statut.

Classification :

```text
L1
```

---

# 31. DueItem derived states

On peut dériver :

```text
FULLY_OPEN
PARTIALLY_SETTLED
SETTLED
```

sans les stocker.

---

# 32. DueItem rule

Ne pas ajouter un statut persistant sauf besoin non dérivable.

Sinon risque :

```text
status = OPEN
open_amount = 0
```

---

# 33. AccountingPolicySet lifecycle

Baseline :

```text
DRAFT
ACTIVE
SUPERSEDED
RETIRED
```

avec :

```text
activate()
supersede()
retire()
```

Classification :

```text
L2
```

---

# 34. PolicySet business meaning

Le lifecycle matérialise :

```text
editable?
effective?
historically replayable?
still applicable?
```

---

# 35. PolicySet immutability rule

Après activation :

```text
bindings are no longer freely mutable
```

Les versions historiques doivent rester disponibles pour replay.

---

# 36. CompanyChart lifecycle

Deux niveaux existent :

```text
CompanyChart
    ↓
CompanyChartVersion
```

Version statuses :

```text
DRAFT
ACTIVE
SUPERSEDED
ARCHIVED
```

Classification :

```text
CompanyChartVersion = L2
CompanyChart = L2/L3
```

---

# 37. CompanyChart temporal semantics

Les versions sont résolues selon :

```text
effective_from
effective_to
accounting_date
```

Le lifecycle est donc aussi :

```text
temporal version lifecycle
```

et pas seulement status lifecycle.

---

# 38. RegulatoryAccountBinding lifecycle

Baseline :

```text
CANDIDATE
ACTIVE
RETIRED
```

Classification :

```text
L2
```

---

# 39. Candidate != active rule

Le lifecycle protège une règle importante :

```text
candidate mapping
!=
executable mapping
```

---

# 40. StatementMappingSet lifecycle

Baseline status vocabulary :

```text
DRAFT
REVIEW_REQUIRED
VALIDATED
ACTIVE
SUPERSEDED
ARCHIVED
```

Classification :

```text
L2/L3
```

---

# 41. StatementAccountMapping status

Baseline :

```text
CANDIDATE
REVIEW_REQUIRED
VALIDATED
REJECTED
SUPERSEDED
```

Attention :

```text
individual mapping lifecycle
```

et :

```text
mapping set lifecycle
```

sont distincts.

---

# 42. RegulatoryMappingSet lifecycle

Même famille :

```text
DRAFT
REVIEW_REQUIRED
VALIDATED
ACTIVE
SUPERSEDED
ARCHIVED
```

Classification :

```text
L2/L3
```

---

# 43. RegulatoryReportingProfile lifecycle

Baseline :

```text
DRAFT
REVIEW_REQUIRED
VALIDATED
ACTIVE
SUPERSEDED
ARCHIVED
```

Classification :

```text
L2/L3
```

Ce lifecycle protège l'exécutabilité réglementaire.

---

# 44. ReportSnapshot lifecycle

Baseline statuses :

```text
DRAFT
VALIDATED
PUBLISHED
SUPERSEDED
```

Classification :

```text
L3
```

---
# 45. ReportSnapshot gap important

Le code actuel peut construire un snapshot directement avec :

```text
status = PUBLISHED
```

par défaut.

Cela montre que :

```text
status vocabulary exists
```

mais :

```text
transition governance is incomplete
```

---

# 46. ReportSnapshot target concept

Conceptuellement :

```text
DRAFT
    ↓ validate
VALIDATED
    ↓ publish
PUBLISHED
    ↓ supersede
SUPERSEDED
```

Les guards seront définis dans `36`.

---

# 47. FinancialIndicatorDefinition lifecycle

Baseline :

```text
DRAFT
VALIDATED
ACTIVE
DEPRECATED
SUPERSEDED
```

Classification :

```text
L2
```

---

# 48. IndicatorValueStatus is not a lifecycle

Baseline :

```text
CALCULATED
NOT_APPLICABLE
UNDEFINED
INDETERMINATE
ERROR
```

Classification :

```text
L0 result semantics
```

Ce statut décrit le résultat d'un calcul.

Il ne représente pas forcément une transition historique.

---

# 49. DiagnosticRule vs FinancialDiagnostic

`DiagnosticRule` possède une définition versionnée.

Classification :

```text
L2
```

`FinancialDiagnostic` contient :

```text
MATCHED
NOT_MATCHED
INDETERMINATE
```

Classification :

```text
L0
```

car il s'agit d'un résultat.

---

# 50. MatchingCandidate lifecycle

`MatchingCandidate` représente une proposition calculée.

Il devient éventuellement un :

```text
AccountingMatch
```

via :

```text
validate()
```

Ce n'est pas forcément :

```text
same object changing status
```

---

# 51. Candidate-to-result pattern

Pattern :

```text
MatchingCandidate
    ↓ validate
AccountingMatch
```

Il s'agit davantage d'une :

```text
domain transformation
```

que d'une machine à états classique.

Classification :

```text
Candidate = L0/L1
Match = L2 evidence entity
```

---

# 52. SubledgerReconciliation lifecycle

Baseline status :

```text
MATCHED
DIFFERENCE
```

Classification :

```text
L0
```

Pourquoi :

```text
it describes reconciliation outcome
```

et non un process lifecycle persistant.

---

# 53. Future ReconciliationRun

En revanche :

```text
ReconciliationRun
```

aura probablement :

```text
L4
```

car il représente un processus durable :

```text
created
running
review
completed
failed
superseded
```

à confirmer dans la spec dédiée.

---

# 54. Future ConsolidationRun

Même logique.

Classification cible :

```text
L4
```

---

# 55. Reference snapshots

Un snapshot réglementaire peut posséder :

```text
build
seal
publish
supersede
```

selon son niveau de gouvernance.

Classification cible :

```text
L2/L3
```

Mais un simple objet de référence immutable chargé depuis un provider peut rester :

```text
L0
```

---

# 56. Snapshot lifecycle rule

Ne pas confondre :

```text
immutable data object
```

avec :

```text
published version lifecycle
```

---

# 57. Three lifecycle dimensions

PyAccountingKit doit distinguer au minimum :

```text
BUSINESS STATE
PROCESS STATE
PUBLICATION STATE
```

---

# 58. Business state

Exemples :

```text
JournalEntry POSTED
Settlement FULLY_ALLOCATED
Period CLOSED
```

---

# 59. Process state

Exemples :

```text
ImportBatch IMPORTING
ClosingRun RUNNING
ExternalEffect RECONCILING
```

---

# 60. Publication state

Exemples :

```text
ReportSnapshot PUBLISHED
MappingSet ACTIVE
PolicySet SUPERSEDED
```

---

# 61. Ne pas fusionner les dimensions sans nécessité

Un objet peut combiner :

```text
business state
+
publication state
```

mais une enum cartésienne massive est souvent une mauvaise solution.

---

# 62. Lifecycle source of truth

Pour chaque objet, une seule représentation canonique doit exister.

Possibilités :

```text
explicit status field
derived state
temporal version interval
process phase
immutable replacement semantics
```

---

# 63. One source of truth rule

Interdit :

```text
status says CLOSED
but closed_at is None
```

ou :

```text
status says OPEN
but derived values imply settled
```

sauf si la divergence est explicitement modélisée.

---

# 64. Lifecycle invariants

Chaque lifecycle explicite doit définir :

```text
initial state
reachable states
terminal states
guards
side conditions
temporal constraints
re-entry policy
```

---

# 65. Lifecycle and immutability

PyAccountingKit privilégie :

```text
immutable objects
```

Donc une transition produit généralement :

```text
old immutable state
    ↓
new immutable state
```

plutôt qu'une mutation en place.

---

# 66. Immutable transition model

Exemple :

```text
JournalEntry(DRAFT)
    ↓ validate()
JournalEntry(VALIDATED)
```

---

# 67. Lifecycle and identity

Même objet logique :

```text
same aggregate identity
```

à travers ses transitions.

Exemple :

```text
EntryId remains stable
```

entre :

```text
DRAFT
VALIDATED
POSTED
REVERSED
```

---

# 68. Lifecycle and revision

Les lifecycles critiques doivent considérer :

```text
optimistic concurrency
revision
expected state
```

Exemple :

```text
Settlement.revision
```

---

# 69. Transition race

Un lifecycle devient critique lorsque deux commandes peuvent tenter :

```text
same current state
→ different next states
```

Exemple :

```text
Period OPEN
    ├── posting
    └── close
```

---

# 70. Lifecycle and transaction boundary

Le changement d'état critique doit être atomique avec ses preuves applicables.

Exemple :

```text
POSTED state
+
audit
+
idempotency
+
outbox
```

---

# 71. Lifecycle and audit

Toutes les transitions ne nécessitent pas nécessairement un AuditEvent.

Mais les transitions critiques doivent être traçables.

---

# 72. Lifecycle and events

Le document `37` décidera si une transition produit :

```text
DOMAIN_EVENT_REQUIRED
DOMAIN_EVENT_OPTIONAL
APPLICATION_EVENT_ONLY
AUDIT_ONLY
NO_EVENT
```

---

# 73. Lifecycle and state machine

Le document `36` transformera les lifecycles explicites en :

```text
transition tables
guards
forbidden paths
terminal states
```

---

# 74. Lifecycle and event mapping

Le document `38` reliera :

```text
Lifecycle
    ↓
Transition
    ↓
Meaningful Business Fact
    ↓
Domain Event
```

---

# 75. Anti-pattern — Status Everywhere

Ne pas ajouter :

```text
status: Status
```

à chaque dataclass.

---

# 76. Anti-pattern — Boolean state explosion

Éviter :

```text
is_active
is_validated
is_published
is_superseded
is_archived
```

si ces booléens sont mutuellement exclusifs.

Préférer un lifecycle explicite.

---

# 77. Anti-pattern — Impossible combinations

Exemple mauvais :

```text
is_published = True
is_validated = False
```

---

# 78. Anti-pattern — Derived state duplicated

Exemple :

```text
DueItem.status = SETTLED
open_amount = 100
```

---

# 79. Anti-pattern — Generic state machine engine

Ne pas introduire prématurément :

```text
GenericStateMachine[T]
WorkflowEngine
TransitionRegistry
```

dans le core.

---

# 80. Domain-specific methods preferred

Préférer :

```text
entry.validate()
policy_set.activate()
allocation.reversed()
batch.transition()
```

avec noms métier explicites.

---

# 81. Generic primitive only if proven useful

Un primitive partagé peut être envisagé uniquement pour :

```text
transition validation
transition metadata
state graph testing
```

si une duplication significative existe.

---

# 82. Lifecycle ownership

Le lifecycle appartient au bounded context qui possède l'objet.

Exemple :

```text
JournalEntry lifecycle
→ journals / ledger domain
```

Pas :

```text
generic workflow package
```

---

# 83. Application responsibility

Application orchestre :

```text
load aggregate
invoke legal transition
persist new state
record audit/outbox
commit
```

---

# 84. Domain responsibility

Domain décide :

```text
transition allowed?
invariants satisfied?
new domain state?
```

---

# 85. Infrastructure responsibility

Infrastructure décide :

```text
how state is stored
how concurrency is enforced
how outbox is persisted
```

---

# 86. Lifecycle maturity levels

Introduire aussi une maturité :

```text
M0 — STATUS_ONLY
M1 — GUARDED_METHODS
M2 — EXPLICIT_TRANSITION_GRAPH
M3 — CROSS_ADAPTER_CONCURRENCY_QUALIFIED
M4 — EVENT_COVERED
```

---

# 87. Current maturity examples

| Objet | Maturité approximative |
|---|---|
| `AccountingImportBatch` | M2 |
| `AccountingPeriod` | M2 |
| `JournalEntry` | M1/M2 |
| `Settlement` | M1/M2 |
| `PolicySet` | M1 |
| `CompanyChartVersion` | M1 |
| `ReportSnapshot` | M0/M1 |
| `ClosingRun` | M1 |
| `DueItem` | derived, outside scale |

---

# 88. Maturity is not release status

Un objet peut être production-usable sans être M4.

Le niveau M4 signifie seulement :

```text
event coverage explicitly modeled
```

---

# 89. Lifecycle coverage matrix target

Créer un artifact de qualification :

```text
BUSINESS_LIFECYCLE_MATRIX.md
```

ou générer la matrice depuis la documentation.

Colonnes :

```text
object
bounded_context
object_kind
lifecycle_class
state_source
initial_state
terminal_state
transition_owner
concurrency_level
event_required
qualification_status
```

---

# 90. Lifecycle qualification statuses

```text
NOT_APPLICABLE
IDENTIFIED
MODELED
IMPLEMENTED
QUALIFIED
```

---

# 91. Lifecycle concurrency classification

```text
NONE
LOW
MEDIUM
HIGH
CRITICAL
```

---

# 92. HIGH / CRITICAL candidates

```text
JournalEntry
AccountingPeriod
ClosingRun
Settlement
ImportBatch
ReportSnapshot publication
future ExternalEffect
```

---

# 93. Why ReportSnapshot is high risk

Parce qu'une publication incorrecte peut rendre visible :

```text
invalid financial output
```

même sans mutation du ledger.

---

# 94. Why ImportBatch is high risk

Parce qu'un état incohérent peut provoquer :

```text
duplicate accounting
partial accounting
false completion
```

---

# 95. Why Settlement is high risk

Parce qu'il combine :

```text
operational allocation
accounting effect
reversal
concurrency
```

---

# 96. Why Period is critical

Parce qu'il régule :

```text
whether posting is legally allowed
```

---

# 97. Relationship with audit remediation

La remédiation actuelle doit stabiliser plusieurs lifecycles avant leur formalisation future.

Mapping :

```text
REM-03
    JournalEntry

REM-05
    AccountingPeriod / ClosingRun

REM-07
    ReportSnapshot publication

REM-09
    persistent subledger lifecycles
```

---

# 98. Relationship with LOT-40

LOT-40 ne doit pas inventer des events sans lifecycle ownership clair.

Prérequis conceptuel :

```text
35 Lifecycle catalog
    ↓
36 Transition rules
    ↓
37 Event coverage
    ↓
38 Mapping
    ↓
LOT-40
```

---

# 99. Relationship with LOT-42

Les lifecycles critiques doivent générer des scénarios :

```text
golden transitions
forbidden transitions
concurrency races
```

---

# 100. Relationship with LOT-44

`ExternalEffect` sera probablement le lifecycle le plus explicite du runtime :

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

Il relève :

```text
L4
```

---

# 101. Relationship with Domain-First migration

Chaque lifecycle doit rester propriétaire de son bounded context lors du futur move de packages.

La migration package ne doit pas séparer :

```text
aggregate
transition rules
lifecycle errors
```

---

# 102. Lifecycle error taxonomy

Les lifecycles critiques doivent utiliser des erreurs métier typées.

Exemples :

```text
InvalidEntryStateError
InvalidImportTransitionError
AlreadyReversedError
PeriodClosedError
```

---

# 103. No generic InvalidStateError everywhere

Préférer une erreur contextuelle lorsque la sémantique métier est utile.

---

# 104. Time semantics

Certains lifecycles nécessitent :

```text
transition timestamp
effective_from
effective_to
posted_at
completed_at
sealed_at
```

---

# 105. Clock rule

Le temps métier doit provenir :

```text
Clock
```

dans les use cases/transactions concernés.

---
# 106. Effective-time vs transaction-time

Distinguer :

```text
effective_from
```

de :

```text
recorded_at
```

pour les objets versionnés.

---

# 107. Temporal lifecycle examples

```text
PolicySet
CompanyChartVersion
RegulatoryProfile
MappingSet
```

---

# 108. Terminal state rule

Un état terminal signifie :

```text
no ordinary forward transition
```

mais n'interdit pas forcément une opération compensatoire.

Exemple :

```text
JournalEntry POSTED
```

n'est pas modifié.

Une contrepassation produit :

```text
new JournalEntry
+
original REVERSED marker/reference
```

---

# 109. Supersession rule

Pour les objets versionnés :

```text
SUPERSEDED
```

ne signifie pas :

```text
deleted
```

Il signifie :

```text
historically preserved
not current
```

---

# 110. Archive rule

```text
ARCHIVED
```

doit être distingué de :

```text
SUPERSEDED
```

si les deux ont une valeur métier différente.

---

# 111. Review-required rule

Pour les mappings réglementaires :

```text
REVIEW_REQUIRED
```

est un état de gouvernance.

Il doit bloquer l'exécutabilité si le contrat l'exige.

---

# 112. Candidate rule

```text
CANDIDATE
```

doit rester distinct de :

```text
VALIDATED
ACTIVE
```

---

# 113. Lifecycle visibility

Un lifecycle peut être :

```text
internal
public
integration-visible
```

Tout état interne n'a pas besoin d'être exposé dans l'API publique.

---

# 114. Public API mapping

La façade publique doit exposer :

```text
stable lifecycle semantics
```

pas nécessairement :

```text
internal enum implementation
```

---

# 115. Persistence mapping

Les adapters doivent préserver :

```text
state semantics
revision
timestamps
identity
```

sans inventer de transitions.

---

# 116. ORM constraint rule

Pour les lifecycles critiques, certaines invariants peuvent être doublées par :

```text
CHECK
UNIQUE
FOREIGN KEY
optimistic revision
```

mais l'ORM ne devient pas l'unique source des règles.

---

# 117. Cross-adapter parity

Même command sequence :

```text
InMemory
Django/PostgreSQL
SQLAlchemy/PostgreSQL
```

doit produire :

```text
same business lifecycle outcome
```

---

# 118. Lifecycle contract tests

Exemples :

```text
DRAFT → VALIDATED succeeds
DRAFT → POSTED fails
POSTED mutation fails
REVERSED → POSTED fails
```

---

# 119. Property tests

Invariants :

```text
terminal state cannot regress
revision monotonically increases where relevant
superseded version remains queryable
derived state matches underlying amounts
```

---

# 120. Golden lifecycle tests

Scénarios P0 :

```text
GOLD-LIFE-ENTRY-001
GOLD-LIFE-PERIOD-001
GOLD-LIFE-IMPORT-001
GOLD-LIFE-SETTLEMENT-001
GOLD-LIFE-REPORT-001
```

---

# 121. Race lifecycle tests

```text
RACE-LIFE-PERIOD-001
posting vs close

RACE-LIFE-SETTLEMENT-001
double allocation

RACE-LIFE-REPORT-001
validate/publish conflict
```

---

# 122. Architecture Fitness Functions

Propositions :

```text
AFF-LIFE-001
Value Objects MUST NOT expose mutable lifecycle state.

AFF-LIFE-002
Derived lifecycle state MUST NOT be redundantly persisted without justification.

AFF-LIFE-003
Critical lifecycle transitions MUST be guarded by domain logic.

AFF-LIFE-004
Adapters MUST NOT invent business transitions.

AFF-LIFE-005
Production-critical lifecycles MUST have contract tests.

AFF-LIFE-006
Terminal/superseded historical states MUST remain replayable when required.

AFF-LIFE-007
Lifecycle transitions MUST preserve aggregate identity.

AFF-LIFE-008
State transitions MUST NOT bypass UnitOfWork when persistence is involved.
```

---

# 123. ADR proposals

| ADR | Décision |
|---|---|
| ADR-LIFE-001 | Tous les objets métier n'ont pas un lifecycle explicite |
| ADR-LIFE-002 | Les Value Objects n'ont pas de state machine |
| ADR-LIFE-003 | Les états dérivables ne sont pas persistés par défaut |
| ADR-LIFE-004 | Les lifecycles métier appartiennent au bounded context propriétaire |
| ADR-LIFE-005 | Les transitions critiques sont exprimées par des méthodes métier |
| ADR-LIFE-006 | PyAccountingKit n'introduit pas de GenericStateMachine universelle |
| ADR-LIFE-007 | Les objets de domaine restent immutables entre transitions |
| ADR-LIFE-008 | Une transition conserve l'identité logique de l'aggregate |
| ADR-LIFE-009 | Process state et business state peuvent être orthogonaux |
| ADR-LIFE-010 | Publication state est distinct de calculation result state |
| ADR-LIFE-011 | `status` descriptif n'implique pas une machine à états |
| ADR-LIFE-012 | Candidate/Validated/Active doivent rester distincts lorsqu'ils affectent l'exécutabilité |
| ADR-LIFE-013 | Superseded ne signifie jamais deleted |
| ADR-LIFE-014 | Les lifecycles critiques sont qualifiés cross-adapter |
| ADR-LIFE-015 | Les transitions illégales doivent échouer explicitement |
| ADR-LIFE-016 | La concurrence fait partie du contract des lifecycles critiques |
| ADR-LIFE-017 | Les lifecycles n'impliquent pas Event Sourcing |
| ADR-LIFE-018 | Les Domain Events sont étudiés séparément dans la spec 37 |
| ADR-LIFE-019 | Le mapping transition/event appartient à la spec 38 |
| ADR-LIFE-020 | Le lifecycle catalog doit rester synchronisé avec les objets métier |

---

# 124. Definition of Done — lifecycle catalog

```text
[ ] major business objects inventoried
[ ] object kind identified
[ ] lifecycle class L0..L4 assigned
[ ] source of truth identified
[ ] explicit vs derived status distinguished
[ ] concurrency importance classified
[ ] ownership bounded context identified
[ ] future state-machine candidates listed
```

---

# 125. Definition of Done — explicit lifecycle

```text
[ ] initial state identified
[ ] terminal states identified
[ ] transition ownership identified
[ ] timestamps identified
[ ] revision/concurrency need identified
[ ] persistence boundary identified
[ ] public visibility identified
```

---

# 126. Open questions for `36`

Le document suivant devra répondre à :

```text
exact allowed transitions?
exact guards?
reopen semantics?
terminal state semantics?
cross-dimension constraints?
transition error taxonomy?
transition metadata?
```

---

# 127. Open questions for `37`

Le catalogue d'events devra répondre à :

```text
which lifecycle facts deserve DomainEvent?
which remain audit-only?
which are application-only?
which events are integration-visible?
```

---

# 128. Open questions for `38`

Le mapping final devra répondre à :

```text
transition
    ↓
event?
    ↓
audit?
    ↓
outbox?
    ↓
integration?
```

---

# 129. Recommended implementation sequence

```text
35
Lifecycle catalog
    ↓
36
State machines
    ↓
37
Event coverage
    ↓
38
Lifecycle/State/Event mapping
    ↓
LOT-40
Domain Events implementation
```

---

# 130. Non-goals

Ce document ne propose pas :

```text
event sourcing
generic BPM engine
workflow DSL
state-machine dependency
saga framework
universal status base class
```

---

# 131. Architecture target

```text
VALUE OBJECTS
    no lifecycle

DERIVED ENTITIES
    derived lifecycle

SIMPLE VERSIONED OBJECTS
    explicit simple lifecycle

AGGREGATE ROOTS
    guarded lifecycle

LONG-RUNNING PROCESSES
    explicit process lifecycle
```

---

# 132. Canonical decision rule

Pour chaque objet :

```text
Does it have stable identity?
        │
        ├── NO → normally no lifecycle
        │
        └── YES
              ↓
Does it evolve through meaningful stages?
        │
        ├── NO → no explicit lifecycle
        │
        └── YES
              ↓
Can state be fully derived?
        │
        ├── YES → derived lifecycle
        │
        └── NO
              ↓
Are transitions constrained?
        │
        ├── LOW complexity → simple lifecycle
        │
        └── HIGH complexity → state-machine candidate
```

---

# 133. Conclusion

PyAccountingKit possède déjà plusieurs lifecycles métier réels.

Ils ne sont cependant pas encore documentés avec une taxonomie commune.

La cible n'est pas :

```text
put a status on every object
```

mais :

```text
identify real business lifecycles
    ↓
distinguish explicit / derived / descriptive states
    ↓
formalize only meaningful transitions
    ↓
connect them later to Domain Events
```

Le principe final est :

> **Un lifecycle n'est justifié que lorsqu'il protège l'évolution d'une identité métier dans le temps. Les Value Objects, projections et résultats calculés ne doivent pas recevoir artificiellement une machine à états.**

Le prochain document logique est :

```text
36_PYACCOUNTINGKIT_STATE_MACHINES_AND_TRANSITION_RULES.md
```