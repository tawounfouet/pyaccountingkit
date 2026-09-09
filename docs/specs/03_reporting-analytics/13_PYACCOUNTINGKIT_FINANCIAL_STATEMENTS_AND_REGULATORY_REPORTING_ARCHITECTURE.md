# 13 - PyAccountingKit - Architecture des états financiers et du reporting réglementaire

> **Projet** : PyAccountingKit  
> **Document** : `13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md`  
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
> **Statut** : P1.2 - Architecture des états financiers et du reporting réglementaire  
> **Langue** : Français  
> **Objet** : Définir le moteur d'états financiers, les définitions de lignes, les mappings compte -> état, les sources Trial Balance, les variantes de présentation, les snapshots immuables, le reporting réglementaire multi-référentiels, les exports, les contrôles de cohérence, le drill-down et les contrats d'intégration avec `regulatory-accounting-data-framework`.

---

# 1. Résumé exécutif

Le moteur de reporting de PyAccountingKit ne doit jamais considérer :

```text
Financial Statement
```

comme une seconde source comptable.

La source reste :

```text
JournalEntry / JournalEntryLine
    ->
Ledger
    ->
Trial Balance
```

Les états financiers sont des **projections versionnées** :

```text
Trial Balance
    |
    v
Statement Mapping
    |
    v
Statement Definition
    |
    v
Statement Lines
    |
    v
Financial Statement
    |
    v
Report Snapshot
```

Le reporting réglementaire ajoute :

```text
Reference Reporting Model

Regulatory Profile

Regulatory Mapping

Validation Rules

Export Definition
```

Architecture cible :

```text
POSTED ACCOUNTING DATA
        |
        v
TRIAL BALANCE / SNAPSHOT
        |
        v
STATEMENT ENGINE
        |
        +--> Balance Sheet
        +--> Income Statement
        +--> Cash Flow Statement
        +--> Other Statements
        |
        v
REPORT SNAPSHOT
        |
        +--> Financial Analysis
        |
        +--> Regulatory Reporting
                |
                +--> Regulatory Validation
                +--> Export Artifact
```

Le principe central est :

```text
CompanyAccount
    !=
StatementLine

StatementLine
    !=
ReferenceReportingNode

StatementDefinition
    !=
RegulatoryExportFormat

Mapping
    !=
Accounting Source of Truth
```

---

# 2. Sources et hiérarchie d'autorité

Le moteur s'appuie sur quatre familles de sources, avec des rôles distincts :

```text
1. regulatory-accounting-data-framework
       = source de vérité réglementaire versionnée

2. cfa_fra_django_mvp_sprint_7
       = référence fonctionnelle exécutable

3. doctrine comptable
       = principes, terminologie, mécanismes

4. PyAccountingKit
       = moteur générique et portable
```

---

# 3. Source réglementaire

Le `regulatory-accounting-data-framework` fournit notamment :

```text
reporting datasets

statement structures

relations

reference ids

candidate account hints

human validation flags

effective plans
```

PyAccountingKit consomme ces artefacts par :

```text
AccountingReferenceProvider
```

---

# 4. Règle critique : structure officielle != mapping exécutable

Un dataset de reporting peut contenir :

```text
official statement structure

+

candidate account hints
```

Ces deux dimensions doivent rester séparées.

Exemple conceptuel :

```text
Statement line:
    official

Account hint:
    derived candidate
    human_validation_required = true
    account_hints_executable = false
```

---

# 5. Conséquence

Interdit :

```text
candidate hint
    ->
automatic statement mapping
```

sans validation explicite.

---

# 6. Source fonctionnelle CFA FRA

CFA FRA fournit déjà un `Financial Statement Engine` conceptuel :

```text
posted lines

-> ledger / adjusted balance

-> account-to-statement mapping

-> definitions

-> financial statements

-> ratios

-> drill-down
```

PyAccountingKit reprend cette séparation.

---

# 7. Objectifs

Le bounded context doit permettre de :

1. construire des états financiers à partir d'une balance ;
2. définir des structures d'état versionnées ;
3. mapper les comptes entreprise vers les lignes d'état ;
4. supporter des mappings multiples par référentiel ;
5. supporter plusieurs variantes de présentation ;
6. produire bilan, compte de résultat, cash-flow et autres états ;
7. gérer les totaux et sous-totaux ;
8. gérer les formules de lignes ;
9. gérer les lignes calculées ;
10. gérer les comparatifs N / N-1 ;
11. gérer les périodes intermédiaires ;
12. produire des snapshots immuables ;
13. permettre le drill-down vers la balance / ledger / entry ;
14. valider l'équation de bilan ;
15. valider les réconciliations de cash-flow ;
16. produire des exports réglementaires ;
17. figer mapping / définition / référence / source dans l'export ;
18. préserver la provenance des mappings ;
19. refuser les mappings ambiguës ou non exécutables ;
20. permettre un reporting multi-référentiels.

---

# 8. Non-objectifs

Ce document ne couvre pas :

```text
les ratios financiers détaillés

SIG / CAF / FRNG / BFR

scoring

NPV / IRR / cost of capital

consolidation de groupe

XBRL complet

taxonomies réglementaires externes non présentes dans le provider
```

Le prochain document `14` couvrira l'analyse financière.

---

# 9. Bounded contexts impliqués

```text
Ledger & Balances

Financial Statements

Regulatory Reporting

Accounting Reference Data

Company Chart of Accounts

Controls

Audit & Traceability

Financial Analysis
```

---

# 10. Separation Financial Statements / Regulatory Reporting

```text
Financial Statements
    = moteur générique de projection et présentation

Regulatory Reporting
    = application d'un profil réglementaire versionné
      sur les projections
```

---

# 11. Pourquoi séparer

Une organisation peut produire :

```text
internal management statements

statutory statements

regulatory filings

analytical statements
```

depuis la même source comptable.

---

# 12. Canonical reporting source

Par défaut :

```text
TrialBalance
```

ou :

```text
TrialBalanceSnapshot
```

---

# 13. `ReportingSource`

```text
ReportingSource
|
+-- source_type
+-- source_ref
+-- scope
+-- variant
+-- as_of
+-- watermark?
+-- checksum?
```

---

# 14. `ReportingSourceType`

```text
TRIAL_BALANCE

TRIAL_BALANCE_SNAPSHOT

LEDGER_QUERY

CUSTOM_PROJECTION
```

P0/P1 recommandé :

```text
TRIAL_BALANCE_SNAPSHOT
```

pour publication.

---

# 15. Pourquoi snapshot pour publication

Un report publié doit être :

```text
stable

reproducible

auditable
```

---

# 16. `FinancialStatementDefinition`

Aggregate Root / définition versionnée :

```text
FinancialStatementDefinition
|
+-- id
+-- code
+-- statement_type
+-- version
+-- standard_scope?
+-- reporting_profile?
+-- effective_from
+-- effective_to?
+-- lines
+-- presentation_rules
+-- metadata
```

---

# 17. `FinancialStatementType`

```text
BALANCE_SHEET

INCOME_STATEMENT

CASH_FLOW_STATEMENT

CHANGES_IN_EQUITY

NOTES_INDEX

CUSTOM
```

---

# 18. P1 minimal

```text
BALANCE_SHEET

INCOME_STATEMENT

CASH_FLOW_STATEMENT
```

---

# 19. `StatementLineDefinition`

```text
StatementLineDefinition
|
+-- line_id
+-- code
+-- label
+-- line_type
+-- parent_line_id?
+-- order
+-- sign_convention
+-- aggregation_rule
+-- formula?
+-- visibility
+-- drilldown_policy
+-- metadata
```

---

# 20. `StatementLineType`

```text
DETAIL

SUBTOTAL

TOTAL

FORMULA

HEADER

SPACER

MEMO

DISCLOSURE
```

---

# 21. Header / Spacer

Ces lignes sont de présentation.

Elles n'ont pas de valeur comptable propre.

---

# 22. Detail

Une ligne detail reçoit :

```text
mapped balances
```

---

# 23. Subtotal

Agrège :

```text
child statement lines
```

---

# 24. Formula

Calcule :

```text
expression over other statement lines
```

---

# 25. `StatementFormula`

```text
StatementFormula
|
+-- expression
+-- dependencies
+-- rounding_policy?
+-- version
```

---

# 26. Pas de `eval()` arbitraire

Interdit :

```python
eval(formula)
```

avec contenu non fiable.

---

# 27. DSL limitée

Opérations initiales :

```text
ADD

SUBTRACT

SUM

NEGATE

ABS

MIN

MAX
```

---

# 28. Formules déterministes

Pas d'appel externe dans une formule d'état.

---

# 29. `StatementSignConvention`

```text
NATURAL

DEBIT_POSITIVE

CREDIT_POSITIVE

ABSOLUTE

CUSTOM
```

---

# 30. Sign convention != normal balance

La présentation d'une ligne d'état peut inverser le signe sans modifier :

```text
ledger signed balance
```

---

# 31. Mapping compte -> ligne d'état

Objet central :

```text
StatementAccountMapping
```

---

# 32. `StatementAccountMapping`

