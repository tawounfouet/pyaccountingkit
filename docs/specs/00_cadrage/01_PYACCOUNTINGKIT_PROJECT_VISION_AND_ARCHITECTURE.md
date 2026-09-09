# 01 - PyAccountingKit - Vision du projet et architecture cible

> **Projet** : PyAccountingKit  
> **Document** : `01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`  
> **Document parent** : `00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`  
> **Statut** : P0.2 - Macro-architecture mise à jour  
> **Langue** : Français  
> **Objet** : Définir la vision produit, la macro-architecture, les responsabilités de chaque couche, les flux de dépendance, les frontières de domaine et la trajectoire d'extraction de PyAccountingKit en intégrant les nouveaux axes `Accounting Policies & Measurement` et `Financial Analysis`.

---

# 1. Résumé exécutif

PyAccountingKit est destiné à devenir un **framework Python générique de comptabilité financière**.

Il ne doit pas être :

```text
un ERP complet
un logiciel comptable avec UI imposée
un clone du projet CFA FRA
un wrapper du regulatory-accounting-data-framework
un plan comptable codé en dur
un moteur universel de corporate finance
```

Il doit être :

```text
un moteur comptable générique
+
un modèle de policies comptables explicites
+
un système de plans comptables d'entreprise multi-référentiels
+
un moteur de posting / ledger / clôture
+
un moteur de reporting financier et réglementaire
+
un read-side d'analyse financière
+
des ports et adapters réutilisables
```

La macro-architecture cible est désormais :

```text
REFERENCE
    |
    v
ACCOUNTING POLICIES & MEASUREMENT
    |
    v
ACCOUNTING CORE
    |
    v
LEDGER
    |
    v
REPORTING
    |
    v
FINANCIAL ANALYSIS
```

Cette chaîne est enrichie transversalement par :

```text
Controls
Audit
Traceability
Imports
Persistence
Concurrency
Adapters
```

---

# 2. Les quatre sources de spécification

PyAccountingKit est construit à partir de quatre sources complémentaires.

## 2.1 Source réglementaire

```text
regulatory-accounting-data-framework
```

Responsabilité :

```text
décrire ce que le référentiel réglementaire EST
```

Il fournit notamment :

- structures de plans ;
- comptes réglementaires ;
- plans effectifs ;
- overlays ;
- modèles de reporting ;
- relations entre standards ;
- crosswalks ;
- concepts ;
- provenance ;
- validation.

---

## 2.2 Référence fonctionnelle exécutable

```text
cfa_fra_django_mvp_sprint_7
```

Responsabilité dans la spécification :

```text
démontrer des comportements comptables déjà implémentés
```

Il apporte notamment :

- organisations ;
- exercices ;
- périodes ;
- comptes ;
- journaux ;
- écritures ;
- partie double ;
- workflow `DRAFT -> VALIDATED -> POSTED -> REVERSED` ;
- posting ;
- reversal ;
- audit ;
- import FEC ;
- ledger ;
- balance ;
- reporting ;
- mappings ;
- snapshots ;
- tests.

CFA FRA est une **référence fonctionnelle** et un futur consommateur de PyAccountingKit. Il ne constitue pas une dépendance du coeur.

---

## 2.3 Source doctrinale comptable

```text
Comptabilité générale - Système français et normes IFRS
```

Rôle :

```text
formaliser le langage comptable,
les méthodes,
les mécanismes de reconnaissance et d'évaluation,
les traitements d'inventaire,
les états financiers,
la consolidation.
```

Cette source doctrinale ne remplace jamais une règle réglementaire versionnée.

---

## 2.4 Source doctrinale d'analyse financière

```text
Maxi fiches de Gestion financière de l'entreprise
```

Rôle :

```text
formaliser les indicateurs et méthodes
du read-side analytique.
```

Domaines concernés :

```text
SIG
EBE
EBITDA
CAF
FRNG
BFR
trésorerie nette
ratios
scores
diagnostics
tableaux de financement
tableaux de flux
```

---

# 3. Hiérarchie d'autorité

En cas de divergence, l'architecture respecte l'ordre suivant :

```text
1. Référentiel réglementaire versionné et validé
2. AccountingPolicySet / configuration explicite de l'organisation
3. Invariant comptable générique du domaine
4. Référence fonctionnelle CFA FRA
5. Source doctrinale
6. Heuristique / suggestion
```

Une heuristique ne devient jamais normative silencieusement.

---

# 4. Vision du produit

La vision cible est :

