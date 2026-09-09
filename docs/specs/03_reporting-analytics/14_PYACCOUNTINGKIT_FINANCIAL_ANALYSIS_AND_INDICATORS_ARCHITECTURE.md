# 14 - PyAccountingKit - Architecture de l'analyse financière et des indicateurs

> **Projet** : PyAccountingKit  
> **Document** : `14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md`  
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
> - `10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md`
> - `11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md`
> - `12_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md`
> - `13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md`
> **Statut** : P1.3 - Architecture de l'analyse financière et des indicateurs  
> **Langue** : Français  
> **Objet** : Définir le bounded context `Financial Analysis`, ses sources, définitions d'indicateurs, SIG, EBE/EBITDA, CAF, FRNG, BFR, trésorerie nette, ratios, scores, diagnostics, comparatifs, snapshots, drill-down, reproductibilité et frontières avec le Corporate Finance.

---

# 1. Résumé exécutif

Le bounded context `Financial Analysis` est un **read-side analytique** situé en aval de la comptabilité et du reporting :

```text
JournalEntry / JournalEntryLine
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
    Financial Analysis
            |
            +--> SIG
            +--> EBE / EBITDA
            +--> CAF
            +--> FRNG
            +--> BFR
            +--> Trésorerie nette
            +--> Ratios
            +--> Scores
            +--> Diagnostics
```

Il ne modifie jamais :

```text
JournalEntry

JournalEntryLine

CompanyAccount

TrialBalanceSnapshot

ReportSnapshot
```

Il produit des objets dérivés et versionnés :

```text
FinancialIndicatorDefinition

FinancialIndicatorValue

FinancialRatioDefinition

FinancialRatioValue

FinancialScoreDefinition

FinancialScoreValue

FinancialDiagnostic

AnalysisSnapshot
```

Le principe central est :

```text
Financial Analysis
    consumes accounting truth

but

never becomes accounting truth
```

---

# 2. Sources et rôle doctrinal

Le design du bounded context est notamment inspiré des familles d'analyse financière généralement structurées autour de :

```text
soldes intermédiaires de gestion

excédent brut d'exploitation

capacité d'autofinancement

équilibre financier fonctionnel

fonds de roulement

besoin en fonds de roulement

trésorerie nette

ratios

scoring

diagnostic
```

Ces concepts servent ici à définir le domaine analytique.

Les définitions exécutables restent :

```text
versionnées

configurables

traçables

liées à une source comptable précise
```

et ne sont pas déduites de manière implicite d'un ouvrage, d'un code de compte ou d'une convention historique.

---

# 3. Hiérarchie d'autorité

Pour l'analyse financière :

```text
1. Accounting truth
       TrialBalanceSnapshot / ReportSnapshot

2. Versioned analytical definitions
       FinancialIndicatorDefinition
       FinancialRatioDefinition
       FinancialScoreDefinition

3. Regulatory / reference context
       when indicator semantics depend on a standard

4. Doctrine
       terminology, conceptual models, sample formulas
```

---

# 4. Objectifs

Le bounded context doit permettre de :

1. calculer des indicateurs financiers versionnés ;
2. calculer des SIG ;
3. calculer EBE / EBITDA selon définition explicite ;
4. calculer CAF selon définition explicite ;
5. calculer FRNG, BFR, BFRE, BFRHE et trésorerie nette ;
6. calculer des ratios ;
7. calculer des scores ;
8. produire des diagnostics structurés ;
9. faire des comparaisons N / N-1 ;
10. faire des tendances multi-périodes ;
11. conserver les définitions utilisées ;
12. conserver les sources comptables utilisées ;
13. produire des snapshots immuables ;
14. permettre un drill-down vers les états et comptes sources ;
15. produire des résultats reproductibles ;
16. distinguer indicateur comptable, ratio, score et diagnostic ;
17. gérer les données manquantes et divisions par zéro explicitement ;
18. gérer les seuils et interprétations par policy ;
19. permettre des définitions custom ;
20. maintenir une frontière claire avec Corporate Finance.

---

# 5. Non-objectifs

Le core `Financial Analysis` ne doit pas devenir un moteur de Corporate Finance complet.

Sont hors core P1.3 :

```text
VAN / NPV

TRI / IRR

WACC / cost of capital

capital budgeting

investment choice

enterprise valuation

DCF

Monte Carlo investment risk

financing optimization

portfolio optimization
```

Ces sujets appartiennent plutôt à :

```text
optional extension

or

future corporate-finance framework
```

---

# 6. Bounded context

Nom :

```text
Financial Analysis
```

Dépendances principales :

```text
Financial Statements

Ledger / Trial Balance

Accounting Reference Data

Controls

Audit & Traceability
```

---

# 7. Direction de dépendance

```text
Financial Statements
        |
        v
Financial Analysis
```

Jamais :

```text
Financial Analysis
        |
        v
Financial Statements mutation
```

---

# 8. Architecture conceptuelle

```text
ReportSnapshot
     |
     +-------------------------+
     |                         |
     v                         v
Indicator Definitions      Ratio Definitions
     |                         |
     v                         v
Indicator Engine          Ratio Engine
     |                         |
     +------------+------------+
                  |
                  v
             Score Engine
                  |
                  v
         Diagnostic Engine
                  |
                  v
          AnalysisSnapshot
```

---

# 9. Deux types de sources

Le moteur peut consommer :

```text
ReportSnapshot

TrialBalanceSnapshot
```

---

# 10. Source recommandée

Pour analyse publiée :

```text
ReportSnapshot
```

est recommandé lorsque les indicateurs dépendent des états financiers.

---

# 11. Source Trial Balance

Utile pour :

```text
indicateurs non exposés dans les états

analyses de structure plus fines

analyses custom
```

---

# 12. `FinancialAnalysisSource`

```text
FinancialAnalysisSource
|
+-- source_type
+-- source_ref
+-- entity_id
+-- period
+-- currency
+-- checksum
+-- freshness
+-- metadata
```

---

# 13. `FinancialAnalysisSourceType`

```text
REPORT_SNAPSHOT

TRIAL_BALANCE_SNAPSHOT

MULTI_REPORT_SNAPSHOT

CUSTOM_ANALYTICAL_SOURCE
```

---

# 14. Source freshness

```text
CURRENT

STALE

SUPERSEDED
```

---

# 15. Publication

Une analyse publiée doit refuser par défaut :

```text
STALE source
```

sauf mode historique explicitement demandé.

---

# 16. `FinancialIndicatorDefinition`

Objet central :

```text
FinancialIndicatorDefinition
|
+-- id
+-- code
+-- label
+-- category
+-- version
+-- formula
+-- dependencies
+-- source_requirements
+-- interpretation_policy?
+-- unit
+-- rounding_policy
+-- applicability
+-- provenance
+-- status
```

---

# 17. `FinancialIndicatorCategory`

```text
PERFORMANCE

PROFITABILITY

ACTIVITY

CASH_GENERATION

LIQUIDITY

WORKING_CAPITAL

SOLVENCY

LEVERAGE

CAPITAL_STRUCTURE

EFFICIENCY

GROWTH

CUSTOM
```

---

# 18. `IndicatorUnit`

```text
CURRENCY

PERCENTAGE

RATIO

DAYS

COUNT

INDEX

CUSTOM
```

---

# 19. `IndicatorStatus`

```text
DRAFT

VALIDATED

ACTIVE

DEPRECATED

SUPERSEDED
```

---

# 20. Définition versionnée

Changer la formule de :

```text
CAF
```

doit produire :

```text
new definition version
```

pas une mutation silencieuse.

---

# 21. Formule

Réutiliser une DSL déterministe.

Opérations initiales :

```text
ADD

SUBTRACT

MULTIPLY

DIVIDE

SUM

NEGATE

ABS

MIN

MAX

COALESCE

IF_DEFINED
```

---

# 22. Pas de `eval()` arbitraire

Interdit.

---

# 23. Dépendances

Un indicateur peut dépendre :

```text
statement line

trial balance measure

another indicator
```

---

# 24. `IndicatorDependency`

```text
IndicatorDependency
|
+-- dependency_type
+-- dependency_id
+-- required
+-- fallback?
```

---

# 25. `IndicatorDependencyType`

```text
STATEMENT_LINE

TRIAL_BALANCE_MEASURE

INDICATOR

EXTERNAL_ANALYTICAL_INPUT
```

---

# 26. Graph de dépendance

Les définitions forment un DAG.

---

# 27. Cycle

Interdit :

```text
A -> B -> A
```

---

# 28. `IndicatorDependencyCycleError`

---

# 29. `FinancialIndicatorValue`

```text
FinancialIndicatorValue
|
+-- indicator_definition_id
+-- indicator_version
+-- value
+-- unit
+-- source_refs
+-- dependency_values
+-- status
+-- interpretation?
+-- calculated_at
```