```text
StatementAccountMapping
|
+-- id
+-- mapping_set_id
+-- company_account_id
+-- statement_line_id
+-- allocation
+-- sign_rule?
+-- effective_from
+-- effective_to?
+-- mapping_status
+-- provenance
```

---

# 33. Distinction importante

```text
CompanyAccount
    ->
ReferenceAccount
```

est un mapping réglementaire de compte.

```text
CompanyAccount
    ->
StatementLine
```

est un mapping de présentation.

---

# 34. Ils ne sont pas interchangeables

Un même compte peut :

```text
avoir un binding réglementaire
```

mais :

```text
être présenté différemment
```

selon le report.

---

# 35. `StatementMappingSet`

Aggregate Root :

```text
StatementMappingSet
|
+-- id
+-- accounting_entity_id
+-- statement_definition_id
+-- version
+-- status
+-- mappings
+-- effective_from
+-- effective_to?
+-- provenance
+-- checksum
```

---

# 36. Statuts

```text
DRAFT

REVIEW_REQUIRED

VALIDATED

ACTIVE

SUPERSEDED

ARCHIVED
```

---

# 37. Seul ACTIVE / VALIDATED est exécutable

Selon policy.

---

# 38. Mapping one-to-one

```text
CompanyAccount A
    ->
StatementLine X
```

---

# 39. Mapping many-to-one

```text
Account A
Account B
Account C
    ->
StatementLine X
```

---

# 40. Mapping one-to-many

Possible si :

```text
allocation
```

explicite.

---

# 41. `MappingAllocation`

```text
MappingAllocation
|
+-- ratio
+-- amount_rule?
+-- condition?
```

---

# 42. Ratio

Utilise :

```text
Decimal
```

---

# 43. Mapping total allocation

Si one-to-many :

```text
sum(allocation ratios) == 1
```

sauf policy spéciale.

---

# 44. Allocation conditionnelle

P1/P2.

Exemple :

```text
debit balance -> Asset line

credit balance -> Liability line
```

---

# 45. `BalanceSideMappingRule`

```text
DEBIT_SIDE

CREDIT_SIDE

SIGNED_CONDITION
```

---

# 46. Utilité

Certains comptes peuvent changer de présentation selon leur solde.

---

# 47. Règle explicite

Ne jamais coder :

```text
if account code starts with ...
```

pour déterminer la présentation universelle.

---

# 48. `StatementMappingStatus`

```text
CANDIDATE

REVIEW_REQUIRED

VALIDATED

REJECTED

SUPERSEDED
```

---

# 49. Candidate hints

Les hints réglementaires entrent comme :

```text
CANDIDATE
```

---

# 50. `MappingProvenance`

```text
MANUAL

REFERENCE_HINT

RULE_BASED

MIGRATION

IMPORTED

VALIDATED_CANDIDATE
```

---

# 51. Hints non exécutables

Si source indique :

```text
human_validation_required = true
```

alors :

```text
mapping_status != VALIDATED
```

par défaut.

---

# 52. `StatementMappingCandidate`

```text
StatementMappingCandidate
|
+-- company_account_id?
+-- reference_account_id?
+-- statement_line_id
+-- source_hint
+-- confidence?
+-- rationale
+-- review_required
```

---

# 53. Mapping par référence

Un mapping peut être dérivé de :

```text
CompanyAccount
    ->
ReferenceAccount
    ->
validated regulatory mapping
```

si le provider expose un mapping exécutable.

---

# 54. Fail-closed

Si le provider expose seulement :

```text
candidate account hints
```

aucun mapping automatique actif.

---

# 55. `ReportingModel`

Provenant du provider :

```text
ReferenceReportingModel
```

---

# 56. `ReferenceReportingModel`

```text
ReferenceReportingModel
|
+-- standard_id
+-- edition
+-- reporting_model_id
+-- version
+-- statements
+-- nodes
+-- provenance
+-- executable_capabilities
```

---

# 57. `ReportingNode`

```text
ReportingNode
|
+-- node_id
+-- node_type
+-- code
+-- label
+-- parent_node_id?
+-- order
+-- attributes
+-- provenance
```

---

# 58. Provider contract

```python
class AccountingReferenceProvider(Protocol):
    def get_reporting_model(
        self,
        standard_id: str,
        edition: str,
        reporting_model_id: str | None = None,
    ) -> "ReferenceReportingModel":
        ...
```

---

# 59. Aucun hardcode de taxonomy

Interdit :

```python
BALANCE_SHEET_LINES = [...]
```

pour un référentiel officiel.

---

# 60. Moteur de reporting

```text
FinancialStatementEngine
```

---

# 61. `FinancialStatementEngine`

```python
class FinancialStatementEngine:
    def build(
        self,
        request: "FinancialStatementBuildRequest",
    ) -> "FinancialStatementResult":
        ...
```

---

# 62. `FinancialStatementBuildRequest`

```text
FinancialStatementBuildRequest
|
+-- accounting_entity_id
+-- reporting_source
+-- statement_definition
+-- mapping_set
+-- comparison_sources?
+-- presentation_context
+-- as_of
```

---

# 63. Build algorithm

```text
1. validate source freshness

2. validate definition

3. validate mapping set

4. load trial balance rows

5. apply account mappings

6. aggregate detail lines

7. evaluate formulas/subtotals

8. apply sign conventions

9. apply rounding

10. run statement controls

11. build drill-down refs

12. produce result
```

---

# 64. `FinancialStatementResult`

```text
FinancialStatementResult
|
+-- statement_type
+-- definition_version
+-- mapping_set_version
+-- source_ref
+-- lines
+-- controls
+-- generated_at
+-- checksum
```

---

# 65. `FinancialStatementLine`

```text
FinancialStatementLine
|
+-- line_id
+-- code
+-- label
+-- value
+-- comparison_values
+-- source_refs
+-- drilldown_refs
+-- metadata
```

---

# 66. Missing mapping

Un compte avec solde significatif sans mapping peut produire :

```text
UNMAPPED_STATEMENT_ACCOUNT
```

---

# 67. Policy

Selon type d'état :

```text
blocking

warning

ignore
```

---

# 68. P1 recommandé

Pour un état réglementaire :

```text
blocking
```

---

# 69. Mapping completeness

```text
mapped relevant balance
/
total relevant balance
```

---

# 70. Coverage != correctness

100 % coverage peut être faux sémantiquement.

---

# 71. `StatementMappingCoverage`

```text
account_count_coverage

balance_amount_coverage

unmapped_accounts

unmapped_amount
```

---

# 72. Line value

Un detail line :

```text
sum(mapped account values)
```

avec sign/allocations.

---

# 73. Source balance selection

Chaque mapping doit préciser :

```text
closing balance

movement debit

movement credit

net movement

opening balance
```

si nécessaire.

---

# 74. `BalanceMeasure`

```text
CLOSING_BALANCE

OPENING_BALANCE

DEBIT_MOVEMENT

CREDIT_MOVEMENT

NET_MOVEMENT
```

---

# 75. Income Statement

Typiquement basé sur :

```text
period movements
```

---

# 76. Balance Sheet

Typiquement basé sur :

```text
closing balances
```

---

# 77. Cash Flow

Peut nécessiter :

```text
movement classification

opening/closing cash

indirect adjustments

direct cash mappings
```

---

# 78. Cash flow architecture

Le cash-flow ne doit pas être un énorme `if/else`.

---

# 79. `CashFlowDefinition`

```text
CashFlowDefinition
|
+-- method
+-- sections
+-- lines
+-- mappings
+-- reconciliation_formula
+-- version
```

---

# 80. `CashFlowMethod`

```text
DIRECT

INDIRECT

CUSTOM
```

---

# 81. P1

Support minimal :

```text
INDIRECT
```

ou méthode configurée par définition.

---

# 82. Cash flow source

Peut consommer :

```text
Trial Balance

Statement results

specific movement mappings
```

---

# 83. Cash flow reconciliation

Contrôle :

```text
Opening Cash
+
CFO
+
CFI
+
CFF
=
Closing Cash
```

---

# 84. `CASHFLOW_RECONCILED`

Control existant.

---

# 85. Balance sheet equation

Contrôle conceptuel :

```text
Assets
=
Liabilities
+
Equity
```

---

# 86. `BALANCE_SHEET_BALANCED`

Doit être calculé à partir de :

```text
statement definition
```

et non de codes hardcodés.

---

# 87. Income statement equation

Peut contrôler :

```text
revenues
-
expenses
=
net result
```

selon la définition.

---

# 88. `INCOME_STATEMENT_RECONCILED`

Control possible.

---

# 89. Change in equity

P1/P2.

Peut être modélisé par :

```text
StatementDefinition
```

avec roll-forward.

---

# 90. `StatementControlDefinition`

```text
StatementControlDefinition
|
+-- control_code
+-- statement_type
+-- formula
+-- tolerance
+-- blocking
+-- version
```

---

# 91. Tolérance

Utiliser :

```text
Decimal
```

---

# 92. Rounding

La présentation peut arrondir.

---

# 93. `ReportingRoundingPolicy`

```text
NONE

CURRENCY_SCALE

UNITS

THOUSANDS

MILLIONS

CUSTOM
```

