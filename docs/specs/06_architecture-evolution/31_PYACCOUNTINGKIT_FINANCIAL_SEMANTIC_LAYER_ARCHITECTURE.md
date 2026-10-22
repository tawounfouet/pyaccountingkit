# 31_PYACCOUNTINGKIT_FINANCIAL_SEMANTIC_LAYER_ARCHITECTURE.md

# PyAccountingKit — Financial Semantic Layer Architecture

> **Projet** : PyAccountingKit  
> **Document** : `31_PYACCOUNTINGKIT_FINANCIAL_SEMANTIC_LAYER_ARCHITECTURE.md`  
> **Statut** : Spécification d'architecture — P3 / extension analytique transverse  
> **Date** : 22 octobre 2026  
> **Langue** : Français  

---

# 1. Objet du document

Ce document définit l'architecture cible d'une **Financial Semantic Layer** pour PyAccountingKit.

Cette couche a pour objectif de transformer les sorties comptables, réglementaires et analytiques du framework en un modèle sémantique stable, explicite et interopérable pouvant être consommé par :

```text
Power BI
Tableau
Apache Superset
Metabase
notebooks
pandas / Polars
DuckDB
APIs analytiques
applications métier
agents IA
```

La Financial Semantic Layer n'est **pas** un nouveau moteur comptable.

Elle ne devient pas une deuxième source de vérité.

Elle est une couche de lecture située en aval de :

```text
Accounting Core
Ledger
Financial Statements
Financial Analysis
```

et en amont des consommateurs BI et analytiques.

---

# 2. Positionnement dans la baseline PyAccountingKit

Ce document complète notamment :

```text
02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md
13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md
14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md
16_PYACCOUNTINGKIT_PUBLIC_API_DESIGN.md
```

Il ne les remplace pas.

La séparation cible est :

```text
13 — Financial Statements
    = produire les états comptables et réglementaires

14 — Financial Analysis
    = calculer des indicateurs et diagnostics financiers

31 — Financial Semantic Layer
    = exposer ces concepts sous une forme analytique
      cohérente, réutilisable et indépendante du moteur BI
```

---

# 3. Problème adressé

Une application utilisant PyAccountingKit peut déjà produire :

```text
Journal Entries
General Ledger
Trial Balance
Balance Sheet
Income Statement
Cash Flow Statement
Financial Ratios
Financial Indicators
Aging
Subledger balances
```

Mais un outil BI ne doit pas être obligé de comprendre directement :

- les agrégats DDD ;
- les repositories ;
- les tables ORM ;
- les détails du posting engine ;
- les conventions internes d'un adapter ;
- les mappings réglementaires bruts ;
- la structure physique des snapshots.

Sans couche sémantique, chaque consommateur risque de reconstruire ses propres calculs :

```text
Power BI EBITDA
Tableau EBITDA
Notebook EBITDA
API EBITDA
```

avec des définitions potentiellement différentes.

La cible est donc :

```text
UNE définition sémantique canonique
        ↓
PLUSIEURS consommateurs
```

---

# 4. Vision

La Financial Semantic Layer doit permettre d'écrire conceptuellement :

```text
Revenue
EBITDA
WorkingCapital
NetDebt
CurrentRatio
ReceivableAging
CashPosition
```

sans que le consommateur ait besoin de savoir :

```text
dans quelle table
dans quel ORM
dans quel référentiel
dans quelle version du plan
dans quel mapping réglementaire
```

les données sont physiquement stockées.

La couche sémantique doit répondre à :

```text
What does this metric mean?
Where does it come from?
Which period does it represent?
Which entity does it belong to?
Which standard and mapping version produced it?
Which currency is used?
Can the result be reproduced?
```

---

# 5. Principes fondamentaux

## SEM-001 — Downstream only

La couche sémantique consomme le domaine comptable.

Elle ne modifie jamais :

```text
JournalEntry
JournalEntryLine
CompanyAccount
AccountingPeriod
Settlement
```

Flux autorisé :

```text
Accounting Domain
      ↓
Read Models
      ↓
Semantic Layer
```

Flux interdit :

```text
Semantic Layer
      X
Posting Engine
```

---

## SEM-002 — No second accounting engine

La couche sémantique ne doit jamais recalculer une balance à partir de règles différentes du ledger canonique.

Elle consomme :

```text
TrialBalanceSnapshot
LedgerSnapshot
FinancialStatementSnapshot
AnalysisSnapshot
SubledgerSnapshot
```

ou des query contracts équivalents.

---

## SEM-003 — Business meaning over storage

Un concept sémantique doit être défini par son sens métier et non par une colonne SQL.

Éviter :

```text
metric = SUM(table_a.column_17)
```

Préférer :

```text
Revenue
    source concept = recognized operating revenue
    aggregation = SUM
    grain = entity × period × currency
```

---

## SEM-004 — Version everything that changes meaning

La signification d'une mesure peut dépendre de :

```text
Accounting Framework
Reference Edition
Company Chart Version
Statement Mapping Version
Metric Definition Version
Analysis Definition Set
Currency Conversion Policy
Consolidation Scope
Scenario
```

Le semantic model doit conserver ces versions.

---

## SEM-005 — Semantic definitions are explicit

Aucune mesure importante ne doit être cachée dans :

```text
Power BI DAX
Tableau calculation
SQL dashboard query
Excel formula
```

si cette mesure appartient au contrat métier PyAccountingKit.

---

## SEM-006 — Metric != Result

La définition :

```text
CurrentRatioDefinition
```

est distincte du résultat :

```text
CurrentRatioResult
```

Même principe pour :

```text
MetricDefinition
MetricObservation
```

---

## SEM-007 — Undefined is not zero

Une mesure non calculable doit être représentée explicitement.

Exemple :

```text
Current Ratio
denominator = 0
```

ne doit pas automatiquement produire :

```text
0
```

mais un résultat tel que :

```text
status = UNDEFINED
reason = ZERO_DENOMINATOR
```

---

## SEM-008 — Regulatory and analytical semantics are distinct

Un état réglementaire et un KPI analytique peuvent reposer sur les mêmes données mais ne constituent pas la même chose.

```text
Balance Sheet Line
!=
Financial KPI
```

---

# 6. Architecture globale