---

# 30. `IndicatorValueStatus`

```text
CALCULATED

NOT_APPLICABLE

UNDEFINED

INDETERMINATE

ERROR
```

---

# 31. Division par zéro

Ne doit jamais produire silencieusement :

```text
Infinity

NaN
```

---

# 32. Policy division par zéro

```text
UNDEFINED

NOT_APPLICABLE

ZERO_IF_CONFIGURED

ERROR
```

---

# 33. P1 recommandé

```text
UNDEFINED
```

par défaut.

---

# 34. Missing dependency

Si une donnée requise manque :

```text
INDETERMINATE
```

---

# 35. Distinction

```text
UNDEFINED
    formula mathématiquement non définie

INDETERMINATE
    input manquant / ambigu
```

---

# 36. SIG

Le moteur doit pouvoir modéliser les Soldes Intermédiaires de Gestion comme une chaîne de définitions.

---

# 37. `IntermediateManagementBalanceDefinition`

Extension logique de :

```text
FinancialIndicatorDefinition
```

---

# 38. Exemple de chaîne SIG

```text
Commercial Margin
    |
    v
Production
    |
    v
Value Added
    |
    v
EBE
    |
    v
Operating Result
    |
    v
Current Result Before Tax
    |
    v
Exceptional Result
    |
    v
Net Result
```

---

# 39. Important

Les formules exactes sont :

```text
definition-driven
```

et non codées en dur dans le moteur.

---

# 40. Pourquoi

Différences possibles selon :

```text
référentiel

présentation

secteur

convention de gestion

niveau de détail
```

---

# 41. `SIGDefinitionSet`

```text
SIGDefinitionSet
|
+-- id
+-- code
+-- version
+-- indicator_definitions
+-- ordering
+-- applicability
+-- status
```

---

# 42. EBE

`EBE` est modélisé comme :

```text
FinancialIndicatorDefinition
```

---

# 43. EBITDA

Même principe.

---

# 44. EBE != EBITDA

Le framework ne doit pas considérer :

```text
EBE == EBITDA
```

comme invariant universel.

---

# 45. `IndicatorSemanticAlias`

Peut signaler :

```text
related concepts
```

sans fusionner les définitions.

---

# 46. CAF

La capacité d'autofinancement est modélisée comme :

```text
FinancialIndicatorDefinition
```

---

# 47. Méthodes CAF

Le moteur peut supporter plusieurs définitions :

```text
ADDITIVE

SUBTRACTIVE

CUSTOM
```

---

# 48. `CashFlowCapacityMethod`

```text
ADDITIVE

SUBTRACTIVE

CUSTOM
```

---

# 49. Deux méthodes

Si les deux sont configurées :

```text
CAF additive

CAF subtractive
```

peuvent être comparées via un control.

---

# 50. `CAF_RECONCILED`

Control possible.

---

# 51. Functional balance sheet

Le moteur doit supporter une représentation analytique fonctionnelle.

---

# 52. `FunctionalBalanceDefinition`

```text
FunctionalBalanceDefinition
|
+-- id
+-- version
+-- stable_resources
+-- stable_uses
+-- operating_current_assets
+-- operating_current_liabilities
+-- non_operating_current_assets
+-- non_operating_current_liabilities
+-- cash_assets
+-- cash_liabilities
+-- mapping_set
```

---

# 53. Important

Le bilan fonctionnel est une :

```text
ANALYTICAL_DEFINITION
```

pas une nouvelle source comptable.

---

# 54. `FunctionalBalance`

Résultat :

```text
FunctionalBalance
|
+-- stable_resources
+-- stable_uses
+-- operating_current_assets
+-- operating_current_liabilities
+-- non_operating_current_assets
+-- non_operating_current_liabilities
+-- cash_assets
+-- cash_liabilities
+-- source_refs
```

---

# 55. FRNG

```text
FRNG
=
Stable Resources
-
Stable Uses
```

dans une définition donnée.

---

# 56. `WorkingCapitalIndicator`

Type spécialisé possible.

---

# 57. BFR

Définition analytique :

```text
BFR
=
Current Operating Assets
-
Current Operating Liabilities
+
/-
non-operating components
```

selon définition configurée.

---

# 58. BFRE / BFRHE

Supporter :

```text
BFRE

BFRHE

BFR
```

comme indicateurs distincts.

---

# 59. Relation

Une configuration peut définir :

```text
BFR = BFRE + BFRHE
```

---

# 60. Trésorerie nette

Définition possible :

```text
Net Treasury
=
FRNG - BFR
```

---

# 61. Réconciliation alternative

Ou :

```text
Cash Assets
-
Cash Liabilities
```

---

# 62. `NET_TREASURY_RECONCILED`

Control possible entre les deux méthodes.

---

# 63. `WorkingCapitalAnalysis`

```text
WorkingCapitalAnalysis
|
+-- frng
+-- bfre
+-- bfrhe
+-- bfr
+-- net_treasury
+-- reconciliation
+-- source_refs
```

---

# 64. Ratios

Un ratio est défini séparément d'un indicateur simple.

---

# 65. `FinancialRatioDefinition`

```text
FinancialRatioDefinition
|
+-- id
+-- code
+-- label
+-- category
+-- version
+-- numerator
+-- denominator
+-- scale
+-- unit
+-- interpretation_policy?
+-- applicability
+-- status
```

---

# 66. Ratio categories

```text
ACTIVITY

PROFITABILITY

LIQUIDITY

SOLVENCY

LEVERAGE

EFFICIENCY

COVERAGE

CASH_GENERATION

CUSTOM
```

---

# 67. `FinancialRatioValue`

```text
FinancialRatioValue
|
+-- ratio_definition_id
+-- ratio_version
+-- value
+-- numerator_value
+-- denominator_value
+-- status
+-- interpretation
+-- source_refs
```

---

# 68. Ratios issus de CFA FRA

La référence fonctionnelle a déjà identifié des exemples analytiques tels que :

```text
NET_MARGIN

ROA

CURRENT_RATIO

DEBT_TO_ASSETS

EQUITY_RATIO

CFO_TO_REVENUE

ASSET_TURNOVER
```

Ces ratios sont analytiques, pas réglementaires.

---

# 69. `NET_MARGIN`

Exemple :

```text
Net Result
/
Revenue
```

---

# 70. `ROA`

Exemple :

```text
Net Result
/
Average Total Assets
```

---

# 71. Average denominator

Un ratio peut nécessiter :

```text
opening balance

closing balance

average
```

---

# 72. `DenominatorAggregation`

```text
CLOSING

OPENING

AVERAGE_OPEN_CLOSE

AVERAGE_PERIODIC

CUSTOM
```

---

# 73. `CURRENT_RATIO`

Exemple :

```text
Current Assets
/
Current Liabilities
```

---

# 74. `DEBT_TO_ASSETS`

Exemple :

```text
Debt
/
Assets
```

---

# 75. `EQUITY_RATIO`

Exemple :

```text
Equity
/
Assets
```

---

# 76. `CFO_TO_REVENUE`

Exemple :

```text
Cash Flow From Operations
/
Revenue
```

---

# 77. `ASSET_TURNOVER`

Exemple :

```text
Revenue
/
Average Assets
```

---

# 78. Definitions are not universal

Les dénominateurs exacts, agrégats et conventions sont :

```text
versioned ratio definitions
```

---

# 79. Ratio scaling

```text
1

100

365

360
```

selon ratio.

---

# 80. Days ratios

Pour :

```text
DSO

DPO

Inventory Days
```

le facteur peut être :

```text
365

360

custom
```

---

# 81. `DayCountPolicy`

```text
CALENDAR_365

COMMERCIAL_360

ACTUAL_PERIOD_DAYS

CUSTOM
```

---

# 82. Activity ratios future

Support possible :

```text
DSO

DPO

Inventory Turnover

Inventory Days
```

---

# 83. Source requirements

Ces ratios peuvent nécessiter :

```text
average receivables

average payables

average inventory

period sales

period purchases / COGS
```

---

# 84. Absence de source

Fail as :

```text
INDETERMINATE
```

pas estimation silencieuse.

---

# 85. Interpretation

Un ratio peut avoir une interprétation.

---

# 86. `IndicatorInterpretationPolicy`

```text
IndicatorInterpretationPolicy
|
+-- thresholds
+-- labels
+-- direction
+-- applicability
+-- version
```

---

# 87. Exemple

```text
Current Ratio >= X
```

ne doit pas être codé universellement comme :

```text
GOOD
```

---

# 88. Pourquoi

Le sens dépend :

```text
secteur

pays

business model

historique

saisonnalité
```

---

# 89. `InterpretationLabel`

```text
VERY_WEAK

WEAK

NEUTRAL

GOOD

VERY_GOOD

CUSTOM
```

---

# 90. Relative interpretation