---

# 94. Calcul vs présentation

Toujours calculer avec :

```text
full Decimal precision
```

puis arrondir pour affichage/export.

---

# 95. Contrôles sur valeurs arrondies

Peuvent nécessiter :

```text
display tolerance
```

distincte du contrôle comptable exact.

---

# 96. Comparatifs

Le moteur doit supporter :

```text
current period

prior period

prior year

budget/forecast future extension
```

---

# 97. `ComparisonColumnDefinition`

```text
ComparisonColumnDefinition
|
+-- code
+-- source
+-- label
+-- order
+-- display_rule
```

---

# 98. Exemple

```text
N

N-1
```

---

# 99. Source N-1

Peut avoir :

```text
different chart version

different mapping set version
```

---

# 100. Reclassification comparatives

P1/P2.

Si mapping change :

```text
reported comparatives
```

peuvent nécessiter un mapping historique ou restatement.

---

# 101. `ComparativeRestatementPolicy`

```text
AS_REPORTED

RESTATED

BOTH
```

---

# 102. P1 recommandé

Support :

```text
AS_REPORTED
```

plus extension prévue.

---

# 103. Statement hierarchy

La hiérarchie est explicitement définie.

---

# 104. Pas de parent inféré par code

Même principe que COA.

---

# 105. Sorting

```text
order
```

explicite.

---

# 106. Duplicate order

Doit être déterministe.

---

# 107. `StatementLineOrder`

Peut être entier ou clé ordonnée.

---

# 108. Visibility

```text
ALWAYS

NON_ZERO_ONLY

MATERIAL_ONLY

NEVER

CONTEXTUAL
```

---

# 109. Zero lines

Peuvent être cachées en présentation.

---

# 110. Mais snapshot peut conserver la ligne

Différencier :

```text
calculation result

rendered result
```

---

# 111. `StatementCalculationResult`

Contient toutes les lignes calculées.

---

# 112. `StatementRenderedView`

Applique :

```text
visibility

labels

localization

formatting
```

---

# 113. Financial statement result vs view

```text
Result
    = semantic data

View
    = presentation
```

---

# 114. Localization

Les labels réglementaires peuvent venir du provider.

L'application peut ajouter :

```text
localized labels
```

---

# 115. No translation as key

Les IDs restent stables.

---

# 116. Drill-down

Chaque ligne doit pouvoir exposer :

```text
source account rows

trial balance rows

ledger movements

JournalEntry

JournalEntryLine
```

---

# 117. `StatementDrilldownQuery`

```python
class StatementDrilldownQuery(Protocol):
    def drilldown(
        self,
        report_snapshot_id,
        statement_line_id,
    ) -> "StatementDrilldownResult":
        ...
```

---

# 118. `StatementDrilldownResult`

```text
statement line

mapped accounts

trial balance contributions

ledger refs

entry refs
```

---

# 119. Snapshot

Publication produit :

```text
ReportSnapshot
```

---

# 120. `ReportSnapshot`

```text
ReportSnapshot
|
+-- id
+-- accounting_entity_id
+-- reporting_profile_id?
+-- report_type
+-- source_snapshot_ref
+-- statement_definition_version
+-- mapping_set_version
+-- reference_snapshot_id?
+-- generated_at
+-- generated_by?
+-- values
+-- control_run_refs
+-- checksum
+-- status
+-- supersedes?
+-- metadata
```

---

# 121. Snapshot immutable

Une fois finalisé :

```text
no update
```

---

# 122. `ReportSnapshotStatus`

```text
DRAFT

VALIDATED

PUBLISHED

SUPERSEDED

WITHDRAWN
```

---

# 123. DRAFT snapshot

Peut être recalculé / remplacé avant validation selon implementation.

---

# 124. VALIDATED

Mapping + controls pass.

---

# 125. PUBLISHED

Artefact officiellement publié.

---

# 126. SUPERSEDED

Remplacé par nouveau snapshot.

---

# 127. WITHDRAWN

Retiré sans suppression historique.

---

# 128. Reopen impact

Une réouverture de période peut marquer :

```text
ReportSnapshot
```

comme :

```text
STALE / SUPERSEDED
```

via relation d'impact, mais ne le supprime jamais.

---

# 129. `ReportSnapshotFreshness`

```text
CURRENT

STALE

SUPERSEDED
```

---

# 130. Rebuild

Un report non publié peut être recalculé.

Un report publié produit :

```text
new snapshot
```

---

# 131. `ReportSnapshotChecksum`

SHA-256 de la représentation canonique.

---

# 132. Canonical payload

Doit exclure :

```text
volatile timestamps
```

si l'objectif est de comparer les valeurs.

---

# 133. `ReportReproducibilityEnvelope`

```text
ReportReproducibilityEnvelope
|
+-- runtime_version
+-- source_snapshot_ref
+-- statement_definition_version
+-- mapping_set_version
+-- reference_snapshot_id?
+-- reporting_profile_version?
+-- control_definition_versions
+-- checksum
```

---

# 134. Regulatory Reporting

Le bounded context ajoute :

```text
RegulatoryReportingProfile
```

---

# 135. `RegulatoryReportingProfile`

Aggregate Root :

```text
RegulatoryReportingProfile
|
+-- id
+-- accounting_entity_id
+-- standard_id
+-- edition
+-- reporting_model_id
+-- profile_version
+-- effective_from
+-- effective_to?
+-- statement_definitions
+-- mapping_sets
+-- export_definitions
+-- control_sets
+-- reference_snapshot
+-- status
```

---

# 136. Status

```text
DRAFT

REVIEW_REQUIRED

ACTIVE

SUPERSEDED

ARCHIVED
```

---

# 137. Activation gate

Avant ACTIVE :

```text
reference snapshot valid

statement definitions valid

mapping sets validated

blocking human-review flags resolved

controls qualified
```

---

# 138. `REGULATORY_PROFILE_ACTIVATION_GATE`

Control Gate.

---

# 139. Multi-standard

Une entité peut avoir :

```text
Primary statutory profile

Secondary reporting profile

Management profile
```

---

# 140. Exemple

```text
fr-pcg:2026

+

fr-nonprofit:2026

+

custom management report
```

selon contexte.

---

# 141. `ReportingPurpose`

```text
STATUTORY

REGULATORY

MANAGEMENT

ANALYTICAL

CONSOLIDATION

CUSTOM
```

---

# 142. Reference snapshot pin

Tout profil réglementaire actif doit pinner :

```text
AccountingReferenceSnapshot
```

---

# 143. Reporting model upgrade

Nouveau dataset :

```text
ReferenceSnapshot R2
```

ne modifie pas le profil actif silencieusement.

---

# 144. Upgrade flow

```text
R1 profile
    |
    v
impact analysis
    |
    v
new profile version
    |
    v
mapping review
    |
    v
qualification
    |
    v
activation
```

---

# 145. `RegulatoryReportingUpgradePlan`

```text
RegulatoryReportingUpgradePlan
|
+-- source_profile
+-- target_reference_snapshot
+-- changed_nodes
+-- mapping_impacts
+-- control_impacts
+-- export_impacts
+-- required_reviews
```

---

# 146. Mapping migration

Une nouvelle structure de reporting peut :

```text
add line

remove line

rename line

split line

merge line
```

---

# 147. Split / Merge

Doivent être traités explicitement.

---

# 148. Pas de migration automatique sémantique

Un code de ligne identique ne suffit pas à conclure :

```text
same meaning
```

---

# 149. `ReportingCrosswalk`

Si provider expose un crosswalk :

```text
validated mappings only
```

peuvent être exécutés automatiquement.

---

# 150. Human review flags

Toujours respectés.

---

# 151. Regulatory export

Un export est produit à partir d'un :

```text
ReportSnapshot
```

---

# 152. Pas directement depuis ledger live

Pour publication réglementaire :

```text
snapshot first
```

---

# 153. `RegulatoryExportDefinition`

```text
RegulatoryExportDefinition
|
+-- id
+-- format
+-- schema_version
+-- file_naming_rule
+-- field_mappings
+-- validation_rules
+-- encoding
+-- metadata
```

---

# 154. Export formats

```text
CSV

JSON

XML

XLSX

PDF presentation

CUSTOM
```

---

# 155. XBRL future

Prévoir :

```text
XBRL
```

mais ne pas l'implémenter implicitement sans taxonomy réelle.

---

# 156. `RegulatoryExportRequest`

```text
RegulatoryExportRequest
|
+-- report_snapshot_id
+-- export_definition_id
+-- requested_by
+-- destination?
```

---

# 157. `RegulatoryExportArtifact`

```text
RegulatoryExportArtifact
|
+-- id
+-- report_snapshot_id
+-- export_definition_version
+-- artifact_ref
+-- checksum
+-- generated_at
+-- generated_by
+-- validation_results
+-- status
```

---

# 158. Export status

```text
GENERATED

VALIDATED

PUBLISHED

FAILED

SUPERSEDED
```

---

# 159. Export checksum

SHA-256.

---

# 160. Export audit

```text
REGULATORY_EXPORT_CREATE

REGULATORY_EXPORT_VALIDATE

REGULATORY_EXPORT_PUBLISH
```