```text
┌──────────────────────────────────────────────────────────────┐
│                 ACCOUNTING SOURCE OF TRUTH                   │
│                                                              │
│ Journal Entries • Ledger • Subledgers • Reference Data      │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                   CANONICAL READ MODELS                      │
│                                                              │
│ Trial Balance Snapshot                                      │
│ Ledger Snapshot                                             │
│ Financial Statement Snapshot                                │
│ Financial Analysis Snapshot                                 │
│ Aging Snapshot                                              │
│ Cash / Subledger Snapshot                                   │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                 FINANCIAL SEMANTIC LAYER                     │
│                                                              │
│ Dimensions                                                  │
│ Measures                                                    │
│ Metrics                                                     │
│ Calculation Definitions                                     │
│ Hierarchies                                                 │
│ Semantic Relationships                                      │
│ Time Intelligence                                           │
│ Currency Semantics                                          │
│ Provenance / Lineage                                        │
│ Version Context                                             │
└─────────────────────────────┬────────────────────────────────┘
                              │
             ┌────────────────┼──────────────────┐
             ▼                ▼                  ▼
          BI Tools       Python / SQL        APIs / AI
```

---

# 7. Frontières avec les autres bounded contexts

## 7.1 Ledger

Le Ledger possède :

```text
authoritative balances
```

Le Semantic Layer possède :

```text
analytical meaning
```

---

## 7.2 Financial Statements

Financial Statements possède :

```text
statement structure
regulatory presentation
statement mappings
published snapshots
```

Le Semantic Layer peut exposer :

```text
BalanceSheet.TotalAssets
IncomeStatement.Revenue
IncomeStatement.NetIncome
```

mais ne redéfinit pas leur calcul réglementaire.

---

## 7.3 Financial Analysis

Financial Analysis possède :

```text
SIG
EBE
CAF
BFR
FRNG
ratios
scores
diagnostic
```

Le Semantic Layer rend ces concepts accessibles comme :

```text
measures
metrics
dimensions
time series
```

---

## 7.4 Regulatory Reference Data

La couche sémantique consomme les métadonnées utiles telles que :

```text
standard
edition
taxonomy
statement concept
account classification
```

sans dépendre du dataset brut.

---

# 8. Bounded Context — Financial Semantics

La Financial Semantic Layer peut être modélisée comme un bounded context downstream :

```text
Financial Semantics
```

Sa responsabilité est :

> traduire les sorties canoniques de PyAccountingKit en concepts analytiques stables et interopérables.

Il ne possède pas la réalité comptable.

Il possède la **sémantique analytique**.

---

# 9. Concepts principaux

Le modèle sémantique doit distinguer :

```text
SemanticModel
SemanticDataset
Dimension
DimensionMember
Hierarchy
MeasureDefinition
MetricDefinition
MetricObservation
SemanticRelationship
CalculationDefinition
TimeIntelligenceDefinition
CurrencyContext
ScenarioContext
SemanticSnapshot
SemanticManifest
LineageReference
```

---

# 10. `SemanticModel`

Représente un modèle sémantique versionné.

Exemple conceptuel :

```text
FinancialSemanticModel
|
+-- id
+-- code
+-- version
+-- entity scope
+-- source contracts
+-- dimensions
+-- measures
+-- metrics
+-- hierarchies
+-- relationships
+-- policies
+-- status
```

Un modèle peut être :

```text
DRAFT
ACTIVE
DEPRECATED
RETIRED
```

---

# 11. `SemanticDataset`

Représente un ensemble analytique exposable.

Exemples :

```text
GeneralLedgerAnalytics
FinancialStatementsAnalytics
FinancialPerformanceAnalytics
ReceivablesAnalytics
PayablesAnalytics
CashAnalytics
FixedAssetsAnalytics
BudgetVsActualAnalytics
```

Un SemanticDataset possède :

```text
grain
dimensions
measures
source snapshot contract
semantic version
```

---

# 12. Grain

Chaque dataset doit déclarer explicitement son grain.

Exemples :

```text
one row per:
entity × account × period
```

```text
entity × statement_line × period
```

```text
entity × party × aging_bucket × as_of_date
```

```text
entity × metric × period × scenario
```

Aucune mesure ne doit être exposée sans grain identifiable.

---

# 13. Dimensions canoniques

## 13.1 Entity Dimension

```text
Entity
    id
    name
    jurisdiction
    functional_currency
```

---

## 13.2 Time Dimension

```text
Date
Month
Quarter
FiscalPeriod
FiscalYear
```

Doit supporter :

```text
calendar year
fiscal year
period sequence
opening / closing
comparative periods
```

---

## 13.3 Account Dimension

```text
Account
Account Code
Account Label
Account Type
Normal Balance
Parent Account
Reference Binding
```

---

## 13.4 Accounting Framework Dimension

```text
Standard
Edition
Jurisdiction
Dataset Version
```

Exemples :

```text
PCG 2026
SYSCOHADA 2017
OHADA EBNL 2023
PCEMF
```

---

## 13.5 Journal Dimension

```text
Journal
Journal Type
Journal Code
```

---

## 13.6 Party Dimension

```text
Party
Customer
Supplier
Member
Employee
Bank
Other
```

La role dimension doit permettre qu'un même Party possède plusieurs rôles.

---

## 13.7 Statement Dimension

```text
Statement
Section
Line
Regulatory Concept
Display Order
```

---

## 13.8 Scenario Dimension

```text
Actual
Budget
Forecast
Base
Optimistic
Pessimistic
Stress
```

---

## 13.9 Currency Dimension

```text
Transaction Currency
Functional Currency
Presentation Currency
```

---

## 13.10 Analytical Dimensions

Extensions possibles :

```text
Cost Center
Profit Center
Project
Department
Agency
Product
Program
Geography
```

---

# 14. Dimensions conformes

Les dimensions partagées doivent être **conformed dimensions**.

Ainsi :

```text
Entity
Period
Account
Party
Currency
Scenario
```

doivent conserver le même sens entre :

```text
Ledger Analytics
Financial Statements
Financial Analysis
Subledger Analytics
```

Un consommateur peut ainsi croiser les datasets sans recréer des mappings.

---

# 15. Hiérarchies

Exemples :

```text
Account Class
  ↓
Account Group
  ↓
Account
```

```text
Fiscal Year
  ↓
Quarter
  ↓
Period
  ↓
Date
```

```text
Statement
  ↓
Section
  ↓
Subsection
  ↓
Line
```

```text
Organization Group
  ↓
Entity
```

Les hiérarchies doivent être versionnables.

---

# 16. Facts / datasets analytiques recommandés

## 16.1 `FactLedgerBalance`

Grain :

```text
entity × account × period × currency
```

Mesures possibles :

```text
opening_debit
opening_credit
period_debit
period_credit
closing_debit
closing_credit
net_balance
```

---

## 16.2 `FactJournalActivity`

Grain :

```text
entry_line
```

Mesures :

```text
debit
credit
signed_amount
```

Dimensions :

```text
Entity
Date
Period
Account
Journal
Party
Currency
Source
```

---

## 16.3 `FactFinancialStatement`

Grain :

