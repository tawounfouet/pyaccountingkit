# 07 - PyAccountingKit - Architecture du Ledger, du Posting et du Reversal

> **Projet** : PyAccountingKit  
> **Document** : `07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md`  
> **Documents parents** :
> - `00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`
> - `01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`
> - `02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`
> - `03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md`
> - `04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md`
> - `05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md`
> - `06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md`
> **Statut** : P0.8 - Architecture du coeur transactionnel et des projections comptables  
> **Langue** : Français  
> **Objet** : Définir les journaux, écritures, lignes, validation, posting, immutabilité, reversal/extourne, journal comptable, grand livre, balances, conventions de solde, projections, drill-down, contrats de concurrence et règles de reconstruction du ledger.

---

# 1. Résumé exécutif

Le coeur comptable de PyAccountingKit repose sur une séparation stricte entre :

```text
WRITE MODEL
    Journal
    JournalEntry
    JournalEntryLine
    AccountingPeriod
    CompanyAccount

READ MODEL
    Accounting Journal View
    General Ledger
    Trial Balance
    Financial Statements
    Financial Analysis
```

La source comptable canonique est :

```text
JournalEntry
+
JournalEntryLine
+
CompanyAccount
+
AccountingPeriod
```

Les objets suivants sont des **projections** :

```text
Journal report
General Ledger
Account Balance
Trial Balance
Financial Statements
Financial Analysis
```

Le cycle transactionnel principal est :

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

Une écriture `POSTED` est immutable.

Une correction ne consiste jamais à modifier l'écriture initiale :

```text
POSTED original
      |
      v
POSTED reversal
      |
      v
new correct entry
```

Le ledger est ensuite reconstruit à partir des lignes postées.

---

# 2. Source fonctionnelle de référence

Le projet CFA FRA fournit une référence fonctionnelle exécutable utile pour ce bounded context.

Il formalise notamment :

```text
Journal
JournalEntry
JournalLine
DRAFT
VALIDATED
POSTED
REVERSED
partie double
posting
reversal
audit
journal comptable
general ledger
trial balance
drill-down
```

PyAccountingKit reprend les comportements génériques mais pas les dépendances Django, PostgreSQL ou HTMX.

---

# 3. Principes d'architecture

## P-LED-001 - Source comptable unique

Les mouvements comptables proviennent exclusivement des écritures et lignes comptables.

---

## P-LED-002 - Les projections ne deviennent pas sources primaires

Le grand livre ou la balance peuvent être :

```text
calculés à la volée
cachés
matérialisés
indexés
```

pour la performance.

Mais ils restent reconstructibles.

---

## P-LED-003 - Posting append-oriented

Après posting :

```text
pas d'UPDATE métier destructif
pas de DELETE métier
```

La correction passe par une nouvelle écriture.

---

## P-LED-004 - Séparer mutation et lecture

```text
Commands
    create
    validate
    post
    reverse

Queries
    journal
    ledger
    trial balance
```

---

## P-LED-005 - Infrastructure agnostique

Le domaine ne connaît pas :

```text
transaction.atomic
select_for_update
Django ORM
SQLAlchemy
PostgreSQL Window
```

Il exprime les garanties requises.

---

# 4. Bounded contexts concernés

```text
Journal & Entries
        |
        v
Posting & Reversal
        |
        v
Ledger & Balances
```

avec dépendances vers :

```text
Company Chart of Accounts
Accounting Periods
Accounting Policies
Audit & Traceability
Controls
```

---

# 5. `Journal`

Aggregate Root :

```text
Journal
|
+-- id
+-- accounting_entity_id
+-- code
+-- label
+-- journal_type
+-- active
+-- valid_from
+-- valid_to?
+-- posting_policy_id?
+-- metadata
```

---

# 6. `JournalType`

Valeurs initiales génériques :

```text
SALES
PURCHASE
BANK
CASH
PAYROLL
TAX
GENERAL
OPENING
ADJUSTMENT
CLOSING
CUSTOM
```

Ces types sont des catégories applicatives.

Ils ne sont pas des obligations réglementaires universelles.

---

# 7. Invariants du journal

```text
journal.code non vide

journal.accounting_entity_id obligatoire

code unique dans le scope défini

inactive journal rejects ordinary posting
```

---

# 8. `JournalPostingPolicy`

Un journal peut limiter :

```text
entry types
date ranges
allowed account roles
allowed sources
manual posting
automated posting
```

Cette policy n'appartient pas à `JournalEntry`.

---

# 9. `JournalEntry`

Aggregate Root central :

```text
JournalEntry
|
+-- id
+-- accounting_entity_id
+-- journal_id
+-- period_id
+-- entry_number
+-- accounting_date
+-- document_date?
+-- posting_date?
+-- description
+-- source
+-- source_reference?
+-- entry_type
+-- status
+-- lines
+-- created_at
+-- validated_at?
+-- posted_at?
+-- reversed_at?
+-- created_by?
+-- validated_by?
+-- posted_by?
+-- reversed_by?
+-- reversal_of?
+-- revision
+-- metadata
```

---

# 10. Pourquoi `JournalEntry` est Aggregate Root

Les invariants de partie double concernent l'écriture complète :

```text
nombre de lignes
équilibre
cohérence de devise
cohérence d'entité
cycle de vie
```

Une ligne ne doit donc pas être persistée comme mutation métier indépendante de son écriture.

---

# 11. `JournalEntryLine`

Entité interne :

```text
JournalEntryLine
|
+-- line_id
+-- line_number
+-- account_id
+-- debit
+-- credit
+-- description?
+-- counterparty?
+-- dimensions
+-- cash_flow_tag?
+-- source_line_reference?
+-- metadata
```

---

# 12. Montants

Les lignes utilisent :

```text
Decimal
```

et jamais `float`.

---

# 13. Invariant ligne - non négativité

```text
debit >= 0
credit >= 0
```

---

# 14. Invariant ligne - débit XOR crédit

Interdit :

```text
debit > 0
AND
credit > 0
```

---

# 15. Invariant ligne - ligne nulle

Par défaut, lors de validation :

```text
debit == 0
AND
credit == 0
```

est refusé.

---

# 16. Forme alternative future

Une future primitive pourrait utiliser :

```text
PostingAmount(
    side = DEBIT | CREDIT,
    amount > 0
)
```

afin de rendre l'invariant structurel.

---

# 17. Nombre minimal de lignes

Une écriture validée doit posséder au moins :

```text
2 lines
```

Un `DRAFT` peut être incomplet.

---

# 18. Partie double

Invariant central :

```text
SUM(line.debit)
=
SUM(line.credit)
```

pour :

```text
VALIDATED
POSTED
```

---

# 19. `JournalEntryStatus`

```text
DRAFT
VALIDATED
POSTED
REVERSED
```

---

# 20. State machine

```text
           validate
DRAFT ----------------> VALIDATED
                           |
                           | post
                           v
                        POSTED
                           |
                           | reverse
                           v
                       REVERSED
```

---

# 21. Transitions interdites

```text
DRAFT -> POSTED

DRAFT -> REVERSED

VALIDATED -> REVERSED

REVERSED -> POSTED

POSTED -> DRAFT
```

sauf éventuelle migration technique contrôlée hors API métier normale.

---

# 22. DRAFT

Propriétés :

```text
modifiable
supprimable selon policy
peut être incomplet
ne contribue pas au ledger
```

---

# 23. VALIDATED

Propriétés :

```text
équilibré
structure valide
prêt à être posté
pas encore source du ledger
```

Une policy peut permettre retour en `DRAFT` avant posting, mais ce comportement n'est pas requis en P0.

---

# 24. POSTED

