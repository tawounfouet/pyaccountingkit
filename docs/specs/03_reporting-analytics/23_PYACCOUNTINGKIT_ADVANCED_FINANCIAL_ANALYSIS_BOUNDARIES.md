# 23 - PyAccountingKit - Frontières de l'analyse financière avancée et du Corporate Finance

> **Projet** : PyAccountingKit  
> **Document** : `23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md`  
> **Statut** : P2.3 - Ajout optionnel / frontières avancées  
> **Langue** : Français  
> **Objet** : Déterminer précisément ce qui reste dans PyAccountingKit et ce qui doit relever d'un futur framework de Corporate Finance : VAN/NPV, TRI/IRR, coût du capital, valorisation, financement, risque, scénarios et simulations.

---

# 1. Résumé exécutif

PyAccountingKit doit rester un **framework comptable et d'analyse financière dérivée de la comptabilité**, et ne pas devenir progressivement un moteur général de finance d'entreprise.

La frontière cible est :

```text
ACCOUNTING FACTS
    |
    v
Financial Statements
    |
    v
PyAccountingKit Financial Analysis
    |
    +--> SIG
    +--> EBE / EBITDA
    +--> CAF
    +--> FRNG / BFR / Treasury
    +--> accounting-based ratios
    +--> historical trends
    +--> accounting-based risk diagnostics
    +--> immutable AnalysisSnapshot
    |
    v
Financial Facts / Analysis Snapshot
    |
    v
Future Corporate Finance Framework
    |
    +--> Investment Projects
    +--> Forecast Cash Flows
    +--> Discounting
    +--> NPV / VAN
    +--> IRR / TRI
    +--> Cost of Equity
    +--> Cost of Debt
    +--> WACC
    +--> Capital Structure
    +--> DCF
    +--> FCFF / FCFE
    +--> Enterprise / Equity Valuation
    +--> Sensitivity / Scenario Analysis
    +--> Monte Carlo
    +--> Project / Valuation Risk
```

Principe central :

```text
Historical accounting analysis
    belongs to PyAccountingKit

Forward-looking valuation and financing decisions
    belong outside PyAccountingKit
```

La règle la plus importante est :

```text
If a calculation requires future assumptions,
market inputs, discount rates, hypothetical financing,
valuation hypotheses or stochastic scenarios,
it is not part of the PyAccountingKit core.
```

---

# 2. Motivation

Le document `14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md` a déjà fixé une première frontière :

```text
In PyAccountingKit:
    SIG
    EBE
    EBITDA
    CAF
    FRNG
    BFR
    Treasury
    ratios
    diagnostics
    trends

Outside core:
    NPV / VAN
    IRR / TRI
    WACC
    DCF
    valuation
    investment appraisal
    financing optimization
    Monte Carlo
```

Le P2.3 transforme cette frontière en **contrat architectural explicite**.

---

# 3. Pourquoi ne pas tout mettre dans PyAccountingKit

Le moteur comptable travaille principalement sur :

```text
observed transactions
posted journal entries
trial balances
financial statements
accounting policies
reference snapshots
historical facts
```

Le Corporate Finance travaille principalement sur :

```text
future cash flows
assumptions
market prices
risk premia
capital structure
cost of capital
terminal values
investment alternatives
scenario probabilities
valuation models
```

Ces deux familles de problèmes n'ont pas le même statut sémantique.

---

# 4. Critère de frontière principal

Une capability reste dans PyAccountingKit si elle répond majoritairement aux questions :

```text
What happened?

What is the accounting position?

What historical financial performance is observable?

What accounting-based indicator can be deterministically derived?

What historical trend or diagnostic can be reproduced from pinned accounting snapshots?
```

Elle sort du core si elle répond à :

```text
What should we invest in?

What is an asset/company/project worth?

What discount rate should we use?

What will future cash flows be?

How should we finance the company?

What happens under uncertain future scenarios?
```

---

# 5. Decision Test

Pour chaque nouvelle feature, appliquer :

```text
Does it require only historical accounting facts?
    |
    +-- YES --> candidate for PyAccountingKit Financial Analysis
    |
    +-- NO --> Does it require future assumptions / markets / discounting?
                  |
                  +-- YES --> Corporate Finance / Risk / Planning framework
                  |
                  +-- NO --> evaluate as reporting/control extension
```

---

# 6. Bounded Contexts après P2.3

```text
PyAccountingKit
|
+-- Accounting Core
+-- Ledger
+-- Reporting
+-- Financial Analysis
+-- Subledgers
+-- Consolidation
+-- Reconciliation

Future framework
|
+-- Corporate Finance
    +-- Investment Appraisal
    +-- Cost of Capital
    +-- Financing
    +-- Valuation
    +-- Corporate Finance Risk
    +-- Scenario / Sensitivity
```

---

# 7. Nom du futur framework

Nom de travail recommandé :

```text
PyCorporateFinanceKit
```

Le nom est une décision de produit future, non une dépendance de PyAccountingKit.

PyAccountingKit ne doit pas importer :

```text
pycorporatefinancekit
```

Le sens de dépendance recommandé est :

```text
PyAccountingKit
    exposes stable financial facts
        |
        v
PyCorporateFinanceKit
    consumes them
```

---

# 8. Dépendance interdite

Interdit :

```text
PyAccountingKit
    ->
Corporate Finance runtime
```

Autorisé :

```text
Corporate Finance
    ->
PyAccountingKit public snapshots / protocols
```

---

# 9. Financial Analysis - scope conservé

Le bounded context `Financial Analysis` garde :

```text
SIG

EBE

EBITDA

CAF

FRNG

BFRE

BFRHE

BFR

Net Treasury

historical ratios

historical trends

accounting-based diagnostics

common-size analysis

period comparisons

financial statement decomposition
```

---

# 10. SIG

Reste dans :

```text
PyAccountingKit Financial Analysis
```

Car les SIG sont dérivés de :

```text
historical accounting statements
```

selon une définition analytique versionnée.

---

# 11. EBE / EBITDA

Reste dans PyAccountingKit.

Mais :

```text
EBE != EBITDA
```

et chaque définition doit être explicitement versionnée.

---

# 12. CAF

Reste dans PyAccountingKit.

Nature :

```text
historical accounting-derived indicator
```

---

# 13. FRNG / BFR / Treasury

Restent dans PyAccountingKit.

Ils décrivent :

```text
historical / current financial structure
```

à partir de données comptables observées.

---

# 14. Ratios historiques

Restent dans PyAccountingKit.

Exemples :

```text
NET_MARGIN

ROA

CURRENT_RATIO

DEBT_TO_ASSETS

EQUITY_RATIO

CFO_TO_REVENUE

ASSET_TURNOVER

INTEREST_COVERAGE

DEBT_SERVICE_COVERAGE
```

si leurs inputs sont comptables et leur définition explicite.

---

# 15. Ratios de marché

Sortent du core.

Exemples :

```text
P/E

EV/EBITDA market multiple

Price-to-Book

Dividend Yield

Enterprise Value / Revenue
```

car ils nécessitent typiquement :

```text
market price
shares outstanding
enterprise value
market capitalization
```

---

# 16. Exception - ratios de marché en lecture

PyAccountingKit peut éventuellement **stocker ou exposer** un indicateur importé comme external observation.

Mais il ne devient pas propriétaire du modèle de marché.

---

# 17. Historical trend analysis

Reste dans PyAccountingKit :

```text
N vs N-1

multi-period trends

growth of accounting metrics

historical margins

historical working-capital evolution
```

---

# 18. Forecast trend

Sort du core.

```text
Revenue 2027E

EBITDA 2028E

FCF 2030E
```

sont des données prévisionnelles.

---

# 19. Historical common-size analysis

Reste dans PyAccountingKit.

Exemples :

```text
expense / revenue

cash / total assets

debt / total liabilities
```

sur données historiques.

---

# 20. Forecast common-size analysis

Relève de :

```text
Planning / Corporate Finance
```

si basé sur projections.

---

# 21. Diagnostic financier

Reste dans PyAccountingKit lorsque le diagnostic est :

```text
historical

accounting-based

rule-based

reproducible
```

---

# 22. Exemple diagnostic PyAccountingKit

```text
Liquidity weakened because:
    Current Ratio declined from 1.6 to 1.1

Leverage increased because:
    Debt / Equity increased from 0.9 to 1.4
```

