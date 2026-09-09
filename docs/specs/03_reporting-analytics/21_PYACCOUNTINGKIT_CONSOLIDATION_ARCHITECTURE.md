# 21 - PyAccountingKit - Architecture de consolidation

> **Projet** : PyAccountingKit  
> **Document** : `21_PYACCOUNTINGKIT_CONSOLIDATION_ARCHITECTURE.md`  
> **Statut** : P2.1 - Architecture de consolidation  
> **Langue** : Français  
> **Objet** : Définir le bounded context `Consolidation`, ses agrégats, policies, flux, méthodes, mappings, traductions de devise, éliminations intragroupe, intérêts ne donnant pas le contrôle, ajustements de consolidation, snapshots, contrôles, traçabilité et frontières avec la comptabilité individuelle, le reporting et la réconciliation.

---

# 1. Résumé exécutif

La consolidation PyAccountingKit doit agréger plusieurs entités comptables sans modifier leurs comptabilités individuelles.

La cible est :

```text
Entity Accounting
    |
    +--> Entity A Trial Balance / Report Snapshot
    +--> Entity B Trial Balance / Report Snapshot
    +--> Entity C Trial Balance / Report Snapshot
    |
    v
Consolidation Scope
    |
    +--> Ownership / Control
    +--> Group Chart Mapping
    +--> Currency Translation
    +--> Accounting Policy Alignment
    +--> Intercompany Matching
    +--> Elimination Entries
    +--> Consolidation Adjustments
    +--> Non-Controlling Interests
    |
    v
Consolidated Trial Balance
    |
    v
Consolidated Financial Statements
    |
    v
Consolidation Snapshot
```

Principe central :

```text
Consolidation
    consumes individual accounting

but

never mutates individual accounting
```

Les écritures de consolidation vivent dans un registre de consolidation séparé.

---

# 2. Principes structurants

```text
Entity Ledger
    !=
Consolidation Ledger

Entity JournalEntry
    !=
ConsolidationEntry

Intercompany Matching
    !=
Elimination

Currency Translation
    !=
FX Settlement Accounting

Ownership
    !=
Control

Group Chart
    !=
Company Chart

Consolidation Adjustment
    !=
Entity Accounting Correction

Consolidated Snapshot
    !=
sum of entity reports without policy
```

---

# 3. Objectifs

Le bounded context doit permettre de :

1. représenter un groupe ;
2. définir un périmètre de consolidation ;
3. versionner l'appartenance au groupe ;
4. versionner les pourcentages de détention et de contrôle ;
5. définir la méthode de consolidation par entité ;
6. gérer les dates d'entrée et de sortie de périmètre ;
7. mapper les plans de comptes individuels vers un plan groupe ;
8. convertir les balances locales vers une devise de présentation groupe ;
9. gérer les différences de conversion ;
10. enregistrer des ajustements de consolidation ;
11. rapprocher les positions intragroupe ;
12. éliminer les opérations et soldes intragroupe ;
13. calculer les intérêts ne donnant pas le contrôle ;
14. gérer les retraitements d'homogénéisation ;
15. produire une balance consolidée ;
16. produire des états financiers consolidés ;
17. préserver le drill-down jusqu'aux comptes individuels ;
18. produire des snapshots immuables ;
19. garantir la reproductibilité ;
20. gérer les réouvertures et changements de périmètre sans réécriture historique ;
21. rester indépendante d'IFRS, PCG ou OHADA tant que les policies ne sont pas explicitement liées ;
22. supporter plusieurs référentiels via policies/configuration ;
23. préparer les intégrations futures de réconciliation avancée ;
24. rester framework-neutral.

---

# 4. Non-objectifs

Le P2.1 ne doit pas devenir :

```text
un outil de valorisation M&A complet

un moteur actuariel

un moteur fiscal de groupe complet

un moteur juridique de fusion

un outil de legal entity management

un moteur de purchase price allocation complet

un système de deal management

un outil de consolidation réglementaire spécifique à une juridiction sans source/policy explicite
```

Certaines de ces capacités peuvent être ajoutées ultérieurement comme extensions.

---

# 5. Bounded Context

Nom :

```text
Consolidation
```

Dépendances principales :

```text
Accounting Core
Ledger & Trial Balance
Financial Statements
Accounting Policies
Reference Data
Controls
Audit & Traceability
Reconciliation
```

---

# 6. Direction de dépendance

```text
Entity Accounting
        |
        v
Consolidation
```

Jamais :

```text
Consolidation
        |
        v
mutate Entity Ledger
```

---

# 7. Source d'entrée recommandée

Le moteur de consolidation consomme de préférence :

```text
TrialBalanceSnapshot
```

ou :

```text
ReportSnapshot
```

selon le type de consolidation.

---

# 8. Source canonique P2.1

Pour la consolidation comptable :

```text
TrialBalanceSnapshot
```

est la source privilégiée.

Pourquoi :

```text
granularité compte
mapping groupe
eliminations
adjustments
drill-down
```

---

# 9. ReportSnapshot comme source

Peut être utilisé pour :

```text
comparative reporting

light consolidation

presentation-only aggregation
```

mais pas pour tous les besoins d'élimination.

---

# 10. `Group`

Aggregate Root :

```text
Group
|
+-- id
+-- code
+-- name
+-- reporting_currency
+-- status
+-- metadata
```

---

# 11. `GroupStatus`

```text
DRAFT

ACTIVE

INACTIVE

ARCHIVED
```

---

# 12. Group != AccountingEntity

Un groupe :

```text
Group
```

n'est pas une entité comptable source.

---

# 13. Consolidation Scope

Aggregate Root :

```text
ConsolidationScope
|
+-- id
+-- group_id
+-- version
+-- effective_from
+-- effective_to?
+-- entities
+-- scope_policy
+-- status
+-- provenance
```

---

# 14. `ConsolidationScopeStatus`

```text
DRAFT

VALIDATED

ACTIVE

SUPERSEDED

ARCHIVED
```

---

# 15. Scope versioning

Tout changement de périmètre crée :

```text
new scope version
```

Pas de mutation silencieuse d'un scope historique.

---

# 16. `ConsolidationEntity`

```text
ConsolidationEntity
|
+-- accounting_entity_id
+-- consolidation_scope_id
+-- consolidation_method
+-- ownership_interest
+-- control_interest
+-- effective_from
+-- effective_to?
+-- functional_currency
+-- reporting_currency
+-- policy_set_ref?
+-- group_chart_mapping_ref?
+-- metadata
```

---

# 17. Ownership != Control

Toujours distinguer :

```text
ownership_interest

control_interest
```

---

# 18. Pourquoi

Les deux peuvent diverger selon :

```text
direct holdings

indirect holdings

voting rights

contractual arrangements

specific consolidation policies
```

---

# 19. `OwnershipInterest`

```text
OwnershipInterest
|
+-- percentage
+-- effective_from
+-- effective_to?
+-- provenance
```

---

# 20. `ControlInterest`

Même structure.

---

# 21. Ownership graph

Le groupe peut contenir :

```text
Parent
    |
    +--> Subsidiary A
    |       |
    |       +--> Subsidiary C
    |
    +--> Subsidiary B
```

---

# 22. Direct vs indirect ownership

Le modèle doit supporter :

```text
direct_interest

indirect_interest

effective_interest
```

---

# 23. `OwnershipEdge`

```text
OwnershipEdge
|
+-- investor_entity_id
+-- investee_entity_id
+-- ownership_percentage
+-- voting_percentage?
+-- effective_from
+-- effective_to?
+-- source_ref
```

---

# 24. `OwnershipGraph`

Read model / calculation input.

---

# 25. No automatic legal conclusion

PyAccountingKit ne conclut pas :

```text
"control exists"
```

uniquement à partir d'un pourcentage sans `ControlPolicy`.

---

# 26. `ControlPolicy`

```text
ControlPolicy
|
+-- id
+-- version
+-- decision_rules
+-- applicability
+-- provenance
```

---

# 27. Control decision

```text
ControlDecision
|
+-- entity_id
+-- status
+-- method_candidate
+-- rationale
+-- evidence
+-- review_required
```

---

# 28. `ControlDecisionStatus`

```text
CONTROLLED

JOINT_CONTROL

SIGNIFICANT_INFLUENCE

NO_CONTROL

INDETERMINATE

REQUIRES_REVIEW
```

---

# 29. Consolidation methods

Le framework doit permettre :

```text
FULL

PROPORTIONATE

EQUITY

EXCLUDED

CUSTOM
```

---

# 30. Important

Le choix d'une méthode :

```text
is policy-driven
```

et non universel.

---

# 31. `ConsolidationMethod`

Value object / code.

---

# 32. `ConsolidationMethodPolicy`

```text
ConsolidationMethodPolicy
|
+-- control_decision
+-- method
+-- applicability
+-- version
+-- provenance
```

---

# 33. Full consolidation

Conceptuellement :

```text
100% of eligible balances
+
NCI allocation if applicable
```

---

# 34. Proportionate consolidation

Conceptuellement :

```text
eligible balances
*
consolidation percentage
```

selon policy.

---

# 35. Equity method

Conceptuellement :

```text
investment carrying amount
+
share of post-acquisition result/equity changes
```

La formule exacte reste policy-driven.

---

# 36. `EXCLUDED`

