# 02 - PyAccountingKit - Modèle de domaine et Bounded Contexts

> **Projet** : PyAccountingKit  
> **Document** : `02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`  
> **Documents parents** :  
> - `00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`  
> - `01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`  
> **Statut** : Modèle de domaine cible - version de cadrage  
> **Langue** : Français  
> **Objet** : Définir le langage ubiquitaire, les sous-domaines, les bounded contexts, les agrégats, entités, value objects, services de domaine, événements et relations de contexte de PyAccountingKit.

---

# 1. Résumé exécutif

PyAccountingKit doit être construit comme un **moteur comptable générique** dont le domaine est indépendant :

- des frameworks web ;
- de l'ORM ;
- du moteur de base de données ;
- d'un référentiel réglementaire particulier ;
- d'un format d'import particulier ;
- d'une application cliente particulière.

Le modèle de domaine s'appuie sur deux sources complémentaires :

```text
regulatory-accounting-data-framework
        = source de vérité réglementaire

cfa_fra_django_mvp_sprint_7
        = référence fonctionnelle exécutable
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
```

sont des **projections calculées** et non des sources primaires indépendantes.

Le domaine est découpé en bounded contexts explicites afin d'éviter un modèle monolithique où comptes, référentiels, écritures, imports, reporting et contrôle seraient mélangés.

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

# 4. Classification des sous-domaines

PyAccountingKit peut être découpé en trois catégories DDD.

## 4.1 Core Domains

Ils portent la valeur principale du framework.

```text
Journal & Entries
Posting & Reversal
Ledger & Balances
Company Chart of Accounts
```

---

## 4.2 Supporting Domains

Ils soutiennent le coeur mais ne constituent pas seuls la proposition de valeur.

```text
Accounting Periods & Closing
Accounting Imports
Accounting Controls
Financial Statements
Regulatory Reporting
Reconciliation
Audit & Traceability
```

---

## 4.3 Generic / Integration Domains

Ils fournissent des capacités nécessaires mais génériques.

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
| Entity / Organization     |
+-------------+-------------+
              |
              v
+---------------------------+
| Accounting Periods        |
| FiscalYear / Period       |
+-------------+-------------+
              |
              |
              v
+---------------------------+       +---------------------------+
| Company Chart of Accounts |<------| Accounting Reference Data |
| CompanyAccount            |       | ReferenceStandard         |
+-------------+-------------+       +-------------+-------------+
              |                                   |
              |                                   |
              v                                   v
+---------------------------+       +---------------------------+
| Journal & Entries         |       | Financial Reporting       |
| JournalEntry / Lines      |------>| Statement Definitions     |
+-------------+-------------+       +-------------+-------------+
              |                                   |
              v                                   v
+---------------------------+       +---------------------------+
| Posting & Reversal        |       | Regulatory Reporting      |
+-------------+-------------+       | Profiles / Snapshots      |
              |                     +---------------------------+
              v
+---------------------------+
| Ledger & Balances         |
+------+------+-------------+
       |      |
       |      +--------------------------+
       v                                 v
+-------------------+           +----------------------+
| Controls          |           | Reconciliation       |
+-------------------+           +----------------------+

+---------------------------+
| Accounting Imports        |
| Raw -> Normalize -> Entry |
+-------------+-------------+
              |
              v
      Journal & Entries

Audit & Traceability observe les mutations de tous les contexts.
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

# 8. Bounded Context 3 - Company Chart of Accounts

## 8.1 Responsabilité

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

## 8.2 Aggregate Root - `CompanyChartOfAccounts`

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

## 8.3 Aggregate Root - `CompanyAccount`

Chaque compte opérationnel est un aggregate root distinct.

Raisons :

- grand volume possible ;
- activation/désactivation indépendante ;
- modification indépendante du libellé ;
- hiérarchie pouvant être profonde ;
- besoin de requêtes sélectives ;
- besoin d'éviter un agrégat chart géant.

---

## 8.4 `CompanyAccount`

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

## 8.5 Value Objects

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

## 8.6 `RegulatoryAccountBinding`

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

## 8.7 Invariants

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

# 9. Politiques de codification

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

# 10. Comptes collectifs et auxiliaires

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

# 11. Bounded Context 4 - Accounting Periods & Closing

## 11.1 Responsabilité

Gérer :