```text
entity × statement_line × period × scenario
```

Mesures :

```text
reported_amount
comparative_amount
```

---

## 16.4 `FactFinancialMetric`

Grain :

```text
entity × metric × period × scenario
```

Contient :

```text
value
unit
status
definition_version
source_snapshot_ids
```

---

## 16.5 `FactReceivableAging`

Grain :

```text
entity × party × obligation × aging_bucket × as_of_date
```

Mesures :

```text
original_amount
outstanding_amount
overdue_amount
```

---

## 16.6 `FactPayableAging`

Même structure conceptuelle côté fournisseurs.

---

## 16.7 `FactCashPosition`

Grain :

```text
entity × cash_account × date × currency
```

---

## 16.8 `FactBudgetActual`

Grain :

```text
entity × account × period × scenario × analytical_dimensions
```

Mesures :

```text
actual
budget
variance
variance_percentage
```

---

# 17. MeasureDefinition

Une mesure est une agrégation sémantique réutilisable.

Exemple :

```text
MeasureDefinition
    code = "revenue"
    label = "Revenue"
    aggregation = SUM
    source_concept = OPERATING_REVENUE
    unit = MONEY
    additive = true
```

---

# 18. MetricDefinition

Une métrique peut être calculée à partir d'autres mesures.

Exemple conceptuel :

```text
MetricDefinition
    code = "current_ratio"
    numerator = CurrentAssets
    denominator = CurrentLiabilities
    unit = RATIO
    undefined_policy = ZERO_DENOMINATOR
```

---

# 19. Définition ≠ observation

```text
MetricDefinition
      ↓ evaluate()MetricObservation
```

Exemple :

```text
CurrentRatio Definition v2
```

produit :

```text
Entity A
FY2026
value = 1.47
```

---

# 20. Catalogue initial de mesures

Le catalogue peut exposer notamment :

```text
Revenue
OperatingExpenses
GrossMargin
ValueAdded
EBITDA / EBE
OperatingIncome
FinancialResult
NetIncome
CashFlow
WorkingCapital
WorkingCapitalRequirement / BFR
NetCash
NetDebt
Equity
TotalAssets
CurrentAssets
CurrentLiabilities
Receivables
Payables
Inventory
Cash
FinancialDebt
```

Le détail réglementaire dépend des mappings et definitions versionnées.

---

# 21. Catalogue initial de ratios

Exemples :

```text
GrossMarginRate
OperatingMargin
EBITDAMargin
NetMargin
CurrentRatio
QuickRatio
DebtRatio
FinancialAutonomyRatio
ROA
ROE
DebtToEBITDA
ReceivableDays
PayableDays
InventoryDays
WorkingCapitalToRevenue
```

Ces définitions appartiennent au framework uniquement si leur sémantique est explicitement définie et versionnée.

---

# 22. Analyse financière comme source doctrinale

La couche sémantique doit être capable de représenter les grandes familles d'analyse financière déjà prévues dans PyAccountingKit :

```text
profitability
liquidity
financial structure
cash generation
working capital
ratios
comparative analysis
```

Elle doit en particulier permettre des séries temporelles et des comparaisons inter-périodes.

---

# 23. Time Intelligence

Le semantic layer doit fournir une abstraction indépendante de DAX ou d'un moteur BI particulier.

Définitions possibles :

```text
PERIOD_VALUE
YTD
QTD
MTD
PRIOR_PERIOD
PRIOR_YEAR
ROLLING_3
ROLLING_12
CHANGE
CHANGE_PERCENT
CAGR
```

---

# 24. Exemple

Conceptuellement :

```text
Revenue_YTD
    =
SUM Revenue from fiscal-year start to current period
```

La définition canonique doit être portable vers différents adapters.

---

# 25. Snapshot semantics

Les métriques doivent indiquer si elles représentent :

```text
FLOW
STOCK
AVERAGE
RATIO
CUMULATIVE
```

Exemples :

```text
Revenue = FLOW
Cash = STOCK
AverageReceivables = AVERAGE
CurrentRatio = RATIO
```

Cela évite des agrégations temporelles incorrectes.

---

# 26. Additivité

Chaque mesure doit déclarer son comportement.

```text
ADDITIVE
SEMI_ADDITIVE
NON_ADDITIVE
```

Exemples :

```text
Revenue
    additive across periods

Cash Balance
    not additive across periods

Ratio
    non-additive
```

---

# 27. Currency semantics

Une valeur monétaire doit préciser :

```text
currency
currency_role
conversion_policy
rate_date
rate_type
```

Rôles :

```text
TRANSACTION
FUNCTIONAL
PRESENTATION
```

---

# 28. Interdiction des conversions implicites

Jamais :

```text
EUR + USD
```

sans politique explicite.

La couche sémantique doit soit :

```text
reject
```

soit :

```text
convert using explicit CurrencyConversionContext
```

---

# 29. CurrencyConversionContext

Exemple :

```text
CurrencyConversionContext
    source_currency
    target_currency
    rate_type
    effective_date
    exchange_rate_source
    exchange_rate_version
```

---

# 30. Multi-référentiels

Le semantic model ne doit pas supposer que :

```text
account code = universal meaning
```

Il doit s'appuyer sur :

```text
canonical concepts
+
reference mappings
+
statement mappings
```

Exemple :

```text
PCG Account 707
SYSCOHADA equivalent
Custom ERP account
        ↓
Canonical Revenue Concept
```

---

# 31. Canonical Semantic Concept

Un concept sémantique peut fournir un pivot entre référentiels.

```text
SemanticConcept
    id
    code
    label
    concept_type
    metadata
```

Exemples :

```text
REVENUE
CASH
TRADE_RECEIVABLES
TRADE_PAYABLES
EQUITY
FINANCIAL_DEBT
```

---

# 32. Mapping sémantique

```text
Company Account
        ↓
Regulatory Binding
        ↓
Semantic Concept
        ↓
Measure
```

Cette chaîne doit rester auditable.

---

# 33. Source contracts

La Financial Semantic Layer ne doit pas requêter directement les tables ORM.

Elle consomme des ports de lecture.

Exemples :

```python
class TrialBalanceSemanticSource(Protocol):
    def get_snapshot(...) -> TrialBalanceSemanticInput: ...

class FinancialStatementSemanticSource(Protocol):
    def get_snapshot(...) -> StatementSemanticInput: ...

class FinancialAnalysisSemanticSource(Protocol):
    def get_snapshot(...) -> AnalysisSemanticInput: ...
```

---

# 34. Semantic DTOs

Les DTOs d'entrée doivent être :

```text
immutable
versioned
framework-neutral
```

Ils ne doivent pas exposer :

