# 04 - PyAccountingKit - Architecture des Accounting Policies, de la reconnaissance et de l'évaluation

> **Projet** : PyAccountingKit  
> **Document** : `04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md`  
> **Documents parents** :
> - `00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`
> - `01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`
> - `02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`
> - `03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md`
> **Statut** : P0.5 - Spécification du bounded context `Accounting Policies & Measurement`  
> **Langue** : Français  
> **Objet** : Définir l'architecture de reconnaissance comptable, d'évaluation initiale et ultérieure, de bases de mesure, d'amortissement, de dépréciation, de rattachement, de provisions et de résolution de policies dépendantes d'un référentiel, d'une organisation, d'une période ou d'une catégorie comptable.

---

# 1. Résumé exécutif

PyAccountingKit ne doit pas confondre :

```text
référentiel comptable
policy comptable
règle de reconnaissance
règle d'évaluation
écriture comptable
posting
présentation
analyse financière
```

Le bounded context `Accounting Policies & Measurement` est introduit pour répondre à une question centrale :

> Comment exécuter un moteur comptable générique lorsque les règles de reconnaissance et d'évaluation peuvent varier selon le référentiel, l'édition, la juridiction, la catégorie d'actif ou de passif, le secteur, la période et les options de l'organisation ?

La réponse architecturale est :

```text
Accounting Reference Data
        |
        v
Policy Resolution
        |
        v
AccountingPolicySet
        |
        +--> RecognitionPolicy
        +--> MeasurementPolicy
        +--> DepreciationPolicy
        +--> ImpairmentPolicy
        +--> InventoryValuationPolicy
        +--> AccrualPolicy
        +--> ProvisionPolicy
        +--> RoundingPolicy
        |
        v
PolicyExecutionTrace
        |
        v
Accounting Decision / Measurement Result
        |
        v
JournalEntryProposal
        |
        v
Journal & Entries
        |
        v
Validation / Posting
```

Le moteur de posting reste volontairement simple :

```text
il ne décide pas
comment mesurer un actif,
quand reconnaître une provision,
quelle méthode d'amortissement appliquer,
ni si une valeur doit être réévaluée.
```

Ces décisions appartiennent aux policies.

---

# 2. Problème métier adressé

Une architecture comptable naïve finit souvent par contenir :

```python
if standard == "PCG":
    ...
elif standard == "IFRS":
    ...
elif standard == "SYSCOHADA":
    ...
```

dans :

```text
PostingService
JournalEntry
Repository
FinancialStatementService
ImportService
```

Cette approche crée :

- couplage réglementaire ;
- duplication ;
- impossibilité de versionner les méthodes ;
- difficulté d'audit ;
- difficultés de migration ;
- tests complexes ;
- contamination du coeur générique.

PyAccountingKit doit au contraire rendre les règles explicites et remplaçables.

---

# 3. Objectifs du bounded context

Le bounded context doit permettre de :

1. déterminer si un événement ou élément est reconnu comptablement ;
2. déterminer à quelle date il est reconnu ;
3. déterminer la base de mesure applicable ;
4. calculer une mesure initiale ;
5. calculer une mesure ultérieure ;
6. gérer amortissement et dépréciation ;
7. gérer rattachement, régularisations et provisions ;
8. résoudre la policy applicable ;
9. versionner les policies ;
10. conserver une trace complète de leur exécution ;
11. produire des propositions d'écritures sans contourner le coeur comptable ;
12. séparer méthode comptable et règle réglementaire ;
13. permettre à un même moteur transactionnel de fonctionner sous plusieurs référentiels.

---

# 4. Non-objectifs

Ce bounded context ne doit pas :

```text
tenir le grand livre
poster directement une écriture
gérer une transaction SQL
gérer Django / SQLAlchemy
définir un plan réglementaire
interpréter automatiquement tout texte réglementaire
inventer une règle absente du référentiel
faire de l'analyse financière
faire de la valorisation d'entreprise
```

---

# 5. Position dans l'architecture

```text
+-----------------------------------+
| Accounting Reference Data         |
| standard / edition / concepts     |
+-----------------+-----------------+
                  |
                  v
+-----------------------------------+
| Accounting Policies & Measurement |
| policy resolution                 |
| recognition                       |
| measurement                       |
| depreciation                      |
| impairment                        |
| accruals / provisions             |
+-----------------+-----------------+
                  |
                  v
+-----------------------------------+
| Journal & Entries                 |
| JournalEntryProposal              |
| JournalEntry                      |
+-----------------+-----------------+
                  |
                  v
+-----------------------------------+
| Posting & Reversal                |
+-----------------------------------+
```

---

# 6. Principe fondamental : Reference != Policy

Le référentiel décrit le cadre normatif disponible.

La policy détermine comment une organisation applique ce cadre dans un contexte donné.

```text
ReferenceStandard
    fr-pcg:2026
        |
        v
AccountingPolicySet
    entity-a-v3
```

Les deux objets ont des responsabilités distinctes.

---

# 7. Principe fondamental : Policy != Posting

```text
Policy
    -> calcule / décide

Posting
    -> valide / rend définitif
```

Une `MeasurementPolicy` peut calculer un montant.

Elle ne doit pas appeler directement :

```text
repository.save()
transaction.commit()
entry.status = POSTED
```

---

# 8. Principe fondamental : Policy != Heuristique

Une heuristique peut produire :

```text
suggested policy
suggested mapping
candidate treatment
```

mais ne devient pas exécutable par défaut si une validation est requise.

---

# 9. Aggregate Root - `AccountingPolicySet`

```text
AccountingPolicySet
|
+-- id
+-- accounting_entity_id
+-- code
+-- version
+-- status
+-- effective_from
+-- effective_to
+-- reference_snapshot
+-- parent_policy_set_id?
+-- bindings
+-- metadata
```