> Fournir une infrastructure Python de comptabilité financière permettant de construire des produits comptables fiables, auditables, multi-référentiels et extensibles, sans réimplémenter le moteur comptable, les policies d'évaluation, les projections financières et les contrôles dans chaque application.

Une application cliente doit pouvoir se concentrer sur :

- UX ;
- workflows ;
- identité / IAM ;
- orchestration ;
- stockage ;
- API ;
- intégrations spécifiques ;

tout en déléguant à PyAccountingKit :

- modèle comptable ;
- plan de comptes ;
- policies ;
- règles de validation ;
- posting ;
- reversal ;
- ledger ;
- clôture ;
- contrôles ;
- audit ;
- reporting ;
- analyse financière.

---

# 5. Proposition de valeur

PyAccountingKit doit rendre possible :

```text
1 moteur comptable
        +
N référentiels réglementaires
        +
N politiques comptables
        +
N plans d'entreprise
        +
N formats d'import
        +
N adapters techniques
        +
N définitions de reporting
        +
N définitions analytiques
```

sans couplage structurel entre ces dimensions.

---

# 6. Positionnement fonctionnel

PyAccountingKit couvre :

```text
Accounting Infrastructure
Accounting Policies
Company Accounting Model
Accounting Execution
Ledger & Closing
Financial Reporting
Regulatory Reporting
Financial Analysis
Controls & Audit
```

Il ne couvre pas par défaut :

```text
CRM
ERP complet
facturation complète
paie complète
IAM
UI
WACC
VAN / NPV
TRI / IRR
valorisation d'entreprise
gestion de portefeuille d'investissement
```

---

# 7. Macro-architecture cible

```text
+--------------------------------------------------------------+
|             regulatory-accounting-data-framework             |
|                                                              |
| Standards / Accounts / Effective Plans / Reporting /         |
| Relations / Crosswalks / Concepts / Provenance / Validation  |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
|                    REFERENCE LAYER                           |
|                                                              |
| AccountingReferenceProvider                                  |
| ReferenceCatalog                                             |
| ReferenceStandard                                            |
| ReferenceAccount                                             |
| ReferenceStatementDefinition                                 |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
|              ACCOUNTING POLICIES & MEASUREMENT               |
|                                                              |
| AccountingPolicySet                                          |
| RecognitionPolicy                                            |
| MeasurementPolicy                                            |
| DepreciationPolicy                                           |
| ImpairmentPolicy                                             |
| InventoryValuationPolicy                                     |
| AccrualPolicy                                                |
| ProvisionPolicy                                              |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
|                   ACCOUNTING CORE                            |
|                                                              |
| AccountingEntity                                             |
| CompanyChartOfAccounts                                       |
| CompanyAccount                                               |
| FiscalYear / AccountingPeriod                                |
| Journal / JournalEntry / JournalEntryLine                    |
| Validation / Posting / Reversal                              |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
|                        LEDGER                                |
|                                                              |
| General Ledger                                               |
| Account Balance                                              |
| Trial Balance                                                |
| Closing / Opening                                            |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
|                       REPORTING                              |
|                                                              |
| Financial Statements                                        |
| Regulatory Reporting                                        |
| Statement Mappings                                           |
| ReportSnapshot                                               |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
|                  FINANCIAL ANALYSIS                          |
|                                                              |
| SIG / EBE / CAF                                              |
| FRNG / BFR / Treasury                                        |
| Ratios                                                       |
| Scores / Diagnostics                                         |
| AnalysisSnapshot                                             |
+--------------------------------------------------------------+
```

---

# 8. Capacités transversales

Les couches précédentes sont accompagnées de capacités transversales.

```text
Controls
Audit
Traceability
Imports
Concurrency
Persistence
Observability
Security Context
Adapters
```

Elles ne doivent pas inverser les dépendances métier.

---

# 9. Principe Reference -> Policies -> Accounting Core

Cette séquence est fondamentale.

```text
Reference
    = structure et règle externe disponible

Policy
    = méthode applicable dans un contexte donné

Accounting Core
    = exécution transactionnelle
```

Exemple :

```text
ReferenceStandard
    fr-pcg:2026

        +
AccountingPolicySet
    company-fr-v3

        |
        v

CompanyAccount
JournalEntry
Posting
```

Le moteur transactionnel ne doit pas savoir directement :

```text
"si IFRS alors..."
"si PCG alors..."
```

Il reçoit des policies explicites.

---

# 10. Pourquoi introduire `Accounting Policies & Measurement`

Le coeur initial distinguait surtout :

```text
Reference
Accounting Core
Ledger
Reporting
```

