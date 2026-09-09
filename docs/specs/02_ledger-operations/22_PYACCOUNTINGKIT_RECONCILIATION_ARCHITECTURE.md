# 22 - PyAccountingKit - Architecture de réconciliation

> **Projet** : PyAccountingKit  
> **Document** : `22_PYACCOUNTINGKIT_RECONCILIATION_ARCHITECTURE.md`  
> **Statut** : P2.2 - Architecture de réconciliation  
> **Langue** : Français  
> **Objet** : Définir un bounded context générique `Reconciliation` capable de rapprocher des sources comptables ou externes, de produire des candidats de matching, d'expliquer les écarts, de piloter leur résolution, de générer des contrôles et des preuves auditables sans dupliquer le moteur de posting, les sous-livres ou la consolidation.

---

# 1. Résumé exécutif

PyAccountingKit dispose déjà de plusieurs besoins de rapprochement :

```text
Bank Statement
    vs
General Ledger

Accounts Receivable Subledger
    vs
Receivable Control Account

Accounts Payable Subledger
    vs
Payable Control Account

Intercompany Entity A
    vs
Intercompany Entity B

External Confirmation
    vs
Internal Ledger

Imported Source Totals
    vs
Posted Accounting

Consolidation Source
    vs
Consolidation Ledger
```

Le P2.2 les généralise dans un bounded context unique :

```text
Reconciliation
```

Architecture cible :

```text
Source A Snapshot
        |
        +------------------+
                           |
                           v
                  Reconciliation Run
                           ^
                           |
        +------------------+
        |
Source B Snapshot
        |
        v
Normalization
        |
        v
Candidate Generation
        |
        v
Matching
        |
        +--> Exact Match
        +--> Partial Match
        +--> Many-to-Many Match
        +--> Suggested Match
        |
        v
Difference Analysis
        |
        +--> Timing
        +--> FX
        +--> Mapping
        +--> Missing Item
        +--> Amount Difference
        +--> Classification Error
        +--> Unknown
        |
        v
Resolution Workflow
        |
        +--> Accept Match
        +--> Adjust Source Mapping
        +--> Create Accounting Adjustment Proposal
        +--> Defer
        +--> Reject
        |
        v
Reconciliation Snapshot
        |
        v
Controls / Closing / Audit / Evidence
```

Principe central :

```text
Reconciliation
    detects and explains

but

does not silently rewrite accounting
```

---

# 2. Principes structurants

```text
Reconciliation != Posting

Reconciliation != Settlement

Reconciliation != AccountingMatch

Reconciliation != Consolidation Elimination

Match Candidate != Validated Match

Difference != Accounting Error

Tolerance != Write-Off

Fuzzy Similarity != Semantic Proof

Reconciliation Snapshot != Live Query Result

Resolution != Destructive Source Mutation
```

---

# 3. Objectifs

Le bounded context doit permettre de :

1. rapprocher deux sources ou plus ;
2. supporter des rapprochements comptables et opérationnels ;
3. supporter les rapprochements bancaires ;
4. supporter les sous-livres vs grand livre ;
5. supporter l'intercompany ;
6. supporter les confirmations externes ;
7. supporter les imports et sources historiques ;
8. produire des candidats de rapprochement ;
9. gérer les matches exacts ;
10. gérer les matches partiels ;
11. gérer les matches plusieurs-à-plusieurs ;
12. gérer les matches proposés avec validation humaine ;
13. distinguer les tolérances de matching des corrections comptables ;
14. classifier les différences ;
15. tracer les résolutions ;
16. générer des `JournalEntryProposal` lorsqu'un ajustement comptable est réellement requis ;
17. ne jamais poster directement depuis le moteur de réconciliation ;
18. produire des contrôles de clôture ;
19. produire des snapshots immuables ;
20. fournir un drill-down complet ;
21. supporter les devises et dates différentes ;
22. être déterministe lorsque les règles le permettent ;
23. être idempotent ;
24. supporter le replay ;
25. rester framework-neutral ;
26. être utilisable par `Consolidation` sans dupliquer sa logique ;
27. rester compatible avec les sources incomplètes ou historiques ;
28. exposer explicitement les cas `INDETERMINATE`.

---

# 4. Non-objectifs

Le moteur n'est pas :

```text
un moteur bancaire de paiement

un système de recouvrement

un ERP

un moteur de trésorerie complet

un moteur de détection de fraude

un moteur ML imposé pour le fuzzy matching

un moteur de consolidation

un moteur de posting alternatif
```

---

# 5. Bounded Context

Nom :

```text
Reconciliation
```

Dépendances principales :

```text
Ledger & Balances

Subledgers

Imports

Controls

Audit & Traceability

Closing

Consolidation

Accounting Core
```

---

# 6. Direction de dépendance

```text
Source Bounded Contexts
        |
        v
Reconciliation
```

Le moteur de réconciliation consomme des snapshots/read models.

Il ne doit pas prendre possession de leurs agrégats.

---

# 7. Reconciliation Types

```text
BANK

SUBLEDGER_GL

INTERCOMPANY

EXTERNAL_CONFIRMATION

STATEMENT_LEDGER

IMPORT_CONTROL

CONSOLIDATION

GENERIC

CUSTOM
```

---

# 8. `ReconciliationDefinition`

Aggregate / configuration versionnée :

```text
ReconciliationDefinition
|
+-- id
+-- code
+-- name
+-- reconciliation_type
+-- source_a_definition
+-- source_b_definition
+-- matching_policy
+-- difference_policy
+-- resolution_policy
+-- tolerance_policy
+-- control_policy
+-- effective_from
+-- effective_to?
+-- version
+-- status
```

---

# 9. `ReconciliationDefinitionStatus`

```text
DRAFT

ACTIVE

SUPERSEDED

RETIRED
```

---

# 10. Versioning

Toute modification de :

```text
matching rules

tolerances

source semantics

resolution rules
```

crée une nouvelle version.

---

# 11. `ReconciliationSourceDefinition`

```text
ReconciliationSourceDefinition
|
+-- source_type
+-- source_port
+-- scope_definition
+-- item_schema
+-- amount_semantics
+-- date_semantics
+-- currency_semantics
+-- identity_strategy
```

---

# 12. Source Types

```text
GENERAL_LEDGER

TRIAL_BALANCE

SUBLEDGER

BANK_STATEMENT

EXTERNAL_STATEMENT

IMPORT_BATCH

CONSOLIDATION_LEDGER

REPORT_SNAPSHOT

CUSTOM
```

---

# 13. Source Snapshot

Chaque run doit consommer des sources figées :

```text
ReconciliationSourceSnapshot
```

---

# 14. `ReconciliationSourceSnapshot`

```text
ReconciliationSourceSnapshot
|
+-- id
+-- source_type
+-- source_ref
+-- as_of
+-- period?
+-- currency_context
+-- source_watermark
+-- item_count
+-- amount_totals
+-- checksum
+-- completeness
+-- generated_at
```

---

# 15. Source completeness

```text
COMPLETE

PARTIAL

UNKNOWN
```

---

# 16. Partial source

Un rapprochement peut fonctionner sur une source partielle.

Mais son résultat peut devenir :

```text
INDETERMINATE
```

---

# 17. Source immutability

Les snapshots utilisés par un run finalisé sont immuables.

---

# 18. Live source

Interdit pour résultat publié :

```text
SELECT current rows while matching
```

sans snapshot/watermark.

---

# 19. `ReconciliationItem`

Objet normalisé :