Préférable lorsqu'on dispose :

```text
historical trend

peer benchmark

target
```

---

# 91. Benchmark

P1.3 prévoit l'extension :

```text
BenchmarkProvider
```

mais ne dépend pas d'une source externe par défaut.

---

# 92. `BenchmarkObservation`

```text
metric_code

population

period

value

source

checksum
```

---

# 93. Benchmark reproducibility

Si utilisé dans une analyse publiée :

```text
benchmark snapshot
```

doit être capturé.

---

# 94. Scores

Un score combine plusieurs indicateurs.

---

# 95. `FinancialScoreDefinition`

```text
FinancialScoreDefinition
|
+-- id
+-- code
+-- label
+-- version
+-- components
+-- aggregation_method
+-- thresholds
+-- applicability
+-- provenance
+-- status
```

---

# 96. `ScoreComponent`

```text
ScoreComponent
|
+-- metric_ref
+-- weight
+-- normalization
+-- required
```

---

# 97. `FinancialScoreValue`

```text
FinancialScoreValue
|
+-- score_definition_id
+-- value
+-- component_values
+-- status
+-- interpretation
+-- source_refs
```

---

# 98. Scoring doctrine

La littérature de gestion financière présente des méthodes de scoring.

PyAccountingKit doit les modéliser comme :

```text
ANALYTICAL_DEFINITION
```

pas comme vérité réglementaire.

---

# 99. Scoring model status

```text
EXPERIMENTAL

VALIDATED

PRODUCTION

DEPRECATED
```

---

# 100. Model governance

Un score déclaré Production doit avoir :

```text
definition version

test suite

provenance

validation evidence
```

---

# 101. ML scores

P2 possible.

Mais distinct de :

```text
rule-based financial score
```

---

# 102. Diagnostic

Un diagnostic assemble des faits analytiques.

---

# 103. `FinancialDiagnostic`

```text
FinancialDiagnostic
|
+-- id
+-- code
+-- version
+-- observations
+-- strengths
+-- weaknesses
+-- alerts
+-- conclusions
+-- source_refs
+-- generated_at
+-- generation_mode
```

---

# 104. `DiagnosticGenerationMode`

```text
RULE_BASED

HUMAN_AUTHORED

HYBRID

CUSTOM
```

---

# 105. P1 recommandé

```text
RULE_BASED
```

et :

```text
HUMAN_AUTHORED
```

---

# 106. Pas de texte opaque obligatoire

Le diagnostic doit rester structuré.

---

# 107. `DiagnosticObservation`

```text
DiagnosticObservation
|
+-- metric_ref
+-- observed_value
+-- interpretation
+-- severity
+-- rationale
+-- evidence_refs
```

---

# 108. Diagnostic severity

```text
INFO

NOTICE

WARNING

CRITICAL
```

---

# 109. Diagnostic != Accounting Control

Un diagnostic peut dire :

```text
liquidity weak
```

sans bloquer aucune opération comptable.

---

# 110. Control != Diagnostic

`Control` :

```text
est-ce cohérent / valide ?
```

`Diagnostic` :

```text
qu'est-ce que cela signifie ?
```

---

# 111. `AnalysisDefinitionSet`

Aggregate Root :

```text
AnalysisDefinitionSet
|
+-- id
+-- code
+-- version
+-- indicator_definitions
+-- ratio_definitions
+-- score_definitions
+-- diagnostic_rules
+-- applicability
+-- status
+-- provenance
```

---

# 112. Pourquoi un DefinitionSet

Permet de pinner :

```text
entire analytical methodology
```

dans un snapshot.

---

# 113. Status

```text
DRAFT

VALIDATED

ACTIVE

SUPERSEDED

ARCHIVED
```

---

# 114. `FinancialAnalysisRun`

Process / aggregate :

```text
FinancialAnalysisRun
|
+-- id
+-- entity_id
+-- source_refs
+-- definition_set_id
+-- definition_set_version
+-- status
+-- period
+-- comparison_periods
+-- started_at
+-- completed_at?
+-- generated_by?
+-- correlation_id
```

---

# 115. Run status

```text
CREATED

RUNNING

COMPLETED

COMPLETED_WITH_WARNINGS

FAILED

CANCELLED
```

---

# 116. Pipeline

```text
validate sources

load definitions

resolve dependencies

calculate indicators

calculate ratios

calculate scores

generate diagnostics

run analysis controls

create AnalysisSnapshot
```

---

# 117. `FinancialAnalysisEngine`

```python
class FinancialAnalysisEngine:
    def analyze(
        self,
        request: "FinancialAnalysisRequest",
    ) -> "FinancialAnalysisResult":
        ...
```

---

# 118. `FinancialAnalysisRequest`

```text
FinancialAnalysisRequest
|
+-- entity_id
+-- sources
+-- definition_set
+-- period
+-- comparison_periods?
+-- benchmarks?
+-- presentation_context?
```

---

# 119. `FinancialAnalysisResult`

```text
FinancialAnalysisResult
|
+-- indicators
+-- ratios
+-- scores
+-- diagnostics
+-- working_capital_analysis?
+-- sig?
+-- warnings
+-- source_refs
+-- definition_set_version
```

---

# 120. `AnalysisSnapshot`

Aggregate immutable :

```text
AnalysisSnapshot
|
+-- id
+-- entity_id
+-- period
+-- source_snapshot_refs
+-- definition_set_id
+-- definition_set_version
+-- indicator_values
+-- ratio_values
+-- score_values
+-- diagnostics
+-- control_run_refs
+-- generated_at
+-- generated_by?
+-- checksum
+-- status
+-- supersedes?
+-- metadata
```

---

# 121. Snapshot status

```text
DRAFT

VALIDATED

PUBLISHED

SUPERSEDED

WITHDRAWN
```

---

# 122. Immutable after publication

Même principe que `ReportSnapshot`.

---

# 123. Source immutability

Un AnalysisSnapshot ne doit pas recalculer ses valeurs à partir de sources actuelles.

---

# 124. Reopen impact

Si un ReportSnapshot devient stale :

```text
AnalysisSnapshot downstream
```

devient :

```text
STALE / SUPERSEDED
```

sans mutation destructive.

---

# 125. `AnalysisFreshness`

```text
CURRENT

STALE

SUPERSEDED
```

---

# 126. Drill-down

Architecture :

```text
Indicator / Ratio
    |
    v
Source Statement Lines
    |
    v
Statement Mapping
    |
    v
Trial Balance
    |
    v
Ledger
    |
    v
JournalEntryLine
```

---

# 127. `FinancialAnalysisDrilldownQuery`

```python
class FinancialAnalysisDrilldownQuery(Protocol):
    def drilldown(
        self,
        analysis_snapshot_id,
        metric_code,
    ) -> "FinancialAnalysisDrilldownResult":
        ...
```

---

# 128. Drilldown result

```text
metric definition

formula

dependency values

statement lines

source accounts

ledger refs

entry refs
```

---

# 129. Formula explainability

Toute valeur doit pouvoir montrer :

```text
formula

inputs

intermediate values

rounding

output
```

---

# 130. `CalculationTrace`

```text
CalculationTrace
|
+-- formula
+-- dependency_values
+-- intermediate_values
+-- rounding_steps
+-- result
```

---

# 131. Required for published analysis

Recommandé :

```text
AUDITABLE
```

reproducibility level.

---

# 132. Reproducibility

Un AnalysisSnapshot doit pinner :

```text
runtime version

definition set version

source report snapshots

source trial balance snapshots

benchmark snapshots if any

rounding policy

interpretation policy
```

---

# 133. `AnalysisReproducibilityEnvelope`

```text
AnalysisReproducibilityEnvelope
|
+-- runtime_version
+-- definition_set_version
+-- source_snapshot_refs
+-- benchmark_snapshot_refs
+-- external_observations
+-- calculation_parameters
+-- checksum
```

---

# 134. No live benchmark in published analysis

Même principe que FX.

---

# 135. Comparative analysis

Le moteur doit supporter :

```text
N vs N-1

multi-year trend

period-over-period
```

---

# 136. `FinancialTrendDefinition`

```text
FinancialTrendDefinition
|
+-- metric_code
+-- periods
+-- transformation
+-- display_rule
```

---

# 137. Trend transformations

```text
ABSOLUTE_CHANGE

PERCENT_CHANGE

CAGR

INDEX_BASE_100

CUSTOM
```

---

# 138. CAGR

Appartient au domaine analytique.

---

# 139. CAGR prerequisites

```text
positive/compatible start and end
```

sinon :

```text
UNDEFINED
```

---

# 140. `FinancialTrendValue`

```text
period_values

absolute_change

percent_change

cagr?

status
```

---

# 141. Growth indicators

Peuvent porter sur :

```text
Revenue

EBE

Net Result

CFO

Assets

Equity
```

---