Le `AccountingPolicySet` représente un ensemble cohérent de policies applicables à une entité.

---

# 10. Statuts d'un PolicySet

```text
DRAFT
ACTIVE
SUPERSEDED
RETIRED
```

Transitions possibles :

```text
DRAFT
  |
  | activate
  v
ACTIVE
  |
  | supersede
  v
SUPERSEDED

ACTIVE
  |
  | retire
  v
RETIRED
```

---

# 11. Invariants du PolicySet

## INV-POLSET-001

Une seule version active ne doit être sélectionnée pour un même scope et une même date si leurs priorités sont identiques.

---

## INV-POLSET-002

Une policy active doit référencer une version stable.

---

## INV-POLSET-003

La période d'effet doit être valide :

```text
effective_from <= effective_to
```

si `effective_to` existe.

---

## INV-POLSET-004

Un `AccountingPolicySet` lié à un référentiel doit conserver :

```text
standard_id
edition
dataset_version
checksum / reference snapshot
```

---

# 12. `PolicyBinding`

Le `AccountingPolicySet` ne contient pas nécessairement toutes les implémentations.

Il peut contenir des bindings :

```text
PolicyBinding
|
+-- policy_type
+-- policy_id
+-- policy_version
+-- applicability
+-- priority
+-- parameters
+-- source
```

Exemple :

```text
policy_type = DEPRECIATION
policy_id = "straight-line-v1"
scope = ASSET_CATEGORY:PPE
```

---

# 13. Types de policy

Types initiaux :

```text
RecognitionPolicy
MeasurementPolicy
DepreciationPolicy
ImpairmentPolicy
InventoryValuationPolicy
AccrualPolicy
DeferralPolicy
ProvisionRecognitionPolicy
ProvisionMeasurementPolicy
RoundingPolicy
EntryNumberingPolicy
ReversalDatePolicy
ClosingPolicy
OpeningBalancePolicy
```

Tous ne seront pas implémentés en P0.

---

# 14. `PolicyApplicability`

```text
PolicyApplicability
|
+-- standard_id?
+-- edition?
+-- jurisdiction?
+-- sector?
+-- accounting_entity_id?
+-- account_type?
+-- reference_concept_id?
+-- asset_category?
+-- liability_category?
+-- transaction_type?
+-- journal_type?
+-- effective_date_range?
```

Le moteur de résolution utilise ces critères.

---

# 15. Priorité des scopes

Proposition initiale :

```text
1. entity-specific
2. sector-specific
3. jurisdiction-specific
4. standard-specific
5. generic
```

A priorité identique, un conflit doit produire une erreur explicite.

---

# 16. `PolicyResolutionService`

Responsabilité :

```text
context
+
available policy bindings
=
one applicable policy
```

Signature conceptuelle :

```python
class PolicyResolutionService:
    def resolve(
        self,
        *,
        policy_type: PolicyType,
        context: PolicyContext,
        policy_set: AccountingPolicySet,
    ) -> ResolvedPolicy:
        ...
```

---

# 17. `PolicyContext`

```text
PolicyContext
|
+-- accounting_entity_id
+-- accounting_date
+-- standard_id
+-- edition
+-- reference_snapshot
+-- accounting_item_type
+-- account_id?
+-- reference_concept_id?
+-- transaction_type?
+-- asset_category?
+-- metadata
```

---

# 18. Résolution fail-closed

Si le moteur trouve :

```text
0 policies applicables
```

alors :

```text
PolicyNotFoundError
```

si la policy est obligatoire.

S'il trouve :

```text
2 policies de même priorité
```

alors :

```text
AmbiguousPolicyResolutionError
```

Il ne choisit pas arbitrairement.

---

# 19. Reconnaissance comptable

La reconnaissance répond à :

```text
Faut-il comptabiliser cet événement / élément ?
```

et :

```text
A quelle date ?
```

---

# 20. `RecognitionPolicy`

Contrat conceptuel :

```python
class RecognitionPolicy(Protocol):
    def evaluate(
        self,
        *,
        event: AccountingEvent,
        context: PolicyContext,
    ) -> RecognitionDecision:
        ...
```

---

# 21. `RecognitionDecision`

```text
RecognitionDecision
|
+-- recognized
+-- recognition_date?
+-- accounting_category?
+-- rationale
+-- evidence
+-- policy_trace
```

---

# 22. États de reconnaissance

```text
RECOGNIZED
NOT_RECOGNIZED
DEFERRED
REQUIRES_REVIEW
```

`REQUIRES_REVIEW` permet de rester fail-closed lorsqu'une décision humaine est nécessaire.

---

# 23. Reconnaissance et événements économiques

Le framework doit distinguer :

```text
EconomicEvent
```

de :

```text
JournalEntry
```

Un événement peut :

```text
ne produire aucune écriture
produire une écriture immédiate
produire une écriture différée
produire plusieurs écritures dans le temps
```

---

# 24. `AccountingEvent`

Concept générique :

```text
AccountingEvent
|
+-- id
+-- entity_id
+-- event_type
+-- occurred_at
+-- document_date?
+-- accounting_date?
+-- source
+-- source_reference
+-- facts
```

Le modèle détaillé des sous-ledgers sera défini plus tard.

---

# 25. Evaluation comptable

La mesure répond à :

```text
Pour quel montant l'élément doit-il être comptabilisé ?
```

Le modèle doit distinguer :

```text
initial measurement
subsequent measurement
```

---

# 26. `MeasurementPolicy`

```python
class MeasurementPolicy(Protocol):
    def measure(
        self,
        *,
        subject: MeasurableAccountingItem,
        context: MeasurementContext,
    ) -> MeasurementResult:
        ...
```

---

# 27. `MeasurementContext`

