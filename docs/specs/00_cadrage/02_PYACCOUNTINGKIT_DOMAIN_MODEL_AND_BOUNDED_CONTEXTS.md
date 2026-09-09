# 02 - PyAccountingKit - Modèle de domaine et Bounded Contexts

> **Projet** : PyAccountingKit  
> **Document** : `02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`  
> **Documents parents** :  
> - `00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`  
> - `01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`  
> **Statut** : P0.3 - Modèle de domaine enrichi avec Policies, Financial Analysis et futurs sous-domaines opérationnels
> **Langue** : Français  
> **Objet** : Définir le langage ubiquitaire, les sous-domaines, les bounded contexts, les agrégats, entités, value objects, services de domaine, événements et relations de contexte de PyAccountingKit, en intégrant explicitement `Accounting Policies & Measurement`, `Financial Analysis`, ainsi que les futurs contexts `Inventory`, `Fixed Assets`, `Accruals & Provisions` et `Consolidation`.

---

# 1. Résumé exécutif

PyAccountingKit doit être construit comme un **moteur comptable générique** dont le domaine est indépendant :

- des frameworks web ;
- de l'ORM ;
- du moteur de base de données ;
- d'un référentiel réglementaire particulier ;
- d'un format d'import particulier ;
- d'une application cliente particulière.

Le modèle de domaine s'appuie désormais sur quatre familles d'apports :

```text
regulatory-accounting-data-framework
        = source de vérité réglementaire

cfa_fra_django_mvp_sprint_7
        = référence fonctionnelle exécutable

Comptabilité générale - Système français et normes IFRS
        = source doctrinale comptable

Maxi fiches de Gestion financière de l'entreprise
        = source doctrinale d'analyse financière
```

La macro-chaîne métier est :

```text
Reference
    ->
Accounting Policies & Measurement
    ->
Company Accounting Model
    ->
Journal / Posting
    ->
Ledger
    ->
Financial / Regulatory Reporting
    ->
Financial Analysis
```

Le modèle cible conserve le principe éprouvé selon lequel le coeur comptable canonique repose principalement sur :

```text
AccountingEntity
FiscalYear
AccountingPeriod
CompanyChartOfAccounts
CompanyAccount
Journal
JournalEntry
JournalEntryLine
```

et que :

```text
General Ledger
Trial Balance
Financial Statements
Financial Indicators
```

sont des **projections calculées** et non des sources primaires indépendantes.

Cette révision introduit explicitement deux bounded contexts structurants :

```text
Accounting Policies & Measurement
Financial Analysis
```

et prépare quatre bounded contexts spécialisés :

```text
Inventory
Fixed Assets
Accruals & Provisions
Consolidation
```

Ces quatre contexts futurs ne doivent pas être implémentés prématurément dans le coeur P0, mais leurs frontières doivent être connues dès maintenant pour éviter de disperser leurs règles dans `JournalEntry`, `PostingService` ou `FinancialStatementEngine`.

---

# 2. Objectifs du document

Ce document doit répondre aux questions suivantes :

```text
Quels sont les sous-domaines de PyAccountingKit ?

Quels sont les bounded contexts ?

Qui possède quelle donnée ?

Quels objets sont des Aggregate Roots ?

Quels objets sont des Entities ?

Quels objets sont des Value Objects ?

Quelles règles doivent être protégées à l'intérieur d'un agrégat ?

Quelles règles nécessitent un Domain Service ?

Quelles interactions passent par des Application Services ?

Quels événements de domaine doivent être produits ?

Quels concepts viennent de regulatory-accounting-data-framework ?

Quelles règles relèvent de `Accounting Policies & Measurement` plutôt que du Posting Engine ?

Quels calculs relèvent de `Financial Analysis` plutôt que du reporting comptable ?

Quelles frontières faut-il préparer pour Inventory, Fixed Assets, Accruals & Provisions et Consolidation ?

Quels concepts sont extraits de CFA FRA ?

Quelles frontières doivent empêcher le couplage à Django ?
```

---

# 3. Principes de modélisation

## DDD-001 - Un modèle métier, pas un modèle ORM

Les classes du domaine ne doivent pas être conçues comme des tables.

Eviter :

```text
1 classe domaine
=
1 table
=
1 formulaire
=
1 endpoint
```

Une entité DDD existe parce qu'elle possède :

- une identité ;
- un cycle de vie ;
- des invariants ;
- un comportement métier.

---

## DDD-002 - Agrégats petits et transactionnels

Un agrégat doit protéger les invariants qui nécessitent une cohérence atomique.

Exemple :

```text
JournalEntry
    |
    +-- JournalEntryLine
    +-- JournalEntryLine
```

est un agrégat naturel car :

```text
SUM(debit) = SUM(credit)
```

doit être vérifié sur l'ensemble des lignes d'une même écriture.

En revanche :

```text
CompanyChartOfAccounts
    +-- 100 000 comptes
```

ne doit pas être chargé comme un seul gros agrégat.

---

## DDD-003 - Les projections ne sont pas des agrégats

Les objets suivants sont des read models ou résultats de query services :

```text
GeneralLedger
TrialBalance
IncomeStatement
BalanceSheet
CashFlowStatement
```

Ils peuvent être matérialisés pour la performance, mais ne deviennent pas pour autant la source de vérité.

---

## DDD-004 - Les standards réglementaires sont externes au coeur transactionnel

Les données de référence :

```text
ReferenceStandard
ReferenceAccount
ReferenceStatementDefinition
ReferenceConcept
StandardRelation
Crosswalk
```

sont consommées depuis `regulatory-accounting-data-framework`.

Elles ne doivent pas être confondues avec :

```text
CompanyAccount
CompanyStatementMapping
JournalEntry
```

---

## DDD-005 - Les mappings sont des objets métier explicites

Le domaine distingue au minimum :

```text
RegulatoryAccountBinding
```

qui relie un compte entreprise à une référence comptable,

et :

```text
StatementAccountMapping
```

qui relie un compte ou un solde à une ligne d'état financier.

---

## DDD-006 - Les corrections comptables sont append-oriented

Une écriture postée est immuable.

```text
POSTED
  |
  +--> Reversal Entry
  |
  +--> Replacement Entry
```

---


## DDD-007 - Recognition, Measurement, Posting, Presentation et Analysis sont distincts

Le modèle doit distinguer :

```text
Recognition
    = faut-il comptabiliser ?

Measurement
    = pour quel montant ?

Posting
    = comment l'écriture est-elle rendue définitive ?

Presentation
    = où le solde est-il présenté ?

Analysis
    = quel indicateur ou diagnostic en dérive ?
```

Ces responsabilités ne doivent pas être fusionnées dans un même service.

---

## DDD-008 - Les policies sont versionnées et contextualisées

Une policy comptable doit pouvoir dépendre de :

```text
standard
edition
jurisdiction
sector
entity
effective date
asset / transaction category
```

Une méthode comptable particulière ne devient pas un invariant universel.

---

## DDD-009 - Financial Analysis est downstream et read-only

Le bounded context `Financial Analysis` consomme :

```text
Ledger
Trial Balance
Financial Statements
```

mais ne modifie jamais :

```text
JournalEntry
JournalEntryLine
CompanyAccount
AccountingPeriod
```

---

## DDD-010 - Les futurs domaines opérationnels ne doivent pas contaminer le coeur

Les règles propres aux :

```text
stocks
immobilisations
provisions
accruals
consolidation
```

ne doivent pas être codées en dur dans les agrégats génériques.

Elles appartiennent à des bounded contexts spécialisés ou à des policies explicites.

---

# 4. Classification des sous-domaines

PyAccountingKit est découpé en trois catégories DDD.

## 4.1 Core Domains

Ils portent la valeur principale du framework :

```text
Accounting Policies & Measurement
Company Chart of Accounts
Journal & Entries
Posting & Reversal
Ledger & Balances
```

`Accounting Policies & Measurement` devient un Core Domain car le moteur doit pouvoir appliquer des méthodes comptables différentes sans dupliquer le coeur transactionnel.

---

## 4.2 Supporting Domains

Ils soutiennent le coeur :

```text
Accounting Periods & Closing
Accounting Imports
Accounting Controls
Audit & Traceability
Financial Statements
Regulatory Reporting
Financial Analysis
Reconciliation
```

`Financial Analysis` est un supporting domain downstream : il enrichit l'exploitation des données sans modifier la comptabilité.

---

## 4.3 Future Specialized Domains

Ces contexts sont préparés architecturalement mais ne sont pas requis dans le premier core stable :

```text
Inventory
Fixed Assets
Accruals & Provisions
Consolidation
```

Ils pourront évoluer vers des packages ou modules spécialisés lorsque leur richesse fonctionnelle le justifiera.

---

## 4.4 Generic / Integration Domains

```text
Accounting Identity
Money / Currency
Clock
Typed IDs
Reference Provider
Object Storage
Persistence Ports
```

---

# 5. Carte globale des bounded contexts

```text
+---------------------------+
| Accounting Identity       |
+-------------+-------------+
              |
              v
+---------------------------+       +---------------------------+
| Accounting Reference Data |------>| Accounting Policies &     |
| standards / accounts      |       | Measurement               |
+-------------+-------------+       +-------------+-------------+
              |                                   |
              +----------------+------------------+
                               |
                               v
                    +---------------------------+
                    | Company Chart of Accounts |
                    +-------------+-------------+
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
          +-------------------+      +----------------------+
          | Accounting       |      | Journal & Entries    |
          | Periods & Closing|----->| Posting & Reversal   |
          +-------------------+      +----------+-----------+
                                               |
                                               v
                                    +----------------------+
                                    | Ledger & Balances    |
                                    +----+------------+----+
                                         |            |
                                         v            v
                               +--------------+   +------------------+
                               | Controls     |   | Financial        |
                               | Audit        |   | Statements       |
                               +--------------+   +--------+---------+
                                                           |
                                            +--------------+--------------+
                                            |                             |
                                            v                             v
                                  +-------------------+        +-------------------+
                                  | Regulatory        |        | Financial Analysis|
                                  | Reporting         |        | SIG / CAF / BFR   |
                                  +-------------------+        +-------------------+

Accounting Imports ---> Journal & Entries

Future specialized contexts:
Inventory / Fixed Assets / Accruals & Provisions
    ---> generate or enrich accounting events / entries through explicit ports

Consolidation
    <--- consumes entity-level reporting / mappings / reference data

Reconciliation
    <--- consumes ledger + external data

Audit & Traceability observes significant mutations across contexts.
```

---

# 6. Bounded Context 1 - Accounting Identity

## 6.1 Responsabilité

Identifier l'entité comptable à laquelle appartiennent :

- les plans ;
- les exercices ;
- les journaux ;
- les écritures ;
- les imports ;
- les rapports ;
- les snapshots.

Le concept générique retenu dans PyAccountingKit est :

```text
AccountingEntity
```

Une application Django peut continuer à utiliser :

```text
Organization
```

comme traduction locale.

---

## 6.2 Aggregate Root - `AccountingEntity`