Cette vision était insuffisante.

Les traitements comptables nécessitent de distinguer :

```text
Recognition
Measurement
Posting
Presentation
Analysis
```

Exemple :

```text
événement économique
    |
    v
RecognitionPolicy
    |
    v
MeasurementPolicy
    |
    v
JournalEntry
    |
    v
PostingEngine
    |
    v
Ledger
    |
    v
StatementMapping
    |
    v
Financial Analysis
```

Ces étapes ne doivent pas être confondues.

---

# 11. `AccountingPolicySet`

Une entité ou un ledger doit pouvoir utiliser un ensemble versionné de policies.

```text
AccountingPolicySet
|
+-- RecognitionPolicy
+-- MeasurementPolicy
+-- DepreciationPolicy
+-- ImpairmentPolicy
+-- InventoryValuationPolicy
+-- AccrualPolicy
+-- ProvisionPolicy
+-- RoundingPolicy
```

Le `AccountingPolicySet` doit pouvoir dépendre de :

```text
standard
edition
jurisdiction
sector
entity
effective date
company choice
```

---

# 12. Portée des policies

Une policy peut être :

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

Une policy doit déclarer explicitement sa portée.

---

# 13. `PolicyExecutionTrace`

Toute policy générant une valeur ou une écriture doit pouvoir produire une trace.

```text
PolicyExecutionTrace
|
+-- policy_id
+-- policy_version
+-- effective_date
+-- inputs
+-- calculation
+-- result
+-- generated_entry_id?
+-- reference_snapshot
+-- metadata
```

Cette trace soutient :

- audit ;
- reproductibilité ;
- tests ;
- explication ;
- migration de policy.

---

# 14. Accounting Core

Le coeur transactionnel conserve les primitives validées par CFA FRA.

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

Le coeur protège :

```text
identité
partie double
statuts
périodes
comptes actifs
workflow
posting
reversal
immutabilité
```

---

# 15. Source comptable canonique

La source transactionnelle canonique est :

```text
JournalEntry
+
JournalEntryLine
+
CompanyAccount
+
AccountingPeriod
```

Les projections suivantes sont dérivées :

```text
Journal report
General Ledger
Trial Balance
Financial Statements
Financial Analysis
```

Elles ne deviennent pas des sources comptables indépendantes.

---

# 16. Workflow des écritures

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

Interdit :

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

# 17. Ledger

Le Ledger est downstream des écritures postées.

```text
POSTED JournalEntryLine
        |
        v
General Ledger
        |
        v
Trial Balance
```

Le Ledger doit pouvoir produire :

```text
opening balance
debit
credit
running balance
closing balance
```

---

# 18. Variantes de balance

Les variantes déjà éprouvées sont conservées :

```text
BEFORE_ADJUSTMENTS
ADJUSTED
POST_CLOSING
```

Le contenu exact de chaque variante doit être défini par policy et documenté.

---

# 19. Closing Architecture

La clôture est un processus coordonné :

```text
Ledger
    |
    v
Closing Controls
    |
    v
Accrual / Provision / Adjustment Policies
    |
    v
Generated Closing Entries
    |
    v
Posting
    |
    v
Post-closing Trial Balance
    |
    v
Close / Lock Period
```

La clôture ne doit pas être une simple modification de statut de période.

---

# 20. Accounting Imports

Le domaine générique connaît :

```text
ExternalAccountingSource
RawRecord
ImportBatch
ImportIssue
Mapping
NormalizedEntry
```

Pipeline :

```text
Source
    |
    v
Raw
    |
    v
Parse
    |
    v
Validate
    |
    v
Map
    |
    v
Normalize
    |
    v
JournalEntry
```

---

# 21. FEC comme adapter

Le FEC est spécifique au contexte français.

Il doit être un adapter :

```text
FEC
    |
    v
FEC Adapter
    |
    v
Generic Accounting Import
    |
    v
JournalEntry
```

Le coeur ne connaît pas les noms de colonnes FEC.

---

# 22. Financial Statements

Les états financiers sont des projections du ledger.

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
Financial Statement
```

Etats principaux :

```text
Income Statement
Balance Sheet
Cash Flow Statement
```

---

# 23. Séparation des mappings

L'architecture distingue :

```text
CompanyAccount
    |
    v
RegulatoryAccountBinding
    |
    v
ReferenceAccount
```

de :

```text
CompanyAccount / TrialBalanceRow
    |
    v
StatementAccountMapping
    |
    v
StatementLine
```

et de :

```text
StatementLine
    |
    v