```text
MeasurementContext
|
+-- accounting_date
+-- functional_currency
+-- measurement_purpose
+-- reference_snapshot
+-- policy_set_version
+-- previous_measurement?
+-- inputs
```

---

# 28. `MeasurementResult`

```text
MeasurementResult
|
+-- amount
+-- currency
+-- measurement_basis
+-- measurement_date
+-- inputs
+-- adjustments
+-- rounding
+-- policy_trace
```

---

# 29. Bases de mesure

Value Object :

```text
MeasurementBasis
```

Valeurs initiales génériques :

```text
HISTORICAL_COST
REVALUED_COST
FAIR_VALUE
AMORTIZED_COST
VALUE_IN_USE
NET_REALIZABLE_VALUE
CURRENT_COST
CUSTOM
```

Attention :

```text
la présence d'une valeur dans cette enum
!=
autorisation de l'utiliser dans tous les référentiels
```

L'applicabilité dépend des policies et du référentiel.

---

# 30. Coût historique

Le coût historique est représenté comme une base de mesure.

```text
MeasurementBasis.HISTORICAL_COST
```

Il peut être composé de :

```text
purchase price
directly attributable costs
adjustments
taxes / duties
discounts
other policy-defined components
```

La composition exacte relève de la policy applicable.

---

# 31. Coût réévalué

Le coût réévalué doit être distinct du coût historique.

```text
MeasurementBasis.REVALUED_COST
```

La réévaluation doit produire :

```text
previous carrying amount
revaluation input
new amount
difference
effective date
policy trace
```

---

# 32. Juste valeur

La juste valeur doit être modélisée comme une base de mesure possible :

```text
MeasurementBasis.FAIR_VALUE
```

PyAccountingKit ne doit pas supposer :

```text
fair value applies to all assets
```

La policy définit :

```text
applicability
source of value
measurement date
confidence / evidence
review requirements
```

---

# 33. Provider externe de valeur

Port proposé :

```python
class ValuationProvider(Protocol):
    def get_value(
        self,
        request: ValuationRequest,
    ) -> ValuationObservation:
        ...
```

Exemples d'adapters futurs :

```text
manual valuation
market data
valuation service
internal appraisal
```

---

# 34. `ValuationObservation`

```text
ValuationObservation
|
+-- value
+-- currency
+-- observed_at
+-- source
+-- source_reference
+-- confidence?
+-- metadata
```

Le provider fournit une observation.

La policy décide comment elle est utilisée.

---

# 35. Mesure initiale

Pipeline :

```text
recognized accounting event
        |
        v
InitialMeasurementPolicy
        |
        v
MeasurementResult
        |
        v
JournalEntryProposal
```

---

# 36. Mesure ultérieure

Pipeline :

```text
existing accounting item
        |
        v
SubsequentMeasurementPolicy
        |
        +--> no change
        +--> depreciation
        +--> impairment
        +--> revaluation
        +--> amortization
        |
        v
MeasurementAdjustment
```

---

# 37. `MeasurementAdjustment`

```text
MeasurementAdjustment
|
+-- previous_amount
+-- new_amount
+-- delta
+-- adjustment_type
+-- accounting_date
+-- policy_trace
```

Types :

```text
DEPRECIATION
AMORTIZATION
IMPAIRMENT
REVERSAL_OF_IMPAIRMENT
REVALUATION
ACCRETION
OTHER
```

---

# 38. Amortissement / depreciation

Le terme `DepreciationPolicy` est utilisé pour les actifs amortissables.

Responsabilité :

```text
déterminer le montant périodique de consommation
selon une méthode configurée
```

---

# 39. `DepreciationPolicy`

Entrées génériques :

```text
depreciable_base
start_date
useful_life
residual_value
method
period
previous_depreciation
```

Sortie :

```text
DepreciationResult
```

---

# 40. Méthodes d'amortissement

Le framework doit permettre des stratégies.

```text
STRAIGHT_LINE
DECLINING_BALANCE
UNITS_OF_PRODUCTION
CUSTOM
```

La disponibilité d'une stratégie ne vaut pas conformité réglementaire universelle.

---

# 41. `DepreciationResult`

```text
DepreciationResult
|
+-- period_amount
+-- cumulative_amount
+-- carrying_amount_after
+-- method
+-- policy_trace
```

---

# 42. Composants d'immobilisation

Le futur bounded context `Fixed Assets` pourra modéliser :

```text
FixedAsset
    |
    +-- AssetComponent A
    +-- AssetComponent B
```

Chaque composant peut utiliser :

```text
different useful life
different depreciation policy
```

Le détail sera spécifié dans le document `Fixed Assets`.

---

# 43. Dépréciation / impairment

`ImpairmentPolicy` détermine si une réduction de valeur doit être reconnue.

---

# 44. `ImpairmentPolicy`

Contrat :

```python
class ImpairmentPolicy(Protocol):
    def assess(
        self,
        *,
        subject: ImpairableItem,
        context: ImpairmentContext,
    ) -> ImpairmentDecision:
        ...
```

---

# 45. `ImpairmentDecision`

```text
ImpairmentDecision
|
+-- impaired
+-- carrying_amount_before
+-- recoverable_or_reference_amount?
+-- impairment_amount
+-- carrying_amount_after
+-- reversal_allowed?
+-- policy_trace
```

---

# 46. Prudence et impairment

Le principe de prudence ne doit pas être un booléen global.

Correct :

```text
Prudence-related requirement
    ->
ImpairmentPolicy
    ->
ImpairmentDecision
```

Incorrect :

```python
if company.prudence:
    write_down_everything()
```

---

# 47. Reversal de dépréciation

Une éventuelle reprise de dépréciation doit être une policy distincte ou une capacité explicite de la policy.

```text
ImpairmentReversalPolicy
```

Elle dépend du référentiel.

---

# 48. Amortized cost