```text
Django Model
SQLAlchemy Session
SQL Row
```

---

# 35. Semantic Query Engine

La couche peut fournir un moteur de query conceptuel :

```text
SemanticQuery
    dataset
    dimensions
    measures
    filters
    time_context
    currency_context
    scenario
```

Exemple :

```python
query = SemanticQuery(
    dataset="financial_performance",
    dimensions=["fiscal_year", "entity"],
    measures=["revenue", "ebitda", "net_income"],
)
```

---

# 36. Résultat

```text
SemanticResult
    columns
    rows
    metadata
    lineage
    manifest
```

Le résultat ne dépend pas d'un outil BI particulier.

---

# 37. API publique cible

Extension possible de :

```text
AccountingApplication
```

avec :

```text
accounting.semantic
```

Exemple :

```python
result = accounting.semantic.query(
    dataset="financial_performance",
    entity_id=entity_id,
    measures=["revenue", "ebitda", "net_income"],
    period_range=period_range,
)
```

---

# 38. API de métadonnées

```python
model = accounting.semantic.get_model("financial_core")

metrics = accounting.semantic.list_metrics()

definition = accounting.semantic.get_metric_definition("current_ratio")
```

---

# 39. Exposition vers Power BI

PyAccountingKit ne doit pas dépendre de Power BI.

Un adapter dédié peut exposer :

```text
SemanticModel
      ↓
Power BI Adapter
      ↓
star schema / semantic model metadata
```

L'adapter peut générer ou alimenter :

```text
facts
dimensions
relationships
measure metadata
```

mais les formules canoniques restent définies en amont.

---

# 40. Exposition vers Tableau / Superset

Même principe :

```text
Canonical Semantic Model
      ↓
Adapter
      ↓
Tool-specific representation
```

Pas de logique métier divergente par outil.

---

# 41. SQL Semantic Adapter

Une implémentation possible peut produire :

```text
views
materialized views
tables
```

Exemple :

```text
semantic.dim_entity
semantic.dim_account
semantic.dim_period
semantic.fact_ledger_balance
semantic.fact_financial_metric
```

Ces objets restent des read models.

---

# 42. DataFrame Adapter

Un adapter peut produire :

```text
pandas.DataFrame
Polars.DataFrame
Arrow Table
```

sans modifier le modèle métier.

---

# 43. DuckDB / local analytics

Pour les cas embarqués ou notebooks :

```text
Semantic Snapshot
      ↓
Parquet / Arrow
      ↓
DuckDB
```

peut fournir un mode analytique léger.

---

# 44. Star Schema

Le star schema est une projection possible, non une contrainte du domaine.

Exemple :

```text
                  dim_period
                      |
dim_entity -- fact_financial_metric -- dim_metric
                      |
                 dim_scenario
                      |
                 dim_currency
```

---

# 45. Modèle Ledger analytique

```text
                 dim_account
                     |
dim_entity -- fact_ledger_balance -- dim_period
                     |
                 dim_currency
```

---

# 46. Model Financial Statements

```text
                   dim_statement_line
                           |
dim_entity -- fact_financial_statement -- dim_period
                           |
                      dim_scenario
```

---

# 47. Model Aging

```text
                     dim_party
                         |
dim_entity -- fact_receivable_aging -- dim_aging_bucket
                         |
                     dim_date
```

---

# 48. Semantic lineage

Toute mesure importante doit pouvoir expliquer sa provenance.

Exemple :

```text
EBITDA
  ↓
MetricDefinition v3
  ↓
SemanticConcepts
  ↓
Statement / account mappings
  ↓
TrialBalanceSnapshot
  ↓
Ledger state
```

---

# 49. LineageReference

Concept :

```text
LineageReference
    source_type
    source_id
    source_version
    checksum?
```

---

# 50. Explicabilité

Un consommateur doit pouvoir demander :

```text
Why is EBITDA = 2,450,000 EUR?
```

La réponse doit pouvoir référencer :

- définition de la métrique ;
- version ;
- période ;
- entité ;
- source snapshots ;
- mappings ;
- currency context ;
- composants intermédiaires.

---

# 51. SemanticManifest

Chaque génération matérialisée peut produire :

```text
SemanticManifest
```

contenant :

```text
pyaccountingkit_version
semantic_model_version
dataset_definition_version
metric_definition_set_version
reference_standard
reference_edition
mapping_versions
source_snapshot_ids
source_snapshot_checksums
currency_policy_version
generated_at
output_checksum
```

---

# 52. Reproductibilité

À données et versions identiques :

```text
same canonical inputs
+
same semantic definitions
+
same policies
=
same semantic output
```

La reproductibilité constitue un objectif de premier ordre.

---

# 53. SemanticSnapshot

Un snapshot matérialisé est immuable.

Exemple :

```text
FinancialSemanticSnapshot
    id
    model_version
    entity_id
    period
    generated_at
    manifest_id
    checksum
```

---

# 54. Live model vs snapshot

Deux modes sont possibles :

```text
LIVE
SNAPSHOT
```

## LIVE

Calcul à la demande.

Avantages :

```text
fresh
```

## SNAPSHOT

Résultat figé.

Avantages :

```text
audit
reproducibility
publication
comparison
```

---

# 55. Security boundary

Le semantic layer doit respecter le scope :

```text
tenant
organization
accounting entity
```

Aucun query engine ne doit permettre un accès cross-tenant implicite.

---

# 56. Row-level filtering

L'implémentation peut appliquer :

```text
tenant_id
entity_id
authorized_scope
```

mais la stratégie de sécurité applicative reste extérieure au cœur comptable.

---

# 57. Sensitive dimensions

Certaines dimensions peuvent contenir :

```text
party
employee
supplier
customer
```

Elles doivent pouvoir être :

```text
hidden
masked
restricted
```

selon l'intégration.

---

# 58. Performance

La couche doit permettre :

```text
query pushdown
pre-aggregation
materialized snapshots
columnar exports
incremental refresh
partitioning
```

sans changer la définition métier.

---

# 59. Incremental refresh

Le semantic dataset doit pouvoir indiquer :

```text
refresh grain
watermark
source revision
```

Exemple :

```text
refresh only periods impacted since last ledger revision
```

---

# 60. Cache

Un cache est autorisé uniquement si sa clé inclut les éléments qui affectent le résultat.

Exemple :

```text
model_version
entity_id
period
scenario
currency_context
source_revision
```

---

# 61. Invalidations

Les événements suivants peuvent invalider une projection :

```text
JournalEntryPosted
JournalEntryReversed
PeriodReopened
StatementMappingChanged
MetricDefinitionChanged
ReferenceVersionChanged
CurrencyPolicyChanged
```

---

# 62. Event-driven refresh