RegulatoryStatementMapping
    |
    v
ReferenceStatementLine
```

Ces trois relations ont des responsabilités différentes.

---

# 24. Regulatory Reporting

Pipeline :

```text
Financial Statement
        |
        v
RegulatoryStatementMapping
        |
        v
Target Regulatory Statement
        |
        v
Regulatory Controls
        |
        v
ReportSnapshot
        |
        v
Export Adapter
```

---

# 25. `ReportSnapshot`

Une publication réglementaire doit pouvoir être figée.

```text
ReportSnapshot
|
+-- entity
+-- fiscal year / period
+-- chart version
+-- AccountingPolicySet version
+-- reference snapshot
+-- mapping versions
+-- statement definitions
+-- line values
+-- controls
+-- warnings
+-- comparatives
+-- generated_at
+-- checksum
```

---

# 26. Financial Analysis

`Financial Analysis` devient un bounded context explicite et séparé.

Il est :

```text
read-only
downstream
versioned
explainable
drill-down capable
```

Il ne peut pas modifier :

```text
JournalEntry
JournalEntryLine
CompanyAccount
AccountingPeriod
```

---

# 27. Architecture Financial Analysis

```text
POSTED JournalEntryLine
        |
        v
Ledger
        |
        v
Trial Balance
        |
        v
Financial Statements
        |
        v
Financial Analysis Engine
        |
        +--> SIG
        +--> EBE / EBITDA
        +--> CAF
        +--> FRNG / BFR
        +--> Net Treasury
        +--> Ratios
        +--> Scores
        +--> Diagnostics
```

---

# 28. `FinancialIndicatorDefinition`

Un indicateur analytique doit être data-driven ou policy-driven.

```text
FinancialIndicatorDefinition
|
+-- code
+-- label
+-- category
+-- formula / computation strategy
+-- dependencies
+-- version
+-- applicability
+-- provenance
```

Exemples :

```text
EBE
CAF
FRNG
BFR
NET_TREASURY
NET_MARGIN
CURRENT_RATIO
```

---

# 29. SIG

Le moteur pourra supporter une définition versionnée des soldes intermédiaires de gestion.

```text
Marge commerciale
Production
Valeur ajoutée
EBE
Résultat d'exploitation
Résultat courant
Résultat exceptionnel
Résultat net
```

Ces concepts ne sont pas codés comme invariants universels.

Ils appartiennent à une définition analytique applicable à un contexte.

---

# 30. CAF

La CAF est une projection analytique.

Le moteur doit permettre plusieurs stratégies :

```text
additive
subtractive
custom / regulatory-specific
```

La stratégie utilisée doit être identifiable.

---

# 31. Analyse fonctionnelle

Le moteur analytique doit pouvoir représenter :

```text
FRNG
BFRE
BFRHE
BFR
Net Treasury
```

Cette analyse dépend d'une classification fonctionnelle explicite.

---

# 32. Ratios

Les ratios doivent être regroupés par familles :

```text
Activity
Profitability
Liquidity
Capital Structure
Cash Flow
```

Un ratio doit exposer :

```text
numerator
denominator
period
unit
definition version
source values
```

---

# 33. Scores et diagnostics

Les scores sont analytiques.

```text
FinancialScoreDefinition
FinancialScoreResult
FinancialDiagnostic
```

Ils ne peuvent jamais bloquer le posting d'une écriture par défaut.

---

# 34. Drill-down analytique

Tout indicateur doit pouvoir être expliqué :

```text
Indicator
    |
    v
Statement / Balance components
    |
    v
Trial Balance rows
    |
    v
Ledger rows
    |
    v
JournalEntryLine
```

Le drill-down est une propriété architecturale, pas uniquement une fonctionnalité UI.

---

# 35. Frontière avec la Corporate Finance

La frontière initiale est :

```text
PyAccountingKit Financial Analysis
    |
    +-- SIG
    +-- CAF
    +-- FRNG / BFR
    +-- treasury
    +-- ratios
    +-- diagnostics

Corporate Finance extension
    |
    +-- NPV / VAN
    +-- IRR / TRI
    +-- WACC
    +-- investment decisions
    +-- financing strategy
    +-- enterprise valuation
    +-- Monte Carlo investment risk
```

Cette frontière protège la cohérence du produit.

---

# 36. Architecture en couches

```text
+------------------------------------------------------+
|                    Public API                        |
+------------------------------------------------------+
                          |
                          v
+------------------------------------------------------+
|                  Application Layer                   |
| Commands / Queries / Use Cases / Orchestration       |
+------------------------------------------------------+
                          |
                          v