# 142. Seasonality

P2 extension.

---

# 143. Common-size analysis

Support P1 possible.

---

# 144. `CommonSizeAnalysisDefinition`

Exemple :

```text
Balance Sheet:
    each line / total assets

Income Statement:
    each line / revenue
```

---

# 145. `CommonSizeValue`

```text
line

base

ratio
```

---

# 146. Vertical analysis

Synonyme fréquent de common-size.

---

# 147. Horizontal analysis

Trend / period comparison.

---

# 148. `FinancialStructureAnalysis`

Peut agréger :

```text
common-size

trends

ratios
```

---

# 149. Comparative definitions must be versioned

---

# 150. Average balance calculations

Pour ratios nécessitant moyenne :

```text
opening

closing
```

ou :

```text
periodic observations
```

---

# 151. `AverageBalancePolicy`

```text
OPEN_CLOSE_MEAN

MONTHLY_MEAN

DAILY_MEAN

CUSTOM
```

---

# 152. No implicit average

---

# 153. Working capital days

Possible :

```text
DSO

DPO

Inventory Days
```

---

# 154. Example DSO

```text
Average Receivables
/
Revenue
*
DayCount
```

mais définition exacte configurée.

---

# 155. Credit sales vs total revenue

Ne pas supposer :

```text
total revenue == credit sales
```

si le metric a besoin de credit sales.

---

# 156. Missing credit sales

Result :

```text
INDETERMINATE
```

unless configured approximation is explicit.

---

# 157. `ApproximationPolicy`

```text
DISALLOW

ALLOW_WITH_WARNING

ALLOW_CONFIGURED_PROXY
```

---

# 158. Approximation trace

Toujours visible.

---

# 159. Proxy

Exemple :

```text
total revenue used as proxy for credit sales
```

si explicitement configuré.

---

# 160. `AnalyticalAssumption`

```text
AnalyticalAssumption
|
+-- code
+-- value
+-- reason
+-- provenance
+-- approved_by?
```

---

# 161. Assumptions included in snapshot

---

# 162. External analytical inputs

Exemples :

```text
headcount

market benchmark

budget

industry percentile
```

---

# 163. P1 core

Peut recevoir :

```text
ExternalAnalyticalInput
```

sans provider spécifique.

---

# 164. `ExternalAnalyticalInput`

```text
code

period

value

unit

source

checksum

captured_at
```

---

# 165. Budget/forecast

P2.

---

# 166. Actual vs budget

P2 extension.

---

# 167. Forecast

Ne doit pas être mélangé avec les données comptables historiques.

---

# 168. `DataNature`

```text
ACTUAL

BUDGET

FORECAST

BENCHMARK

SIMULATION
```

---

# 169. P1.3

Primary :

```text
ACTUAL
```

---

# 170. Financial diagnostic rule

```text
DiagnosticRule
|
+-- id
+-- version
+-- condition
+-- severity
+-- message_template
+-- evidence_requirements
+-- applicability
```

---

# 171. No opaque AI requirement

Le diagnostic P1 peut être entièrement déterministe.

---

# 172. AI-generated narrative

P2 optional.

Si utilisé :

```text
narrative layer
```

must not change numerical results.

---

# 173. Narrative provenance

Must preserve:

```text
model/provider

prompt/template version

source analysis snapshot
```

if enabled.

---

# 174. Core analysis remains deterministic

---

# 175. Controls

Financial Analysis peut avoir des controls propres.

---

# 176. `ANALYSIS_INPUTS_COMPLETE`

---

# 177. `ANALYSIS_FORMULA_RECONCILED`

---

# 178. `CAF_RECONCILED`

---

# 179. `NET_TREASURY_RECONCILED`

---

# 180. `INDICATOR_DRILLDOWN_COMPLETE`

---

# 181. `ANALYSIS_SNAPSHOT_CURRENT`

---

# 182. Control vs diagnostic

Toujours distinct.

---

# 183. `AnalysisControlSet`

```text
ANALYSIS_VALIDATION
```

---

# 184. Publication gate

```text
ANALYSIS_PUBLICATION_GATE
```

---

# 185. Gate possible

Requires:

```text
all required inputs

no formula errors

source snapshots current

control set pass
```

---

# 186. Financial analysis mappings

Il peut exister un mapping analytique distinct.

---

# 187. `AnalyticalLineMapping`

Exemple :

```text
statement line
    ->
functional balance bucket
```

---

# 188. Not same as statement mapping

```text
CompanyAccount -> StatementLine
```

vs :

```text
StatementLine -> AnalyticalBucket
```

---

# 189. `AnalyticalMappingSet`

```text
AnalyticalMappingSet
|
+-- id
+-- version
+-- mappings
+-- definition_scope
+-- status
+-- provenance
```

---

# 190. Functional balance mapping

Peut mapper :

```text
FinancialStatementLine
```

ou directement :

```text
CompanyAccount
```

selon définition.

---

# 191. Recommandation

Préférer :

```text
ReportSnapshot / statement lines
```

lorsque la structure est suffisante.

---

# 192. Direct account mapping

Utiliser uniquement si l'indicateur exige plus de granularité.

---

# 193. Mapping ambiguity

Fail-closed.

---

# 194. No prefix heuristic

Interdit :

```text
classify by account prefix
```

dans le core analytique.

---

# 195. Suggestion strategy

Allowed:

```text
candidate analytical mapping
```

---

# 196. Candidate != active

---

# 197. Analytical mapping provenance

```text
MANUAL

REFERENCE

RULE_BASED

VALIDATED_CANDIDATE

CUSTOM
```

---

# 198. Reference concepts

Le `regulatory-accounting-data-framework` contient aussi des concepts neutres comme :

```text
cash

inventory

receivables

payables

operating expense

operating revenue
```

---

# 199. Important

Les bindings de ces concepts peuvent être :

```text
deferred

human-review-required
```

PyAccountingKit ne doit pas les inventer.

---

# 200. Analytical concept mapping

Si un concept binding validé existe :

```text
ReferenceConcept
    ->
CompanyAccount / StatementLine
```

il peut alimenter des définitions analytiques.

---

# 201. No inferred concept binding

---

# 202. `AnalyticalConceptProvider`

Port optional:

```python
class AnalyticalConceptProvider(Protocol):
    def resolve(
        self,
        concept_id: str,
        context: "AnalyticalConceptContext",
    ) -> "ConceptBindingResult":
        ...
```

---

# 203. `ConceptBindingResult`

```text
VALIDATED

CANDIDATE

UNRESOLVED
```

---

# 204. Fail-closed for required metrics

If required concept unresolved:

```text
INDETERMINATE
```

---

# 205. Financial analysis source scope

Every calculation includes:

```text
entity_id

period

currency

source snapshots
```

---

# 206. Multi-entity

No silent group aggregation.

---

# 207. Group analysis

Future Consolidation.

---

# 208. Multi-currency

Published analysis should normally consume already translated report snapshots.

---

# 209. Direct FX analysis

P2.

---

# 210. `AnalysisCurrencyPolicy`

```text
SOURCE_CURRENCY

PRESENTATION_CURRENCY

CUSTOM
```

---

# 211. Precision

Use:

```text
Decimal
```

for all metrics.

---

# 212. Percent serialization

Use Decimal string.

---

# 213. Rounding

Separate:

```text
calculation precision

presentation precision
```

---

# 214. `AnalysisRoundingPolicy`

```text
FULL_PRECISION

FIXED_DECIMALS

PERCENTAGE_DECIMALS

CUSTOM
```

---

# 215. Formula evaluation before rounding

---

# 216. Ratio comparison

Compare unrounded values when possible.

---

# 217. Threshold comparison

Must specify whether threshold applies to:

```text
raw

rounded
```

P1 recommendation:

```text
raw
```

---

# 218. `ThresholdComparisonPolicy`

---

# 219. FinancialScore weights

Use Decimal.

---

# 220. Sum of weights

If normalized weighted average:

```text
sum(weights) == 1
```

---

# 221. Alternative score methods

```text
WEIGHTED_SUM

RULE_TREE

POINTS

CUSTOM
```

---

# 222. `ScoreAggregationMethod`

---

# 223. Rule tree

Can support:

```text
if ratio < x then ...
```

using safe declarative conditions.

---

# 224. No arbitrary code from data

---

# 225. Diagnostic ordering

Stable ordering by:

```text
severity

rule order

code
```

---

# 226. Trend comparatives

All source snapshots pinned individually.

---

# 227. Different mapping versions

Allowed.

---

# 228. Metric definition identity

To compare N vs N-1:

```text
same metric definition semantics
```

or validated crosswalk.

---

# 229. Same code != same semantics

Same rule as reporting/reference.

---

# 230. `MetricCrosswalk`

```text
MetricCrosswalk
|
+-- source_metric
+-- target_metric
+-- relationship
+-- validation_status
```