---

# 23. Diagnostic prédictif

Sort du core si la conclusion dépend de :

```text
forecast

market conditions

probability model

future scenario
```

---

# 24. Scores financiers

Deux catégories.

```text
Accounting-Based Score
    -> can remain in PyAccountingKit

Predictive / Market / Credit Model
    -> external framework
```

---

# 25. Accounting-Based Score

Exemple :

```text
weighted historical ratios
```

avec formule explicite.

Peut rester dans `Financial Analysis`.

---

# 26. Predictive default score

Si le score représente :

```text
probability of future default
```

sur un modèle statistique/ML, il ne doit pas être confondu avec un simple diagnostic comptable.

Boundary :

```text
Risk / Credit Analytics extension
```

---

# 27. Risque - pourquoi le terme est ambigu

`Risk` recouvre plusieurs notions :

```text
accounting financial risk indicators

liquidity risk

leverage risk

concentration risk

market risk

credit risk

project risk

valuation risk

interest-rate risk

FX market risk

stochastic risk
```

P2.3 doit les séparer.

---

# 28. Accounting-Based Financial Risk

Reste dans PyAccountingKit si calculé depuis :

```text
historical statements

subledger snapshots

consolidated snapshots
```

---

# 29. Exemples in-core risk diagnostics

```text
liquidity ratio deterioration

high leverage

interest coverage deterioration

working-capital stress

customer concentration

supplier concentration

debt maturity concentration if source data exists

covenant-like accounting ratio breach
```

---

# 30. Limite des diagnostics de risque

PyAccountingKit peut dire :

```text
historical liquidity position is weak under definition X
```

mais ne doit pas automatiquement dire :

```text
probability of insolvency next year = 27.3%
```

sans modèle de risque externe/versionné.

---

# 31. Market Risk

Hors PyAccountingKit core.

Exemples :

```text
beta

asset-price volatility

interest-rate sensitivity

market VaR

Expected Shortfall

option Greeks
```

---

# 32. Project Risk

Hors core.

Exemples :

```text
probability NPV < 0

project cash-flow volatility

scenario-weighted IRR

Monte Carlo project valuation
```

---

# 33. Valuation Risk

Hors core.

Exemples :

```text
terminal value sensitivity

WACC sensitivity

growth-rate sensitivity

multiple sensitivity
```

---

# 34. NPV / VAN

Hors PyAccountingKit.

Objet futur :

```text
NetPresentValue
```

---

# 35. Pourquoi VAN sort du core

Elle requiert :

```text
cash-flow series

discount rate

timing convention

investment assumptions
```

---

# 36. `InvestmentProject`

Objet futur Corporate Finance :

```text
InvestmentProject
|
+-- id
+-- name
+-- initial_investment
+-- projected_cash_flows
+-- terminal_cash_flow?
+-- currency
+-- assumptions
+-- scenario_ref?
```

---

# 37. `ProjectCashFlow`

```text
ProjectCashFlow
|
+-- period
+-- cash_flow_type
+-- amount
+-- currency
+-- source
+-- assumption_ref?
```

---

# 38. Cash-flow source distinction

```text
Historical Cash Flow
    -> PyAccountingKit

Projected Cash Flow
    -> Corporate Finance / Planning
```

---

# 39. Historical CFO

Reste dans PyAccountingKit.

---

# 40. Forecast FCF

Hors core.

---

# 41. `DiscountRate`

Objet Corporate Finance.

```text
DiscountRate
|
+-- annual_rate
+-- compounding
+-- convention
+-- source
+-- effective_date
+-- assumptions
```

---

# 42. Time Value of Money

Hors PyAccountingKit core.

Capabilities :

```text
present value

future value

annuity

perpetuity

discount factors
```

---

# 43. TRI / IRR

Hors core.

---

# 44. IRR result

Objet futur :

```text
InternalRateOfReturnResult
```

Doit gérer :

```text
no root

one root

multiple roots

numerical convergence failure
```

---

# 45. Multiple IRRs

Le futur framework doit traiter explicitement les cash flows non conventionnels.

PyAccountingKit ne doit pas embarquer cette complexité numérique.

---

# 46. MIRR

Hors core.

---

# 47. Payback Period

Classification :

```text
Corporate Finance
```

même si le payback simple ne discount pas.

Pourquoi :

```text
investment decision metric
```

---

# 48. Discounted Payback

Corporate Finance.

---

# 49. Profitability Index

Corporate Finance.

---

# 50. Equivalent Annual Annuity

Corporate Finance.

---

# 51. Cost of Capital

Hors PyAccountingKit.

---

# 52. Cost of Equity

Objet futur :

```text
CostOfEquity
```

Méthodes possibles :

```text
CAPM

build-up

dividend-growth

custom
```

---

# 53. CAPM

Nécessite :

```text
risk-free rate

beta

market risk premium
```

Donc hors core comptable.

---

# 54. Beta

Hors core.

---

# 55. Risk-Free Rate

External market observation.

---

# 56. Market Risk Premium

External corporate-finance assumption / market input.

---

# 57. Cost of Debt

Corporate Finance lorsqu'il s'agit d'estimer :

```text
marginal cost of borrowing

market yield

forward financing cost
```

---

# 58. Historical interest expense ratio

Peut rester dans PyAccountingKit.

Exemple :

```text
historical interest expense / average debt
```

mais doit être nommé comme **historical accounting-derived rate**, pas `CostOfDebt` sans qualification.

---

# 59. After-tax Cost of Debt

Corporate Finance.

---

# 60. WACC

Hors core.

Objet futur :

```text
WeightedAverageCostOfCapital
```

---

# 61. WACC inputs

```text
market value of equity

market value of debt

cost of equity

cost of debt

tax rate assumption

capital structure weights
```

---

# 62. Accounting debt/equity ratio

Reste dans PyAccountingKit.

---

# 63. Market-value capital structure

Corporate Finance.

---

# 64. Target capital structure

Corporate Finance.

---

# 65. Capital Structure Optimization

Corporate Finance.

---

# 66. Financing alternatives

Corporate Finance :

```text
debt

equity

convertible

hybrid

lease financing

project financing
```

---

# 67. Historical debt schedule

Peut être consommé/exposé par PyAccountingKit si source disponible.

---

# 68. Future debt schedule simulation

Corporate Finance / Treasury Planning.

---

# 69. DCF Valuation

Hors PyAccountingKit.

---

# 70. `ValuationRun`

Objet futur :

```text
ValuationRun
|
+-- valuation_date
+-- valuation_method
+-- forecast_snapshot
+-- discount_rate_snapshot
+-- terminal_value_policy
+-- adjustments
+-- result
+-- sensitivity_refs
+-- version
```

---

# 71. Valuation methods

```text
DCF_FCFF

DCF_FCFE

DIVIDEND_DISCOUNT

MULTIPLES

ASSET_BASED

CUSTOM
```

Corporate Finance.

---

# 72. FCFF

Hors core comme forecast valuation measure.

---

# 73. Historical FCFF-like indicator

PyAccountingKit peut éventuellement calculer un **historical analytical cash-flow indicator** si sa définition est explicite.

Mais il ne doit pas le transformer automatiquement en forecast valuation cash flow.

---

# 74. FCFE

Même règle.

---

# 75. Terminal Value

Corporate Finance.

---

# 76. Gordon Growth

Corporate Finance.

---

# 77. Exit Multiple

Corporate Finance.

---

# 78. Enterprise Value

Corporate Finance.

---

# 79. Equity Value

Corporate Finance.

---

# 80. Net Debt

Deux niveaux :

```text
Historical Net Debt
    -> PyAccountingKit Financial Analysis

Valuation Net Debt Adjustments
    -> Corporate Finance
```

---

# 81. Net Debt historical

Peut être un indicateur versionné basé sur comptes/statement lines explicites.

---

# 82. Valuation adjustments

Exemples :

```text
lease adjustments

pension adjustments

minority interests

non-operating assets

contingent liabilities
```

Corporate Finance / valuation policy.

---

# 83. Comparable Company Analysis

Corporate Finance.

---

# 84. Precedent Transactions

Corporate Finance.

---

# 85. Multiples

Distinction :

```text
Historical accounting multiple denominator
    -> PyAccountingKit may provide denominator facts

Market valuation multiple
    -> Corporate Finance
```

---