Entité hors périmètre pour une période donnée.

---

# 37. Effective period

Le scope doit être évalué :

```text
as_of / period
```

---

# 38. Acquisition / disposal dates

Le modèle supporte :

```text
entry_date

exit_date
```

---

# 39. Mid-period entry

Le traitement de résultats partiels dépend d'une policy.

---

# 40. `ConsolidationPeriod`

```text
ConsolidationPeriod
|
+-- id
+-- group_id
+-- fiscal_period
+-- reporting_date
+-- status
+-- revision
```

---

# 41. `ConsolidationPeriodStatus`

```text
OPEN

COLLECTING

ADJUSTING

REVIEW

CLOSED

REOPENED
```

---

# 42. Consolidation period != entity period

Le groupe peut avoir :

```text
group reporting period
```

distinct techniquement des périodes sources.

---

# 43. Period alignment

Chaque entity source doit être alignée vers le period group.

---

# 44. `PeriodAlignmentPolicy`

```text
EXACT

NEAREST_CLOSED_PERIOD

PRO_RATA

CUSTOM
```

---

# 45. P2.1 recommendation

Préférer :

```text
EXACT
```

pour le chemin standard.

---

# 46. Different fiscal year ends

Préparer :

```text
reporting package adjustments
```

mais ne pas les appliquer implicitement.

---

# 47. `EntityReportingPackage`

Objet d'entrée consolidé :

```text
EntityReportingPackage
|
+-- entity_id
+-- consolidation_period_id
+-- source_trial_balance_snapshot
+-- source_report_snapshot?
+-- policy_snapshot
+-- reference_snapshot
+-- group_chart_mapping
+-- currency_context
+-- package_adjustments
+-- checksum
+-- status
```

---

# 48. Package status

```text
DRAFT

VALIDATED

SUBMITTED

ACCEPTED

REJECTED

SUPERSEDED
```

---

# 49. Reporting package

Le package permet de figer :

```text
entity source
group mapping
currency rates
local-to-group adjustments
```

avant consolidation.

---

# 50. Reporting package immutability

Après `ACCEPTED` :

```text
immutable
```

---

# 51. Package resubmission

Nouvelle version.

---

# 52. Group Chart

```text
GroupChartOfAccounts
|
+-- id
+-- group_id
+-- version
+-- accounts
+-- status
```

---

# 53. Group Account

```text
GroupAccount
|
+-- id
+-- code
+-- label
+-- parent?
+-- role?
+-- statement_mapping?
+-- status
```

---

# 54. Group Chart != Company Chart

Une entité peut avoir :

```text
CompanyAccount 51200101
```

et le groupe :

```text
GroupAccount CASH_BANK
```

ou :

```text
GroupAccount 512
```

selon policy.

---

# 55. `GroupAccountMapping`

```text
GroupAccountMapping
|
+-- entity_id
+-- company_account_id
+-- group_account_id
+-- mapping_type
+-- effective_from
+-- effective_to?
+-- validation_status
+-- provenance
```

---

# 56. Mapping type

```text
DIRECT

SPLIT

AGGREGATE

FORMULA

CUSTOM
```

---

# 57. One-to-many mapping

Un CompanyAccount peut éventuellement être ventilé vers plusieurs GroupAccounts.

---

# 58. Split requires allocation

```text
AllocationRule
```

obligatoire.

---

# 59. Many-to-one mapping

Très fréquent :

```text
many local accounts
    ->
one group account
```

---

# 60. No prefix inference

Interdit :

```python
if local_code.startswith("512"):
    group = "CASH"
```

dans le core.

---

# 61. Mapping candidate

Allowed :

```text
GroupAccountMappingCandidate
```

---

# 62. Candidate != active

Toujours.

---

# 63. Mapping completeness

Contrôle :

```text
GROUP_CHART_MAPPING_COMPLETE
```

---

# 64. Mapping coverage

Read model :

```text
GroupMappingCoverage
```

---

# 65. Currency model

Chaque entité peut avoir :

```text
functional_currency
```

Le groupe possède :

```text
reporting_currency
```

---

# 66. Translation != transaction FX

La conversion de consolidation :

```text
Currency Translation
```

est distincte de la comptabilisation des écarts de change sur règlements.

---

# 67. `CurrencyTranslationPolicy`

```text
CurrencyTranslationPolicy
|
+-- id
+-- version
+-- balance_sheet_rate_policy
+-- income_statement_rate_policy
+-- equity_rate_policy
+-- translation_difference_policy
+-- applicability
+-- provenance
```

---

# 68. No universal rate rule

PyAccountingKit ne hardcode pas :

```text
closing rate for all balance sheet

average rate for all P&L
```

comme vérité universelle.

---

# 69. Rate types

```text
CLOSING

AVERAGE

HISTORICAL

TRANSACTION_DATE

CUSTOM
```

---

# 70. `ExchangeRateObservation`

```text
ExchangeRateObservation
|
+-- from_currency
+-- to_currency
+-- rate_type
+-- effective_date
+-- rate
+-- source
+-- checksum
```

---

# 71. `CurrencyTranslationSnapshot`

```text
CurrencyTranslationSnapshot
|
+-- group_id
+-- period_id
+-- rates
+-- policy_version
+-- checksum
```

---

# 72. No live FX in historical replay

Toujours snapshoté.

---

# 73. Translation result

```text
TranslatedTrialBalance
|
+-- entity_id
+-- source_trial_balance_ref
+-- reporting_currency
+-- translated_lines
+-- translation_difference
+-- rate_snapshot_ref
+-- checksum
```

---

# 74. Translation difference

Peut être affectée selon policy à :

```text
translation reserve / CTA role
```

sans hardcoder un compte.

---

# 75. `GroupAccountRole`

Exemples :

```text
TRANSLATION_RESERVE

NON_CONTROLLING_INTEREST

GOODWILL

INVESTMENT_IN_SUBSIDIARY

INTERCOMPANY_RECEIVABLE

INTERCOMPANY_PAYABLE

INTERCOMPANY_REVENUE

INTERCOMPANY_EXPENSE

GROUP_RESULT
```

---

# 76. Role resolution

Via :

```text
GroupAccountRoleResolutionService
```

---

# 77. Accounting policy alignment

Les entités peuvent avoir des policies différentes.

---

# 78. Consolidation homogenization

Le moteur doit permettre :

```text
ConsolidationAdjustment
```

pour homogénéiser vers les policies groupe.

---

# 79. `GroupAccountingPolicySet`

```text
GroupAccountingPolicySet
|
+-- id
+-- group_id
+-- version
+-- policies
+-- effective_from
+-- status
```

---

# 80. Local vs Group policy

```text
Entity Policy
    ->
Policy Difference Analysis
    ->
Consolidation Adjustment
```

---

# 81. No mutation local ledger

Même si une policy locale diffère :

```text
no entity ledger rewrite
```

---

# 82. `PolicyAlignmentAssessment`

```text
PolicyAlignmentAssessment
|
+-- entity_id
+-- group_policy_ref
+-- local_policy_ref
+-- differences
+-- adjustment_required
+-- review_required
```

---

# 83. Consolidation Entry

Aggregate :

```text
ConsolidationEntry
|
+-- id
+-- group_id
+-- consolidation_period_id
+-- entry_type
+-- lines
+-- source_refs
+-- policy_trace?
+-- status
+-- revision
+-- provenance
```

---

# 84. `ConsolidationEntryStatus`

```text
DRAFT

VALIDATED

POSTED

REVERSED
```

---

# 85. Reuse accounting workflow

Même discipline :

```text
DRAFT
    ->
VALIDATED
    ->
POSTED
    ->
REVERSED
```

---

# 86. But separate ledger

Ces écritures ne vont jamais dans :

```text
entity JournalEntry repository
```

---

# 87. `ConsolidationEntryType`

```text
POLICY_ALIGNMENT

CURRENCY_TRANSLATION

INTERCOMPANY_BALANCE_ELIMINATION

INTERCOMPANY_TRANSACTION_ELIMINATION

INVESTMENT_ELIMINATION

EQUITY_ADJUSTMENT

NCI_ALLOCATION

GOODWILL_ADJUSTMENT

DIVIDEND_ELIMINATION

UNREALIZED_PROFIT_ELIMINATION

OPENING_CONSOLIDATION

MANUAL_ADJUSTMENT

CUSTOM
```

---

# 88. Double-entry

Toute `ConsolidationEntry` comptable :

```text
SUM(debit) = SUM(credit)
```

---

# 89. `ConsolidationLine`

```text
ConsolidationLine
|
+-- group_account_id
+-- debit
+-- credit
+-- entity_dimension?
+-- counterparty_dimension?
+-- source_refs
+-- metadata
```

---

# 90. Decimal only

Toujours `Decimal`.

---

# 91. Consolidation Ledger

Read-side :

```text
ConsolidationLedger
```

---

# 92. Sources du consolidation ledger

```text
translated entity balances
+
posted consolidation entries
```

---

# 93. `ConsolidatedTrialBalance`

```text
ConsolidatedTrialBalance
|
+-- group_id
+-- period_id
+-- reporting_currency
+-- lines
+-- source_package_refs
+-- consolidation_entry_refs
+-- checksum
+-- status
```

---

# 94. Trial Balance formula

Conceptuellement :