Une implémentation peut consommer l'outbox pour planifier :

```text
semantic refresh
```

mais le refresh reste un effet downstream.

---

# 63. Scénarios

La couche doit nativement distinguer :

```text
ACTUAL
BUDGET
FORECAST
```

et permettre :

```text
Actual vs Budget
Actual vs Forecast
N vs N-1
```

sans mélanger les sources.

---

# 64. Comparative Analysis

Concept :

```text
ComparisonContext
    base_period
    comparison_period
    base_scenario
    comparison_scenario
```

---

# 65. Variance measures

Définitions possibles :

```text
Variance = Actual - Reference
VariancePercent = Variance / Reference
```

avec règles explicites de division par zéro.

---

# 66. Budget integration

Le budget ne doit pas être artificiellement converti en écritures comptables réelles.

Il reste une source analytique distincte :

```text
Actual Ledger
       │
       ├─── Semantic Layer
       │
Budget Model
       │
       └─── Semantic Layer
```

---

# 67. Consolidation

La couche sémantique peut exposer :

```text
entity-level
group-level
consolidated
```

mais la logique :

```text
elimination
goodwill
minority interests
currency translation
```

reste dans le bounded context Consolidation.

---

# 68. Multi-entity reporting

Dimension :

```text
Group
Entity
```

permet :

```text
group drill-down
entity comparison
```

sans recalculer la consolidation.

---

# 69. Drill-down

Le semantic layer doit pouvoir naviguer :

```text
KPI
  ↓
Statement Line
  ↓
Account
  ↓
Journal Entry
  ↓
Entry Line
```
selon les permissions.

---

# 70. Drill-through contract

Un résultat peut exposer :

```text
drill_targets
```

mais sans inclure automatiquement toutes les écritures dans la réponse.

---

# 71. Semantic metadata

Chaque measure/metric doit pouvoir exposer :

```text
code
label
description
unit
format
aggregation behavior
definition version
applicable dimensions
source concepts
status
```

---

# 72. Localization

Les labels peuvent être localisés :

```text
fr
en
es
```

sans changer le code canonique.

Exemple :

```text
code = "net_income"

fr = "Résultat net"
en = "Net income"
```

---

# 73. Stable codes

Le code canonique constitue le contrat machine.

Le label est présentation.

```text
net_income
```

reste stable même si le libellé évolue.

---

# 74. Units

Types possibles :

```text
MONEY
PERCENTAGE
RATIO
DAYS
COUNT
QUANTITY
INDEX
```

---

# 75. Formatting

Le format d'affichage ne doit pas altérer la valeur.

Exemple :

```text
stored semantic value = Decimal("0.1537")
display = 15.37 %
```

---

# 76. Null semantics

Le modèle doit distinguer :

```text
0
NULL
UNDEFINED
NOT_APPLICABLE
NOT_AVAILABLE
```

---

# 77. MetricStatus

Exemple :

```text
VALID
UNDEFINED
NOT_APPLICABLE
MISSING_INPUT
STALE
ERROR
```

---

# 78. Freshness

Un dataset peut exposer :

```text
source_revision
generated_at
freshness_status
```

afin qu'un dashboard sache si le résultat est à jour.

---

# 79. Quality metadata

Des indicateurs peuvent accompagner les résultats :

```text
complete
reconciled
period_closed
source_validated
```

---

# 80. Closed-period semantics

Un consommateur doit pouvoir distinguer :

```text
provisional data
```

de :

```text
closed / published data
```

Dimension ou metadata :

```text
AccountingDataStatus
```

---

# 81. Public API — Query

Concept possible :

```python
result = accounting.semantic.query(
    dataset="ledger_balances",
    entity_id=entity_id,
    dimensions=("account", "fiscal_period"),
    measures=("debit", "credit", "net_balance"),
    filters={...},
)
```

---

# 82. Public API — Metrics

```python
result = accounting.semantic.metrics.evaluate(
    entity_id=entity_id,
    metric_codes=(
        "working_capital",
        "working_capital_requirement",
        "net_cash",
        "current_ratio",
    ),
    period_id=period_id,
)
```

---

# 83. Public API — Metadata

```python
metadata = accounting.semantic.describe(
    dataset="financial_performance"
)
```

---

# 84. Public API — Lineage

```python
lineage = accounting.semantic.explain(
    metric_code="ebitda",
    observation_id=observation_id,
)
```

---

# 85. Extension API

Les adapter authors peuvent implémenter :

```text
SemanticStorageAdapter
SemanticExportAdapter
SemanticBIAdapter
SemanticCacheAdapter
```

sans changer les contrats métier.

---

# 86. BI-specific adapters

Exemples futurs :

```text
pyaccountingkit.adapters.semantic.powerbi
pyaccountingkit.adapters.semantic.tableau
pyaccountingkit.adapters.semantic.superset
pyaccountingkit.adapters.semantic.arrow
pyaccountingkit.adapters.semantic.duckdb
```

Ces packages doivent rester optionnels.

---

# 87. Anti-pattern — direct ORM BI

Interdit comme architecture de référence :

```text
Power BI
    ↓
raw Django tables
```

car les tables physiques ne sont pas un contrat métier stable.

---

# 88. Anti-pattern — DAX as business source of truth

Interdit :

```text
EBITDA logic only exists in PBIX
```

La définition canonique doit vivre dans PyAccountingKit ou son definition registry.

---

# 89. Anti-pattern — metrics duplicated per dashboard

Interdit :

```text
Dashboard A CurrentRatio v1
Dashboard B CurrentRatio v2
Excel CurrentRatio v3
```

sans version métier explicite.

---

# 90. Anti-pattern — star schema as domain model

Le star schema est une projection analytique.

Il ne doit pas déterminer la conception des aggregates DDD.

---

# 91. Anti-pattern — silent currency mixing

Interdit :

```text
SUM(EUR, USD, XAF)
```

sans conversion explicite.

---

# 92. Anti-pattern — account-code semantics

Interdit :

```text
if account.code.startswith("7"):
    revenue += amount
```

comme contrat universel.

Le code dépend du référentiel.

---

# 93. Anti-pattern — mutable published semantic snapshot

Un snapshot publié doit être immutable.

Toute correction crée :

```text
new semantic snapshot
```

---

# 94. Tests unitaires

Tester :

```text
metric definitions
aggregation semantics
time intelligence
currency behavior
null semantics
hierarchies
version resolution
```

---

# 95. Property-based tests

Exemples :

```text
Revenue(period A + period B)
=
Revenue(A) + Revenue(B)
```

uniquement pour une mesure déclarée additive.

---

# 96. Contract tests

Tout adapter sémantique doit respecter :