- exercices ;
- périodes ;
- ouverture ;
- fermeture ;
- verrouillage ;
- clôture ;
- réouverture contrôlée.

---

## 11.2 Aggregate Root - `FiscalYear`

Responsabilités :

```text
start_date
end_date
status
accounting_entity_id
```

---

## 11.3 Aggregate Root - `AccountingPeriod`

Plutôt que de forcer toutes les périodes comme entities d'un gros agrégat `FiscalYear`, PyAccountingKit peut traiter `AccountingPeriod` comme aggregate root indépendant relié à `FiscalYearId`.

Motifs :

- verrouillage concurrent ;
- fermeture indépendante ;
- requêtes fréquentes ;
- contrôle de posting ;
- changement de statut transactionnel ciblé.

---

## 11.4 Value Objects

```text
FiscalYearId
AccountingPeriodId
FiscalYearStatus
AccountingPeriodStatus
PeriodNumber
DateRange
```

---

## 11.5 Statuts

Base proposée :

```text
OPEN
CLOSING
CLOSED
LOCKED
```

La sémantique exacte sera figée dans le document des invariants.

---

## 11.6 Invariants

```text
- start_date <= end_date ;
- une période appartient à un exercice ;
- une date comptable doit tomber dans la période ciblée ;
- une période CLOSED/LOCKED refuse le posting ;
- fermeture et réouverture sont auditées ;
- un closing ne peut être validé si les contrôles bloquants échouent.
```

---

# 12. Closing comme orchestration

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

# 13. Bounded Context 5 - Journal & Entries

## 13.1 Responsabilité

C'est le coeur transactionnel du moteur.

Il porte :

```text
Journal
JournalEntry
JournalEntryLine
```

---

## 13.2 Aggregate Root - `Journal`

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

## 13.3 Aggregate Root - `JournalEntry`

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

## 13.4 `JournalEntry`

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

## 13.5 Entity - `JournalEntryLine`

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

## 13.6 Value Object - `PostingAmount`

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

# 14. Invariants de `JournalEntry`

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

# 15. Cycle de vie de l'écriture

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

# 16. Domain Events - Journal & Entries

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

# 17. Bounded Context 6 - Posting & Reversal

## 17.1 Responsabilité

Le posting n'est pas une simple modification de champ.

Il représente une transition métier contrôlée.

---

## 17.2 Domain Service - `EntryValidationService`

Utilisé lorsqu'une validation nécessite plusieurs collaborators :

```text
AccountRepository
AccountingPeriodRepository
JournalRepository
```

Les invariants purement internes restent dans `JournalEntry`.

---

## 17.3 Domain/Application Service - `PostingService`

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

## 17.4 Domain/Application Service - `ReversalService`

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

# 18. Concurrence autour des écritures

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

# 19. Bounded Context 7 - Ledger & Balances

## 19.1 Responsabilité

Produire les projections comptables issues des lignes postées.

Il est volontairement séparé du write model.

---

## 19.2 Pas d'Aggregate Root `GeneralLedger`

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

## 19.3 `LedgerRow`

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

## 19.4 `TrialBalance`

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

## 19.5 Invariant de projection

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

# 20. Read Models du Ledger

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

# 21. Bounded Context 8 - Accounting Imports

## 21.1 Responsabilité

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

## 21.2 Aggregate Root - `AccountingImportBatch`

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

## 21.3 Statuts

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

## 21.4 Raw records

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

## 21.5 Value Objects

```text
SourceReference
SourceLineNumber
SourceRecordKey
ContentChecksum
NormalizedEntryKey
ImportStatus
```

---

# 22. FEC comme Anti-Corruption Adapter

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

# 23. Idempotence des imports

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

# 24. Bounded Context 9 - Accounting Controls

## 24.1 Responsabilité

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

## 24.2 `AccountingControl`

Abstraction :

```python
class AccountingControl(Protocol):
    code: ControlCode
    severity: ControlSeverity

    def evaluate(self, context) -> ControlResult:
        ...
```

---

## 24.3 Value Object - `ControlResult`

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

## 24.4 Aggregate Root - `ControlRun`

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

## 24.5 Severities

Base proposée :

```text
INFO
WARNING
ERROR
BLOCKING
```

---

# 25. Bounded Context 10 - Audit & Traceability

## 25.1 Responsabilité

Tracer les mutations significatives.