```text
Translated entity balances
+
Consolidation adjustments
-
Eliminated effects
=
Consolidated Trial Balance
```

---

# 95. Intercompany dimensions

Pour permettre matching :

```text
entity_id
counterparty_entity_id
document_ref?
transaction_ref?
```

---

# 96. `IntercompanyPosition`

```text
IntercompanyPosition
|
+-- reporting_entity_id
+-- counterparty_entity_id
+-- account_role
+-- amount
+-- currency
+-- period
+-- source_refs
```

---

# 97. Intercompany Matching

Process :

```text
Entity A position
    vs
Entity B reciprocal position
```

---

# 98. Matching != elimination

Le matching détecte :

```text
correspondence / difference
```

L'élimination comptabilise :

```text
removal from group totals
```

---

# 99. `IntercompanyMatch`

```text
IntercompanyMatch
|
+-- id
+-- group_id
+-- period_id
+-- side_a
+-- side_b
+-- matched_amount
+-- difference
+-- status
+-- cause?
+-- review_status
```

---

# 100. Match status

```text
MATCHED

PARTIAL

UNMATCHED

INDETERMINATE

REVIEW_REQUIRED
```

---

# 101. Matching tolerance

```text
IntercompanyMatchingPolicy
```

---

# 102. `IntercompanyMatchingPolicy`

```text
currency_tolerance

absolute_tolerance

relative_tolerance?

date_tolerance?

reference_rules

auto_match_rules

review_rules

version
```

---

# 103. No silent tolerance write-off

Une différence tolérée pour matching n'est pas :

```text
automatically eliminated
```

sans policy.

---

# 104. Difference causes

```text
TIMING

FX

MAPPING

DOCUMENT_MISSING

AMOUNT_DIFFERENCE

UNRECORDED_COUNTERPART

OTHER
```

---

# 105. `IntercompanyDifference`

```text
IntercompanyDifference
|
+-- match_id
+-- amount
+-- cause
+-- status
+-- resolution
+-- evidence
```

---

# 106. Elimination candidate

Après matching :

```text
IntercompanyEliminationCandidate
```

---

# 107. Candidate != posted elimination

---

# 108. `IntercompanyEliminationCandidate`

```text
source_match_id

elimination_type

proposed_lines

difference_handling

status

review_required
```

---

# 109. Elimination types

```text
BALANCE

REVENUE_EXPENSE

DIVIDEND

INTERCOMPANY_ASSET_LIABILITY

UNREALIZED_PROFIT

CAPITAL_INVESTMENT

CUSTOM
```

---

# 110. Balance elimination

Exemple conceptuel :

```text
Group receivable
    vs
Group payable
```

---

# 111. Revenue/expense elimination

Exemple :

```text
Intercompany Revenue
    vs
Intercompany Expense
```

---

# 112. Dividend elimination

Policy-driven.

---

# 113. Unrealized profit

Le P2.1 doit prévoir l'architecture.

Exemple :

```text
inventory sold within group
with profit not realized externally
```

---

# 114. `UnrealizedProfitCase`

```text
UnrealizedProfitCase
|
+-- seller_entity
+-- buyer_entity
+-- source_transaction
+-- remaining_asset
+-- original_margin
+-- unrealized_amount
+-- tax_effect?
+-- policy_trace
```

---

# 115. Measurement

Le calcul exact dépend d'une policy.

---

# 116. Investment elimination

Le P2.1 prépare :

```text
investment in subsidiary
vs
share of subsidiary equity
```

---

# 117. `InvestmentEliminationCase`

```text
InvestmentEliminationCase
|
+-- investor
+-- investee
+-- investment_carrying_amount
+-- equity_components
+-- ownership_interest
+-- acquisition_context?
+-- goodwill_component?
+-- nci_component?
```

---

# 118. Acquisition accounting

Le moteur doit prévoir :

```text
AcquisitionContext
```

mais ne hardcode pas une méthode réglementaire unique.

---

# 119. `AcquisitionContext`

```text
acquisition_date
consideration?
ownership_acquired
control_acquired
fair_value_adjustments?
goodwill_policy?
nci_policy?
```

---

# 120. Goodwill

Objet potentiel :

```text
GoodwillMeasurement
```

---

# 121. Goodwill calculation

Policy-driven.

---

# 122. No universal goodwill formula

PyAccountingKit n'impose pas :

```text
one universal goodwill equation
```

sans policy/référentiel.

---

# 123. Negative goodwill / bargain purchase

Préparé comme résultat policy-driven.

---

# 124. Non-Controlling Interests

Objet :

```text
NonControllingInterest
```

---

# 125. `NonControllingInterest`

```text
entity_id
period_id
ownership_percentage
opening_balance
share_of_result
share_of_other_changes
dividends?
closing_balance
policy_trace
```

---

# 126. NCI != ownership edge

L'ownership edge est une donnée de structure.

Le NCI est un résultat de consolidation.

---

# 127. `NCIAllocationPolicy`

```text
basis

measurement_method

result_allocation

equity_allocation

rounding

version
```

---

# 128. No universal NCI measurement method

---

# 129. Parent result attribution

Le moteur peut produire :

```text
GroupResultAttribution
```

---

# 130. `GroupResultAttribution`

```text
total_consolidated_result

parent_share

nci_share
```

---

# 131. Group Equity

Read model :

```text
ConsolidatedEquity
```

---

# 132. Group equity does not equal simple sum

Il intègre :

```text
eliminations

translation differences

NCI

consolidation adjustments
```

---

# 133. Consolidation adjustments

Objet :

```text
ConsolidationAdjustment
```

---

# 134. `ConsolidationAdjustment`

```text
id
group_id
period_id
entity_id?
adjustment_type
reason
source_refs
proposed_entry
status
review
```

---

# 135. Adjustment types

```text
POLICY_ALIGNMENT

CLASSIFICATION

MEASUREMENT

PRESENTATION

ACQUISITION

TAX_EFFECT

MANUAL

CUSTOM
```

---

# 136. Adjustment != correction

Si l'entité source est erronée :

```text
Entity Accounting Correction
```

devrait idéalement être réalisée dans la comptabilité individuelle.

---

# 137. Group-only adjustment

Si le traitement est propre au groupe :

```text
ConsolidationAdjustment
```

---

# 138. `AdjustmentOrigin`

```text
GROUP_ONLY

ENTITY_ERROR_TEMPORARILY_COMPENSATED

REGULATORY_ALIGNMENT

POLICY_ALIGNMENT

MIGRATION

OTHER
```

---

# 139. Entity error compensated

Doit être clairement marqué.

---

# 140. No hidden permanent workaround

---

# 141. Tax effects

Le modèle peut prévoir :

```text
ConsolidationTaxEffect
```

mais P2.1 ne définit pas un moteur fiscal complet.

---

# 142. Deferred tax

Préparé via port/policy si nécessaire.

---

# 143. `ConsolidationTaxPolicy`

Extension future.

---

# 144. Opening consolidation

N+1 doit pouvoir repartir d'un :

```text
ConsolidationOpeningSnapshot
```

ou reconstruire à partir des sources.

---

# 145. Opening principle

Les adjustments récurrents peuvent être :

```text
carried forward

recomputed

reversed
```

selon policy.

---

# 146. `ConsolidationAdjustmentCarryForwardPolicy`

```text
NO_CARRY

CARRY_FORWARD

RECOMPUTE

REVERSE_AND_REBUILD

CUSTOM
```

---

# 147. Period close

Le workflow groupe :

```text
OPEN
    ↓
COLLECTING
    ↓
ADJUSTING
    ↓
REVIEW
    ↓
CLOSED
```

---

# 148. Consolidation Run

Aggregate Root :

```text
ConsolidationRun
|
+-- id
+-- group_id
+-- period_id
+-- scope_version
+-- group_policy_version
+-- group_chart_version
+-- status
+-- stages
+-- source_packages
+-- control_runs
+-- snapshot_ref?
+-- revision
```

---

# 149. Run status

```text
CREATED

COLLECTING

MAPPING

TRANSLATING

MATCHING

ADJUSTING

ELIMINATING

CALCULATING_NCI

VALIDATING

READY_TO_CLOSE

CLOSED

FAILED

SUPERSEDED
```

---

# 150. Consolidation pipeline

```text
1. resolve scope

2. collect entity packages

3. validate package completeness

4. map local accounts to group chart

5. align policies

6. translate currencies

7. build pre-elimination group trial balance

8. match intercompany positions

9. create/review eliminations

10. calculate investment/equity adjustments

11. calculate NCI

12. apply remaining consolidation adjustments

13. build consolidated trial balance

14. run controls

15. build consolidated statements

16. publish consolidation snapshot
```

---

# 151. Staged durable workflow

Ne pas garder toute la consolidation dans une seule DB transaction.

---

# 152. Transaction scope

Chaque stage critique utilise :

```text
short UnitOfWork
```

---

# 153. Final close atomicity

Le passage :

```text
READY_TO_CLOSE
    ->
CLOSED
```

doit être atomique.

---

# 154. Source package revisions

Le `ConsolidationRun` doit pinner :

```text
exact package versions
```

---

# 155. Source package change

Si une entité resoumet :

```text
new package version
```

le run devient potentiellement :

```text
STALE
```

---

# 156. `ConsolidationFreshness`

```text
CURRENT

STALE

SUPERSEDED

INDETERMINATE
```