Responsabilités :

- identité stable ;
- nom ;
- devise fonctionnelle ;
- juridiction éventuelle ;
- état actif/inactif ;
- paramètres comptables de haut niveau.

Exemple conceptuel :

```python
@dataclass
class AccountingEntity:
    id: AccountingEntityId
    name: str
    functional_currency: Currency
    country_code: str | None
    status: AccountingEntityStatus
```

---

## 6.3 Value Objects

```text
AccountingEntityId
LegalName
RegistrationNumber
CountryCode
Currency
AccountingEntityStatus
```

---

## 6.4 Invariants

```text
- l'identité est stable ;
- une entité inactive ne peut pas recevoir de nouvelles opérations si la policy l'interdit ;
- la devise fonctionnelle doit être valide ;
- toutes les écritures sont scopées par AccountingEntityId.
```

---

## 6.5 Traduction CFA FRA

```text
Organization
    ->
AccountingEntity
```

Le scoping `organization_id` observé dans CFA FRA devient une exigence de frontière sur les repositories et queries.

---

# 7. Bounded Context 2 - Accounting Reference Data

## 7.1 Responsabilité

Représenter en lecture les artefacts réglementaires fournis par `regulatory-accounting-data-framework`.

Ce bounded context est principalement **read-only** du point de vue PyAccountingKit.

---

## 7.2 Concepts principaux

```text
ReferenceStandard
ReferenceEdition
ReferenceDatasetVersion
ReferenceChart
ReferenceAccount
ReferenceStatementDefinition
ReferenceStatementLine
ReferenceConcept
StandardRelation
ReferenceCrosswalk
AccountingReferenceSnapshot
```

---

## 7.3 `ReferenceStandard`

Représente :

```text
standard_id
edition
jurisdiction
dataset_version
effective dates
metadata
```

Exemples :

```text
fr-pcg / 2026
ohada-syscohada / 2017
fr-nonprofit / 2026
ohada-ebnl / 2023
```

---

## 7.4 `ReferenceAccount`

Exemple conceptuel :

```python
@dataclass(frozen=True)
class ReferenceAccount:
    id: ReferenceAccountId
    standard: StandardId
    edition: StandardEdition
    code: ReferenceAccountCode
    label: str
    parent_id: ReferenceAccountId | None
    is_leaf: bool
    metadata: Mapping[str, object]
```

---

## 7.5 Nature des objets

Les objets de ce context sont principalement :

```text
Immutable Reference Objects
```

Ils ne suivent pas le cycle de vie des écritures.

---

## 7.6 Source d'identité

Les IDs externes doivent être conservés.

Exemple :

```text
account:fr-pcg:2026:512
```

PyAccountingKit peut les encapsuler :

```python
ReferenceAccountId("account:fr-pcg:2026:512")
```

sans les remplacer.

---

## 7.7 Anti-Corruption Layer

Le domaine ne dépend pas du JSON brut.

```text
JSON datasets
    |
    v
Regulatory Adapter
    |
    v
Reference DTO
    |
    v
Reference Domain Model
```

Ainsi un changement du format physique ne doit pas contaminer les autres contexts.

---

# 8. Bounded Context 3 - Accounting Policies & Measurement

## Responsabilité

Représenter et exécuter les méthodes comptables qui déterminent :

```text
si un événement doit être reconnu
pour quel montant
selon quelle base de mesure
avec quelle méthode d'amortissement / dépréciation / provision
à quelle date d'effet
selon quel standard / contexte
```

Ce bounded context se situe entre :

```text
Accounting Reference Data
        |
        v
Accounting Policies & Measurement
        |
        v
Accounting Core
```

---

## Aggregate Root - `AccountingPolicySet`

Un `AccountingPolicySet` représente l'ensemble versionné des policies applicables à une entité ou un ledger.

```text
AccountingPolicySet
|
+-- id
+-- entity_id
+-- reference_snapshot
+-- version
+-- effective_from
+-- effective_to
+-- status
+-- policy_bindings
```

Il ne doit pas charger toutes les policies comme un énorme graphe si celles-ci sont nombreuses. Les bindings peuvent être référencés et résolus via repository/registry.

---

## Concepts principaux

```text
AccountingPolicySet
RecognitionPolicy
MeasurementPolicy
DepreciationPolicy
ImpairmentPolicy
InventoryValuationPolicy
AccrualPolicy
ProvisionPolicy
RoundingPolicy
PolicyApplicability
PolicyExecutionTrace
MeasurementBasis
```

---

## `RecognitionPolicy`

Question métier :

```text
Cet événement économique doit-il donner lieu à comptabilisation ?
```

Résultat conceptuel :

```text
RecognitionDecision
    recognized: bool
    recognition_date
    target_category
    rationale / provenance
```

---

## `MeasurementPolicy`

Question métier :

```text
Pour quel montant l'élément doit-il être comptabilisé ?
```

Elle doit pouvoir exposer :

```text
measurement basis
inputs
calculation
currency
rounding
result
effective context
```

---

## `PolicyApplicability`

Une policy doit déclarer sa portée :

```text
GLOBAL
STANDARD_SPECIFIC
JURISDICTION_SPECIFIC
SECTOR_SPECIFIC
COMPANY_SPECIFIC
ACCOUNT_CLASS_SPECIFIC
ASSET_CATEGORY_SPECIFIC
TIME_BOUND
```

---

## Value Object - `PolicyExecutionTrace`

```text
PolicyExecutionTrace
|
+-- policy_id
+-- policy_version
+-- evaluated_at
+-- effective_date
+-- inputs
+-- result
+-- generated_entry_id?
+-- reference_snapshot
+-- metadata
```

Cette trace soutient :

- audit ;
- reproductibilité ;
- golden tests ;
- migration de policies ;
- explication des montants générés.

---

## Invariants

```text
- une policy exécutable possède une version ;
- une policy doit déclarer sa portée ;
- une policy expirée ne doit pas être appliquée hors de sa période ;
- une policy dépendante d'un standard doit être cohérente avec le ReferenceSnapshot ;
- une policy ne peut pas modifier directement une écriture POSTED ;
- toute écriture automatisée par policy passe par les mêmes règles de validation/posting que les écritures manuelles.
```

---

## Domain Events

```text
AccountingPolicySetCreated
AccountingPolicySetActivated
AccountingPolicySetSuperseded
PolicyEvaluated
PolicyGeneratedAccountingEntry
```

---

## Relations

```text
Reference Data
    -> fournit le contexte normatif

Company / Ledger
    -> sélectionne AccountingPolicySet

Policies
    -> produisent décisions / mesures / propositions d'écritures

Journal & Entries
    -> reste responsable de l'écriture comptable

Audit
    -> conserve PolicyExecutionTrace
```

---

# 9. Bounded Context 4 - Company Chart of Accounts

## 9.1 Responsabilité

Créer et gérer le plan comptable réellement utilisable par une organisation.

Il constitue la frontière entre :

```text
référentiel réglementaire
```

et :

```text
comptabilité opérationnelle
```

---

## 9.2 Aggregate Root - `CompanyChartOfAccounts`

Le chart ne doit pas contenir tous les comptes en mémoire comme enfants d'agrégat.

Il porte surtout :

```text
id
accounting_entity_id
name
reference_snapshot
version
status
generation_profile
```

---

## 9.3 Aggregate Root - `CompanyAccount`

Chaque compte opérationnel est un aggregate root distinct.

Raisons :

- grand volume possible ;
- activation/désactivation indépendante ;
- modification indépendante du libellé ;
- hiérarchie pouvant être profonde ;
- besoin de requêtes sélectives ;
- besoin d'éviter un agrégat chart géant.

---

## 9.4 `CompanyAccount`

```python
@dataclass
class CompanyAccount:
    id: AccountId
    entity_id: AccountingEntityId
    chart_id: CompanyChartId
    code: AccountCode
    label: str
    account_type: AccountType
    normal_balance: DebitCredit
    status: AccountStatus
    parent_account_id: AccountId | None
    reference_binding: RegulatoryAccountBinding | None
```

---

## 9.5 Value Objects

```text
CompanyChartId
AccountId
AccountCode
AccountType
AccountKind
AccountStatus
NormalBalance
RegulatoryAccountBinding
```

---

## 9.6 `RegulatoryAccountBinding`

```python
@dataclass(frozen=True)
class RegulatoryAccountBinding:
    reference_account_id: ReferenceAccountId
    binding_type: BindingType
    confidence: Decimal | None
    validated: bool
```

Le binding n'est pas nécessairement un aggregate root.

Il est une propriété métier du compte ou une relation dédiée selon le mode de persistance.

---

## 9.7 Invariants

```text
- code unique dans un plan ;
- code conforme à AccountCodePolicy ;
- parent dans le même plan ;
- pas de cycle hiérarchique ;
- compte postable uniquement si la policy l'autorise ;
- compte désactivé non utilisable pour une nouvelle ligne ;
- le binding doit viser un compte de référence connu lorsqu'il est présent.
```

---

# 10. Politiques de codification

Le plan entreprise doit être indépendant d'une longueur unique.

Concepts :

```text
AccountCodePolicy
AccountCodeSchema
AccountCodeSegment
CompanyAccountingProfile
ChartGenerationMode
```

Modes :

```text
REFERENCE_ONLY
PAD_TO_LENGTH
TEMPLATE_EXPANSION
CUSTOM
```

Exemple :

```text
ReferenceAccount 512
       |
       +--> 512001
       +--> 51200001
       +--> 512000001
```

Le code opérationnel n'est jamais utilisé comme identité réglementaire.

---


Les conventions nationales de codification éventuellement observées dans un référentiel restent des `ReferenceSpecificAccountCodeRule`.

Exemple conceptuel :

```text
PCG-specific numbering convention
    !=
universal Account invariant
```

---

# 11. Comptes collectifs et auxiliaires

Le modèle doit permettre :

```text
collective account
    +
auxiliary account
```

Deux stratégies :

```text
SUBLEDGER
EXTENDED_ACCOUNT_CODE
```

et éventuellement :

```text
HYBRID
```

Concepts possibles :

```text
AuxiliaryAccount
AuxiliaryAccountId
AuxiliaryAccountingPolicy
CounterpartyId
```

La conception détaillée sera finalisée dans le document 05.

---

# 12. Bounded Context 5 - Accounting Periods & Closing

## 12.1 Responsabilité

Gérer :

- exercices ;
- périodes ;
- ouverture ;
- fermeture ;
- verrouillage ;
- clôture ;
- réouverture contrôlée.

---

## 12.2 Aggregate Root - `FiscalYear`

Responsabilités :

```text
start_date
end_date
status
accounting_entity_id
```

---

## 12.3 Aggregate Root - `AccountingPeriod`

Plutôt que de forcer toutes les périodes comme entities d'un gros agrégat `FiscalYear`, PyAccountingKit peut traiter `AccountingPeriod` comme aggregate root indépendant relié à `FiscalYearId`.

Motifs :