# 86. Example

```text
EBITDA historical
    -> PyAccountingKit

Enterprise Value / EBITDA
    -> Corporate Finance
```

---

# 87. Investment Appraisal

Hors core.

Regroupe :

```text
NPV
IRR
MIRR
Payback
Discounted Payback
Profitability Index
Equivalent Annual Annuity
```

---

# 88. Project selection

Corporate Finance.

---

# 89. Mutually exclusive projects

Corporate Finance.

---

# 90. Capital rationing

Corporate Finance.

---

# 91. Scenario Analysis

Hors PyAccountingKit core dès que :

```text
future assumptions vary
```

---

# 92. Historical scenario comparison

PyAccountingKit peut comparer :

```text
actual N
vs
actual N-1
```

Ce n'est pas du scenario planning.

---

# 93. Future scenarios

Corporate Finance / Planning :

```text
BASE
UPSIDE
DOWNSIDE
STRESS
CUSTOM
```

---

# 94. `FinancialScenario`

Objet futur :

```text
FinancialScenario
|
+-- scenario_id
+-- assumptions
+-- projected_financials
+-- probability?
+-- version
```

---

# 95. Sensitivity Analysis

Corporate Finance lorsque :

```text
WACC
terminal growth
revenue growth
margin
capex
working capital
```

sont choqués.

---

# 96. `SensitivityRun`

Objet futur.

---

# 97. Tornado analysis

Corporate Finance visualization / analytics.

---

# 98. Monte Carlo

Hors core.

---

# 99. Pourquoi Monte Carlo sort

Nécessite :

```text
probability distributions

correlations

random generation

simulation engine

seed

scenario statistics
```

---

# 100. `MonteCarloRun`

Objet futur :

```text
MonteCarloRun
|
+-- model_version
+-- distributions
+-- correlation_model
+-- iterations
+-- seed
+-- output_distribution
+-- risk_metrics
```

---

# 101. Stochastic risk metrics

Corporate Finance / Risk.

---

# 102. Probability NPV < 0

Corporate Finance.

---

# 103. Distribution of IRR

Corporate Finance.

---

# 104. Value at Risk

Pas PyAccountingKit core.

---

# 105. Expected Shortfall

Pas PyAccountingKit core.

---

# 106. Covenant Analysis

Boundary spécifique.

---

# 107. Historical covenant test

Peut rester dans PyAccountingKit si :

```text
formula is accounting-based

period is historical

threshold is explicit/versioned
```

---

# 108. Forecast covenant headroom

Corporate Finance / Treasury Planning.

---

# 109. Credit Analysis

Deux niveaux.

```text
Historical borrower diagnostics
    -> potentially PyAccountingKit Financial Analysis

Forward credit underwriting / PD / pricing
    -> separate Credit/Risk framework
```

---

# 110. Concentration Risk

Historical concentration from :

```text
AR subledger
AP subledger
```

peut rester dans PyAccountingKit.

---

# 111. Concentration stress simulation

Hors core.

---

# 112. Liquidity analysis

Historical :

```text
current ratio
quick ratio
cash ratio
working capital
cash flow coverage
```

PyAccountingKit.

---

# 113. Liquidity forecast

Corporate Finance / Treasury / Planning.

---

# 114. Debt maturity analysis

Si fondé sur instruments existants et échéanciers observés :

```text
historical/current analytical view
```

peut être exposé par PyAccountingKit.

---

# 115. Refinancing risk simulation

Hors core.

---

# 116. Interest-rate shock

Hors core.

---

# 117. FX shock

Hors core.

---

# 118. Historical FX effects

Peuvent être analysés dans PyAccountingKit à partir des écritures réelles.

---

# 119. Budgeting

Hors PyAccountingKit core.

---

# 120. Forecasting

Hors PyAccountingKit core.

---

# 121. FP&A boundary

Le futur Corporate Finance framework ne doit pas nécessairement devenir un framework FP&A complet.

Architecture recommandée :

```text
Historical Accounting
    -> PyAccountingKit

Budgets / Forecasts
    -> Planning / FP&A source

Corporate Finance
    consumes both
```

---

# 122. Forecast ownership

Corporate Finance peut accepter :

```text
ForecastSnapshot
```

mais ne doit pas nécessairement en être l'auteur.

---

# 123. `ForecastSnapshot`

Contrat futur possible :

```text
ForecastSnapshot
|
+-- scenario
+-- periods
+-- projected_income_statement
+-- projected_balance_sheet
+-- projected_cash_flow
+-- assumptions
+-- checksum
```

---

# 124. PyAccountingKit input to forecast

PyAccountingKit fournit :

```text
historical baselines
```

pas la projection elle-même.

---

# 125. Normalized Financials

Boundary délicate.

---

# 126. Historical restatement for comparability

Peut rester dans PyAccountingKit si :

```text
explicit analytical definition

non-destructive

snapshot-based
```

---

# 127. Valuation normalization

Exemples :

```text
remove exceptional litigation

adjust owner compensation

normalize one-off restructuring
```

Relève plutôt de Corporate Finance / valuation.

---

# 128. Why

Ces ajustements sont souvent :

```text
judgmental

valuation-purpose-specific
```

---

# 129. `ValuationNormalizationAdjustment`

Objet futur Corporate Finance.

---

# 130. Historical accounting remains unchanged

Toujours.

---

# 131. Data flow cible

```text
JournalEntryLine
    ↓
Ledger
    ↓
TrialBalanceSnapshot
    ↓
Financial Statements
    ↓
AnalysisSnapshot
    ↓
FinancialFactsSnapshot
    ↓
Corporate Finance
```

---

# 132. `FinancialFactsSnapshot`

Bridge recommandé entre frameworks.

```text
FinancialFactsSnapshot
|
+-- entity_or_group_ref
+-- as_of / period
+-- statement_snapshot_refs
+-- analysis_snapshot_ref
+-- historical_series
+-- currencies
+-- source_checksums
+-- definition_versions
+-- checksum
```

---

# 133. Why a bridge object

Évite que Corporate Finance dépende :

```text
des repositories

des ORM models

des JournalEntry internals
```

---

# 134. Financial facts are immutable inputs

Corporate Finance doit consommer des facts pinés.

---

# 135. Corporate Finance cannot mutate accounting

Même règle que Consolidation/Analysis.

---

# 136. Possible port

```python
class FinancialFactsProvider(Protocol):
    def get_snapshot(...): ...
    def get_historical_series(...): ...
```

---

# 137. Provider ownership

PyAccountingKit peut implémenter :

```text
FinancialFactsProvider
```

---

# 138. Corporate Finance dependency

Le futur framework dépend seulement de ce port ou de DTOs publics.

---

# 139. No shared database assumption

---

# 140. No shared ORM assumption

---

# 141. Market Data

Le Corporate Finance a besoin d'un autre port :

```text
MarketDataProvider
```

---

# 142. `MarketDataProvider`

Possible :

```python
class MarketDataProvider(Protocol):
    def risk_free_rate(...): ...
    def market_risk_premium(...): ...
    def equity_price(...): ...
    def beta(...): ...
    def comparable_multiples(...): ...
```

---

# 143. Market data never becomes accounting data

---

# 144. `MarketDataSnapshot`

Must be pinned for valuation replay.

---

# 145. Assumptions

Corporate Finance introduces :

```text
AssumptionSet
```

---

# 146. `AssumptionSet`

```text
AssumptionSet
|
+-- id
+-- version
+-- scenario
+-- variables
+-- source
+-- reviewer?
+-- checksum
```

---

# 147. No assumptions inside historical accounting facts

---

# 148. Reproducibility split

PyAccountingKit snapshot pins :

```text
accounting facts
analysis definitions
```

Corporate Finance snapshot pins :

```text
financial facts
forecasts
market data
assumptions
discount rates
valuation model
scenario model
```

---

# 149. `CorporateFinanceReproducibilityEnvelope`

Future object.

---

# 150. NPV reproducibility

Needs :

```text
cash flows
cash flow dates
rate
convention
model version
```

---

# 151. WACC reproducibility

Needs :

```text
risk-free rate
beta
market risk premium
cost of debt
tax assumption
capital structure
source dates
```

---

# 152. DCF reproducibility

Needs :

```text
forecast snapshot
WACC snapshot
terminal value policy
net debt adjustments
valuation date
```

---