+------------------------------------------------------+
|                    Domain Layer                      |
| Entities / Aggregates / VO / Policies / Rules        |
+------------------------------------------------------+
                          ^
                          |
+------------------------------------------------------+
|                        Ports                         |
| Repositories / UoW / Reference / Audit / Clock       |
+------------------------------------------------------+
                          ^
                          |
+------------------------------------------------------+
|                       Adapters                       |
| InMemory / SQLAlchemy / Django / FEC / HTTP Ref      |
+------------------------------------------------------+
```

---

# 37. Règles de dépendance

```text
adapters
    -> application
        -> domain
```

Interdit :

```text
domain -> Django
domain -> SQLAlchemy
domain -> FastAPI
domain -> FEC
domain -> regulatory JSON loader
```

---

# 38. Architecture logique du package

```text
src/pyaccountingkit/
|
+-- core/
|
+-- domain/
|   |
|   +-- identity/
|   +-- references/
|   +-- policies/
|   +-- chart/
|   +-- periods/
|   +-- journals/
|   +-- posting/
|   +-- closing/
|   +-- controls/
|   +-- reporting/
|   +-- financial_analysis/
|   +-- audit/
|
+-- application/
|   |
|   +-- commands/
|   +-- queries/
|   +-- services/
|   +-- dto/
|
+-- ports/
|   |
|   +-- repositories/
|   +-- unit_of_work.py
|   +-- references.py
|   +-- audit.py
|   +-- storage.py
|   +-- clock.py
|
+-- adapters/
|   |
|   +-- memory/
|   +-- regulatory/
|   +-- imports/
|
+-- integrations/
    |
    +-- sqlalchemy/
    +-- django/
    +-- fec/
    +-- fastapi/
```

---

# 39. `core`

`core` contient uniquement des primitives transverses :

```text
Typed IDs
Money
Currency
Clock
Date ranges
Errors
Result
Decimal policies
```

Il ne contient pas :

```text
PCG
SYSCOHADA
IFRS
FEC
Django
```

---

# 40. `domain`

Le domaine porte :

```text
AccountingEntity
AccountingPolicySet
CompanyChartOfAccounts
CompanyAccount
Journal
JournalEntry
AccountingPeriod
Posting rules
Closing policies
Control definitions
Statement definitions
Financial indicator definitions
```

---

# 41. `application`

La couche application orchestre :

```text
CreateCompanyChart
SelectAccountingPolicySet
CreateJournalEntry
ValidateJournalEntry
PostJournalEntry
ReverseJournalEntry
CloseAccountingPeriod
ImportAccountingData
BuildGeneralLedger
BuildTrialBalance
GenerateFinancialStatement
GenerateRegulatoryReport
ComputeFinancialAnalysis
CreateReportSnapshot
```

---

# 42. Commands et Queries

## Commands

```text
create
validate
post
reverse
close
import
bind
map
activate
deactivate
```

## Queries

```text
ledger
trial balance
financial statements
financial indicators
audit history
reference lookup
mapping diagnostics
```

Une query ne doit pas modifier le domaine.

---

# 43. Ports principaux

```text
AccountingEntityRepository
CompanyChartRepository
AccountRepository
JournalRepository
JournalEntryRepository
AccountingPeriodRepository

AccountingPolicyRepository
AccountingReferenceProvider

UnitOfWork
Clock
IdFactory
AuditPort

LedgerQueryPort
TrialBalanceQueryPort
FinancialStatementQueryPort
FinancialAnalysisQueryPort
```

---

# 44. Persistence Agnostic

Le domaine ne connaît pas :

```text
PostgreSQL
SQLite
SQL Server
Django ORM
SQLAlchemy
```

Les adapters choisissent la technologie.

---

# 45. Concurrence

Cas critiques :

```text
double validate
double post
double reverse
double close
double import
```

Le domaine exige une transition atomique.

Les adapters peuvent implémenter :

```text
pessimistic locking
optimistic concurrency
SELECT FOR UPDATE
version columns
```

---

# 46. Unit of Work

Pattern cible :

```python
with unit_of_work:
    entry = repository.get(...)
    posting_service.post(entry, ...)
    repository.save(entry)
    unit_of_work.commit()
```

Le domaine ne démarre pas une transaction SQL.

---

# 47. Audit

L'audit est append-only.

```text
AuditEvent
|
+-- event_type
+-- entity_type
+-- entity_id
+-- actor
+-- before
+-- after
+-- metadata
+-- policy_trace?
+-- source
+-- occurred_at
```

---

# 48. Controls

Architecture :

```text
AccountingContext
    |
    v