---

# 231. Crosswalk relationships

```text
EQUIVALENT

APPROXIMATE

SPLIT

MERGED

NOT_COMPARABLE
```

---

# 232. Historical trend

If definition changed materially:

```text
trend may be NOT_COMPARABLE
```

---

# 233. Re-statement

P2.

---

# 234. `AsReported` principle

P1 stores each snapshot under original definition.

---

# 235. Analysis publication

`AnalysisSnapshot` is the publication unit.

---

# 236. `AnalysisSnapshotChecksum`

SHA-256 canonical payload.

---

# 237. Canonical payload

Includes:

```text
metric IDs

definition versions

values

statuses

source refs

assumptions
```

---

# 238. Excludes volatile metadata

When computing semantic checksum.

---

# 239. Analysis rendering

Separate:

```text
AnalysisSnapshot

AnalysisRenderer
```

---

# 240. `AnalysisRenderer`

```python
class AnalysisRenderer(Protocol):
    def render(
        self,
        snapshot: AnalysisSnapshot,
        definition: "AnalysisRenderDefinition",
    ) -> "RenderedArtifact":
        ...
```

---

# 241. Renderers

```text
JSON

HTML

PDF

XLSX

CUSTOM
```

---

# 242. Rendering doesn't recalculate

---

# 243. API - define metric

```python
definition = accounting.analysis.define_indicator(
    code="CURRENT_RATIO",
    ...
)
```

---

# 244. API - analyze

```python
result = accounting.analysis.run(
    entity_id=entity_id,
    source_snapshot_ids=(report_snapshot.id,),
    definition_set_id=definition_set.id,
)
```

---

# 245. API - snapshot

```python
snapshot = accounting.analysis.snapshot(
    result=result,
)
```

---

# 246. API - drilldown

```python
details = accounting.analysis.drilldown(
    snapshot_id=snapshot.id,
    metric_code="CURRENT_RATIO",
)
```

---

# 247. API - trends

```python
trend = accounting.analysis.trend(
    metric_code="NET_MARGIN",
    snapshot_ids=(s1.id, s2.id, s3.id),
)
```

---

# 248. API - working capital

```python
wc = accounting.analysis.working_capital(
    snapshot_id=snapshot.id,
)
```

---

# 249. API - diagnostic

```python
diagnostic = accounting.analysis.diagnostic(
    snapshot_id=snapshot.id,
)
```

---

# 250. No write-side coupling

No API:

```text
analysis.adjust_ledger(...)
```

---

# 251. If analysis reveals accounting error

Workflow:

```text
Diagnostic
    ->
human/application decision
    ->
accounting correction via reversal + replacement
```

not automatic back-propagation.

---

# 252. FinancialAnalysisRepository

```text
AnalysisDefinitionSetRepository

AnalysisSnapshotRepository

FinancialAnalysisRunRepository

AnalyticalMappingSetRepository
```

---

# 253. Queries

```text
FinancialAnalysisQuery

FinancialAnalysisDrilldownQuery

FinancialTrendQuery
```

---

# 254. Ports

```text
ReportSnapshotQuery

TrialBalanceQuery

AccountingReferenceProvider

AnalyticalConceptProvider

BenchmarkProvider

ArtifactStorePort

AuditPort

ControlRunRepository

UnitOfWork

Clock
```

---

# 255. Package domain

```text
src/pyaccountingkit/domain/financial_analysis/
|
+-- definitions/
|   +-- indicator.py
|   +-- ratio.py
|   +-- score.py
|   +-- sig.py
|   +-- working_capital.py
|
+-- calculation/
|   +-- engine.py
|   +-- formula.py
|   +-- dependency_graph.py
|   +-- trace.py
|
+-- results/
|   +-- indicator_value.py
|   +-- ratio_value.py
|   +-- score_value.py
|   +-- working_capital.py
|
+-- diagnostics/
|   +-- rule.py
|   +-- observation.py
|   +-- diagnostic.py
|
+-- snapshots/
|   +-- analysis_snapshot.py
|   +-- reproducibility.py
|
+-- mappings/
|   +-- analytical_mapping.py
|   +-- concept_binding.py
|
+-- trends/
    +-- trend_definition.py
    +-- trend_value.py
```

---

# 256. Application package

```text
src/pyaccountingkit/application/financial_analysis/
|
+-- create_definition_set.py
+-- validate_definition_set.py
+-- activate_definition_set.py
+-- run_analysis.py
+-- create_analysis_snapshot.py
+-- publish_analysis_snapshot.py
+-- build_diagnostic.py
+-- build_trend.py
+-- drilldown.py
```

---

# 257. Adapter examples

```text
adapters/financial_analysis/
|
+-- in_memory/
+-- sql/
+-- renderers/
+-- benchmarks/
```

---

# 258. SQL persistence

Possible tables:

```text
analysis_definition_set

indicator_definition

ratio_definition

score_definition

analytical_mapping_set

financial_analysis_run

analysis_snapshot
```

---

# 259. Definition storage

Definitions may be:

```text
normalized tables

JSON with schema
```

---

# 260. Recommendation

Keep stable identity/version metadata relational.

Complex formulas may be JSON.

---

# 261. Snapshot storage

Append-only.

---

# 262. Snapshot update

Forbidden after publication.

---

# 263. Analysis run revision

Mutable process can use optimistic revision.

---

# 264. Definition set revision

DRAFT can use revision.

ACTIVE version immutable.

---

# 265. Mapping set revision

Same.

---

# 266. Transaction boundary - activate definition set

```text
lock applicable scope

validate dependencies

validate formulas

validate mappings

activate

supersede old if configured

audit

commit
```

---

# 267. Transaction boundary - publish snapshot

```text
load analysis result

verify source freshness

run controls

persist immutable snapshot

audit

outbox

commit
```

---

# 268. Calculation itself

Read-only and can happen outside write transaction.

---

# 269. Performance

Metric graph evaluation is:

```text
O(number of definitions + dependencies)
```

after source values loaded.

---

# 270. Source loading

Batch all statement lines.

---

# 271. No one-query-per-metric

---

# 272. Dependency cache

Per run.

---

# 273. Formula memoization

Allowed inside run.

---

# 274. Large trend history

Use paged snapshot query.

---

# 275. Benchmarks

Cache by immutable snapshot.

---

# 276. Observability

Metrics:

```text
analysis_runs_total

analysis_duration

indicator_calculation_total

undefined_metric_total

indeterminate_metric_total

diagnostic_alert_total

analysis_snapshot_total

analysis_replay_mismatch_total
```

---

# 277. Logs

Context:

```text
entity_id

analysis_run_id

definition_set_version

source_snapshot_ids

metric_code

correlation_id
```

---

# 278. Do not log full financial dataset

---

# 279. Tracing spans

```text
load_analysis_sources

resolve_analytical_mappings

evaluate_indicator_graph

evaluate_ratios

evaluate_scores

generate_diagnostics

persist_analysis_snapshot
```

---

# 280. Error taxonomy

```text
FinancialAnalysisError
|
+-- AnalysisDefinitionNotFoundError
+-- AnalysisDefinitionInvalidError
+-- IndicatorDependencyCycleError
+-- RatioDefinitionInvalidError
+-- ScoreDefinitionInvalidError
+-- AnalyticalMappingAmbiguousError
+-- AnalyticalConceptUnresolvedError
+-- AnalysisSourceUnavailableError
+-- AnalysisSourceStaleError
+-- AnalysisInputMissingError
+-- IndicatorUndefinedError
+-- AnalysisCalculationError
+-- AnalysisControlFailedError
+-- AnalysisSnapshotIntegrityError
```

---

# 281. Division by zero error model

Not necessarily exception.

Prefer result status:

```text
UNDEFINED
```

unless strict mode.

---

# 282. Strict mode

```text
AnalysisStrictnessPolicy
```

---

# 283. `AnalysisStrictnessPolicy`

```text
LENIENT_PREVIEW

STANDARD

STRICT_PUBLICATION
```

---

# 284. Preview

Can return:

```text
partial metrics
warnings
```

---

# 285. Publication

Fails on:

```text
required metric indeterminate

source stale

definition ambiguity

control blocking fail
```

---

# 286. `AnalysisBuildMode`

```text
PREVIEW

VALIDATION

PUBLICATION
```

---

# 287. Golden tests - SIG

Fixture produces stable:

```text
Commercial Margin

Value Added

EBE

Operating Result

Net Result
```

under a pinned definition set.

---

# 288. Golden tests - CAF

Test:

```text
additive method

subtractive method
```

and reconciliation when both configured.

---

# 289. Golden tests - Working Capital

Expected:

```text
FRNG

BFRE

BFRHE

BFR

Net Treasury
```

---

# 290. Golden tests - Ratios

Include:

```text
NET_MARGIN

ROA

CURRENT_RATIO

DEBT_TO_ASSETS

EQUITY_RATIO

CFO_TO_REVENUE

ASSET_TURNOVER
```

---

# 291. Golden ratio source

Use immutable ReportSnapshot fixture.

---

# 292. Property tests - formula determinism

```text
same source + same definitions
=
same output
```

---

# 293. Property - ratio

If denominator non-zero:

```text
ratio * denominator
≈ numerator
```

within Decimal precision.

---

# 294. Property - FRNG/BFR treasury reconciliation

If both methods configured:

```text
FRNG - BFR
=
Net Treasury
```

and compare to cash assets - cash liabilities.

---

# 295. Property - drilldown

Sum of source contributions must reconcile with metric input values where additive.

---

# 296. Property - snapshot checksum

Same canonical analysis:

```text
same checksum
```

---

# 297. Unit tests - indicator definitions

```text
test_definition_requires_version

test_dependency_must_exist

test_cycle_rejected

test_formula_is_deterministic
```

---

# 298. Unit tests - ratio

```text
test_zero_denominator_returns_undefined

test_ratio_scale_applied

test_average_balance_policy_explicit
```

---

# 299. Unit tests - score

```text
test_weights_sum_to_one_when_required

test_missing_required_component_indeterminate
```

---

# 300. Unit tests - diagnostic

```text
test_rule_trigger_creates_observation

test_diagnostic_does_not_mutate_source
```

---

# 301. Unit tests - snapshot

```text
test_published_analysis_snapshot_immutable

test_snapshot_pins_definition_set

test_snapshot_pins_source_reports
```

---

# 302. Integration test

```text
TrialBalanceSnapshot
    ->
ReportSnapshot
    ->
AnalysisRun
    ->
AnalysisSnapshot
```

---

# 303. Replay test

Same:

```text
source snapshots

definition set

benchmarks

runtime
```

Expected same checksum.

---

# 304. Current engine comparison

Same historical inputs under new engine:

```text
AnalysisComparison
```

---

# 305. `AnalysisComparison`

```text
AnalysisComparison
|
+-- source_snapshot
+-- target_snapshot
+-- metric_differences
+-- definition_differences
+-- comparability_status
```

---

# 306. Comparability

```text
COMPARABLE

PARTIALLY_COMPARABLE

NOT_COMPARABLE
```

---

# 307. Migration tests

Must preserve:

```text
historical AnalysisSnapshot

definition versions

checksums

source refs
```

---

# 308. Contract tests - renderer

Same semantic snapshot yields same semantic rendering structure.

---

# 309. Security

Financial analysis can reveal sensitive financial performance.

Authorization remains application concern.

---

# 310. Audit minimization

Audit:

```text
snapshot IDs

metric codes

checksums
```

not entire report payload.

---

# 311. Audit events

```text
ANALYSIS_DEFINITION_SET_CREATED

ANALYSIS_DEFINITION_SET_ACTIVATED

ANALYSIS_RUN_STARTED

ANALYSIS_RUN_COMPLETED

ANALYSIS_SNAPSHOT_CREATED

ANALYSIS_SNAPSHOT_PUBLISHED

ANALYTICAL_MAPPING_VALIDATED
```

---

# 312. Domain events

```text
AnalysisSnapshotCreated

AnalysisSnapshotPublished

AnalysisDefinitionSetActivated
```

---

# 313. Lineage

```text
JournalEntryLine
    ->
TrialBalance
    ->
ReportSnapshot
    ->
FinancialIndicatorValue
    ->
FinancialRatioValue
    ->
FinancialScoreValue
    ->
FinancialDiagnostic
```

---

# 314. Provenance

Every metric keeps:

```text
definition

source refs

calculation trace

assumptions
```

---

# 315. Controls vs interpretation

A metric can be:

```text
valid
```

but interpreted as:

```text
weak
```

---

# 316. Example

```text
Current Ratio = 0.8
```

Can be:

```text
correctly calculated
```

yet:

```text
diagnostically weak
```

---

# 317. Do not confuse quality control with business interpretation

---

# 318. Statistical analysis

P2.

Could include:

```text
distribution

z-score

peer percentile

volatility
```

---

# 319. Statistical score

Separate from accounting control.

---

# 320. Corporate Finance boundary

The following remain outside core:

```text
investment projects

discounted cash flows

NPV

IRR

WACC

valuation

financing optimization
```

---

# 321. Why boundary

These capabilities depend on:

```text
future assumptions

discount rates

capital market inputs

scenario modeling
```

and no longer only on historical accounting facts.

---

# 322. Optional extension boundary

Possible future package:

```text
pyaccountingkit.corporate_finance
```

or separate framework.

---

# 323. In-core accepted advanced analytics

Can include:

```text
historical trends

ratios

scores

financial diagnostics

common-size analysis

working capital analysis
```

because they remain historical/read-side.

---

# 324. Scenario analysis

P2 boundary.

---

# 325. Forecasting

P2 boundary.

---

# 326. Budget variance

P2 possible analytical extension.

---

# 327. Decision support

Not part of P1.3.

---

# 328. Documentation source registry

Each predefined analytical definition should include:

```text
definition origin

provenance

version

status

applicability
```

---

# 329. `AnalyticalDefinitionOrigin`

```text
DOCTRINAL

REFERENCE

COMPANY

CUSTOM

CFA_FRA_REFERENCE
```

---

# 330. Doctrine-origin definition

Does not imply:

```text
regulatory
```

---

# 331. CFA FRA-origin ratio

Does not imply:

```text
regulatory
```

---

# 332. `OfficialityStatus`

For analytics:

```text
ANALYTICAL

MANAGEMENT

REFERENCE_DERIVED

CUSTOM
```

---

# 333. No "official financial ratio" unless source explicitly says so

---

# 334. Naming

Technical codes stable:

```text
CURRENT_RATIO

NET_MARGIN

FRNG

BFR

NET_TREASURY
```

Labels localized separately.

---

# 335. Localization

Display labels can be translated.

---

# 336. Formula IDs stable

---

# 337. Public API freeze

Indicator/ratio definition contracts likely public extension APIs.

---

# 338. Custom metrics

Users should be able to register:

```text
custom metric definitions
```

without modifying core.

---

# 339. `MetricDefinitionRegistry`

```python
class MetricDefinitionRegistry:
    def register(self, definition):
        ...
```

---

# 340. Dynamic registry safety

Only trusted Python/config definitions.

No arbitrary code execution from untrusted data.

---

# 341. Declarative custom metrics

Preferred.

---

# 342. Plugin extension

Future plugin package may provide sector-specific metrics.

Examples:

```text
banking

insurance

real estate

nonprofit

microfinance
```

---

# 343. Sector-specific metrics

Must carry:

```text
sector applicability
```

---

# 344. Microfinance future

Could consume:

```text
COBAC / PCEMF-specific reference data
```

but not in generic P1.3.

---

# 345. Nonprofit metrics

Can use different interpretation/definitions.

---

# 346. Real estate

Can use specific operational KPIs external to accounting.

---

# 347. External KPI integration

Out of core P1.3 except via generic input port.

---

# 348. Quality gates for a Production analytical definition

Must have:

```text
unit tests

golden tests

boundary tests

zero/missing input tests

reproducibility test

provenance
```

---

# 349. `AnalyticalDefinitionQualification`

```text
definition_id

version

status

test_suite_version

qualified_at
```

---

# 350. Qualification statuses

```text
EXPERIMENTAL

VALIDATED

PRODUCTION
```

---

# 351. P1 builtin definitions

Recommended starter set:

```text
SIG core

EBE

CAF

FRNG

BFRE

BFRHE

BFR

NET_TREASURY

NET_MARGIN

ROA

CURRENT_RATIO

DEBT_TO_ASSETS

EQUITY_RATIO

CFO_TO_REVENUE

ASSET_TURNOVER
```

---

# 352. Optional starter ratios

```text
ROE

QUICK_RATIO

DEBT_TO_EQUITY

INTEREST_COVERAGE

DSO

DPO

INVENTORY_DAYS
```

if source definitions are explicitly provided.

---

# 353. No silent assumptions for purchases/credit sales

---

# 354. Financial score starter set

Do not ship a scoring model as Production without explicit validated definition.

---

# 355. Diagnostic starter rules

Could include neutral observations:

```text
negative working capital

negative net treasury

declining margin

high leverage

low liquidity
```

but thresholds must be configurable.

---

# 356. No normative judgment hardcoded

---

# 357. Materiality

Analytical materiality may suppress immaterial observations.

---

# 358. `AnalysisMaterialityPolicy`

```text
threshold

currency

relative_threshold?

applicability
```

---

# 359. Analytical materiality != accounting recognition materiality

---

# 360. Suppressed diagnostic

Still may be present in calculation trace.

---

# 361. Presentation