# 153. Monte Carlo reproducibility

Needs :

```text
seed
distributions
correlations
iterations
model version
```

---

# 154. Historical financial risk objects

Possible PyAccountingKit objects :

```text
FinancialRiskIndicatorDefinition

FinancialRiskIndicatorValue

RiskDiagnostic
```

---

# 155. Scope restriction

They are allowed only when :

```text
historical
accounting-based
deterministic
```

---

# 156. `RiskDiagnosticType`

Possible :

```text
LIQUIDITY
LEVERAGE
COVERAGE
WORKING_CAPITAL
CONCENTRATION
COVENANT
```

---

# 157. No probabilistic semantics by default

---

# 158. Financial Analysis read-only rule

Toujours :

```text
Financial Analysis
    cannot mutate JournalEntry
```

---

# 159. Corporate Finance read-only accounting rule

Toujours :

```text
Corporate Finance
    cannot mutate JournalEntry
```

---

# 160. Decision output

Corporate Finance peut produire :

```text
Recommendation

InvestmentDecisionSupport

ValuationResult

FinancingScenario
```

mais aucun de ces objets n'est une écriture comptable.

---

# 161. Accounting consequence of a finance decision

Si une décision entraîne ensuite une opération réelle :

```text
Corporate Finance decision
    ↓
Operational transaction
    ↓
AccountingEvent
    ↓
PyAccountingKit
```

---

# 162. No direct valuation-to-posting

Interdit :

```text
DCF result
    ->
JournalEntry POSTED
```

sans policy comptable spécifique et événement reconnu.

---

# 163. Fair value boundary

Important :

```text
Valuation for accounting measurement
    !=
Enterprise valuation
```

---

# 164. Accounting fair value measurement

Peut rester lié à PyAccountingKit `MeasurementPolicy` si :

```text
required by an accounting policy
```

---

# 165. Enterprise valuation

Corporate Finance.

---

# 166. Example

```text
Fair value of financial instrument for accounting measurement
    -> accounting MeasurementPolicy / external valuation provider

Enterprise value for M&A
    -> Corporate Finance
```

---

# 167. Impairment boundary

Accounting impairment :

```text
PyAccountingKit policy / supporting domain
```

Enterprise valuation downside case :

```text
Corporate Finance
```

---

# 168. Goodwill boundary

Accounting goodwill in consolidation :

```text
PyAccountingKit Consolidation
```

M&A valuation premium :

```text
Corporate Finance
```

---

# 169. Cost of capital as accounting input?

If an accounting measurement policy requires a discount rate :

```text
PyAccountingKit may consume an externally supplied rate
```

but does not become owner of WACC/CAPM calculation.

---

# 170. `ValuationProvider` from P0.5

The policy layer can receive :

```text
external observations
valuation inputs
```

without embedding Corporate Finance.

---

# 171. Discounted accounting measurement

Example class :

```text
present-value measurement required by accounting policy
```

Can remain in Measurement architecture.

---

# 172. Key distinction

```text
Discounting as an accounting measurement technique
    can be in PyAccountingKit

Discounting to decide investment/value of firm
    belongs to Corporate Finance
```

---

# 173. Time value primitive sharing

Potential shared utility :

```text
discount_factor
```

should not force module ownership.

---

# 174. Recommendation

Do not put generic Corporate Finance math in PyAccountingKit core merely because an accounting policy occasionally uses present value.

---

# 175. Shared numerical utilities

If needed, extract to :

```text
small neutral utility package
```

or duplicate minimal pure math behind separate contracts.

---

# 176. Avoid dependency inversion violation

---

# 177. Valuation methods matrix

| Capability | PyAccountingKit | Future Corporate Finance |
|---|---:|---:|
| Historical EBITDA | **oui** | consomme |
| Historical CFO | **oui** | consomme |
| Historical Net Debt | **oui** | consomme |
| Historical ratios | **oui** | consomme |
| Forecast revenue | non | **oui / external forecast** |
| Forecast FCF | non | **oui** |
| NPV | non | **oui** |
| IRR | non | **oui** |
| WACC | non | **oui** |
| DCF | non | **oui** |
| Terminal Value | non | **oui** |
| Enterprise Value | non | **oui** |
| Equity Value | non | **oui** |
| Comparable Multiples | non | **oui** |
| Sensitivity Analysis | non | **oui** |
| Monte Carlo | non | **oui** |

---

# 178. Risk matrix

| Risk capability | PyAccountingKit | Corporate Finance / Risk |
|---|---:|---:|
| Historical liquidity risk indicators | **oui** | consomme |
| Historical leverage diagnostics | **oui** | consomme |
| Historical concentration | **oui** | consomme |
| Historical covenant test | **oui** | consomme |
| Forecast covenant headroom | non | **oui** |
| Beta | non | **oui** |
| Market volatility model | non | **oui** |
| VaR / Expected Shortfall | non | **oui / risk framework** |
| NPV-at-risk | non | **oui** |
| Monte Carlo project risk | non | **oui** |
| WACC sensitivity | non | **oui** |
| Refinancing scenario risk | non | **oui** |

---

# 179. Financing matrix

| Capability | PyAccountingKit | Corporate Finance |
|---|---:|---:|
| Historical debt balance | **oui** | consomme |
| Historical interest expense | **oui** | consomme |
| Historical debt/equity | **oui** | consomme |
| Current debt schedule if source available | read/analysis | consomme |
| Cost of new debt | non | **oui** |
| Target leverage | non | **oui** |
| Optimal capital structure | non | **oui** |
| Debt vs equity decision | non | **oui** |
| Refinancing simulation | non | **oui** |

---

# 180. Planning matrix

| Capability | PyAccountingKit | Planning / Corporate Finance |
|---|---:|---:|
| Historical actuals | **oui** | consomme |
| Historical trend | **oui** | consomme |
| Budget | non | **oui / FP&A** |
| Forecast | non | **oui / FP&A** |
| Scenario plan | non | **oui** |
| Stress plan | non | **oui** |

---

# 181. Proposed future Corporate Finance bounded contexts

```text
Corporate Finance
|
+-- Time Value of Money
|
+-- Investment Appraisal
|
+-- Capital Structure
|
+-- Cost of Capital
|
+-- Valuation
|
+-- Scenario & Sensitivity
|
+-- Corporate Finance Risk
```

---

# 182. Time Value of Money

Objects :

```text
DiscountConvention
DiscountCurve
PresentValueResult
FutureValueResult
```

---

# 183. Investment Appraisal

Objects :

```text
InvestmentProject
ProjectCashFlow
NPVResult
IRRResult
MIRRResult
PaybackResult
ProfitabilityIndex
```

---

# 184. Capital Structure

Objects :

```text
CapitalStructure
DebtComponent
EquityComponent
TargetCapitalStructure
FinancingScenario
```

---

# 185. Cost of Capital

Objects :

```text
CostOfEquityDefinition
CostOfDebtDefinition
CAPMDefinition
WACCDefinition
CostOfCapitalSnapshot
```

---

# 186. Valuation

Objects :

```text
ValuationModelDefinition
ValuationRun
DCFValuation
FCFFValuation
FCFEValuation
TerminalValue
EnterpriseValue
EquityValue
ValuationAdjustment
```

---

# 187. Scenario & Sensitivity

Objects :

```text
FinancialScenario
SensitivityDefinition
SensitivityRun
ScenarioComparison
```

---

# 188. Corporate Finance Risk

Objects :

```text
RiskFactor
RiskDistribution
RiskScenario
MonteCarloDefinition
MonteCarloRun
RiskMetric
```

---

# 189. Corporate Finance source inputs

```text
FinancialFactsSnapshot

ForecastSnapshot

MarketDataSnapshot

AssumptionSet
```

---

# 190. Corporate Finance outputs

```text
InvestmentAnalysisSnapshot

CostOfCapitalSnapshot

ValuationSnapshot

FinancingScenarioSnapshot

RiskAnalysisSnapshot
```

---

# 191. Immutable outputs

Recommended.

---

# 192. Snapshot pattern reuse

Future framework should reuse the same architectural principles :

```text
versioned definitions

pinned inputs

immutable snapshots

audit

replay

fail-closed ambiguity
```

---

# 193. But not same domain package

---

# 194. API boundary

PyAccountingKit can expose :