- verrouillage concurrent ;
- fermeture indépendante ;
- requêtes fréquentes ;
- contrôle de posting ;
- changement de statut transactionnel ciblé.

---

## 12.4 Value Objects

```text
FiscalYearId
AccountingPeriodId
FiscalYearStatus
AccountingPeriodStatus
PeriodNumber
DateRange
```

---

## 12.5 Statuts

Base proposée :

```text
OPEN
CLOSING
CLOSED
LOCKED
```

La sémantique exacte sera figée dans le document des invariants.

---

## 12.6 Invariants

```text
- start_date <= end_date ;
- une période appartient à un exercice ;
- une date comptable doit tomber dans la période ciblée ;
- une période CLOSED/LOCKED refuse le posting ;
- fermeture et réouverture sont auditées ;
- un closing ne peut être validé si les contrôles bloquants échouent.
```

---

# 13. Closing comme orchestration

`Closing` ne doit pas nécessairement devenir un gros aggregate.

Il s'agit surtout d'un processus métier orchestrant :

```text
Controls
    |
    v
Generate closing entries
    |
    v
Validate
    |
    v
Post
    |
    v
Close period
```

Concepts :

```text
ClosingService
ClosingPolicy
ClosingRun
OpeningBalanceService
```

Un `ClosingRun` peut devenir aggregate root si l'on doit tracer un workflow de sign-off complexe.

---

# 14. Bounded Context 6 - Journal & Entries

## 14.1 Responsabilité

C'est le coeur transactionnel du moteur.

Il porte :

```text
Journal
JournalEntry
JournalEntryLine
```

---

## 14.2 Aggregate Root - `Journal`

Responsabilités :

```text
id
entity_id
code
label
journal_type
status
numbering_policy
```

Types possibles :

```text
SALES
PURCHASE
BANK
CASH
PAYROLL
TAX
GENERAL
OPENING
```

La liste peut être extensible.

---

## 14.3 Aggregate Root - `JournalEntry`

C'est l'agrégat central.

```text
JournalEntry
    |
    +-- JournalEntryLine
    +-- JournalEntryLine
    +-- ...
```

Toutes les lignes nécessaires à la validation de l'écriture appartiennent à l'agrégat.

---

## 14.4 `JournalEntry`

Attributs conceptuels :

```text
JournalEntryId
AccountingEntityId
JournalId
AccountingPeriodId
EntryNumber
EntryType
AccountingDate
PostingDate
DocumentReference
Description
EntryStatus
SourceReference
ReversalOf
lines
```

---

## 14.5 Entity - `JournalEntryLine`

Une ligne possède une identité locale ou globale selon la stratégie de persistance.

Attributs :

```text
JournalEntryLineId
AccountId
DebitAmount
CreditAmount
Description
CounterpartyId?
CostCenterId?
CashFlowTag?
SourceReference?
metadata?
```

---

## 14.6 Value Object - `PostingAmount`

Une modélisation utile consiste à éviter deux montants mutables indépendants.

Exemple conceptuel :

```python
Debit(Money(...))
Credit(Money(...))
```

ou :

```python
PostingAmount(side=DEBIT, amount=Money(...))
```

Cela rend structurellement impossible :

```text
debit > 0 AND credit > 0
```

sur la même ligne.

---

# 15. Invariants de `JournalEntry`

Invariants de base :

```text
- au moins deux lignes pour validation ;
- chaque ligne a un montant strictement positif ;
- une ligne est soit débit soit crédit ;
- comptes appartenant à la même AccountingEntity ;
- comptes actifs ;
- période compatible ;
- total débit = total crédit ;
- montant total non nul ;
- statut cohérent avec l'opération demandée.
```

Ces règles seront détaillées dans :

```text
03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md
```

---

# 16. Cycle de vie de l'écriture

```text
DRAFT
  |
  | validate
  v
VALIDATED
  |
  | post
  v
POSTED
  |
  | reverse
  v
REVERSED
```

Transition interdite :

```text
DRAFT -> POSTED
```

Correction :

```text
POSTED original
      |
      v
POSTED reversal
      |
      v
new correct entry
```

---

# 17. Domain Events - Journal & Entries

Evénements initiaux :

```text
JournalEntryCreated
JournalEntryUpdated
JournalEntryValidated
JournalEntryPosted
JournalEntryReversed
JournalEntryRejected
```

Payload minimal :

```text
event_id
occurred_at
entity_id
journal_entry_id
actor_id?
correlation_id?
```

Les Domain Events ne remplacent pas l'AuditEvent complet.

---

# 18. Bounded Context 7 - Posting & Reversal

## 18.1 Responsabilité

Le posting n'est pas une simple modification de champ.

Il représente une transition métier contrôlée.

---

## 18.2 Domain Service - `EntryValidationService`

Utilisé lorsqu'une validation nécessite plusieurs collaborators :

```text
AccountRepository
AccountingPeriodRepository
JournalRepository
```

Les invariants purement internes restent dans `JournalEntry`.

---

## 18.3 Domain/Application Service - `PostingService`

Pseudo-flux :

```text
load entry
    |
    v
ensure VALIDATED
    |
    v
ensure journal active
    |
    v
ensure period open
    |
    v
ensure accounts valid
    |
    v
ensure balanced
    |
    v
transition POSTED
```

La transaction appartient à la couche application via `UnitOfWork`.

---

## 18.4 Domain/Application Service - `ReversalService`

Responsabilités :

```text
- refuser reversal d'une écriture non postée ;
- choisir une date/période autorisée ;
- créer une nouvelle écriture miroir ;
- inverser débit/crédit ;
- conserver reversal_of ;
- poster selon policy ;
- marquer l'originale comme REVERSED si le modèle retenu l'exige.
```

---

# 19. Concurrence autour des écritures

Le domaine exprime :

```text
expected current state
```

et l'adapter garantit l'atomicité.

Cas :

```text
VALIDATED -> POSTED
```

ne peut se produire deux fois.

Ports possibles :

```text
JournalEntryRepository.get_for_update(...)
VersionedEntity / revision
UnitOfWork
```

La stratégie peut être :

```text
pessimistic lock
optimistic concurrency
```

sans modifier le domaine.

---

# 20. Bounded Context 8 - Ledger & Balances

## 20.1 Responsabilité

Produire les projections comptables issues des lignes postées.

Il est volontairement séparé du write model.

---

## 20.2 Pas d'Aggregate Root `GeneralLedger`

`GeneralLedger` est un résultat de query.

Concepts :

```text
LedgerQuery
LedgerRow
AccountLedger
RunningBalance
TrialBalanceQuery
TrialBalanceRow
```

---

## 20.3 `LedgerRow`

Peut exposer :

```text
posting_date
entry_number
journal
account
description
debit
credit
signed_amount
running_balance
source_reference
```

---

## 20.4 `TrialBalance`

Types :

```text
BEFORE_ADJUSTMENTS
ADJUSTED
POST_CLOSING
```

Une `TrialBalance` est un résultat immutable d'une query pour :

```text
entity
date range
variant
filters
```

---

## 20.5 Invariant de projection

```text
SUM(trial_balance.debit)
=
SUM(trial_balance.credit)
```

si les écritures sources satisfont les invariants.

Un écart indique :

- corruption ;
- filtre incohérent ;
- bug de projection ;
- donnée externe non qualifiée.

---

# 21. Read Models du Ledger

```text
JournalReport
GeneralLedgerView
TrialBalanceView
AccountBalance
PeriodBalance
```

Ces objets peuvent être :

- calculés à la volée ;
- cachés ;
- matérialisés ;
- pré-agrégés.

Mais :

```text
source_of_truth = POSTED JournalEntryLine
```

---

# 22. Bounded Context 9 - Accounting Imports

## 22.1 Responsabilité

Transformer une source externe en écritures comptables tout en conservant la provenance.

Pipeline générique :

```text
External Source
       |
       v
ImportBatch
       |
       v
RawRecord
       |
       v
Validation
       |
       v
Mapping
       |
       v
NormalizedEntry
       |
       v
JournalEntry
```

---

## 22.2 Aggregate Root - `AccountingImportBatch`

Attributs conceptuels :

```text
ImportBatchId
AccountingEntityId
FiscalYearId?
source_type
source_name
checksum
status
created_at
source_metadata
```

---

## 22.3 Statuts

Exemple générique :

```text
UPLOADED
PARSED
MAPPING
READY
IMPORTING
IMPORTED
FAILED
```

Le détail peut dépendre de l'adapter.

---

## 22.4 Raw records

Les raw records peuvent être volumineux.

Ils ne doivent pas tous devenir des entities chargées dans l'agrégat `AccountingImportBatch`.

Modèle :

```text
ImportBatch
    |
    +--> RawRecordRepository
```

Le batch protège le workflow ; les records sont stockés séparément.

---

## 22.5 Value Objects

```text
SourceReference
SourceLineNumber
SourceRecordKey
ContentChecksum
NormalizedEntryKey
ImportStatus
```

---

# 23. FEC comme Anti-Corruption Adapter

Le FEC appartient à l'integration layer.

Concepts spécifiques :

```text
FECParser
FECRawRecord
FECValidator
FECAccountMapping
FECJournalMapping
FECNormalizer
```

Ces objets traduisent le FEC vers le langage PyAccountingKit.

```text
CompteNum
    ->
AccountCode / SourceAccountCode

JournalCode
    ->
JournalCode

Debit/Credit
    ->
PostingAmount
```

Le domaine central ne connaît pas les noms de colonnes FEC.

---

# 24. Idempotence des imports

Un import peut être identifié par :

```text
AccountingEntityId
+
source checksum
+
fiscal year
```

ou une clé externe.

Le mécanisme exact est une policy :

```text
ImportIdempotencyPolicy
```

Domain event :

```text
AccountingImportCompleted
AccountingImportFailed
```

---

# 25. Bounded Context 10 - Accounting Controls

## 25.1 Responsabilité

Exécuter des règles de contrôle explicites sur différents contexts.

Exemples issus de la référence fonctionnelle :

```text
ENTRY_BALANCED
ACCOUNT_EXISTS
ACCOUNT_ACTIVE
PERIOD_OPEN
DEBIT_OR_CREDIT_ONLY
ENTRY_HAS_AT_LEAST_TWO_LINES
TRIAL_BALANCE_BALANCED
BALANCE_SHEET_BALANCED
CASHFLOW_RECONCILED
TEMPORARY_ACCOUNTS_CLOSED
```

---

## 25.2 `AccountingControl`

Abstraction :

```python
class AccountingControl(Protocol):
    code: ControlCode
    severity: ControlSeverity

    def evaluate(self, context) -> ControlResult:
        ...
```

---

## 25.3 Value Object - `ControlResult`

```text
control_code
severity
status
expected
actual
details
evidence
```

Le résultat est immuable.

---

## 25.4 Aggregate Root - `ControlRun`

Pour une exécution groupée :

```text
ControlRun
    |
    +-- scope
    +-- started_at
    +-- completed_at
    +-- results
    +-- status
```