L'audit est transversal mais possède son propre modèle.

---

## 25.2 `AuditEvent`

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

## 25.3 Evénements à auditer

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

## 25.4 AuditEvent vs DomainEvent

```text
DomainEvent
    = notification métier interne

AuditEvent
    = preuve persistante destinée à l'audit
```

Un DomainEvent peut déclencher un AuditEvent, mais les deux concepts restent distincts.

---

# 26. Bounded Context 11 - Financial Statements

## 26.1 Responsabilité

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

## 26.2 `StatementDefinition`

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

## 26.3 `StatementLine`

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

## 26.4 Aggregate Root - `StatementMappingSet`

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

## 26.5 `StatementAccountMapping`

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

# 27. Résultats d'états financiers

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

# 28. Bounded Context 12 - Regulatory Reporting

## 28.1 Responsabilité

Transformer un état financier canonique ou interne vers une présentation réglementaire cible.

---

## 28.2 Concepts

```text
RegulatoryReportingProfile
RegulatoryStatementMapping
RegulatoryMappingSet
RegulatoryControl
ReportSnapshot
ExportDefinition
```

---

## 28.3 Aggregate Root - `RegulatoryReportingProfile`

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

## 28.4 `RegulatoryStatementMapping`

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

## 28.5 Aggregate Root - `ReportSnapshot`

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

# 29. Exports

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

# 30. Bounded Context 13 - Reconciliation

## 30.1 Statut

Ce bounded context est prévu mais non prioritaire pour le premier core stable.

---

## 30.2 Responsabilité

Gérer :

```text
bank reconciliation
account reconciliation
matching
differences
tolerances
```

---

## 30.3 Concepts futurs

```text
ReconciliationSession
ReconciliationItem
ReconciliationMatch
ReconciliationRule
Tolerance
Discrepancy
```

---

## 30.4 Aggregate Root - `ReconciliationSession`

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

# 31. Dimensions analytiques

CFA FRA expose notamment :

```text
Counterparty
CostCenter
CashFlowTag
```

PyAccountingKit doit éviter de figer trop tôt un modèle analytique universel.

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

# 32. Ubiquitous Language - Entités et périodes

| Terme | Définition |
|---|---|
| Accounting Entity | Entité tenant une comptabilité autonome dans le moteur |
| Fiscal Year | Exercice comptable |
| Accounting Period | Fenêtre temporelle dans laquelle des écritures peuvent être postées |
| Functional Currency | Devise principale de tenue des comptes |
| Closing | Processus de contrôle, écritures de clôture et verrouillage d'une période |

---

# 33. Ubiquitous Language - Plan comptable

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

# 34. Ubiquitous Language - Ecritures

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

# 35. Ubiquitous Language - Ledger et reporting

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

# 36. Ubiquitous Language - Import et contrôle

| Terme | Définition |
|---|---|
| Import Batch | Unité de traitement d'une source comptable externe |
| Raw Record | Enregistrement source conservé avant transformation |
| Normalized Entry | Ecriture intermédiaire conforme au modèle PyAccountingKit |
| Control | Règle de vérification |
| Control Result | Résultat structuré d'un contrôle |
| Audit Event | Preuve persistante d'une mutation ou opération significative |

---

# 37. Agrégats retenus

Synthèse cible :

| Bounded Context | Aggregate Root |
|---|---|
| Accounting Identity | `AccountingEntity` |
| Reference Data | objets read-only / `ReferenceCatalog` côté application |
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
| Reconciliation | `ReconciliationSession` |

---

# 38. Entities principales

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

# 39. Value Objects principaux

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

# 40. Domain Services

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

# 41. Application Services

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

# 42. Repository Ports

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

# 43. Domain Events globaux

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

# 44. Relations inter-contextes

## 44.1 Identity -> tous les contexts

```text
AccountingEntity
    = upstream identity
```

Tous les contextes transactionnels utilisent :

```text
AccountingEntityId
```

---

## 44.2 Reference Data -> Company COA

Relation :

```text
Customer / Supplier
```

Le plan entreprise consomme les références.

Il ne modifie pas la source réglementaire.

---

## 44.3 Company COA -> Journal & Entries

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

## 44.4 Periods -> Posting

Le posting consulte :

```text
AccountingPeriodStatus
```

avant transition.

---

## 44.5 Journal & Entries -> Ledger

