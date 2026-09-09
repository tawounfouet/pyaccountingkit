# 08 - PyAccountingKit - Architecture de clôture, cut-off, accruals, provisions et ajustements

> **Projet** : PyAccountingKit  
> **Document** : `08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md`  
> **Documents parents** :
> - `00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`
> - `01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`
> - `02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`
> - `03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md`
> - `04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md`
> - `05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md`
> - `06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md`
> - `07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md`
> **Statut** : P0.9 - Architecture des opérations d'inventaire et de clôture  
> **Langue** : Français  
> **Objet** : Définir le lifecycle des périodes, les opérations d'inventaire comptable, le cut-off, les charges à payer, produits à recevoir, charges et produits constatés d'avance, amortissements, dépréciations, provisions, ajustements, contrôles pré-clôture, écritures de clôture, balance post-clôture, à-nouveaux et réouverture.

---

# 1. Résumé exécutif

La clôture comptable ne doit jamais être modélisée comme :

```text
period.status = CLOSED
```

La clôture est un **processus métier orchestré** qui transforme une comptabilité courante en comptabilité de fin de période puis en période fermée.

La chaîne cible est :

```text
OPEN PERIOD
    |
    v
CUT-OFF / INVENTORY REVIEW
    |
    +--> accrued expenses
    +--> accrued income
    +--> prepaid expenses
    +--> deferred income
    +--> stock adjustments
    +--> depreciation
    +--> impairment
    +--> provisions
    +--> other adjustments
    |
    v
ADJUSTING ENTRY PROPOSALS
    |
    v
VALIDATION / POSTING
    |
    v
ADJUSTED TRIAL BALANCE
    |
    v
CLOSING CONTROLS
    |
    v
CLOSING ENTRIES
    |
    v
POST-CLOSING TRIAL BALANCE
    |
    v
CLOSED / LOCKED PERIOD
    |
    +--> opening balance generation
    +--> controlled reopen if authorized
```

Le principe d'architecture fondamental est :

```text
Closing
    orchestrates

Policies
    decide / measure

Specialized domains
    calculate

Journal & Posting
    persist accounting effects

Ledger
    projects results

Controls
    decide readiness
```

Le bounded context de clôture ne crée donc pas un second moteur de posting.

---

# 2. Fondement doctrinal

Le corpus comptable étudié identifie explicitement comme régularisations de fin d'exercice :

```text
variation de stocks
dotations aux amortissements
charges à payer
produits à recevoir
charges constatées d'avance
produits constatés d'avance
```

Cette liste constitue un excellent socle doctrinal pour structurer le moteur d'inventaire comptable.

Le même corpus traite séparément :

```text
provisions pour risques et charges
dépréciations d'actifs
amortissements
```

et montre que ces traitements ne sont pas de simples opérations de posting : ils résultent d'une décision de reconnaissance et/ou de mesure.

---

# 3. Attention sur l'autorité de la source doctrinale

L'ouvrage doctrinal date de 2008.

Il sert ici à identifier :

```text
concepts
mécanismes
familles d'opérations
workflow de régularisation
```

Il ne doit pas être utilisé comme source réglementaire actuelle lorsqu'une règle a évolué.

Pour les conditions exactes de :

```text
reconnaissance
évaluation
reprise
actualisation
présentation
```

l'autorité reste :

```text
regulatory-accounting-data-framework
+
AccountingPolicySet versionné
```

---

# 4. Référence fonctionnelle CFA FRA

CFA FRA fournit déjà une première architecture de clôture :

```text
Review controls
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

et refuse la clôture lorsque certains contrôles bloquants échouent.

Le modèle de conception prévoit également :

```text
OPEN
REVIEW
CLOSING
CLOSED
```

et précise qu'après fermeture :

```text
POST interdit
```

Il prévoit en outre :

```text
clôture des comptes temporaires
transfert du résultat
génération des à-nouveaux
réouverture
```

PyAccountingKit généralise ces comportements hors de Django.

---

# 5. Deux sens du mot "inventaire"

Il faut distinguer deux concepts.

## 5.1 Inventaire comptable de fin de période

```text
Accounting Closing Inventory
```

désigne l'ensemble des travaux de fin de période :

```text
cut-off
amortissements
dépréciations
provisions
régularisations
stocks
contrôles
```

---

## 5.2 Inventory bounded context

```text
Inventory
```

désigne le domaine opérationnel des stocks :

```text
articles
mouvements
quantités
valorisation
inventaire physique
```

Le `Closing` consomme les résultats du bounded context `Inventory` mais ne doit pas le remplacer.

---

# 6. Position dans l'architecture

```text
Accounting Policies & Measurement
         |
         +------------------------------+
         |                              |
         v                              v
Accruals & Provisions             Fixed Assets / Inventory
         |                              |
         +---------------+--------------+
                         |
                         v
                    Closing
                         |
                         v
                JournalEntryProposal
                         |
                         v
             Journal / Validation / Posting
                         |
                         v
                Ledger / Trial Balance
```

---

# 7. Bounded contexts impliqués

```text
Accounting Periods & Closing

Accounting Policies & Measurement

Accruals & Provisions

Inventory

Fixed Assets

Journal & Entries

Posting & Reversal

Ledger & Balances

Accounting Controls

Audit & Traceability
```

---

# 8. Responsabilité de `Accounting Periods & Closing`

Ce bounded context possède :

```text
period lifecycle

close readiness

closing run orchestration

period lock

reopen workflow

opening workflow
```

Il ne possède pas :

```text
la formule d'amortissement

la règle de provision

la valorisation des stocks

la logique de journal entry

le calcul du grand livre
```

---

# 9. Aggregate Root - `AccountingPeriod`

```text
AccountingPeriod
|
+-- id
+-- accounting_entity_id
+-- fiscal_year_id
+-- period_number
+-- start_date
+-- end_date
+-- status
+-- close_revision
+-- closed_at?
+-- closed_by?
+-- reopened_at?
+-- metadata
```

---

# 10. `AccountingPeriodStatus`

Proposition cible :

```text
OPEN

REVIEW

CLOSING

CLOSED

LOCKED
```

---

# 11. Pourquoi ajouter `REVIEW`

`REVIEW` distingue :

```text
période encore modifiable
```

de :

```text
période en travaux de clôture
```

Elle permet de lancer :

```text
cut-off checks
inventory reviews
policy runs
control runs
```

sans fermer la période.

---

# 12. Pourquoi distinguer `CLOSED` et `LOCKED`

```text
CLOSED
    = clôture métier terminée

LOCKED
    = verrouillage renforcé / publication définitive
```

Cette distinction est une **proposition d'architecture**.

Elle n'est pas imposée par CFA FRA ni par l'ouvrage doctrinal.

Une première implémentation peut fusionner les deux si nécessaire.

---

# 13. State machine de période

```text
OPEN
  |
  | start_review
  v
REVIEW
  |
  | start_closing
  v
CLOSING
  |
  | close
  v
CLOSED
  |
  | lock
  v
LOCKED
```

Flux exceptionnel :

```text
CLOSED
   |
   | reopen
   v
REVIEW
```

ou :

```text
CLOSED
   |
   | reopen
   v
OPEN
```

selon `ReopenPolicy`.

---

# 14. Transitions interdites par défaut

```text
OPEN -> CLOSED

REVIEW -> CLOSED

CLOSING -> OPEN
    sans abort explicite

LOCKED -> OPEN
    sans procédure spéciale

CLOSED -> OPEN
    sans ReopenCommand
```

---

# 15. `FiscalYear`

```text
FiscalYear
|
+-- id
+-- accounting_entity_id
+-- start_date
+-- end_date
+-- status
+-- periods
```

La clôture d'une période et la clôture annuelle sont deux opérations distinctes.

---

# 16. Period close vs fiscal-year close

## Period close

Peut concerner :

```text
mois
trimestre
période personnalisée
```

## Fiscal-year close

Ajoute potentiellement :

```text
final adjustments
temporary account closing
result transfer
opening balances
year-end report snapshot
```

---

# 17. `ClosingRun`

Aggregate Root recommandé :

```text
ClosingRun
|
+-- id
+-- accounting_entity_id
+-- fiscal_year_id
+-- period_id?
+-- closing_type
+-- status
+-- policy_set_id
+-- reference_snapshot_id
+-- control_run_ids
+-- adjustment_run_ids
+-- generated_entry_ids
+-- started_at
+-- completed_at?
+-- started_by?
+-- metadata
```

---

# 18. Pourquoi un `ClosingRun`

La clôture doit être :

```text
rejouable
auditée
observable
idempotente
reprenable
```

Un `ClosingRun` fournit le point d'orchestration.

---

# 19. `ClosingType`

```text
PERIOD_CLOSE

MONTH_END

QUARTER_END

YEAR_END

SPECIAL_CLOSE

CUSTOM
```

---

# 20. `ClosingRunStatus`

```text
DRAFT

REVIEWING

ADJUSTING

VALIDATING

READY_TO_CLOSE

CLOSING

COMPLETED

FAILED