---

# 161. Export evidence bundle

```text
RegulatoryExportEvidenceBundle
|
+-- report_snapshot
+-- reference_snapshot
+-- profile_version
+-- mapping_set_version
+-- control_runs
+-- export_definition_version
+-- artifact_checksum
+-- audit_refs
```

---

# 162. Validation pré-export

Control set :

```text
REGULATORY_REPORT_PRE_EXPORT
```

---

# 163. Contrôles P1

```text
TRIAL_BALANCE_BALANCED

STATEMENT_MAPPING_COMPLETE

BALANCE_SHEET_BALANCED

CASHFLOW_RECONCILED

REQUIRED_STATEMENT_LINE_PRESENT

REFERENCE_SNAPSHOT_PINNED

REPORT_SNAPSHOT_CURRENT

EXPORT_CHECKSUM_PRESENT
```

---

# 164. Mapping completeness control

```text
STATEMENT_MAPPING_COMPLETE
```

---

# 165. Unknown statement line

```text
STATEMENT_LINE_UNSUPPORTED
```

---

# 166. Missing required line

```text
REQUIRED_STATEMENT_LINE_PRESENT
```

---

# 167. Candidate mapping unresolved

```text
UNRESOLVED_REPORTING_MAPPING_CANDIDATE
```

---

# 168. `REGULATORY_EXPORT_GATE`

Bloque publication si :

```text
blocking controls fail
```

---

# 169. Internal financial statements

Peuvent utiliser un gate plus souple.

---

# 170. Statement Engine vs Report Renderer

Séparer :

```text
calculation
```

de :

```text
rendering
```

---

# 171. `ReportRenderer`

Port :

```python
class ReportRenderer(Protocol):
    def render(
        self,
        snapshot: ReportSnapshot,
        definition: "RenderDefinition",
    ) -> "RenderedArtifact":
        ...
```

---

# 172. Renderers possibles

```text
HTML

PDF

XLSX

CSV

JSON
```

---

# 173. Renderer != Regulatory Exporter

Un renderer de présentation :

```text
PDF management report
```

n'a pas la même responsabilité qu'un :

```text
regulatory XML export
```

---

# 174. `RegulatoryExporter`

Port séparé.

---

# 175. `RegulatoryExporter`

```python
class RegulatoryExporter(Protocol):
    def export(
        self,
        snapshot: ReportSnapshot,
        definition: RegulatoryExportDefinition,
    ) -> RegulatoryExportArtifact:
        ...
```

---

# 176. Statement query API

```text
build

preview

snapshot

drilldown

compare
```

---

# 177. Public API - build

```python
result = accounting.statements.build(
    entity_id=entity_id,
    statement="balance_sheet",
    source=trial_balance_snapshot,
    mapping_set=mapping_set,
)
```

---

# 178. Public API - snapshot

```python
snapshot = accounting.statements.snapshot(
    result=result,
)
```

---

# 179. Public API - drilldown

```python
details = accounting.statements.drilldown(
    snapshot_id=snapshot.id,
    line_id=line_id,
)
```

---

# 180. Public API - regulatory profile

```python
profile = accounting.reporting.activate_profile(
    entity_id=entity_id,
    standard_id="fr-pcg",
    edition="2026",
    reference_snapshot=reference_snapshot,
)
```

---

# 181. Public API - regulatory report

```python
snapshot = accounting.reporting.build_report(
    profile_id=profile.id,
    source=trial_balance_snapshot,
)
```

---

# 182. Public API - export

```python
artifact = accounting.reporting.export(
    snapshot_id=snapshot.id,
    export_definition="statutory-json-v1",
)
```

---

# 183. Read-only nature

Le reporting :

```text
never modifies JournalEntry
```

---

# 184. No back-propagation

Interdit :

```text
statement line changed
    ->
rewrite accounting entries
```

---

# 185. Reporting adjustments

Si besoin d'ajustements de présentation :

```text
ReportingAdjustment
```

doit être séparé du ledger statutaire.

---

# 186. `ReportingAdjustment`

P1/P2 concept :

```text
ReportingAdjustment
|
+-- id
+-- report_scope
+-- target_line
+-- amount
+-- reason
+-- source
+-- approval
```

---

# 187. Warning

Ces adjustments ne doivent pas être confondus avec :

```text
JournalEntry adjustments
```

---

# 188. Statutory report

Par défaut :

```text
should not use ad hoc reporting adjustments
```

sauf profil explicite.

---

# 189. Consolidation

Future consolidation may use:

```text
reporting adjustments
```

in a separate context.

---

# 190. Statement source variants

```text
BEFORE_ADJUSTMENTS

ADJUSTED

POST_CLOSING
```

---

# 191. Income Statement source

Typically:

```text
ADJUSTED
```

before annual temporary accounts are closed.

---

# 192. Balance Sheet source

May be:

```text
ADJUSTED
```

or a definition-specific snapshot.

---

# 193. Post-closing

Useful for:

```text
opening balances

certain controls
```

---

# 194. Important

The exact source variant is:

```text
StatementSourcePolicy
```

not universal.

---

# 195. `StatementSourcePolicy`

```text
StatementSourcePolicy
|
+-- statement_type
+-- required_trial_balance_variant
+-- source_date_rule
+-- comparison_rule
+-- applicability
```

---

# 196. Closing integration

Closing can produce:

```text
Adjusted TrialBalanceSnapshot
PostClosing TrialBalanceSnapshot
```

---

# 197. Report freshness

A report snapshot stores:

```text
source close revision
```

if relevant.

---

# 198. Reopen

If close revision changes:

```text
report may become stale
```

---

# 199. `SourceCloseRevision`

Stored in reproducibility envelope.

---

# 200. Periodic statements

Support:

```text
monthly

quarterly

annual

custom period
```

---

# 201. YTD

A statement can be:

```text
period movement

year-to-date

as-of date
```

---

# 202. `StatementPeriodMode`

```text
PERIOD

YEAR_TO_DATE

AS_OF

ROLLING

CUSTOM
```

---

# 203. P1

Support:

```text
PERIOD

YEAR_TO_DATE

AS_OF
```

---

# 204. Balance sheet

Typically:

```text
AS_OF
```

---

# 205. Income statement

Typically:

```text
PERIOD
or
YEAR_TO_DATE
```

---

# 206. Cash flow

Typically:

```text
PERIOD
or
YEAR_TO_DATE
```

---

# 207. No universal assumption

Definition decides.

---

# 208. Statement dimensions

Future:

```text
segment

business unit

project

region
```

---

# 209. `StatementDimensionFilter`

Can be applied to source scope.

---

# 210. Regulatory reports

May forbid dimension slicing.

---

# 211. Management reports

May allow it.

---

# 212. Multi-currency

Statements may require:

```text
functional currency

presentation currency
```

---

# 213. P1 boundary

Base architecture supports:

```text
currency code

rounding policy

future translation provider
```

Detailed FX translation can be P2.

---

# 214. `PresentationCurrency`

Value Object.

---

# 215. Currency translation

Must be policy-driven.

---

# 216. No live exchange-rate lookup during reproducible published report

If FX used:

```text
rate snapshot must be captured
```

---

# 217. `ExchangeRateSnapshot`

Future integration.

---

# 218. Statement formulas and cycles

Formula graph must be acyclic.

---

# 219. `StatementFormulaCycleError`

If:

```text
A depends on B

B depends on A
```

---

# 220. Topological evaluation

Formula engine can evaluate:

```text
dependency DAG
```

---

# 221. Parent aggregation cycles

Hierarchy also must be acyclic.

---

# 222. `StatementHierarchyCycleError`

---

# 223. Duplicate mappings

A mapping set must detect:

```text
same account
same period
same purpose
ambiguous target
```

---

# 224. Ambiguity

Fail closed.

---

# 225. Overlap

Temporal overlaps in mappings must be rejected or explicitly prioritized.

---

# 226. `MappingApplicability`

```text
effective dates

statement type

purpose

source side condition
```

---

# 227. Priority

Avoid hidden priorities.

If two mappings match:

```text
AmbiguousStatementMappingError
```

unless explicit precedence policy exists.

---

# 228. Missing reference reporting model

If regulatory profile requires it:

```text
ReferenceReportingModelNotFoundError
```

---

# 229. Incomplete model

If provider indicates:

```text
human review required
```

activation gate blocks.

---

# 230. Reporting definition source

Three sources possible:

```text
REFERENCE

COMPANY

CUSTOM
```

---

# 231. `StatementDefinitionOrigin`

```text
REFERENCE

COMPANY

CUSTOM
```

---

# 232. Reference-derived definition

Must preserve:

```text
reference node ids

provenance

edition

snapshot
```

---

# 233. Company definition

Can be management-specific.

---

# 234. Custom

Developer-defined via public API.

---

# 235. Statement identifiers

Use stable IDs:

```text
statement:fr-pcg:2026:balance-sheet

line:fr-pcg:2026:BS:A100
```

if provider supplies them.

Do not replace with random UUIDs unnecessarily for regulatory refs.

---

# 236. Internal IDs

Company mapping sets can have internal UUIDs.

---