Le coût amorti peut être supporté comme base de mesure :

```text
MeasurementBasis.AMORTIZED_COST
```

Le calcul détaillé n'est pas figé dans P0.

Il pourra être implémenté par une stratégie :

```text
AmortizedCostMeasurementPolicy
```

---

# 49. Stocks

Le futur bounded context `Inventory` consommera :

```text
InventoryValuationPolicy
```

---

# 50. `InventoryValuationPolicy`

Entrées futures :

```text
inventory movements
cost layers
quantity
purchase costs
production costs
period
```

Sortie :

```text
InventoryValuationResult
```

---

# 51. Méthodes de valorisation des stocks

PyAccountingKit doit être capable de brancher :

```text
FIFO
WEIGHTED_AVERAGE
SPECIFIC_IDENTIFICATION
CUSTOM
```

sans les déclarer toutes valides pour tous les référentiels.

---

# 52. Valeur nette de réalisation

La valeur nette de réalisation peut être représentée comme :

```text
MeasurementBasis.NET_REALIZABLE_VALUE
```

Son calcul appartient à une policy dédiée.

---

# 53. Rattachement

Le rattachement est géré par :

```text
AccrualPolicy
DeferralPolicy
MatchingPolicy
```

et non par le Posting Engine.

---

# 54. `AccrualPolicy`

Responsabilité :

```text
déterminer si une charge / un produit
doit être reconnu dans une période
avant facturation ou encaissement
```

---

# 55. `DeferralPolicy`

Responsabilité :

```text
reporter une charge / un produit
sur une période ultérieure
```

---

# 56. `AccrualSchedule`

Concept futur :

```text
AccrualSchedule
|
+-- source_event
+-- start_period
+-- end_period
+-- total_amount
+-- allocation_method
+-- generated_entries
```

---

# 57. Provisions

Les provisions nécessitent deux décisions distinctes :

```text
ProvisionRecognitionPolicy
ProvisionMeasurementPolicy
```

---

# 58. `ProvisionRecognitionPolicy`

Répond à :

```text
Une provision doit-elle être reconnue ?
```

Sortie :

```text
ProvisionRecognitionDecision
```

---

# 59. `ProvisionMeasurementPolicy`

Répond à :

```text
Pour quel montant ?
```

Sortie :

```text
ProvisionMeasurementResult
```

---

# 60. Revue périodique d'une provision

Pipeline futur :

```text
ProvisionCase
    |
    v
review
    |
    +--> unchanged
    +--> increase
    +--> decrease
    +--> release
```

Chaque changement produit une nouvelle mesure et une trace.

---

# 61. `RoundingPolicy`

Le rounding est transversal.

```text
RoundingPolicy
|
+-- calculation_scale
+-- posting_scale
+-- rounding_mode
+-- currency_rules
+-- stage
```

---

# 62. Stades d'arrondi

```text
INPUT
CALCULATION
LINE
ENTRY
REPORT
```

Le moteur doit éviter les arrondis implicites multiples.

---

# 63. `PolicyExecutionTrace`

Objet central :

```text
PolicyExecutionTrace
|
+-- trace_id
+-- policy_type
+-- policy_id
+-- policy_version
+-- policy_set_id
+-- policy_set_version
+-- context
+-- inputs
+-- result
+-- generated_object_refs
+-- reference_snapshot
+-- executed_at
+-- checksum?
```

---

# 64. Objectifs de la trace

Elle doit permettre :

```text
audit
reproductibilité
explication
non-régression
migration
comparaison de policy
replay contrôlé
```

---

# 65. Trace immutable

Une `PolicyExecutionTrace` finalisée est immutable.

Toute correction produit une nouvelle trace.

---

# 66. `JournalEntryProposal`

Les policies ne créent pas directement une écriture postée.

Elles produisent :

```text
JournalEntryProposal
|
+-- entity_id
+-- journal_hint?
+-- accounting_date
+-- entry_type
+-- lines
+-- source
+-- source_reference
+-- policy_traces
```

---

# 67. Ligne proposée

```text
JournalEntryLineProposal
|
+-- account_role
+-- resolved_account_id?
+-- debit / credit
+-- amount
+-- description
+-- dimensions
```

---

# 68. Résolution des comptes

Une policy métier ne doit pas nécessairement connaître le code du compte entreprise.

Elle peut exprimer :

```text
AccountRole
```

Exemples conceptuels :

```text
ASSET_COST_ACCOUNT
DEPRECIATION_EXPENSE_ACCOUNT
ACCUMULATED_DEPRECIATION_ACCOUNT
IMPAIRMENT_EXPENSE_ACCOUNT
PROVISION_ACCOUNT
```

Un `AccountResolutionService` traduit ce rôle vers un `CompanyAccount`.

---

# 69. `AccountRole`

```text
AccountRole
    !=
ReferenceAccountId
    !=
CompanyAccountCode
```

Cette séparation réduit le couplage des policies aux codes.

---

# 70. `AccountResolutionService`

```python
class AccountResolutionService:
    def resolve(
        self,
        *,
        role: AccountRole,
        entity_id: AccountingEntityId,
        context: PolicyContext,
    ) -> CompanyAccountId:
        ...
```

---

# 71. Fail-closed sur les comptes

Si aucun compte n'est résolu :

```text
AccountRoleResolutionError
```

Si plusieurs comptes sont candidats et qu'aucune règle ne départage :

```text
AmbiguousAccountRoleError
```

---

# 72. Relation avec `regulatory-accounting-data-framework`

Le framework réglementaire peut fournir :

```text
standard
edition
reference account hierarchy
concepts
reporting definitions
relations
crosswalks
provenance
```

PyAccountingKit peut construire des bindings de policy à partir de ces informations.

Il ne doit pas inventer :

```text
policy semantics
concept bindings
crosswalk approvals
```