CANCELLED
```

---

# 21. Principe : clôture n'est pas écriture

`ClosingRun` :

```text
orchestrates
```

Il ne contient pas les écritures comme enfants d'agrégat.

Les écritures restent des `JournalEntry`.

---

# 22. Cut-off

Le cut-off répond à :

```text
Les charges et produits sont-ils affectés
à la bonne période ?
```

---

# 23. `CutOffPolicy`

```text
CutOffPolicy
|
+-- applicability
+-- recognition rules
+-- date basis
+-- materiality?
+-- reversal policy
+-- evidence requirements
```

---

# 24. `CutOffReview`

```text
CutOffReview
|
+-- id
+-- period_id
+-- status
+-- candidates
+-- issues
+-- generated_adjustments
```

---

# 25. `CutOffCandidate`

```text
CutOffCandidate
|
+-- source_event
+-- transaction_date
+-- service_period?
+-- invoice_date?
+-- accounting_period
+-- candidate_type
+-- amount_estimate?
+-- evidence
+-- status
```

---

# 26. Types de cut-off

```text
ACCRUED_EXPENSE

ACCRUED_INCOME

PREPAID_EXPENSE

DEFERRED_INCOME

INVENTORY_ADJUSTMENT

OTHER
```

---

# 27. Charges à payer

Concept générique :

```text
AccruedExpense
```

Cas-type :

```text
service consommé en N

facture non encore reçue à la clôture

charge appartient à N
```

---

# 28. `AccruedExpenseCase`

```text
AccruedExpenseCase
|
+-- id
+-- entity_id
+-- period_id
+-- source_event
+-- recognition_date
+-- estimated_amount
+-- currency
+-- evidence
+-- status
+-- generated_entry_id?
+-- reversal_entry_id?
```

---

# 29. Policy de charge à payer

```text
AccrualRecognitionPolicy
+
AccrualMeasurementPolicy
```

L'une décide :

```text
recognize?
```

L'autre :

```text
how much?
```

---

# 30. Écriture de charge à payer

Le framework ne code aucun numéro de compte.

Il exprime :

```text
Debit:
    ACCRUED_EXPENSE_CHARGE_ROLE

Credit:
    ACCRUED_EXPENSE_LIABILITY_ROLE
```

puis :

```text
AccountRoleResolutionService
```

résout les comptes de l'entreprise.

---

# 31. Estimation

Une charge à payer peut dépendre d'une estimation.

La trace conserve :

```text
basis
inputs
calculation
evidence
policy version
```

---

# 32. Produits à recevoir

Concept :

```text
AccruedIncome
```

Cas-type :

```text
revenu acquis à N

document / encaissement ultérieur

produit appartient à N
```

---

# 33. `AccruedIncomeCase`

```text
AccruedIncomeCase
|
+-- source_event
+-- recognition_date
+-- amount
+-- evidence
+-- generated_entry
```

---

# 34. Écriture conceptuelle de produit à recevoir

```text
Debit:
    ACCRUED_INCOME_ASSET_ROLE

Credit:
    ACCRUED_INCOME_REVENUE_ROLE
```

---

# 35. Charges constatées d'avance

Concept :

```text
PrepaidExpense
```

Cas-type :

```text
charge enregistrée en N

consommation économique en N+1
```

Le corpus doctrinal décrit explicitement ce mécanisme comme une régularisation de rattachement.

---

# 36. `PrepaidExpenseCase`

```text
PrepaidExpenseCase
|
+-- original_entry_id
+-- amount_to_defer
+-- service_start
+-- service_end
+-- allocation_schedule?
+-- generated_adjustment
```

---

# 37. Écriture conceptuelle de charge constatée d'avance

```text
Debit:
    PREPAID_EXPENSE_ASSET_ROLE

Credit:
    ORIGINAL_EXPENSE_ROLE
```

La configuration réelle dépend du référentiel.

---

# 38. Produits constatés d'avance

Concept :

```text
DeferredIncome
```

Cas-type :

```text
produit enregistré en N

prestation / livraison rattachée à N+1
```

Le corpus fournit un exemple explicite de régularisation à la clôture puis de contre-passation au début de N+1.

---

# 39. `DeferredIncomeCase`

```text
DeferredIncomeCase
|
+-- original_entry_id
+-- amount_to_defer
+-- earning_period
+-- generated_adjustment
+-- reversal_schedule
```

---

# 40. Écriture conceptuelle de produit constaté d'avance

```text
Debit:
    ORIGINAL_REVENUE_ROLE

Credit:
    DEFERRED_INCOME_LIABILITY_ROLE
```

---

# 41. Reversal des écritures de cut-off

Certaines écritures de régularisation sont destinées à être contrepassées.

Exemple :

```text
31/12/N
    accrual / deferral

01/01/N+1
    reversal
```

---

# 42. `AdjustmentReversalPolicy`

```text
AdjustmentReversalPolicy
|
+-- mode
+-- reversal_date_strategy
+-- automatic
+-- target_period
```

---

# 43. Modes de reversal d'ajustement

```text
NO_AUTO_REVERSAL

FIRST_DAY_NEXT_PERIOD

NEXT_OPEN_PERIOD

EXPLICIT_DATE

CUSTOM
```

---

# 44. Important : toutes les régularisations ne sont pas contrepassées

Exemples typiques :

```text
amortissement
dépréciation
certaines provisions
stock valuation
```

ne suivent pas nécessairement la même logique de reversal qu'une charge à payer.

La policy décide.

---

# 45. `AdjustmentType`

```text
ACCRUED_EXPENSE

ACCRUED_INCOME

PREPAID_EXPENSE

DEFERRED_INCOME

DEPRECIATION

IMPAIRMENT

IMPAIRMENT_REVERSAL

PROVISION

PROVISION_REMEASUREMENT

PROVISION_RELEASE

INVENTORY

FX_REVALUATION

OTHER
```

---

# 46. `AdjustmentProposal`

Objet commun :

```text
AdjustmentProposal
|
+-- id
+-- adjustment_type
+-- period_id
+-- policy_trace
+-- evidence
+-- journal_entry_proposal
+-- reversal_policy?
+-- status
```

---

# 47. Statuts d'une proposition

```text
DRAFT

REVIEW_REQUIRED

APPROVED

REJECTED

MATERIALIZED

SUPERSEDED
```

---

# 48. Human-in-the-loop

Une estimation significative peut nécessiter :

```text
REVIEW_REQUIRED
```

selon :

```text
materiality
policy
uncertainty
regulatory requirement
```

---

# 49. Inventaire des stocks

Le corpus doctrinal traite la variation des stocks comme une régularisation de fin d'exercice.

PyAccountingKit distingue :

```text
physical / operational inventory
```

et :

```text
accounting adjustment
```

---

# 50. Pipeline stock

```text
Inventory bounded context
    |
    +--> quantities
    +--> physical count
    +--> valuation
    |
    v
InventoryValuationResult
    |
    v
Closing
    |
    v
AdjustmentProposal
    |
    v
JournalEntry
```

---

# 51. `InventoryClosingResult`

Concept d'intégration :

```text
InventoryClosingResult
|
+-- period_id
+-- valuation_method
+-- opening_value
+-- closing_value
+-- adjustment_amount
+-- source_inventory_snapshot
+-- policy_trace
```

---

# 52. Pas de logique stock dans Closing

`ClosingService` ne calcule pas :

```text
FIFO
weighted average
specific identification
```

Ces méthodes appartiennent à `InventoryValuationPolicy`.

---

# 53. Inventaire physique

Un écart :

```text
system quantity
vs
physical quantity
```

peut produire :

```text
InventoryAdjustmentProposal
```

---

# 54. Amortissements

Le corpus doctrinal identifie les dotations aux amortissements parmi les opérations de fin d'exercice.

PyAccountingKit délègue le calcul à :

```text
Fixed Assets
+
DepreciationPolicy
```

---

# 55. Pipeline amortissement

```text
FixedAsset / AssetComponent
    |
    v
DepreciationPolicy
    |
    v
DepreciationResult
    |
    v
Closing
    |
    v
AdjustmentProposal
    |
    v
JournalEntry
```

---

# 56. `DepreciationRun`

```text
DepreciationRun
|
+-- id
+-- period_id
+-- policy_set
+-- asset_scope
+-- results
+-- status
+-- generated_entry_ids
```

---

# 57. Regroupement des écritures d'amortissement

La policy d'application peut choisir :

```text
one entry per asset

one entry per asset category

one entry per account pair

one consolidated entry
```

Le drill-down doit rester disponible.

---

# 58. Dépréciations

Le corpus doctrinal distingue les dépréciations d'actifs des provisions pour risques.

Cette distinction doit être structurante.

---

# 59. `ImpairmentRun`

```text
ImpairmentRun
|
+-- period_id
+-- subjects
+-- decisions
+-- generated_adjustments
```

---

# 60. Pipeline dépréciation

```text
Impairable subject
    |
    v
ImpairmentPolicy
    |
    v
ImpairmentDecision
    |
    v
AdjustmentProposal
```

---

# 61. Reprise de dépréciation

Le moteur doit supporter :

```text
IMPAIRMENT_REVERSAL
```

uniquement si la policy applicable l'autorise.

---

# 62. Provision != impairment

```text
Provision
    = obligation / risque / charge future selon policy

Impairment
    = réduction de valeur d'un actif
```

Les deux produisent potentiellement des charges mais appartiennent à des logiques différentes.

---

# 63. Provisions

Le futur specialized domain `Accruals & Provisions` porte :

```text
ProvisionCase

ProvisionRecognitionPolicy

ProvisionMeasurementPolicy