# 237. Distinguish

```text
internal id

reference reporting id

business code
```

---

# 238. Audit events

```text
STATEMENT_DEFINITION_CREATED

STATEMENT_MAPPING_SET_CREATED

STATEMENT_MAPPING_VALIDATED

REPORT_SNAPSHOT_CREATED

REPORT_SNAPSHOT_VALIDATED

REPORT_SNAPSHOT_PUBLISHED

REGULATORY_PROFILE_ACTIVATED

REGULATORY_EXPORT_CREATED

REGULATORY_EXPORT_PUBLISHED
```

---

# 239. Domain events

```text
ReportSnapshotCreated

ReportSnapshotPublished

RegulatoryProfileActivated

RegulatoryExportGenerated
```

---

# 240. Audit vs domain event

Remain separate.

---

# 241. Lineage

```text
JournalEntryLine
    ->
TrialBalanceRow
    ->
StatementLine
    ->
ReportSnapshot
    ->
ExportArtifact
```

---

# 242. `StatementLineageEdge`

Can reuse generic:

```text
LineageEdge
```

---

# 243. Statement evidence

For each line:

```text
mapped account refs

source balance refs

formula dependencies
```

---

# 244. Formula lineage

A formula line must expose:

```text
dependent line ids
```

---

# 245. Drill-down formula

Formula -> dependencies -> account mappings -> ledger.

---

# 246. Reproducibility

Published report must pin:

```text
runtime

source snapshot

statement definition

mapping set

reference snapshot

rounding policy

control definitions
```

---

# 247. No live mapping in historical snapshot

Historical report uses:

```text
mapping_set_version
```

stored in snapshot.

---

# 248. Report comparison

`ReportComparison`

```text
snapshot A

snapshot B

line-by-line delta
```

---

# 249. `ReportComparison`

```text
ReportComparison
|
+-- left_snapshot
+-- right_snapshot
+-- aligned_lines
+-- differences
+-- mapping_notes
```

---

# 250. Different definitions

If A and B use different statement definitions:

```text
crosswalk required
```

---

# 251. No implicit line-code equality

Same line code does not automatically mean same semantics across editions.

---

# 252. `StatementCrosswalk`

Can be supplied by provider or manually validated.

---

# 253. Mapping migration test

Must verify:

```text
old report remains reproducible

new report uses new definitions
```

---

# 254. Rendering

The calculation result should be renderable without accessing ledger again.

---

# 255. Why

Ensures:

```text
stable published artifact
```

---

# 256. Render input

```text
ReportSnapshot
```

---

# 257. PDF / Word

Presentation artifact generation belongs to adapters/renderers.

---

# 258. Internal JSON representation

Canonical representation recommended.

---

# 259. `ReportSnapshotSchemaVersion`

Required.

---

# 260. Serialization

Values as:

```text
Decimal strings
```

---

# 261. Dates

ISO 8601.

---

# 262. Stable order

Statement lines preserve:

```text
definition order
```

---

# 263. JSON canonical hash

Use:

```text
stable ordering
stable decimals
stable enums
```

---

# 264. Export file naming

Regulatory export definition can define:

```text
entity

period

profile

version

timestamp
```

---

# 265. Filename not semantic identity

Artifact ref/checksum remains identity.

---

# 266. Report storage

Two possibilities:

```text
database JSON

artifact store
```

---

# 267. P1 recommendation

Store:

```text
metadata in DB

canonical payload in DB or immutable artifact store
```

depending volume.

---

# 268. Large notes

Future notes/disclosures may require artifact storage.

---

# 269. Notes to financial statements

P2:

```text
DisclosureDefinition

DisclosureSnapshot
```

---

# 270. Footnotes

P1 optional.

---

# 271. Regulatory filing status

Future:

```text
DRAFT

SUBMITTED

ACCEPTED

REJECTED
```

if integration with external regulator.

---

# 272. Not part of core P1

The framework only prepares export.

---

# 273. External filing adapter

P2.

---

# 274. Control severity

Regulatory controls may be:

```text
blocking
```

by profile.

---

# 275. Internal reports

Can allow warnings.

---

# 276. `ReportingControlPolicy`

```text
ReportingControlPolicy
|
+-- profile
+-- required_controls
+-- blocking_controls
+-- tolerance_rules
+-- effective_dates
```

---

# 277. Statement build errors

```text
FinancialStatementError
|
+-- StatementDefinitionNotFoundError
+-- StatementDefinitionInvalidError
+-- StatementHierarchyCycleError
+-- StatementFormulaCycleError
+-- StatementMappingSetNotFoundError
+-- StatementMappingIncompleteError
+-- AmbiguousStatementMappingError
+-- StatementSourceUnavailableError
+-- StatementSourceStaleError
+-- StatementBuildError
```

---

# 278. Regulatory errors

```text
RegulatoryReportingError
|
+-- RegulatoryProfileNotFoundError
+-- RegulatoryProfileNotActiveError
+-- ReferenceReportingModelNotFoundError
+-- UnresolvedRegulatoryMappingError
+-- RegulatoryControlFailedError
+-- RegulatoryExportDefinitionNotFoundError
+-- RegulatoryExportValidationError
+-- RegulatoryExportIntegrityError
```

---

# 279. Fail-closed

Must fail:

```text
ambiguous mapping

required unmapped account

non-executable candidate used

stale source for regulatory publication

reference snapshot missing

blocking control fail

checksum mismatch

definition cycle
```

---

# 280. Warning examples

```text
non-material unmapped internal account

zero hidden line

presentation label missing translation
```

depending profile.

---

# 281. Query ports

```text
FinancialStatementQuery

StatementDrilldownQuery

ReportSnapshotQuery

RegulatoryReportQuery
```

---

# 282. Repositories

```text
StatementDefinitionRepository

StatementMappingSetRepository

ReportSnapshotRepository

RegulatoryReportingProfileRepository

RegulatoryExportRepository
```

---

# 283. Snapshot repository

Append-oriented.

---

# 284. Published snapshot update

Forbidden.

---

# 285. Mapping set repository

Optimistic revision during DRAFT/VALIDATED lifecycle.

---

# 286. Profile activation

Uses UoW.

---

# 287. Export creation

Should not modify report snapshot.

---

# 288. Transaction boundary - snapshot publish

```text
load validated result

verify source freshness

verify controls

persist immutable snapshot

audit

outbox

commit
```

---

# 289. Transaction boundary - profile activation

```text
lock profile scope

validate reference snapshot

validate mappings

validate required controls

activate profile

supersede prior profile if applicable

audit

commit
```

---

# 290. Transaction boundary - export

Artifact creation may be external.

Use workflow:

```text
create export record PENDING

render artifact

compute checksum

finalize export

audit
```

or upload-first pattern.

---

# 291. No distributed 2PC

Same principle as artifact store.

---

# 292. Export idempotence

Key:

```text
report snapshot id

export definition version

requested purpose
```

---

# 293. Same export request

Can return same artifact if immutable and identical.

---

# 294. Different renderer version

May produce new artifact.

---

# 295. `ExportRuntimeVersion`

Capture renderer version.

---

# 296. Control run link

Report snapshot stores:

```text
control_run_refs
```

---

# 297. Build vs validate

Statement engine can build:

```text
DRAFT result
```

even with warnings.

Publication requires controls.

---

# 298. `ReportBuildMode`

```text
PREVIEW

VALIDATION

PUBLICATION
```

---

# 299. PREVIEW

Can tolerate incomplete mappings with findings.

---

# 300. VALIDATION

Runs full controls.

---

# 301. PUBLICATION

Requires gate pass.

---

# 302. `ReportPublicationGate`

```text
REPORT_PUBLICATION_GATE
```

---

# 303. Regulatory profile gate

May be stricter than generic publication gate.

---

# 304. Statement definition validation

Checks:

```text
unique line ids

valid parent refs

acyclic hierarchy

acyclic formulas

valid order

formula deps exist

required totals exist
```

---

# 305. Mapping validation

Checks:

```text
target lines exist

accounts exist

effective dates valid

allocation sums valid

no ambiguity

provenance present
```

---

# 306. Source validation

Checks:

```text
entity matches

period scope matches

trial balance variant matches policy

snapshot fresh
```

---

# 307. Control validation

Checks:

```text
balance equation

cash flow reconciliation

mapping coverage

required lines

drill-down completeness
```

---

# 308. Public API stability

Statement definitions and mappings are likely extension APIs.

Need versioned public contracts.

---

# 309. Adapter extensibility

Third parties may provide:

```text
custom renderer

custom regulatory exporter

custom statement definition provider
```

---

# 310. `StatementDefinitionProvider`

Port optional:

```python
class StatementDefinitionProvider(Protocol):
    def get(
        self,
        code: str,
        version: str | None = None,
    ) -> FinancialStatementDefinition:
        ...
```

---

# 311. Reference adapter

Can transform:

```text
ReferenceReportingModel
```

into:

```text
FinancialStatementDefinition
```

while preserving IDs.

---

# 312. Transformation trace

```text
ReferenceReportingModel
    ->
StatementDefinition
```

must preserve provenance.

---

# 313. `ReferenceStatementAdapter`