lorsque la source ne les affirme pas.

---

# 73. `AccountingReferenceSnapshot`

Toute exécution de policy dépendante d'un référentiel doit pouvoir figer :

```text
AccountingReferenceSnapshot
|
+-- standard_id
+-- edition
+-- dataset_version
+-- checksum
+-- loaded_at
```

---

# 74. Policy dépendante du référentiel

Exemple :

```text
PolicyBinding
    policy_type = INVENTORY_VALUATION
    standard_id = X
    edition = Y
    policy_id = Z
```

Si le standard change :

```text
PolicyResolution
```

peut sélectionner une autre policy.

---

# 75. Policy d'organisation

Une organisation peut ajouter une policy explicite lorsque le référentiel autorise plusieurs méthodes.

```text
Reference
    allows method A or B

CompanyAccountingProfile
    selects method B
```

La policy sélectionnée devient partie du `AccountingPolicySet`.

---

# 76. Override

Modèle initial :

```text
Generic Policy
    |
    v
Standard Policy
    |
    v
Sector Policy
    |
    v
Entity Policy
```

Un override doit être explicite et traçable.

---

# 77. Pas d'héritage implicite

Le moteur ne doit pas supposer :

```text
standard B belongs to same family as A
    ->
B inherits all A policies
```

L'héritage doit être déclaré.

---

# 78. `PolicyOverride`

```text
PolicyOverride
|
+-- base_policy_id
+-- overriding_policy_id
+-- scope
+-- reason
+-- effective_from
+-- approved_by?
```

---

# 79. Changement de méthode

Un changement de méthode produit :

```text
AccountingPolicySetSuperseded
```

avec :

```text
old version
new version
effective date
reason
actor
reference context
```

---

# 80. Migration de policy

Une migration peut nécessiter :

```text
prospective application
retrospective recalculation
opening adjustment
disclosure-only change
```

PyAccountingKit doit modéliser le **type de migration** sans imposer la méthode réglementaire.

---

# 81. `PolicyMigrationPlan`

```text
PolicyMigrationPlan
|
+-- from_policy_set
+-- to_policy_set
+-- effective_date
+-- migration_strategy
+-- affected_subjects
+-- generated_adjustments
+-- audit_context
```

---

# 82. Stratégies de migration

Enum générique :

```text
PROSPECTIVE
RETROSPECTIVE
OPENING_ADJUSTMENT
NO_RESTATEMENT
CUSTOM
```

L'utilisation autorisée dépend du référentiel.

---

# 83. Comparabilité

La permanence des méthodes est soutenue par :

```text
PolicySet versioning
PolicyMigrationPlan
Analysis / Reporting snapshots
```

Le moteur peut donc expliquer :

```text
pourquoi N et N-1 utilisent des policies différentes
```

---

# 84. Continuité d'exploitation

Le contexte de continuité doit être représenté séparément.

```text
GoingConcernContext
|
+-- status
+-- assessed_at
+-- evidence
+-- effective_from
```

---

# 85. `GoingConcernStatus`

```text
GOING_CONCERN
UNCERTAIN
NON_GOING_CONCERN
```

Le statut ne sélectionne pas à lui seul une base de mesure.

Il enrichit `PolicyContext`.

---

# 86. Interaction continuité / mesure

```text
GoingConcernContext
        |
        v
PolicyResolution
        |
        v
MeasurementPolicy
```

La policy décide de la conséquence.

---

# 87. Prudence

Même logique :

```text
Prudence requirement
        |
        v
specific Recognition / Measurement Policies
```

Pas de :

```text
global_prudence_boolean
```

dans le domaine.

---

# 88. Modèle de preuve

Une décision comptable peut conserver :

```text
EvidenceRef
|
+-- source_type
+-- source_id
+-- document_ref?
+-- observation_ref?
+-- note?
```

---

# 89. Human-in-the-loop

Certaines policies peuvent retourner :

```text
REQUIRES_REVIEW
```

Exemples :

```text
ambiguous impairment evidence
unvalidated valuation
policy conflict
candidate regulatory mapping
```

---

# 90. `PolicyReviewRequest`

```text
PolicyReviewRequest
|
+-- subject
+-- policy
+-- reason
+-- candidate_result
+-- evidence
+-- requested_at
+-- status
```

---

# 91. Statuts de revue

```text
PENDING
APPROVED
REJECTED
SUPERSEDED
```

Une décision approuvée doit être auditable.

---

# 92. Domain Events

```text
AccountingPolicySetCreated
AccountingPolicySetActivated
AccountingPolicySetSuperseded
AccountingPolicySetRetired

PolicyResolved
PolicyResolutionFailed

RecognitionEvaluated
MeasurementCompleted
DepreciationCalculated
ImpairmentAssessed
ProvisionMeasured

PolicyReviewRequested
PolicyReviewApproved
PolicyReviewRejected

PolicyGeneratedEntryProposal
PolicyMigrationPlanned
```

---

# 93. Ports

```text
AccountingPolicySetRepository
PolicyDefinitionRepository
PolicyExecutionTraceRepository

AccountingReferenceProvider
ValuationProvider
ExchangeRateProvider
Clock
IdFactory
AuditPort
```

---

# 94. Application Services

```text
CreateAccountingPolicySet
ActivateAccountingPolicySet
ResolveAccountingPolicy
EvaluateRecognition
MeasureAccountingItem
CalculateDepreciation
AssessImpairment
MeasureProvision
GeneratePolicyBasedEntry
ReviewPolicyDecision
MigrateAccountingPolicySet
```

---

# 95. Command - `EvaluateRecognition`

Entrée :

```text
AccountingEvent
PolicyContext
PolicySetId
```

Sortie :

```text
RecognitionDecision
PolicyExecutionTrace
```

---

# 96. Command - `MeasureAccountingItem`