```text
accounting.analysis.snapshot(...)

accounting.statements.snapshot(...)

accounting.consolidation.publish(...)
```

Corporate Finance consumes those IDs/DTOs.

---

# 195. Possible Corporate Finance API

Future example :

```python
finance = CorporateFinanceApplication(...)
```

---

# 196. Example NPV

```python
result = finance.investments.npv(
    project_id=project.id,
    discount_rate=rate,
)
```

---

# 197. Example IRR

```python
result = finance.investments.irr(
    project_id=project.id,
)
```

---

# 198. Example WACC

```python
wacc = finance.cost_of_capital.wacc(
    entity_id=entity_id,
    market_snapshot=market,
    capital_structure=structure,
)
```

---

# 199. Example DCF

```python
valuation = finance.valuation.dcf(
    forecast_snapshot=forecast,
    wacc_snapshot=wacc,
    terminal_value_policy=terminal_policy,
)
```

---

# 200. Example Monte Carlo

```python
risk = finance.risk.monte_carlo(
    model=valuation_model,
    distributions=distributions,
    iterations=100_000,
    seed=42,
)
```

---

# 201. No such API under `accounting.*`

Do not add :

```text
accounting.analysis.wacc()

accounting.analysis.dcf()

accounting.analysis.monte_carlo()
```

---

# 202. In-core advanced analytics still acceptable

PyAccountingKit may grow advanced historical analysis such as :

```text
multi-period decomposition

historical variance analysis

historical distribution of margins

historical rolling ratios

accounting-based concentration analysis

historical cash conversion cycle
```

---

# 203. Historical statistical analysis

Can remain if it describes observed accounting data only.

---

# 204. Example

```text
5-year historical EBITDA margin mean / median / variance
```

can be in Financial Analysis.

---

# 205. But predictive inference

```text
forecast next year's EBITDA distribution
```

is out.

---

# 206. Correlation historical

A historical correlation between observed accounting metrics may remain analytical.

---

# 207. Correlation used as simulation input

Corporate Finance / Risk.

---

# 208. Peer analysis

Boundary :

```text
historical internal peer entities
    -> PyAccountingKit possible

public market comparable companies
    -> Corporate Finance / Market Data
```

---

# 209. Consolidated analysis

PyAccountingKit Financial Analysis can consume :

```text
Consolidated ReportSnapshot
```

---

# 210. Group valuation

Corporate Finance.

---

# 211. Subledger analytics

PyAccountingKit can expose :

```text
DSO
DPO
aging
concentration
```

when historical/accounting-based.

---

# 212. Working-capital optimization

If the feature recommends future policy changes :

```text
Corporate Finance / FP&A
```

---

# 213. Cash Conversion Cycle

Historical CCC can remain in PyAccountingKit.

---

# 214. Target CCC

Outside core.

---

# 215. Performance attribution

Historical accounting attribution can remain.

---

# 216. Shareholder-return attribution

Market/corporate finance.

---

# 217. ROIC

Boundary :

Historical ROIC can remain if definition uses historical accounting inputs.

---

# 218. EVA / Economic Profit

Boundary :

If it requires :

```text
WACC
```

then Corporate Finance.

---

# 219. Historical operating profit after tax

Can be an accounting-derived analytical input.

---

# 220. Economic Value Added

Corporate Finance due to cost of capital.

---

# 221. Residual Income Valuation

Corporate Finance.

---

# 222. Shareholder Value Added

Corporate Finance.

---

# 223. DuPont Analysis

Historical DuPont decomposition can stay in PyAccountingKit.

---

# 224. Forecast DuPont

Outside core.

---

# 225. Break-even analysis

Boundary dependent.

Historical observed break-even diagnostics can be analytical.

Forward decision model belongs Planning/Corporate Finance.

---

# 226. Operating leverage

Historical degree of operating leverage may remain if derived deterministically.

Scenario leverage simulation is outside.

---

# 227. Financial leverage

Historical leverage indicators remain.

Optimal leverage decision is Corporate Finance.

---

# 228. Debt capacity

Forward debt capacity is Corporate Finance / Credit.

---

# 229. Historical debt capacity proxy

Can exist but must be named as a proxy/diagnostic, not future borrowing capacity.

---

# 230. Return on Invested Capital

Historical : PyAccountingKit.

---

# 231. Invested Capital Valuation

Corporate Finance.

---

# 232. Economic balance sheet

If purely analytical reclassification of historical accounts : potentially PyAccountingKit.

If it introduces market values / valuation assumptions : Corporate Finance.

---

# 233. Risk-adjusted return

If risk adjustment requires market/model risk : outside core.

---

# 234. Risk-free discounted cash flow

Corporate Finance.

---

# 235. Certainty equivalent

Corporate Finance.

---

# 236. Real options

Corporate Finance.

---

# 237. Black-Scholes / option pricing

Outside PyAccountingKit.

---

# 238. M&A

Corporate Finance.

---

# 239. Acquisition accretion/dilution

Corporate Finance.

---

# 240. Synergy valuation

Corporate Finance.

---

# 241. Purchase Price Allocation

Boundary :

```text
transaction valuation / allocation model
    -> Corporate Finance / specialized M&A

accounting recognition of resulting assets/goodwill
    -> PyAccountingKit policies / consolidation
```

---

# 242. Dividends

Historical dividend accounting : PyAccountingKit.

Dividend policy optimization : Corporate Finance.

---

# 243. Share buybacks

Accounting effects : PyAccountingKit.

Buyback valuation/decision : Corporate Finance.

---

# 244. Capital increase

Accounting effects : PyAccountingKit.

Financing decision : Corporate Finance.

---

# 245. Debt issuance

Accounting effects after transaction : PyAccountingKit.

Pricing/structure before issuance : Corporate Finance.

---

# 246. Boundary principle - decision vs accounting consequence

```text
Decision model
    -> Corporate Finance

Executed transaction
    -> AccountingEvent
    -> PyAccountingKit
```

---

# 247. Market data dependency

PyAccountingKit core should not require :

```text
Bloomberg
Reuters
exchange prices
risk-free curves
market betas
```

---

# 248. Corporate Finance may integrate market providers

---

# 249. External Market Data Adapter

Future.

---

# 250. Auditability

Both frameworks should preserve :

```text
who
what
when
source
version
assumption
result
```

---

# 251. Different audit semantics

Accounting audit :

```text
bookkeeping / regulatory evidence
```

Corporate Finance audit :

```text
model / assumption / decision evidence
```

---

# 252. Controls boundary

PyAccountingKit Controls can verify :

```text
analysis definition completeness
snapshot reproducibility
historical ratio consistency
```

---

# 253. Corporate Finance controls

Future :

```text
forecast completeness
WACC inputs complete
terminal value consistency
scenario probabilities sum to 1
Monte Carlo seed present
valuation bridge reconciled
```

---

# 254. No Corporate Finance control catalog in PyAccountingKit core

---

# 255. Testing boundary

PyAccountingKit tests :

```text
historical accounting analytics
```

Corporate Finance tests :

```text
NPV
IRR numerical behavior
WACC
DCF
scenario
Monte Carlo
```

---

# 256. Shared golden inputs

Historical financial facts can be shared.

---

# 257. NPV property tests future

```text
zero discount rate => sum cash flows

higher positive discount rate lowers PV for positive future cash flows
```

Corporate Finance only.

---

# 258. IRR numerical tests future

Corporate Finance only.

---

# 259. WACC tests future

Corporate Finance only.

---

# 260. Monte Carlo deterministic-seed tests future

Corporate Finance only.

---

# 261. Release boundary

PyAccountingKit adding Corporate Finance calculations would no longer be a minor analytical extension.

It would materially expand the domain.

---

# 262. Recommendation

Do not place those features into :

```text
pyaccountingkit.analysis
```

---

# 263. Optional integration package

Potential :

```text
pyaccountingkit-corporate-finance-bridge
```

only if a separate framework exists.

---

# 264. Better default

Use stable DTO/protocol integration without a bridge package initially.

---

# 265. Public API change required in PyAccountingKit

P2.3 recommends only adding :

```text
FinancialFactsSnapshot
FinancialFactsProvider
```

if/when the downstream framework is implemented.

---

# 266. No implementation required now

P2.3 is a **boundary document**.

---

# 267. `AdvancedFinancialAnalysisBoundaryPolicy`

Optional architectural object/documented rule :