Pour de grands volumes, les résultats peuvent être externalisés et référencés.

---

## 25.5 Severities

Base proposée :

```text
INFO
WARNING
ERROR
BLOCKING
```

---

# 26. Bounded Context 11 - Audit & Traceability

## 26.1 Responsabilité

Tracer les mutations significatives.

L'audit est transversal mais possède son propre modèle.

---

## 26.2 `AuditEvent`

Objet append-only :

```text
AuditEventId
AccountingEntityId
action
entity_type
entity_id
actor
occurred_at
before
after
metadata
source
correlation_id
request_id?
```

---

## 26.3 Evénements à auditer

```text
ACCOUNT_CREATED
ACCOUNT_UPDATED
ACCOUNT_DISABLED

ENTRY_CREATED
ENTRY_UPDATED
ENTRY_VALIDATED
ENTRY_POSTED
ENTRY_REVERSED

PERIOD_CLOSED
PERIOD_REOPENED

IMPORT_CREATED
IMPORT_EXECUTED

REFERENCE_LOADED
MAPPING_UPDATED

REPORT_GENERATED
REGULATORY_EXPORT_CREATED
```

---

## 26.4 AuditEvent vs DomainEvent

```text
DomainEvent
    = notification métier interne

AuditEvent
    = preuve persistante destinée à l'audit
```

Un DomainEvent peut déclencher un AuditEvent, mais les deux concepts restent distincts.

---

# 27. Bounded Context 12 - Financial Statements

## 27.1 Responsabilité

Transformer les balances comptables en états financiers structurés.

Pipeline :

```text
Trial Balance
      |
      +
StatementAccountMapping
      |
      v
StatementDefinition
      |
      v
FinancialStatement
```

---

## 27.2 `StatementDefinition`

Modèle de structure :

```text
StatementDefinition
    |
    +-- StatementLine
            |
            +-- child StatementLine
```

Types :

```text
INCOME_STATEMENT
BALANCE_SHEET
CASH_FLOW_STATEMENT
STATEMENT_OF_CHANGES_IN_EQUITY
```

Le support initial peut se limiter aux trois premiers.

---

## 27.3 `StatementLine`

Attributs :

```text
StatementLineId
code
label
parent_id
order
role
calculation
```

---

## 27.4 Aggregate Root - `StatementMappingSet`

Un ensemble versionné de mappings :

```text
StatementMappingSet
    |
    +-- mapping version
    +-- statement definition
    +-- entity scope
    +-- mappings
```

---

## 27.5 `StatementAccountMapping`

```text
AccountId / selector
StatementLineId
multiplier
mapping_type
confidence
validated_by?
validated_at?
notes?
```

Types :

```text
MANUAL
RULE
SUGGESTED
```

Une suggestion ne doit pas devenir exécutable sans policy explicite.

---

# 28. Résultats d'états financiers

Les états générés sont des Value Objects / read models :

```text
IncomeStatement
BalanceSheet
CashFlowStatement
```

Ils ne sont pas des aggregates transactionnels.

Ils doivent permettre le drill-down :

```text
StatementLine
    |
    v
TrialBalanceRow
    |
    v
LedgerRow
    |
    v
JournalEntry
```

---

# 29. Bounded Context 13 - Regulatory Reporting

## 29.1 Responsabilité

Transformer un état financier canonique ou interne vers une présentation réglementaire cible.

---

## 29.2 Concepts

```text
RegulatoryReportingProfile
RegulatoryStatementMapping
RegulatoryMappingSet
RegulatoryControl
ReportSnapshot
ExportDefinition
```

---

## 29.3 Aggregate Root - `RegulatoryReportingProfile`

Porte :

```text
AccountingEntityId
target standard
target edition
reference snapshot
mapping set version
status
```

---

## 29.4 `RegulatoryStatementMapping`

Relie :

```text
source StatementLine
       |
       v
target ReferenceStatementLine
```

Attributs :

```text
multiplier
mapping_type
confidence
validation_status
notes
```

---

## 29.5 Aggregate Root - `ReportSnapshot`

Objet immuable représentant une publication.

```text
ReportSnapshot
|
+-- entity
+-- period
+-- chart version
+-- accounting reference snapshot
+-- mapping versions
+-- statement definitions
+-- line values
+-- warnings
+-- controls
+-- comparatives
+-- generated_at
+-- checksum
```

Une fois finalisé :

```text
ReportSnapshot = immutable
```

---

# 30. Bounded Context 14 - Financial Analysis

## Responsabilité

Transformer des projections comptables en indicateurs financiers explicables.

```text
Ledger
    ->
Trial Balance
    ->
Financial Statements
    ->
Financial Analysis
```

Il s'agit d'un **read-side pur**.

---

## Concepts principaux

```text
FinancialAnalysisDefinition
FinancialIndicatorDefinition
IndicatorValue
RatioDefinition
RatioValue
FunctionalBalanceDefinition
FinancialScoreDefinition
FinancialScoreResult
FinancialDiagnostic
AnalysisSnapshot
```

---

## `FinancialIndicatorDefinition`

```text
FinancialIndicatorDefinition
|
+-- code
+-- label
+-- category
+-- computation_strategy
+-- dependencies
+-- version
+-- applicability
+-- provenance
```

Exemples :

```text
MARGIN
VALUE_ADDED
EBE
EBITDA
CAF
FRNG
BFR
NET_TREASURY
NET_MARGIN
CURRENT_RATIO
```

---

## SIG

Le bounded context doit pouvoir représenter des définitions versionnées de :

```text
marge commerciale
production
valeur ajoutée
EBE
résultat d'exploitation
résultat courant avant impôt
résultat exceptionnel
résultat net
```

Ces définitions ne sont pas des invariants universels.

---

## CAF

La CAF peut disposer de plusieurs stratégies de calcul :

```text
ADDITIVE
SUBTRACTIVE
CUSTOM
```

Le résultat doit conserver la stratégie utilisée.

---

## Analyse fonctionnelle

Concept :

```text
FunctionalBalance
|
+-- StableUses
+-- StableResources
+-- OperatingCurrentAssets
+-- OperatingCurrentLiabilities
+-- NonOperatingCurrentAssets
+-- NonOperatingCurrentLiabilities
+-- TreasuryAssets
+-- TreasuryLiabilities
```

Indicateurs dérivés :

```text
FRNG
BFRE
BFRHE
BFR
NetTreasury
```

---

## Ratios

Familles :

```text
ACTIVITY
PROFITABILITY
LIQUIDITY
CAPITAL_STRUCTURE
CASH_FLOW
```

Un `RatioValue` doit conserver :

```text
numerator
denominator
period
unit
definition_version
source_snapshot
```

---

## Scores et diagnostics

```text
FinancialScoreDefinition
FinancialScoreResult
FinancialDiagnostic
```

Un score n'est jamais une règle comptable normative.

---

## Aggregate Root - `AnalysisSnapshot`

Un snapshot analytique finalisé peut conserver :

```text
entity
period
source report snapshot / trial balance snapshot
indicator definition versions
ratio definition versions
values
diagnostics
generated_at
checksum
```

Il est immutable une fois finalisé.

---

## Drill-down

```text
IndicatorValue
    |
    v
Statement / Trial Balance components
    |
    v
Ledger rows
    |
    v
JournalEntryLine
```

---

## Frontière corporate finance

Hors coeur initial :

```text
VAN / NPV
TRI / IRR
WACC
investment decision
financing strategy
enterprise valuation
Monte Carlo investment risk
```

Ces capacités pourront être fournies par extension ou framework voisin.

---

## Invariants

```text
- aucune mutation du write model ;
- toute définition exécutable est versionnée ;
- une valeur calculée conserve sa définition et sa source ;
- le drill-down doit être possible lorsque les mappings sources existent ;
- aucun score ne bloque le posting par défaut.
```

---

# 31. Exports

Les formats :

```text
JSON
CSV
XLSX
PDF
```

sont des adapters de sortie.

Le domaine produit :

```text
ReportSnapshot
```

L'adapter produit :

```text
bytes / file
```

---

# 32. Bounded Context 15 - Reconciliation

## 32.1 Statut

Ce bounded context est prévu mais non prioritaire pour le premier core stable.

---

## 32.2 Responsabilité

Gérer :

```text
bank reconciliation
account reconciliation
matching
differences
tolerances
```

---

## 32.3 Concepts futurs

```text
ReconciliationSession
ReconciliationItem
ReconciliationMatch
ReconciliationRule
Tolerance
Discrepancy
```

---

## 32.4 Aggregate Root - `ReconciliationSession`

Une session de rapprochement regroupe :

```text
scope
period
items
matches
status
```

mais les gros volumes pourront nécessiter des items externalisés.

---


Le contexte peut également fournir des indicateurs downstream à `Financial Analysis`, par exemple des taux de rapprochement ou des écarts de trésorerie, sans modifier les définitions comptables.

---

# 33. Bounded Context 16 - Inventory (Future)

## Statut

```text
Future Specialized Domain
Priority: P1/P2 selon roadmap
```

---

## Responsabilité

Gérer les règles opérationnelles liées aux stocks :

```text
stock item / category
inventory movements
physical inventory
cost layers
valuation
write-down / impairment
inventory adjustments
period-end stock entries
```

Le contexte ne doit pas être réduit à quelques comptes `3xx` ou à des préfixes nationaux.

---

## Concepts futurs

```text
InventoryItem
InventoryCategory
InventoryMovement
InventoryValuationMethod
InventoryLayer
PhysicalInventory
InventoryAdjustment
InventoryValuationSnapshot
```

---

## Policies

```text
InventoryRecognitionPolicy
InventoryValuationPolicy
InventoryWriteDownPolicy
InventoryClosingPolicy
```

---

## Relations

```text
Inventory
    -> Accounting Policies & Measurement
    -> Journal & Entries

Inventory
    -> Closing

Inventory
    -> Financial Statements / Analysis
```

Le posting final reste dans le coeur comptable.

---

# 34. Bounded Context 17 - Fixed Assets (Future)

## Statut

```text
Future Specialized Domain
Priority: P1/P2
```

---

## Responsabilité

Gérer le cycle de vie comptable des immobilisations :

```text
acquisition
capitalization
componentization
depreciation
impairment
revaluation when applicable
disposal
retirement
```

---

## Concepts futurs

```text
FixedAsset
AssetComponent
AssetCategory
UsefulLife
ResidualValue
DepreciationPlan
DepreciationRun
ImpairmentAssessment
AssetDisposal
```

---

## Policies

```text
CapitalizationPolicy
DepreciationPolicy
ImpairmentPolicy
RevaluationPolicy
DisposalPolicy
```

---

## Relation au coeur

```text
Fixed Assets
    -> computes business events / amounts
    -> proposes JournalEntries
    -> Posting Engine validates/posts
```

Le module ne modifie jamais directement les lignes postées.

---

# 35. Bounded Context 18 - Accruals & Provisions (Future)

## Statut

```text
Future Specialized Domain
Priority: P1
```

---

## Responsabilité