ProvisionReview
```

---

# 64. `ProvisionCase`

```text
ProvisionCase
|
+-- id
+-- entity_id
+-- case_type
+-- description
+-- origin_date
+-- expected_resolution_date?
+-- evidence
+-- status
+-- current_measurement?
+-- policy_context
```

---

# 65. `ProvisionStatus`

```text
OPEN

RECOGNIZED

REVIEWED

RELEASED

SETTLED

CLOSED
```

---

# 66. Recognition vs measurement

Une provision nécessite deux questions distinctes :

```text
1. doit-elle être reconnue ?

2. à quel montant ?
```

---

# 67. Charge à payer vs provision

Le corpus doctrinal distingue les deux notamment lorsque l'incertitude concerne :

```text
la réalisation
le montant
l'échéance
```

PyAccountingKit ne code pas cette distinction sous forme d'un seuil universel.

Elle appartient au :

```text
ProvisionRecognitionPolicy
```

du référentiel concerné.

---

# 68. Réévaluation périodique des provisions

```text
ProvisionCase
    |
    v
ProvisionReview
    |
    +--> unchanged
    +--> increase
    +--> decrease
    +--> release
    +--> settle
```

---

# 69. `ProvisionReview`

```text
ProvisionReview
|
+-- review_date
+-- prior_measurement
+-- new_measurement
+-- rationale
+-- evidence
+-- policy_trace
```

---

# 70. `ProvisionAdjustmentType`

```text
INITIAL_RECOGNITION

INCREASE

DECREASE

RELEASE

UTILIZATION

SETTLEMENT
```

---

# 71. Réserves sur la doctrine historique des provisions

Certaines distinctions ou possibilités exposées dans l'ouvrage de 2008 reflètent le corpus réglementaire de son époque.

PyAccountingKit ne doit pas en déduire :

```text
une liste universelle de provisions autorisées
```

La réglementation courante est fournie par le référentiel versionné.

---

# 72. FX revaluation future

Une clôture peut nécessiter :

```text
foreign currency remeasurement
```

Ce sujet n'est pas détaillé dans P0.9.

Point d'extension :

```text
ForeignCurrencyClosingPolicy
```

---

# 73. Materiality

Le seuil de matérialité peut influencer :

```text
review
adjustment proposal
control severity
```

mais ne doit pas permettre de violer un invariant structurel.

---

# 74. `MaterialityPolicy`

```text
MaterialityPolicy
|
+-- thresholds
+-- scope
+-- currency
+-- applicability
+-- effective dates
```

---

# 75. Cut-off completeness

Un `CutOffControl` doit pouvoir rechercher des cas tels que :

```text
goods/services received but not invoiced

invoices recorded before service period

revenues recorded before performance

revenues earned but not recorded
```

---

# 76. Sources de candidats cut-off

Adapters possibles :

```text
accounts payable

accounts receivable

purchase orders

contracts

billing

bank

payroll

manual evidence
```

Le core ne dépend d'aucun ERP.

---

# 77. `ClosingEvidence`

```text
ClosingEvidence
|
+-- evidence_type
+-- source
+-- source_reference
+-- effective_date
+-- amount?
+-- document_hash?
+-- metadata
```

---

# 78. Source immuable

Pour un ajustement finalisé, les preuves utilisées doivent être traçables.

---

# 79. `AdjustmentRun`

Aggregate ou process entity selon implémentation :

```text
AdjustmentRun
|
+-- id
+-- closing_run_id
+-- adjustment_family
+-- period
+-- status
+-- candidates
+-- proposals
+-- generated_entries
```

---

# 80. `AdjustmentRunStatus`

```text
PENDING

RUNNING

REVIEW_REQUIRED

READY

POSTING

COMPLETED

FAILED
```

---

# 81. Idempotence d'un AdjustmentRun

Fingerprint :

```text
entity
period
adjustment family
policy version
source snapshot
```

---

# 82. Rerun

Si les inputs changent :

```text
new run
```

Le précédent reste dans l'audit.

---

# 83. Supersession

Une proposition non postée peut être :

```text
SUPERSEDED
```

par une proposition plus récente.

---

# 84. Proposition déjà postée

Une écriture postée n'est pas remplacée par mutation.

Correction :

```text
reversal
+
new adjustment entry
```

---

# 85. `ClosingJournalPolicy`

Les ajustements peuvent être dirigés vers :

```text
general adjustment journal

special closing journal

policy-specific journal
```

sans code journal universel.

---

# 86. EntryType des ajustements

```text
ADJUSTING
```

pour la plupart des écritures d'inventaire.

---

# 87. EntryType de clôture

```text
CLOSING
```

pour les écritures qui ferment les comptes selon `ClosingPolicy`.

---

# 88. EntryType d'ouverture

```text
OPENING
```

pour les à-nouveaux.

---

# 89. Balance avant ajustements

```text
BEFORE_ADJUSTMENTS
```

fournit la base du processus d'inventaire.

---

# 90. Balance ajustée

Après posting de tous les ajustements retenus :

```text
ADJUSTED
```

doit être reconstruite.

---

# 91. Pourquoi reconstruire après chaque batch

Parce qu'un nouvel ajustement peut :

```text
modifier un contrôle

créer un nouvel écart

modifier une provision

modifier les états
```

---

# 92. Pre-closing controls

Avant de fermer :

```text
trial balance balanced

no forbidden draft entries

required adjustment runs completed

blocking controls passed

required reconciliations passed

required evidence complete
```

selon `ClosingPolicy`.

---

# 93. CFA FRA controls

La référence fonctionnelle prévoit notamment :

```text
TRIAL_BALANCE_BALANCED

BALANCE_SHEET_BALANCED

CASHFLOW_RECONCILED

TEMPORARY_ACCOUNT_AFTER_CLOSE
```

Le caractère bloquant de chacun doit rester configurable.

---

# 94. `ClosingControlDefinition`

```text
ClosingControlDefinition
|
+-- control_code
+-- stage
+-- severity
+-- blocking
+-- applicability
+-- policy_version
```

---

# 95. Stades de contrôle

```text
PRE_REVIEW

PRE_ADJUSTMENT

POST_ADJUSTMENT

PRE_CLOSE

POST_CLOSE

PRE_LOCK

POST_REOPEN
```

---

# 96. `ClosingReadinessResult`

```text
ClosingReadinessResult
|
+-- ready
+-- blocking_issues
+-- warnings
+-- controls
+-- missing_runs
+-- unresolved_reviews
```

---

# 97. `ClosingPolicy`

Objet central :

```text
ClosingPolicy
|
+-- required_adjustment_families
+-- required_controls
+-- temporary_account_strategy
+-- result_transfer_strategy
+-- opening_strategy
+-- reopen_policy
+-- zero_balance_policy
+-- applicability
+-- version
```

---

# 98. Policy de clôture != PostingService

Le `ClosingPolicy` détermine :

```text
what must happen
```

Le `PostingService` garantit :

```text
how entries become final
```

---

# 99. Comptes temporaires

La clôture annuelle peut nécessiter de solder certains comptes temporaires.

---

# 100. `TemporaryAccountPolicy`

```text
TemporaryAccountPolicy
|
+-- classification_source
+-- temporary_account_roles
+-- target_result_role
+-- applicability
```

---

# 101. Pas de préfixe universel

Interdit :

```python
if code.startswith("6") or code.startswith("7"):
    temporary = True
```

dans le core.

---

# 102. Classification des comptes temporaires

Doit venir de :

```text
validated AccountRole

reference-specific rule

company policy
```

---

# 103. `TemporaryAccountClosingService`

Produit :

```text
JournalEntryProposal
```

pour solder les comptes concernés.

---

# 104. Transfert du résultat

Le transfert du résultat dépend :

```text
ClosingPolicy
+
AccountRoleResolutionService
```

---

# 105. Pas de numéro de compte en dur

Correct :

```text
CURRENT_PERIOD_RESULT_ROLE
RETAINED_EARNINGS_ROLE
```

Incorrect :

```text
120
129
110
```

dans le core générique.

---

# 106. `ClosingEntryProposal`

```text
ClosingEntryProposal
|
+-- closing_run_id
+-- purpose
+-- lines
+-- source_balance_snapshot
+-- policy_trace
```

---

# 107. Validation des closing entries

Même pipeline que toute écriture :

```text
proposal
    |
    v
JournalEntry
    |
    v
validate
    |
    v
post
```

---

# 108. Pas de bypass

Interdit :

```text
ClosingService
    -> mutate balances
```

---

# 109. Post-closing balance

Une fois les closing entries postées :

```text
POST_CLOSING
```

est reconstruite.

---

# 110. Contrôle post-clôture

Exemples :

```text
temporary accounts expected to be zero

trial balance balanced

result transfer coherent

no pending closing entries
```

---

# 111. `TEMPORARY_ACCOUNTS_CLOSED`

Contrôle générique :

```text
expected temporary accounts
have zero closing balance
```

sous réserve de la policy de classification.

---

# 112. Transition vers CLOSED

Préconditions :

```text
ClosingRun.status == READY_TO_CLOSE

all required closing entries posted

post-closing controls passed

no unresolved blocking issue
```

---

# 113. Effets de `close()`

```text
period.status = CLOSED

closed_at = Clock.now()

closed_by = actor

close_revision += 1