```text
ReconciliationItem
|
+-- id
+-- source_snapshot_id
+-- source_side
+-- source_item_ref
+-- item_type
+-- business_reference?
+-- counterparty_ref?
+-- account_ref?
+-- document_ref?
+-- transaction_ref?
+-- accounting_date?
+-- value_date?
+-- due_date?
+-- amount
+-- currency
+-- functional_amount?
+-- dimensions
+-- provenance
```

---

# 20. Source side

```text
A

B

C...
```

Le P2.2 standardise A/B mais prépare le multi-source.

---

# 21. Amount sign semantics

Chaque source doit définir :

```text
signed amount semantics
```

---

# 22. No universal sign convention

Interdit :

```text
bank debit always negative
```

comme vérité générique.

---

# 23. `AmountNormalizationPolicy`

```text
source_sign_convention

target_sign_convention

rounding

currency_conversion?
```

---

# 24. Reconciliation normalization

```text
Raw Source Item
    ↓
Source Adapter
    ↓
ReconciliationItem
```

---

# 25. Adapter responsibilities

Les adapters traduisent :

```text
source field names

signs

dates

identifiers

currencies
```

vers le modèle générique.

---

# 26. Core responsibilities

Le core gère :

```text
candidate generation

matching

difference classification

resolution state

controls

evidence
```

---

# 27. Reconciliation Scope

```text
ReconciliationScope
|
+-- entity_id?
+-- group_id?
+-- account_scope?
+-- partner_scope?
+-- period?
+-- as_of?
+-- currencies?
+-- dimensions?
```

---

# 28. Scope compatibility

Deux sources doivent être comparables sur un scope explicite.

---

# 29. Scope mismatch

Doit produire :

```text
ReconciliationScopeMismatchError
```

ou `INDETERMINATE` selon mode.

---

# 30. `ReconciliationRun`

Aggregate Root :

```text
ReconciliationRun
|
+-- id
+-- definition_id
+-- definition_version
+-- scope
+-- source_snapshots
+-- status
+-- stages
+-- metrics
+-- findings
+-- snapshot_ref?
+-- revision
+-- created_at
+-- completed_at?
```

---

# 31. Run status

```text
CREATED

COLLECTING

NORMALIZING

MATCHING

REVIEWING

RESOLVING

VALIDATING

COMPLETED

FAILED

SUPERSEDED
```

---

# 32. Run pipeline

```text
1. Resolve definition

2. Capture source snapshots

3. Validate scope compatibility

4. Normalize items

5. Generate candidates

6. Apply deterministic matching

7. Apply permitted tolerant matching

8. Generate suggested matches

9. Classify residual differences

10. Review/resolve

11. Run controls

12. Publish reconciliation snapshot
```

---

# 33. Matching hierarchy

Recommended order :

```text
1. Explicit stable identity

2. Exact business reference

3. Exact structured key

4. Exact amount/date/counterparty rule

5. Partial deterministic allocation

6. Tolerance-based deterministic rule

7. Heuristic/fuzzy candidate

8. Manual
```

---

# 34. Deterministic before heuristic

Règle P2.2 :

```text
deterministic matching is preferred
```

---

# 35. `MatchingPolicy`

```text
MatchingPolicy
|
+-- id
+-- version
+-- strategies
+-- precedence
+-- tolerance_policy
+-- auto_accept_rules
+-- review_rules
+-- ambiguity_policy
```

---

# 36. Matching Strategies

```text
IDENTITY

REFERENCE

COMPOSITE_KEY

AMOUNT_DATE

PARTIAL_ALLOCATION

TOLERANCE

HEURISTIC

FUZZY

MANUAL

CUSTOM
```

---

# 37. `MatchingStrategy`

Protocol :

```python
class MatchingStrategy(Protocol):
    def generate_candidates(
        self,
        context: "MatchingContext",
    ) -> tuple["MatchCandidate", ...]:
        ...
```

---

# 38. Strategy is pure where possible

Une strategy de matching :

```text
does not post

does not mutate source

does not approve itself
```

---

# 39. `MatchCandidate`

```text
MatchCandidate
|
+-- id
+-- run_id
+-- source_item_refs
+-- target_item_refs
+-- proposed_allocations
+-- strategy
+-- score?
+-- rationale
+-- deterministic
+-- ambiguity
+-- review_required
+-- status
```

---

# 40. Candidate status

```text
PROPOSED

AUTO_ACCEPTABLE

REVIEW_REQUIRED

ACCEPTED

REJECTED

EXPIRED
```

---

# 41. Candidate != Match

Toujours.

---

# 42. Confidence score

Un score de similarité :

```text
does not authorize accounting action
```

---

# 43. Auto-accept

Doit être défini par :

```text
MatchingPolicy
```

et non seulement :

```text
score >= 0.9
```

---

# 44. Ambiguity

Si plusieurs candidats valides sont équivalents :

```text
AMBIGUOUS
```

et review.

---

# 45. `MatchAmbiguity`

```text
NONE

LOW

MULTIPLE_EXACT

MULTIPLE_TOLERANT

UNRESOLVED
```

---

# 46. `ReconciliationMatch`

Objet validé :

```text
ReconciliationMatch
|
+-- id
+-- run_id
+-- matching_type
+-- allocations
+-- matched_amount
+-- residual_amount
+-- status
+-- validated_by?
+-- validated_at?
+-- evidence
```

---

# 47. Matching Types

```text
ONE_TO_ONE

ONE_TO_MANY

MANY_TO_ONE

MANY_TO_MANY

PARTIAL
```

---

# 48. `MatchAllocation`

```text
MatchAllocation
|
+-- source_item_id
+-- target_item_id
+-- allocated_amount
+-- currency
+-- normalized_amount?
```

---

# 49. Allocation invariant

```text
allocated amount
<=
available unmatched amount
```

sur chaque item.

---

# 50. Many-to-many

Exemple :

```text
3 bank transactions
    vs
2 ledger entries
```

peuvent constituer un groupe de match.

---

# 51. Matching group

```text
MatchGroup
```

peut encapsuler les allocations.

---

# 52. Full match

```text
residual = 0
```

après normalisation/tolerance explicitement appliquée.

---

# 53. Partial match

```text
residual != 0
```

et reste visible.

---

# 54. Tolerance

```text
ReconciliationTolerancePolicy
```

---

# 55. `ReconciliationTolerancePolicy`

```text
absolute_amount?

relative_amount?

date_days?

fx_amount?

rounding_amount?

currency_scope

handling

version
```

---

# 56. Tolerance handling

```text
MATCH_WITH_RESIDUAL

REVIEW_REQUIRED

REJECT

CREATE_ADJUSTMENT_CANDIDATE
```

---

# 57. Tolerance != Write-Off

Règle ferme :

```text
tolerance is a comparison rule

not a permission to erase accounting difference
```

---

# 58. Difference

Objet :

```text
ReconciliationDifference
```

---

# 59. `ReconciliationDifference`

```text
ReconciliationDifference
|
+-- id
+-- run_id
+-- source_item_refs
+-- target_item_refs
+-- difference_type
+-- amount?
+-- currency?
+-- cause
+-- status
+-- materiality?
+-- evidence
+-- resolution_ref?
```

---

# 60. Difference Types

```text
UNMATCHED_SOURCE

UNMATCHED_TARGET

AMOUNT_DIFFERENCE

DATE_DIFFERENCE

FX_DIFFERENCE

MAPPING_DIFFERENCE

CLASSIFICATION_DIFFERENCE

DUPLICATE_CANDIDATE

MISSING_COUNTERPART

TIMING_DIFFERENCE

ROUNDING_DIFFERENCE

OTHER
```

---

# 61. Difference cause

Distincte du type technique.

---

# 62. Cause catalogue