Analysis rendering can organize:

```text
Performance

Cash Generation

Working Capital

Liquidity

Solvency

Leverage

Efficiency

Trend
```

---

# 362. Canonical analysis payload

Not tied to UI layout.

---

# 363. Dashboard

Application concern.

---

# 364. Charting

Renderer/application concern.

---

# 365. Export JSON

P1 recommended canonical format.

---

# 366. XLSX/PDF

Adapters.

---

# 367. `AnalysisExportArtifact`

Optional:

```text
analysis_snapshot_id

format

artifact_ref

checksum
```

---

# 368. Export evidence

Same pattern as reporting.

---

# 369. Analysis publish audit

```text
ANALYSIS_SNAPSHOT_PUBLISHED
```

---

# 370. Error handling preview

Preview can include:

```text
undefined metrics

indeterminate metrics

mapping warnings
```

---

# 371. Error handling publication

Blocks required metrics only.

---

# 372. `RequiredMetricPolicy`

```text
RequiredMetricPolicy
|
+-- required_metric_codes
+-- optional_metric_codes
+-- applicability
```

---

# 373. Missing optional metric

Warning.

---

# 374. Missing required metric

Blocking.

---

# 375. Source profile

An analysis definition set can target:

```text
management report profile

statutory report profile

custom
```

---

# 376. `AnalysisApplicability`

```text
standard?

reporting_profile?

sector?

entity?

effective_dates?
```

---

# 377. Version activation

New definition set does not silently alter historical snapshots.

---

# 378. Upgrade flow

```text
DefinitionSet v1
    |
    v
Impact Analysis
    |
    v
DefinitionSet v2
    |
    v
Golden / Replay Qualification
    |
    v
Activation
```

---

# 379. `AnalysisDefinitionUpgradePlan`

```text
changed formulas

changed mappings

changed thresholds

affected metrics

comparability impact

required tests
```

---

# 380. Historical comparability

May be:

```text
preserved

partial

broken
```

---

# 381. `MetricSemanticChange`

```text
NONE

NON_BREAKING

BREAKING
```

---

# 382. Breaking semantic change

Requires new metric version.

---

# 383. Metric deprecation

Keep old definition readable for historical snapshots.

---

# 384. No deletion of historical definition

---

# 385. Data model summary

```text
AnalysisDefinitionSet
    |
    +--> FinancialIndicatorDefinition
    +--> FinancialRatioDefinition
    +--> FinancialScoreDefinition
    +--> DiagnosticRule
    +--> AnalyticalMappingSet

FinancialAnalysisRun
    |
    v
FinancialAnalysisResult
    |
    v
AnalysisSnapshot
```

---

# 386. Relationship summary

```text
ReportSnapshot
    |
    v
AnalysisDefinitionSet
    |
    v
FinancialAnalysisEngine
    |
    v
AnalysisSnapshot
```

---

# 387. Testing matrix

| Capability | Unit | Property | Integration | Golden | Replay |
|---|---:|---:|---:|---:|---:|
| SIG | oui | oui | oui | oui | oui |
| EBE | oui | oui | oui | oui | oui |
| CAF | oui | oui | oui | oui | oui |
| FRNG/BFR | oui | oui | oui | oui | oui |
| Ratios | oui | oui | oui | oui | oui |
| Scores | oui | partiel | oui | oui | oui |
| Diagnostics | oui | - | oui | oui | oui |
| Snapshot | oui | oui | oui | oui | oui |
| Drill-down | oui | oui | oui | oui | - |

---

# 388. ADRs

| ID | Décision |
|---|---|
| ADR-ANA-001 | `Financial Analysis` est un bounded context read-only |
| ADR-ANA-002 | Le bounded context consomme `ReportSnapshot` et `TrialBalanceSnapshot` |
| ADR-ANA-003 | Les indicateurs analytiques ne deviennent jamais source comptable |
| ADR-ANA-004 | `FinancialIndicatorDefinition` est versionnée |
| ADR-ANA-005 | `FinancialRatioDefinition` est versionnée |
| ADR-ANA-006 | `FinancialScoreDefinition` est versionnée |
| ADR-ANA-007 | Les formules utilisent une DSL déterministe et sûre |
| ADR-ANA-008 | Les dépendances d'indicateurs forment un DAG |
| ADR-ANA-009 | Une division par zéro produit `UNDEFINED` par défaut |
| ADR-ANA-010 | Une donnée requise manquante produit `INDETERMINATE` |
| ADR-ANA-011 | Les SIG sont definition-driven |
| ADR-ANA-012 | EBE et EBITDA ne sont pas fusionnés comme concepts universellement équivalents |
| ADR-ANA-013 | La CAF peut supporter plusieurs méthodes versionnées |
| ADR-ANA-014 | Le bilan fonctionnel est une définition analytique, pas un état comptable canonique |
| ADR-ANA-015 | FRNG, BFR et trésorerie nette sont des indicateurs analytiques |
| ADR-ANA-016 | Les ratios CFA FRA sont analytiques, pas réglementaires |
| ADR-ANA-017 | Les seuils d'interprétation sont policy-driven |
| ADR-ANA-018 | Un score n'est pas livré Production sans définition validée |
| ADR-ANA-019 | `Control` et `Diagnostic` sont distincts |
| ADR-ANA-020 | `AnalysisDefinitionSet` fige une méthodologie analytique complète |
| ADR-ANA-021 | `AnalysisSnapshot` publié est immutable |
| ADR-ANA-022 | Un AnalysisSnapshot pinne ses sources et définitions |
| ADR-ANA-023 | Un reopen n'altère jamais un AnalysisSnapshot historique |
| ADR-ANA-024 | Le drill-down Metric -> Statement -> TrialBalance -> Ledger est requis |
| ADR-ANA-025 | Toute valeur publiée doit disposer d'un CalculationTrace ou équivalent |
| ADR-ANA-026 | Les benchmarks utilisés en publication sont snapshotés |
| ADR-ANA-027 | Une approximation analytique doit être explicitement configurée et tracée |
| ADR-ANA-028 | Les concept bindings non validés ne sont pas inventés |
| ADR-ANA-029 | Les mappings analytiques ne reposent pas sur des préfixes universels |
| ADR-ANA-030 | Les tendances pinent chaque source historique |
| ADR-ANA-031 | Same metric code ne prouve pas l'équivalence sémantique entre versions |
| ADR-ANA-032 | Les changements sémantiques breaking créent une nouvelle version |
| ADR-ANA-033 | Le Corporate Finance reste hors du core P1.3 |
| ADR-ANA-034 | VAN/NPV, TRI/IRR, WACC et valuation sont hors du bounded context |
| ADR-ANA-035 | Les analyses historiques, ratios, SIG, BFR et diagnostics restent dans le core |
| ADR-ANA-036 | Les narrations IA éventuelles ne peuvent pas modifier les résultats numériques |
| ADR-ANA-037 | Les définitions doctrinales n'ont aucune autorité réglementaire implicite |
| ADR-ANA-038 | Les définitions Production doivent être qualifiées par golden/replay tests |
| ADR-ANA-039 | Les AnalysisSnapshot published sont append-oriented |
| ADR-ANA-040 | Le moteur analytique utilise Decimal de bout en bout |

---

# 389. Critères d'acceptation P1.3

```text
[ ] Financial Analysis est explicitement read-only

[ ] FinancialAnalysisSource est défini

[ ] FinancialIndicatorDefinition est défini

[ ] FinancialIndicatorValue est défini

[ ] FinancialRatioDefinition est défini

[ ] FinancialRatioValue est défini

[ ] FinancialScoreDefinition est défini

[ ] FinancialScoreValue est défini

[ ] FinancialDiagnostic est défini

[ ] AnalysisDefinitionSet est défini

[ ] FinancialAnalysisRun est défini

[ ] AnalysisSnapshot est défini

[ ] AnalysisSnapshot publié est immutable

[ ] SIGDefinitionSet est défini

[ ] EBE est supporté

[ ] EBITDA est préparé sans équivalence implicite à EBE

[ ] CAF est supportée

[ ] méthodes CAF multiples sont possibles

[ ] FunctionalBalanceDefinition est défini

[ ] FRNG est supporté

[ ] BFRE est supporté

[ ] BFRHE est supporté

[ ] BFR est supporté

[ ] Net Treasury est supportée

[ ] NET_TREASURY_RECONCILED est prévu

[ ] NET_MARGIN est supporté

[ ] ROA est supporté

[ ] CURRENT_RATIO est supporté

[ ] DEBT_TO_ASSETS est supporté

[ ] EQUITY_RATIO est supporté

[ ] CFO_TO_REVENUE est supporté

[ ] ASSET_TURNOVER est supporté

[ ] division par zéro est gérée explicitement

[ ] missing input est géré explicitement

[ ] interpretation policy est versionnée

[ ] benchmark snapshot est prévu

[ ] diagnostic rule est définie

[ ] control != diagnostic est explicite

[ ] analytical mapping est défini

[ ] concept binding non validé est fail-closed

[ ] CalculationTrace est défini

[ ] drill-down complet est défini

[ ] trends N/N-1 sont supportés

[ ] metric versioning est défini

[ ] semantic breaking change est défini

[ ] replay est prévu

[ ] Corporate Finance boundary est explicite

[ ] tests unit/property/golden/replay sont définis
```