AccountingPeriodClosed emitted
```

---

# 114. Atomicité de close

La transition finale doit être atomique.

Elle ne doit pas re-poster les ajustements déjà finalisés dans la même transaction si le processus est long.

Le `ClosingRun` orchestre des étapes durables puis effectue une transition finale courte et contrôlée.

---

# 115. `AccountingPeriodClosed`

Domain Event :

```text
AccountingPeriodClosed
|
+-- period_id
+-- closing_run_id
+-- close_revision
+-- closed_at
+-- actor
```

---

# 116. Audit de clôture

```text
CLOSING_STARTED

ADJUSTMENT_RUN_COMPLETED

CLOSING_CONTROLS_COMPLETED

CLOSING_ENTRIES_POSTED

PERIOD_CLOSED
```

---

# 117. Après fermeture

Posting normal :

```text
forbidden
```

---

# 118. Historical reads

La fermeture ne modifie pas :

```text
Journal
Ledger
Trial Balance
```

hormis les nouvelles closing entries elles-mêmes.

---

# 119. Lock

`LOCKED` peut être utilisé après :

```text
publication
audit sign-off
regulatory filing
```

---

# 120. Réouverture

CFA FRA prévoit conceptuellement la réouverture et un audit event `PERIOD_REOPENED`, mais ne détaille pas entièrement ses règles.

Les règles suivantes sont donc une **proposition PyAccountingKit**.

---

# 121. `ReopenPolicy`

```text
ReopenPolicy
|
+-- allowed_from_statuses
+-- target_status
+-- required_reason
+-- authorization_hook
+-- require_new_close_revision
+-- report_invalidation_policy
+-- snapshot_policy
+-- applicability
```

---

# 122. `ReopenPeriodCommand`

```text
ReopenPeriodCommand
|
+-- period_id
+-- reason
+-- actor
+-- expected_close_revision
```

---

# 123. Preconditions de réouverture

Exemples configurables :

```text
period == CLOSED

not hard locked

reason provided

actor authorized externally

no conflicting close/reopen operation
```

---

# 124. Effets de réouverture

```text
period.status = REVIEW or OPEN

reopened_at = Clock.now()

close_revision += 1

AccountingPeriodReopened emitted
```

---

# 125. La réouverture ne supprime rien

Elle ne supprime pas :

```text
closing entries

adjustment entries

report snapshots

audit events
```

---

# 126. Correction après réouverture

Si une closing entry doit être corrigée :

```text
reversal
+
replacement
```

comme toute écriture postée.

---

# 127. Nouvelle clôture

Après correction :

```text
new ClosingRun

new close revision
```

---

# 128. Snapshots après reopen

Un `ReportSnapshot` déjà publié doit rester immutable.

Un nouveau closing produit :

```text
new ReportSnapshot
```

avec relation de supersession si nécessaire.

---

# 129. `CloseRevision`

```text
CloseRevision
```

permet de distinguer :

```text
first close
reopened
second close
```

---

# 130. Contrôle de concurrence reopen

Un `close()` et un `reopen()` concurrents doivent être sérialisés.

---

# 131. Lock technique

Les adapters peuvent utiliser :

```text
optimistic revision

pessimistic row lock
```

---

# 132. À-nouveaux

La clôture annuelle peut préparer les soldes d'ouverture de N+1.

---

# 133. `OpeningBalancePolicy`

```text
OpeningBalancePolicy
|
+-- source_variant
+-- eligible_accounts
+-- target_period
+-- aggregation
+-- journal_role
+-- numbering_policy
+-- generation_mode
```

---

# 134. Source recommandée

Les à-nouveaux sont dérivés de :

```text
POST_CLOSING Trial Balance
```

ou d'un snapshot équivalent validé.

---

# 135. `OpeningBalanceRun`

```text
OpeningBalanceRun
|
+-- source_fiscal_year
+-- target_fiscal_year
+-- source_snapshot
+-- proposals
+-- status
```

---

# 136. Génération des opening entries

```text
Post-closing Trial Balance N
        |
        v
OpeningBalancePolicy
        |
        v
JournalEntryProposal(s)
        |
        v
OPENING entries in N+1
```

---

# 137. Comptes éligibles

Les comptes éligibles doivent être définis par :

```text
AccountRole
ClosingPolicy
ReferenceSpecificRule
```

pas par préfixe global.

---

# 138. Idempotence des à-nouveaux

Fingerprint :

```text
source fiscal year
target fiscal year
source close revision
opening policy version
```

---

# 139. Rerun après réouverture

Si N est réouvert et re-clôturé :

```text
opening balance run N+1
```

peut devenir obsolète.

Il faut :

```text
supersede / reverse / regenerate
```

selon policy.

---

# 140. Pas de mutation d'une OPENING postée

Une opening entry déjà postée est corrigée par :

```text
reversal + replacement
```

---

# 141. Cut-off schedule

Les régularisations répétitives peuvent être décrites par :

```text
AccrualSchedule

DeferralSchedule
```

---

# 142. `AccrualSchedule`

```text
AccrualSchedule
|
+-- source
+-- amount_basis
+-- start_period
+-- end_period
+-- allocation_method
+-- reversal_method
+-- generated_adjustments
```

---

# 143. Allocation methods

```text
STRAIGHT_LINE

DAILY_PRORATA

MONTHLY_PRORATA

EVENT_BASED

CUSTOM
```

---

# 144. Allocation != règle universelle

La méthode est explicitement sélectionnée.

---

# 145. `DeferralSchedule`

Même logique pour :

```text
prepaid expenses
deferred income
```

---

# 146. Reconciliation des schedules

A chaque période :

```text
expected recognized amount
vs
posted amount
```

doit être contrôlable.

---

# 147. `ScheduleReconciliationControl`

Résultat :

```text
PASS
WARNING
BLOCKING
```

selon policy.

---

# 148. Cut-off par date de service

Un event peut porter :

```text
service_period_start
service_period_end
```

séparément de :

```text
invoice_date
payment_date
```

---

# 149. Importance du modèle temporel

Le moteur doit distinguer :

```text
economic occurrence

recognition date

document date

invoice date

payment date

accounting date

posting timestamp
```

---

# 150. `AccountingPeriodResolver`

Port/service :

```python
class AccountingPeriodResolver:

    def resolve(
        self,
        entity_id,
        accounting_date,
    ) -> AccountingPeriod:
        ...
```

---

# 151. Ambiguïté de période

```text
0 matching periods
    -> PeriodNotFoundError

>1 matching periods
    -> AmbiguousAccountingPeriodError
```

---

# 152. Pré-clôture des sources externes

Un closing peut dépendre d'un freeze applicatif sur :

```text
invoicing

payroll

inventory

bank

subledgers
```

mais PyAccountingKit ne gère pas ces applications.

---

# 153. `ClosingDependencyPort`

Interface future :

```text
check_readiness(
    entity,
    period,
) -> DependencyReadiness
```

---

# 154. Dependency readiness

```text
READY
NOT_READY
UNKNOWN
```

---

# 155. Fail-closed configurable

Pour une dépendance obligatoire :

```text
UNKNOWN
```

peut être bloquant.

---

# 156. Cut-off checklist

Exemples génériques :

```text
all expected purchase invoices reviewed

unbilled received services reviewed

unbilled revenues reviewed

prepaids reviewed

deferred revenues reviewed

inventory complete

fixed assets depreciation run

impairment review

provisions review

subledger reconciliations complete
```

La liste réelle vient du `ClosingPolicy`.

---

# 157. `ClosingChecklist`

```text
ClosingChecklist
|
+-- items
+-- status
+-- evidence_refs
+-- completed_by
+-- completed_at
```

---

# 158. Checklist != accounting control

Une checklist peut être :

```text
process evidence
```

sans être une règle comptable.

---

# 159. Classification des closing rules

```text
DOMAIN_POLICY

ACCOUNTING_METHOD

REGULATORY_RULE

CONTROL

PROCESS_REQUIREMENT
```

---

# 160. `PROCESS_REQUIREMENT`

Nouvelle catégorie recommandée pour :

```text
approval
checklist completion
evidence upload
review sign-off
```

Elle ne doit pas être confondue avec un invariant comptable.

---

# 161. Exemple de classification

```text
ENTRY_BALANCED
    UNIVERSAL_ACCOUNTING_INVARIANT

ACCRUED_EXPENSE_RECOGNITION
    ACCOUNTING_METHOD / REGULATORY_RULE

TRIAL_BALANCE_BALANCED
    CONTROL

REVIEW_SIGNOFF_REQUIRED
    PROCESS_REQUIREMENT
```

---

# 162. Rattachement et materiality

Une policy peut combiner :

```text
AccrualRecognitionPolicy
+
MaterialityPolicy
```

mais le seuil doit être versionné.

---

# 163. Cut-off exceptions

Une décision de non-ajustement peut être tracée :

```text
AdjustmentWaiver
```

---

# 164. `AdjustmentWaiver`

```text
AdjustmentWaiver
|
+-- candidate_id
+-- reason
+-- materiality_basis?
+-- policy
+-- approved_by?
+-- effective_period
```

---

# 165. Waiver != suppression de l'évidence

Le candidat initial reste auditable.

---

# 166. Post-adjustment review

Après posting :

```text
rebuild ADJUSTED Trial Balance
```

et relancer :

```text
relevant controls
```

---

# 167. `AdjustmentBatch`

Pour performance, plusieurs proposals peuvent être regroupées.

---

# 168. Atomicité batch

Deux modes :

```text
ALL_OR_NOTHING