AccountingControl
    |
    v
ControlResult
```

Exemples :

```text
ENTRY_BALANCED
ACCOUNT_ACTIVE
PERIOD_OPEN
TRIAL_BALANCE_BALANCED
BALANCE_SHEET_BALANCED
CASHFLOW_RECONCILED
TEMPORARY_ACCOUNTS_CLOSED
```

---

# 49. Controls vs Policies

```text
Policy
    = détermine comment traiter / calculer

Control
    = vérifie un résultat ou une condition
```

Exemple :

```text
DepreciationPolicy
    -> calcule un amortissement

DEPRECIATION_CONTROL
    -> vérifie la cohérence du résultat
```

---

# 50. Observabilité

Le coeur fournit :

```text
operation ids
correlation ids
domain events
structured audit events
error taxonomy
timing hooks
```

L'application peut utiliser :

```text
OpenTelemetry
Prometheus
Sentry
structured logging
```

---

# 51. Sécurité

Le framework ne gère pas directement :

```text
login
password
cookies
MFA
CSRF
```

Il supporte :

```text
ActorContext
AccountingEntity scoping
audit
authorization hooks
immutable posted data
safe error handling
```

---

# 52. Multi-entité

Tous les objets métier sont scopés par :

```text
AccountingEntityId
```

Le scoping doit être présent dans les repositories et query ports.

---

# 53. Money

Tous les montants utilisent :

```text
Decimal
```

et une abstraction :

```text
Money(amount, currency)
```

Le `float` est interdit pour les montants comptables.

---

# 54. Multi-devise

Concepts prévus :

```text
TransactionCurrency
FunctionalCurrency
ExchangeRate
TransactionAmount
FunctionalAmount
```

Le modèle exact sera précisé dans un document spécialisé ou dans les policies.

---

# 55. Temps

Utiliser :

```text
Clock
SystemClock
FixedClock
```

et distinguer :

```text
DocumentDate
AccountingDate
PostingDate
TechnicalTimestamp
```

---

# 56. Identités

Séparer :

```text
internal identity
business code
regulatory identity
```

Exemple :

```text
AccountId
    UUID

AccountCode
    "51200001"

ReferenceAccountId
    "account:fr-pcg:2026:512"
```

---

# 57. Gestion des erreurs

Hiérarchie initiale :

```text
AccountingError
|
+-- ValidationError
+-- PostingError
+-- PeriodError
+-- AccountError
+-- PolicyError
+-- MeasurementError
+-- ReferenceError
+-- ImportError
+-- ReportingError
+-- FinancialAnalysisError
```

---

# 58. Idempotence

A traiter explicitement pour :

```text
imports
external commands
reference loading
policy execution when replayed
report snapshot creation
migration operations
```

---

# 59. Extensibilité

Points d'extension :

```text
new reference provider
new accounting policy
new measurement basis
new account code policy
new import adapter
new control
new statement definition
new financial indicator
new persistence adapter
new reconciliation strategy
```

---

# 60. Dépendances optionnelles

Proposition :

```text
pyaccountingkit
pyaccountingkit[sqlalchemy]
pyaccountingkit[django]
pyaccountingkit[fec]
pyaccountingkit[fastapi]
```

La décision finale de packaging sera prise lors du bootstrap.

---

# 61. Stratégie d'extraction de CFA FRA

Processus :

```text
CFA FRA behavior
      |
      v
identify invariant / policy / query
      |
      v
create PyAccountingKit abstraction
      |
      v
golden test
      |
      v
framework implementation
      |
      v
Django adapter
      |
      v
migrate CFA FRA
```

---

# 62. Classification des éléments CFA FRA

A conserver :

```text
entry workflow
posting
reversal
audit
transaction boundaries
FEC provenance
ledger semantics
trial balance variants
statement mappings
report snapshots
golden tests
```

A ne pas conserver dans le coeur :

```text
Django Models
Views
Forms
HTMX
Templates
Admin
Sessions
ORM calls
request objects
```

---

# 63. Heuristiques

Les règles du type :

```text
if code.startswith("6")
if code.startswith("7")
```

doivent être classées comme :

```text
SuggestionStrategy
MigrationHeuristic
ReferenceSpecificRule
```

jamais comme invariant universel.

---

# 64. Golden Tests

Les scénarios CFA FRA doivent produire des fixtures attendues.

```text
Scenario
    |
    +-- journal entries
    +-- trial balance
    +-- income statement
    +-- balance sheet
    +-- cash flow
    +-- controls
    |
    v