Ledger est downstream des lignes postées.

```text
JournalEntryLine
    ->
Ledger Projection
```

---

## 44.6 Imports -> Journal & Entries

L'import produit des écritures via l'Application Layer.

Il ne contourne pas les règles de domaine.

Une policy peut autoriser un import de source déjà validée à créer des écritures directement postées, mais ce comportement doit rester explicite.

---

## 44.7 Ledger -> Financial Statements

```text
TrialBalance
    ->
FinancialStatementEngine
```

---

## 44.8 Reference Data -> Regulatory Reporting

Les structures réglementaires viennent du provider.

---

## 44.9 Controls -> Closing / Reporting

```text
Blocking controls
    ->
can block close/export
```

---

## 44.10 Domain Events -> Audit

L'audit observe ou est appelé explicitement depuis l'application pour les mutations importantes.

---

# 45. Context Map détaillée

```text
[Accounting Identity]
      |
      | Shared IDs
      v
[Accounting Periods] ----------------------+
      |                                    |
      | status                             |
      v                                    |
[Posting & Reversal]                       |
      ^                                    |
      |                                    |
[Journal & Entries] <---- [Accounting Imports]
      ^
      |
      | AccountId
      |
[Company Chart of Accounts]
      ^
      |
      | ACL / Reference Provider
      |
[Accounting Reference Data]

[Journal & Entries]
      |
      | posted lines
      v
[Ledger & Balances]
      |
      +-------------------+
      |                   |
      v                   v
[Controls]        [Financial Statements]
                          |
                          v
                 [Regulatory Reporting]
                          ^
                          |
              [Accounting Reference Data]

[Audit & Traceability]
      ^
      |
      +---- observes commands/events from all contexts

[Reconciliation]
      ^
      |
      +---- consumes ledger / external data
```

---

# 46. Anti-Corruption Layers

## 46.1 Regulatory ACL

```text
regulatory JSON
    ->
Regulatory Adapter
    ->
PyAccountingKit Reference Model
```

---

## 46.2 Django ACL

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

## 46.3 FEC ACL

```text
FEC columns
    ->
FEC Adapter
    ->
Generic Import Model
```

---

# 47. Modèle d'identité

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

# 48. Multi-entity scoping

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

# 49. Modèle monétaire

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

# 50. Multi-devise

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

# 51. Modèle temporel

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

# 52. Status models

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

# 53. Erreurs de domaine

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
+-- ImportDomainError
|
+-- ReportingError
```

Les exceptions ORM ne doivent pas remonter directement dans l'API métier.

---

# 54. Règles de mutation

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

# 55. Règles de lecture

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

# 56. Séparation Write Model / Read Model

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

# 57. Transactions métier

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

# 58. Invariants inter-agrégats

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

# 59. Cohérence forte vs éventuelle

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

# 60. Politique d'immutabilité

Objets candidats à l'immutabilité complète :

```text
Money
AccountCode
ReferenceAccount
AccountingReferenceSnapshot
ControlResult
ReportSnapshot final
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

# 61. Mapping de CFA FRA vers PyAccountingKit

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

# 62. Concepts CFA FRA non repris tels quels

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

# 63. Actor Context

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

# 64. Source Context

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

# 65. Provenance

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

# 66. Reporting provenance

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

# 67. Regulatory provenance

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

# 68. Versioning du modèle

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

# 69. Règles de suppression

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

# 70. Historisation

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

# 71. Extension points

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

# 72. Domain Policy Registry

Pour certains points d'extension, un registry contrôlé peut être utile :

```text
AccountCodePolicyRegistry
ControlRegistry
ImportAdapterRegistry
StatementGeneratorRegistry
```

Ces registries appartiennent plutôt à l'application/integration layer qu'aux entities.

---

# 73. InMemory Model

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

# 74. Boundary tests

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

# 75. Modèle initial de packages

```text
pyaccountingkit/domain/
|
+-- identity/
|   +-- entity.py
|
+-- references/
|   +-- standard.py
|   +-- account.py
|   +-- snapshot.py
|
+-- chart/
|   +-- chart.py
|   +-- account.py
|   +-- policies.py
|
+-- periods/
|   +-- fiscal_year.py
|   +-- period.py
|   +-- closing.py
|
+-- journals/
|   +-- journal.py
|   +-- entry.py
|   +-- line.py
|
+-- posting/
|   +-- validation.py
|   +-- posting.py
|   +-- reversal.py
|
+-- controls/
|   +-- control.py
|   +-- result.py
|
+-- reporting/
|   +-- statements.py
|   +-- mappings.py
|   +-- snapshots.py
|
+-- reconciliation/
    +-- session.py
```