PER_PROPOSAL
```

doivent être explicites.

---

# 169. P0 recommandé

Pour un même type de run critique :

```text
ALL_OR_NOTHING
```

est préférable si le volume le permet.

---

# 170. Reprise après erreur

Un `AdjustmentRun` en erreur peut être repris à partir de :

```text
last durable stage
```

si l'Application Layer le permet.

---

# 171. Workflow complet d'une clôture

```text
1. start ClosingRun

2. move period OPEN -> REVIEW

3. build BEFORE_ADJUSTMENTS balance

4. run cut-off review

5. run inventory valuation

6. run depreciation

7. run impairment

8. run provisions

9. review adjustment proposals

10. create / validate / post adjustments

11. build ADJUSTED balance

12. run financial statement controls

13. run pre-close controls

14. move period REVIEW -> CLOSING

15. generate closing entries

16. validate / post closing entries

17. build POST_CLOSING balance

18. run post-close controls

19. close period

20. generate immutable closing evidence / snapshot refs

21. if year end, generate opening balance run
```

---

# 172. `ClosingStage`

Enum proposée :

```text
INITIAL

CUT_OFF

INVENTORY

DEPRECIATION

IMPAIRMENT

PROVISIONS

ADJUSTMENTS

ADJUSTED_BALANCE

PRE_CLOSE_CONTROLS

CLOSING_ENTRIES

POST_CLOSING_BALANCE

FINAL_CONTROLS

CLOSED
```

---

# 173. Stage dependencies

Exemple :

```text
POST_CLOSING_BALANCE
requires
CLOSING_ENTRIES complete
```

---

# 174. `ClosingStageResult`

```text
ClosingStageResult
|
+-- stage
+-- status
+-- started_at
+-- completed_at
+-- outputs
+-- errors
+-- warnings
```

---

# 175. Pipeline configurable

Tous les closings ne nécessitent pas tous les stages.

Exemple mensuel :

```text
no annual temporary account close
```

---

# 176. `ClosingPipelineDefinition`

```text
ClosingPipelineDefinition
|
+-- closing_type
+-- stages
+-- dependencies
+-- policy_version
```

---

# 177. Monthly close

Peut inclure :

```text
cut-off
depreciation
accruals
reconciliations
adjusted balance
period lock
```

sans :

```text
annual result transfer
```

---

# 178. Year-end close

Ajoute typiquement :

```text
full inventory review
final provisions
temporary account closing
result transfer
opening balances
```

---

# 179. Closing evidence bundle

```text
ClosingEvidenceBundle
|
+-- closing_run_id
+-- reference_snapshot
+-- policy_set
+-- before_adjustments_balance_ref
+-- adjustment_runs
+-- control_runs
+-- adjusted_balance_ref
+-- closing_entries
+-- post_closing_balance_ref
+-- audit_refs
+-- checksum
```

---

# 180. Pourquoi un evidence bundle

Permet de répondre :

```text
quelles policies ?

quels contrôles ?

quelles écritures ?

quelles preuves ?

quel référentiel ?

quelle version de clôture ?
```

---

# 181. Immutable after close

Le bundle final de close est immutable.

---

# 182. `ClosingSnapshot`

Alternative légère :

```text
ClosingSnapshot
```

peut contenir les références plutôt que toutes les données.

---

# 183. Interaction avec `ReportSnapshot`

```text
ClosingSnapshot
    |
    v
FinancialStatement generation
    |
    v
ReportSnapshot
```

---

# 184. Interaction avec Financial Analysis

```text
ReportSnapshot / TrialBalanceSnapshot
    |
    v
Financial Analysis
```

La réouverture produit de nouveaux snapshots ; les anciens restent historiques.

---

# 185. Interaction avec Reconciliation

Le close peut exiger :

```text
bank reconciled

subledger reconciled

intercompany reconciled
```

selon policy.

---

# 186. Cash-flow reconciliation

CFA FRA le considère comme condition bloquante de clôture dans son MVP.

PyAccountingKit le classe comme :

```text
CONTROL
```

dont le caractère bloquant est configuré par `ClosingPolicy`.

---

# 187. DRAFT entries

CFA FRA bloque la clôture si des `DRAFT` subsistent.

PyAccountingKit transforme cela en :

```text
DraftEntryClosingControl
```

configurable.

---

# 188. Pourquoi configurable

Une application pourrait autoriser :

```text
drafts future-dated
```

ou :

```text
drafts hors scope
```

Le contrôle doit donc préciser son périmètre.

---

# 189. Scope d'un closing control

```text
entity
period
journals
entry types
date range
```

---

# 190. `TemporaryAccountAfterCloseControl`

Vérifie :

```text
temporary accounts
expected to be zero
```

dans `POST_CLOSING`.

---

# 191. `AdjustmentCompletenessControl`

Vérifie que les runs requis sont :

```text
COMPLETED
```

---

# 192. `PolicyTraceCompletenessControl`

Vérifie que les ajustements automatiques possèdent :

```text
PolicyExecutionTrace
```

---

# 193. `EvidenceCompletenessControl`

Vérifie :

```text
required evidence
```

pour les décisions manuelles.

---

# 194. Reopen control

Après réouverture :

```text
previous close revision
```

est marqué historique.

---

# 195. `ReopenImpactAnalysis`

```text
ReopenImpactAnalysis
|
+-- affected_report_snapshots
+-- affected_opening_runs
+-- affected_exports
+-- affected_reconciliations
+-- required_regeneration
```

---

# 196. Reopen n'invalide pas physiquement

On marque :

```text
superseded / stale
```

mais on ne supprime pas l'historique.

---

# 197. `SnapshotFreshness`

```text
CURRENT

STALE

SUPERSEDED
```

---

# 198. External filings

Si un rapport a été déposé extérieurement, PyAccountingKit peut conserver :

```text
external_filing_ref
```

mais ne gère pas la procédure réglementaire elle-même.

---

# 199. Multi-entité

Tous les closing objects sont scopés par :

```text
AccountingEntityId
```

---

# 200. Consolidation

La clôture statutaire d'une entité est distincte de :

```text
group consolidation close
```

---

# 201. Consolidation close

Le futur bounded context `Consolidation` aura son propre :

```text
ConsolidationRun
```

consommant les closes statutaires.

---

# 202. Multi-devise

La clôture pourra intégrer :

```text
FX remeasurement
```

sans modifier l'architecture générale.

---

# 203. Tax closing

Les règles fiscales peuvent nécessiter des traitements spécifiques.

Elles doivent être :

```text
Tax-specific policies / adapters
```

et non des invariants génériques.

---

# 204. Deferred tax future

Hors P0.9 :

```text
DeferredTaxPolicy
```

peut être ajoutée ultérieurement.

---

# 205. `ClosingPolicySet`

Option : agréger les policies de fin de période.

```text
ClosingPolicySet
|
+-- cut_off_policy
+-- depreciation_policy
+-- impairment_policy
+-- provision_policy
+-- inventory_policy
+-- closing_policy
+-- opening_policy
+-- reopen_policy
```

---

# 206. Relation avec `AccountingPolicySet`

Recommandation :

```text
ClosingPolicySet
```

n'est pas une racine indépendante.

Il est une vue / composition de :

```text
AccountingPolicySet
```

pour la période de close.

---

# 207. Snapshot de policy

Le `ClosingRun` fige :

```text
AccountingPolicySet version
```

au démarrage ou à un stage déterminé.

---

# 208. Changement de policy en cours de close

Par défaut :

```text
forbidden
```

sans nouveau run ou réinitialisation explicite.

---

# 209. Pourquoi

Sinon :

```text
depreciation
```

pourrait utiliser v1 et :

```text
provisions
```

v2 sans trace cohérente.

---

# 210. `ClosingPolicySnapshot`

```text
ClosingPolicySnapshot
|
+-- policy_set_id
+-- version
+-- captured_at
+-- checksum
```

---

# 211. Reference snapshot

Même logique :

```text
reference_snapshot
```

est figé pour le run.

---

# 212. Determinism

A :

```text
same source snapshots
same policy versions
same evidence
```

un adjustment run déterministe doit produire le même résultat.

---

# 213. External observations

Si une valorisation externe intervient :

```text
market value
exchange rate
actuarial input
```

l'observation utilisée doit être figée.

---

# 214. Audit manual override

Un utilisateur peut corriger une proposition avant posting selon policy.

Le système conserve :

```text
calculated amount

approved amount

difference

reason

actor
```

---

# 215. `AdjustmentOverride`

```text
AdjustmentOverride
|
+-- proposal_id
+-- calculated_value
+-- approved_value
+-- reason
+-- actor
+-- approved_at
```

---

# 216. Override policy

Peut interdire :

```text
manual override
```

pour certaines règles réglementaires.

---

# 217. Error taxonomy

```text
ClosingError
|
+-- ClosingRunNotFoundError
+-- ClosingRunStateError
+-- ClosingNotReadyError
+-- ClosingControlFailedError
+-- ClosingConcurrencyError
+-- ClosingPolicyChangedError
|
+-- CutOffError
|   +-- CutOffEvidenceMissingError
|   +-- CutOffMeasurementError
|
+-- AdjustmentError
|   +-- AdjustmentRunFailedError
|   +-- AdjustmentAlreadyPostedError
|   +-- AdjustmentReviewRequiredError
|
+-- ProvisionError
+-- DepreciationClosingError
+-- ImpairmentClosingError
+-- InventoryClosingError
|
+-- PeriodCloseError
|   +-- PeriodAlreadyClosedError
|   +-- PeriodNotClosableError
|
+-- PeriodReopenError
|   +-- PeriodNotClosedError
|   +-- PeriodLockedError
|   +-- ReopenReasonRequiredError
|
+-- OpeningBalanceError
    +-- OpeningSourceNotClosedError
    +-- OpeningAlreadyGeneratedError