Propriétés :

```text
immutable
contribue au ledger
audité
posted_at défini
posted_by éventuellement défini
```

---

# 25. REVERSED

`REVERSED` signifie :

```text
l'écriture originale reste dans l'historique
+
une écriture de reversal a été postée
```

Il ne signifie pas :

```text
l'écriture est supprimée
```

---

# 26. `EntryType`

Valeurs initiales :

```text
OPENING
NORMAL
ADJUSTING
CLOSING
REVERSAL
CUSTOM
```

---

# 27. EntryType != JournalType

Exemple :

```text
Journal GENERAL
peut contenir
NORMAL
ADJUSTING
```

La relation est contrôlée par policy.

---

# 28. `EntrySource`

Exemples :

```text
MANUAL
FEC
API
IMPORT
POLICY
REVERSAL
MIGRATION
CUSTOM
```

---

# 29. Provenance

Chaque écriture doit pouvoir conserver :

```text
source
source_reference
```

et chaque ligne :

```text
source_line_reference
```

lorsque disponible.

---

# 30. `EntryNumber`

Value Object :

```text
EntryNumber
```

stabilisé au plus tard lors du posting.

---

# 31. Numérotation

La numérotation dépend de :

```text
EntryNumberingPolicy
```

et peut être scoped par :

```text
entity
journal
fiscal year
period
```

---

# 32. Unicité de numéro

La contrainte d'unicité exacte dépend de la policy.

Exemple :

```text
UNIQUE(entity, journal, fiscal_year, entry_number)
```

---

# 33. Dates

Le modèle distingue :

```text
DocumentDate

AccountingDate

PostingDate

CreatedAt

ValidatedAt

PostedAt
```

---

# 34. `AccountingDate`

Détermine la période comptable de rattachement.

---

# 35. `PostingDate`

Représente la date comptable ou opérationnelle de comptabilisation selon policy.

Le nom exact et sa sémantique doivent être explicites pour éviter la confusion.

---

# 36. `Clock`

Les timestamps techniques utilisent :

```text
Clock
```

et non :

```text
datetime.now()
```

directement dans le domaine testable.

---

# 37. `JournalEntryValidator`

Contrat :

```python
class JournalEntryValidator:

    def validate(
        self,
        entry: JournalEntry,
        context: EntryValidationContext,
    ) -> EntryValidationResult:
        ...
```

---

# 38. `EntryValidationContext`

```text
EntryValidationContext
|
+-- entity
+-- journal
+-- period
+-- accounts
+-- policy_set
+-- clock
+-- validation_stage
```

---

# 39. Contrôles P0 de validation

```text
ENTRY_HAS_MINIMUM_LINES

LINE_NON_NEGATIVE

LINE_DEBIT_OR_CREDIT

LINE_NON_ZERO

ACCOUNT_EXISTS

ACCOUNT_ACTIVE

ACCOUNT_POSTABLE

JOURNAL_ACTIVE

PERIOD_COMPATIBLE

ACCOUNTING_DATE_WITHIN_PERIOD

SAME_ACCOUNTING_ENTITY

ENTRY_BALANCED
```

---

# 40. `EntryValidationResult`

```text
EntryValidationResult
|
+-- valid
+-- issues
+-- total_debit
+-- total_credit
+-- difference
```

---

# 41. `ValidationIssue`

```text
ValidationIssue
|
+-- code
+-- severity
+-- message
+-- line_id?
+-- account_id?
+-- expected?
+-- actual?
```

---

# 42. `validate()` ne persiste pas automatiquement

Le domaine peut effectuer :

```text
entry.validate(...)
```

puis l'Application Layer orchestre la persistence.

---

# 43. Validation DRAFT -> VALIDATED

Préconditions :

```text
entry.status == DRAFT
validation_result.valid
```

Effets :

```text
status = VALIDATED
validated_at
revision increment
DomainEvent
```

---

# 44. `JournalEntryValidated`

Domain Event :

```text
JournalEntryValidated
|
+-- entry_id
+-- entity_id
+-- validated_at
+-- actor?
```

---

# 45. Posting

Le posting transforme une écriture validée en mouvement comptable définitif.

```text
VALIDATED
    |
    v
POSTED
```

---

# 46. `PostingService`

Contrat conceptuel :

```python
class PostingService:

    def post(
        self,
        entry: JournalEntry,
        context: PostingContext,
    ) -> PostingResult:
        ...
```

---

# 47. Préconditions du posting

P0 :

```text
status == VALIDATED

period accepts posting

journal active

accounts active

accounts postable

entity scopes coherent

entry remains balanced

no conflicting state transition
```

---

# 48. Revalidation au posting

Le posting doit revalider les invariants critiques.

Pourquoi :

```text
VALIDATED peut avoir été créé plus tôt

période peut avoir été fermée depuis

compte peut avoir été désactivé

journal peut avoir été désactivé
```

---

# 49. `PostingContext`

```text
PostingContext
|
+-- actor?
+-- clock
+-- expected_revision
+-- period
+-- journal
+-- account_states
+-- policy_set
```

---

# 50. Effets du posting

```text
status = POSTED

posted_at = Clock.now()

posted_by = actor

revision += 1

JournalEntryPosted emitted
```

---

# 51. `PostingResult`

```text
PostingResult
|
+-- entry_id
+-- posted_at
+-- entry_number
+-- revision
+-- domain_events
```

---

# 52. Atomicité

Le posting constitue une seule transaction logique :

```text
load
lock / version check
validate
transition
save
audit enqueue
commit
```

---

# 53. Pas de transaction dans le domaine

Le domaine n'utilise pas :

```text
BEGIN
COMMIT
ROLLBACK
```

L'Application Layer utilise :

```text
UnitOfWork
```

---

# 54. Exemple UnitOfWork

```python
with unit_of_work:
    entry = unit_of_work.entries.get(entry_id)

    result = posting_service.post(
        entry,
        context=posting_context,
    )

    unit_of_work.entries.save(entry)
    unit_of_work.audit.append(...)

    unit_of_work.commit()
```

---

# 55. Concurrence

Cas critique :

```text
Worker A posts entry E

Worker B posts entry E
```

Le résultat attendu :

```text
one successful transition
one concurrency failure / idempotent acknowledgement
```

jamais :

```text
two posting effects
```

---

# 56. `revision`

Le `JournalEntry` porte :

```text
revision
```

pour optimistic concurrency.

---

# 57. Optimistic locking

```text
expected_revision
=
stored_revision
```

sinon :

```text
ConcurrentJournalEntryModificationError
```

---

# 58. Pessimistic locking

Un adapter peut utiliser un verrou de ligne.

Exemples :

```text
SELECT FOR UPDATE
Django select_for_update
SQLAlchemy with_for_update
```

sans exposer ces APIs au domaine.

---

# 59. Idempotence du posting

Un appel répété avec la même clé d'idempotence peut :

```text
retourner le PostingResult existant
```

si la requête est identique.

---

# 60. `PostingIdempotencyKey`

```text
PostingIdempotencyKey
```

peut être fournie par :

```text
API
import
workflow engine
```

---

# 61. Immutabilité POSTED

Après posting, interdiction de modifier :

```text
accounting_date
journal_id
period_id
entry_number
description comptable significative
source
source_reference
lines
amounts
accounts
dimensions comptables
```

---

# 62. Métadonnées techniques

Des métadonnées purement techniques peuvent évoluer si elles sont physiquement séparées :

```text
projection watermark
cache metadata
search index metadata
```

---

# 63. Reversal

Une reversal est une **nouvelle écriture**.

```text
original entry
    remains unchanged
```

---

# 64. `ReversalService`