```text
HISTORICAL_ACCOUNTING

FORWARD_CORPORATE_FINANCE

MARKET_RISK

PLANNING
```

---

# 268. Capability classification

```text
CapabilityClassification
|
+-- code
+-- owner_context
+-- rationale
+-- required_input_types
+-- prohibited_dependencies
```

---

# 269. Why useful

Prevents future scope creep.

---

# 270. Classification example - NPV

```text
owner_context:
    CORPORATE_FINANCE

requires:
    projected_cash_flows
    discount_rate

prohibited_in:
    PYACCOUNTINGKIT_CORE
```

---

# 271. Classification example - Current Ratio

```text
owner_context:
    FINANCIAL_ANALYSIS

requires:
    historical statement lines
```

---

# 272. Classification example - Beta

```text
owner_context:
    MARKET_RISK / CORPORATE_FINANCE

requires:
    market return series
```

---

# 273. Classification example - Historical Customer Concentration

```text
owner_context:
    FINANCIAL_ANALYSIS

requires:
    subledger snapshot
```

---

# 274. Classification example - Forecast DSO

```text
owner_context:
    PLANNING / CORPORATE_FINANCE
```

---

# 275. Complete boundary matrix

| Capability | PyAccountingKit | Future Corporate Finance | Planning / FP&A | Risk-specialized |
|---|---:|---:|---:|---:|
| Historical P&L / BS / CF | **oui** | input | input | input |
| SIG / EBE / EBITDA | **oui** | input | input | input |
| CAF | **oui** | input | input | input |
| FRNG / BFR / Treasury | **oui** | input | input | input |
| Historical ratios | **oui** | input | input | input |
| Historical diagnostics | **oui** | input | input | input |
| Historical concentration | **oui** | input | input | input |
| Historical covenant test | **oui** | input | input | input |
| Budget | non | input | **oui** | input |
| Forecast | non | input | **oui** | input |
| NPV / VAN | non | **oui** | non | input |
| IRR / TRI | non | **oui** | non | input |
| MIRR | non | **oui** | non | input |
| Payback | non | **oui** | non | input |
| Cost of Equity | non | **oui** | non | input |
| Cost of Debt | non | **oui** | non | input |
| WACC | non | **oui** | non | input |
| Target Capital Structure | non | **oui** | input | input |
| DCF | non | **oui** | input | input |
| FCFF / FCFE forecast | non | **oui** | input | input |
| Enterprise Value | non | **oui** | non | input |
| Equity Value | non | **oui** | non | input |
| Comparable Companies | non | **oui** | non | input |
| Sensitivity | non | **oui** | input | input |
| Scenario valuation | non | **oui** | input | input |
| Monte Carlo valuation | non | **oui** | non | **oui possible** |
| Beta | non | **oui input** | non | **oui** |
| VaR / ES | non | possible | non | **oui** |
| Forecast covenant headroom | non | **oui** | **oui** | input |
| Accounting fair-value measurement | **oui via policy/provider** | source possible | non | input |
| Enterprise valuation | non | **oui** | non | input |

---

# 276. Objects that remain in PyAccountingKit

```text
FinancialIndicatorDefinition
FinancialIndicatorValue
FinancialRatioDefinition
FinancialRatioValue
FinancialScoreDefinition
FinancialScoreValue
FinancialDiagnostic
AnalysisDefinitionSet
AnalysisSnapshot
CalculationTrace
HistoricalTrend
HistoricalComparison
FunctionalBalance
WorkingCapitalAnalysis
```

---

# 277. Objects that do not enter PyAccountingKit core

```text
InvestmentProject
ProjectedCashFlow
DiscountRate
DiscountCurve
NPVResult
IRRResult
MIRRResult
WACCDefinition
CostOfEquity
CostOfDebt
CapitalStructure
ValuationRun
DCFValuation
TerminalValue
EnterpriseValue
EquityValue
ComparableSet
SensitivityRun
FinancialScenario
MonteCarloRun
MarketRiskMetric
```

---

# 278. Objects that may bridge both worlds

```text
FinancialFactsSnapshot
HistoricalFinancialSeries
ExternalObservation
Money
CurrencyCode
EntityRef
GroupRef
PeriodRef
```

---

# 279. Money reuse

The future framework may depend on a neutral/shared `Money` contract or PyAccountingKit public type.

---

# 280. Avoid cyclical dependency

---

# 281. Corporate Finance package target - conceptual

```text
src/pycorporatefinancekit/
|
+-- domain/
|   +-- investments/
|   +-- cost_of_capital/
|   +-- financing/
|   +-- valuation/
|   +-- scenarios/
|   +-- risk/
|
+-- application/
|
+-- ports/
|   +-- financial_facts.py
|   +-- market_data.py
|   +-- forecasts.py
|
+-- adapters/
|
+-- public/
```

---

# 282. Future bounded context - Investment Appraisal

```text
InvestmentProject
    ↓
Projected Cash Flows
    ↓
Discounting
    ↓
NPV / IRR / MIRR / Payback
```

---

# 283. Future bounded context - Cost of Capital

```text
Market Data
    +
Capital Structure
    +
Tax Assumptions
        ↓
Cost of Equity
Cost of Debt
WACC
```

---

# 284. Future bounded context - Valuation

```text
Forecast
    +
Cost of Capital
    +
Terminal Value
        ↓
DCF
        ↓
Enterprise Value
        ↓
Equity Bridge
        ↓
Equity Value
```

---

# 285. Future bounded context - Risk

```text
Valuation Model
    +
Risk Factors
    +
Distributions
        ↓
Sensitivity
Scenario
Monte Carlo
```

---

# 286. Future bounded context - Financing

```text
Current Capital Structure
    +
Financing Alternatives
    +
Market Terms
        ↓
Financing Scenarios
        ↓
Cost / Risk / Dilution
```

---

# 287. Governance rule

Toute future Pull Request proposant :

```text
NPV
IRR
WACC
DCF
Monte Carlo
```

dans `pyaccountingkit` doit référencer ce P2.3 et justifier explicitement une exception.

---

# 288. Exception process

Une exception nécessite :

```text
new ADR

bounded-context impact analysis

public API impact

dependency impact

release impact
```

---

# 289. No convenience creep

Argument interdit :

```text
"NPV is only 10 lines of Python, so put it in analysis."
```

La frontière est sémantique, pas basée sur la taille du code.

---

# 290. No dependency creep

PyAccountingKit ne doit pas finir par nécessiter :

```text
market-data SDKs
optimization libraries
stochastic simulation libraries
portfolio analytics libraries
```

pour fonctionner comme framework comptable.

---

# 291. Numerical dependencies

Corporate Finance peut utiliser des dépendances numériques spécialisées séparément.

---

# 292. SciPy / NumPy boundary

PyAccountingKit peut utiliser des outils numériques si réellement nécessaires à son scope.

Mais l'ajout de NPV/IRR ne doit pas être le prétexte à faire du core un moteur scientifique général.

---

# 293. Pure Decimal preference

Accounting amounts remain Decimal.

---

# 294. Numerical root solving

Corporate Finance peut utiliser float/numerical methods internally pour IRR si son contrat de précision le permet.

Ce choix ne doit pas contaminer `Money` accounting semantics.

---

# 295. Precision boundary

```text
Accounting monetary truth
    -> Decimal exactness

Numerical finance solver
    -> numerical precision policy
```

---

# 296. Risk probability precision

Corporate Finance/Risk policy.

---

# 297. Reconciliation with accounting outputs

A Corporate Finance valuation should be able to reconcile its historical base to :

```text
AnalysisSnapshot
```

---

# 298. `ValuationBridge`

Future object :

```text
ValuationBridge
|
+-- accounting_snapshot_ref
+-- normalization_adjustments
+-- forecast_bridge
+-- valuation_adjustments
+-- result
```

---

# 299. Bridge control

Future control :

```text
VALUATION_BASE_RECONCILED_TO_ACCOUNTING
```

---

# 300. Why important

Prevents valuation models from becoming detached from audited historical facts.

---

# 301. Group valuation input

Can consume :

```text
ConsolidationSnapshot
```

---

# 302. Standalone entity valuation input

Can consume :

```text
AnalysisSnapshot
```

---

# 303. Transaction-specific valuation

May add adjustments outside accounting.

---

# 304. Provenance

Every Corporate Finance input should preserve :