```text
TIMING

LATE_POSTING

MISSING_POSTING

DUPLICATE_POSTING

MAPPING_ERROR

SOURCE_ERROR

BANK_FEE

FX

ROUNDING

UNRECORDED_TRANSACTION

WRONG_COUNTERPARTY

WRONG_ACCOUNT

UNKNOWN

CUSTOM
```

---

# 63. Difference status

```text
OPEN

UNDER_REVIEW

EXPLAINED

RESOLVED

DEFERRED

ACCEPTED_EXCEPTION

REOPENED
```

---

# 64. Explained != Resolved

Une différence peut être comprise mais encore non corrigée.

---

# 65. `ResolutionCase`

Aggregate / entity :

```text
ResolutionCase
|
+-- id
+-- difference_id
+-- resolution_type
+-- proposed_action
+-- status
+-- owner?
+-- reviewer?
+-- due_date?
+-- evidence
+-- accounting_adjustment_ref?
+-- source_correction_ref?
```

---

# 66. Resolution Types

```text
NO_ACTION_EXPLAINED

SOURCE_MAPPING_UPDATE

SOURCE_CORRECTION

ACCOUNTING_ADJUSTMENT

COUNTERPARTY_CONFIRMATION

TIMING_CLEARING

WRITE_OFF_PROPOSAL

RECLASSIFICATION

DEFER

CUSTOM
```

---

# 67. `ResolutionStatus`

```text
PROPOSED

APPROVED

IN_PROGRESS

COMPLETED

REJECTED

CANCELLED
```

---

# 68. Accounting adjustment

Si une différence nécessite une écriture :

```text
ResolutionCase
    ↓
JournalEntryProposal
    ↓
normal Validation / Posting
```

---

# 69. No direct posting

Le moteur de réconciliation n'appelle pas un raccourci :

```text
force_post_difference()
```

---

# 70. Adjustment trace

L'écriture proposée conserve :

```text
reconciliation_run_id

difference_id

resolution_case_id

source evidence
```

---

# 71. Source correction

Peut signifier :

```text
correct ERP mapping

correct bank import

correct subledger reference
```

mais le bounded context ne modifie pas la source en silence.

---

# 72. External action

Peut émettre :

```text
ResolutionRequest
```

ou integration event.

---

# 73. Bank Reconciliation

Type :

```text
BANK
```

---

# 74. Bank sources

```text
BankStatementSnapshot
    vs
GeneralLedgerSnapshot
```

---

# 75. Bank Statement Item

Adapter vers :

```text
ReconciliationItem
```

avec dimensions :

```text
statement_line_id

bank_reference

value_date

transaction_date

amount

currency
```

---

# 76. Ledger bank item

Dimensions :

```text
journal_line_id

entry_number

account_id

accounting_date

reference

amount
```

---

# 77. Bank matching strategies

Exemples :

```text
exact bank reference

payment reference

exact amount/date

amount + date window

many bank lines to one batch entry

one bank line to many accounting entries
```

---

# 78. Bank balance reconciliation

Au niveau agrégé :

```text
Opening GL Bank Balance
+
Ledger Movements
vs
Bank Statement Closing Balance
+
Known Outstanding Items
```

selon définition.

---

# 79. No universal bank equation

Les comptes et sources peuvent avoir des conventions différentes.

La définition doit être configurable.

---

# 80. `BankReconciliationDefinition`

Specialization / config preset.

---

# 81. Outstanding checks/transfers

Peuvent être représentés comme :

```text
TimingDifference
```

---

# 82. Bank fee

Peut produire :

```text
ACCOUNTING_ADJUSTMENT
```

candidate.

---

# 83. Interest / fee discovered by bank

Même pattern.

---

# 84. Duplicate bank line

Difference / control.

---

# 85. Bank reconciliation snapshot

```text
BankReconciliationSnapshot
```

peut être un wrapper spécialisé de `ReconciliationSnapshot`.

---

# 86. Subledger vs GL

Type :

```text
SUBLEDGER_GL
```

---

# 87. Source A

```text
SubledgerSnapshot
```

---

# 88. Source B

```text
GeneralLedger control account snapshot
```

---

# 89. Aggregate first

Recommandation :

```text
compare aggregate balance first
```

---

# 90. If aggregate matches

Pas nécessaire de faire un detailed item matching si le control scope ne l'exige pas.

---

# 91. If mismatch

Drill-down :

```text
partner

open item

journal line
```

---

# 92. Reuse P1.4

Le P2.2 ne remplace pas :

```text
SettlementAllocation

AccountingMatch
```

du sous-livre.

---

# 93. It consumes them

Comme evidence/read-model.

---

# 94. `SubledgerGLReconciliationDefinition`

Peut utiliser :

```text
control account

subledger type

as_of

currency
```

---

# 95. Control

```text
SUBLEDGER_GL_RECONCILED
```

continue d'exister.

Le bounded context fournit désormais le moteur générique qui le calcule.

---

# 96. Intercompany Reconciliation

Type :

```text
INTERCOMPANY
```

---

# 97. Use by Consolidation

`Consolidation` peut déléguer :

```text
candidate matching

difference classification

review workflow
```

au moteur de réconciliation.

---

# 98. Consolidation remains owner of elimination

Important :

```text
Reconciliation:
    matches and explains

Consolidation:
    eliminates
```

---

# 99. Intercompany sources

```text
Entity A IC positions

Entity B reciprocal positions
```

---

# 100. Counterparty required where available

---

# 101. Intercompany match

Peut être matérialisé comme :

```text
ReconciliationMatch
```

puis référencé par :

```text
IntercompanyMatch
```

dans Consolidation.

---

# 102. No duplicate truth

Une seule source d'état de match doit être choisie dans l'implémentation.

---

# 103. Recommended

Le bounded context `Reconciliation` détient :

```text
match evidence
difference state
resolution
```

La consolidation détient :

```text
elimination decision
elimination entry
```

---

# 104. External Confirmation

Type :

```text
EXTERNAL_CONFIRMATION
```

---

# 105. Use cases

```text
bank confirmation

customer balance confirmation

supplier confirmation

loan balance confirmation

custodian confirmation
```

---

# 106. Source A

Internal accounting/subledger.

---

# 107. Source B

External artifact / confirmation.

---

# 108. `ExternalConfirmationSnapshot`

```text
source_party

confirmation_date

confirmed_amount

currency

scope

artifact_ref

checksum
```

---

# 109. External confirmation provenance

Mandatory.

---

# 110. Human evidence

Possible :

```text
signed PDF

email attachment

API response

external statement
```

---

# 111. Artifact content

Le core consomme une représentation normalisée.

---

# 112. Document parser

Adapter responsibility.

---

# 113. Statement-to-Ledger

Type :

```text
STATEMENT_LEDGER
```

Générique pour :

```text
card processor settlement

payment provider statement

custodian statement

loan statement

tax statement
```

---

# 114. Import Control

Type :

```text
IMPORT_CONTROL
```

---

# 115. Example

```text
source file totals
    vs
posted import results
```

---

# 116. FEC control

Peut vérifier :

```text
source debit total

source credit total

imported debit total

imported credit total

entry count

line count
```

---

# 117. No import reprocessing from reconciliation

Le moteur peut demander une résolution :

```text
REPROCESS_IMPORT
```

via external action.

---

# 118. Consolidation reconciliation

Type :

```text
CONSOLIDATION
```

Exemples :

```text
entity packages vs group mapping

source contributions vs consolidated TB

NCI rollforward

elimination totals
```

---

# 119. Multi-source future

Some reconciliations need :

```text
A vs B vs C
```