```text
same semantic input
→ semantically equivalent output
```

---

# 97. Golden semantic model

Créer un jeu de données de référence contenant :

```text
ledger
statements
analysis
aging
budget
```

avec outputs attendus.

---

# 98. Golden scenario — P&L

```text
Journal Entries
      ↓
Trial Balance
      ↓
Income Statement
      ↓
Semantic Revenue / EBITDA / Net Income
      ↓
BI export
```

Les valeurs doivent rester identiques.

---

# 99. Golden scenario — Balance Sheet

```text
Ledger Snapshot
      ↓
Balance Sheet
      ↓
Semantic Assets / Equity / Debt
      ↓
Ratios
```

---

# 100. Golden scenario — Working Capital

```text
Receivables
Payables
Inventory
      ↓
BFR
      ↓
Working Capital Analysis
```

---

# 101. Golden scenario — Aging

```text
Invoices
Payments
Settlements
      ↓
Outstanding
      ↓
Aging Buckets
      ↓
Semantic Aging Dataset
```

---

# 102. Cross-adapter equivalence

Le même dataset exporté vers :

```text
DataFrame
SQL
Power BI adapter
```

doit conserver :

```text
grain
measure values
dimension keys
semantic version
```

---

# 103. Snapshot reproducibility test

Given :

```text
same source checksums
same semantic model version
same mapping versions
same currency policy
```

then :

```text
output checksum
```

doit être stable.

---

# 104. Architecture fitness rules

La CI devra pouvoir protéger :

```text
semantic.domain
    X adapters

semantic.domain
    X django

semantic.domain
    X sqlalchemy

semantic.domain
    X powerbi SDK
```

---

# 105. Dependency direction

```text
semantic domain
      ↑
semantic application
      ↑
semantic ports
      ↑
semantic adapters
```

Les adapters dépendent des contrats, jamais l'inverse.

---

# 106. Package topology possible

Dans une future organisation domain-first :

```text
pyaccountingkit/
└── semantic/
    ├── domain/
    │   ├── model.py
    │   ├── dimensions.py
    │   ├── measures.py
    │   ├── metrics.py
    │   ├── lineage.py
    │   └── manifests.py
    ├── application/
    │   ├── queries.py
    │   ├── evaluation.py
    │   └── snapshots.py
    ├── ports/
    │   ├── sources.py
    │   ├── storage.py
    │   └── exporters.py
    └── adapters/
        ├── memory/
        ├── arrow/
        ├── sql/
        └── powerbi/
```

---

# 107. Compatibilité avec la topologie actuelle

Avant une migration domain-first, une structure transitoire peut être :

```text
domain/semantic/
application/semantic/
ports/semantic/
adapters/semantic/
```

La public API doit masquer le déplacement physique.

---

# 108. Matrice de responsabilité

| Capability | Owner |
|---|---|
| Journal correctness | Ledger |
| Trial Balance | Ledger |
| Statement calculation | Financial Statements |
| Regulatory layout | Regulatory Reporting |
| Financial ratios | Financial Analysis |
| Semantic dimensions | Financial Semantics |
| Semantic measures | Financial Semantics |
| BI model export | Semantic Adapter |
| DAX/tool syntax | Adapter uniquement |
| Source of truth | Accounting Core / Snapshots |
| Metric lineage | Financial Semantics |
| BI visualization | Consumer |

---

# 109. Définition d'une mesure portable

Exemple conceptuel :

```yaml
code: revenue
label:
  fr: Chiffre d'affaires
  en: Revenue
unit: money
semantic_type: flow
aggregation: sum
additivity:
  time: additive
  entity: additive_if_same_currency_or_converted
sources:
  - concept: OPERATING_REVENUE
version: 1
```

Le format physique exact reste à définir.

---

# 110. Définition d'une métrique portable

```yaml
code: current_ratio
label:
  fr: Ratio de liquidité générale
  en: Current Ratio
unit: ratio
numerator: current_assets
denominator: current_liabilities
zero_denominator: undefined
version: 1
```

---

# 111. Expression language

Un futur moteur peut introduire une DSL contrôlée.

Exemple :

```text
metric.current_ratio =
    measure.current_assets
    /
    measure.current_liabilities
```

La DSL doit être :

```text
deterministic
safe
versioned
portable
```

---

# 112. Pas de Python arbitraire par défaut

Une métrique réglementaire ou publique ne doit pas dépendre d'un script arbitraire non versionné.

Les extensions Python peuvent exister mais doivent être encapsulées comme providers explicites.

---

# 113. Semantic registry

Un registry instance-scoped peut contenir :

```text
dimensions
measures
metrics
datasets
hierarchies
```

Pas de registre global modifiable au moment de l'import.

---

# 114. DefinitionSet

Les définitions peuvent être regroupées :

```text
FinancialSemanticDefinitionSet
    version
    measures
    metrics
    dimensions
```

---

# 115. Versioning

Il faut distinguer :

```text
PyAccountingKit package version
Semantic API contract version
Semantic model version
Metric definition version
Regulatory reference version
Dataset version
```

Ces versions ne doivent pas être confondues.

---

# 116. Breaking semantic change

Exemples :

```text
changer la formule d'un KPI
changer son unité
changer son grain
changer le sens d'une dimension
```

doivent déclencher une nouvelle version sémantique.

---

# 117. Non-breaking change

Exemples possibles :

```text
ajouter un label
ajouter une métrique optionnelle
ajouter un adapter
```

si les contrats existants restent inchangés.

---

# 118. Deprecation

Une définition peut suivre :

```text
ACTIVE
→ DEPRECATED
→ RETIRED
```

avec référence éventuelle vers :

```text
superseded_by
```

---

# 119. Data contracts

Chaque SemanticDataset doit publier un contrat comprenant :

```text
dataset code
version
grain
dimensions
measures
types
nullability
freshness
source contract
```

---

# 120. Semantic schema manifest

Artifact possible :

```text
SEMANTIC_MODEL_MANIFEST.json
```

contenant :

```text
models
datasets
dimensions
measures
metrics
versions
relationships
```

---

# 121. Metric contract manifest

Artifact possible :

```text
FINANCIAL_METRIC_MANIFEST.json
```

pour détecter les changements de définition.

---

# 122. Compatibility gate

Une release peut comparer :

```text
previous semantic manifest
vs
current semantic manifest
```

et refuser une rupture silencieuse.

---

# 123. Public documentation

Chaque métrique publique doit documenter :

```text
business meaning
formula
inputs
unit
grain
time semantics
currency semantics
undefined behavior
version
examples
```

---

# 124. Discoverability

Un consommateur doit pouvoir demander :