```python
class ReversalService:

    def reverse(
        self,
        original: JournalEntry,
        request: ReversalRequest,
    ) -> ReversalResult:
        ...
```

---

# 65. `ReversalRequest`

```text
ReversalRequest
|
+-- original_entry_id
+-- reversal_date
+-- journal_id?
+-- reason
+-- actor?
+-- idempotency_key?
```

---

# 66. Préconditions de reversal

```text
original.status == POSTED

reversal date allowed

target period accepts posting

no active full reversal already exists

entity consistent
```

---

# 67. Construction de l'écriture inverse

Pour chaque ligne :

```text
original.debit
    ->
reversal.credit

original.credit
    ->
reversal.debit
```

---

# 68. Lien `reversal_of`

La reversal conserve :

```text
reversal_of = original_entry_id
```

---

# 69. Source de reversal

```text
source = REVERSAL
```

---

# 70. Numéro de reversal

Le numéro peut être généré par une policy.

Exemple possible :

```text
REV-<original_number>
```

mais ce format n'est pas un invariant universel.

---

# 71. Statut de la reversal

La nouvelle écriture passe :

```text
DRAFT / generated
    ->
VALIDATED
    ->
POSTED
```

même si l'Application Layer orchestre ces étapes dans une seule commande transactionnelle.

---

# 72. Marquage de l'original

Une fois la reversal postée :

```text
original.status = REVERSED
```

Cette propriété indique le cycle métier.

Les lignes originales restent dans les projections.

---

# 73. Pourquoi inclure les REVERSED dans le ledger

Le modèle de référence CFA FRA inclut l'original et l'extourne.

Ainsi :

```text
original movement
+
reversal movement
=
net zero
```

pour une reversal complète.

---

# 74. Reversal complète

P0 cible :

```text
FULL_REVERSAL
```

---

# 75. Partial reversal

Une reversal partielle pourra être étudiée plus tard.

Elle nécessite :

```text
partial amount
line-level relation
remaining unreversed amount
```

Elle n'est pas requise P0.

---

# 76. Reversal automatique future

Cas :

```text
accrual on 31/12
automatic reversal on 01/01
```

sera piloté par :

```text
ReversalDatePolicy
AccrualPolicy
```

---

# 77. Date de reversal

Stratégies possibles :

```text
SAME_PERIOD_IF_OPEN

CURRENT_OPEN_PERIOD

NEXT_OPEN_PERIOD

EXPLICIT_ALLOWED_DATE
```

---

# 78. Audit reversal

Audit minimal :

```text
ENTRY_REVERSE_REQUESTED

REVERSAL_ENTRY_CREATED

REVERSAL_ENTRY_POSTED

ORIGINAL_ENTRY_MARKED_REVERSED
```

---

# 79. Erreur de double reversal

```text
AlreadyReversedError
```

---

# 80. Reversal et concurrence

Deux reversals simultanées de la même écriture doivent être empêchées.

---

# 81. Journal comptable comme projection

Le journal comptable de restitution :

```text
AccountingJournalView
```

est différent de l'aggregate `Journal`.

---

# 82. `AccountingJournalQuery`

```python
class AccountingJournalQuery(Protocol):

    def query(
        self,
        request: JournalQueryRequest,
    ) -> JournalPage:
        ...
```

---

# 83. `JournalQueryRequest`

```text
JournalQueryRequest
|
+-- entity_id
+-- fiscal_year_id?
+-- date_from?
+-- date_to?
+-- journal_ids?
+-- entry_types?
+-- sources?
+-- search?
+-- page
+-- page_size
+-- ordering
```

---

# 84. Scope du journal de restitution

Par défaut :

```text
POSTED
REVERSED
```

Sont exclus :

```text
DRAFT
VALIDATED
```

---

# 85. Pourquoi REVERSED est visible

Parce qu'un audit comptable doit montrer :

```text
original
reversal
```

et non seulement le net.

---

# 86. `JournalRow`

```text
JournalRow
|
+-- entry_id
+-- line_id
+-- entry_number
+-- accounting_date
+-- journal
+-- account
+-- description
+-- debit
+-- credit
+-- source
+-- reversal_of?
```

---

# 87. Totaux journal

Une page ou un résultat peut exposer :

```text
total_debit
total_credit
difference
```

---

# 88. General Ledger

Le grand livre est une projection par compte.

```text
POSTED / REVERSED lines
        |
        v
partition by account
        |
        v
ordered movements
        |
        v
running balance
```

---

# 89. `GeneralLedgerQuery`

```python
class GeneralLedgerQuery(Protocol):

    def query(
        self,
        request: GeneralLedgerRequest,
    ) -> GeneralLedgerPage:
        ...
```

---

# 90. `GeneralLedgerRequest`

```text
GeneralLedgerRequest
|
+-- entity_id
+-- account_ids?
+-- fiscal_year_id?
+-- date_from?
+-- date_to?
+-- entry_types?
+-- dimensions?
+-- include_zero_movements?
+-- page
+-- page_size
+-- ordering
```

---

# 91. Composants du grand livre

Pour chaque compte :

```text
opening balance

debit movements

credit movements

running balance

closing balance
```

---

# 92. Solde d'ouverture

Pour une période demandée :

```text
opening balance
=
sum of eligible movements before date_from
```

dans le périmètre considéré.

---

# 93. Running balance

Convention P0 :

```text
signed_balance
=
debit - credit
```

---

# 94. Présentation du solde

```text
signed_balance >= 0
    -> debit balance

signed_balance < 0
    -> credit balance = abs(signed_balance)
```

---

# 95. Signed balance != normal balance

Ne pas confondre :

```text
signed_balance
```

avec :

```text
account.normal_balance
```

---

# 96. Ordre déterministe

Le calcul cumulatif exige un ordre total stable.

Proposition :

```text
accounting_date
posting_sequence
entry_id
line_number
```

---

# 97. Pourquoi `created_at` seul est insuffisant

Des timestamps peuvent être :

```text
identiques
importés
réécrits lors de migration technique
```

Un ordre déterministe explicite est préférable.

---

# 98. `PostingSequence`

Value Object / valeur technique durable :

```text
PostingSequence
```

assignée au posting ou par l'adapter de persistence.

---

# 99. Ordre recommandé

```text
ORDER BY
    accounting_date,
    posting_sequence,
    entry_id,
    line_number
```

---

# 100. Pagination du grand livre

La pagination ne doit pas casser le solde courant.

Deux stratégies :

```text
1. compute opening balance before page

2. use database/window projection preserving prefix sum
```

---

# 101. Projection SQL possible

Un adapter PostgreSQL peut utiliser :

```sql
SUM(debit - credit)
OVER (
    PARTITION BY account_id
    ORDER BY accounting_date, posting_sequence, line_number
)
```

Le domaine ne dépend pas de SQL.

---

# 102. Trial Balance

La balance agrège par compte :

```text
debit movements
credit movements
signed balance
debit balance
credit balance
```

---

# 103. `TrialBalanceQuery`

```python
class TrialBalanceQuery(Protocol):

    def query(
        self,
        request: TrialBalanceRequest,
    ) -> TrialBalance:
        ...
```

---

# 104. `TrialBalanceRequest`

```text
TrialBalanceRequest
|
+-- entity_id
+-- fiscal_year_id
+-- date_from?
+-- date_to?
+-- variant
+-- account_filter?
+-- dimensions?
+-- include_zero_balance_accounts
```

---

# 105. Calcul d'une ligne de balance

```text
movement_debit =
SUM(debit)

movement_credit =
SUM(credit)

signed_balance =
movement_debit - movement_credit

debit_balance =
MAX(signed_balance, 0)

credit_balance =
MAX(-signed_balance, 0)
```