Gérer les traitements périodiques de rattachement et d'estimation :

```text
accrued expenses
accrued income
prepaid expenses
deferred income
provisions
impairments
period-end adjustments
reversing entries
```

---

## Concepts futurs

```text
AccrualSchedule
DeferralSchedule
ProvisionCase
ProvisionEstimate
AdjustmentProposal
ReversingEntryPolicy
PeriodEndAdjustmentRun
```

---

## Policies

```text
AccrualRecognitionPolicy
AccrualMeasurementPolicy
ProvisionRecognitionPolicy
ProvisionMeasurementPolicy
ReversalTimingPolicy
```

---

## Relations

```text
Accounting Periods & Closing
        |
        v
Accruals & Provisions
        |
        v
JournalEntry proposals
        |
        v
Validation / Posting
```

Ce bounded context justifie la séparation entre une règle d'inventaire et le mécanisme générique de posting.

---

# 36. Bounded Context 19 - Consolidation (Future)

## Statut

```text
Future Specialized Domain
Priority: P2
```

---

## Responsabilité

Gérer la consolidation multi-entités et potentiellement multi-référentiels.

```text
group perimeter
ownership
control
group chart
entity mappings
currency translation
intercompany matching
eliminations
minority interests
goodwill
consolidated statements
```

---

## Concepts futurs

```text
ConsolidationGroup
ConsolidationPerimeter
GroupEntity
OwnershipRelation
GroupChartOfAccounts
ConsolidationMapping
IntercompanyRelation
EliminationEntry
ConsolidationAdjustment
Goodwill
NonControllingInterest
ConsolidationRun
ConsolidatedStatement
```

---

## Sources

Le contexte consomme :

```text
entity-level financial statements
company charts
reference mappings
crosswalks
exchange rates
group policies
```

---

## Frontière

Les `EliminationEntry` et `ConsolidationAdjustment` ne doivent pas modifier les ledgers statutaires des entités.

```text
Statutory Ledger
    -> immutable source

Consolidation Layer
    -> adjustments / eliminations

Consolidated Statements
    -> derived output
```

---

## Relation aux référentiels

La consolidation doit pouvoir s'appuyer sur :

```text
ReferenceCrosswalk
Group Chart
RegulatoryAccountBinding
Statement Mapping
```

sans supposer que des codes identiques entre standards sont sémantiquement équivalents.

---

# 37. Dimensions analytiques

CFA FRA expose notamment :

```text
Counterparty
CostCenter
CashFlowTag
```

PyAccountingKit doit éviter de figer trop tôt un modèle analytique universel.

Attention : `Accounting Dimensions` (axes analytiques sur les écritures) est distinct du bounded context `Financial Analysis` (indicateurs dérivés).

Approche cible :

```text
AccountingDimension
DimensionMember
JournalLineDimension
```

puis des spécialisations optionnelles :

```text
Counterparty
CostCenter
Project
Department
BusinessUnit
```

`CashFlowTag` peut rester un Value Object spécialisé car il influence directement le cash-flow.

---

# 38. Ubiquitous Language - Entités et périodes

| Terme | Définition |
|---|---|
| Accounting Entity | Entité tenant une comptabilité autonome dans le moteur |
| Fiscal Year | Exercice comptable |
| Accounting Period | Fenêtre temporelle dans laquelle des écritures peuvent être postées |
| Functional Currency | Devise principale de tenue des comptes |
| Closing | Processus de contrôle, écritures de clôture et verrouillage d'une période |

---

# 39. Ubiquitous Language - Plan comptable

| Terme | Définition |
|---|---|
| Reference Standard | Référentiel comptable réglementaire externe |
| Reference Account | Compte défini dans un référentiel |
| Company Chart of Accounts | Plan comptable opérationnel d'une organisation |
| Company Account | Compte utilisable dans les écritures |
| Regulatory Account Binding | Rattachement explicite d'un compte entreprise à une référence |
| Account Code Policy | Règles de validation/génération des codes |
| Auxiliary Account | Compte ou identifiant auxiliaire relié à un compte collectif |

---

# 40. Ubiquitous Language - Ecritures

| Terme | Définition |
|---|---|
| Journal | Registre logique d'écritures |
| Journal Entry | Ecriture comptable atomique au sens métier |
| Journal Entry Line | Mouvement sur un compte |
| Debit | Côté débit d'une ligne |
| Credit | Côté crédit d'une ligne |
| Validation | Vérification permettant le passage DRAFT -> VALIDATED |
| Posting | Comptabilisation définitive VALIDATED -> POSTED |
| Reversal | Nouvelle écriture inversant une écriture postée |
| Replacement Entry | Nouvelle écriture correcte créée après extourne |

---

# 41. Ubiquitous Language - Ledger et reporting

| Terme | Définition |
|---|---|
| General Ledger | Projection détaillée par compte des lignes postées |
| Trial Balance | Agrégation débit/crédit/solde par compte |
| Statement Definition | Structure d'un état financier |
| Statement Line | Rubrique d'un état |
| Statement Account Mapping | Affectation d'un compte/solde à une rubrique |
| Regulatory Statement Mapping | Transformation d'une rubrique vers une présentation réglementaire |
| Report Snapshot | Capture immuable de l'état publié et de son contexte |

---

# 42. Ubiquitous Language - Import et contrôle

| Terme | Définition |
|---|---|
| Import Batch | Unité de traitement d'une source comptable externe |
| Raw Record | Enregistrement source conservé avant transformation |
| Normalized Entry | Ecriture intermédiaire conforme au modèle PyAccountingKit |
| Control | Règle de vérification |
| Control Result | Résultat structuré d'un contrôle |
| Audit Event | Preuve persistante d'une mutation ou opération significative |

---


---
## Ubiquitous Language - Policies & Measurement

| Terme | Définition |
|---|---|
| Accounting Policy Set | Ensemble versionné de policies comptables applicables à une entité/ledger |
| Recognition Policy | Règle déterminant si et quand un élément est comptabilisé |
| Measurement Policy | Règle déterminant la base et le montant de mesure |
| Measurement Basis | Base de valorisation utilisée par une policy |
| Policy Applicability | Portée contextuelle d'une policy |
| Policy Execution Trace | Trace expliquant quelle policy a produit quel résultat |


---
## Ubiquitous Language - Financial Analysis

| Terme | Définition |
|---|---|
| Financial Indicator | Mesure dérivée des projections comptables |
| Indicator Definition | Définition versionnée du calcul d'un indicateur |
| Functional Balance | Reclassement fonctionnel servant au calcul FRNG/BFR/trésorerie |
| Financial Ratio | Rapport entre deux grandeurs financières définies |
| Financial Score | Résultat d'une méthode analytique ou prédictive |
| Analysis Snapshot | Capture immuable des indicateurs, définitions et sources |

# 43. Agrégats retenus

Synthèse cible :

| Bounded Context | Aggregate Root / nature |
|---|---|
| Accounting Identity | `AccountingEntity` |
| Reference Data | objets read-only / `ReferenceCatalog` côté application |
| Accounting Policies & Measurement | `AccountingPolicySet` |
| Company COA | `CompanyChartOfAccounts`, `CompanyAccount` |
| Periods | `FiscalYear`, `AccountingPeriod` |
| Journals | `Journal`, `JournalEntry` |
| Posting | pas d'aggregate propre, services sur `JournalEntry` |
| Ledger | aucun aggregate, projections |
| Imports | `AccountingImportBatch` |
| Controls | `ControlRun` |
| Audit | `AuditEvent` append-only |
| Financial Statements | `StatementMappingSet` / définitions read-only |
| Regulatory Reporting | `RegulatoryReportingProfile`, `ReportSnapshot` |
| Financial Analysis | `AnalysisSnapshot`, définitions read-only/versionnées |
| Reconciliation | `ReconciliationSession` |
| Inventory (future) | `InventoryItem` / `PhysicalInventory` selon design détaillé |
| Fixed Assets (future) | `FixedAsset` |
| Accruals & Provisions (future) | `ProvisionCase` / `PeriodEndAdjustmentRun` |
| Consolidation (future) | `ConsolidationGroup`, `ConsolidationRun` |

---

# 44. Entities principales

```text
AccountingEntity
CompanyChartOfAccounts
CompanyAccount
FiscalYear
AccountingPeriod
Journal
JournalEntry
JournalEntryLine
AccountingImportBatch
ControlRun
AuditEvent
StatementMappingSet
RegulatoryReportingProfile
ReportSnapshot
ReconciliationSession
```

---


A ajouter dans les futures versions :

```text
AccountingPolicySet
AnalysisSnapshot

InventoryItem
PhysicalInventory
FixedAsset
AssetComponent
ProvisionCase
PeriodEndAdjustmentRun
ConsolidationGroup
ConsolidationRun
```

---

# 45. Value Objects principaux

```text
AccountingEntityId
FiscalYearId
AccountingPeriodId
CompanyChartId
AccountId
AccountCode
JournalId
JournalEntryId
JournalEntryLineId

Money
Currency
ExchangeRate

AccountingDate
PostingDate
DateRange
EntryNumber
DocumentReference
SourceReference

DebitCredit
PostingAmount
AccountType
AccountKind
AccountStatus
EntryStatus
JournalType
PeriodStatus

ReferenceAccountId
StandardId
StandardEdition
ReferenceDatasetVersion
AccountingReferenceSnapshot

ControlCode
ControlSeverity
ControlStatus

StatementLineId
MappingType
MappingConfidence

ContentChecksum
CorrelationId
```

---


Policies & Analysis :

```text
AccountingPolicySetId
PolicyId
PolicyVersion
PolicyApplicability
MeasurementBasis
RecognitionDecision
PolicyExecutionTraceId

IndicatorCode
IndicatorDefinitionVersion
RatioCode
AnalysisSnapshotId
```

Future specialized domains :

```text
InventoryItemId
InventoryValuationMethod
FixedAssetId
UsefulLife
ResidualValue
ProvisionCaseId
ConsolidationGroupId
ConsolidationRunId
OwnershipPercentage
```

---

# 46. Domain Services

Services métier probables :

```text
EntryValidationService
PostingService
ReversalService
ChartGenerationService
AccountCodeGenerationService
ClosingService
OpeningBalanceService
AccountingControlEngine
FinancialStatementEngine
RegulatoryReportingEngine
ReconciliationService
```

Critère :

> Un Domain Service n'est créé que lorsque le comportement ne trouve pas naturellement sa place dans un seul agrégat.

---


Nouveaux services probables :

```text
RecognitionService
MeasurementService
PolicyResolutionService
PolicyExecutionService

FinancialAnalysisEngine
FunctionalBalanceService
FinancialRatioService

InventoryValuationService
DepreciationService
ProvisionMeasurementService
ConsolidationEngine
```

Ces services ne doivent être introduits que lorsque le comportement ne trouve pas naturellement sa place dans un agrégat ou une policy.

---

# 47. Application Services

Cas d'usage :