```text
reference node -> statement line
```

---

# 314. No semantic guessing

If reference node lacks executable mapping info:

```text
structure only
```

---

# 315. Company-specific mappings

Stored separately from reference model.

---

# 316. Why

Prevents contaminating regulatory source with company config.

---

# 317. Management statement

Can reuse same engine with:

```text
custom StatementDefinition
```

---

# 318. Example management P&L

```text
Revenue
Cost of Sales
Gross Margin
Operating Expenses
Operating Profit
```

No regulatory authority implied.

---

# 319. Financial Analysis boundary

The next context consumes:

```text
ReportSnapshot

StatementLine values

TrialBalanceSnapshot
```

---

# 320. Financial Analysis never writes report source

Read-only.

---

# 321. Example ratio lineage

```text
Current Ratio
    ->
Current Assets line
Current Liabilities line
    ->
mapped accounts
    ->
ledger
```

---

# 322. Report snapshot IDs in analysis

Analysis snapshot pins input report snapshot.

---

# 323. Consolidation boundary

Future consolidation may produce:

```text
ConsolidatedReportSnapshot
```

using separate mappings / eliminations.

---

# 324. Do not merge with statutory reporting P1

---

# 325. Performance

Statement building is generally:

```text
O(number of mapped accounts + number of lines)
```

---

# 326. Mapping index

Recommended:

```text
(mapping_set_id, company_account_id)
```

---

# 327. Line index

```text
(statement_definition_id, line_id)
```

---

# 328. Snapshot index

```text
(entity_id, report_type, period, generated_at)
```

---

# 329. Profile index

```text
(entity_id, standard_id, edition, status)
```

---

# 330. Query optimization

Load all relevant mappings in batch.

---

# 331. No one-query-per-line

Avoid N+1.

---

# 332. Formula evaluation

Can be in-memory after line aggregation.

---

# 333. Large reports

Still generally modest line count.

---

# 334. Source size

Trial balance size may be larger; batch load.

---

# 335. Drill-down pagination

Required for large accounts.

---

# 336. Render performance

Separate concern.

---

# 337. Caching

Preview reports can be cached by:

```text
source checksum

definition version

mapping version
```

---

# 338. Published snapshot needs no recalculation cache

It is immutable.

---

# 339. Controls caching

Possible reuse if same immutable snapshot.

---

# 340. Test strategy - statement definition

```text
test_line_ids_unique

test_hierarchy_no_cycle

test_formula_dependencies_exist

test_formula_no_cycle
```

---

# 341. Unit tests - mapping

```text
test_many_accounts_to_one_line

test_one_account_to_multiple_lines_with_allocation

test_allocation_sum_must_equal_one

test_candidate_mapping_not_executable

test_ambiguous_mapping_fails
```

---

# 342. Unit tests - engine

```text
test_balance_sheet_uses_closing_balance_measure

test_income_statement_uses_period_movement_when_defined

test_subtotal_sums_children

test_formula_line_calculates

test_sign_convention_applies
```

---

# 343. Unit tests - snapshot

```text
test_published_snapshot_immutable

test_snapshot_pins_mapping_version

test_snapshot_pins_definition_version

test_snapshot_checksum_stable
```

---

# 344. Unit tests - regulatory profile

```text
test_profile_requires_reference_snapshot

test_profile_activation_blocks_unresolved_candidates

test_new_reference_does_not_mutate_active_profile
```

---

# 345. Property tests - mapping conservation

For any mapped source balances:

```text
sum allocated amounts
=
sum source mapped amounts
```

when allocation is total.

---

# 346. Property - formula determinism

Same values + same definition:

```text
same formula output
```

---

# 347. Property - snapshot checksum

Same canonical report:

```text
same checksum
```

---

# 348. Property - drilldown sum

For detail line:

```text
sum(drilldown contributions)
=
line value
```

before presentation rounding.

---

# 349. Integration tests

Use:

```text
TrialBalanceSnapshot

mapping set

statement definition

controls

snapshot persistence
```

---

# 350. Golden CFA FRA statement scenarios

Use existing reference behavior:

```text
trial balance
-> statement mapping
-> balance sheet
-> income statement
-> cash flow
-> drill-down
```

---

# 351. Golden regulatory fixtures

For each supported reporting dataset:

```text
structure

node IDs

hierarchy

required line metadata

human-review flags
```

---

# 352. Golden non-executable hints

Expected:

```text
candidate remains candidate
```

---

# 353. Golden balance sheet

Source balances produce:

```text
Assets = Liabilities + Equity
```

---

# 354. Golden cash flow

Expected reconciliation.

---

# 355. Golden comparative

N / N-1 with same definition.

---

# 356. Golden upgrade

Old profile + new reference:

```text
old snapshot unchanged

new profile requires review
```

---

# 357. Replay

Rebuild report snapshot using:

```text
same trial balance snapshot

same mapping set

same definition

same reference snapshot

same runtime
```

Expected same checksum.

---

# 358. Current-engine comparison

Same inputs, newer engine:

```text
difference report
```

---

# 359. Migration tests

Schema migration must preserve:

```text
report snapshots

mapping versions

profile versions

checksums
```

---

# 360. Contract tests - renderer

```text
same snapshot -> deterministic semantic representation
```

Presentation bytes may vary if metadata timestamps included, but canonical report must be stable.

---

# 361. Contract tests - exporter

```text
valid snapshot

valid definition

artifact checksum

validation results

no snapshot mutation
```

---

# 362. Adapter qualification

A regulatory exporter marked Production must pass:

```text
contract

golden

checksum

failure

artifact persistence

replay
```

---

# 363. Observability

Metrics:

```text
statement_build_total

statement_build_duration

report_snapshot_total

mapping_incomplete_total

regulatory_export_total

regulatory_export_failure_total

report_replay_mismatch_total
```

---

# 364. Logs

Context:

```text
entity_id

statement_type

definition_version

mapping_set_version

report_snapshot_id

profile_id

correlation_id
```

---

# 365. Tracing spans

```text
load_trial_balance

resolve_statement_mappings

aggregate_statement_lines

evaluate_formulas

run_statement_controls

persist_report_snapshot

render_regulatory_export
```

---

# 366. Security / confidentiality

Financial statements may contain sensitive data.

Audit should log:

```text
refs / ids / checksums
```

not full reports.

---

# 367. Artifact access

Handled by application/runtime authorization.

---

# 368. Multi-entity isolation

All report queries and repositories scoped by:

```text
AccountingEntityId
```

---

# 369. Cross-entity reporting

Belongs to future:

```text
Consolidation
```

---

# 370. Package domain

```text
src/pyaccountingkit/domain/
|
+-- statements/
|   +-- definition.py
|   +-- line_definition.py
|   +-- formula.py
|   +-- mapping.py
|   +-- mapping_set.py
|   +-- engine.py
|   +-- result.py
|   +-- snapshot.py
|   +-- comparison.py
|   +-- source_policy.py
|
+-- regulatory_reporting/
    +-- profile.py
    +-- upgrade.py
    +-- export_definition.py
    +-- export_artifact.py
    +-- evidence.py
    +-- errors.py
```

---

# 371. Application package

```text
src/pyaccountingkit/application/
|
+-- statements/
|   +-- create_definition.py
|   +-- validate_mapping_set.py
|   +-- build_statement.py
|   +-- create_snapshot.py
|   +-- publish_snapshot.py
|   +-- compare_reports.py
|
+-- regulatory_reporting/
    +-- create_profile.py
    +-- activate_profile.py
    +-- plan_upgrade.py
    +-- build_regulatory_report.py
    +-- export_report.py
```

---

# 372. Ports

```text
TrialBalanceQuery

StatementDefinitionRepository

StatementMappingSetRepository

ReportSnapshotRepository

RegulatoryReportingProfileRepository

RegulatoryExportRepository

AccountingReferenceProvider

ReportRenderer

RegulatoryExporter

ArtifactStorePort

AuditPort

ControlRunRepository

UnitOfWork

Clock
```

---

# 373. Adapter examples

```text
adapters/
|
+-- statements/
|   +-- in_memory/
|   +-- sql/
|
+-- reporting/
|   +-- json/
|   +-- csv/
|   +-- xlsx/
|   +-- pdf/
|   +-- custom/
|
+-- references/
    +-- regulatory_framework/
```

---

# 374. Reference adapter behavior

```text
load ReferenceReportingModel

preserve node IDs

preserve provenance

preserve review flags

convert structure to StatementDefinition

do NOT auto-validate hints
```

---

# 375. SQL persistence

Suggested tables:

```text
statement_definition

statement_line_definition

statement_mapping_set

statement_account_mapping

report_snapshot

regulatory_reporting_profile

regulatory_export
```

---

# 376. Mapping set uniqueness

Example:

```text
UNIQUE(
    entity_id,
    statement_definition_id,
    version
)
```

---

# 377. Active profile uniqueness

Potential:

```text
one active profile
per entity / standard / purpose / effective date
```

with transactional validation.

---

# 378. Snapshot append-only

No generic update.

---

# 379. Export append-only

Published artifacts immutable.

---

# 380. Report revision

Not same as mutable revision.