---

# 106. Contrôle d'équilibre de balance

```text
SUM(debit_balance)
=
SUM(credit_balance)
```

doit être vérifiable.

---

# 107. Nature de ce contrôle

Il s'agit d'un :

```text
CONTROL
```

sur une projection.

Ce n'est pas une nouvelle source d'équilibre indépendante des écritures.

---

# 108. `TrialBalanceVariant`

Valeurs initiales issues de la référence CFA FRA :

```text
BEFORE_ADJUSTMENTS

ADJUSTED

POST_CLOSING
```

---

# 109. Important - ce ne sont pas des invariants universels

Les inclusions précises par `EntryType` sont une :

```text
TrialBalanceVariantPolicy
```

et peuvent évoluer.

---

# 110. `BEFORE_ADJUSTMENTS`

Configuration de référence :

```text
include:
    OPENING
    NORMAL
    REVERSAL

exclude:
    ADJUSTING
    CLOSING
```

---

# 111. `ADJUSTED`

Configuration de référence :

```text
include:
    OPENING
    NORMAL
    ADJUSTING
    REVERSAL

exclude:
    CLOSING
```

Cette balance alimente typiquement les états financiers avant fermeture des comptes temporaires.

---

# 112. `POST_CLOSING`

Configuration de référence :

```text
include:
    OPENING
    NORMAL
    ADJUSTING
    CLOSING
    REVERSAL
```

---

# 113. Masquage des comptes à zéro

Option de présentation :

```text
include_zero_balance_accounts
```

Par défaut :

```text
false
```

pour certains usages.

---

# 114. Comptes temporaires

Le caractère :

```text
temporary
```

ne doit pas être inféré universellement d'un code.

Il doit provenir :

```text
AccountRole
validated classification
ClosingPolicy
```

---

# 115. `TrialBalanceVariantPolicy`

```text
TrialBalanceVariantPolicy
|
+-- variant
+-- included_entry_types
+-- excluded_entry_types
+-- zero_balance_visibility
+-- applicability
```

---

# 116. EntryType et FEC

La classification d'un journal source comme `ADJUSTING` relève de l'adapter FEC.

Elle ne doit pas être codée dans le Ledger universel.

---

# 117. Projection journal

```text
JournalEntry / Lines
    |
    v
JournalProjection
```

---

# 118. Projection ledger

```text
JournalProjection
    |
    v
GeneralLedgerProjection
```

---

# 119. Projection balance

```text
GeneralLedger movements
    |
    v
TrialBalanceProjection
```

---

# 120. Chaîne de lecture

```text
POSTED lines
    |
    v
Accounting Journal
    |
    v
General Ledger
    |
    v
Trial Balance
    |
    v
Financial Statements
    |
    v
Financial Analysis
```

---

# 121. Projection directe possible

Techniquement :

```text
Trial Balance
```

peut être calculée directement depuis les lignes postées.

Elle n'est pas obligée de lire une table de grand livre matérialisée.

---

# 122. Principe de reconstructibilité

Toute projection doit pouvoir être recalculée depuis :

```text
canonical posted lines
+
projection policy
```

---

# 123. `ProjectionDefinitionVersion`

Une projection dont les règles peuvent évoluer doit avoir une version.

---

# 124. Rebuild

Commande applicative :

```text
RebuildLedgerProjection
```

peut recalculer les vues matérialisées.

---

# 125. Matérialisation

Autorisé pour :

```text
performance
reporting
analytics
large volumes
```

---

# 126. Matérialisation != source canonique

Une table :

```text
ledger_projection
```

peut être supprimée puis reconstruite.

---

# 127. `ProjectionWatermark`

Pour les mises à jour incrémentales :

```text
ProjectionWatermark
|
+-- projection_name
+-- entity_id
+-- last_posting_sequence
+-- updated_at
```

---

# 128. Projection synchrone vs asynchrone

Deux modèles :

```text
synchronous query
```

ou :

```text
event-driven materialized projection
```

Le P0 peut utiliser le calcul synchrone.

---

# 129. Cohérence

Le write model exige :

```text
strong consistency
```

Le read model peut accepter :

```text
eventual consistency
```

si l'application le documente.

---

# 130. Drill-down

Le système doit préserver :

```text
Trial Balance
    ->
General Ledger
    ->
JournalEntry
    ->
JournalEntryLine
```

---

# 131. Pourquoi le drill-down est architectural

Il assure :

```text
auditability
explainability
debugging
user trust
```

---

# 132. `ProjectionSourceRef`

Chaque ligne projetée doit pouvoir référencer :

```text
source entry id
source line id
```

---

# 133. Drill-down Balance -> Ledger

Entrée :

```text
account_id
period
variant
```

---

# 134. Drill-down Ledger -> Entry

Entrée :

```text
entry_id
line_id
```

---

# 135. Multi-entité

Toutes les queries exigent :

```text
AccountingEntityId
```

---

# 136. Isolation

Une query de ledger pour l'entité A ne peut jamais lire les lignes de l'entité B.

---

# 137. Multi-chart

Si une entité change de chart dans le temps :

```text
account_id
```

reste la clé historique.

Le code affiché doit respecter la version applicable.

---

# 138. Reversal et affichage du code historique

Une reversal d'une ancienne écriture doit conserver :

```text
account identities
```

même si le chart évolue.

---

# 139. Dimension filtering

Le ledger pourra filtrer :

```text
cost center
counterparty
project
custom dimensions
```

si les dimensions existent.

---

# 140. Dimension != compte

Un filtre dimensionnel ne change pas le compte source.

---

# 141. Subledger

Le ledger général et les sous-ledgers sont distincts.

```text
General Ledger
    = CompanyAccount movements

Subledger
    = detail by auxiliary entity
```

---

# 142. Reconciliation

Le futur bounded context Reconciliation consommera :

```text
General Ledger
Subledger
external statements
```

sans modifier les écritures.

---

# 143. Posting des policies

Les outputs de :

```text
DepreciationPolicy
AccrualPolicy
ProvisionPolicy
InventoryPolicy
```

deviennent :

```text
JournalEntryProposal
```

puis suivent le même pipeline :

```text
Create
Validate
Post
```

---

# 144. Aucun bypass de posting

Interdit :

```text
DepreciationService
    -> append directly to ledger
```

---

# 145. Import et posting

Un adapter d'import peut proposer une voie optimisée.

Mais conceptuellement, il doit garantir les mêmes invariants.

---

# 146. Cas FEC déjà validé

Une application peut choisir une policy :

```text
TrustedExternalPostedEntryImportPolicy
```

permettant un import direct vers état `POSTED` si :

```text
source is trusted
validation succeeded
period accepts import
audit/provenance is preserved
transaction is atomic
```

---

# 147. Cette exception n'est pas universelle

P0 normal :

```text
DRAFT -> VALIDATED -> POSTED
```

Import de comptabilité déjà validée :

```text
special explicit adapter policy
```

---

# 148. Ledger et reversals

Les projections incluent :

```text
POSTED
REVERSED originals
POSTED reversal entries
```

selon la représentation de statut retenue.

---

# 149. Attention à la double exclusion

Ne pas faire :

```text
exclude original because status=REVERSED
+
include reversal
```

si l'objectif est de préserver l'audit et le mouvement comptable.

---

# 150. Modèle recommandé

Les lignes de l'original restent :

```text
ledger_effective = true
```

même si l'aggregate métier est marqué `REVERSED`.

La neutralisation vient de la reversal.

---

# 151. Alternative technique

Séparer :

```text
lifecycle_status
```

de :

```text
ledger_inclusion_status
```