```text
CreateAccountingEntity
CreateCompanyChart
ImportReferenceChart
CreateCompanyAccount

CreateJournalEntry
UpdateDraftEntry
ValidateJournalEntry
PostJournalEntry
ReverseJournalEntry

CloseAccountingPeriod
ReopenAccountingPeriod

ImportAccountingData

BuildGeneralLedger
BuildTrialBalance

RunAccountingControls

GenerateFinancialStatement
GenerateRegulatoryReport
CreateReportSnapshot
```

---


Nouveaux cas d'usage :

```text
CreateAccountingPolicySet
ActivateAccountingPolicySet
EvaluateRecognition
MeasureAccountingItem
GeneratePolicyBasedEntry

ComputeFinancialIndicators
BuildFunctionalBalance
ComputeFinancialRatios
CreateAnalysisSnapshot

RunInventoryValuation
RunDepreciation
RunPeriodEndAdjustments
RunConsolidation
```

---

# 48. Repository Ports

Repository contracts principaux :

```text
AccountingEntityRepository
FiscalYearRepository
AccountingPeriodRepository
CompanyChartRepository
AccountRepository
JournalRepository
JournalEntryRepository
ImportBatchRepository
ControlRunRepository
ReportSnapshotRepository
```

Reference data :

```text
AccountingReferenceProvider
```

Read side :

```text
LedgerQueryPort
TrialBalanceQueryPort
StatementQueryPort
AuditQueryPort
```

---


Nouveaux ports :

```text
AccountingPolicySetRepository
PolicyDefinitionRepository
AnalysisSnapshotRepository

InventoryRepository
FixedAssetRepository
ProvisionRepository
ConsolidationRepository
```

Read-side :

```text
FinancialAnalysisQueryPort
IndicatorDefinitionProvider
```

---

# 49. Domain Events globaux

Catalogue initial :

```text
AccountingEntityCreated

CompanyChartCreated
CompanyAccountCreated
CompanyAccountUpdated
CompanyAccountDisabled
ReferenceAccountBound

FiscalYearOpened
AccountingPeriodOpened
AccountingPeriodClosed
AccountingPeriodReopened

JournalCreated

JournalEntryCreated
JournalEntryUpdated
JournalEntryValidated
JournalEntryPosted
JournalEntryReversed

AccountingImportStarted
AccountingImportCompleted
AccountingImportFailed

ControlRunStarted
ControlRunCompleted
BlockingControlFailed

FinancialStatementGenerated

RegulatoryProfileUpdated
ReportSnapshotCreated

ReconciliationCompleted
```

---


Nouveaux événements :

```text
AccountingPolicySetCreated
AccountingPolicySetActivated
AccountingPolicySetSuperseded
PolicyEvaluated
PolicyGeneratedAccountingEntry

FinancialAnalysisComputed
AnalysisSnapshotCreated

InventoryValuationCompleted
DepreciationRunCompleted
ProvisionMeasured
PeriodEndAdjustmentRunCompleted

ConsolidationRunStarted
ConsolidationRunCompleted
```

---

# 50. Relations inter-contextes

## 50.1 Identity -> tous les contexts

```text
AccountingEntity
    = upstream identity
```

Tous les contextes transactionnels utilisent :

```text
AccountingEntityId
```

---

## 50.2 Reference Data -> Company COA

Relation :

```text
Customer / Supplier
```

Le plan entreprise consomme les références.

Il ne modifie pas la source réglementaire.

---

## 50.3 Company COA -> Journal & Entries

Une ligne référence :

```text
AccountId
```

et non directement :

```text
ReferenceAccountId
```

Le référentiel ne remplace jamais le plan opérationnel.

---

## 50.4 Periods -> Posting

Le posting consulte :

```text
AccountingPeriodStatus
```

avant transition.

---

## 50.5 Journal & Entries -> Ledger

Ledger est downstream des lignes postées.

```text
JournalEntryLine
    ->
Ledger Projection
```

---

## 50.6 Imports -> Journal & Entries

L'import produit des écritures via l'Application Layer.

Il ne contourne pas les règles de domaine.

Une policy peut autoriser un import de source déjà validée à créer des écritures directement postées, mais ce comportement doit rester explicite.

---

## 50.7 Ledger -> Financial Statements

```text
TrialBalance
    ->
FinancialStatementEngine
```

---

## 50.8 Reference Data -> Regulatory Reporting

Les structures réglementaires viennent du provider.

---

## 50.9 Controls -> Closing / Reporting

```text
Blocking controls
    ->
can block close/export
```

---

## 50.10 Domain Events -> Audit

L'audit observe ou est appelé explicitement depuis l'application pour les mutations importantes.

---


## Accounting Reference Data -> Accounting Policies & Measurement

```text
ReferenceStandard / Edition
    ->
Policy applicability / reference context
```

Le référentiel ne contient pas nécessairement l'intégralité des choices organisationnels ; le `AccountingPolicySet` résout la méthode applicable.

---

## Accounting Policies & Measurement -> Journal & Entries

Les policies produisent :

```text
RecognitionDecision
MeasurementResult
JournalEntryProposal
```

mais le coeur `Journal & Entries` reste propriétaire de l'écriture.

---

## Financial Statements -> Financial Analysis

```text
Financial Statements / Trial Balance
    ->
Financial Analysis
```

La dépendance inverse est interdite.

---

## Future specialized contexts -> Accounting Core

```text
Inventory
Fixed Assets
Accruals & Provisions
    ->
business events / calculated amounts
    ->
JournalEntry proposals
    ->
Validation / Posting
```

Ils ne contournent jamais le Posting Engine.

---

## Entity Reporting -> Consolidation

```text
Entity Financial Statements
    ->
Consolidation
    ->
Eliminations / Group Adjustments
    ->
Consolidated Statements
```

Les ajustements de consolidation ne réécrivent pas les ledgers statutaires.

---

# 51. Context Map détaillée

```text
[Accounting Identity]
      |
      v
[Accounting Reference Data] -----> [Accounting Policies & Measurement]
      |                                      |
      |                                      v
      +----------------------------> [Company Chart of Accounts]
                                             |
                                             v
[Accounting Periods] ----------------> [Journal & Entries] <---- [Accounting Imports]
                                             |
                                             v
                                      [Posting & Reversal]
                                             |
                                             v
                                      [Ledger & Balances]
                                        /           \
                                       v             v
                               [Controls]     [Financial Statements]
                                                   /        \
                                                  v          v
                                      [Regulatory Reporting] [Financial Analysis]

[Audit & Traceability]
      ^
      |
      +---- observes important commands/events from all contexts


Future specialized contexts:

[Inventory] ----------------------+
[Fixed Assets] -------------------+--> [Policies] --> [Journal & Entries]
[Accruals & Provisions] ----------+

[Reconciliation] <---------------- [Ledger & Balances]

[Consolidation]
      ^
      |
      +---- Entity Financial Statements
      +---- Reference Data / Crosswalks
      +---- Group Policies
```

---

# 52. Anti-Corruption Layers

## 52.1 Regulatory ACL

```text
regulatory JSON
    ->
Regulatory Adapter
    ->
PyAccountingKit Reference Model
```

---

## 52.2 Django ACL

Lors de la migration CFA FRA :

```text
Django model
    <->
Django Adapter
    <->
PyAccountingKit Domain
```

Les APIs Django ne doivent pas traverser la frontière.

---

## 52.3 FEC ACL

```text
FEC columns
    ->
FEC Adapter
    ->
Generic Import Model
```

---


## Policy Definition ACL

Lorsque des policies sont chargées depuis un référentiel externe ou une configuration applicative :

```text
External policy representation
    ->
Policy Adapter
    ->
PyAccountingKit Policy Model
```

---

## Corporate Finance boundary

Une future extension de corporate finance doit consommer `Financial Analysis` via une API dédiée sans dépendre du write model comptable.

---

# 53. Modèle d'identité

Principe :

```text
internal identity
    !=
business code
    !=
regulatory identity
```

Exemple :

```text
AccountId
    UUID/typed id

AccountCode
    "51200001"

ReferenceAccountId
    "account:fr-pcg:2026:512"
```

Ces trois notions doivent rester distinctes.

---

# 54. Multi-entity scoping

Tous les repositories métier doivent garantir le scope.

Exemple :

```python
repository.get(
    entity_id=AccountingEntityId(...),
    entry_id=JournalEntryId(...),
)
```

Le scoping ne doit pas être seulement implicite via l'utilisateur connecté.

---

# 55. Modèle monétaire

`Money` doit être un Value Object.

```python
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: Currency
```

Règles :

```text
- Decimal uniquement ;
- aucune addition entre devises incompatibles sans conversion explicite ;
- arrondi via policy ;
- précision explicitement définie.
```

---

# 56. Multi-devise

Concepts futurs / P1 :

```text
TransactionCurrency
FunctionalCurrency
ExchangeRate
FunctionalAmount
OriginalAmount
```

Une ligne pourra éventuellement conserver :

```text
transaction_amount
functional_amount
exchange_rate
```

Le détail n'est pas figé dans ce document.

---

# 57. Modèle temporel

Value Objects :

```text
AccountingDate
PostingDate
DocumentDate
PeriodDateRange
```

Le domaine doit distinguer :

```text
date de pièce
date comptable
date de posting
timestamp technique
```

---

# 58. Status models

## Account

```text
ACTIVE
INACTIVE
```

Extension possible :

```text
BLOCKED
ARCHIVED
```

## Entry

```text
DRAFT
VALIDATED
POSTED
REVERSED
```

## Period

```text
OPEN
CLOSING
CLOSED
LOCKED
```

## Import

```text
UPLOADED
PARSED
MAPPING
READY
IMPORTING
IMPORTED
FAILED
```

---

# 59. Erreurs de domaine

Hiérarchie proposée :

```text
AccountingDomainError
|
+-- AccountError
|   +-- AccountInactiveError
|   +-- InvalidAccountCodeError
|
+-- EntryError
|   +-- InvalidEntryStateError
|   +-- UnbalancedEntryError
|   +-- InvalidJournalLineError
|
+-- PeriodError
|   +-- ClosedPeriodError
|   +-- DateOutsidePeriodError
|
+-- ReferenceError
|   +-- UnknownReferenceAccountError
|   +-- NonExecutableMappingError
|
+-- PolicyError
|   +-- PolicyNotApplicableError
|   +-- PolicyVersionError
|   +-- MeasurementError
|
+-- FinancialAnalysisError
|   +-- UnknownIndicatorDefinitionError
|   +-- MissingAnalysisDependencyError
|
+-- ImportDomainError
|
+-- ReportingError
```

Les exceptions ORM ne doivent pas remonter directement dans l'API métier.

---

# 60. Règles de mutation

Chaque mutation importante suit :

```text
Command
   |
   v
load aggregates
   |
   v
execute domain behavior
   |
   v
collect events
   |
   v
persist via repositories
   |
   v
audit
   |
   v
commit UnitOfWork
```

---


Une écriture proposée par `Inventory`, `Fixed Assets` ou `Accruals & Provisions` suit exactement le même flux :