Expected Results
```

PyAccountingKit doit reproduire ces résultats lorsque le contexte et les policies sont identiques.

---

# 65. Tests des policies

Chaque policy doit être testée séparément de l'infrastructure.

Tests :

```text
inputs
effective context
expected recognition
expected measurement
expected generated entry
expected trace
```

---

# 66. Tests analytiques

Les indicateurs doivent disposer de golden datasets.

```text
source trial balance
+
definition version
=
expected indicator values
```

---

# 67. Anti-patterns

## 67.1 Standard codé en dur

```python
if country == "FR":
```

dans le coeur.

## 67.2 Policy cachée dans un service technique

```text
ORM repository
    contains depreciation logic
```

## 67.3 Analyse financière mutante

Un ratio ne doit jamais générer une écriture.

## 67.4 Report stocké comme source primaire

Le reporting reste dérivé.

## 67.5 FEC dans le domaine universel

Le FEC reste un adapter.

## 67.6 Mapping candidat exécuté silencieusement

Une suggestion n'est pas normative.

---

# 68. Architecture Django

```text
Django View / DRF
        |
        v
Application Adapter
        |
        v
PyAccountingKit Command / Query
        |
        v
Django Repository Adapter
        |
        v
Django ORM
        |
        v
PostgreSQL
```

---

# 69. Architecture FastAPI

```text
FastAPI Router
      |
      v
Dependency Injection
      |
      v
PyAccountingKit Application Service
      |
      v
SQLAlchemy Adapter
      |
      v
Database
```

---

# 70. Architecture CLI / Batch

```text
CLI
 |
 v
Application Command
 |
 v
PyAccountingKit
 |
 v
Adapters
```

---

# 71. Roadmap architecturale

## Phase 1 - Foundation

```text
core primitives
typed ids
Money
Clock
errors
```

## Phase 2 - Reference

```text
ReferenceProvider
ReferenceCatalog
ReferenceAccount
ReferenceSnapshot
```

## Phase 3 - Policies

```text
AccountingPolicySet
RecognitionPolicy
MeasurementPolicy
PolicyExecutionTrace
```

## Phase 4 - Accounting Core

```text
entity
chart
accounts
journals
entries
periods
validation
```

## Phase 5 - Posting & Ledger

```text
posting
reversal
general ledger
trial balance
```

## Phase 6 - Closing

```text
accruals
provisions
adjustments
closing
opening
```

## Phase 7 - Controls & Audit

```text
control engine
audit trail
traceability
```

## Phase 8 - Reporting

```text
financial statements
regulatory mappings
ReportSnapshot
```

## Phase 9 - Financial Analysis

```text
SIG
CAF
FRNG / BFR
ratios
diagnostics
AnalysisSnapshot
```

## Phase 10 - Imports & Integrations

```text
generic imports
FEC
SQLAlchemy
Django
FastAPI
```

---

# 72. Architecture documentaire alignée

```text
00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md
    [MAJ P0.1 - terminé]

01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md
    [MAJ P0.2 - présent document]

02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md
    [MAJ P0.3]

03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md

04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md

05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md

06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md

07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md

08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md

09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md

10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md

11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md

12_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md

13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md

14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md

15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md

16_PYACCOUNTINGKIT_PUBLIC_API_DESIGN.md

17_PYACCOUNTINGKIT_RELEASE_AND_VERSIONING_STRATEGY.md

18_PYACCOUNTINGKIT_CFA_FRA_EXTRACTION_AND_MIGRATION_MAP.md

19_PYACCOUNTINGKIT_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX.md

20_PYACCOUNTINGKIT_ADR_REGISTER.md

21_PYACCOUNTINGKIT_CONSOLIDATION_ARCHITECTURE.md

22_PYACCOUNTINGKIT_RECONCILIATION_ARCHITECTURE.md