peut éviter l'ambiguïté.

---

# 152. `LedgerInclusionPolicy`

Par défaut :

```text
include every successfully posted entry
including originals later reversed
```

---

# 153. Suppression et ledger

Une écriture postée ne peut jamais être supprimée via API métier.

---

# 154. GDPR / retention

Si une obligation de suppression de données personnelles existe, il faut :

```text
anonymisation
pseudonymisation
metadata redaction
```

sans altérer les montants et traces comptables nécessaires.

Ce sujet relève d'un document sécurité/compliance futur.

---

# 155. Journaux désactivés

Désactiver un journal :

```text
blocks future ordinary posting
```

mais ne retire pas ses mouvements historiques des projections.

---

# 156. Comptes désactivés

Même principe :

```text
inactive account
    blocks new posting

historical movements
    remain visible
```

---

# 157. Période fermée

```text
CLOSED
```

bloque le posting normal.

Elle ne masque pas les écritures existantes.

---

# 158. Période réouverte

La réouverture est une opération distincte et auditée.

Le détail sera approfondi dans le document Closing.

---

# 159. `PostingAuthorizationPolicy`

Optionnellement, une application peut fournir :

```text
who may post
who may reverse
```

mais l'autorisation utilisateur reste hors coeur.

---

# 160. `ActorContext`

```text
ActorContext
|
+-- actor_id
+-- actor_type
+-- correlation_id
+-- request_id?
```

---

# 161. Audit event posting

```text
AuditEvent
|
+-- action = ENTRY_POST
+-- entry_id
+-- actor
+-- occurred_at
+-- before_status
+-- after_status
+-- metadata
```

---

# 162. Audit event reversal

```text
ENTRY_REVERSE
```

avec :

```text
original_entry_id
reversal_entry_id
reason
```

---

# 163. Domain Events P0

```text
JournalEntryCreated

JournalEntryValidated

JournalEntryPosted

JournalEntryReversed

ReversalEntryCreated
```

---

# 164. Outbox future

Les domain events peuvent être persistés avec un :

```text
Transactional Outbox
```

dans les adapters.

Pas requis dans le domaine P0.

---

# 165. `PostingPort` ?

Le Posting Engine est une logique métier interne.

Il ne doit pas être un port d'infrastructure.

Les ports concernent :

```text
repositories
unit of work
clock
audit
idempotency
```

---

# 166. Repository `JournalEntryRepository`

```python
class JournalEntryRepository(Protocol):

    def get(
        self,
        entry_id: JournalEntryId,
    ) -> JournalEntry:
        ...

    def save(
        self,
        entry: JournalEntry,
    ) -> None:
        ...

    def exists_by_idempotency_key(
        self,
        key: str,
    ) -> bool:
        ...
```

---

# 167. `JournalRepository`

```python
class JournalRepository(Protocol):

    def get(
        self,
        journal_id: JournalId,
    ) -> Journal:
        ...
```

---

# 168. `AccountingPeriodRepository`

```python
class AccountingPeriodRepository(Protocol):

    def get(
        self,
        period_id: AccountingPeriodId,
    ) -> AccountingPeriod:
        ...
```

---

# 169. Account state

Le PostingService peut recevoir un snapshot des comptes nécessaires :

```text
AccountPostingState
|
+-- account_id
+-- entity_id
+-- active
+-- posting_allowed
```

---

# 170. Ne pas charger le chart complet

Pour poster une écriture :

```text
load only accounts referenced by lines
```

---

# 171. Performance validation

Un entry avec N lignes :

```text
batch load accounts
```

plutôt que :

```text
N repository calls
```

---

# 172. `AccountPostingStateProvider`

Port query possible :

```python
class AccountPostingStateProvider(Protocol):

    def get_many(
        self,
        account_ids: tuple[CompanyAccountId, ...],
    ) -> dict[CompanyAccountId, AccountPostingState]:
        ...
```

---

# 173. Erreurs Posting

```text
PostingError
|
+-- EntryNotValidatedError
+-- EntryAlreadyPostedError
+-- EntryUnbalancedError
+-- InactiveJournalError
+-- InactiveAccountError
+-- NonPostableAccountError
+-- ClosedPeriodError
+-- EntryEntityMismatchError
+-- PostingConcurrencyError
+-- PostingIdempotencyConflictError
```

---

# 174. Erreurs Reversal

```text
ReversalError
|
+-- EntryNotPostedError
+-- AlreadyReversedError
+-- ReversalPeriodClosedError
+-- InvalidReversalDateError
+-- ReversalConcurrencyError
+-- ReversalIdempotencyConflictError
```

---

# 175. Erreurs projection

```text
LedgerProjectionError
|
+-- ProjectionDefinitionNotFoundError
+-- InvalidTrialBalanceVariantError
+-- ProjectionIntegrityError
+-- MissingSourceEntryError
```

---

# 176. Fail-closed

Posting critique :

```text
unknown account
unknown period
unknown journal
ambiguous entity
unbalanced entry
invalid status
```

=

```text
failure
```

pas warning.

---

# 177. Query fail-safe

Une query analytique peut retourner :

```text
warning
partial result
```

uniquement si le contrat l'autorise explicitement.

---

# 178. Tests unitaires - entry

```text
test_draft_can_be_modified

test_validated_entry_requires_minimum_two_lines

test_line_debit_and_credit_cannot_both_be_positive

test_balanced_entry_can_validate

test_unbalanced_entry_cannot_validate
```

---

# 179. Tests unitaires - posting

```text
test_draft_cannot_post

test_validated_entry_can_post

test_posting_revalidates_period

test_posting_revalidates_account_status

test_posting_requires_postable_accounts

test_posting_records_posted_at

test_posting_emits_domain_event

test_posted_entry_is_immutable
```

---

# 180. Tests unitaires - reversal

```text
test_only_posted_entry_can_be_reversed

test_reversal_creates_new_entry

test_reversal_swaps_debit_and_credit

test_reversal_links_original

test_original_remains_unchanged

test_original_marked_reversed_after_reversal_posted

test_double_reversal_is_rejected
```

---

# 181. Property-based test - balance

Pour toute écriture validée générée :

```text
sum(debit)
=
sum(credit)
```

---

# 182. Property-based test - reversal net zero

Pour toute reversal intégrale :

```text
net(original + reversal)
=
0
```

par compte et devise, lorsque la reversal est strictement symétrique.

---

# 183. Property-based test - ledger reconstruction

Pour tout ensemble de lignes postées :

```text
trial balance totals
=
aggregation of same source lines
```

---

# 184. Tests journal

```text
test_drafts_are_excluded_from_accounting_journal

test_posted_entries_are_included

test_reversed_originals_remain_visible

test_reversal_entries_are_visible

test_journal_total_debit_equals_total_credit
```

---

# 185. Tests grand livre

```text
test_opening_balance_is_before_start_date

test_running_balance_is_deterministic

test_closing_balance_equals_opening_plus_movements

test_pagination_preserves_running_balance

test_ledger_drilldown_returns_entry
```

---

# 186. Tests balance

```text
test_trial_balance_is_balanced

test_before_adjustments_variant

test_adjusted_variant

test_post_closing_variant

test_zero_balance_visibility

test_balance_drilldown_to_ledger
```

---

# 187. Golden tests CFA FRA

Conserver comme oracle comportemental :

```text
DRAFT excluded

POSTED included

REVERSED original included

reversal offsets original

opening balance correct

signed balance = debit - credit

BEFORE_ADJUSTMENTS

ADJUSTED

POST_CLOSING

drill-down to source entry
```

---

# 188. Exemple de grand livre

Source :