```text
Specialized Domain
    -> Proposal
    -> Application Command
    -> JournalEntry
    -> Validation
    -> Posting
```

---

# 61. Règles de lecture

Les queries peuvent bypasser les agrégats pour lire efficacement les projections.

Exemple :

```text
TrialBalanceQuery
    ->
SQL aggregate / in-memory projection / optimized read model
```

sans charger chaque `JournalEntry`.

C'est volontaire.

---

# 62. Séparation Write Model / Read Model

Write model :

```text
CompanyAccount
JournalEntry
AccountingPeriod
```

Read model :

```text
LedgerRow
TrialBalanceRow
StatementRow
AuditRow
```

Cette séparation doit rester légère et pragmatique.

Pas d'obligation d'utiliser deux bases.

---


`Financial Analysis` appartient intégralement au read model :

```text
IndicatorValue
RatioValue
FinancialDiagnostic
AnalysisSnapshot
```

à l'exception de ses définitions/versionnements, qui sont des configurations métier.

---

# 63. Transactions métier

Frontières transactionnelles minimales :

```text
validate entry
post entry
reverse entry
close period
execute import
create final report snapshot
```

Un report calculé non persisté n'a pas nécessairement besoin d'une transaction d'écriture.

---

# 64. Invariants inter-agrégats

Certaines règles dépassent un agrégat.

Exemple posting :

```text
JournalEntry.status == VALIDATED

AND AccountingPeriod.status == OPEN

AND Journal.status == ACTIVE

AND all Account.status == ACTIVE
```

Ces règles sont orchestrées via service de domaine/application.

Elles ne justifient pas un mega-aggregate.

---

# 65. Cohérence forte vs éventuelle

## Cohérence forte

Nécessaire pour :

```text
posting
reversal
period close
import final
```

## Cohérence éventuelle admissible

Possible pour :

```text
dashboard
analytics
cached ledger
materialized statements
search indexes
```

---


`Financial Analysis` peut accepter une cohérence éventuelle lorsqu'il fonctionne sur des snapshots finalisés.

`Accounting Policies & Measurement` exige une cohérence forte lorsqu'une policy participe directement à la génération d'une écriture à poster.

---

# 66. Politique d'immutabilité

Objets candidats à l'immutabilité complète :

```text
Money
AccountCode
ReferenceAccount
AccountingReferenceSnapshot
ControlResult
ReportSnapshot final
AnalysisSnapshot final
PolicyExecutionTrace
LedgerRow
TrialBalanceRow
```

Objets mutables sous contraintes :

```text
CompanyAccount
JournalEntry DRAFT
AccountingPeriod
ImportBatch
```

---

# 67. Mapping de CFA FRA vers PyAccountingKit

| CFA FRA | PyAccountingKit |
|---|---|
| `Organization` | `AccountingEntity` |
| `FiscalYear` | `FiscalYear` |
| `AccountingPeriod` | `AccountingPeriod` |
| `ChartOfAccounts` | `CompanyChartOfAccounts` |
| `Account` | `CompanyAccount` |
| `Journal` | `Journal` |
| `JournalEntry` | `JournalEntry` |
| `JournalLine` | `JournalEntryLine` |
| `FECImport` | `AccountingImportBatch` + FEC adapter |
| `FECRawLine` | `RawAccountingRecord` / FEC raw record |
| `ImportError` | `ImportIssue` |
| `AccountingFramework` | `ReferenceStandard` |
| `FrameworkVersion` | `ReferenceEdition` / dataset version |
| `FrameworkAccount` | `ReferenceAccount` |
| `AccountMapping` | `RegulatoryAccountBinding` |
| `StatementDefinition` | `StatementDefinition` |
| `StatementLine` | `StatementLine` |
| `StatementAccountMapping` | `StatementAccountMapping` |
| `ControlResult` | `ControlResult` |
| `AuditEvent` | `AuditEvent` |
| `PostingService` | `PostingService` / command handler |
| `ReversalService` | `ReversalService` |
| `GeneralLedgerService` | `LedgerQueryService` |
| `TrialBalanceService` | `TrialBalanceQueryService` |

---


Nouveaux concepts sans équivalent direct complet dans CFA FRA :

```text
AccountingPolicySet
RecognitionPolicy
MeasurementPolicy
PolicyExecutionTrace
FinancialAnalysisDefinition
AnalysisSnapshot
Inventory Domain
Fixed Assets Domain
Accruals & Provisions Domain
Consolidation Domain
```

Ils sont introduits par généralisation du framework et par l'apport doctrinal des nouveaux ouvrages.

---

# 68. Concepts CFA FRA non repris tels quels

Certains concepts sont applicatifs :

```text
User
OrganizationMembership
HTMX
Django forms
Views
Admin
routes
session
```

Ils restent hors du domaine PyAccountingKit.

Les rôles :

```text
ADMIN
ACCOUNTANT
REVIEWER
AUDITOR
```

ne sont pas nécessairement des enums du coeur.

Le framework peut recevoir un :

```text
ActorContext
```

et laisser l'autorisation détaillée à l'application cliente.

---

# 69. Actor Context

Concept transverse possible :

```python
@dataclass(frozen=True)
class ActorContext:
    actor_id: str | None
    roles: frozenset[str]
    source: str | None
```

Usage :

- audit ;
- policies ;
- traçabilité.

Mais PyAccountingKit ne devient pas un framework IAM.

---

# 70. Source Context

Pour imports et API externes :

```text
SourceContext
    source_system
    external_reference
    import_batch_id
    correlation_id
```

peut accompagner une écriture.

---

# 71. Provenance

Une ligne issue d'un import doit pouvoir remonter vers :

```text
JournalEntryLine
    |
    v
SourceReference
    |
    v
RawRecord
    |
    v
ImportBatch
    |
    v
Original Source
```

Cette relation est essentielle pour l'audit.

---

# 72. Reporting provenance

Une ligne d'état doit pouvoir remonter :

```text
Report line
    |
    v
Statement mapping
    |
    v
Trial balance rows
    |
    v
Ledger rows
    |
    v
JournalEntryLine
```

Le drill-down est donc une propriété architecturale du modèle de reporting.

---

# 73. Regulatory provenance

Un compte entreprise peut remonter :

```text
CompanyAccount
    |
    v
RegulatoryAccountBinding
    |
    v
ReferenceAccount
    |
    v
ReferenceStandard
    |
    v
Reference Dataset
```

---

# 74. Versioning du modèle

Chaque plan d'entreprise possède une version.

Chaque snapshot réglementaire possède :

```text
standard
edition
dataset version
checksum
```

Chaque mapping set possède une version.

Chaque report snapshot conserve ces versions.

---

# 75. Règles de suppression

## Données de référence

Pas de suppression destructive nécessaire côté domaine transactionnel.

## CompanyAccount

Préférer :

```text
INACTIVE
```

à suppression si le compte a déjà été utilisé.

## JournalEntry POSTED

Suppression interdite.

## AuditEvent

Suppression interdite dans le modèle normal.

## ReportSnapshot final

Suppression physique dépend des politiques de rétention, mais la mutation est interdite.

---

# 76. Historisation

Concepts nécessitant potentiellement historisation :

```text
CompanyChart version
Account label
Account binding
MappingSet
ReferenceSnapshot
ReportingProfile
```

Le modèle précis sera approfondi dans les documents dédiés.

---

# 77. Extension points

Le domaine doit permettre l'ajout de :

```text
new AccountCodePolicy
new JournalType
new ImportAdapter
new Control
new StatementDefinition
new MappingStrategy
new ReferenceProvider
new ReconciliationRule
```

sans modifier les agrégats principaux.

---

# 78. Domain Policy Registry

Pour certains points d'extension, un registry contrôlé peut être utile :

```text
AccountCodePolicyRegistry
ControlRegistry
ImportAdapterRegistry
StatementGeneratorRegistry
```

Ces registries appartiennent plutôt à l'application/integration layer qu'aux entities.

---

# 79. InMemory Model

Chaque repository P0 doit avoir une implémentation mémoire.

Objectif :

```text
domain tests
example usage
contract tests
fast feedback
```

Cela garantit que les agrégats ne dépendent pas de l'ORM.

---

# 80. Boundary tests

Les tests de frontière doivent vérifier :

```text
domain imports do not import django
domain imports do not import sqlalchemy
reference domain does not import JSON loader
FEC names do not leak into generic imports
ledger is read-only projection
posted entries reject mutation
```

---

# 81. Modèle initial de packages

```text
pyaccountingkit/domain/
|
+-- identity/
|
+-- references/
|
+-- policies/
|   +-- policy_set.py
|   +-- recognition.py
|   +-- measurement.py
|   +-- applicability.py
|   +-- trace.py
|
+-- chart/
|
+-- periods/
|
+-- journals/
|
+-- posting/
|
+-- closing/
|
+-- controls/
|
+-- reporting/
|
+-- financial_analysis/
|   +-- indicators.py
|   +-- ratios.py
|   +-- functional_balance.py
|   +-- scores.py
|   +-- snapshots.py
|
+-- reconciliation/
|
+-- inventory/                # future
|
+-- fixed_assets/             # future
|
+-- accruals/                 # future
|
+-- consolidation/            # future
```

Les modules futurs peuvent rester absents du package initial tant que leurs contrats ne sont pas stabilisés.

---

# 82. Décisions de modélisation actées

| ID | Décision |
|---|---|
| ADR-DOM-001 | `AccountingEntity` est le terme générique, `Organization` reste une traduction applicative |
| ADR-DOM-002 | `JournalEntry` est un Aggregate Root |
| ADR-DOM-003 | `JournalEntryLine` appartient à l'agrégat `JournalEntry` |
| ADR-DOM-004 | `CompanyAccount` est un Aggregate Root indépendant |
| ADR-DOM-005 | Un chart ne charge pas tous ses comptes comme enfants d'agrégat |
| ADR-DOM-006 | `AccountingPeriod` peut être verrouillé comme Aggregate Root indépendant |
| ADR-DOM-007 | General Ledger et Trial Balance sont des projections |
| ADR-DOM-008 | `ReferenceAccount` est un objet externe immutable |
| ADR-DOM-009 | `AccountingPolicySet` est un Aggregate Root versionné |
| ADR-DOM-010 | Recognition, Measurement, Posting, Presentation et Analysis sont distincts |
| ADR-DOM-011 | `PolicyExecutionTrace` est immutable |
| ADR-DOM-012 | `RegulatoryAccountBinding` est distinct de `StatementAccountMapping` |
| ADR-DOM-013 | FEC est traduit via Anti-Corruption Layer |
| ADR-DOM-014 | `AccountingImportBatch` protège le workflow d'import sans contenir toutes les raw lines |
| ADR-DOM-015 | `AuditEvent` est append-only |
| ADR-DOM-016 | `ReportSnapshot` final est immutable |
| ADR-DOM-017 | `Financial Analysis` est un bounded context read-only downstream |
| ADR-DOM-018 | `AnalysisSnapshot` final est immutable |
| ADR-DOM-019 | Les heuristiques de mapping ne sont pas des invariants universels |
| ADR-DOM-020 | Les transactions inter-agrégats sont orchestrées par l'Application Layer |
| ADR-DOM-021 | Les read models peuvent être optimisés indépendamment du write model |
| ADR-DOM-022 | Les identités interne, business et réglementaire sont distinctes |
| ADR-DOM-023 | `Money` utilise `Decimal` |
| ADR-DOM-024 | Le multi-entity scoping est obligatoire dans les ports |
| ADR-DOM-025 | Inventory, Fixed Assets et Accruals & Provisions sont des specialized domains futurs |
| ADR-DOM-026 | Ces specialized domains produisent des propositions d'écriture mais ne contournent jamais le Posting Engine |
| ADR-DOM-027 | Consolidation est un bounded context P2 distinct des ledgers statutaires |
| ADR-DOM-028 | Les ajustements de consolidation ne modifient pas les écritures statutaires |
| ADR-DOM-029 | Reconciliation reste un supporting context avancé |
| ADR-DOM-030 | Corporate Finance avancée reste hors du coeur PyAccountingKit |