23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md
```

---

# 73. ADRs structurants

| ID | Décision |
|---|---|
| ADR-ARCH-001 | Architecture domain-first et ports/adapters |
| ADR-ARCH-002 | Django et SQLAlchemy restent hors du domaine |
| ADR-ARCH-003 | `regulatory-accounting-data-framework` est consommé via provider |
| ADR-ARCH-004 | CFA FRA est une référence comportementale, pas une dépendance |
| ADR-ARCH-005 | Les ouvrages sont des sources doctrinales, pas des sources réglementaires actuelles |
| ADR-ARCH-006 | La chaîne cible est `Reference -> Policies -> Core -> Ledger -> Reporting -> Analysis` |
| ADR-ARCH-007 | `AccountingPolicySet` est versionné |
| ADR-ARCH-008 | Recognition, Measurement, Posting, Presentation et Analysis sont distincts |
| ADR-ARCH-009 | Entries/lines/accounts/periods forment la source canonique minimale |
| ADR-ARCH-010 | Ledger et états financiers sont des projections |
| ADR-ARCH-011 | Financial Analysis est downstream et read-only |
| ADR-ARCH-012 | Posting et reversal sont transactionnels |
| ADR-ARCH-013 | FEC est un adapter optionnel |
| ADR-ARCH-014 | Mapping réglementaire et mapping de présentation sont distincts |
| ADR-ARCH-015 | Les publications peuvent être figées dans `ReportSnapshot` |
| ADR-ARCH-016 | Les résultats analytiques peuvent être figés dans `AnalysisSnapshot` |
| ADR-ARCH-017 | Les heuristiques sont des suggestions/configurations |
| ADR-ARCH-018 | Corporate finance avancée est hors coeur obligatoire |
| ADR-ARCH-019 | Le package démarre comme repository unique avec extensions optionnelles |

---

# 74. Critères d'architecture

```text
[ ] le domaine peut être importé sans Django
[ ] les tests du domaine fonctionnent sans base
[ ] un standard est chargeable via ReferenceProvider
[ ] un AccountingPolicySet est sélectionnable explicitement
[ ] une policy peut produire une trace reproductible
[ ] un compte entreprise garde sa référence réglementaire
[ ] le posting fonctionne via UnitOfWork
[ ] une écriture postée est immuable
[ ] une reversal est traçable
[ ] le ledger est reconstruit depuis les lignes postées
[ ] les balances sont des projections
[ ] le FEC est branchable comme adapter
[ ] les mappings réglementaires ont un statut explicite
[ ] un ReportSnapshot est sérialisable
[ ] Financial Analysis ne modifie pas le ledger
[ ] un indicateur peut être drill-down jusqu'à l'écriture
[ ] CFA FRA peut être migré progressivement
```

---

# 75. Architecture cible synthétique

```text
                    REGULATORY DATA
                         |
                         v
                +------------------+
                |    Reference     |
                +--------+---------+
                         |
                         v
                +------------------+
                |     Policies     |
                | Recognition      |
                | Measurement      |
                +--------+---------+
                         |
                         v
                +------------------+
                | Accounting Core  |
                | Entries / Period |
                +--------+---------+
                         |
                         v
                +------------------+
                |      Ledger      |
                +--------+---------+
                         |
                         v
                +------------------+
                |    Reporting     |
                +--------+---------+
                         |
                         v
                +------------------+
                | Financial        |
                | Analysis         |
                +------------------+
```

Transversal :

```text
Controls
Audit
Traceability
Imports
Persistence
Concurrency
Adapters
```

---

# 76. Conclusion

La macro-architecture de PyAccountingKit évolue d'un simple moteur :

```text
Reference
    -> Accounting Core
    -> Ledger
    -> Reporting
```

vers une architecture plus correcte et plus durable :

```text
Reference
    -> Accounting Policies & Measurement
    -> Accounting Core
    -> Ledger
    -> Reporting
    -> Financial Analysis
```

Cette évolution est importante car elle empêche plusieurs confusions :

```text
référentiel != policy
policy != posting
posting != présentation
présentation != analyse
analyse != corporate finance
```

Le framework peut ainsi :

- consommer plusieurs référentiels ;
- appliquer des méthodes comptables différentes ;
- conserver un moteur transactionnel unique ;
- produire des états reproductibles ;
- dériver une analyse financière riche ;
- rester indépendant de Django et de l'infrastructure ;
- évoluer sans transformer chaque variation comptable en `if/else` dans le coeur.

---

**Prochaine action recommandée :**

```text
MAJ 02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md
```

avec introduction explicite des bounded contexts :

```text
Accounting Policies & Measurement
Financial Analysis
```

et préparation des supporting contexts :

```text
Fixed Assets
Inventory
Accruals & Provisions
Operational Subledgers
Consolidation
```


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

## Plans d'implémentation principaux

Ce document est couvert par les plans suivants :

- [PLAN-00 — Repository Bootstrap (0.0.1)](../../plans/PLAN-00_REPOSITORY_BOOTSTRAP_0.0.1.md)
- [PLAN-01 — Accounting Core (0.1.0)](../../plans/PLAN-01_ACCOUNTING_CORE_0.1.0.md)