```text
Opening:
Cash      Dr 1 000
Capital   Cr 1 000

Normal:
Rent      Dr   200
Cash      Cr   200
```

Grand livre Cash :

```text
Opening balance  1 000 Dr

Movement         200 Cr

Closing balance    800 Dr
```

---

# 189. Exemple avec adjustment

```text
Adjusting:
Rent      Dr 50
Accrued   Cr 50
```

---

# 190. Balance avant ajustements

```text
Cash       Dr 800
Rent       Dr 200
Capital    Cr 1 000
```

---

# 191. Balance ajustée

```text
Cash       Dr 800
Rent       Dr 250
Capital    Cr 1 000
Accrued    Cr 50
```

---

# 192. Closing example

```text
Closing:
Capital   Dr 250
Rent      Cr 250
```

---

# 193. Balance post-clôture

```text
Cash       Dr 800
Capital    Cr 750
Accrued    Cr 50
Rent       0
```

---

# 194. La classification de clôture est configurable

L'exemple précédent reflète une stratégie de référence.

La vraie implémentation devra s'appuyer sur :

```text
ClosingPolicy
AccountRole
TrialBalanceVariantPolicy
```

---

# 195. Example reversal

Original :

```text
Dr Expense  100
Cr Bank     100
```

Reversal :

```text
Dr Bank     100
Cr Expense  100
```

Net :

```text
Expense 0
Bank    0
```

---

# 196. Example correction

```text
Original wrong entry
    POSTED

Reversal
    POSTED

Correct replacement
    POSTED
```

Le ledger montre les trois événements.

---

# 197. Reporting period

Une projection doit prendre une borne temporelle :

```text
date_from
date_to
```

indépendamment de l'exercice complet.

---

# 198. Périodes chevauchantes

Le domaine Accounting Periods devra empêcher les périodes incompatibles selon sa policy.

Le ledger suppose une résolution de période non ambiguë.

---

# 199. Opening balances

Le solde d'ouverture d'une query n'est pas nécessairement une `OPENING` entry.

C'est :

```text
sum of eligible previous movements
```

---

# 200. `OPENING` EntryType

Une `OPENING` entry est un type d'écriture métier.

Elle est distincte du concept query :

```text
opening balance
```

---

# 201. Materialized ledger future

Schema possible :

```text
LedgerProjectionRow
|
+-- entity_id
+-- account_id
+-- entry_id
+-- line_id
+-- accounting_date
+-- posting_sequence
+-- debit
+-- credit
+-- signed_balance
```

---

# 202. Rebuildability test

```text
delete materialized ledger

rebuild from canonical lines

expected rows / totals unchanged
```

---

# 203. Snapshot de balance

Une balance utilisée pour publication peut être figée :

```text
TrialBalanceSnapshot
```

---

# 204. P0 vs snapshot

P0 peut fonctionner sans `TrialBalanceSnapshot`.

Le besoin devient important pour :

```text
reporting publication
audit
financial analysis reproducibility
```

---

# 205. `TrialBalanceSnapshot`

```text
TrialBalanceSnapshot
|
+-- entity_id
+-- period
+-- variant
+-- definition_version
+-- source_watermark
+-- rows
+-- totals
+-- generated_at
+-- checksum
```

---

# 206. Relationship to ReportSnapshot

```text
TrialBalanceSnapshot
    ->
Financial Statements
    ->
ReportSnapshot
```

---

# 207. Eventual consistency marker

Si projections asynchrones :

```text
projection_as_of_posting_sequence
```

doit être exposé.

---

# 208. API publique - create

```python
entry = accounting.entries.create(
    entity_id=entity_id,
    journal_id=journal_id,
    accounting_date=date(...),
    description="...",
)
```

---

# 209. API publique - add line

```python
entry.add_line(
    account_id=expense_account,
    debit=Decimal("100.00"),
    credit=Decimal("0"),
)
```

---

# 210. API publique - validate

```python
result = accounting.entries.validate(
    entry_id=entry.id,
)
```

---

# 211. API publique - post

```python
result = accounting.entries.post(
    entry_id=entry.id,
    expected_revision=entry.revision,
)
```

---

# 212. API publique - reverse

```python
result = accounting.entries.reverse(
    entry_id=entry.id,
    reversal_date=date(...),
    reason="Correction",
)
```

---

# 213. API publique - journal

```python
page = accounting.journal.query(
    entity_id=entity_id,
    date_from=...,
    date_to=...,
)
```

---

# 214. API publique - ledger

```python
ledger = accounting.ledger.query(
    entity_id=entity_id,
    account_ids=(account_id,),
    date_from=...,
    date_to=...,
)
```

---

# 215. API publique - trial balance

```python
balance = accounting.trial_balance.build(
    entity_id=entity_id,
    fiscal_year_id=fiscal_year_id,
    variant=TrialBalanceVariant.ADJUSTED,
)
```

---

# 216. Package domaine

```text
src/pyaccountingkit/domain/
|
+-- journals/
|   +-- journal.py
|   +-- journal_type.py
|   +-- entry.py
|   +-- line.py
|   +-- entry_type.py
|   +-- status.py
|
+-- posting/
|   +-- validator.py
|   +-- posting_service.py
|   +-- posting_context.py
|   +-- posting_result.py
|   +-- reversal_service.py
|   +-- reversal_request.py
|   +-- reversal_result.py
|   +-- errors.py
|
+-- ledger/
    +-- balance.py
    +-- variants.py
    +-- projection_definition.py
```

---

# 217. Application package

```text
application/accounting/
|
+-- create_entry.py
+-- update_draft_entry.py
+-- validate_entry.py
+-- post_entry.py
+-- reverse_entry.py
```

---

# 218. Query package

```text
application/queries/
|
+-- journal.py
+-- general_ledger.py
+-- trial_balance.py
```

---

# 219. Ports

```text
JournalRepository

JournalEntryRepository

AccountingPeriodRepository

CompanyAccountRepository

UnitOfWork

Clock

AuditPort

IdempotencyStore

AccountingJournalQuery

GeneralLedgerQuery

TrialBalanceQuery
```

---

# 220. Adapter SQL

Un adapter peut optimiser :

```text
journal query

window running balance

trial balance GROUP BY

pagination

materialized projections
```

sans modifier l'API métier.

---

# 221. Adapter Django

Peut utiliser :

```text
transaction.atomic

select_for_update

Window

Sum
```

mais cette logique reste dans l'adapter.

---

# 222. Adapter SQLAlchemy

Peut fournir les mêmes garanties via :

```text
Session transaction

with_for_update

window functions
```

---

# 223. InMemory adapter

Doit permettre :

```text
unit tests

golden tests

property tests
```

sans base de données.

---

# 224. Complexité

Posting :

```text
O(number_of_entry_lines)
```

hors coût repository.

---

# 225. Ledger query

Complexité dépend :

```text
number of eligible lines
indexes
materialization strategy
```

---

# 226. Indexes recommandés

Persistence SQL :

```text
JournalEntry:
    entity_id
    journal_id
    period_id
    accounting_date
    status
    entry_type
    source
    posting_sequence

JournalEntryLine:
    entry_id
    account_id

Composite:
    entity_id + accounting_date + status
    account_id + accounting_date
```

---

# 227. Unique constraints

Selon policy :

```text
entry numbering uniqueness

idempotency key

reversal_of unique for full reversal
```

---

# 228. Reversal uniqueness

Pour P0 full reversal :

```text
UNIQUE(reversal_of)
```

peut être matérialisé dans l'adapter.

---

# 229. Transaction scope posting

Doit inclure :

```text
JournalEntry
relevant state checks
audit / outbox if atomic guarantee required
```

---

# 230. Transaction scope reversal