Entrée :

```text
MeasurableAccountingItem
MeasurementContext
PolicySetId
```

Sortie :

```text
MeasurementResult
PolicyExecutionTrace
```

---

# 97. Command - `GeneratePolicyBasedEntry`

Pipeline :

```text
Recognize
    |
    v
Measure
    |
    v
Resolve Account Roles
    |
    v
JournalEntryProposal
```

Puis l'application appelle le bounded context `Journal & Entries`.

---

# 98. Transaction boundary

Le calcul d'une policy peut être pur.

Le passage :

```text
PolicyExecutionTrace
+
JournalEntry creation
```

peut être orchestré dans un `UnitOfWork`.

Le domaine ne dépend pas du stockage.

---

# 99. Déterminisme

A inputs identiques et policy version identique :

```text
same inputs
+
same policy version
+
same reference snapshot
=
same deterministic result
```

sauf si la policy dépend explicitement d'une observation externe datée.

---

# 100. Dépendances externes

Lorsqu'une policy utilise :

```text
market price
exchange rate
valuation
index
```

l'observation externe doit être figée dans la trace.

---

# 101. Replay

Un replay exact doit pouvoir réutiliser :

```text
captured external observations
```

au lieu de rappeler un provider externe avec une nouvelle valeur.

---

# 102. Checksums

Un `PolicyExecutionTrace` ou `AnalysisSnapshot` peut contenir :

```text
checksum
```

pour détecter des altérations.

---

# 103. Erreurs métier

```text
AccountingPolicyError
|
+-- PolicyNotFoundError
+-- AmbiguousPolicyResolutionError
+-- PolicyNotApplicableError
+-- PolicyExpiredError
+-- PolicyConflictError
+-- PolicyExecutionError
|
+-- RecognitionError
|   +-- RecognitionUndeterminedError
|
+-- MeasurementError
|   +-- UnsupportedMeasurementBasisError
|   +-- MissingMeasurementInputError
|   +-- ValuationUnavailableError
|
+-- DepreciationError
+-- ImpairmentError
+-- ProvisionMeasurementError
|
+-- AccountRoleResolutionError
+-- AmbiguousAccountRoleError
|
+-- PolicyMigrationError
```

---

# 104. Tests unitaires P0

```text
test_policy_set_cannot_have_invalid_effective_range
test_active_policy_has_stable_version

test_policy_resolution_prefers_entity_scope
test_policy_resolution_fails_on_same_priority_conflict
test_required_policy_missing_fails_closed

test_recognition_decision_contains_policy_trace
test_measurement_result_contains_basis
test_measurement_trace_contains_reference_snapshot

test_policy_does_not_post_entry_directly
test_policy_generates_journal_entry_proposal

test_account_role_resolution_fails_when_ambiguous
```

---

# 105. Property-based tests

Exemples :

```text
for any valid policy set:
    resolve(policy_type, context)
    returns at most one executable policy

for any deterministic measurement policy:
    same inputs + same policy version
    => same result

for any depreciation result:
    carrying_amount_after
    = carrying_amount_before - period_amount
    when no other adjustment exists
```

Les propriétés spécifiques dépendent de chaque stratégie.

---

# 106. Golden tests doctrinaux

Les ouvrages servent à construire des scénarios de validation de concepts.

Ils ne sont pas utilisés comme vérité réglementaire actuelle.

Exemples de scénarios futurs :

```text
historical cost initial recognition
straight-line depreciation
impairment
period-end accrual
provision remeasurement
inventory valuation
```

---

# 107. Golden tests réglementaires

Lorsqu'une policy est déclarée conforme à un standard précis :

```text
standard
edition
dataset
policy version
```

doivent être figés dans le test.

---

# 108. Tests de changement de référentiel

Scénario :

```text
same economic event
+
ReferenceStandard A
+
PolicySet A
=
Result A

same economic event
+
ReferenceStandard B
+
PolicySet B
=
Result B
```

Le moteur de posting reste identique.

---

# 109. Tests de changement de méthode

```text
same standard
same entity
different effective policy set
=
different measurement allowed
```

si la configuration l'autorise.

---

# 110. Tests de replay

```text
captured PolicyExecutionTrace
+
captured external observations
=
same reconstructed result
```

---

# 111. Package cible

```text
src/pyaccountingkit/domain/policies/
|
+-- policy_set.py
+-- binding.py
+-- applicability.py
+-- context.py
+-- resolution.py
+-- trace.py
|
+-- recognition/
|   +-- policy.py
|   +-- decision.py
|
+-- measurement/
|   +-- basis.py
|   +-- policy.py
|   +-- result.py
|   +-- adjustment.py
|
+-- depreciation/
|   +-- policy.py
|   +-- result.py
|
+-- impairment/
|   +-- policy.py
|   +-- decision.py
|
+-- accruals/
|   +-- accrual.py
|   +-- deferral.py
|
+-- provisions/
|   +-- recognition.py
|   +-- measurement.py
|
+-- rounding/
    +-- policy.py
```

---

# 112. Application package

```text
src/pyaccountingkit/application/policies/
|
+-- create_policy_set.py
+-- activate_policy_set.py
+-- resolve_policy.py
+-- evaluate_recognition.py
+-- measure_item.py
+-- calculate_depreciation.py
+-- assess_impairment.py
+-- measure_provision.py
+-- generate_entry_proposal.py
+-- migrate_policy_set.py
```

---

# 113. Ports package

```text
src/pyaccountingkit/ports/
|
+-- policy_repository.py
+-- policy_trace_repository.py
+-- valuation_provider.py
+-- exchange_rate_provider.py
+-- reference_provider.py
```

---

# 114. Adapters futurs