```python
accounting.semantic.list_datasets()
accounting.semantic.list_dimensions(...)
accounting.semantic.list_measures(...)
accounting.semantic.list_metrics(...)
```

---

# 125. Notebook experience

Exemple cible :

```python
df = accounting.semantic.query(
    dataset="financial_performance",
    dimensions=("fiscal_year",),
    measures=("revenue", "ebitda", "net_income"),
).to_pandas()
```

---

# 126. BI experience

L'utilisateur BI doit voir :

```text
Financial Performance
    Revenue
    EBITDA
    EBITDA Margin
    Operating Income
    Net Income

Liquidity
    Working Capital
    BFR
    Current Ratio
    Quick Ratio

Structure
    Equity
    Financial Debt
    Net Debt
    Debt Ratio
```

plutôt que des colonnes techniques.

---

# 127. AI consumption

Une API sémantique peut également aider des agents IA à demander :

```text
"Compare EBITDA margin over the last 3 fiscal years"
```

sans leur donner accès directement aux tables transactionnelles.

---

# 128. AI safety / correctness boundary

L'IA peut :

```text
query
summarize
compare
explain
```

mais ne doit pas inventer une définition de métrique absente du registry.

---

# 129. Provenance for AI

Les réponses analytiques peuvent inclure :

```text
metric definition id
source snapshot ids
period
currency
semantic model version
```

pour réduire les interprétations ambiguës.

---

# 130. Observability

Métriques techniques possibles :

```text
semantic_query_count
semantic_query_latency
semantic_cache_hit
semantic_snapshot_generation_duration
semantic_refresh_failures
```

---

# 131. Audit events

Événements possibles :

```text
SemanticSnapshotGenerated
SemanticModelActivated
MetricDefinitionChanged
SemanticDatasetPublished
SemanticExportProduced
```

---

# 132. Domain events vs audit

Ces événements sémantiques ne doivent pas être confondus avec les événements comptables.

Ils décrivent la production analytique, pas une mutation du ledger.

---
# 133. Failure semantics

Erreurs possibles :

```text
UNKNOWN_SEMANTIC_DATASET
UNKNOWN_MEASURE
UNKNOWN_METRIC
INCOMPATIBLE_DIMENSIONS
UNSUPPORTED_AGGREGATION
CURRENCY_CONTEXT_REQUIRED
SOURCE_SNAPSHOT_MISSING
SEMANTIC_VERSION_MISMATCH
METRIC_UNDEFINED
```

---

# 134. Fail-closed

Si une métrique dépend d'un mapping versionné indisponible :

```text
do not guess
```

Le résultat doit être :

```text
MISSING_INPUT
```

ou une erreur explicite.

---

# 135. Materialization policy

Une définition peut spécifier :

```text
ON_DEMAND
ON_PERIOD_CLOSE
ON_EVENT
SCHEDULED
```

La politique de scheduling appartient à l'application/runtime, pas au domaine.

---

# 136. Publication workflow

Exemple :

```text
Build Semantic Snapshot
      ↓
Validate
      ↓
Reconcile
      ↓
Publish
```

Un snapshot publié devient immutable.

---

# 137. Validation

Contrôles possibles :

```text
totals reconcile with source snapshot
required dimensions exist
metric definitions resolve
currency context is valid
source versions are compatible
```

---

# 138. Reconciliation

Exemple :

```text
Semantic Total Assets
==
Published Balance Sheet Total Assets
```

```text
Semantic Net Income
==
Published Income Statement Net Income
```

selon le modèle concerné.

---

# 139. BI qualification

Un adapter BI est qualifié si :

```text
canonical dataset
→ adapter export
→ consumer read
```

conserve les résultats attendus.

---

# 140. Consumer E2E

Scénario :

```text
PyAccountingKit
      ↓
FinancialSemanticSnapshot
      ↓
Power BI / SQL / DataFrame adapter
      ↓
consumer
      ↓
same expected KPI
```

---

# 141. Performance qualification

Benchmarks à définir :

```text
1 entity / 1 year
10 entities / 5 years
100 entities / 10 years
large journal dataset
large aging dataset
```

---

# 142. Scalability

La couche sémantique doit permettre un futur backend :

```text
in-memory
SQL
warehouse
lakehouse
columnar
```

sans modifier la définition des métriques.

---

# 143. Semantic warehouse boundary

PyAccountingKit ne devient pas :

```text
a data warehouse product
```

Il fournit :

```text
semantic contracts
read models
portable definitions
adapters
```

---

# 144. Relation avec dbt

Un adapter ou consumer peut matérialiser les contracts avec dbt.

Mais :

```text
dbt
```

n'est pas une dépendance du core semantic domain.

---

# 145. Relation avec Power BI semantic model

Le modèle Power BI est une cible d'export.

Il ne doit pas devenir la définition canonique.

```text
PyAccountingKit Semantic Model
         ↓
Power BI projection
```

---

# 146. Relation avec Microsoft Fabric

Même logique :

```text
Semantic Snapshot
      ↓
Lakehouse / Warehouse
      ↓
Fabric Semantic Model
```

Cette intégration est optionnelle.

---

# 147. Relation avec OLAP

Des dimensions et mesures peuvent être exposées vers un moteur OLAP futur.

Le contrat PyAccountingKit reste indépendant du moteur.

---

# 148. Relation avec APIs

Une API REST/GraphQL peut exposer :

```text
datasets
dimensions
metrics
observations
lineage
```

mais le transport ne fait pas partie du contrat métier.

---

# 149. Relation avec exports

Formats possibles :

```text
CSV
Parquet
Arrow
JSON
```

Le format physique est adapter-specific.

---

# 150. Exemple de modèle sémantique complet

```text
FinancialCoreModel v1
│
├── Dimensions
│   ├── Entity
│   ├── Period
│   ├── Account
│   ├── Party
│   ├── Currency
│   ├── Scenario
│   └── AccountingFramework
│
├── Datasets
│   ├── LedgerBalance
│   ├── FinancialStatements
│   ├── FinancialPerformance
│   ├── ReceivableAging
│   └── CashPosition
│
├── Measures
│   ├── Revenue
│   ├── EBITDA
│   ├── NetIncome
│   ├── TotalAssets
│   ├── Equity
│   ├── Debt
│   └── Cash
│
└── Metrics
    ├── EBITDAMargin
    ├── CurrentRatio
    ├── DebtRatio
    ├── ROA
    ├── ROE
    └── NetDebtToEBITDA
```

---

# 151. Architecture physique possible

```text
PyAccountingKit
     │
     ▼
Semantic Application Service
     │
     ├── InMemory Semantic Store
     ├── SQL Semantic Store
     ├── Arrow/Parquet Exporter
     └── BI Adapters
```

---