Doit inclure :

```text
lock original
check not already reversed
create reversal
validate
post reversal
mark original reversed
audit
commit
```

---

# 231. Failure during reversal

Si une étape échoue :

```text
rollback everything
```

Résultat interdit :

```text
reversal posted
but original not marked

or
original marked reversed
but reversal absent
```

---

# 232. Idempotence reversal

Même commande répétée avec même idempotency key :

```text
same ReversalResult
```

si identique.

---

# 233. Mismatched idempotency key

Même key mais autre payload :

```text
IdempotencyConflictError
```

---

# 234. Audit + outbox

Dans une implémentation production :

```text
accounting mutation
+
audit record
+
outbox event
```

peuvent être commités atomiquement.

---

# 235. Domain vs Audit event

```text
JournalEntryPosted
    = DomainEvent

ENTRY_POST
    = AuditEvent
```

---

# 236. Observabilité

Metrics :

```text
entries_created_total

entries_validated_total

entries_posted_total

entries_reversed_total

posting_failures_total

posting_duration

ledger_query_duration

trial_balance_build_duration
```

---

# 237. Logs structurés

Contexte utile :

```text
entity_id
entry_id
journal_id
period_id
status
correlation_id
```

Eviter de logger inutilement :

```text
full descriptions
PII
entire lines
```

---

# 238. Tracing

Spans possibles :

```text
validate_entry

post_entry

reverse_entry

build_general_ledger

build_trial_balance
```

---

# 239. Security boundary

L'autorisation n'est pas une responsabilité du domaine.

L'Application Layer décide :

```text
actor may validate?

actor may post?

actor may reverse?
```

---

# 240. SoD future

Une application peut imposer :

```text
creator != validator

validator != poster
```

via :

```text
ApprovalPolicy
```

hors invariant P0.

---

# 241. Bulk posting

Une API future peut poster plusieurs écritures.

Deux sémantiques :

```text
ALL_OR_NOTHING

PER_ENTRY
```

doivent être explicites.

---

# 242. P0 bulk

Non requis.

---

# 243. Batch import

L'import peut batcher techniquement les écritures.

Mais l'audit/provenance par écriture doit rester disponible.

---

# 244. Ledger integrity check

Contrôle :

```text
sum all debits
=
sum all credits
```

dans un périmètre fermé cohérent.

---

# 245. Pourquoi un contrôle global peut différer

Un filtre partiel peut naturellement produire :

```text
debit != credit
```

par exemple si on filtre un seul compte.

Le contrôle d'équilibre s'applique au bon périmètre.

---

# 246. Projection scope

Chaque projection doit expliciter :

```text
entity
dates
accounts
entry types
status
dimensions
variant
```

---

# 247. `AccountingScope`

```text
AccountingScope
|
+-- entity_id
+-- period?
+-- date_range?
+-- account_filter?
+-- entry_type_filter?
+-- dimensions?
```

---

# 248. Pas de scope implicite global

Interdit :

```text
query all entities
```

par défaut.

---

# 249. Reproducibilité

Pour reproduire une balance :

```text
AccountingScope
+
TrialBalanceVariantPolicy version
+
source watermark
=
reproducible result
```

---

# 250. `LedgerProjectionDefinition`

```text
LedgerProjectionDefinition
|
+-- version
+-- eligible_statuses
+-- ordering
+-- signed_balance_convention
```

---

# 251. `TrialBalanceDefinition`

```text
TrialBalanceDefinition
|
+-- variant
+-- policy_version
+-- included_entry_types
+-- zero_balance_policy
```

---

# 252. Versioning

Changer :

```text
which EntryType belongs to BEFORE_ADJUSTMENTS
```

doit changer :

```text
TrialBalanceDefinitionVersion
```

---

# 253. Pas de breaking semantic change silencieux

Une release ne doit pas modifier la définition d'une projection existante sans version ou migration.

---

# 254. Comparatives

Les balances N/N-1 peuvent utiliser des versions différentes de chart ou policy.

Le reporting doit conserver ce contexte.

---

# 255. Consolidation future

Le ledger statutaire reste par entité.

Consolidation consomme :

```text
entity trial balances
```

et ajoute ses propres ajustements hors ledger statutaire.

---

# 256. Financial Analysis

Consomme :

```text
TrialBalance / Financial Statements
```

sans écrire dans le ledger.

---

# 257. Closing

Le prochain document `08` détaillera :

```text
adjustments
accruals
provisions
closing entries
period lock
opening
```

Ce document définit déjà les primitives nécessaires :

```text
ADJUSTING
CLOSING
OPENING
TrialBalanceVariant
```

---

# 258. Anti-pattern - ledger table comme source primaire

Interdit :

```text
update account balance directly
```

---

# 259. Anti-pattern - account current_balance mutable

Eviter :

```text
CompanyAccount.current_balance
```

comme vérité métier.

Un cache technique peut exister, mais il doit être reconstructible.

---

# 260. Anti-pattern - edit posted entry

Interdit :

```text
entry.lines[0].debit = ...
entry.save()
```

si `POSTED`.

---

# 261. Anti-pattern - reverse by delete

Interdit :

```text
DELETE original entry
```

---

# 262. Anti-pattern - reverse by negative flag

Eviter un simple :

```text
entry.cancelled = True
```

sans écriture de contre-passation.

---

# 263. Anti-pattern - projection excludes reversed original

Eviter de neutraliser en supprimant l'original des agrégats si la reversal est elle-même comptabilisée.

---

# 264. Anti-pattern - mutable running balance

Eviter de stocker un cumul ligne par ligne comme vérité non reconstructible.

---

# 265. Anti-pattern - query ordering unstable

Interdit de calculer un running balance sans ordre déterministe.

---

# 266. Anti-pattern - business logic in templates

Le calcul du grand livre ou de la balance appartient au query layer.

---

# 267. Anti-pattern - DB technology in domain

Interdit :

```text
Window
Sum
transaction.atomic
```

dans `domain/`.

---

# 268. Anti-pattern - posting without revalidation

Une validation historique ne garantit pas que le contexte est encore valide.

---

# 269. Anti-pattern - bypass policies

Une écriture générée automatiquement ne contourne pas les mêmes invariants.

---

# 270. ADRs

| ID | Décision |
|---|---|
| ADR-LED-001 | `JournalEntry` est l'Aggregate Root transactionnel central |
| ADR-LED-002 | `JournalEntryLine` appartient à `JournalEntry` |
| ADR-LED-003 | La source canonique est constituée des écritures/lignes/comptes/périodes |
| ADR-LED-004 | Journal report, General Ledger et Trial Balance sont des projections |
| ADR-LED-005 | DRAFT ne contribue pas au ledger |
| ADR-LED-006 | VALIDATED ne contribue pas au ledger |
| ADR-LED-007 | Toute écriture postée est équilibrée |
| ADR-LED-008 | Toute écriture POSTED est immutable |
| ADR-LED-009 | La correction passe par reversal + nouvelle écriture |
| ADR-LED-010 | Une reversal est une nouvelle écriture |
| ADR-LED-011 | L'écriture originale reste historiquement visible |
| ADR-LED-012 | Les lignes d'une écriture REVERSED restent dans le ledger ; la neutralisation vient de la reversal |
| ADR-LED-013 | P0 supporte la reversal intégrale |
| ADR-LED-014 | Posting et reversal sont atomiques |
| ADR-LED-015 | Le domaine exprime la concurrence sans dépendre d'un mécanisme SQL |
| ADR-LED-016 | `revision` supporte optimistic concurrency |
| ADR-LED-017 | Les adapters peuvent utiliser pessimistic locking |
| ADR-LED-018 | `signed_balance = debit - credit` est une convention de projection P0 |
| ADR-LED-019 | Running balance utilise un ordre déterministe |
| ADR-LED-020 | Opening balance est calculé depuis les mouvements antérieurs |
| ADR-LED-021 | BEFORE_ADJUSTMENTS / ADJUSTED / POST_CLOSING sont des variants de projection |
| ADR-LED-022 | La composition des variants est versionnée par policy |
| ADR-LED-023 | Les comptes à solde nul sont une option de présentation |
| ADR-LED-024 | Le drill-down jusqu'à `JournalEntryLine` est une capacité architecturale |
| ADR-LED-025 | Les projections matérialisées restent reconstructibles |
| ADR-LED-026 | Toutes les queries sont scopées par `AccountingEntityId` |
| ADR-LED-027 | L'import direct POSTED exige une policy explicite de source déjà validée |
| ADR-LED-028 | `EntryType` est distinct de `JournalType` |
| ADR-LED-029 | `AccountRole`/policy détermine les catégories métier, pas un préfixe universel |
| ADR-LED-030 | Le Ledger ne connaît pas Django, SQLAlchemy ou PostgreSQL |