P2.2 core targets A/B but data model should avoid hardcoding exactly two sides everywhere.

---

# 120. `ReconciliationSide`

```text
side_id

label

source_snapshot_ref
```

---

# 121. Matching identity strategies

```text
SOURCE_STABLE_ID

BUSINESS_REFERENCE

COMPOSITE_REFERENCE

HASHED_CONTENT

CUSTOM
```

---

# 122. Stable source ID

Preferred.

---

# 123. Source hash

Useful when no stable business identity.

---

# 124. Hash != semantic identity

---

# 125. Duplicate detection

Separate from matching.

---

# 126. `DuplicateCandidate`

Can exist within one side.

---

# 127. Duplicate resolution

May be :

```text
valid repetition

source duplicate

posting duplicate

unknown
```

---

# 128. Matching by date

Dates can include :

```text
transaction_date

accounting_date

value_date

due_date
```

---

# 129. `DateMatchingPolicy`

```text
source_date_field

target_date_field

exact_or_window

window_days
```

---

# 130. Date tolerance

Does not change original dates.

---

# 131. Matching by reference

Normalize separately.

---

# 132. `ReferenceNormalizationPolicy`

Possible rules :

```text
case folding

whitespace normalization

separator stripping

prefix normalization

custom
```

---

# 133. No destructive normalization

Preserve original source value.

---

# 134. Reference trace

Store :

```text
raw value

normalized value

normalization policy version
```

---

# 135. Currency matching

If currencies differ :

```text
FX policy required
```

---

# 136. `ReconciliationCurrencyPolicy`

```text
SAME_CURRENCY_ONLY

FUNCTIONAL_CURRENCY

REPORTING_CURRENCY

EXPLICIT_RATE

CUSTOM
```

---

# 137. FX rates

Pinned snapshot.

---

# 138. FX difference

Can classify :

```text
FX_DIFFERENCE
```

rather than force amount match.

---

# 139. Currency conversion != source mutation

---

# 140. Rounding

Explicit.

---

# 141. `ReconciliationRoundingPolicy`

```text
precision

rounding_mode

tolerance_after_rounding

version
```

---

# 142. Materiality

Distinct from tolerance.

---

# 143. `ReconciliationMaterialityPolicy`

```text
absolute_threshold?

relative_threshold?

scope

classification
```

---

# 144. Materiality affects review priority

Not the existence of a difference.

---

# 145. A difference below materiality still exists

---

# 146. `DifferencePriority`

```text
LOW

MEDIUM

HIGH

CRITICAL
```

---

# 147. Materiality != blocking

Controls decide blocking.

---

# 148. Reconciliation controls

Generic :

```text
RECONCILIATION_SOURCES_COMPLETE

RECONCILIATION_SCOPE_COMPATIBLE

RECONCILIATION_SOURCE_TOTALS_VALID

RECONCILIATION_MATCHING_COMPLETE

RECONCILIATION_DIFFERENCES_REVIEWED

RECONCILIATION_BLOCKING_DIFFERENCES_RESOLVED

RECONCILIATION_SNAPSHOT_REPRODUCIBLE
```

---

# 149. Bank controls

```text
BANK_STATEMENT_BALANCE_RECONCILED

BANK_UNMATCHED_ITEMS_REVIEWED

BANK_TIMING_DIFFERENCES_REVIEWED
```

---

# 150. Subledger controls

```text
SUBLEDGER_GL_RECONCILED

OPEN_ITEM_BALANCE_RECONCILED
```

---

# 151. Intercompany controls

```text
INTERCOMPANY_POSITIONS_MATCHED

INTERCOMPANY_DIFFERENCES_REVIEWED
```

---

# 152. Import controls

```text
IMPORT_SOURCE_TOTAL_RECONCILED

IMPORT_SOURCE_COUNT_RECONCILED
```

---

# 153. Control execution

Reconciliation engine produces facts.

`Controls` decides :

```text
PASS / FAIL / WARNING / INDETERMINATE
```

---

# 154. `ReconciliationControlContext`

```text
run_id

snapshot_id

definition_version

scope

source_snapshots
```

---

# 155. Closing integration

A `ClosingPolicy` peut exiger :

```text
BANK reconciled

AR/AP reconciled

critical external balances reviewed
```

---

# 156. Closing uses control results

Not raw reconciliation implementation.

---

# 157. Reconciliation close gate

Optional :

```text
RECONCILIATION_SIGNOFF_GATE
```

---

# 158. Sign-off

Reuse :

```text
SignOff
```

from controls/audit architecture.

---

# 159. Reconciliation sign-off

```text
prepared_by

reviewed_by

approved_by?
```

application policy-driven.

---

# 160. No RBAC in core

---

# 161. `ReconciliationSnapshot`

Immutable publication object :

```text
ReconciliationSnapshot
|
+-- id
+-- run_id
+-- definition_id
+-- definition_version
+-- scope
+-- source_snapshot_refs
+-- source_checksums
+-- matches
+-- differences
+-- resolution_summary
+-- control_run_refs
+-- metrics
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

# 163. Published immutable

Always.

---

# 164. Rerun

New :

```text
ReconciliationRun
```

not mutation of finalized run.

---

# 165. Source change

If source snapshot changes :

```text
old reconciliation remains

new run required
```

---

# 166. Freshness

```text
CURRENT

STALE

SUPERSEDED

UNKNOWN
```

---

# 167. `ReconciliationFreshness`

Derived from source watermarks/snapshots.

---

# 168. Drill-down

```text
Reconciliation Summary
    ↓
Match / Difference
    ↓
ReconciliationItem
    ↓
Source Snapshot
    ↓
Source object
```

---

# 169. Accounting drill-down

```text
Difference
    ↓
JournalEntryProposal?
    ↓
JournalEntry
    ↓
JournalEntryLine
```

---

# 170. Bank drill-down

```text
Match
    ├─ BankStatementLine
    └─ JournalEntryLine
```

---

# 171. Subledger drill-down

```text
Difference
    ├─ DueItem / Partner balance
    └─ Control account lines
```

---

# 172. Intercompany drill-down

```text
Difference
    ├─ Entity A source
    └─ Entity B source
```

---

# 173. `ReconciliationDrilldownQuery`

Protocol.

---

# 174. Evidence

Each match/difference can reference :

```text
SOURCE_ITEM

SOURCE_ARTIFACT

LEDGER_LINE

SUBLEDGER_ITEM

BANK_STATEMENT_LINE

EXTERNAL_CONFIRMATION

MATCH_RULE

REVIEW_DECISION

ADJUSTMENT_ENTRY

CONTROL_RESULT
```

---

# 175. Provenance

Use common `ProvenanceRef`.

---

# 176. Lineage

Use common `LineageEdge`.

---

# 177. Trace Context

Carry :

```text
correlation_id

causation_id

request_id

actor
```

---

# 178. Audit events

```text
RECONCILIATION_DEFINITION_CREATED

RECONCILIATION_DEFINITION_ACTIVATED

RECONCILIATION_RUN_STARTED

RECONCILIATION_SOURCE_CAPTURED

MATCH_CANDIDATE_CREATED

MATCH_ACCEPTED

MATCH_REJECTED

DIFFERENCE_CREATED

DIFFERENCE_CLASSIFIED

RESOLUTION_CASE_CREATED

RESOLUTION_APPROVED

ACCOUNTING_ADJUSTMENT_PROPOSED

RECONCILIATION_RUN_COMPLETED

RECONCILIATION_SNAPSHOT_PUBLISHED

RECONCILIATION_RUN_REOPENED
```

---

# 179. Domain events

```text
ReconciliationCompleted

MatchAccepted

DifferenceResolved