```text
accounting source
forecast source
market source
assumption source
```

---

# 305. Historical source priority

Accounting historical facts remain the baseline of truth.

---

# 306. Forecast is not accounting truth

---

# 307. Market price is not accounting truth

---

# 308. Valuation result is not accounting truth

---

# 309. Decision-support semantics

Corporate Finance outputs are :

```text
decision-support artifacts
```

unless another accounting policy later recognizes a transaction.

---

# 310. Controls - PyAccountingKit boundary

Allowed controls :

```text
ANALYSIS_SOURCE_SNAPSHOT_PRESENT
ANALYSIS_DEFINITION_VERSION_PINNED
ANALYSIS_FORMULA_RECONCILED
HISTORICAL_RATIO_REPRODUCIBLE
```

---

# 311. Controls - future Corporate Finance

```text
FORECAST_SNAPSHOT_PRESENT
MARKET_DATA_SNAPSHOT_PRESENT
DISCOUNT_RATE_TRACEABLE
WACC_COMPONENTS_COMPLETE
TERMINAL_VALUE_POLICY_PRESENT
VALUATION_BASE_RECONCILED
MONTE_CARLO_SEED_PRESENT
SCENARIO_WEIGHTS_VALID
```

---

# 312. Testing - PyAccountingKit

Keep golden cases for :

```text
SIG
EBE
EBITDA
CAF
FRNG
BFR
Treasury
historical ratios
historical diagnostics
```

---

# 313. Testing - future framework

Separate golden/property tests for :

```text
NPV
IRR
MIRR
WACC
DCF
terminal value
sensitivity
Monte Carlo
```

---

# 314. Public documentation

PyAccountingKit README should state :

```text
PyAccountingKit is not a corporate valuation or investment-appraisal engine.
```

---

# 315. Corporate Finance README future

Should state :

```text
Historical accounting facts may be consumed from PyAccountingKit,
but financial projections and valuation assumptions remain distinct artifacts.
```

---

# 316. Release strategy impact

P2.3 adds no runtime capability by itself.

It is :

```text
architecture governance
```

---

# 317. Version impact

Documentation-only boundary :

```text
PATCH / no package release
```

if no public API changes.

---

# 318. Future bridge API

Adding `FinancialFactsProvider` may be :

```text
MINOR
```

if backward compatible.

---

# 319. Future Corporate Finance framework

Independent SemVer.

---

# 320. ADRs

| ID | Décision |
|---|---|
| ADR-AFA-001 | PyAccountingKit reste un framework comptable et d'analyse financière historique, pas un moteur Corporate Finance général |
| ADR-AFA-002 | Les capacités nécessitant hypothèses futures, données de marché ou discounting sortent du core |
| ADR-AFA-003 | SIG, EBE, EBITDA, CAF, FRNG, BFR et trésorerie restent dans Financial Analysis |
| ADR-AFA-004 | Les ratios historiques accounting-based restent dans PyAccountingKit |
| ADR-AFA-005 | Les ratios de marché relèvent du Corporate Finance |
| ADR-AFA-006 | Les tendances historiques restent dans PyAccountingKit, les forecasts sortent du core |
| ADR-AFA-007 | Les diagnostics historiques accounting-based restent dans PyAccountingKit |
| ADR-AFA-008 | Les diagnostics prédictifs/probabilistes nécessitent un framework de Risk/Credit/Corporate Finance |
| ADR-AFA-009 | Le risque de liquidité/leverage historique peut être analysé dans PyAccountingKit |
| ADR-AFA-010 | Market Risk, Project Risk et Valuation Risk restent hors core |
| ADR-AFA-011 | VAN/NPV relève du Corporate Finance |
| ADR-AFA-012 | TRI/IRR et MIRR relèvent du Corporate Finance |
| ADR-AFA-013 | Payback et Profitability Index relèvent de l'Investment Appraisal |
| ADR-AFA-014 | Le calcul du coût des fonds propres relève du Corporate Finance |
| ADR-AFA-015 | CAPM et Beta restent hors PyAccountingKit |
| ADR-AFA-016 | Le coût marginal de la dette relève du Corporate Finance |
| ADR-AFA-017 | Un ratio historique d'intérêt/dette ne doit pas être nommé implicitement `CostOfDebt` |
| ADR-AFA-018 | WACC relève du Corporate Finance |
| ADR-AFA-019 | La structure de capital historique peut être analysée, la structure cible relève du Corporate Finance |
| ADR-AFA-020 | DCF, FCFF/FCFE forecast et Terminal Value restent hors core |
| ADR-AFA-021 | Enterprise Value et Equity Value relèvent du Corporate Finance |
| ADR-AFA-022 | Les multiples de marché relèvent du Corporate Finance |
| ADR-AFA-023 | Sensitivity et Scenario Analysis prospectifs restent hors core |
| ADR-AFA-024 | Monte Carlo reste hors PyAccountingKit |
| ADR-AFA-025 | VaR et Expected Shortfall ne sont pas des capacités core PyAccountingKit |
| ADR-AFA-026 | Les covenant tests historiques peuvent rester, le forecast covenant headroom sort du core |
| ADR-AFA-027 | Les concentrations historiques issues des subledgers peuvent rester dans Financial Analysis |
| ADR-AFA-028 | Les stress simulations de concentration/liquidité sortent du core |
| ADR-AFA-029 | Budgeting et Forecasting ne sont pas des responsabilités du core PyAccountingKit |
| ADR-AFA-030 | Un futur Corporate Finance framework peut consommer un ForecastSnapshot provenant d'un système FP&A |
| ADR-AFA-031 | Les normalisations de valorisation judgmental restent hors accounting analysis historique |
| ADR-AFA-032 | `FinancialFactsSnapshot` est le bridge conceptuel recommandé vers Corporate Finance |
| ADR-AFA-033 | Corporate Finance ne dépend pas des repositories/ORM internes de PyAccountingKit |
| ADR-AFA-034 | Corporate Finance ne modifie jamais les écritures comptables |
| ADR-AFA-035 | Les données de marché restent distinctes des données comptables |
| ADR-AFA-036 | Les assumptions prospectives restent distinctes des accounting facts |
| ADR-AFA-037 | Les résultats de valuation sont des decision-support artifacts, pas des accounting facts |
| ADR-AFA-038 | Accounting fair-value measurement et enterprise valuation sont deux domaines différents |
| ADR-AFA-039 | PyAccountingKit peut consommer un taux externe pour une measurement policy sans devenir propriétaire du WACC |
| ADR-AFA-040 | Discounting comptable et investment discounting doivent rester séparés sémantiquement |
| ADR-AFA-041 | L'historical Net Debt peut rester dans Financial Analysis, les valuation adjustments restent Corporate Finance |
| ADR-AFA-042 | Historical ROIC peut rester, EVA nécessitant WACC sort du core |
| ADR-AFA-043 | Historical DuPont Analysis peut rester, forecast DuPont sort du core |
| ADR-AFA-044 | Accounting effects d'une décision de financement restent dans PyAccountingKit, la décision elle-même reste Corporate Finance |
| ADR-AFA-045 | Aucun SDK de market data ne devient une dépendance obligatoire de PyAccountingKit core |
| ADR-AFA-046 | Les solveurs numériques d'IRR ne doivent pas contaminer les garanties Decimal de Money accounting |
| ADR-AFA-047 | Les futures valuations doivent pouvoir se réconcilier à un snapshot comptable via un ValuationBridge |
| ADR-AFA-048 | Les tests NPV/IRR/WACC/DCF/Monte Carlo appartiennent au futur framework, pas au test contract PyAccountingKit |
| ADR-AFA-049 | Toute proposition d'ajouter Corporate Finance au core doit passer par un nouvel ADR de scope |
| ADR-AFA-050 | La frontière est définie par la sémantique et les inputs requis, pas par la taille du code |

---

# 321. Critères d'acceptation P2.3