---

# 157. Scope change

Si le scope change pendant un run :

```text
run stale
```

sauf policy explicite.

---

# 158. Group policy change

Même principe.

---

# 159. Group chart change

Même principe.

---

# 160. Currency snapshot change

Même principe.

---

# 161. `ConsolidationSnapshot`

Aggregate immutable :

```text
ConsolidationSnapshot
|
+-- id
+-- group_id
+-- period_id
+-- scope_snapshot
+-- source_package_refs
+-- group_chart_version
+-- group_policy_version
+-- currency_translation_snapshot
+-- intercompany_match_refs
+-- consolidation_entry_refs
+-- consolidated_trial_balance
+-- statement_snapshot_refs
+-- nci_summary
+-- control_run_refs
+-- generated_at
+-- checksum
+-- status
```

---

# 162. Snapshot status

```text
DRAFT

VALIDATED

PUBLISHED

SUPERSEDED

WITHDRAWN
```

---

# 163. Published snapshot immutable

Toujours.

---

# 164. Snapshot supersession

Une correction produit :

```text
new snapshot
```

et non mutation de l'ancien.

---

# 165. Reopen

Un groupe consolidé peut être réouvert via :

```text
ReopenConsolidationPeriod
```

---

# 166. Reopen consequence

```text
new ConsolidationRun revision
new snapshot
old snapshot preserved
```

---

# 167. Source entity reopen

Si une entité source rouvre sa période :

```text
entity TrialBalanceSnapshot becomes stale/superseded
```

les consolidations downstream deviennent :

```text
STALE
```

---

# 168. No automatic recalc

---

# 169. Drill-down

```text
Consolidated Statement Line
    ↓
Consolidated Trial Balance Line
    ↓
Group Account
    ↓
Translated Entity Balance
    ↓
Company Account
    ↓
Entity Trial Balance
    ↓
General Ledger
    ↓
JournalEntryLine
```

---

# 170. Elimination drill-down

```text
Consolidated Balance
    ↓
ConsolidationEntry
    ↓
IntercompanyMatch / Adjustment
    ↓
Entity source lines
```

---

# 171. `ConsolidationDrilldownQuery`

```python
class ConsolidationDrilldownQuery(Protocol):
    def drilldown(
        self,
        snapshot_id,
        target_ref,
    ) -> "ConsolidationDrilldownResult":
        ...
```

---

# 172. Provenance edge types

```text
SOURCE_ENTITY_BALANCE

GROUP_MAPPING

CURRENCY_TRANSLATION

POLICY_ALIGNMENT

INTERCOMPANY_MATCH

ELIMINATION

NCI_ALLOCATION

CONSOLIDATION_ADJUSTMENT

STATEMENT_MAPPING
```

---

# 173. Lineage graph

Le modèle doit permettre de distinguer :

```text
origin contribution

adjustment contribution

elimination contribution
```

---

# 174. Contribution model

```text
ConsolidationContribution
|
+-- source_type
+-- source_ref
+-- amount
+-- sign
+-- transformation
```

---

# 175. Controls - scope

```text
CONSOLIDATION_SCOPE_VALID

OWNERSHIP_GRAPH_VALID

CONTROL_DECISIONS_COMPLETE

CONSOLIDATION_METHODS_ASSIGNED
```

---

# 176. Controls - packages

```text
ENTITY_PACKAGES_COMPLETE

ENTITY_PACKAGES_CURRENT

ENTITY_TRIAL_BALANCES_BALANCED

GROUP_CHART_MAPPING_COMPLETE
```

---

# 177. Controls - currency

```text
CURRENCY_RATES_COMPLETE

CURRENCY_TRANSLATION_RECONCILED

TRANSLATION_DIFFERENCE_ACCOUNT_CONFIGURED
```

---

# 178. Controls - intercompany

```text
INTERCOMPANY_POSITIONS_MATCHED

INTERCOMPANY_DIFFERENCES_REVIEWED

INTERCOMPANY_ELIMINATIONS_COMPLETE
```

---

# 179. Controls - investments/NCI

```text
INVESTMENT_ELIMINATION_COMPLETE

NCI_RECONCILED

GROUP_RESULT_ATTRIBUTION_RECONCILED
```

---

# 180. Controls - balance

```text
CONSOLIDATED_TRIAL_BALANCE_BALANCED

CONSOLIDATED_BALANCE_SHEET_BALANCED

CONSOLIDATED_CASHFLOW_RECONCILED
```

---

# 181. Controls - provenance

```text
CONSOLIDATION_SOURCE_PACKAGES_PINNED

CONSOLIDATION_POLICY_SNAPSHOT_PRESENT

CONSOLIDATION_CURRENCY_SNAPSHOT_PRESENT

CONSOLIDATION_LINEAGE_COMPLETE
```

---

# 182. Gate

```text
CONSOLIDATION_CLOSE_GATE
```

---

# 183. Suggested blockers

Policy configurable.

Exemples :

```text
missing entity package

unbalanced source TB

mapping incomplete

required FX rate missing

blocking intercompany difference

consolidated TB unbalanced

NCI unreconciled
```

---

# 184. Control vs adjustment

Un control détecte.

Un adjustment comptabilise.

---

# 185. Control vs intercompany match

Un match rapproche.

Un control vérifie la qualité du matching.

---

# 186. Audit events

```text
GROUP_CREATED

CONSOLIDATION_SCOPE_CREATED

CONSOLIDATION_SCOPE_ACTIVATED

CONSOLIDATION_ENTITY_ADDED

OWNERSHIP_UPDATED

CONTROL_DECISION_REVIEWED

GROUP_CHART_MAPPING_VALIDATED

ENTITY_PACKAGE_SUBMITTED

ENTITY_PACKAGE_ACCEPTED

CONSOLIDATION_RUN_STARTED

CURRENCY_TRANSLATION_EXECUTED

INTERCOMPANY_MATCH_CREATED

INTERCOMPANY_ELIMINATION_POSTED

CONSOLIDATION_ADJUSTMENT_POSTED

NCI_CALCULATED

CONSOLIDATION_RUN_CLOSED

CONSOLIDATION_PERIOD_REOPENED

CONSOLIDATION_SNAPSHOT_PUBLISHED
```

---

# 187. Domain events

```text
ConsolidationScopeActivated

EntityReportingPackageAccepted

IntercompanyMatched

ConsolidationEntryPosted

ConsolidationRunClosed

ConsolidationSnapshotPublished
```

---

# 188. Audit != Domain Event

Même principe transversal.

---

# 189. Reproducibility

Un snapshot doit pinner :

```text
framework version

scope version

ownership graph snapshot

control policy version

method policy version

group chart version

mapping set versions

group accounting policy version

source entity snapshot IDs

currency rate snapshot

intercompany matching policy version

elimination policy version

NCI policy version

statement definitions

control definitions
```

---

# 190. `ConsolidationReproducibilityEnvelope`

```text
ConsolidationReproducibilityEnvelope
|
+-- framework_version
+-- scope_snapshot
+-- source_package_snapshots
+-- group_chart_snapshot
+-- policy_snapshots
+-- currency_snapshot
+-- control_versions
+-- mapping_versions
+-- output_checksum
```

---

# 191. Replay

Same envelope :

```text
should reproduce same semantic output
```

---

# 192. Current-engine comparison

Historical snapshot can be recalculated under new engine for comparison.

But :

```text
historical published snapshot remains unchanged
```

---

# 193. Comparison object

```text
ConsolidationReplayComparison
|
+-- historical_snapshot
+-- current_engine_result
+-- differences
+-- classification
```

---

# 194. Difference classification

```text
NONE

EXPECTED_VERSION_DIFFERENCE

POLICY_DIFFERENCE

MAPPING_DIFFERENCE

ENGINE_REGRESSION

SOURCE_DIFFERENCE
```

---

# 195. Multi-entity isolation

Every entity balance contribution must carry :

```text
entity_id
```

---

# 196. Counterparty dimension

Intercompany lines should carry :

```text
counterparty_entity_id
```

where available.

---

# 197. Missing counterparty

Can produce :

```text
INTERCOMPANY_COUNTERPARTY_MISSING
```

warning/error by policy.

---

# 198. Entity-specific mapping

Same local account code can map differently by entity.

---

# 199. Group code stability

Group account codes are versioned.

---

# 200. Group chart migration

New version :

```text
GroupChartMigrationPlan
```

---

# 201. Mapping versioning

No silent mapping replacement.

---

# 202. Mapping effective dates

Required.

---

# 203. Ownership versioning

Ownership changes are effective-dated.

---

# 204. Historical ownership

Never overwritten.

---

# 205. Intercompany counterparty binding

```text
IntercompanyPartnerBinding
```

can link external/business-partner IDs to group entities.

---

# 206. Subledger integration

If P1.4 provides :

```text
BusinessPartner.related_entity_ref
```

consolidation can use it as candidate evidence.

---

# 207. Candidate only

Unless validated.

---

# 208. Intercompany open items

Future/optional source :

```text
SubledgerSnapshot
```

---

# 209. Reconciliation bounded context

P2.2 will generalize matching/reconciliation.

Consolidation P2.1 should therefore define interfaces, not duplicate all reconciliation infrastructure.

---

# 210. `IntercompanyReconciliationPort`