ReconciliationSnapshotPublished
```

---

# 180. DomainEvent != AuditEvent

Toujours.

---

# 181. Reproducibility envelope

```text
ReconciliationReproducibilityEnvelope
|
+-- framework_version
+-- definition_version
+-- source_snapshot_refs
+-- source_checksums
+-- normalization_policy_versions
+-- matching_policy_version
+-- tolerance_policy_version
+-- currency_snapshot?
+-- control_versions
+-- output_checksum
```

---

# 182. Replay

Same envelope :

```text
same semantic matches/differences
```

---

# 183. Heuristic replay

If heuristic implementation evolves :

```text
strategy version
```

must be pinned.

---

# 184. ML/fuzzy future

If added :

```text
model version

feature config

threshold policy

random seed if applicable
```

must be part of reproducibility.

---

# 185. But ML not mandatory

P2.2 works entirely without ML.

---

# 186. Fuzzy candidate safety

Fuzzy engine may only generate :

```text
candidates
```

unless policy explicitly qualifies deterministic auto-accept behavior.

---

# 187. Human review

Review decision must be audit-trailed.

---

# 188. Manual match

Requires :

```text
actor

reason?

evidence?

```

depending policy.

---

# 189. Override

A user may accept a match outside normal tolerance only via :

```text
explicit override / review
```

---

# 190. Override cannot violate hard allocation invariant

No over-allocation.

---

# 191. Match reversibility

A validated match can be :

```text
UNMATCHED / REVERSED
```

through explicit command.

---

# 192. No deletion

Preserve history.

---

# 193. `ReverseReconciliationMatch`

Creates audit record and restores unmatched amounts.

---

# 194. Difference reopening

Resolved difference can become :

```text
REOPENED
```

if source changes or resolution fails.

---

# 195. Idempotence

Critical operations :

```text
capture source

start run

auto-match

accept match

publish snapshot

create adjustment proposal
```

---

# 196. Idempotency scope

```text
definition

scope

period/as_of

source snapshot IDs

operation
```

---

# 197. Duplicate run

Same definition + exact source snapshots can return prior result if policy permits.

---

# 198. `ReconciliationFingerprint`

```text
definition_version

scope hash

source checksums

policy versions
```

---

# 199. Concurrency - accepting same candidate

Two reviewers cannot double-accept allocations.

---

# 200. Lock

Protect :

```text
candidate/match state

item available unmatched amount
```

---

# 201. Concurrency - source rerun

Published snapshot independent.

---

# 202. Concurrency - adjustment creation

Same difference cannot generate duplicate adjustment unintentionally.

---

# 203. `AdjustmentProposalIdempotencyKey`

Based on :

```text
difference_id

resolution_version
```

---

# 204. Repository ports

```text
ReconciliationDefinitionRepository

ReconciliationRunRepository

ReconciliationMatchRepository

ReconciliationDifferenceRepository

ResolutionCaseRepository

ReconciliationSnapshotRepository
```

---

# 205. Query ports

```text
ReconciliationSummaryQuery

ReconciliationMatchQuery

ReconciliationDifferenceQuery

ReconciliationDrilldownQuery

ReconciliationHistoryQuery
```

---

# 206. Source ports

```text
LedgerReconciliationSourcePort

TrialBalanceReconciliationSourcePort

SubledgerReconciliationSourcePort

BankStatementSourcePort

ExternalConfirmationSourcePort

ImportReconciliationSourcePort

IntercompanyPositionSourcePort
```

---

# 207. Generic source protocol

```python
class ReconciliationSourcePort(Protocol):
    def snapshot(
        self,
        request: "ReconciliationSourceRequest",
    ) -> "ReconciliationSourceSnapshot":
        ...
```

---

# 208. Bank adapter

```text
CSV

CAMT

MT940

API

custom
```

possible, but parsers are adapters.

---

# 209. No bank format in core

---

# 210. External confirmation adapter

Can parse/normalize external systems.

---

# 211. Artifact storage

Use :

```text
ArtifactStorePort
```

for source evidence.

---

# 212. Application Services

```text
CreateReconciliationDefinition

ActivateReconciliationDefinition

StartReconciliationRun

CaptureReconciliationSources

GenerateMatchCandidates

AutoMatchReconciliation

AcceptMatch

RejectMatch

ReverseMatch

ClassifyDifference

CreateResolutionCase

ApproveResolution

CreateAccountingAdjustmentProposal

CompleteReconciliationRun

PublishReconciliationSnapshot

ReopenDifference

RerunReconciliation
```

---

# 213. Public API

New facade :

```text
accounting.reconciliation
```

---

# 214. API - create definition

```python
definition = accounting.reconciliation.create_definition(
    code="BANK_MAIN",
    reconciliation_type="BANK",
    ...
)
```

---

# 215. API - start

```python
run = accounting.reconciliation.start(
    definition_id=definition.id,
    as_of=date(2026, 12, 31),
)
```

---

# 216. API - candidates

```python
candidates = accounting.reconciliation.generate_candidates(
    run_id=run.id,
)
```

---

# 217. API - auto match

```python
result = accounting.reconciliation.auto_match(
    run_id=run.id,
)
```

---

# 218. API - accept

```python
match = accounting.reconciliation.accept_match(
    candidate_id=candidate.id,
    context=review_context,
)
```

---

# 219. API - difference

```python
accounting.reconciliation.classify_difference(
    difference_id=difference.id,
    cause="TIMING",
)
```

---

# 220. API - resolution

```python
resolution = accounting.reconciliation.create_resolution(
    difference_id=difference.id,
    resolution_type="ACCOUNTING_ADJUSTMENT",
)
```

---

# 221. API - adjustment proposal

```python
proposal = accounting.reconciliation.create_adjustment_proposal(
    resolution_id=resolution.id,
)
```

---

# 222. API - publish

```python
snapshot = accounting.reconciliation.publish(
    run_id=run.id,
)
```

---

# 223. API - drilldown

```python
detail = accounting.reconciliation.drilldown(
    snapshot_id=snapshot.id,
    target_ref=difference.id,
)
```

---

# 224. ORM neutrality

Same API with :

```text
InMemory

Django/PostgreSQL

SQLAlchemy/PostgreSQL
```

---

# 225. Package target

```text
src/pyaccountingkit/domain/reconciliation/
|
+-- definitions/
|   +-- definition.py
|   +-- scope.py
|
+-- sources/
|   +-- snapshot.py
|   +-- item.py
|   +-- normalization.py
|
+-- matching/
|   +-- policy.py
|   +-- strategy.py
|   +-- candidate.py
|   +-- match.py
|   +-- allocation.py
|
+-- differences/
|   +-- difference.py
|   +-- classification.py
|
+-- resolutions/
|   +-- resolution.py
|   +-- adjustment.py
|
+-- runs/
|   +-- reconciliation_run.py
|
+-- snapshots/
|   +-- reconciliation_snapshot.py
|
+-- controls/
|   +-- definitions.py
|
+-- queries/
    +-- drilldown.py
```

---

# 226. Application target

```text
src/pyaccountingkit/application/reconciliation/
|
+-- create_definition.py
+-- start_run.py
+-- capture_sources.py
+-- generate_candidates.py
+-- auto_match.py
+-- accept_match.py
+-- reject_match.py
+-- reverse_match.py
+-- classify_difference.py
+-- resolve_difference.py
+-- create_adjustment_proposal.py
+-- complete_run.py
+-- publish_snapshot.py
```

---

# 227. Adapter target

```text
src/pyaccountingkit/adapters/reconciliation/
|
+-- in_memory/
+-- django/
+-- sqlalchemy/
+-- bank/
+-- external/
+-- import_sources/
```

---

# 228. Persistence

Tables possibles :

```text
reconciliation_definition