---

# 83. Priorisation des bounded contexts

## P0 - Premier coeur stable

```text
Accounting Identity
Accounting Reference Data
Accounting Policies & Measurement
Company Chart of Accounts
Accounting Periods
Journal & Entries
Posting & Reversal
Ledger & Balances
Audit minimal
```

---

## P1 - Capacités structurantes

```text
Accounting Imports
FEC Adapter
Controls
Financial Statements
Regulatory Reporting
Financial Analysis
Closing avancé
Multi-currency
Auxiliary accounting
Accruals & Provisions
```

`Inventory` et `Fixed Assets` peuvent commencer en P1 tardif ou P2 selon le périmètre de la première release métier.

---

## P2 - Capacités avancées

```text
Inventory avancé
Fixed Assets avancé
Reconciliation avancée
Consolidation
Group Chart
Crosswalk automation
Advanced analytical dimensions
Corporate-finance extensions
```

---

# 84. Scénario end-to-end du domaine

```text
1. Load ReferenceStandard fr-pcg:2026

2. Create AccountingEntity

3. Create / select AccountingPolicySet

4. Create CompanyAccountingProfile

5. Generate CompanyChartOfAccounts

6. Create FiscalYear / AccountingPeriods

7. Create Journal

8. Create JournalEntry DRAFT

9. Add JournalEntryLines

10. Validate
      DRAFT -> VALIDATED

11. Post
      VALIDATED -> POSTED

12. Build General Ledger

13. Build Trial Balance

14. Run Controls

15. Build Financial Statements

16. Map to Regulatory Statement

17. Create ReportSnapshot

18. Compute Financial Analysis
      SIG / CAF / FRNG / BFR / ratios

19. Create AnalysisSnapshot
```

Scénario futur specialized domain :

```text
FixedAsset acquisition
    -> CapitalizationPolicy
    -> MeasurementPolicy
    -> JournalEntry proposal
    -> Validation / Posting
    -> Depreciation schedule
    -> periodic depreciation entry
```

---

# 85. Exemple de scénario multi-référentiels

```text
Company France
    |
    +-- CompanyAccount 51200001
    |       |
    |       +--> ReferenceAccount fr-pcg:2026:512
    |
    +-- JournalEntryLine
            |
            v
        Ledger

Company Cameroun
    |
    +-- CompanyAccount 521100001
            |
            +--> ReferenceAccount ohada-syscohada:2017:...
```

Le moteur transactionnel reste le même.

Le moteur transactionnel reste identique tandis que peuvent changer :

```text
reference data
AccountingPolicySet
company chart policy
reporting mappings
financial-analysis definitions
```

---

# 86. Exemple de frontière correcte

Correct :

```text
JournalEntryLine
    references
AccountId
```

Puis :

```text
CompanyAccount
    has
RegulatoryAccountBinding
```

Incorrect :

```text
JournalEntryLine
    references directly
ReferenceAccount
```

car cela court-circuite le plan opérationnel de l'entreprise.

---

# 87. Exemple de frontière reporting correcte

Correct :

```text
TrialBalanceRow
    ->
StatementAccountMapping
    ->
StatementLine
```

puis :

```text
StatementLine
    ->
RegulatoryStatementMapping
    ->
ReferenceStatementLine
```

Cela maintient deux transformations explicites.

---

# 88. Risques de modélisation

## RISK-DOM-001 - Mega Aggregate

Risque :

```text
Chart + tous comptes
```

Réponse :

```text
CompanyAccount aggregate séparé.
```

---

## RISK-DOM-002 - ORM Driven Design

Risque :

les foreign keys dictent les frontières métier.

Réponse :

définir d'abord IDs, invariants et services.

---

## RISK-DOM-003 - Reporting comme source primaire

Réponse :

projections reconstructibles.

---

## RISK-DOM-004 - Référentiel confondu avec plan entreprise

Réponse :

`ReferenceAccount` != `CompanyAccount`.

---

## RISK-DOM-005 - FEC contaminant le core

Réponse :

ACL / adapter spécifique.

---

## RISK-DOM-006 - Contextes trop nombreux trop tôt

Réponse :

les bounded contexts sont des frontières conceptuelles ; ils ne nécessitent pas immédiatement des packages ou services distribués séparés.

---


## RISK-DOM-007 - Policies dispersées dans le coeur

Risque :

```text
if standard == ...
```

dans `JournalEntry`, `PostingService` ou les repositories.

Réponse :

```text
Accounting Policies & Measurement bounded context
```

---

## RISK-DOM-008 - Financial Analysis comme write model

Risque :

faire dépendre le posting d'un ratio ou d'un score.

Réponse :

```text
Financial Analysis = downstream read-only
```

---

## RISK-DOM-009 - Specialized domains implémentés trop tôt

Risque :

sur-concevoir Inventory, Fixed Assets ou Consolidation avant stabilisation du core.

Réponse :

définir les frontières maintenant, différer l'implémentation.

---

## RISK-DOM-010 - Consolidation modifiant le statutaire

Réponse :

les éliminations et ajustements vivent dans le contexte Consolidation, jamais dans les ledgers statutaires.

---

# 89. Ce qui reste à préciser

Les documents suivants devront détailler :

```text
invariants exacts de chaque état
règles de side debit/credit
normal balance
policies de rounding
account code generation
auxiliary accounting
closing entries
opening balances
ledger inclusion rules
trial balance variants
report mappings
multi-currency
persistence contracts
locking semantics
```

---


Nouveaux points à préciser :

```text
modèle exact de AccountingPolicySet
policy inheritance / override
policy applicability resolution
PolicyExecutionTrace persistence
recognition vs measurement contracts
indicator definition DSL / strategy
AnalysisSnapshot serialization
Inventory aggregate boundaries
Fixed Asset componentization
ProvisionCase lifecycle
Consolidation perimeter and group chart
```

---

# 90. Critères d'acceptation du modèle de domaine

Le modèle est acceptable si :

```text
[ ] aucun aggregate principal ne dépend de Django
[ ] JournalEntry protège ses lignes et son équilibre
[ ] CompanyAccount est distinct de ReferenceAccount
[ ] les comptes peuvent avoir des longueurs variables
[ ] AccountingPeriod bloque le posting lorsqu'il est fermé
[ ] les projections ledger ne sont pas des sources primaires
[ ] les imports passent par une ACL
[ ] FEC ne fuit pas dans le core générique
[ ] AuditEvent est séparé de DomainEvent
[ ] StatementAccountMapping est distinct de RegulatoryAccountBinding
[ ] ReportSnapshot peut figer une publication
[ ] tous les contextes sont scopables par AccountingEntityId
[ ] le modèle peut reproduire les workflows validés de CFA FRA
[ ] AccountingPolicySet est distinct du référentiel réglementaire
[ ] une policy produit une trace versionnée et explicable
[ ] Financial Analysis est explicitement read-only
[ ] un indicateur peut être drill-down jusqu'au ledger
[ ] Inventory / Fixed Assets / Accruals ne contournent pas le Posting Engine
[ ] Consolidation est séparée des ledgers statutaires
```

---

# 91. Conclusion

Le modèle de domaine cible repose désormais sur une chaîne explicite :

```text
REFERENCE
    données réglementaires externes

POLICIES & MEASUREMENT
    reconnaissance, mesure, amortissement, dépréciation,
    provisions, rattachement, valorisation

COMPANY MODEL
    plan, comptes, périodes

TRANSACTIONAL CORE
    journaux, écritures, posting, reversal

LEDGER
    grand livre, balances, closing

QUALITY
    controls, audit, provenance

REPORTING
    états financiers, regulatory reporting

FINANCIAL ANALYSIS
    SIG, CAF, FRNG, BFR, ratios, diagnostics

SPECIALIZED DOMAINS
    Inventory / Fixed Assets / Accruals & Provisions / Consolidation

INTEGRATIONS
    FEC, Django, SQLAlchemy, API
```

Cette séparation permet de conserver un coeur transactionnel stable tout en ajoutant progressivement des méthodes comptables et des domaines spécialisés.

Elle évite quatre erreurs majeures :

```text
reference == policy
policy == posting
reporting == analysis
specialized accounting == generic core
```

La prochaine étape doit maintenant figer les règles qui protègent ces frontières.

---

**Prochain document recommandé :**

```text
03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md
```

Il devra classifier chaque règle parmi :

```text
UNIVERSAL_ACCOUNTING_INVARIANT
DOMAIN_POLICY
REGULATORY_RULE
REFERENCE_SPECIFIC_RULE
ACCOUNTING_METHOD
PRESENTATION_RULE
ANALYTICAL_DEFINITION
CONTROL
HEURISTIC
```

afin d'éviter de transformer une méthode ou une convention particulière en invariant universel.


---

## Sources et références documentaires du projet

- 📕 [Comptabilité Générale — Système français et normes IFRS](../../books/Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md)
- 📗 [Maxi fiches de Gestion financière de l'entreprise](../../books/Maxi_fiches_de_Gestion_financiere_de_l_entreprise.md)
- 📂 [Référentiels réglementaires — Datasets](../../referentiels/datasets/)
- 📐 [Référentiels réglementaires — Schémas](../../referentiels/schemas/)
- 🏗️ [CFA FRA Django MVP Sprint 7 — Référence fonctionnelle](../../../resources/cfa_fra_django_mvp_sprint_7/)
- 📄 [CFA FRA — Document de conception](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md)
- 📦 [regulatory-accounting-data-framework](../../../resources/regulatory-accounting-data-framework/)

---

## Couverture dans les plans d'implémentation

Ce document est couvert par les plans suivants :

- [PLAN-00 — Repository Bootstrap (0.0.1)](../../plans/PLAN-00_REPOSITORY_BOOTSTRAP_0.0.1.md)
- [PLAN-01 — Accounting Core (0.1.0)](../../plans/PLAN-01_ACCOUNTING_CORE_0.1.0.md)