```

---

# 218. Fail-closed

Doivent échouer explicitement :

```text
policy ambiguity

missing required run

blocking control failure

missing target account role

unresolved human review

closed period posting attempt

duplicate closing finalization
```

---

# 219. `ClosingService`

Contrat conceptuel :

```python
class ClosingService:

    def start_review(...):
        ...

    def start_closing(...):
        ...

    def evaluate_readiness(...):
        ...

    def close(...):
        ...

    def reopen(...):
        ...
```

---

# 220. Ne pas faire de `run_everything()` opaque

Même si une façade existe, les stages doivent rester observables.

---

# 221. Application services

```text
StartClosingRun

StartPeriodReview

RunCutOffReview

RunInventoryClosing

RunDepreciation

RunImpairmentReview

RunProvisionReview

GenerateAdjustmentEntries

PostAdjustmentEntries

EvaluateClosingReadiness

GenerateClosingEntries

PostClosingEntries

CloseAccountingPeriod

ReopenAccountingPeriod

GenerateOpeningBalances
```

---

# 222. Repositories / Ports

```text
ClosingRunRepository

AccountingPeriodRepository

AdjustmentRunRepository

ProvisionRepository

AccrualScheduleRepository

OpeningBalanceRunRepository

JournalEntryRepository

UnitOfWork

Clock

AuditPort

AccountingControlPort

TrialBalanceQuery

AccountingReferenceProvider
```

---

# 223. Specialized-domain ports

```text
InventoryClosingPort

FixedAssetDepreciationPort

ImpairmentAssessmentPort

ProvisionAssessmentPort
```

Ces ports peuvent d'abord avoir des adapters InMemory / test.

---

# 224. `InventoryClosingPort`

```python
class InventoryClosingPort(Protocol):
    def calculate_closing(
        self,
        request: InventoryClosingRequest,
    ) -> InventoryClosingResult:
        ...
```

---

# 225. `FixedAssetDepreciationPort`

```python
class FixedAssetDepreciationPort(Protocol):
    def run_depreciation(
        self,
        request: DepreciationRunRequest,
    ) -> DepreciationRunResult:
        ...
```

---

# 226. `AccountingControlPort`

```python
class AccountingControlPort(Protocol):
    def run_controls(
        self,
        scope: AccountingScope,
        control_codes: tuple[str, ...],
    ) -> ControlRun:
        ...
```

---

# 227. Transaction boundary d'un adjustment posting

```text
load proposal
verify approved
create JournalEntry
validate
post
link proposal -> entry
audit
commit
```

---

# 228. Transaction boundary du close final

```text
lock period

verify revision

re-evaluate critical readiness

transition CLOSING -> CLOSED

persist audit/outbox

commit
```

---

# 229. Transaction boundary reopen

```text
lock period

verify CLOSED

verify revision

evaluate reopen policy

transition

audit

mark dependent snapshots stale

commit
```

Le marquage des dépendances peut être asynchrone si la cohérence est maîtrisée.

---

# 230. Concurrence

Cas critiques :

```text
two close commands

close vs adjustment post

close vs reopen

two opening balance generations
```

---

# 231. Expected revision

```text
AccountingPeriod.close_revision
```

sert de garde optimistic.

---

# 232. Pessimistic lock

Adapter SQL peut verrouiller :

```text
AccountingPeriod
ClosingRun
```

pendant les transitions critiques.

---

# 233. Idempotence close

Même :

```text
ClosingRunId
+
close command idempotency key
```

doit éviter un double close.

---

# 234. Idempotence reopen

Même logique.

---

# 235. Tests P0 - period lifecycle

```text
test_open_period_can_enter_review

test_review_period_can_enter_closing

test_closing_period_can_close_when_ready

test_open_cannot_jump_directly_to_closed

test_closed_period_rejects_normal_posting

test_reopen_requires_explicit_command
```

---

# 236. Tests P0 - cut-off

```text
test_accrued_expense_generates_adjustment_proposal

test_accrued_income_generates_adjustment_proposal

test_prepaid_expense_generates_deferral

test_deferred_income_generates_deferral

test_cutoff_adjustment_uses_account_roles_not_codes
```

---

# 237. Tests P0 - reversal schedules

```text
test_auto_reversal_uses_reversal_service

test_auto_reversal_does_not_mutate_original_adjustment

test_no_auto_reversal_when_policy_disables_it
```

---

# 238. Tests P0 - provisions

```text
test_provision_recognition_and_measurement_are_separate

test_provision_review_can_increase

test_provision_review_can_decrease

test_provision_release_creates_adjustment_proposal
```

La formule réglementaire réelle est testée dans les policy suites correspondantes.

---

# 239. Tests P0 - depreciation

```text
test_depreciation_run_produces_adjustment_proposals

test_depreciation_run_does_not_post_directly

test_depreciation_entries_use_normal_posting_pipeline
```

---

# 240. Tests P0 - inventory

```text
test_inventory_closing_result_can_generate_adjustment

test_closing_does_not_implement_fifo_itself
```

---

# 241. Tests P0 - controls

```text
test_blocking_control_prevents_close

test_warning_does_not_block_when_policy_says_non_blocking

test_missing_required_adjustment_run_prevents_close
```

---

# 242. Tests P0 - close

```text
test_close_requires_adjusted_balance

test_close_posts_closing_entries_before_closed

test_post_closing_balance_is_rebuilt

test_closed_period_records_actor_and_timestamp

test_close_is_idempotent
```

---

# 243. Tests P0 - reopen

```text
test_closed_period_can_reopen_when_policy_allows

test_locked_period_cannot_reopen_by_default

test_reopen_does_not_delete_closing_entries

test_reopen_increments_close_revision

test_reopen_marks_derived_snapshots_stale
```

---

# 244. Tests P0 - opening

```text
test_opening_balances_derive_from_post_closing_source

test_opening_generation_is_idempotent

test_reclose_after_reopen_detects_stale_opening_run
```

---

# 245. Property-based test - reversal cut-off

Pour une régularisation totalement contrepassée :

```text
adjustment
+
reversal
=
0 net
```

sur le même scope, hors nouvelles opérations réelles.

---

# 246. Property-based test - close

Pour une période clôturée avec policy exigeant comptes temporaires soldés :

```text
all temporary account closing balances == 0
```

---

# 247. Property-based test - balance

Après chaque batch équilibré :

```text
Trial Balance total debit
=
Trial Balance total credit
```

---

# 248. Golden scenario - accrued expense

```text
Service consumed in December N
Invoice received in January N+1

31/12/N:
    adjustment recognized

01/01/N+1:
    reversal according to policy

January invoice:
    normal accounting entry
```

Attendu :

```text
expense belongs to N
no duplicate net expense in N+1
```

---

# 249. Golden scenario - deferred income

```text
Revenue recorded in N
Service belongs to N+1

31/12/N:
    defer revenue

N+1:
    reversal / recognition
```

---

# 250. Golden scenario - prepaid expense

```text
Expense paid in N
Economic consumption in N+1

31/12/N:
    defer expense
```

---

# 251. Golden scenario - impairment

```text
carrying amount
>
policy-defined recoverable/reference amount

=> impairment proposal
```

Le montant exact est fourni par `ImpairmentPolicy`.

---

# 252. Golden scenario - provision review

```text
opening provision 100

new measurement 130

=> increase adjustment 30
```

ou :

```text
new measurement 70

=> decrease/release 30
```

selon policy.

---

# 253. Golden scenario - close

```text
BEFORE_ADJUSTMENTS

+ accrual
+ deferral
+ depreciation
+ impairment
+ provision

= ADJUSTED

+ closing entries

= POST_CLOSING

-> CLOSED
```

---

# 254. Golden scenario - reopen

```text
CLOSED revision 1

reopen

post correcting reversal/replacement

new closing run

CLOSED revision 2
```

Les deux closes restent auditables.

---

# 255. Audit events

```text
CLOSING_RUN_CREATED

PERIOD_REVIEW_STARTED

CUT_OFF_REVIEW_COMPLETED

ADJUSTMENT_PROPOSED

ADJUSTMENT_APPROVED

ADJUSTMENT_POSTED

DEPRECIATION_RUN_COMPLETED

IMPAIRMENT_RUN_COMPLETED

PROVISION_REVIEW_COMPLETED

CLOSING_CONTROLS_RUN

CLOSING_ENTRIES_POSTED

PERIOD_CLOSED

PERIOD_REOPENED

OPENING_BALANCES_GENERATED
```

---

# 256. Domain events

```text
ClosingRunStarted

AdjustmentRunCompleted

ClosingReady

AccountingPeriodClosed

AccountingPeriodReopened

OpeningBalanceRunCompleted
```

---

# 257. Audit vs Domain Event

```text
AccountingPeriodClosed
    = domain fact

PERIOD_CLOSED
    = durable audit evidence
```

---

# 258. Observabilité

Metrics :

```text
closing_runs_total

closing_run_duration

adjustments_proposed_total

adjustments_posted_total