reconciliation_run

reconciliation_source_snapshot

reconciliation_item

match_candidate

reconciliation_match

match_allocation

reconciliation_difference

resolution_case

reconciliation_snapshot
```

---

# 229. ReconciliationItem storage

Large volume concern.

Can be :

```text
materialized table

artifact-backed snapshot

hybrid
```

adapter decision.

---

# 230. Source items immutable within run

---

# 231. Match allocations append-oriented

Accepted match history preserved.

---

# 232. Difference history

State transitions audited.

---

# 233. Optimistic concurrency

Recommended for :

```text
ReconciliationDefinition

ReconciliationRun

MatchCandidate

ReconciliationMatch

ResolutionCase
```

---

# 234. Pessimistic locking

Useful for :

```text
accepting competing matches

reversing match

publishing final snapshot
```

---

# 235. Query consistency

Published snapshot :

```text
strong immutable
```

Live run views :

```text
read-your-writes / current transaction
```

---

# 236. Performance objectives

Critical workloads :

```text
bank lines thousands/millions

ledger lines millions

AR/AP open items

IC positions
```

---

# 237. Performance pattern

```text
pre-filter

partition

exact matching

residual matching

heuristic matching
```

---

# 238. Partition keys

Possible :

```text
currency

account

counterparty

date bucket

entity pair

amount bucket
```

---

# 239. Avoid O(N²)

Never compare every item against every other item naively.

---

# 240. Candidate indexing

Adapters can use :

```text
hash maps

DB indexes

search structures
```

---

# 241. Matching batches

Process partition-wise.

---

# 242. Deterministic ordering

Candidates sorted by stable :

```text
strategy precedence

source item ID

target item ID

candidate ID
```

---

# 243. Pagination

Required for unmatched/differences.

---

# 244. Cursor pagination

Preferred.

---

# 245. Summary-first

UI/query path :

```text
totals
matched amount
unmatched amount
difference counts
then detail
```

---

# 246. `ReconciliationMetrics`

```text
source_a_total

source_b_total

matched_amount

unmatched_source_amount

unmatched_target_amount

difference_amount

match_rate

item_match_rate

difference_count

unresolved_count
```

---

# 247. Match rate semantics

Definition versioned.

---

# 248. No misleading percentage

Document numerator/denominator.

---

# 249. Observability metrics

```text
reconciliation_runs_total

reconciliation_duration

reconciliation_items_total

reconciliation_candidates_total

reconciliation_auto_matches_total

reconciliation_manual_matches_total

reconciliation_unmatched_amount

reconciliation_open_differences_total

reconciliation_adjustment_proposals_total

reconciliation_replay_mismatch_total
```

---

# 250. Logs

Context :

```text
definition_id

run_id

source_snapshot_ids

candidate_id

match_id

difference_id

resolution_id

correlation_id
```

---

# 251. No raw bank/private data in logs by default

---

# 252. Tracing spans

```text
capture_sources

normalize_items

partition_items

generate_exact_candidates

generate_tolerant_candidates

generate_heuristic_candidates

accept_match

classify_differences

run_controls

publish_snapshot
```

---

# 253. Error taxonomy

```text
ReconciliationError
|
+-- ReconciliationDefinitionNotFoundError
+-- ReconciliationDefinitionInactiveError
+-- ReconciliationSourceUnavailableError
+-- ReconciliationSourceIncompleteError
+-- ReconciliationScopeMismatchError
+-- ReconciliationNormalizationError
+-- MatchCandidateNotFoundError
+-- MatchCandidateAmbiguousError
+-- MatchAllocationError
+-- MatchOverAllocationError
+-- MatchConcurrencyConflictError
+-- DifferenceNotFoundError
+-- DifferenceAlreadyResolvedError
+-- ResolutionPolicyError
+-- AdjustmentProposalConflictError
+-- ReconciliationControlFailedError
+-- ReconciliationSnapshotIntegrityError
+-- ReconciliationReplayMismatchError
```

---

# 254. Fail-closed conditions

```text
missing mandatory source

scope incompatibility

ambiguous auto-match

over-allocation

missing required FX rate

source checksum mismatch

stale source at publication

blocking unresolved difference

invalid resolution policy
```

---

# 255. Warnings

```text
partial source

low-priority residual

fuzzy candidate

minor timing difference

materiality-low difference

source completeness unknown
```

---

# 256. Unit tests

```text
definition versioning

source normalization

sign normalization

candidate precedence

exact match

partial match

many-to-many match

over-allocation rejection

tolerance handling

difference classification

resolution workflow

snapshot immutability
```

---

# 257. Property-based tests

```text
allocated amount never exceeds available amount

sum matched + unmatched = source totals

reversing a match restores unmatched amounts

reordering source items does not change deterministic result

same fingerprint gives same deterministic output

Money uses Decimal exactly

normalization is idempotent where declared

published snapshot checksum deterministic
```

---

# 258. Golden - Bank one-to-one

```text
Bank line:
    100 EUR
    ref PAY-001

Ledger line:
    100 EUR
    ref PAY-001

Expected:
    exact match
    residual 0
```

---

# 259. Golden - Bank timing difference

```text
Bank:
    100 on 31/12

Ledger:
    100 on 02/01

Policy:
    date window 3 days

Expected:
    tolerant deterministic candidate
    timing classification
```

---

# 260. Golden - Bank fee

```text
Bank:
    -3 fee

Ledger:
    no matching item

Expected:
    unmatched bank item
    cause candidate BANK_FEE
    optional accounting adjustment proposal
    no direct posting
```

---

# 261. Golden - Subledger GL

```text
AR subledger:
    25,000

GL control:
    25,000

Expected:
    aggregate reconciliation PASS
```

---

# 262. Golden - Subledger mismatch

```text
AR:
    25,000

GL:
    24,950

Expected:
    difference 50
    detailed drill-down
```

---

# 263. Golden - Intercompany

```text
A -> B receivable:
    500

B -> A payable:
    500

Expected:
    match 500
    difference 0
    reconciliation complete
```

---

# 264. Golden - Intercompany mismatch

```text
A:
    500

B:
    490

Expected:
    match 490
    residual 10
    difference open
```

---

# 265. Golden - Import Control

```text
FEC source debit:
    100,000

Posted debit:
    100,000

Source lines:
    1,500

Posted lines:
    1,500

Expected:
    totals/counts reconciled
```

---

# 266. Golden - many-to-one

```text
Source:
    40
    60

Target:
    100

Expected:
    many-to-one match 100
```

---

# 267. Golden - ambiguity

```text
Source:
    100 ref X

Target A:
    100 ref X

Target B:
    100 ref X

Expected:
    MULTIPLE_EXACT
    review required
    no auto-match
```

---

# 268. Golden - tolerance != write-off

```text
Source:
    100.00

Target:
    99.98

Tolerance:
    0.05

Expected:
    match may be accepted by policy
    residual 0.02 remains represented/explained
    no hidden accounting write-off
```

---

# 269. Golden - source changed

```text
Published R1
depends on source snapshot S1

New source S2

Expected:
    R1 immutable
    freshness stale
    new run required
```

---

# 270. Concurrency tests

```text
two reviewers accept competing matches

match vs reverse match

publish vs source refresh

difference resolve vs reopen

duplicate adjustment proposal
```

---

# 271. Integration tests

```text
BankStatement adapter -> Reconciliation -> Ledger

SubledgerSnapshot -> Reconciliation -> GL Query

Intercompany positions -> Reconciliation -> Consolidation