```python
class IntercompanyReconciliationPort(Protocol):
    def reconcile(...):
        ...
```

---

# 211. But P2.1 has a minimal native match model

Required to function independently.

---

# 212. Consolidated Statements

`ConsolidatedFinancialStatementEngine` can reuse the generic statement engine against :

```text
ConsolidatedTrialBalance
```

---

# 213. Prefer reuse

Avoid a second statement formula engine.

---

# 214. Input adapter

Provide :

```text
ConsolidatedTrialBalanceSource
```

compatible with the generic statements engine.

---

# 215. Group statement definitions

Can differ from entity definitions.

---

# 216. `GroupStatementProfile`

```text
statement_definition_set

group_mapping_set

presentation_currency

comparison_policy
```

---

# 217. Consolidated report snapshot

Can be :

```text
ReportSnapshot
```

with source type :

```text
CONSOLIDATED_TRIAL_BALANCE
```

---

# 218. No duplicate reporting model

---

# 219. Financial Analysis

Consolidated statements can feed :

```text
Financial Analysis
```

---

# 220. Group analysis

```text
Consolidated ReportSnapshot
    ↓
Financial Analysis
```

---

# 221. No group ratios inside consolidation core

Unless needed for controls.

---

# 222. Comparative periods

Consolidation can compare :

```text
N

N-1
```

but comparability must consider :

```text
scope changes

currency policy changes

group chart changes
```

---

# 223. `ConsolidationComparabilityAssessment`

```text
scope_changed

policy_changed

currency_changed

mapping_changed

comparable_status
```

---

# 224. Comparability status

```text
COMPARABLE

PARTIALLY_COMPARABLE

NOT_COMPARABLE
```

---

# 225. Scope change disclosure

Can be included as metadata.

---

# 226. Pro forma

Out of P2.1 core.

---

# 227. Budget consolidation

Out of P2.1.

---

# 228. Forecast consolidation

Out of P2.1.

---

# 229. Consolidation source data quality

Can expose :

```text
ConsolidationDataQualitySummary
```

---

# 230. Data quality dimensions

```text
package completeness

mapping completeness

FX completeness

intercompany matching coverage

adjustment review completeness

lineage completeness
```

---

# 231. `ConsolidationDataQualitySummary`

Read-only.

---

# 232. Manual adjustments

Allowed but controlled.

---

# 233. Manual adjustment requirement

```text
reason

actor

approval?

source evidence

reversal/carry-forward policy
```

---

# 234. `ManualConsolidationAdjustmentPolicy`

---

# 235. Approval

P2.1 prepares :

```text
reviewer

approver
```

without defining RBAC.

---

# 236. Sign-off

Reuse `SignOff` architecture from Controls/Audit.

---

# 237. Closing package

A published consolidation can produce :

```text
ConsolidationEvidenceBundle
```

---

# 238. `ConsolidationEvidenceBundle`

```text
scope snapshot

ownership snapshot

entity packages

mapping snapshots

currency snapshot

intercompany matches

consolidation entries

control runs

NCI calculations

consolidated TB

report snapshots

checksums

signoffs
```

---

# 239. Evidence bundle immutable

---

# 240. Outbox

Final close/publication can emit integration event via transactional outbox.

---

# 241. No network calls in transaction

Même règle persistence.

---

# 242. Repositories

```text
GroupRepository

ConsolidationScopeRepository

ConsolidationPeriodRepository

EntityReportingPackageRepository

GroupChartRepository

GroupAccountMappingRepository

ConsolidationRunRepository

ConsolidationEntryRepository

IntercompanyMatchRepository

ConsolidationSnapshotRepository
```

---

# 243. Query ports

```text
OwnershipGraphQuery

GroupMappingQuery

EntityPackageQuery

ConsolidationLedgerQuery

ConsolidatedTrialBalanceQuery

IntercompanyPositionQuery

ConsolidationDrilldownQuery
```

---

# 244. Other ports

```text
TrialBalanceSnapshotQuery

ReportSnapshotQuery

ExchangeRateProvider

AccountingReferenceProvider

IntercompanyReconciliationPort

ArtifactStorePort

AuditPort

Clock

UnitOfWork
```

---

# 245. `ExchangeRateProvider`

```python
class ExchangeRateProvider(Protocol):
    def get_rate(...):
        ...
```

---

# 246. Provider result must be snapshottable

---

# 247. No provider live-call during published replay

---

# 248. Application Services

```text
CreateGroup

CreateConsolidationScope

ActivateConsolidationScope

RegisterOwnership

EvaluateControl

AssignConsolidationMethod

CreateConsolidationPeriod

SubmitEntityReportingPackage

AcceptEntityReportingPackage

MapEntityAccountsToGroup

TranslateEntityPackage

RunIntercompanyMatching

CreateEliminationCandidate

PostConsolidationEntry

CalculateNCI

BuildConsolidatedTrialBalance

RunConsolidationControls

BuildConsolidatedStatements

CloseConsolidationRun

PublishConsolidationSnapshot

ReopenConsolidationPeriod
```

---

# 249. API publique future

Sous-façade :

```text
accounting.consolidation
```

---

# 250. API - group

```python
group = accounting.consolidation.create_group(
    code="GROUP_A",
    reporting_currency="EUR",
)
```

---

# 251. API - scope

```python
scope = accounting.consolidation.create_scope(
    group_id=group.id,
    effective_from=date(2026, 1, 1),
)
```

---

# 252. API - entity

```python
accounting.consolidation.add_entity(
    scope_id=scope.id,
    entity_id=subsidiary.id,
    consolidation_method="FULL",
    ownership_interest=Decimal("0.80"),
    control_interest=Decimal("1.00"),
)
```

---

# 253. API - package

```python
package = accounting.consolidation.submit_package(
    group_id=group.id,
    period_id=period.id,
    entity_id=subsidiary.id,
    trial_balance_snapshot_id=tb.id,
)
```

---

# 254. API - run

```python
run = accounting.consolidation.start(
    group_id=group.id,
    period_id=period.id,
)
```

---

# 255. API - match

```python
matches = accounting.consolidation.match_intercompany(
    run_id=run.id,
)
```

---

# 256. API - eliminate

```python
entry = accounting.consolidation.post_elimination(
    run_id=run.id,
    candidate_id=candidate.id,
)
```

---

# 257. API - consolidated TB

```python
tb = accounting.consolidation.trial_balance(
    run_id=run.id,
)
```

---

# 258. API - publish

```python
snapshot = accounting.consolidation.publish(
    run_id=run.id,
)
```

---

# 259. API no ORM leakage

Toujours.

---

# 260. Package cible

```text
src/pyaccountingkit/domain/consolidation/
|
+-- group/
|   +-- group.py
|   +-- scope.py
|   +-- ownership.py
|   +-- control.py
|
+-- periods/
|   +-- consolidation_period.py
|
+-- packages/
|   +-- reporting_package.py
|
+-- chart/
|   +-- group_chart.py
|   +-- mappings.py
|
+-- currency/
|   +-- translation_policy.py
|   +-- translation_snapshot.py
|
+-- entries/
|   +-- consolidation_entry.py
|   +-- consolidation_line.py
|
+-- intercompany/
|   +-- position.py
|   +-- match.py
|   +-- elimination.py
|
+-- investments/
|   +-- acquisition_context.py
|   +-- investment_elimination.py
|   +-- goodwill.py
|   +-- nci.py
|
+-- adjustments/
|   +-- adjustment.py
|
+-- runs/
|   +-- consolidation_run.py
|
+-- snapshots/
|   +-- consolidation_snapshot.py
|
+-- controls/
|   +-- definitions.py
|
+-- queries/
    +-- drilldown.py
```

---

# 261. Application package

```text
src/pyaccountingkit/application/consolidation/
|
+-- create_group.py
+-- create_scope.py
+-- register_ownership.py
+-- submit_package.py
+-- translate_package.py
+-- match_intercompany.py
+-- create_eliminations.py
+-- post_adjustment.py
+-- calculate_nci.py
+-- build_trial_balance.py
+-- build_statements.py
+-- close_run.py
+-- publish_snapshot.py
+-- reopen_period.py
```

---

# 262. Persistence

Tables possibles :

```text
group

consolidation_scope

consolidation_entity

ownership_edge

consolidation_period

entity_reporting_package

group_chart

group_account

group_account_mapping

consolidation_run

consolidation_entry

consolidation_line

intercompany_match

consolidation_snapshot
```

---

# 263. Append-oriented objects

```text
accepted reporting package

posted consolidation entry

published consolidation snapshot

audit event

evidence bundle
```

---

# 264. Mutable/versioned objects

```text
draft scope

draft mapping set

draft consolidation run

draft adjustment
```

---

# 265. Optimistic concurrency

Recommended for :

```text
ConsolidationScope

EntityReportingPackage

ConsolidationRun

ConsolidationEntry

GroupChart
```

---

# 266. Pessimistic locking

Useful for :

```text
final close

posting elimination

NCI finalization

package acceptance
```

adapter-dependent.

---

# 267. Idempotence

Critical commands :

```text
submit package

post elimination

publish snapshot

close run
```

---

# 268. Idempotency scope

```text
group
period
command type
business key
```

---

# 269. Duplicate elimination

Must not post twice.

---

# 270. `EliminationIdempotencyKey`

Can derive from :