cutoff_candidates_total

provision_reviews_total

closing_controls_failed_total

period_reopens_total
```

---

# 259. Logs structurés

Contexte :

```text
entity_id
period_id
closing_run_id
stage
policy_set_version
reference_snapshot_id
close_revision
```

---

# 260. Tracing

Spans :

```text
run_cutoff

run_depreciation

run_impairment

run_provisions

build_adjusted_balance

run_closing_controls

post_closing_entries

close_period

reopen_period
```

---

# 261. Performance

Les runs spécialisés peuvent être :

```text
batch-oriented
```

notamment :

```text
depreciation
inventory
provisions
```

---

# 262. Long-running jobs

L'Application Layer peut exécuter ces runs :

```text
synchronously

worker queue

workflow engine
```

sans changer le domaine.

---

# 263. Checkpointing

Pour une clôture longue :

```text
stage completion
```

est persisté.

---

# 264. Retry

Un stage retryable ne doit pas dupliquer les écritures grâce à :

```text
idempotency
```

---

# 265. Outbox

Les événements externes peuvent être diffusés via :

```text
Transactional Outbox
```

après les mutations critiques.

---

# 266. Package domaine

```text
src/pyaccountingkit/domain/
|
+-- periods/
|   +-- fiscal_year.py
|   +-- accounting_period.py
|   +-- status.py
|
+-- closing/
|   +-- closing_run.py
|   +-- closing_policy.py
|   +-- pipeline.py
|   +-- stage.py
|   +-- readiness.py
|   +-- evidence.py
|   +-- reopen.py
|   +-- opening.py
|
+-- accruals/
|   +-- accrued_expense.py
|   +-- accrued_income.py
|   +-- prepaid_expense.py
|   +-- deferred_income.py
|   +-- schedules.py
|
+-- provisions/
|   +-- provision_case.py
|   +-- review.py
|
+-- adjustments/
    +-- proposal.py
    +-- run.py
    +-- override.py
```

---

# 267. Specialized modules futurs

```text
domain/inventory/

domain/fixed_assets/
```

restent des bounded contexts séparés.

---

# 268. Application package

```text
application/closing/
|
+-- start_review.py
+-- run_cutoff.py
+-- run_adjustments.py
+-- evaluate_readiness.py
+-- start_closing.py
+-- generate_closing_entries.py
+-- close_period.py
+-- reopen_period.py
+-- generate_opening_balances.py
```

---

# 269. Ports package

```text
ports/
|
+-- closing_repository.py
+-- adjustment_repository.py
+-- accounting_controls.py
+-- inventory_closing.py
+-- fixed_asset_depreciation.py
+-- impairment_assessment.py
+-- provision_assessment.py
```

---

# 270. Anti-pattern - close = status update

Interdit :

```python
period.status = CLOSED
repository.save(period)
```

sans readiness checks.

---

# 271. Anti-pattern - Closing écrit directement dans Ledger

Interdit :

```text
ClosingService
    -> account.current_balance
```

---

# 272. Anti-pattern - provision dans PostingService

Interdit :

```python
if risk_is_probable:
    ...
```

dans le posting.

---

# 273. Anti-pattern - cut-off basé uniquement sur facture

Le cut-off doit pouvoir utiliser :

```text
economic/service dates
```

et pas seulement :

```text
invoice date
```

---

# 274. Anti-pattern - réouverture destructive

Interdit :

```text
delete closing entries
delete report snapshot
```

---

# 275. Anti-pattern - à-nouveaux mutables

Une opening entry postée reste immutable.

---

# 276. Anti-pattern - numéros de compte français dans core

Interdit :

```text
408
418
486
487
15
28
68
78
```

dans le moteur générique.

Ces codes peuvent exister dans un adapter/reference-specific mapping.

---

# 277. Anti-pattern - stock logic inside closing

Interdit :

```text
ClosingService calculates FIFO
```

---

# 278. Anti-pattern - depreciation formula inside closing

Interdit :

```text
ClosingService computes straight-line depreciation
```

---

# 279. Anti-pattern - hardcoded required controls

Le core ne doit pas imposer universellement :

```text
CASHFLOW_RECONCILED
```

comme bloquant.

C'est `ClosingPolicy` qui le décide.

---

# 280. Anti-pattern - stale policy mix

Interdit de terminer un run avec plusieurs versions de policy non maîtrisées.

---

# 281. ADRs

| ID | Décision |
|---|---|
| ADR-CLOSE-001 | La clôture est un workflow, pas un simple changement de statut |
| ADR-CLOSE-002 | `ClosingRun` orchestre les étapes de clôture |
| ADR-CLOSE-003 | Accounting inventory et Inventory bounded context sont distincts |
| ADR-CLOSE-004 | Les cut-off adjustments utilisent `Accounting Policies & Measurement` |
| ADR-CLOSE-005 | Accrued expense, accrued income, prepaid expense et deferred income sont des concepts génériques |
| ADR-CLOSE-006 | Les numéros de comptes nationaux ne sont pas codés dans le core |
| ADR-CLOSE-007 | Les écritures de régularisation passent par JournalEntryProposal -> Validation -> Posting |
| ADR-CLOSE-008 | Une policy détermine si une régularisation est automatiquement extournée |
| ADR-CLOSE-009 | Inventory calcule les valeurs de stocks ; Closing ne calcule pas FIFO/WAC |
| ADR-CLOSE-010 | Fixed Assets calcule l'amortissement ; Closing orchestre son posting |
| ADR-CLOSE-011 | Impairment est distinct de Provision |
| ADR-CLOSE-012 | Provision recognition et provision measurement sont distincts |
| ADR-CLOSE-013 | Les règles réglementaires historiques de l'ouvrage ne sont pas supposées actuelles |
| ADR-CLOSE-014 | BEFORE_ADJUSTMENTS est le point de départ du close |
| ADR-CLOSE-015 | ADJUSTED est reconstruit après les ajustements |
| ADR-CLOSE-016 | POST_CLOSING est reconstruit après les closing entries |
| ADR-CLOSE-017 | La classification des comptes temporaires est policy-driven |
| ADR-CLOSE-018 | Les closing controls ont une sévérité et un caractère bloquant configurables |
| ADR-CLOSE-019 | `CLOSED` interdit le posting normal |
| ADR-CLOSE-020 | La réouverture est explicite, auditée et non destructive |
| ADR-CLOSE-021 | Une réouverture crée une nouvelle close revision |
| ADR-CLOSE-022 | Les snapshots historiques ne sont jamais supprimés par reopen |
| ADR-CLOSE-023 | Les à-nouveaux dérivent d'une source post-closing validée |
| ADR-CLOSE-024 | Les à-nouveaux postés sont corrigés par reversal, jamais par mutation |
| ADR-CLOSE-025 | PolicySet et ReferenceSnapshot sont figés pour un ClosingRun |
| ADR-CLOSE-026 | Les stages de closing sont checkpointables |
| ADR-CLOSE-027 | Closing est multi-entity scoped |
| ADR-CLOSE-028 | Consolidation close est distinct du statutory close |
| ADR-CLOSE-029 | Le process peut inclure des `PROCESS_REQUIREMENT` distincts des règles comptables |
| ADR-CLOSE-030 | Toute correction d'un ajustement déjà posté suit reversal + replacement |

---

# 282. Critères d'acceptation P0.9

```text
[ ] AccountingPeriod lifecycle est spécifié

[ ] OPEN / REVIEW / CLOSING / CLOSED sont définis

[ ] LOCKED est identifié comme extension possible

[ ] ClosingRun est défini

[ ] ClosingRun possède un pipeline observable

[ ] cut-off est modélisé

[ ] AccruedExpense est modélisé

[ ] AccruedIncome est modélisé

[ ] PrepaidExpense est modélisé

[ ] DeferredIncome est modélisé

[ ] AdjustmentProposal est défini

[ ] auto-reversal est policy-driven

[ ] Inventory est séparé du Closing

[ ] Depreciation est calculé hors Closing

[ ] Impairment est séparé de Provision

[ ] ProvisionCase est défini

[ ] provision recognition != provision measurement

[ ] adjustment runs sont idempotents

[ ] BEFORE_ADJUSTMENTS est utilisé avant inventaire

[ ] ADJUSTED est reconstruit après inventaire

[ ] ClosingReadiness est évalué

[ ] controls bloquants empêchent close

[ ] closing entries utilisent le PostingService normal

[ ] temporary accounts sont policy-driven

[ ] POST_CLOSING est reconstruit

[ ] CLOSED bloque posting normal

[ ] reopening est explicite

[ ] reopening est auditée

[ ] reopening ne supprime aucun historique

[ ] close revision est versionnée

[ ] opening balances dérivent du post-closing

[ ] opening generation est idempotente

[ ] policies/reference snapshot sont figés pour la close

[ ] les tests P0 couvrent cut-off, adjustments, close, reopen et opening
```

---

# 283. Ordre d'implémentation recommandé

## CLOSE-00 - Period lifecycle

```text
AccountingPeriodStatus

OPEN

REVIEW

CLOSING

CLOSED

transitions
```

---

## CLOSE-01 - ClosingRun

```text
ClosingRun

ClosingStage

ClosingPipelineDefinition
```

---

## CLOSE-02 - Readiness

```text
ClosingControlDefinition

ClosingReadinessResult

AccountingControlPort
```

---

## CLOSE-03 - Cut-off primitives

```text
CutOffReview