FEC Import -> Reconciliation -> posted totals
```

---

# 272. Contract tests - source ports

Every source adapter :

```text
stable IDs

checksum

scope

currency

Decimal

provenance
```

---

# 273. Replay tests

Pinned :

```text
source snapshots

normalization policy

matching policy

tolerance policy

currency snapshot

strategy versions
```

=> same result.

---

# 274. Performance tests

Datasets :

```text
10k

100k

1M items
```

for exact matching paths.

---

# 275. No flaky performance gate

Use stable environment.

---

# 276. Security-adjacent tests

```text
no cross-entity leakage

no raw sensitive bank payload in logs

artifact authorization delegated to runtime

no arbitrary executable matching rule loaded from source data
```

---

# 277. Declarative rules

Can support a limited DSL later.

---

# 278. No arbitrary Python from dataset

---

# 279. Matching plugin safety

Custom strategy runs through trusted extension registration.

---

# 280. Public API extension

`16_PUBLIC_API_DESIGN` must later add :

```text
accounting.reconciliation
```

without changing existing façades.

---

# 281. Release impact

Addition P2.2 is a :

```text
MINOR
```

after 1.0 if backward-compatible.

---

# 282. Adapter contract

New reconciliation source ports require contract version management.

---

# 283. ADRs

| ID | Décision |
|---|---|
| ADR-REC-001 | `Reconciliation` est un bounded context distinct du Posting |
| ADR-REC-002 | Le moteur rapproche des snapshots/read models, pas des agrégats live |
| ADR-REC-003 | Les sources d'un run publié sont pinées et checksummées |
| ADR-REC-004 | Une source partielle reste explicitement `PARTIAL` |
| ADR-REC-005 | `ReconciliationItem` normalise les sources sans perdre la provenance |
| ADR-REC-006 | Aucune convention de signe n'est universelle dans le core |
| ADR-REC-007 | Les mappings de signe/date/devise sont gérés par policies/adapters |
| ADR-REC-008 | Les définitions de rapprochement sont versionnées |
| ADR-REC-009 | Le matching déterministe précède les heuristiques |
| ADR-REC-010 | Les stratégies ne postent ni ne mutent les sources |
| ADR-REC-011 | `MatchCandidate` est distinct de `ReconciliationMatch` |
| ADR-REC-012 | Un score de confiance n'autorise pas à lui seul un auto-match |
| ADR-REC-013 | Toute ambiguïté de match critique est fail-closed |
| ADR-REC-014 | Les matches one-to-one, one-to-many, many-to-one et many-to-many sont supportés |
| ADR-REC-015 | Les allocations ne dépassent jamais le montant unmatched disponible |
| ADR-REC-016 | Une tolerance est une règle de rapprochement, pas un write-off |
| ADR-REC-017 | Les différences restent visibles même sous le seuil de matérialité |
| ADR-REC-018 | `DifferenceType`, `Cause` et `Status` sont des concepts distincts |
| ADR-REC-019 | `EXPLAINED` ne signifie pas `RESOLVED` |
| ADR-REC-020 | Toute écriture corrective passe par `JournalEntryProposal` puis Posting normal |
| ADR-REC-021 | Le moteur ne modifie jamais silencieusement une source externe |
| ADR-REC-022 | Le rapprochement bancaire est une spécialisation du moteur générique |
| ADR-REC-023 | Les formats bancaires restent dans les adapters |
| ADR-REC-024 | Le rapprochement sous-livre/GL réutilise les snapshots P1.4 |
| ADR-REC-025 | Settlement/AccountingMatch et Reconciliation restent distincts |
| ADR-REC-026 | L'intercompany matching peut être délégué à Reconciliation |
| ADR-REC-027 | Consolidation reste propriétaire des éliminations |
| ADR-REC-028 | Les confirmations externes nécessitent provenance et checksum |
| ADR-REC-029 | Les parsers de confirmations sont des adapters |
| ADR-REC-030 | Les contrôles d'import peuvent réutiliser le moteur générique |
| ADR-REC-031 | Le core cible A/B mais prépare le multi-source |
| ADR-REC-032 | Les normalisations de référence préservent la valeur brute |
| ADR-REC-033 | Les FX de rapprochement utilisent des observations pinées |
| ADR-REC-034 | Matérialité, tolerance et blocking sont trois concepts distincts |
| ADR-REC-035 | Les controls consomment les faits du moteur de réconciliation |
| ADR-REC-036 | Closing dépend de résultats de controls, pas de l'implémentation du matching |
| ADR-REC-037 | Le sign-off réutilise Controls/Audit |
| ADR-REC-038 | Un `ReconciliationSnapshot` publié est immutable |
| ADR-REC-039 | Un rerun crée un nouveau run/snapshot |
| ADR-REC-040 | Un changement de source rend les résultats downstream stale sans réécriture |
| ADR-REC-041 | Le drill-down doit atteindre les éléments sources |
| ADR-REC-042 | Match, difference, resolution et adjustment conservent leur lineage |
| ADR-REC-043 | Le replay pinne toutes les versions de policies/strategies |
| ADR-REC-044 | Les modèles fuzzy/ML éventuels restent optionnels et versionnés |
| ADR-REC-045 | Une fuzzy match produit d'abord un candidat |
| ADR-REC-046 | Les décisions humaines de matching sont auditées |
| ADR-REC-047 | Un match validé est réversible sans suppression historique |
| ADR-REC-048 | Les commandes critiques sont idempotentes |
| ADR-REC-049 | Les acceptations concurrentes protègent les montants unmatched |
| ADR-REC-050 | Une difference ne peut générer deux ajustements comptables non intentionnels |
| ADR-REC-051 | Les repositories write et query ports restent séparés |
| ADR-REC-052 | Les adapters source implémentent un contrat commun de snapshot |
| ADR-REC-053 | Les items volumineux peuvent être materialized, artifact-backed ou hybrides selon adapter |
| ADR-REC-054 | Les algorithmes évitent les scans naïfs O(N²) |
| ADR-REC-055 | L'ordre de candidate generation est déterministe |
| ADR-REC-056 | Les métriques de match documentent leur numérateur/dénominateur |
| ADR-REC-057 | Les logs n'exposent pas les payloads bancaires sensibles par défaut |
| ADR-REC-058 | Les rules declaratives ne peuvent pas exécuter du code arbitraire |
| ADR-REC-059 | `accounting.reconciliation` est la façade publique cible |
| ADR-REC-060 | La réconciliation est un consommateur transversal, jamais une seconde source comptable canonique |

---

# 284. Critères d'acceptation P2.2

```text
[ ] Reconciliation bounded context défini

[ ] ReconciliationDefinition défini

[ ] définition versionnée

[ ] source definitions définies

[ ] source snapshots définis

[ ] source completeness définie

[ ] ReconciliationItem défini

[ ] sign normalization policy définie

[ ] ReconciliationScope défini

[ ] ReconciliationRun défini

[ ] pipeline défini

[ ] MatchingPolicy défini

[ ] matching strategy hierarchy définie

[ ] MatchCandidate défini

[ ] candidate != match explicite

[ ] ambiguity handling défini

[ ] ReconciliationMatch défini

[ ] one-to-many / many-to-many supportés

[ ] MatchAllocation invariant défini

[ ] tolerance policy définie

[ ] tolerance != write-off explicite

[ ] ReconciliationDifference défini

[ ] DifferenceType/Cause/Status distincts

[ ] ResolutionCase défini

[ ] adjustment proposal boundary définie

[ ] Bank Reconciliation définie

[ ] Subledger vs GL défini

[ ] Intercompany boundary définie

[ ] External Confirmation définie