```text
adapters/
|
+-- policy/
|   +-- yaml/
|   +-- json/
|   +-- package/
|
+-- valuation/
|   +-- manual/
|   +-- external/
|
+-- reference/
    +-- regulatory_framework/
```

---

# 115. Policies déclaratives vs policies codées

Deux familles doivent être possibles.

## Déclaratives

```text
JSON / YAML / DSL
```

adaptées aux règles simples.

## Codées

```python
class ComplexMeasurementPolicy:
    ...
```

adaptées aux algorithmes complexes.

---

# 116. Limites d'un DSL

Le framework ne doit pas chercher à transformer toute la comptabilité en DSL.

Le DSL est adapté à :

```text
parameters
thresholds
simple formulas
scope
mappings
```

Il est moins adapté à :

```text
complex domain algorithms
external interactions
multi-step calculations
```

---

# 117. Sérialisation des policies

Une policy sérialisable doit exposer :

```text
policy_id
version
type
parameters
applicability
implementation_ref
checksum
```

---

# 118. Sécurité d'exécution

Une policy chargée dynamiquement ne doit pas exécuter du code arbitraire non fiable.

Les adapters de configuration doivent valider :

```text
schema
allowed strategy ids
parameter types
version compatibility
```

---

# 119. Compatibilité des versions

Le framework doit distinguer :

```text
PyAccountingKit version
Policy schema version
Policy implementation version
Accounting standard edition
Dataset version
Company policy set version
```

---

# 120. `PolicySchemaVersion`

Exemple :

```text
policy_schema_version = "1"
```

permettant de migrer les configurations sans confondre schema et règle métier.

---

# 121. Observabilité

Chaque exécution peut émettre :

```text
policy_type
policy_id
policy_version
duration
result_status
review_required
error_code
```

sans exposer des données sensibles inutiles.

---

# 122. Performance

Les policies doivent être :

```text
stateless when possible
cacheable when safe
batch-friendly
deterministic
```

Le caching doit inclure :

```text
policy version
context
reference snapshot
```

---

# 123. Batch measurement

Cas futurs :

```text
depreciation run
inventory valuation
period-end impairment review
provision review
```

Le moteur doit pouvoir traiter un lot tout en produisant une trace par sujet ou par groupe cohérent.

---

# 124. `PolicyRun`

Concept futur :

```text
PolicyRun
|
+-- run_id
+-- policy_id
+-- policy_version
+-- period
+-- subjects
+-- results
+-- status
```

---

# 125. Statuts de PolicyRun

```text
PENDING
RUNNING
COMPLETED
PARTIALLY_FAILED
FAILED
```

---

# 126. Intégration avec Closing

```text
ClosingService
    |
    +--> AccrualPolicy
    +--> ProvisionPolicy
    +--> DepreciationPolicy
    +--> ImpairmentPolicy
    |
    v
JournalEntryProposals
    |
    v
Validation / Posting
```

---

# 127. Intégration avec Fixed Assets

```text
FixedAsset
    |
    v
DepreciationPolicy
    |
    v
DepreciationResult
    |
    v
JournalEntryProposal
```

---

# 128. Intégration avec Inventory

```text
InventoryMovements
    |
    v
InventoryValuationPolicy
    |
    v
InventoryValuationResult
    |
    v
Adjustment Proposal
```

---

# 129. Intégration avec Accruals & Provisions

```text
ProvisionCase
    |
    +--> RecognitionPolicy
    +--> MeasurementPolicy
    |
    v
ProvisionAdjustmentProposal
```

---

# 130. Intégration avec Reporting

Le reporting consomme le résultat comptable.

Il peut afficher :

```text
policy version
measurement basis
change of policy
```

mais ne doit pas recalculer les écritures.

---

# 131. Intégration avec Financial Analysis

`Financial Analysis` peut consommer :

```text
MeasurementBasis
policy version
change history
```

à des fins d'explication.

Il reste read-only.

---

# 132. Anti-pattern - logique standard dans Posting

Interdit :

```python
def post(entry):
    if standard == "IFRS":
        ...
```

---

# 133. Anti-pattern - code compte dans policy générique

Interdit :

```python
depreciation_account = "681"
```

dans une policy générique.

Utiliser :

```text
AccountRole
```

---

# 134. Anti-pattern - base de mesure implicite

Interdit :

```text
amount = subject.cost
```

sans indiquer :

```text
MeasurementBasis
```

---

# 135. Anti-pattern - policy non versionnée

Interdit :

```text
current_policy()
```

sans identifiant et version.

---

# 136. Anti-pattern - valeur externe non tracée

Interdit :

```text
price = market_api.latest()
```

puis écriture sans conserver l'observation utilisée.

---

# 137. Anti-pattern - policy qui persiste

Interdit :

```text
MeasurementPolicy
    -> ORM.save()
```

La persistence est orchestrée par l'application.

---

# 138. Anti-pattern - prudence globale

Interdit :

```text
company.prudence = True
```

comme mécanisme métier unique.

---

# 139. Anti-pattern - héritage réglementaire implicite

Interdit :

```text
same family
    => same policies
```

sans relation explicite.

---

# 140. ADRs