```text
[x] frontière Historical vs Forward-Looking définie

[x] scope Financial Analysis conservé défini

[x] VAN / NPV hors core explicite

[x] TRI / IRR / MIRR hors core explicite

[x] Payback / Profitability Index hors core explicites

[x] Cost of Equity hors core explicite

[x] Cost of Debt futur hors core explicite

[x] WACC hors core explicite

[x] Capital Structure Optimization hors core explicite

[x] DCF hors core explicite

[x] FCFF / FCFE forecast hors core explicites

[x] Terminal Value hors core explicite

[x] Enterprise Value / Equity Value hors core explicites

[x] Multiples marché hors core explicites

[x] Sensitivity Analysis hors core explicite

[x] Scenario Analysis prospectif hors core explicite

[x] Monte Carlo hors core explicite

[x] Market Risk hors core explicite

[x] Project Risk hors core explicite

[x] historical accounting risk diagnostics conservés

[x] historical covenant analysis boundary définie

[x] concentration analysis boundary définie

[x] Budget/Forecast boundary définie

[x] accounting fair-value vs enterprise valuation séparés

[x] discounting accounting vs investment discounting séparés

[x] FinancialFactsSnapshot bridge défini

[x] FinancialFactsProvider préparé

[x] MarketDataProvider futur défini

[x] ForecastSnapshot futur défini

[x] AssumptionSet futur défini

[x] future Corporate Finance bounded contexts proposés

[x] complete capability matrix définie

[x] 50 ADR-AFA définis
```

---

# 322. Ordre d'implémentation recommandé

P2.3 est optionnel et ne nécessite pas d'implémentation Corporate Finance immédiate.

Si la frontière doit être matérialisée maintenant :

```text
AFA-00
    Document scope classification

AFA-01
    Add FinancialFactsSnapshot contract

AFA-02
    Add FinancialFactsProvider protocol

AFA-03
    Add historical accounting-risk definitions if required

AFA-04
    Add architecture guard tests preventing Corporate Finance dependencies

AFA-05
    Create separate PyCorporateFinanceKit project when first real use case appears
```

---

# 323. Architecture guard tests

Tests recommandés dans PyAccountingKit :

```text
no module named valuation in core public API

no WACC implementation in analysis domain

no market-data dependency in core dependencies

no stochastic simulation dependency in core

no investment-project aggregate in accounting domain
```

---

# 324. First future Corporate Finance milestone

Lorsque le besoin devient réel, le premier lot du futur framework pourrait être :

```text
0.0.1 - Repository Bootstrap

0.1.0a1 - Time Value of Money

0.1.0a2 - Investment Project + Cash Flows

0.1.0b1 - NPV / IRR / MIRR

0.2.0a1 - Cost of Capital

0.2.0b1 - WACC

0.3.0a1 - DCF Valuation

0.3.0b1 - Sensitivity / Scenario

0.4.0a1 - Monte Carlo Risk
```

Ce roadmap n'est pas engagé par PyAccountingKit ; il sert uniquement à démontrer que les capacités forment un domaine autonome cohérent.

---

# 325. Démonstrateur de frontière - historique

```text
Input:
    ReportSnapshot 2026

Compute:
    EBITDA
    CAF
    Current Ratio
    Net Debt
    ROIC historical

Owner:
    PyAccountingKit
```

---

# 326. Démonstrateur de frontière - investissement

```text
Input:
    Initial investment = 1,000,000
    projected FCF years 1..5
    discount rate = 9.5%

Compute:
    NPV
    IRR

Owner:
    Corporate Finance
```

---

# 327. Démonstrateur de frontière - WACC

```text
Historical accounting inputs:
    debt balances
    interest expenses

Market inputs:
    market cap
    beta
    risk-free rate
    market premium

Compute:
    Cost of Equity
    Cost of Debt
    WACC

Owner:
    Corporate Finance
```

---

# 328. Démonstrateur de frontière - valuation

```text
PyAccountingKit:
    historical EBITDA
    historical cash flow
    historical Net Debt

Forecast source:
    projected revenue/margins/FCF

Market source:
    WACC inputs

Corporate Finance:
    DCF
    terminal value
    Enterprise Value
    Equity Value
```

---

# 329. Démonstrateur de frontière - risque

```text
Historical current ratio deterioration
    -> PyAccountingKit

Probability NPV < 0 under Monte Carlo
    -> Corporate Finance / Risk
```

---

# 330. Démonstrateur - accounting measurement

```text
Accounting policy requires present-value measurement
    -> PyAccountingKit MeasurementPolicy may consume external discount input

Management asks what the business is worth under DCF
    -> Corporate Finance
```

---

# 331. Matrice décisionnelle finale

| Question | Owner |
|---|---|
| Que s'est-il passé comptablement ? | PyAccountingKit |
| Quelle est la situation financière historique ? | PyAccountingKit |
| Quels ratios historiques en dérivent ? | PyAccountingKit |
| Quelle tendance historique est observable ? | PyAccountingKit |
| Quel est le risque de liquidité observé ? | PyAccountingKit |
| Quels seront les cash-flows futurs ? | Planning / Forecast |
| Faut-il investir ? | Corporate Finance |
| Quelle est la VAN ? | Corporate Finance |
| Quel est le TRI ? | Corporate Finance |
| Quel est le coût du capital ? | Corporate Finance |
| Quelle structure de financement cibler ? | Corporate Finance |
| Combien vaut l'entreprise ? | Corporate Finance |
| Comment la valorisation varie-t-elle avec WACC/g ? | Corporate Finance |
| Quelle est la distribution probabiliste de la VAN ? | Corporate Finance / Risk |

---

# 332. Impact sur `14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md`

Le P2.3 **confirme** et précise la frontière déjà introduite dans le P1.3.

Il ne remet pas en cause :

```text
ADR-ANA-033
    Corporate Finance hors du core

ADR-ANA-034
    NPV / IRR / WACC / valuation hors du bounded context Financial Analysis
```

Il les développe en un contrat détaillé.

---

# 333. Impact sur `16_PYACCOUNTINGKIT_PUBLIC_API_DESIGN.md`

Aucune nouvelle façade Corporate Finance ne doit apparaître sous :

```text
AccountingApplication
```

La future application aurait sa propre façade :

```text
CorporateFinanceApplication
```

---

# 334. Impact sur `17_RELEASE_AND_VERSIONING_STRATEGY`

Le futur Corporate Finance framework possède :

```text
independent package version

independent public API contract

independent adapter contracts
```

---

# 335. Impact sur `20_ADR_REGISTER`

Les `ADR-AFA-*` devront être ajoutés au prochain rafraîchissement du registre ADR consolidé, ainsi que les namespaces `CON` et `REC` créés après sa baseline initiale.

---

# 336. Conclusion

Le P2.3 ferme explicitement la frontière fonctionnelle de PyAccountingKit.

```text
PyAccountingKit
    = accounting truth
    + reporting
    + historical financial analysis
    + accounting-based diagnostics

Corporate Finance
    = future assumptions
    + investment decisions
    + discounting
    + cost of capital
    + financing
    + valuation
    + scenario/sensitivity
    + stochastic risk
```

Les décisions finales sont :

```text
VAN / NPV                  -> Corporate Finance

TRI / IRR / MIRR           -> Corporate Finance

WACC                       -> Corporate Finance

Cost of Equity / Debt      -> Corporate Finance

Target Capital Structure   -> Corporate Finance

DCF / FCFF / FCFE forecast -> Corporate Finance

Enterprise / Equity Value  -> Corporate Finance

Market Multiples           -> Corporate Finance

Sensitivity                -> Corporate Finance

Scenario Valuation         -> Corporate Finance

Monte Carlo                -> Corporate Finance / Risk

Market / Project Risk      -> Outside PyAccountingKit core

Historical ratios          -> PyAccountingKit

Historical liquidity risk  -> PyAccountingKit

Historical leverage risk   -> PyAccountingKit

Historical concentration   -> PyAccountingKit

Accounting fair-value      -> PyAccountingKit Measurement when policy requires it
```

La frontière fondamentale est donc :

```text
Accounting facts and historical interpretation
    stay in PyAccountingKit.

Forward-looking financial decisions and valuation
    belong to a dedicated Corporate Finance framework.
```

---

**P2.3 clôt la roadmap architecturale optionnelle définie jusqu'au document 23.**


---

## Sources et références documentaires du projet

- 📗 [Maxi fiches de Gestion financière de l'entreprise](../../books/Maxi_fiches_de_Gestion_financiere_de_l_entreprise.md)

---

## Couverture dans les plans d'implémentation

Ce document est couvert par les plans suivants :

- [PLAN-09 — Corporate Finance Boundaries](../../plans/PLAN-09_CORPORATE_FINANCE_BOUNDARIES.md)