Use:

```text
snapshot versions
```

instead.

---

# 381. Profile revision

Mutable DRAFT/ACTIVE lifecycle can use optimistic revision.

---

# 382. Mapping revision

Same.

---

# 383. Statement definition revision

Reference definitions immutable by version.

Company DRAFT definitions may use revision until activated.

---

# 384. Transactional requirements

Activation and publish use UoW.

---

# 385. Controls integration

Use existing `ControlGate`.

---

# 386. `STATEMENT_VALIDATION_GATE`

For snapshot validation.

---

# 387. `REPORT_PUBLICATION_GATE`

For publish.

---

# 388. `REGULATORY_EXPORT_GATE`

For export.

---

# 389. Sign-off

Optional:

```text
reviewer

approver
```

as `PROCESS_REQUIREMENT`.

---

# 390. Audit sign-off

Use generic `SignOff`.

---

# 391. Materiality

Reporting profile may define:

```text
display materiality

mapping materiality

control tolerance
```

---

# 392. Materiality != accounting recognition materiality

Keep separate contexts.

---

# 393. `ReportingMaterialityPolicy`

```text
ReportingMaterialityPolicy
|
+-- threshold
+-- currency
+-- visibility
+-- control_use
```

---

# 394. Hidden zero lines

Presentation only.

---

# 395. Required zero lines

Regulatory definition may require display even at zero.

---

# 396. Visibility source

Reference node attributes may specify.

---

# 397. Required lines

Must not be dropped due to zero.

---

# 398. `RequiredLinePolicy`

---

# 399. Notes on exact regulatory semantics

If the source dataset does not specify:

```text
mapping rule

formula

required visibility

export format
```

PyAccountingKit must not invent it.

---

# 400. Explicit gap

The framework may expose:

```text
unsupported / requires configuration
```

rather than guess.

---

# 401. `UnsupportedReportingCapability`

Examples:

```text
NO_EXECUTABLE_ACCOUNT_MAPPING

NO_EXPORT_DEFINITION

NO_CASHFLOW_DEFINITION

NO_REQUIRED_LINE_METADATA
```

---

# 402. Capability discovery

`ReferenceReportingCapabilities`

```text
structure

candidate_hints

executable_mappings

formulas

exports

controls
```

---

# 403. Profile creation uses capabilities

If capability missing:

```text
manual/configured layer required
```

---

# 404. Company overrides

A company may overlay:

```text
labels

mapping

presentation order
```

depending profile.

---

# 405. Regulatory structure override

Must not alter official structure silently.

Use:

```text
company presentation layer
```

separate.

---

# 406. `PresentationOverlay`

```text
PresentationOverlay
|
+-- labels
+-- visibility
+-- formatting
+-- custom sections?
```

---

# 407. Structural override

Requires:

```text
new custom StatementDefinition
```

and should not be labeled official regulatory output.

---

# 408. `OfficialityStatus`

```text
OFFICIAL_REFERENCE

COMPANY_ADAPTED

MANAGEMENT

CUSTOM
```

---

# 409. Export status should include officiality

Avoid confusing:

```text
custom report
```

with:

```text
official statutory form
```

---

# 410. Report metadata

Include:

```text
entity

period

statement type

standard

edition

profile

source snapshot

generated date

currency

officiality
```

---

# 411. Human-readable footer

Renderer may show:

```text
report snapshot id

generated at

reference edition
```

---

# 412. Not required in canonical semantic payload

Presentation concern.

---

# 413. Comparison with CFA FRA

CFA FRA already separates:

```text
StatementAccountMapping
```

from the regulatory framework account relation.

PyAccountingKit preserves this distinction.

---

# 414. CFA FRA analytical layer

Ratios and drilldown built from statements are pushed to next context.

---

# 415. Doctrine boundary

The accounting books describe statement structure and principles, but current regulatory line structures come from versioned datasets.

---

# 416. Regulatory safety rule

```text
doctrine informs design

reference dataset drives current executable regulatory configuration
```

---

# 417. Risks principaux

## RISK-REP-001 - Statement line becomes source of truth

Réponse :

```text
trial balance remains source projection
```

---

## RISK-REP-002 - Candidate regulatory hints auto-executed

Réponse :

```text
review flags + fail-closed
```

---

## RISK-REP-003 - Hardcoded taxonomy

Réponse :

```text
ReferenceReportingModel provider
```

---

## RISK-REP-004 - Mapping ambiguity

Réponse :

```text
MappingSet validation
```

---

## RISK-REP-005 - Published report changes after reopen

Réponse :

```text
immutable snapshots + supersession
```

---

## RISK-REP-006 - Comparative semantics drift

Réponse :

```text
versioned definitions + crosswalk
```

---

## RISK-REP-007 - Cash flow doesn't reconcile

Réponse :

```text
CASHFLOW_RECONCILED control
```

---

## RISK-REP-008 - Formula cycle

Réponse :

```text
definition validation
```

---

## RISK-REP-009 - Export bytes not traceable

Réponse :

```text
artifact checksum + evidence bundle
```

---

## RISK-REP-010 - Current dataset silently changes old reports

Réponse :

```text
reference snapshot pinning
```

---

# 418. ADRs

| ID | Décision |
|---|---|
| ADR-REP-001 | Les états financiers sont des projections, pas une source comptable |
| ADR-REP-002 | `TrialBalanceSnapshot` est la source recommandée pour publication |
| ADR-REP-003 | `FinancialStatementDefinition` est versionnée |
| ADR-REP-004 | La hiérarchie des lignes est explicite |
| ADR-REP-005 | Les formules utilisent une DSL limitée et déterministe |
| ADR-REP-006 | `StatementAccountMapping` est distinct du `RegulatoryAccountBinding` |
| ADR-REP-007 | `StatementMappingSet` est versionné |
| ADR-REP-008 | Les candidate account hints réglementaires ne sont pas exécutables par défaut |
| ADR-REP-009 | Les human-review flags du provider sont respectés |
| ADR-REP-010 | Aucune taxonomy réglementaire n'est hardcodée dans le core |
| ADR-REP-011 | Le provider peut fournir la structure sans mapping exécutable |
| ADR-REP-012 | Les mappings ambiguës échouent en fail-closed |
| ADR-REP-013 | Les mappings one-to-many exigent une allocation explicite |
| ADR-REP-014 | Le calcul utilise Decimal avant tout rounding de présentation |
| ADR-REP-015 | `ReportSnapshot` publié est immutable |
| ADR-REP-016 | Un reopen ne modifie ni ne supprime un snapshot publié |
| ADR-REP-017 | Les snapshots sont reproductibles par versions/sources pinées |
| ADR-REP-018 | Balance Sheet / Income Statement / Cash Flow sont des StatementDefinitions spécialisées |
| ADR-REP-019 | `CASHFLOW_RECONCILED` reste un control, pas une mutation |
| ADR-REP-020 | La définition exacte d'un TrialBalance variant source est policy-driven |
| ADR-REP-021 | Le reporting réglementaire utilise un `RegulatoryReportingProfile` versionné |
| ADR-REP-022 | Un nouveau ReferenceSnapshot ne modifie jamais un profil actif silencieusement |
| ADR-REP-023 | Les upgrades réglementaires passent par impact analysis + nouvelle version |
| ADR-REP-024 | Les exports réglementaires sont dérivés d'un ReportSnapshot |
| ADR-REP-025 | Tout export réglementaire final possède un checksum |
| ADR-REP-026 | `ReportRenderer` et `RegulatoryExporter` sont distincts |
| ADR-REP-027 | Le reporting est read-only vis-à-vis du Journal/Ledger |
| ADR-REP-028 | Les reporting adjustments éventuels ne modifient pas le ledger statutaire |
| ADR-REP-029 | Le drill-down StatementLine -> TrialBalance -> Ledger -> Entry est requis |
| ADR-REP-030 | Les comparatifs pinent leurs propres mapping/definition versions |
| ADR-REP-031 | Les line-code equalities ne prouvent pas l'équivalence sémantique |
| ADR-REP-032 | Les report snapshots conservent les control run refs |
| ADR-REP-033 | Le moteur distingue semantic result et rendered view |
| ADR-REP-034 | Les labels ne sont jamais utilisés comme clés logiques |
| ADR-REP-035 | La publication réglementaire échoue si un required mapping est non résolu |
| ADR-REP-036 | Les source/reporting capabilities manquantes sont exposées explicitement |
| ADR-REP-037 | Les management statements réutilisent le même engine sans autorité réglementaire implicite |
| ADR-REP-038 | Financial Analysis consomme les snapshots et reste downstream |
| ADR-REP-039 | Consolidation reste un bounded context futur distinct |
| ADR-REP-040 | Les datasets doctrinaux ne remplacent jamais le reporting réglementaire versionné |

---

# 419. Critères d'acceptation P1.2