---

# 271. Critères d'acceptation P0.8

```text
[ ] Journal est défini

[ ] JournalEntry est défini comme Aggregate Root

[ ] JournalEntryLine est interne à l'aggregate

[ ] DRAFT / VALIDATED / POSTED / REVERSED sont définis

[ ] DRAFT -> POSTED direct est interdit

[ ] validation vérifie au moins deux lignes

[ ] débit et crédit simultanés sont interdits

[ ] posting revalide les invariants critiques

[ ] posting exige une période autorisée

[ ] posting exige des comptes actifs/postables

[ ] posting est atomique

[ ] posting gère la concurrence

[ ] POSTED est immutable

[ ] reversal crée une nouvelle écriture

[ ] reversal inverse débit/crédit

[ ] reversal conserve `reversal_of`

[ ] original reste inchangé

[ ] double reversal est bloquée

[ ] journal de restitution exclut DRAFT/VALIDATED

[ ] REVERSED original reste visible

[ ] grand livre calcule opening / movements / running / closing

[ ] running balance possède un ordre déterministe

[ ] signed balance convention est explicite

[ ] Trial Balance est une projection

[ ] BEFORE_ADJUSTMENTS est spécifié

[ ] ADJUSTED est spécifié

[ ] POST_CLOSING est spécifié

[ ] variant composition est policy-driven

[ ] balance vérifie debit total == credit total

[ ] drill-down Balance -> Ledger -> Entry fonctionne

[ ] toutes les queries sont multi-entity scoped

[ ] aucune projection n'est source primaire

[ ] les golden tests CFA FRA sont identifiés
```

---

# 272. Ordre d'implémentation recommandé

## LED-00 - Primitives

```text
JournalId
JournalEntryId
JournalEntryLineId
EntryNumber
EntryType
EntryStatus
PostingSequence
```

---

## LED-01 - Journal

```text
Journal
JournalType
JournalRepository
```

---

## LED-02 - JournalEntry Aggregate

```text
JournalEntry
JournalEntryLine
draft mutations
```

---

## LED-03 - Validation

```text
JournalEntryValidator
EntryValidationContext
EntryValidationResult
```

---

## LED-04 - Posting

```text
PostingService
PostingContext
PostingResult
revision
UnitOfWork
```

---

## LED-05 - Reversal

```text
ReversalService
ReversalRequest
ReversalResult
reversal_of
```

---

## LED-06 - Accounting Journal Query

```text
AccountingJournalQuery
filters
pagination
drill-down
```

---

## LED-07 - General Ledger

```text
opening balance
movements
running balance
closing balance
```

---

## LED-08 - Trial Balance

```text
BEFORE_ADJUSTMENTS
ADJUSTED
POST_CLOSING
```

---

## LED-09 - Projection integrity

```text
rebuild
checks
golden tests
```

---

# 273. Démonstrateur P0.8

Scénario recommandé :

```text
1. Create entity

2. Create active period

3. Create chart

4. Create:
      Cash account
      Expense account
      Capital account

5. Create journal

6. Create opening entry:
      Dr Cash 1,000
      Cr Capital 1,000

7. Validate

8. Post

9. Create normal entry:
      Dr Expense 200
      Cr Cash 200

10. Validate

11. Post

12. Query journal

13. Query Cash ledger

14. Verify:
      opening = 1,000 Dr
      movement = 200 Cr
      closing = 800 Dr

15. Build BEFORE_ADJUSTMENTS balance

16. Reverse expense entry

17. Verify original unchanged

18. Verify reversal posted

19. Verify ledger net movement cancelled

20. Verify journal displays original + reversal

21. Build Trial Balance

22. Verify global debit = global credit
```

---

# 274. Démonstrateur adjusted / closing

```text
1. Add adjusting entry:
      Dr Expense 50
      Cr Accrued 50

2. Build:
      BEFORE_ADJUSTMENTS

3. Build:
      ADJUSTED

4. Add closing entry

5. Build:
      POST_CLOSING

6. Verify:
      temporary account closes
      permanent balances remain
```

Les règles exactes de closing seront détaillées dans le document suivant.

---

# 275. Impact sur le prochain document

Le prochain document est :

```text
08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md
```

Il devra détailler :

```text
AccountingPeriod lifecycle

cut-off

accruals

deferrals

provisions

depreciation runs

impairment runs

adjusting entries

closing entries

temporary accounts

post-closing trial balance

period close

period reopen

opening balances
```

en réutilisant strictement :

```text
JournalEntry
EntryType
PostingService
ReversalService
TrialBalanceVariant
```

sans créer un second moteur de posting.

---

# 276. Conclusion

L'architecture du coeur comptable est désormais :

```text
DRAFT ENTRY
    |
    v
VALIDATION
    |
    v
VALIDATED ENTRY
    |
    v
POSTING
    |
    v
POSTED ENTRY
    |
    +----------------------+
    |                      |
    v                      v
REVERSAL                READ MODELS
    |                      |
    v                      +--> Journal
POSTED reversal            +--> General Ledger
                           +--> Trial Balance
```

Les règles fondamentales sont :

```text
JournalEntry is canonical

JournalEntryLine is atomic inside its aggregate

Posted means immutable

Correction means reversal, not edit

Ledger is derived

Trial Balance is derived

Reversed originals remain historically visible

Running balances require deterministic ordering

Projection variants are policy-driven

Every projection must drill down to source entries

Every projection must be rebuildable
```

Le P0.8 ferme ainsi la spécification du **noyau transactionnel minimal** nécessaire avant d'aborder les opérations de fin de période.

---

**Prochain document recommandé :**

```text
08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md
```


---

## Sources et références documentaires du projet

- 📕 [Comptabilité Générale — Système français et normes IFRS](../../books/Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md)
- 📂 [Référentiels réglementaires — Datasets](../../referentiels/datasets/)
- 📐 [Référentiels réglementaires — Schémas](../../referentiels/schemas/)
- 🏗️ [CFA FRA Django MVP Sprint 7 — Référence fonctionnelle](../../../resources/cfa_fra_django_mvp_sprint_7/)
- 📄 [CFA FRA — Document de conception](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md)

---

## Plans d'implémentation principaux

Ce document est couvert par les plans suivants :

- [PLAN-01 — Accounting Core (0.1.0)](../../plans/PLAN-01_ACCOUNTING_CORE_0.1.0.md)
- [PLAN-03 — Imports & Reporting (0.3.0)](../../plans/PLAN-03_IMPORTS_REPORTING_0.3.0.md)