```text
source match
elimination type
period
policy version
```

---

# 271. Sequence

ConsolidationEntry may use independent numbering.

---

# 272. No entity journal sequence reuse

---

# 273. Performance

Potential large volumes :

```text
many entities
many accounts
many IC transactions
multi-period
```

---

# 274. Performance principles

```text
batch mappings

batch FX translation

aggregate positions before detailed matching

reconcile totals before drill-down

materialize snapshots where useful
```

---

# 275. Intercompany matching scale

Two modes :

```text
SUMMARY

DETAIL
```

---

# 276. `IntercompanyMatchingGranularity`

```text
ACCOUNT

DOCUMENT

TRANSACTION

OPEN_ITEM

CUSTOM
```

---

# 277. P2.1 default

```text
ACCOUNT
```

minimum viable.

---

# 278. Detailed matching

Can use subledgers/reconciliation later.

---

# 279. Observability

Metrics :

```text
consolidation_runs_total

consolidation_run_duration

entity_packages_submitted_total

group_mapping_incomplete_total

currency_translation_total

intercompany_matches_total

intercompany_unmatched_amount

elimination_entries_total

consolidation_adjustments_total

nci_calculations_total

consolidation_replay_mismatch_total
```

---

# 280. Logs

Context :

```text
group_id

period_id

run_id

entity_id

counterparty_entity_id

package_id

entry_id

correlation_id
```

---

# 281. No full financial payload in logs

---

# 282. Tracing spans

```text
resolve_scope

collect_packages

map_group_accounts

translate_currency

match_intercompany

build_eliminations

calculate_nci

build_consolidated_tb

run_controls

build_statements

publish_snapshot
```

---

# 283. Error taxonomy

```text
ConsolidationError
|
+-- GroupNotFoundError
+-- ConsolidationScopeNotFoundError
+-- ConsolidationScopeInvalidError
+-- OwnershipGraphInvalidError
+-- ControlDecisionRequiredError
+-- ConsolidationMethodNotConfiguredError
+-- EntityReportingPackageMissingError
+-- EntityReportingPackageStaleError
+-- GroupChartMappingIncompleteError
+-- CurrencyRateMissingError
+-- CurrencyTranslationError
+-- IntercompanyMatchError
+-- IntercompanyDifferenceUnresolvedError
+-- EliminationCandidateInvalidError
+-- DuplicateEliminationError
+-- ConsolidationEntryNotBalancedError
+-- NCICalculationError
+-- ConsolidationControlFailedError
+-- ConsolidationSnapshotIntegrityError
+-- ConsolidationConcurrencyConflictError
```

---

# 284. Fail-closed

Doivent échouer :

```text
missing required entity package

ambiguous consolidation method

missing group account mapping

missing mandatory FX rate

unresolved blocking intercompany difference

unbalanced consolidation entry

invalid ownership graph

stale source package at close

missing NCI policy when required
```

---

# 285. Warnings

```text
minor IC difference within review tolerance

mapping candidate available

scope changed vs previous period

policy changed vs previous period

comparison partially comparable
```

---

# 286. Golden tests - group mapping

Fixture :

```text
Entity A local accounts
Entity B local accounts
    ->
Group Chart
```

Expected deterministic aggregated balances.

---

# 287. Golden - currency translation

Pinned rates.

Expected exact Decimal outputs.

---

# 288. Golden - IC receivable/payable

```text
A receivable from B = 100

B payable to A = 100

Expected:
    match = 100
    elimination = 100
    net group effect = 0
```

---

# 289. Golden - unmatched IC

```text
A receivable = 100

B payable = 95

Expected:
    match 95
    difference 5
    review/control finding
```

---

# 290. Golden - IC revenue/expense

```text
A revenue to B = 200

B expense from A = 200

Expected:
    elimination removes 200 revenue
    elimination removes 200 expense
```

---

# 291. Golden - NCI

Example :

```text
Parent effective interest = 80%

Subsidiary result = 100

Policy:
    allocate result by ownership

Expected:
    parent share = 80
    NCI share = 20
```

Ce fixture teste la mécanique configurée, pas une règle universelle.

---

# 292. Golden - scope change

N :

```text
A + B
```

N+1 :

```text
A + B + C
```

Expected :

```text
comparability assessment flags scope change
```

---

# 293. Golden - entity reopen

```text
Consolidation snapshot C1
depends on Entity A TB1

Entity A reopened
TB2 created

Expected:
    C1 immutable
    C1 stale
    new consolidation run required
```

---

# 294. Property tests

```text
ConsolidationEntry debit == credit

Translated balance deterministic

Elimination + source IC pair removes group internal effect

Snapshot checksum deterministic

No entity ledger mutation

Group mapping preserves total under pure many-to-one mappings

NCI + parent attribution = total attributed amount
```

---

# 295. Concurrency tests

```text
double package acceptance

double elimination posting

close run vs package resubmission

close run vs mapping change

double publish snapshot

reopen vs publish
```

---

# 296. Contract tests - FX provider

```text
deterministic snapshot

rate identity

missing rate behavior

Decimal preservation
```

---

# 297. Contract tests - reconciliation port

```text
same inputs
same match semantics
```

---

# 298. Replay tests

Same :

```text
scope
packages
mappings
policies
FX rates
entries
```

=> same consolidation checksum.

---

# 299. Migration tests

Schema migration must preserve :

```text
published consolidation snapshots

ownership history

scope versions

posted consolidation entries
```

---

# 300. Testing matrix

| Capability | Unit | Property | Integration | Concurrency | Golden | Replay |
|---|---:|---:|---:|---:|---:|---:|
| Scope | oui | oui | oui | oui | oui | oui |
| Ownership | oui | oui | oui | - | oui | oui |
| Group mapping | oui | oui | oui | oui | oui | oui |
| FX translation | oui | oui | oui | - | oui | oui |
| IC matching | oui | oui | oui | oui | oui | oui |
| Eliminations | oui | oui | oui | oui | oui | oui |
| NCI | oui | oui | oui | - | oui | oui |
| Consolidated TB | oui | oui | oui | oui | oui | oui |
| Snapshot | oui | oui | oui | oui | oui | oui |

---

# 301. Relationship with Reference Data

Le Group Chart peut être lié à :

```text
ReferenceAccount
```

ou :

```text
GroupConcept
```

selon profil.

---

# 302. But no automatic cross-standard conversion

Toujours respecter les règles de `19_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX`.

---

# 303. Crosswalks

Peuvent aider :

```text
candidate group mappings
```

pas :

```text
automatic semantic conversion
```

---

# 304. Regulatory consolidation profile

Future object :

```text
ConsolidationRegulatoryProfile
```

---

# 305. Profile responsibilities

```text
scope policy
method policy
translation policy
NCI policy
goodwill policy
statement profile
```

---

# 306. But not hardcoded in core

---

# 307. Policy snapshot

Chaque run pinne :

```text
ConsolidationPolicySnapshot
```

---

# 308. `ConsolidationPolicySnapshot`

```text
scope policy version

method policy version

currency translation policy version

intercompany policy version

elimination policy version

NCI policy version

goodwill policy version
```

---

# 309. Goodwill boundary

Goodwill peut être stocké/calculé comme :

```text
ConsolidationMeasurementResult
```

---

# 310. Goodwill impairment

Future integration avec :

```text
Impairment Policy
```

---

# 311. No entity-level automatic posting

---

# 312. Equity method boundary

L'equity method peut produire :

```text
ConsolidationEntry
```

dans le group ledger.

---

# 313. Not entity ledger

---

# 314. Proportional method boundary

Même principe.

---

# 315. Full method boundary

Même principe.

---

# 316. Consolidation engine interface

```python
class ConsolidationEngine:
    def build(
        self,
        request: "ConsolidationBuildRequest",
    ) -> "ConsolidationBuildResult":
        ...
```

---

# 317. `ConsolidationBuildRequest`

```text
group_id

period_id

scope_version

source_packages

group_chart

policy_snapshot

currency_snapshot

matching_policy
```

---

# 318. `ConsolidationBuildResult`

```text
translated_balances

intercompany_matches

elimination_candidates

posted_adjustment_refs

nci_summary

consolidated_trial_balance

control_findings

warnings
```

---

# 319. Strictness

```text
PREVIEW

VALIDATION

PUBLICATION
```

---

# 320. Preview

Peut montrer :

```text
missing mappings

candidate eliminations

unresolved IC differences
```

---

# 321. Publication

Fail closed.

---

# 322. Manual journal

L'API peut permettre :

```text
manual consolidation adjustment
```

avec controls.

---

# 323. No direct arbitrary database update

---

# 324. Closing evidence

Publication exige :

```text
control gate pass

source packages pinned

scope pinned

currency pinned

all posted consolidation entries immutable
```

---

# 325. Comparative reporting

N/N-1 uses separate snapshots.

---

# 326. Historical preservation

Never rewrite N-1 under N policy unless explicit restatement.

---

# 327. Restatement

Future capability.

---

# 328. `ConsolidationRestatementPlan`

P2 extension.

---

# 329. Segment reporting

Out of core P2.1.

---

# 330. Cash flow consolidation

Reuses generic cash flow statement engine after elimination.

---

# 331. Direct vs indirect cash flow

Policy/reporting definition concern.

---

# 332. Consolidated cash flow reconciliation