---

# 390. Ordre d'implémentation recommandé

## ANA-00 - Primitives

```text
IndicatorUnit

IndicatorStatus

AnalysisBuildMode

AnalysisFreshness

MetricSemanticChange
```

---

## ANA-01 - Indicator Definitions

```text
FinancialIndicatorDefinition

IndicatorDependency

Formula DSL

Dependency Graph
```

---

## ANA-02 - Ratios

```text
FinancialRatioDefinition

FinancialRatioValue

division-by-zero semantics
```

---

## ANA-03 - Definition Set

```text
AnalysisDefinitionSet

validation

activation
```

---

## ANA-04 - Engine

```text
FinancialAnalysisEngine

CalculationTrace

memoization
```

---

## ANA-05 - SIG

```text
SIGDefinitionSet

core SIG metrics
```

---

## ANA-06 - CAF

```text
CAF additive

CAF subtractive

CAF reconciliation
```

---

## ANA-07 - Working Capital

```text
FunctionalBalanceDefinition

FRNG

BFRE

BFRHE

BFR

Net Treasury
```

---

## ANA-08 - Ratios starter pack

```text
NET_MARGIN

ROA

CURRENT_RATIO

DEBT_TO_ASSETS

EQUITY_RATIO

CFO_TO_REVENUE

ASSET_TURNOVER
```

---

## ANA-09 - Diagnostics

```text
DiagnosticRule

FinancialDiagnostic
```

---

## ANA-10 - Analysis Snapshot

```text
AnalysisSnapshot

checksum

reproducibility
```

---

## ANA-11 - Drill-down

```text
Metric -> Statement -> Ledger
```

---

## ANA-12 - Trends

```text
N/N-1

multi-period

CAGR
```

---

## ANA-13 - Scores

```text
FinancialScoreDefinition

qualification
```

---

## ANA-14 - Golden / replay qualification

```text
Ogien-inspired analytical fixtures

CFA FRA analytical ratios

historical snapshots
```

---

# 391. Démonstrateur P1.3 - SIG

```text
1. Load ReportSnapshot

2. Activate SIGDefinitionSet v1

3. Resolve statement line dependencies

4. Calculate:
      Commercial Margin
      Value Added
      EBE
      Operating Result
      Net Result

5. Build CalculationTrace for each metric

6. Run controls

7. Create AnalysisSnapshot

8. Verify:
      source pinned
      definitions pinned
      checksum stable
```

---

# 392. Démonstrateur P1.3 - Working Capital

```text
1. Load Balance Sheet ReportSnapshot

2. Apply FunctionalBalanceDefinition

3. Build:
      Stable Resources
      Stable Uses
      Operating Current Assets
      Operating Current Liabilities
      Non-operating current items
      Cash Assets
      Cash Liabilities

4. Calculate:
      FRNG
      BFRE
      BFRHE
      BFR
      Net Treasury

5. Reconcile:
      FRNG - BFR
      vs
      Cash Assets - Cash Liabilities

6. Persist AnalysisSnapshot
```

---

# 393. Démonstrateur P1.3 - Ratios

```text
Inputs:
    Revenue
    Net Result
    Assets
    Equity
    Debt
    Current Assets
    Current Liabilities
    CFO

Calculate:
    NET_MARGIN
    ROA
    CURRENT_RATIO
    DEBT_TO_ASSETS
    EQUITY_RATIO
    CFO_TO_REVENUE
    ASSET_TURNOVER
```

---

# 394. Démonstrateur - denominator zero

```text
Current Liabilities = 0

CURRENT_RATIO

Expected:
    status = UNDEFINED

No:
    Infinity
    NaN
```

---

# 395. Démonstrateur - missing input

```text
CFO missing

CFO_TO_REVENUE

Expected:
    INDETERMINATE
```

---

# 396. Démonstrateur - diagnostic

```text
CURRENT_RATIO = 0.7

NET_TREASURY < 0

NET_MARGIN declining 3 years

InterpretationPolicy v2

Expected:
    structured observations
    with traceable thresholds
```

---

# 397. Démonstrateur - trend

```text
AnalysisSnapshot N-2
AnalysisSnapshot N-1
AnalysisSnapshot N

Metric:
    NET_MARGIN

Output:
    period values
    absolute changes
    percent changes
```

---

# 398. Démonstrateur - replay

```text
AnalysisSnapshot S

Inputs:
    ReportSnapshot R
    DefinitionSet D3
    Runtime V1
    Benchmark B2

Replay exact

Expected:
    same semantic checksum
```

---

# 399. Démonstrateur - source reopen

```text
ReportSnapshot R1
    from close revision 1

AnalysisSnapshot A1
    source R1

Period reopened

New report R2

Expected:
    A1 remains immutable
    A1 can be stale/superseded
    new A2 built from R2
```

---

# 400. Démonstrateur - semantic definition upgrade

```text
CURRENT_RATIO v1

New definition v2

Impact analysis:
    denominator definition changed

Expected:
    v1 historical snapshots preserved
    v2 activated for new analyses
    old/new trend marked comparability as appropriate
```

---

# 401. Matrice responsabilités

| Capability | Statements | Analysis | Controls | Corporate Finance |
|---|---:|---:|---:|---:|
| Bilan / P&L / CF | **oui** | consomme | vérifie | consomme éventuellement |
| SIG | non | **oui** | vérifie | consomme |
| CAF | non | **oui** | vérifie | consomme |
| FRNG/BFR | non | **oui** | vérifie | consomme |
| Ratios | non | **oui** | peut contrôler | consomme |
| Diagnostic | non | **oui** | non | consomme |
| NPV/IRR | non | non | non | **oui** |
| WACC | non | non | non | **oui** |
| Valuation | non | non | non | **oui** |

---

# 402. Matrice de nature des objets

| Objet | Nature |
|---|---|
| JournalEntry | Comptable canonique |
| TrialBalanceSnapshot | Projection comptable |
| ReportSnapshot | Reporting |
| FinancialIndicatorValue | Analytique |
| FinancialRatioValue | Analytique |
| FinancialScoreValue | Analytique |
| FinancialDiagnostic | Analytique |
| AnalysisSnapshot | Snapshot analytique immutable |
| NPV / IRR | Corporate Finance, hors core |

---

# 403. Frontière avec le prochain document

Le prochain jalon recommandé est :

```text
15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md
```

Il devra traiter notamment :

```text
clients

fournisseurs

auxiliaires

lettrage

échéances

settlements

operational accounting

control account / auxiliary balance

reconciliation with General Ledger
```

sans déplacer l'analyse financière vers le write-side.

---

# 404. Conclusion

L'architecture de l'analyse financière devient :

```text
ACCOUNTING TRUTH
      |
      v
REPORT SNAPSHOT
      |
      v
ANALYSIS DEFINITION SET
      |
      +--> SIG
      +--> EBE / EBITDA
      +--> CAF
      +--> FUNCTIONAL BALANCE
      +--> FRNG / BFR / NET TREASURY
      +--> RATIOS
      +--> SCORES
      +--> DIAGNOSTICS
      |
      v
ANALYSIS SNAPSHOT
```

Les principes structurants sont :

```text
Analysis is downstream

Analysis never posts entries

Indicator definitions are versioned

Ratios are not regulatory by default

Scores are analytical models

Diagnostics are interpretations, not controls

FRNG/BFR/CAF/SIG are definition-driven

No universal thresholds

No silent approximation

No NaN/Infinity semantics

Every published metric is traceable

Every published analysis is reproducible

Historical snapshots remain immutable

Corporate Finance remains outside the core
```

Le P1.3 fournit ainsi un moteur analytique suffisamment générique pour couvrir l'analyse financière historique et diagnostique, tout en conservant une frontière nette entre comptabilité, reporting, analyse financière et finance d'entreprise.

---

**Prochain document recommandé :**

```text
15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md
```


---

## Sources et références documentaires du projet

- 📗 [Maxi fiches de Gestion financière de l'entreprise](../../books/Maxi_fiches_de_Gestion_financiere_de_l_entreprise.md)

---

## Couverture dans les plans d'implémentation

Ce document est couvert par les plans suivants :

- [PLAN-04 — Subledgers & Financial Analysis (0.4.0)](../../plans/PLAN-04_SUBLEDGERS_FINANCIAL_ANALYSIS_0.4.0.md)