Le ledger et les imports peuvent être principalement répartis entre application, ports et adapters plutôt que forcés dans `domain/`.

---

# 76. Décisions de modélisation actées

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
| ADR-DOM-009 | `RegulatoryAccountBinding` est distinct de `StatementAccountMapping` |
| ADR-DOM-010 | FEC est traduit via Anti-Corruption Layer |
| ADR-DOM-011 | `AccountingImportBatch` protège le workflow d'import sans contenir toutes les raw lines |
| ADR-DOM-012 | `AuditEvent` est append-only |
| ADR-DOM-013 | `ReportSnapshot` final est immutable |
| ADR-DOM-014 | Les heuristiques de mapping ne sont pas des invariants universels |
| ADR-DOM-015 | Les transactions inter-agrégats sont orchestrées par l'Application Layer |
| ADR-DOM-016 | Les read models peuvent être optimisés indépendamment du write model |
| ADR-DOM-017 | Les identités interne, business et réglementaire sont distinctes |
| ADR-DOM-018 | `Money` utilise `Decimal` |
| ADR-DOM-019 | Le multi-entity scoping est obligatoire dans les ports |
| ADR-DOM-020 | Reconciliation reste un supporting context P2 au démarrage |

---

# 77. Priorisation des bounded contexts

## P0 - Premier coeur stable

```text
Accounting Identity
Company Chart of Accounts
Accounting Periods
Journal & Entries
Posting & Reversal
Ledger & Balances
Accounting Reference Data
Audit minimal
```

---

## P1

```text
Accounting Imports
FEC Adapter
Controls
Financial Statements
Regulatory Reporting
Closing avancé
Multi-currency
Auxiliary accounting
```

---

## P2

```text
Reconciliation avancée
Consolidation
Group Chart
Crosswalk automation
Advanced analytical dimensions
```

---

# 78. Scénario end-to-end du domaine

```text
1. Load ReferenceStandard fr-pcg:2026

2. Create AccountingEntity

3. Create CompanyAccountingProfile

4. Generate CompanyChartOfAccounts

5. Create FiscalYear / AccountingPeriods

6. Create Journal

7. Create JournalEntry DRAFT

8. Add JournalEntryLines

9. Validate
      DRAFT -> VALIDATED

10. Post
      VALIDATED -> POSTED

11. Build General Ledger

12. Build Trial Balance

13. Run Controls

14. Build Financial Statements

15. Map to Regulatory Statement

16. Create ReportSnapshot
```

---

# 79. Exemple de scénario multi-référentiels

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

Seules changent :

```text
reference data
company chart policy
reporting mappings
```

---

# 80. Exemple de frontière correcte

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

# 81. Exemple de frontière reporting correcte

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

# 82. Risques de modélisation

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

# 83. Ce qui reste à préciser

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

# 84. Critères d'acceptation du modèle de domaine

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
```

---

# 85. Conclusion

Le modèle de domaine cible repose sur une séparation nette entre :

```text
REFERENCE
    données réglementaires externes

COMPANY MODEL
    plan, comptes, périodes

TRANSACTIONAL CORE
    journaux, écritures, posting, reversal

PROJECTIONS
    ledger, balance

QUALITY
    controls, audit

REPORTING
    financial statements, regulatory reports

INTEGRATIONS
    FEC, Django, SQLAlchemy, API
```

Cette séparation permet de transformer l'expérience fonctionnelle déjà acquise dans CFA FRA en un moteur réutilisable, sans importer l'architecture Django dans le coeur.

Elle permet également de consommer plusieurs standards issus de `regulatory-accounting-data-framework` sans modifier le moteur transactionnel.

Le prochain document doit maintenant figer précisément les règles qui protègent ces agrégats.

---

**Prochain document recommandé :**

```text
03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md
```

Il devra formaliser les invariants comptables, règles de validation, policies de posting, règles de période, immutabilité, extourne, précision monétaire, contraintes inter-agrégats et statut normatif de chaque règle.