AdjustmentProposal

AccruedExpense

AccruedIncome

PrepaidExpense

DeferredIncome
```

---

## CLOSE-04 - Reversal scheduling

```text
AdjustmentReversalPolicy

automatic reversal via ReversalService
```

---

## CLOSE-05 - Specialized domain integration

```text
InventoryClosingPort

FixedAssetDepreciationPort

ImpairmentAssessmentPort

ProvisionAssessmentPort
```

---

## CLOSE-06 - Adjustment posting

```text
AdjustmentRun

approval

JournalEntryProposal

Posting
```

---

## CLOSE-07 - Closing entries

```text
TemporaryAccountPolicy

result transfer

ClosingEntryProposal
```

---

## CLOSE-08 - Final close

```text
POST_CLOSING

final controls

AccountingPeriodClosed
```

---

## CLOSE-09 - Reopen

```text
ReopenPolicy

ReopenPeriodCommand

CloseRevision

impact analysis
```

---

## CLOSE-10 - Opening balances

```text
OpeningBalancePolicy

OpeningBalanceRun
```

---

# 284. Démonstrateur P0.9

Scénario recommandé :

```text
1. Create FiscalYear N

2. Create December period OPEN

3. Post ordinary December entries

4. Start ClosingRun

5. Move period OPEN -> REVIEW

6. Build BEFORE_ADJUSTMENTS balance

7. Detect accrued expense:
      service consumed in December
      invoice not received

8. Approve adjustment

9. Create JournalEntryProposal

10. Validate / Post ADJUSTING entry

11. Detect deferred income

12. Post deferral adjustment

13. Run depreciation adapter

14. Post depreciation adjustments

15. Run impairment review

16. Run provision review

17. Rebuild ADJUSTED balance

18. Run closing controls

19. Move REVIEW -> CLOSING

20. Generate closing entries

21. Validate / Post closing entries

22. Build POST_CLOSING balance

23. Verify temporary accounts according to policy

24. Close period

25. Verify ordinary posting rejected

26. Generate N+1 opening balance run
```

---

# 285. Démonstrateur de réouverture

```text
1. Period CLOSED revision 1

2. Discover late material adjustment

3. Execute ReopenPeriodCommand
      reason required

4. Move CLOSED -> REVIEW

5. Previous report snapshot remains immutable
      but marked stale/superseded as applicable

6. Reverse / replace affected posted closing or adjustment entries

7. Post late adjustment

8. Run new ClosingRun

9. Build new ADJUSTED / POST_CLOSING balances

10. Close period revision 2

11. Regenerate N+1 opening balances if impacted
```

---

# 286. Matrice responsabilité / capability

| Capability | Closing | Policies | Specialized Domain | Posting | Controls |
|---|---:|---:|---:|---:|---:|
| Détecter cut-off | orchestre | définit règles | peut fournir événements | non | vérifie |
| Mesurer accrual | non | oui | Accruals | non | vérifie |
| Calculer amortissement | non | policy | Fixed Assets | non | vérifie |
| Valoriser stock | non | policy | Inventory | non | vérifie |
| Evaluer provision | non | policy | Provisions | non | vérifie |
| Créer proposition | orchestre | oui | oui | non | non |
| Poster écriture | non | non | non | **oui** | non |
| Construire balance | non | non | non | non | Ledger |
| Décider readiness | orchestre | policy | non | non | **oui** |
| Fermer période | **oui** | policy | non | non | précondition |
| Réouvrir période | **oui** | policy | non | non | impact |

---

# 287. Matrice des principales opérations d'inventaire

| Opération | Recognition | Measurement | Auto reversal possible | Specialized context |
|---|---|---|---|---|
| Charge à payer | AccrualPolicy | AccrualPolicy | Oui | Accruals |
| Produit à recevoir | AccrualPolicy | AccrualPolicy | Oui | Accruals |
| Charge constatée d'avance | DeferralPolicy | AllocationPolicy | Oui | Accruals |
| Produit constaté d'avance | DeferralPolicy | AllocationPolicy | Oui | Accruals |
| Stock | InventoryPolicy | InventoryValuationPolicy | Généralement non simple | Inventory |
| Amortissement | DepreciationPolicy | DepreciationPolicy | Non par défaut | Fixed Assets |
| Dépréciation | ImpairmentPolicy | ImpairmentPolicy | Reprise selon policy | Fixed Assets / relevant domain |
| Provision | ProvisionRecognitionPolicy | ProvisionMeasurementPolicy | Revue/reprise selon policy | Provisions |

---

# 288. Matrice source doctrinale vs architecture

| Concept doctrinal | Traduction PyAccountingKit |
|---|---|
| Régularisations de fin d'exercice | `AdjustmentRun` |
| Charges à payer | `AccruedExpenseCase` |
| Produits à recevoir | `AccruedIncomeCase` |
| Charges constatées d'avance | `PrepaidExpenseCase` |
| Produits constatés d'avance | `DeferredIncomeCase` |
| Variations de stocks | `InventoryClosingResult` |
| Dotations aux amortissements | `DepreciationRun` |
| Dépréciations | `ImpairmentRun` |
| Provisions | `ProvisionCase` / `ProvisionReview` |
| Contre-passation | `ReversalService` + `AdjustmentReversalPolicy` |

---

# 289. Frontière avec le document Controls

Le document suivant sur Controls détaillera :

```text
control definitions

severity

blocking behavior

control runs

evidence

control history

audit integration
```

Ce document ne définit que les hooks nécessaires à Closing.

---

# 290. Frontière avec le document Persistence

Les garanties :

```text
locking

atomicity

optimistic revision

idempotency storage
```

seront détaillées dans :

```text
10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md
```

---

# 291. Frontière avec Financial Statements

Closing produit :

```text
ADJUSTED Trial Balance

POST_CLOSING Trial Balance
```

Financial Statements choisit la source adaptée à sa définition.

---

# 292. Frontière avec Regulatory Reporting

La clôture ne décide pas :

```text
la forme réglementaire des états
```

Elle fournit une source comptable finalisée et versionnée.

---

# 293. Frontière avec Financial Analysis

Financial Analysis consomme les résultats.

Il ne participe pas au close write-side.

---

# 294. Risques principaux

## RISK-CLOSE-001 - Clôture monolithique

Un unique job opaque rend le process non reprenable.

Réponse :

```text
ClosingRun + ClosingStage
```

---

## RISK-CLOSE-002 - Double moteur comptable

Risque de poster des ajustements directement.

Réponse :

```text
all entries use JournalEntry + PostingService
```

---

## RISK-CLOSE-003 - Règles nationales codées en dur

Réponse :

```text
AccountRole + AccountingPolicySet
```

---

## RISK-CLOSE-004 - Réouverture destructive

Réponse :

```text
append-oriented corrections
new close revision
immutable snapshots
```

---

## RISK-CLOSE-005 - Stale opening balances

Réponse :

```text
opening run linked to source close revision
```

---

## RISK-CLOSE-006 - Mélange Inventory / accounting inventory

Réponse :

```text
separate bounded contexts
```

---

## RISK-CLOSE-007 - Doctrine historique traitée comme droit actuel

Réponse :

```text
regulatory-accounting-data-framework remains authoritative
```

---

# 295. Conclusion

La clôture de PyAccountingKit devient une orchestration explicite de la logique suivante :

```text
BEFORE_ADJUSTMENTS
        |
        v
Accounting Inventory
        |
        +--> Cut-off
        +--> Stocks
        +--> Depreciation
        +--> Impairment
        +--> Provisions
        |
        v
ADJUSTING ENTRIES
        |
        v
ADJUSTED
        |
        v
CLOSING CONTROLS
        |
        v
CLOSING ENTRIES
        |
        v
POST_CLOSING
        |
        v
CLOSED
        |
        +--> OPENING N+1
        |
        +--> CONTROLLED REOPEN
```

Les principes structurants sont :

```text
Closing != status update

Closing != Posting

Cut-off != invoice-date logic

Provision != Impairment

Accounting Inventory != Inventory bounded context

Adjustment calculation != Posting

Posted adjustment != mutable

Reopen != delete history

Opening balance != mutable carry-forward

Regulatory rule != doctrinal example

All closing effects remain traceable to:
    source
    policy
    evidence
    entry
    control
    close revision
```

Cette architecture permet d'intégrer progressivement :

```text
Inventory

Fixed Assets

Accruals & Provisions

FX closing

Tax adjustments

Consolidation
```

sans fragiliser le coeur transactionnel défini dans `07`.

---

**Prochain document recommandé :**

```text
09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md
```


---

## Sources et références documentaires du projet

- 📕 [Comptabilité Générale — Système français et normes IFRS](../../books/Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md)
- 📂 [Référentiels réglementaires — Datasets](../../referentiels/datasets/)
- 📐 [Référentiels réglementaires — Schémas](../../referentiels/schemas/)
- 🏗️ [CFA FRA Django MVP Sprint 7 — Référence fonctionnelle](../../../resources/cfa_fra_django_mvp_sprint_7/)
- 📄 [CFA FRA — Document de conception](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md)

---

## Couverture dans les plans d'implémentation

Ce document est couvert par les plans suivants :

- [PLAN-04 — Subledgers & Financial Analysis (0.4.0)](../../plans/PLAN-04_SUBLEDGERS_FINANCIAL_ANALYSIS_0.4.0.md)