```text
[ ] FinancialStatementDefinition est défini

[ ] StatementLineDefinition est défini

[ ] StatementLineType est défini

[ ] StatementFormula est défini

[ ] formula DSL est limitée

[ ] hierarchy cycle detection est définie

[ ] formula cycle detection est définie

[ ] StatementAccountMapping est défini

[ ] StatementMappingSet est défini

[ ] mapping statuses sont définis

[ ] candidate mapping n'est pas exécutable

[ ] mapping provenance est préservée

[ ] one-to-many allocation est supportée

[ ] TrialBalance source est définie

[ ] TrialBalanceSnapshot est recommandé pour publication

[ ] StatementSourcePolicy est défini

[ ] Balance Sheet est supporté

[ ] Income Statement est supporté

[ ] Cash Flow est supporté

[ ] CashFlowDefinition est définie

[ ] CASHFLOW_RECONCILED est intégré

[ ] BALANCE_SHEET_BALANCED est intégré

[ ] StatementMappingCoverage est défini

[ ] missing regulatory mapping peut être bloquant

[ ] ReportSnapshot est défini

[ ] ReportSnapshot publié est immutable

[ ] snapshot checksum est défini

[ ] reproducibility envelope est défini

[ ] drill-down complet est défini

[ ] RegulatoryReportingProfile est défini

[ ] reference snapshot pinning est obligatoire

[ ] provider reporting model est consommé

[ ] hardcoded regulatory taxonomy est interdite

[ ] reference candidate hints restent non exécutables

[ ] regulatory upgrade plan est défini

[ ] RegulatoryExportDefinition est définie

[ ] RegulatoryExportArtifact est défini

[ ] export checksum est défini

[ ] export gate est défini

[ ] renderer != exporter est explicite

[ ] comparative reporting est préparé

[ ] multi-standard reporting est supporté conceptuellement

[ ] Statement Engine est read-only vis-à-vis du ledger

[ ] tests unit/property/golden/replay sont définis
```

---

# 420. Ordre d'implémentation recommandé

## REP-00 - Statement primitives

```text
StatementType

StatementLineType

StatementLineDefinition

StatementFormula
```

---

## REP-01 - Statement Definition

```text
FinancialStatementDefinition

validation

hierarchy

formula graph
```

---

## REP-02 - Mapping

```text
StatementMappingSet

StatementAccountMapping

MappingAllocation

MappingProvenance
```

---

## REP-03 - Source integration

```text
ReportingSource

StatementSourcePolicy

TrialBalanceSnapshot integration
```

---

## REP-04 - Engine

```text
FinancialStatementEngine

line aggregation

formulas

sign conventions

rounding
```

---

## REP-05 - Drill-down

```text
StatementDrilldownQuery

source refs
```

---

## REP-06 - Snapshot

```text
ReportSnapshot

checksum

reproducibility envelope
```

---

## REP-07 - Core statements

```text
Balance Sheet

Income Statement

Cash Flow
```

---

## REP-08 - Controls

```text
BALANCE_SHEET_BALANCED

CASHFLOW_RECONCILED

STATEMENT_MAPPING_COMPLETE
```

---

## REP-09 - Regulatory Profile

```text
RegulatoryReportingProfile

ReferenceReportingModel adapter
```

---

## REP-10 - Reference safety

```text
human review flags

candidate hints

capability detection
```

---

## REP-11 - Regulatory Export

```text
RegulatoryExportDefinition

RegulatoryExporter

Artifact checksum
```

---

## REP-12 - Upgrade

```text
RegulatoryReportingUpgradePlan

mapping impact
```

---

## REP-13 - Golden / replay qualification

```text
reference datasets

CFA FRA scenarios

snapshot replay
```

---

# 421. Démonstrateur P1.2 - Balance Sheet

```text
1. Build ADJUSTED TrialBalanceSnapshot

2. Load Balance Sheet StatementDefinition

3. Load active StatementMappingSet

4. Map CompanyAccounts to statement lines

5. Aggregate detail lines

6. Evaluate subtotals

7. Apply sign conventions

8. Run BALANCE_SHEET_BALANCED

9. Build ReportSnapshot

10. Verify:
      source snapshot pinned
      definition version pinned
      mapping version pinned
      checksum stable
      drill-down available
```

---

# 422. Démonstrateur P1.2 - Income Statement

```text
1. Select period / YTD source

2. Apply movement mappings

3. Aggregate revenues / expenses

4. Calculate intermediate lines

5. Calculate net result

6. Run income statement reconciliation

7. Snapshot
```

---

# 423. Démonstrateur P1.2 - Cash Flow

```text
1. Load cash-flow definition

2. Load opening cash

3. Build CFO

4. Build CFI

5. Build CFF

6. Load closing cash

7. Run:
      Opening Cash + CFO + CFI + CFF = Closing Cash

8. Produce ReportSnapshot
```

---

# 424. Démonstrateur réglementaire

```text
1. Load ReferenceReportingModel
      standard = fr-pcg
      edition = 2026

2. Build Reference StatementDefinition

3. Preserve all regulatory node IDs

4. Import candidate account hints as CANDIDATE

5. Detect:
      human_validation_required = true

6. Block profile activation

7. Human validates mappings

8. Create validated StatementMappingSet

9. Activate RegulatoryReportingProfile

10. Build report from TrialBalanceSnapshot

11. Run regulatory control set

12. Create immutable ReportSnapshot

13. Export JSON / CSV

14. Compute SHA-256

15. Persist audit/evidence
```

---

# 425. Démonstrateur - non-executable hint safety

```text
Reference hint:
    line L
    candidate account A
    executable = false

Expected:

    mapping status = CANDIDATE

    report preview may show unresolved candidate

    regulatory publication = BLOCKED
```

---

# 426. Démonstrateur - reopen

```text
ReportSnapshot S1
    published from close revision 1

Period reopened

new entries posted

close revision 2

Expected:

    S1 remains immutable

    S1 may be marked stale/superseded

    new ReportSnapshot S2 created

    both remain traceable
```

---

# 427. Démonstrateur - reference upgrade

```text
Profile P1
    ReferenceSnapshot R1

New ReferenceSnapshot R2

Run RegulatoryReportingUpgradePlan

Detect:
    added lines
    removed lines
    changed mappings

Create Profile P2

Qualify

Activate P2

Expected:
    reports produced under P1 remain reproducible
```

---

# 428. Démonstrateur - comparative

```text
N:
    source snapshot TN
    mapping M2

N-1:
    source snapshot TN1
    mapping M1

Report:
    lines aligned by validated statement identity

No assumption:
    same code = same semantics
```

---

# 429. Matrice responsabilités

| Capability | Ledger | Statements | Regulatory Reporting | Controls | Analysis |
|---|---:|---:|---:|---:|---:|
| Source balances | **oui** | consomme | consomme | vérifie | consomme |
| Account -> Statement mapping | non | **oui** | configure/valide | vérifie | non |
| Statement formula | non | **oui** | peut fournir | vérifie | consomme |
| Regulatory structure | non | non | **oui** | vérifie | non |
| Snapshot | source TB | **oui** | utilise | valide | consomme |
| Export | non | renderer | **oui** | gate | non |
| Ratio | non | non | non | peut contrôler | **oui** |

---

# 430. Matrice objet / source de vérité

| Objet | Source de vérité |
|---|---|
| JournalEntry | Accounting Core |
| TrialBalance | Ledger projection |
| CompanyAccount | Company Chart |
| ReferenceAccount | Regulatory Reference |
| StatementLineDefinition | StatementDefinition / ReferenceReportingModel |
| StatementAccountMapping | Company Reporting Configuration |
| ReportSnapshot | Immutable reporting result |
| RegulatoryExportArtifact | Immutable export artifact |
| FinancialRatio | Financial Analysis |

---

# 431. Frontière avec Financial Analysis

Le prochain document :

```text
14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md
```

devra consommer :

```text
ReportSnapshot

FinancialStatementLine

TrialBalanceSnapshot
```

et ajouter notamment :

```text
SIG

EBE / EBITDA

CAF

FRNG

BFR

Trésorerie nette

ratios

scores

diagnostics
```

sans jamais modifier les états ou le ledger.

---

# 432. Conclusion

L'architecture de reporting de PyAccountingKit devient :

```text
TRIAL BALANCE
      |
      v
STATEMENT MAPPING
      |
      v
STATEMENT DEFINITION
      |
      v
FINANCIAL STATEMENT ENGINE
      |
      v
REPORT SNAPSHOT
      |
      +--> DRILL-DOWN
      |
      +--> FINANCIAL ANALYSIS
      |
      +--> REGULATORY REPORTING PROFILE
               |
               v
         REGULATORY EXPORT
```

Les principes majeurs sont :

```text
Financial Statement is a projection

Trial Balance remains upstream

CompanyAccount != StatementLine

Statement mapping != regulatory account binding

Reference reporting structure != executable account mapping

Candidate hints remain candidates

Human-review flags are honored

Published reports are immutable

Published reports are reproducible

No hardcoded regulatory taxonomy

No silent reference upgrade

No statement-to-ledger back-propagation

Every significant report line must drill down to accounting sources

Every regulatory export must be tied to a snapshot, a profile and a checksum
```

Le P1.2 fournit ainsi le socle nécessaire pour produire des états financiers fiables, multi-référentiels, versionnés, auditables et exportables sans casser les frontières du coeur comptable.

---

**Prochain document recommandé :**

```text
14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md
```