[ ] Statement-to-Ledger défini

[ ] Import Control défini

[ ] currency matching défini

[ ] materiality vs tolerance distinguées

[ ] controls définis

[ ] Closing integration définie

[ ] SignOff integration définie

[ ] ReconciliationSnapshot défini

[ ] published snapshot immutable

[ ] freshness/staleness définie

[ ] drill-down complet défini

[ ] provenance/lineage définies

[ ] replay/reproducibility définis

[ ] idempotence définie

[ ] concurrency définie

[ ] repositories/ports/adapters définis

[ ] public API définie

[ ] tests unit/property/integration/concurrency/golden/replay définis
```

---

# 285. Ordre d'implémentation recommandé

## REC-00 - Primitives

```text
ReconciliationType

ReconciliationScope

SourceSide

DifferenceType

DifferenceCause
```

---

## REC-01 - Definitions

```text
ReconciliationDefinition

SourceDefinition

MatchingPolicy

TolerancePolicy
```

---

## REC-02 - Source Snapshots

```text
ReconciliationSourceSnapshot

ReconciliationItem

normalization
```

---

## REC-03 - Exact Matching

```text
identity

reference

composite key
```

---

## REC-04 - Partial / Many Matching

```text
partial

one-to-many

many-to-many

allocation guards
```

---

## REC-05 - Tolerance Matching

```text
amount

date

rounding

FX
```

---

## REC-06 - Candidates / Review

```text
candidate

ambiguity

accept/reject
```

---

## REC-07 - Differences

```text
classification

cause

priority

materiality
```

---

## REC-08 - Resolution

```text
resolution cases

adjustment proposals

external corrections
```

---

## REC-09 - Bank Reconciliation

```text
bank source adapter contract

ledger source

bank controls
```

---

## REC-10 - Subledger / GL

```text
aggregate

detail

P1.4 integration
```

---

## REC-11 - Intercompany

```text
counterparty matching

Consolidation integration
```

---

## REC-12 - External Confirmation / Import Control

```text
external artifacts

import totals
```

---

## REC-13 - Snapshot / Controls

```text
ReconciliationSnapshot

control sets

sign-off
```

---

## REC-14 - Replay / Qualification

```text
golden

concurrency

performance

replay
```

---

# 286. Démonstrateur P2.2 - Bank Reconciliation

```text
Bank source:
    line B001
    +1,000 EUR
    ref INV-123

Ledger:
    line L900
    +1,000 EUR
    ref INV-123

MatchingPolicy:
    reference + amount exact

Expected:
    exact match
    residual 0
    bank reconciliation control PASS
```

---

# 287. Démonstrateur - Bank fee adjustment

```text
Bank statement:
    -15 EUR fee

Ledger:
    no entry

Expected:
    unmatched source item
    cause = BANK_FEE
    resolution = ACCOUNTING_ADJUSTMENT
    JournalEntryProposal generated

Not:
    direct POSTED entry
```

---

# 288. Démonstrateur - Subledger vs GL

```text
AR subledger:
    80,000

GL customer control:
    80,000

Expected:
    aggregate match
    SUBLEDGER_GL_RECONCILED = PASS
```

---

# 289. Démonstrateur - Intercompany mismatch

```text
Entity A receivable from B:
    1,000

Entity B payable to A:
    980

Expected:
    matched 980
    difference 20
    review required

Consolidation:
    receives match/difference evidence

Reconciliation:
    does not post elimination
```

---

# 290. Démonstrateur - Many-to-many

```text
Source A:
    50
    70

Source B:
    40
    80

Totals:
    120 vs 120

Expected:
    one many-to-many MatchGroup
    allocations total 120
```

---

# 291. Démonstrateur - Ambiguous exact

```text
Source:
    ref X / 100

Targets:
    ref X / 100
    ref X / 100

Expected:
    ambiguity = MULTIPLE_EXACT
    no automatic acceptance
```

---

# 292. Démonstrateur - External confirmation

```text
Internal loan balance:
    500,000

External lender confirmation:
    500,000

Expected:
    exact aggregate match
    artifact checksum linked
    confirmation evidence retained
```

---

# 293. Démonstrateur - Replay

Pinned :

```text
definition v4

source snapshot A7

source snapshot B3

matching policy v8

tolerance v2

normalization v5

FX snapshot FX1
```

Expected :

```text
same accepted deterministic matches

same differences

same snapshot checksum
```

---

# 294. Matrice responsabilités

| Capability | Source Context | Reconciliation | Posting | Controls | Consolidation |
|---|---:|---:|---:|---:|---:|
| Source transaction | **oui** | non | non | non | non |
| Source snapshot | expose | consomme | non | consomme | consomme |
| Candidate matching | non | **oui** | non | non | utilise |
| Match validation | non | **oui** | non | vérifie | utilise |
| Difference classification | non | **oui** | non | vérifie | utilise |
| Accounting correction | source possible | propose | **oui** | vérifie | non |
| Elimination | non | evidence | non | vérifie | **oui** |
| Reconciliation controls | non | faits | non | **oui** | consomme |
| Sign-off | non | prépare | non | **oui** | consomme |

---

# 295. Matrice des concepts à ne pas confondre

| Concept | Signification |
|---|---|
| `Settlement` | règlement économique |
| `AccountingMatch` | lettrage comptable |
| `MatchCandidate` | proposition de rapprochement |
| `ReconciliationMatch` | rapprochement validé entre sources |
| `ReconciliationDifference` | écart identifié |
| `ResolutionCase` | workflow de traitement d'un écart |
| `JournalEntryProposal` | proposition de correction comptable |
| `IntercompanyElimination` | écriture de consolidation |
| `ReconciliationSnapshot` | résultat figé du rapprochement |

---

# 296. Frontière avec P2.3

Le prochain jalon optionnel est :

```text
23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md
```

Il devra borner précisément les extensions hors coeur :

```text
NPV / VAN

IRR / TRI

WACC

DCF

Enterprise Valuation

Investment Appraisal

Financing Structure

Sensitivity Analysis

Scenario Analysis

Monte Carlo
```

sans les confondre avec le bounded context comptable `Financial Analysis` déjà défini dans `14`.

---

# 297. Conclusion

L'architecture cible de réconciliation est :

```text
SOURCE SNAPSHOT A
        |
        +---------+
                  v
          RECONCILIATION
                  ^
        +---------+
        |
SOURCE SNAPSHOT B

        |
        v
NORMALIZATION
        |
        v
CANDIDATE GENERATION
        |
        v
MATCHING
        |
        v
DIFFERENCE ANALYSIS
        |
        v
RESOLUTION
        |
        v
CONTROLS / SIGN-OFF
        |
        v
RECONCILIATION SNAPSHOT
```

Les principes structurants sont :

```text
Reconciliation is read/compare first.

It never becomes a second posting engine.

Candidate is not match.

Confidence is not authority.

Tolerance is not write-off.

Difference is not automatically accounting error.

Explained is not resolved.

Accounting corrections use JournalEntryProposal.

Consolidation owns eliminations.

Sources are pinned for publication.

Published reconciliation snapshots are immutable.

Every match and difference is drillable to source evidence.

When matching is ambiguous, PyAccountingKit fails closed.
```

---

**Prochain document recommandé :**

```text
23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md
```


---

## Sources et références documentaires du projet

- 📕 [Comptabilité Générale — Système français et normes IFRS](../../books/Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md)

---

## Plans d'implémentation principaux

Ce document est couvert par les plans suivants :

- [PLAN-07 — Reconciliation (1.1.0)](../../plans/PLAN-07_RECONCILIATION_1.1.0.md)