| ID | Décision |
|---|---|
| ADR-POL-001 | `AccountingPolicySet` est un Aggregate Root versionné |
| ADR-POL-002 | Reference Data et Policies sont des bounded contexts distincts |
| ADR-POL-003 | Recognition et Measurement sont distincts |
| ADR-POL-004 | Initial Measurement et Subsequent Measurement sont distincts |
| ADR-POL-005 | `MeasurementBasis` est explicite |
| ADR-POL-006 | Une base de mesure disponible n'est pas automatiquement applicable |
| ADR-POL-007 | Les policies ne postent jamais directement |
| ADR-POL-008 | Les policies produisent des `JournalEntryProposal` |
| ADR-POL-009 | Les comptes sont résolus via `AccountRole` |
| ADR-POL-010 | Les policies sont résolues par scope et priorité |
| ADR-POL-011 | Les conflits de résolution sont fail-closed |
| ADR-POL-012 | `PolicyExecutionTrace` est immutable |
| ADR-POL-013 | Toute dépendance réglementaire conserve un ReferenceSnapshot |
| ADR-POL-014 | Toute observation externe ayant influencé une mesure est tracée |
| ADR-POL-015 | Prudence et continuité influencent des policies, pas le Posting Engine |
| ADR-POL-016 | La permanence des méthodes est soutenue par le versioning |
| ADR-POL-017 | Un changement de méthode passe par `PolicyMigrationPlan` |
| ADR-POL-018 | L'héritage de policy n'est jamais implicite |
| ADR-POL-019 | Le framework supporte policies déclaratives et policies codées |
| ADR-POL-020 | Les specialized domains utilisent le moteur de policy plutôt que de dupliquer les règles |

---

# 141. Critères d'acceptation P0.5

```text
[ ] AccountingPolicySet est défini

[ ] PolicyBinding est défini

[ ] PolicyApplicability est défini

[ ] PolicyContext est défini

[ ] PolicyResolutionService est spécifié

[ ] résolution ambiguë = erreur explicite

[ ] RecognitionPolicy est distinct de MeasurementPolicy

[ ] RecognitionDecision est explicite

[ ] MeasurementBasis est explicite

[ ] MeasurementResult conserve la policy utilisée

[ ] InitialMeasurement et SubsequentMeasurement sont distincts

[ ] coût historique est supporté comme base de mesure

[ ] juste valeur est supportée comme base de mesure configurable

[ ] DepreciationPolicy est séparée du coeur transactionnel

[ ] ImpairmentPolicy est séparée du coeur transactionnel

[ ] InventoryValuationPolicy est préparée

[ ] AccrualPolicy / ProvisionPolicy sont préparées

[ ] PolicyExecutionTrace est immutable

[ ] une policy ne peut pas poster directement une écriture

[ ] JournalEntryProposal est défini

[ ] AccountRole est distinct du code de compte

[ ] reference snapshot est conservé

[ ] observation externe est conservée lorsqu'elle influence le résultat

[ ] changement de méthode est versionné / audité

[ ] les tests P0 couvrent résolution, reconnaissance, mesure et fail-closed
```

---

# 142. Ordre d'implémentation recommandé

## Lot POL-00 - Primitives

```text
PolicyId
PolicyVersion
PolicyType
PolicyStatus
PolicyApplicability
PolicyContext
```

---

## Lot POL-01 - PolicySet

```text
AccountingPolicySet
PolicyBinding
activation
supersession
repository contract
```

---

## Lot POL-02 - Resolution

```text
PolicyResolutionService
priority
scope
ambiguity handling
```

---

## Lot POL-03 - Recognition

```text
RecognitionPolicy
RecognitionDecision
tests
```

---

## Lot POL-04 - Measurement

```text
MeasurementBasis
MeasurementPolicy
MeasurementResult
tests
```

---

## Lot POL-05 - Traceability

```text
PolicyExecutionTrace
reference snapshot
external observations
```

---

## Lot POL-06 - Entry Proposal

```text
AccountRole
AccountResolutionService
JournalEntryProposal
```

---

## Lot POL-07 - First Strategies

Premières stratégies techniques de démonstration :

```text
historical cost
straight-line depreciation
simple impairment
simple accrual
```

Elles ne doivent pas être présentées comme couverture réglementaire complète.

---

# 143. Démonstrateur P0

Scénario recommandé :

```text
1. Load reference snapshot

2. Create AccountingPolicySet

3. Bind:
      RecognitionPolicy
      HistoricalCostMeasurementPolicy
      StraightLineDepreciationPolicy

4. Create accounting event

5. Evaluate recognition

6. Measure initial amount

7. Generate JournalEntryProposal

8. Resolve CompanyAccount roles

9. Create JournalEntry

10. Validate

11. Post

12. Run depreciation for next period

13. Generate depreciation proposal

14. Validate / Post

15. Verify PolicyExecutionTrace
```

Ce scénario valide la séparation :

```text
Reference
-> Policy
-> Decision / Measurement
-> Entry Proposal
-> Accounting Core
-> Posting
```

---

# 144. Impacts sur le document suivant

Le prochain document devra détailler :

```text
05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md
```

Il devra notamment préciser :

```text
AccountingReferenceProvider
ReferenceCatalog
ReferenceStandard
ReferenceAccount
ReferenceSnapshot
effective plans
overlays
relations
crosswalks
concepts
reporting definitions
execution status of mappings
provenance
```

et la manière dont `Accounting Policies & Measurement` consomme ce contexte sans recopier les données réglementaires.

---

# 145. Conclusion

Le bounded context `Accounting Policies & Measurement` devient l'élément qui rend réellement possible un PyAccountingKit multi-référentiels.

Sans lui, le moteur serait condamné à accumuler :

```text
if standard == ...
if country == ...
if account.startswith(...)
```

Avec lui, l'architecture devient :

```text
Reference
    ->
Policy Resolution
    ->
Recognition
    ->
Measurement
    ->
JournalEntryProposal
    ->
Validation
    ->
Posting
```

Les principes majeurs sont :

```text
Reference != Policy

Recognition != Measurement

Measurement != Posting

Policy != Heuristic

Account Role != Account Code

Measurement Basis must be explicit

Policy execution must be traceable

Ambiguity must fail closed
```

Cette séparation permet ensuite d'ajouter :

```text
Fixed Assets
Inventory
Accruals & Provisions
Closing
Consolidation
```

sans rendre le coeur transactionnel dépendant d'un référentiel ou d'une méthode unique.

---

**Prochain document recommandé :**

```text
05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md
```