# 152. MVP recommandé

Le MVP ne doit pas commencer par Power BI.

Il doit commencer par le contrat canonique.

### MVP-01

```text
SemanticModel
DimensionDefinition
MeasureDefinition
MetricDefinition
SemanticDataset
SemanticQuery
SemanticResult
```

### MVP-02

```text
LedgerBalance dataset
FinancialStatement dataset
FinancialMetric dataset
```

### MVP-03

```text
pandas/Polars or Arrow adapter
```

### MVP-04

```text
SQL/star-schema adapter
```

### MVP-05

```text
Power BI-oriented export
```

---

# 153. Ordre d'implémentation recommandé

```text
SEM-00 — Semantic primitives
SEM-01 — Dimension registry
SEM-02 — Measure registry
SEM-03 — Metric definitions
SEM-04 — Source ports
SEM-05 — Semantic query engine
SEM-06 — Lineage
SEM-07 — Semantic manifests
SEM-08 — Snapshot materialization
SEM-09 — DataFrame / Arrow adapter
SEM-10 — SQL adapter
SEM-11 — BI adapter contract
SEM-12 — Power BI adapter
SEM-13 — Golden qualification
SEM-14 — Public API stabilization
```

---

# 154. Critères d'acceptation

La première version peut être considérée comme complète lorsque :

```text
[ ] SemanticModel existe
[ ] SemanticDataset existe
[ ] grain explicite pour chaque dataset
[ ] dimensions conformes définies
[ ] MeasureDefinition définie
[ ] MetricDefinition définie
[ ] MetricObservation définie
[ ] time semantics définies
[ ] additivity définie
[ ] currency semantics définies
[ ] null / undefined semantics définies
[ ] lineage disponible
[ ] manifest de reproductibilité disponible
[ ] TrialBalance source contract disponible
[ ] FinancialStatement source contract disponible
[ ] FinancialAnalysis source contract disponible
[ ] query API framework-neutral disponible
[ ] aucun ORM dans l'API
[ ] aucun moteur BI obligatoire
[ ] semantic snapshot immutable
[ ] cross-tenant protection définie
[ ] golden accounting → semantic scenario vert
[ ] au moins un adapter tabulaire vert
[ ] au moins un adapter SQL ou BI vert
```

---

# 155. ADRs proposées

| ID | Décision |
|---|---|
| ADR-SEM-001 | Financial Semantic Layer est downstream et read-only |
| ADR-SEM-002 | Le ledger canonique reste la source de vérité |
| ADR-SEM-003 | Les projections analytiques ne sont pas des agrégats comptables |
| ADR-SEM-004 | Les mesures canoniques ne vivent pas uniquement dans un outil BI |
| ADR-SEM-005 | MetricDefinition est distincte de MetricObservation |
| ADR-SEM-006 | Chaque SemanticDataset déclare son grain |
| ADR-SEM-007 | Les dimensions communes sont conformes |
| ADR-SEM-008 | Les mesures déclarent leur additivité |
| ADR-SEM-009 | Les mesures monétaires déclarent leur currency semantics |
| ADR-SEM-010 | Les conversions de devise implicites sont interdites |
| ADR-SEM-011 | AccountCode n'est jamais une sémantique universelle |
| ADR-SEM-012 | Le semantic model est multi-référentiels |
| ADR-SEM-013 | Les définitions de métriques sont versionnées |
| ADR-SEM-014 | Les snapshots publiés sont immuables |
| ADR-SEM-015 | Lineage et provenance sont de première classe |
| ADR-SEM-016 | SemanticManifest capture les versions et sources |
| ADR-SEM-017 | La public API n'expose aucun ORM |
| ADR-SEM-018 | Les adapters Power BI/Tableau restent optionnels |
| ADR-SEM-019 | Le star schema est une projection, pas le modèle de domaine |
| ADR-SEM-020 | Le semantic layer peut être consommé sans BI |
| ADR-SEM-021 | Undefined, Missing et Zero sont distincts |
| ADR-SEM-022 | Les calculs sémantiques sont déterministes |
| ADR-SEM-023 | Les métriques publiques exposent leur définition |
| ADR-SEM-024 | Les ruptures sémantiques sont versionnées |
| ADR-SEM-025 | Les résultats doivent être réconciliables avec leurs sources canoniques |

---

# 156. Relation avec les sources doctrinales

La doctrine comptable utilisée par PyAccountingKit rappelle que la comptabilité constitue un système d'information destiné à mesurer la valeur des moyens et des résultats d'une entité, et que différentes conceptions comptables peuvent conduire à différentes représentations.

La couche sémantique doit donc éviter de présenter ses concepts comme universels lorsqu'ils dépendent :

```text
d'un référentiel
d'une méthode d'évaluation
d'une convention analytique
d'une définition de ratio
```

Elle doit rendre ce contexte explicite.

Pour l'analyse financière, la couche doit pouvoir représenter les concepts déjà couverts dans la documentation du projet et dans les sources doctrinales associées :

```text
bilan
compte de résultat
SIG
EBE
CAF
BFR
tableaux de flux
ratios
rentabilité
liquidité
structure financière
```

sans les confondre avec le moteur comptable transactionnel.

---

# 157. Positionnement final

La chaîne cible devient :

```text
ECONOMIC EVENTS
       ↓
ACCOUNTING DOMAIN
       ↓
GENERAL LEDGER
       ↓
CANONICAL SNAPSHOTS
       ↓
FINANCIAL STATEMENTS
       ↓
FINANCIAL ANALYSIS
       ↓
FINANCIAL SEMANTIC LAYER
       ↓
BI / DATA / AI CONSUMERS
```

La Financial Semantic Layer est donc :

```text
not a ledger
not a data warehouse
not a BI tool
not an ORM model
```

mais :

> **un contrat sémantique versionné qui donne un sens analytique stable aux sorties financières de PyAccountingKit.**

---

# 158. Conclusion

L'ajout d'une Financial Semantic Layer permet à PyAccountingKit de franchir une frontière importante.

Le framework ne fournit plus seulement :

```text
correct accounting data
```

mais également :

```text
consistently interpretable financial data
```

La cible finale est :

```text
One Accounting Core
        ↓
One Canonical Financial Semantics
        ↓
Many Consumers
```

Cela évite :

```text
one metric definition per dashboard
one accounting interpretation per BI tool
one mapping per consumer
```

et permet à PyAccountingKit de devenir un socle commun entre :

```text
comptabilité
reporting réglementaire
analyse financière
data analytics
business intelligence
IA
```

tout en conservant les principes fondamentaux du projet :

```text
domain first
multi-standard
auditable
deterministic
versioned
framework-neutral
fail-closed
reproducible
```