Control :

```text
CONSOLIDATED_CASHFLOW_RECONCILED
```

---

# 333. Group opening balance

Can use previous published consolidation snapshot.

---

# 334. Previous snapshot dependency

Pinned explicitly.

---

# 335. First consolidation

Requires :

```text
initial consolidation setup
```

---

# 336. `InitialConsolidationContext`

```text
opening ownership

opening equity

investment carrying amounts

initial FX

initial adjustments
```

---

# 337. No implicit opening construction

---

# 338. Data import

Legacy consolidation data may be imported via Accounting Imports extension.

---

# 339. `ConsolidationImportAdapter`

Future.

---

# 340. Migration provenance

Historical consolidated balances without detail can be marked :

```text
PARTIAL_PROVENANCE
```

---

# 341. No invented eliminations

---

# 342. Consolidation completeness

```text
COMPLETE

PARTIAL

UNKNOWN
```

---

# 343. `ConsolidationCompleteness`

Affects controls/publication.

---

# 344. Group-wide materiality

Future/optional :

```text
ConsolidationMaterialityPolicy
```

---

# 345. Materiality != balancing tolerance

Distinct.

---

# 346. `BalancingTolerancePolicy`

May exist for candidate review only.

---

# 347. Universal invariant remains exact double entry

Posted consolidation entries should balance exactly after rounding rules.

---

# 348. Rounding

Policy-driven.

---

# 349. Translation rounding

Can create explicit balancing line if policy allows.

---

# 350. `ConsolidationRoundingPolicy`

```text
calculation_precision

presentation_precision

balancing_role

version
```

---

# 351. No float

---

# 352. ADRs

| ID | Décision |
|---|---|
| ADR-CON-001 | `Consolidation` est un bounded context distinct de la comptabilité individuelle |
| ADR-CON-002 | La consolidation ne modifie jamais les ledgers individuels |
| ADR-CON-003 | `TrialBalanceSnapshot` est la source privilégiée pour la consolidation comptable |
| ADR-CON-004 | `Group` est distinct de `AccountingEntity` |
| ADR-CON-005 | Le périmètre de consolidation est versionné |
| ADR-CON-006 | Ownership et Control sont des concepts distincts |
| ADR-CON-007 | Le contrôle est policy-driven, pas déduit universellement d'un pourcentage |
| ADR-CON-008 | Les méthodes FULL/PROPORTIONATE/EQUITY sont configurables par policy |
| ADR-CON-009 | Le choix de méthode n'est pas un invariant réglementaire universel du core |
| ADR-CON-010 | Les dates d'entrée/sortie de périmètre sont effectives et historisées |
| ADR-CON-011 | `EntityReportingPackage` fige la source individuelle acceptée |
| ADR-CON-012 | Un package accepté est immutable |
| ADR-CON-013 | `GroupChartOfAccounts` est distinct des Company Charts |
| ADR-CON-014 | Les mappings local->groupe sont explicites et versionnés |
| ADR-CON-015 | Aucun prefix mapping universel n'est autorisé |
| ADR-CON-016 | Les split mappings exigent une règle d'allocation explicite |
| ADR-CON-017 | La devise fonctionnelle d'une entité est distincte de la devise de présentation groupe |
| ADR-CON-018 | Currency Translation est distincte de la comptabilisation FX transactionnelle |
| ADR-CON-019 | Les règles de taux de conversion sont policy-driven |
| ADR-CON-020 | Les taux utilisés par un snapshot publié sont pinés |
| ADR-CON-021 | Les différences de conversion utilisent des rôles groupe, pas des codes hardcodés |
| ADR-CON-022 | L'homogénéisation des policies utilise des ConsolidationAdjustments |
| ADR-CON-023 | Un retraitement groupe ne modifie pas la comptabilité individuelle |
| ADR-CON-024 | `ConsolidationEntry` possède son propre ledger |
| ADR-CON-025 | Les ConsolidationEntries respectent la partie double |
| ADR-CON-026 | Matching intercompany et élimination sont distincts |
| ADR-CON-027 | Les différences intercompany sont explicites et reviewables |
| ADR-CON-028 | Une tolerance de matching ne déclenche jamais un write-off implicite |
| ADR-CON-029 | Les éliminations sont générées depuis des candidats validés ou policies explicites |
| ADR-CON-030 | Les profits internes non réalisés sont policy-driven |
| ADR-CON-031 | Investment elimination est distincte des écritures individuelles d'investissement |
| ADR-CON-032 | Goodwill est un résultat de mesure policy-driven |
| ADR-CON-033 | NCI est un résultat de consolidation, distinct de l'ownership graph |
| ADR-CON-034 | La méthode de mesure NCI n'est pas hardcodée dans le core |
| ADR-CON-035 | Les Group Result Attributions doivent se réconcilier |
| ADR-CON-036 | Les ajustements groupe sont typés et tracés |
| ADR-CON-037 | Une erreur de comptabilité individuelle n'est pas silencieusement absorbée par une adjustment permanente |
| ADR-CON-038 | Le workflow de consolidation est staged et durable |
| ADR-CON-039 | Les stages n'utilisent pas une transaction DB unique longue |
| ADR-CON-040 | La fermeture finale du run est atomique |
| ADR-CON-041 | Les versions de packages sont pinées dans le run |
| ADR-CON-042 | Un changement de source/policy/scope peut rendre le run stale |
| ADR-CON-043 | Un ConsolidationSnapshot publié est immutable |
| ADR-CON-044 | Un reopen crée une nouvelle révision/snapshot |
| ADR-CON-045 | Un reopen source rend les consolidations downstream stale |
| ADR-CON-046 | Le drill-down consolidé doit atteindre les JournalEntryLines individuelles |
| ADR-CON-047 | Les contributions source, adjustment et elimination sont distinguées dans la lineage |
| ADR-CON-048 | Les controls de consolidation sont distincts des adjustments |
| ADR-CON-049 | `CONSOLIDATION_CLOSE_GATE` est policy-driven |
| ADR-CON-050 | La reproductibilité pinne scope, ownership, mappings, policies, FX et sources |
| ADR-CON-051 | Le replay historique ne modifie jamais un snapshot publié |
| ADR-CON-052 | Les counterparty dimensions sont conservées lorsque disponibles |
| ADR-CON-053 | La réconciliation avancée intercompany peut être déléguée au bounded context Reconciliation |
| ADR-CON-054 | Le moteur d'états financiers générique est réutilisé pour les comptes consolidés |
| ADR-CON-055 | Financial Analysis reste downstream de la consolidation |
| ADR-CON-056 | Les changements de périmètre affectent la comparabilité |
| ADR-CON-057 | Les manual adjustments nécessitent raison, provenance et audit |
| ADR-CON-058 | Les sign-offs réutilisent l'architecture Controls/Audit |
| ADR-CON-059 | Les snapshots de consolidation disposent d'un EvidenceBundle |
| ADR-CON-060 | Les finalizations peuvent utiliser Transactional Outbox |
| ADR-CON-061 | Les ConsolidationEntries ont une séquence distincte des journaux individuels |
| ADR-CON-062 | Les opérations critiques de consolidation sont idempotentes |
| ADR-CON-063 | Les éliminations ne peuvent pas être postées deux fois |
| ADR-CON-064 | Le matching peut exister à plusieurs granularités |
| ADR-CON-065 | Le mode ACCOUNT constitue le minimum viable P2.1 |
| ADR-CON-066 | Les crosswalks réglementaires ne sont jamais utilisés comme conversions sémantiques automatiques |
| ADR-CON-067 | Un ConsolidationPolicySnapshot est pinner par run |
| ADR-CON-068 | Le Consolidation Engine demeure framework-neutral |
| ADR-CON-069 | Le mode publication fail-closed |
| ADR-CON-070 | Les anciennes consolidations restent conservées avec leur provenance même partielle |

---

# 353. Critères d'acceptation P2.1

```text
[ ] Group défini

[ ] ConsolidationScope défini

[ ] scope versioning défini

[ ] ConsolidationEntity défini

[ ] ownership/control distinction définie

[ ] OwnershipGraph défini

[ ] ControlPolicy défini

[ ] FULL / PROPORTIONATE / EQUITY supportés comme policies

[ ] ConsolidationPeriod défini

[ ] EntityReportingPackage défini

[ ] package accepted immutable

[ ] GroupChartOfAccounts défini

[ ] GroupAccountMapping défini

[ ] split/aggregate mapping préparés

[ ] CurrencyTranslationPolicy défini

[ ] ExchangeRateObservation défini

[ ] CurrencyTranslationSnapshot défini

[ ] TranslatedTrialBalance défini

[ ] GroupAccountingPolicySet défini

[ ] PolicyAlignmentAssessment défini

[ ] ConsolidationEntry défini

[ ] ConsolidationEntry double-entry invariant défini

[ ] ConsolidationLedger défini

[ ] ConsolidatedTrialBalance défini

[ ] IntercompanyPosition défini

[ ] IntercompanyMatch défini

[ ] Matching != Elimination explicite

[ ] IntercompanyDifference défini

[ ] EliminationCandidate défini

[ ] IC balance elimination définie

[ ] IC revenue/expense elimination définie

[ ] unrealized profit architecture définie

[ ] investment elimination préparée

[ ] AcquisitionContext défini

[ ] Goodwill architecture préparée

[ ] NCI défini

[ ] NCI policy-driven

[ ] ConsolidationAdjustment défini

[ ] ConsolidationRun défini

[ ] staged pipeline défini

[ ] ConsolidationSnapshot défini

[ ] published snapshot immutable

[ ] reopen semantics définies

[ ] downstream staleness définie

[ ] drill-down complet défini

[ ] controls/gates définis

[ ] reproducibility envelope défini

[ ] API/ports/repositories définis

[ ] tests unit/property/integration/concurrency/golden/replay définis
```

---

# 354. Ordre d'implémentation recommandé

## CON-00 - Primitives Groupe

```text
Group

ConsolidationPeriod

ConsolidationMethod

OwnershipInterest

ControlInterest
```

---

## CON-01 - Scope & Ownership

```text
ConsolidationScope

ConsolidationEntity

OwnershipEdge

OwnershipGraph

ControlPolicy
```

---

## CON-02 - Group Chart

```text
GroupChartOfAccounts

GroupAccount

GroupAccountMapping

coverage
```

---

## CON-03 - Reporting Packages

```text
EntityReportingPackage

acceptance

snapshot pinning
```

---

## CON-04 - Currency Translation

```text
CurrencyTranslationPolicy

ExchangeRateSnapshot

TranslatedTrialBalance
```

---

## CON-05 - Consolidation Ledger

```text
ConsolidationEntry

ConsolidationLine

ConsolidationLedger
```

---

## CON-06 - Intercompany Matching

```text
IntercompanyPosition

IntercompanyMatch

IntercompanyDifference
```

---

## CON-07 - Eliminations

```text
balance eliminations

revenue/expense eliminations

dividends
```

---

## CON-08 - Policy Alignment

```text
GroupAccountingPolicySet

PolicyAlignmentAssessment

ConsolidationAdjustment
```

---

## CON-09 - Investment / NCI

```text
InvestmentEliminationCase

AcquisitionContext

GoodwillMeasurement

NonControllingInterest
```

---

## CON-10 - Consolidated Trial Balance

```text
pre-elimination TB

post-elimination TB

controls
```

---

## CON-11 - Consolidated Statements

```text
reuse FinancialStatementEngine
```

---

## CON-12 - Snapshot / Replay

```text
ConsolidationSnapshot

ReproducibilityEnvelope

EvidenceBundle
```

---

## CON-13 - Close / Reopen

```text
ConsolidationCloseGate

publish

reopen

staleness
```

---

## CON-14 - Qualification

```text
golden group

FX

IC

NCI

replay

concurrency
```

---

# 355. Démonstrateur P2.1 - Full consolidation simple

```text
Group G

Parent P
Subsidiary S

Ownership P -> S:
    80 %

Method:
    FULL

Both in EUR

Source:
    accepted TrialBalanceSnapshots

Steps:
    map both charts
    aggregate balances
    calculate NCI
    eliminate investment/equity as configured
    build consolidated TB

Expected:
    balanced consolidated TB
    parent/NCI attribution reconciled
```

---

# 356. Démonstrateur - Currency translation

```text
Parent:
    EUR

Subsidiary:
    USD

Group:
    EUR

Pinned rates:
    closing
    average
    historical

Expected:
    translated TB
    translation difference explicit
    rate snapshot pinned
```

---

# 357. Démonstrateur - Intercompany balance elimination

```text
A receivable from B:
    100

B payable to A:
    100

Expected:
    match = 100
    elimination entry balanced
    group net receivable/payable effect = 0
```

---

# 358. Démonstrateur - Intercompany mismatch

```text
A receivable:
    100

B payable:
    97

Expected:
    matched = 97
    difference = 3
    cause/review required
    close blocked if policy says blocking
```

---

# 359. Démonstrateur - Revenue/Expense elimination

```text
A revenue to B:
    500

B expense from A:
    500

Expected:
    group revenue reduced by 500
    group expense reduced by 500
    result impact = 0
```

---

# 360. Démonstrateur - NCI

```text
Ownership:
    Parent 80 %
    NCI 20 %

Subsidiary current result:
    1,000

Configured allocation basis:
    ownership percentage

Expected:
    parent = 800
    NCI = 200
```

---

# 361. Démonstrateur - Source reopen

```text
Consolidation C1
depends on Subsidiary TB v1

Subsidiary period reopened
TB v2 generated

Expected:
    C1 stays immutable
    C1 freshness = STALE
    C2 required for new published consolidation
```

---

# 362. Démonstrateur - Mapping incomplet

```text
Entity account:
    local code X

No GroupAccountMapping

Expected:
    GROUP_CHART_MAPPING_COMPLETE = FAIL
    publication blocked
```

---

# 363. Démonstrateur - Missing FX rate

```text
Entity USD
Group EUR

Mandatory rate missing

Expected:
    CurrencyRateMissingError
    no silent fallback
```

---

# 364. Démonstrateur - Replay

Inputs pinned :

```text
scope v3

ownership snapshot O2

packages A4/B6

group chart v5

policy snapshot P7

FX snapshot FX3

matching policy M2

eliminations E*

NCI policy N2
```

Expected :

```text
same semantic ConsolidationSnapshot checksum
```

---

# 365. Matrice responsabilités

| Capability | Entity Accounting | Consolidation | Reconciliation | Reporting | Analysis |
|---|---:|---:|---:|---:|---:|
| Entity posting | **oui** | non | non | non | non |
| Group scope | non | **oui** | non | non | non |
| Group mapping | non | **oui** | non | consomme | non |
| FX translation | non | **oui** | peut vérifier | consomme | non |
| IC matching | source | **oui** | extension | non | non |
| Eliminations | non | **oui** | vérifie | consomme | non |
| NCI | non | **oui** | vérifie | consomme | consomme |
| Consolidated TB | non | **oui** | vérifie | consomme | consomme |
| Consolidated statements | non | source | non | **oui** | consomme |
| Group ratios | non | non | non | non | **oui** |

---

# 366. Matrice des concepts à ne pas confondre

| Concept | Signification |
|---|---|
| `AccountingEntity` | entité comptable individuelle |
| `Group` | ensemble consolidé |
| `ConsolidationScope` | périmètre versionné |
| `OwnershipInterest` | intérêt économique/détention |
| `ControlInterest` | niveau de contrôle |
| `GroupChartOfAccounts` | plan de comptes groupe |
| `EntityReportingPackage` | package source figé |
| `CurrencyTranslation` | conversion groupe |
| `IntercompanyMatch` | rapprochement réciproque |
| `ConsolidationEntry` | écriture propre au ledger groupe |
| `Elimination` | neutralisation d'effets internes |
| `NCI` | part non attribuable au parent selon policy |
| `ConsolidationSnapshot` | résultat consolidé publié immutable |

---

# 367. Frontière avec P2.2

Le prochain jalon est :

```text
22_PYACCOUNTINGKIT_RECONCILIATION_ARCHITECTURE.md
```

Il devra généraliser :

```text
bank reconciliation

subledger vs GL

intercompany reconciliation

external confirmations

statement-to-ledger matching

difference classification

resolution workflows

reconciliation snapshots

sign-off
```

sans déplacer les règles de consolidation hors du bounded context `Consolidation`.

---

# 368. Conclusion

L'architecture de consolidation devient :

```text
ENTITY ACCOUNTING
       |
       v
ENTITY REPORTING PACKAGES
       |
       +--> GROUP CHART MAPPING
       +--> POLICY ALIGNMENT
       +--> CURRENCY TRANSLATION
       +--> INTERCOMPANY MATCHING
       +--> ELIMINATIONS
       +--> INVESTMENT / NCI
       +--> GROUP ADJUSTMENTS
       |
       v
CONSOLIDATION LEDGER
       |
       v
CONSOLIDATED TRIAL BALANCE
       |
       v
CONSOLIDATED FINANCIAL STATEMENTS
       |
       v
CONSOLIDATION SNAPSHOT
```

Les principes structurants sont :

```text
Individual ledgers are immutable from consolidation.

Group adjustments live in a separate consolidation ledger.

Ownership and control are distinct.

Consolidation methods are policy-driven.

Group mappings are explicit and versioned.

Currency translation is explicit and snapshot-based.

Matching is not elimination.

Eliminations are auditable accounting effects.

NCI and goodwill are policy-driven measurements.

Published consolidations are immutable.

Reopen creates a new revision, never a rewrite.

Every consolidated amount remains drillable to entity accounting.

When a critical source, mapping, policy or rate is ambiguous, consolidation fails closed.
```

---

**Prochain document recommandé :**

```text
22_PYACCOUNTINGKIT_RECONCILIATION_ARCHITECTURE.md
```


---

## Sources et références documentaires du projet

- 📕 [Comptabilité Générale — Système français et normes IFRS](../../books/Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md)
- 📂 [Référentiels réglementaires — Datasets](../../referentiels/datasets/)
- 📐 [Référentiels réglementaires — Schémas](../../referentiels/schemas/)
- 📦 [regulatory-accounting-data-framework](../../../resources/regulatory-accounting-data-framework/)

---

## Plans d'implémentation principaux

Ce document est couvert par les plans suivants :

- [PLAN-08 — Consolidation (1.2.0)](../../plans/PLAN-08_CONSOLIDATION_1.2.0.md)
