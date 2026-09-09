# 18 - PyAccountingKit - Cartographie d'extraction et de migration depuis CFA FRA

> **Projet** : PyAccountingKit  
> **Document** : `18_PYACCOUNTINGKIT_CFA_FRA_EXTRACTION_AND_MIGRATION_MAP.md`  
> **Statut** : P1.7 - Extraction, réécriture, migration et golden-oracle CFA FRA  
> **Langue** : Français  
> **Objet** : Définir précisément ce qui doit être extrait du projet CFA FRA, ce qui doit être réécrit pour devenir framework-neutral, ce qui doit rester un adapter Django/PostgreSQL, ce qui doit être conservé comme oracle de non-régression, et ce qui ne doit pas migrer dans le core PyAccountingKit.

---

# 1. Résumé exécutif

CFA FRA ne doit pas être transformé en PyAccountingKit par un simple :

```text
copy / paste
```

Le bon modèle est :

```text
CFA FRA
    |
    +--> Behavioral Oracle
    |
    +--> Domain Knowledge Extraction
    |
    +--> Golden Fixtures
    |
    +--> Adapter Reference
    |
    +--> Consumer Application
    |
    v
PyAccountingKit
```

La migration doit distinguer cinq catégories :

```text
EXTRACT
    concept / invariant / behavior to preserve

REWRITE
    behavior kept, implementation replaced

ADAPTER
    framework-specific implementation outside domain

GOLDEN
    executable reference / non-regression oracle

DO_NOT_MIGRATE
    UI / app-specific / legacy infrastructure concern
```

La règle principale est :

```text
CFA FRA is a reference implementation

CFA FRA is not the runtime dependency of PyAccountingKit
```

---

# 2. Base documentaire analysée

La présente cartographie s'appuie sur les sources CFA FRA disponibles dans la conversation :

```text
CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md

CFA_FRA_DJANGO_MVP_PLAN_IMPLEMENTATION_DJANGO_HTMX.md

SPRINT_4_README.md

SPRINT_5_README.md

SPRINT_6_README.md

README.md
```

Ces documents décrivent un MVP Django/PostgreSQL avec une architecture :

```text
models
services
selectors
views
```

où les services portent les mutations métier et les selectors les lectures complexes. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

---

# 3. Position de CFA FRA dans PyAccountingKit

CFA FRA doit jouer quatre rôles.

## 3.1 Référence fonctionnelle

CFA FRA démontre des workflows déjà exécutables :

```text
entry creation

validation

posting

reversal

FEC import

ledger

trial balance

financial statements

controls

closing

audit
```

---

## 3.2 Oracle de non-régression

Le document de conception décrit explicitement le classeur Excel comme oracle de comparaison et liste des tests fondamentaux comme l'équilibre d'écriture, l'équilibre de balance, le bilan, le cash-flow, l'idempotence FEC, l'immutabilité des écritures postées et le blocage du posting sur période fermée. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

PyAccountingKit doit prolonger cette idée :

```text
Excel historical oracle
        +
CFA FRA Django executable oracle
        ↓
PyAccountingKit golden suite
```

---

## 3.3 Référence d'adapter Django/PostgreSQL

CFA FRA montre déjà des choix techniques Django/PostgreSQL utiles comme référence d'implémentation :

```text
transaction.atomic

select_for_update

Django ORM aggregation

PostgreSQL window functions

bulk operations
```

Ces choix ne deviennent cependant pas des dépendances du domaine.

---

## 3.4 Première application consommatrice future

La cible de long terme est :

```text
CFA FRA Django
    ↓
PyAccountingKit public API
```

CFA FRA peut donc devenir :

```text
application consumer
+
Django adapter integration testbed
```

plutôt que rester propriétaire de son propre moteur comptable parallèle.

---

# 4. Règle d'autorité

Lorsqu'une divergence apparaît entre :

```text
CFA FRA implementation

et

PyAccountingKit architecture
```

la priorité est :

```text
1. invariants comptables formalisés PyAccountingKit
2. current regulatory-accounting-data-framework pour faits réglementaires
3. behavior CFA FRA s'il représente un cas fonctionnel valide
4. implementation detail CFA FRA
```

---

# 5. Ce qui est migré

PyAccountingKit extrait de CFA FRA :

```text
business behavior

domain invariants

workflow semantics

golden scenarios

control expectations

traceability expectations
```

---

# 6. Ce qui n'est pas migré directement

PyAccountingKit ne copie pas comme core :

```text
Django models

Django forms

Django views

HTMX routes

HTML templates

QuerySets

transaction.atomic decorators

select_for_update calls

PostgreSQL-specific SQL

Celery orchestration

Chart.js dashboard

RBAC implementation
```

---

# 7. Taxonomie de décision

Chaque composant CFA FRA reçoit une décision parmi :

| Code | Signification |
|---|---|
| `EXTRACT` | Concept / règle à extraire dans le domaine |
| `REWRITE` | Sémantique conservée, code réécrit |
| `ADAPTER` | Reste dépendant d'une technologie |
| `GOLDEN` | Utilisé comme oracle / fixture / preuve |
| `CONSUMER` | Reste dans CFA FRA comme application cliente |
| `DEFER` | Concept utile mais hors scope immédiat |
| `DROP` | Ne doit pas migrer dans PyAccountingKit |

---

# 8. Vue globale de migration

```text
CFA FRA
|
+-- accounting/models ----------- REWRITE
+-- accounting/services --------- EXTRACT + REWRITE
+-- accounting/selectors -------- EXTRACT + REWRITE
+-- imports/FEC ----------------- EXTRACT + ADAPTER
+-- reporting ------------------- EXTRACT + REWRITE
+-- financial_statements -------- EXTRACT + REWRITE
+-- controls -------------------- EXTRACT + REWRITE
+-- closing --------------------- EXTRACT + REWRITE
+-- referentials ---------------- REPLACE
+-- analytics ------------------- EXTRACT selectively
+-- audit ----------------------- EXTRACT + REWRITE
+-- exports --------------------- ADAPTER
+-- users/RBAC ------------------ CONSUMER
+-- templates/HTMX -------------- CONSUMER / DROP from core
+-- PostgreSQL specifics -------- ADAPTER
+-- Excel scenarios ------------- GOLDEN
```

---

# 9. Accounting Core - source CFA FRA

Le modèle canonique CFA FRA comprend notamment :

```text
Organization
FiscalYear
AccountingPeriod
ChartOfAccounts
Account
Journal
JournalEntry
JournalLine
```

et le README affirme que grand livre, balance et états financiers sont des projections calculées, pas la source de vérité. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

---

# 10. Mapping Accounting Core

| CFA FRA | PyAccountingKit | Décision |
|---|---|---|
| `Organization` | `AccountingEntity` / Identity context | REWRITE |
| `FiscalYear` | `FiscalYear` | EXTRACT + REWRITE |
| `AccountingPeriod` | `AccountingPeriod` | EXTRACT + REWRITE |
| `ChartOfAccounts` | `CompanyChartOfAccounts` | REWRITE |
| `Account` | `CompanyAccount` | REWRITE |
| `Journal` | `Journal` | EXTRACT + REWRITE |
| `JournalEntry` | `JournalEntry` | EXTRACT + REWRITE |
| `JournalLine` | `JournalEntryLine` | EXTRACT + REWRITE |

---

# 11. Pourquoi `Organization` devient `AccountingEntity`

CFA FRA est une application multi-organisation.

PyAccountingKit généralise le concept :

```text
Organization
    ->
AccountingEntity
```

pour ne pas imposer qu'une entité comptable soit nécessairement une organisation web/app.

Le document CFA FRA impose déjà un scoping organisationnel de toutes les requêtes métier. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

La règle est conservée sous forme générique :

```text
all accounting objects are entity-scoped
```

---

# 12. Account : séparation du modèle

Dans CFA FRA, `Account` contient notamment :

```text
organization
chart
code
name
account_type
normal_balance
parent
framework_account
is_active
```

avec unicité du code dans `(organization, chart)`. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

PyAccountingKit sépare ce modèle en :

```text
CompanyAccount

RegulatoryAccountBinding

StatementAccountMapping
```

---

# 13. Migration `framework_account`

CFA FRA peut attacher `Account.framework_account`.

Cette simplification ne doit pas être copiée telle quelle.

Cible :

```text
CompanyAccount
    |
    +--> RegulatoryAccountBinding
              |
              v
         ReferenceAccount
```

---

# 14. Justification du mapping réglementaire

CFA FRA distingue déjà explicitement le plan réel de l'entreprise et le référentiel réglementaire. Il illustre par exemple plusieurs comptes fournisseurs entreprise convergeant vers une classe de référence. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

La séparation conceptuelle est donc :

```text
CFA FRA concept
    -> retained

CFA FRA direct FK implementation
    -> rewritten
```

---

# 15. `AccountMapping`

CFA FRA modélise un `AccountMapping` avec :

```text
account
framework_account
mapping_type
confidence
validated_by
```

et prévoit un chemin candidat -> validation humaine. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Migration :

```text
AccountMapping
    ->
RegulatoryAccountBinding
+
MappingCandidate / review metadata
```

---

# 16. Interdit lors de la migration

Ne pas convertir :

```text
confidence
```

en autorisation automatique universelle.

La validation humaine ou les règles explicites de `regulatory-accounting-data-framework` restent prioritaires.

---

# 17. JournalEntry workflow

CFA FRA définit :

```text
DRAFT
VALIDATED
POSTED
REVERSED
```

et précise qu'une entrée `POSTED` est immuable. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT
```

---

# 18. PyAccountingKit workflow cible

```text
DRAFT
    ↓
VALIDATED
    ↓
POSTED
    ↓
REVERSED
```

Avec interdiction de mutation comptable après POSTED.

---

# 19. Entry validation

CFA FRA exige :

```text
at least 2 lines
debit >= 0
credit >= 0
not debit and credit simultaneously
account active
period open
journal active
total debit = total credit
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT as accounting rules/invariants
```

---

# 20. Mapping vers PyAccountingKit

```text
CFA FRA validation
    ->
03_ACCOUNTING_RULES_AND_INVARIANTS
    +
07_LEDGER_POSTING_AND_REVERSAL
```

Le comportement est conservé, mais :

```text
Django validators
```

deviennent :

```text
domain validation
application services
```

---

# 21. PostingService

Le pseudo-code CFA FRA utilise :

```python
@transaction.atomic
def post_entry(...):
    validate_period(...)
    validate_entry(...)
    entry.status = POSTED
    ...
    create_audit_event(...)
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

---

# 22. Décision PostingService

```text
Business semantics:
    EXTRACT

Django transaction implementation:
    ADAPTER

Application service:
    REWRITE
```

---

# 23. Cible PyAccountingKit

```text
PostEntry
    |
    v
UnitOfWork
    |
    +--> load/lock
    +--> validate period
    +--> validate entry
    +--> transition POSTED
    +--> audit
    +--> outbox
    |
    v
commit
```

---

# 24. `transaction.atomic`

CFA FRA exige que validation, posting et audit soient enregistrés ensemble dans une transaction. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Le besoin est extrait :

```text
atomic command boundary
```

mais le décorateur Django ne migre pas dans le domaine.

---

# 25. Cible persistence

```text
PyAccountingKit UnitOfWork contract
    |
    +--> Django adapter
    |      transaction.atomic
    |
    +--> SQLAlchemy adapter
           Session transaction
```

---

# 26. ReversalService

CFA FRA crée une nouvelle écriture avec :

```text
debit <-> credit
reversal_of
```

tout en conservant l'original inchangé. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT + REWRITE
```

---

# 27. Cible Reversal

```text
Original POSTED
    remains immutable
        |
        v
New Reversal Entry
    debit/credit inverted
        |
        v
link reversal_of
```

---

# 28. Ce qui ne migre pas de Reversal

La convention :

```text
REV-<entry_number>
```

est une convention CFA FRA.

Elle devient :

```text
EntryNumberPolicy
```

ou configuration application.

---

# 29. Ledger

CFA FRA calcule les soldes cumulés via PostgreSQL `Window + Sum` et utilise un ordre stable de mouvements. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
query semantics -> EXTRACT

PostgreSQL implementation -> ADAPTER
```

---

# 30. Convention signed balance

CFA FRA utilise :

```text
signed_balance = debit - credit
```

puis sépare solde débiteur/créditeur en présentation. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

PyAccountingKit conserve cette convention uniquement comme :

```text
projection convention / policy
```

et non comme invariant universel de tous les read models.

---

# 31. Trial Balance variants

CFA FRA possède :

```text
BEFORE_ADJUSTMENTS
ADJUSTED
POST_CLOSING
```

avec des types d'écritures inclus/exclus distincts. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT
```

---

# 32. Mapping Trial Balance

```text
CFA FRA Trial Balance variants
    ->
TrialBalanceVariant / StatementSourcePolicy
```

---

# 33. Convention JOD

CFA FRA indique qu'au MVP les écritures du journal `JOD` sont normalisées en `ADJUSTING`, tout en précisant que cette convention peut être trop large. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
DO NOT EXTRACT AS UNIVERSAL RULE
```

---

# 34. Cible

```text
source-specific classification
    ->
ImportClassificationPolicy
```

Le journal `JOD` ne devient pas une vérité générique PyAccountingKit.

---

# 35. FEC - architecture source

Le pipeline CFA FRA est :

```text
Upload
    ↓
original file storage
    ↓
Parsing
    ↓
FECRawLine
    ↓
validation
    ↓
account/journal detection
    ↓
duplicate detection
    ↓
normalization
    ↓
JournalEntry + JournalLine
    ↓
double-entry controls
    ↓
POSTED
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

---

# 36. Décision FEC globale

```text
pipeline semantics:
    EXTRACT

generic import architecture:
    REWRITE

FEC parser:
    ADAPTER

Django models:
    REWRITE / ADAPTER

fixtures:
    GOLDEN
```

---

# 37. `FECImport`

CFA FRA stocke :

```text
organization
fiscal_year
original_filename
original_file
sha256
status
imported_at
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Migration :

```text
FECImport
    ->
AccountingImportBatch
+
SourceArtifact
+
ImportSourceFingerprint
```

---

# 38. `FECRawLine`

CFA FRA stocke :

```text
line_number
journal
entry
account
auxiliary
piece
amounts
raw_data
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Migration :

```text
FECRawLine
    ->
RawImportRecord
```

dans le core import générique, plus :

```text
FEC-normalized DTO
```

dans l'adapter.

---

# 39. Raw source preservation

Sprint 4 précise que chaque ligne conserve notamment :

```text
line_number
row_hash
normalized_entry_key
is_valid
raw_data
```

pour audit, debug, reprocessing et preuve d'origine. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT strongly
```

---

# 40. FEC field list

Sprint 4 attend les 18 colonnes FEC standards et supporte TAB ainsi que plusieurs encodages. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
FEC adapter only
```

Ces champs ne doivent pas migrer dans :

```text
domain/imports generic core
```

---

# 41. FEC controls

Sprint 4 distingue contrôles bloquants et warnings, y compris `FEC_DUPLICATE_LINE` en warning. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
control semantics -> EXTRACT

FEC control names -> adapter-specific
```

---

# 42. Duplicate line hash

Sprint 4 calcule un SHA-256 de ligne mais laisse le doublon comme warning car certaines répétitions sont légitimes. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT principle:
    heuristic duplicate != confirmed duplicate
```

---

# 43. FEC grouping

Sprint 4 utilise différentes clés selon les journaux et prévoit un traitement spécial `JAN`. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
CFA FRA grouping behavior:
    GOLDEN

generic grouping:
    REWRITE as strategy

JAN/JOD-specific assumptions:
    FEC adapter policy, not core
```

---

# 44. Double-entry FEC control

Chaque groupe normalisé et le fichier global doivent vérifier :

```text
SUM(Debit) = SUM(Credit)
```

et toute anomalie bloque l'import. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT
```

---

# 45. FEC idempotence

CFA FRA propose :

```text
organization
+
fiscal_year
+
SHA256
```

et des clés complémentaires autour journal/entry/date/piece. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Migration :

```text
batch idempotence
+
entry idempotence
```

dans l'architecture PyAccountingKit.

---

# 46. Import direct POSTED

Sprint 4 précise que l'import final crée directement des écritures `POSTED` car le FEC représente une comptabilité déjà validée dans le système source. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

---

# 47. Décision PyAccountingKit sur ce comportement

Ce comportement est conservé **comme cas métier**, mais pas comme transition universelle.

Mapping :

```text
CFA FRA direct POSTED import
    ->
TRUSTED_POSTED_HISTORY_IMPORT
```

---

# 48. Important

Le mode trusted :

```text
does not mean:
    skip validation

does mean:
    source is imported as already-posted history
```

Il doit toujours vérifier :

```text
balance
accounts
period migration policy
provenance
idempotence
```

---

# 49. Import transactionnel

Sprint 4 utilise :

```text
transaction.atomic
select_for_update on FECImport
bulk JournalEntry / JournalLine
rollback complete on error
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
atomicity + rollback semantics -> EXTRACT

Django locking -> ADAPTER
```

---

# 50. Reporting - Journal / Ledger / Trial Balance

CFA FRA sépare déjà :

```text
POSTED JournalLine
    ->
Journal
    ->
General Ledger
    ->
Trial Balance
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT projection architecture
```

---

# 51. Financial Statements

Sprint 6 décrit :

```text
Account
    +--> JournalLine
    +--> StatementAccountMapping
JournalLine -> Trial Balance
StatementAccountMapping -> StatementLine
both -> Financial Statements Engine
    -> Income
    -> Balance
    -> Cash Flow
    -> Ratios
    -> Drill-down
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT architecture

REWRITE implementation
```

---

# 52. `StatementAccountMapping`

Migration directe conceptuelle :

```text
CFA FRA StatementAccountMapping
    ->
PyAccountingKit StatementAccountMapping
```

Ce mapping reste distinct du binding réglementaire.

---

# 53. Mapping diagnostics

Sprint 6 mesure :

```text
accounts total
mapped
unmapped
coverage %
```

et signale les comptes non mappés avec montant non nul pour éviter un état silencieusement incomplet. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT
```

vers :

```text
StatementMappingCoverage
STATEMENT_MAPPING_COMPLETE
```

---

# 54. Financial Statement Drill-down

Sprint 6 relie :

```text
StatementLine
    ->
StatementAccountMapping
    ->
Account
    ->
Grand Livre
    ->
JournalEntry
    ->
JournalLine source
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT strongly
```

---

# 55. Financial ratios

Sprint 6 livre :

```text
NET_MARGIN
ROA
CURRENT_RATIO
DEBT_TO_ASSETS
EQUITY_RATIO
CFO_TO_REVENUE
ASSET_TURNOVER
```

et les décrit comme analytiques, non réglementaires. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
GOLDEN + EXTRACT to Financial Analysis
```

---

# 56. Ratio implementation

Ne pas copier comme constantes figées.

Migration :

```text
ratio code
    ->
FinancialRatioDefinition

formula
    ->
versioned analytical formula
```

---

# 57. Comparatifs N-1

Sprint 6 calcule N / N-1 pour compte de résultat, bilan et cash-flow lorsqu'un exercice précédent est disponible. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT concept
```

mais PyAccountingKit ajoute le pinning des versions et la comparabilité sémantique.

---

# 58. Frontière réglementaire du Sprint 6

Sprint 6 affirme explicitement que son moteur d'états financiers reste distinct des formats réglementaires officiels et prévoit un mapping réglementaire séparé. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT as major architecture boundary
```

---

# 59. Cible PyAccountingKit

```text
Financial Statement Engine
    !=
Regulatory Reporting Engine
```

Cette séparation existe donc déjà conceptuellement dans CFA FRA et doit être conservée.

---

# 60. Cash-flow

CFA FRA décrit les catégories :

```text
OPERATING
INVESTING
FINANCING
TRANSFER
OPENING
```

et la réconciliation :

```text
Opening Cash
+
Operating Cash Flow
+
Investing Cash Flow
+
Financing Cash Flow
=
Closing Cash
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT reconciliation behavior
```

---

# 61. Cash-flow categories

Les catégories CFA FRA peuvent devenir :

```text
starter CashFlowDefinition
```

mais ne doivent pas être hardcodées comme seule méthode possible.

---

# 62. Controls

CFA FRA liste notamment :

```text
ENTRY_BALANCED
ACCOUNT_EXISTS
ACCOUNT_ACTIVE
PERIOD_OPEN
DEBIT_OR_CREDIT_ONLY
ENTRY_HAS_AT_LEAST_TWO_LINES
FEC_DUPLICATE
FEC_REQUIRED_FIELDS
TRIAL_BALANCE_BALANCED
BALANCE_SHEET_BALANCED
CASHFLOW_RECONCILED
TEMPORARY_ACCOUNTS_CLOSED
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT
```

---

# 63. ControlResult

Le modèle Django CFA FRA stocke :

```text
organization
control_code
severity
status
expected_value
actual_value
details
```

Migration :

```text
ControlDefinition
ControlRun
ControlResult
ControlFinding
```

---

# 64. Ce qui est amélioré

PyAccountingKit sépare davantage :

```text
severity
blocking
status
evidence
scope
definition version
```

---

# 65. Audit

CFA FRA définit un `AuditEvent` avec notamment :

```text
user
organization
action
entity_type
entity_id
timestamp
before
after
source_ip
request_id
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT concept
REWRITE infrastructure
```

---

# 66. Audit migration

Cible :

```text
AuditEvent
+
ActorContext
+
CorrelationContext
+
ObjectReference
```

---

# 67. HTTP-specific audit fields

Des champs comme :

```text
source_ip
request_id
```

restent :

```text
optional metadata from adapter/runtime
```

et non contraintes du domaine comptable.

---

# 68. Audit action catalog

CFA FRA enregistre :

```text
FEC_UPLOAD
FEC_IMPORT
ENTRY_CREATE
ENTRY_VALIDATE
ENTRY_POST
ENTRY_REVERSE
ACCOUNT_CREATE
ACCOUNT_UPDATE
PERIOD_CLOSE
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
GOLDEN + starter audit vocabulary
```

---

# 69. Closing

CFA FRA définit :

```text
OPEN
    ->
REVIEW
    ->
CLOSING
    ->
CLOSED
```

et interdit le posting après fermeture. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT
```

---

# 70. Closing workflow

Le plan MVP décrit :

```text
Review controls
    ->
Generate closing entries
    ->
Validate
    ->
Post
    ->
Close period
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
EXTRACT + REWRITE
```

---

# 71. Closing gates

CFA FRA interdit la clôture lorsque :

```text
balance not balanced
cash flow unreconciled
DRAFT entries remain
blocking controls
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
GOLDEN + EXTRACT
```

---

# 72. Annual closing

CFA FRA prévoit :

```text
close temporary accounts
transfer result
generate opening balances
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Migration :

```text
ClosingPolicy
ClosingEntryGeneration
OpeningBalanceGeneration
```

---

# 73. Referentials - CFA FRA

CFA FRA avait prévu :

```text
AccountingFramework
FrameworkVersion
FrameworkAccount
```

pour SYSCOHADA et IFRS. *(→ source : [regulatory-accounting-data-framework](../../../resources/regulatory-accounting-data-framework/))*

Décision :

```text
DO NOT MIGRATE REFERENCE DATA
```

---

# 74. Pourquoi

PyAccountingKit dispose désormais d'une architecture dédiée :

```text
regulatory-accounting-data-framework
    |
    v
AccountingReferenceProvider
```

Le corpus CFA FRA ne doit pas devenir une seconde source réglementaire.

---

# 75. Migration des référentiels

```text
CFA FRA FrameworkAccount tables
    ->
deprecated as source

PyAccountingKit
    ->
reference adapter to regulatory-accounting-data-framework
```

---

# 76. Conservation historique

Les anciennes données CFA FRA peuvent rester :

```text
migration input / golden fixture
```

mais non :

```text
authoritative regulatory runtime
```

---

# 77. IFRS dans CFA FRA

Le projet CFA FRA contient une vision d'un référentiel IFRS.

PyAccountingKit ne doit pas déclarer ce contenu courant/autoritatif sans source réglementaire versionnée correspondante.

---

# 78. Dashboard

CFA FRA expose des KPI :

```text
Revenue
EBITDA
Net Income
CFO
Cash
Total Assets
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
dashboard UI -> DROP from core
analytical metric concepts -> GOLDEN / Financial Analysis
```

---

# 79. HTMX / Templates

CFA FRA utilise :

```text
Django Templates
HTMX
Chart.js
```

Ces choix restent dans :

```text
CFA FRA consumer application
```

et ne migrent pas vers PyAccountingKit.

---

# 80. Views

Le projet CFA FRA affirme déjà :

```text
views = HTTP / permissions / forms / rendering / HTMX
```

et interdit les calculs comptables dans les vues. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
KEEP PRINCIPLE
DROP IMPLEMENTATION FROM FRAMEWORK
```

---

# 81. Forms

```text
CONSUMER
```

---

# 82. URLs

```text
CONSUMER
```

---

# 83. Templates

```text
CONSUMER
```

---

# 84. RBAC

CFA FRA possède des rôles :

```text
ADMIN
ACCOUNTANT
REVIEWER
AUDITOR
READ_ONLY
```

et une matrice d'actions. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
RBAC implementation -> CONSUMER

Actor / SignOff / PermissionContext -> optional integration contracts
```

---

# 85. Pourquoi RBAC ne migre pas

PyAccountingKit ne doit pas décider :

```text
who is allowed to post in every application
```

Il doit pouvoir recevoir :

```text
actor
approval
signoff
```

depuis le runtime consommateur.

---

# 86. Exports

CFA FRA prévoit notamment :

```text
Journal
Grand Livre
Balance
Financial Statements
```

en formats CSV/XLSX et autres itérations. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
semantic export definitions -> EXTRACT where useful

Django/Excel implementation -> ADAPTER
```

---

# 87. Cible

```text
ReportRenderer
RegulatoryExporter
ArtifactStorePort
```

---

# 88. PostgreSQL

CFA FRA justifie PostgreSQL par :

```text
ACID
transactions
indexes
JSONB
CTE
window functions
materialized views
row-level locking
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
PostgreSQL remains Production reference backend

not domain dependency
```

---

# 89. SQL Window Ledger

Migration :

```text
GeneralLedgerQuery protocol
    |
    +--> Django/PostgreSQL implementation
    +--> SQLAlchemy/PostgreSQL implementation
    +--> InMemory reference implementation
```

---

# 90. Celery / Redis

CFA FRA propose Celery pour gros imports, exports et analytics.

Décision :

```text
DEFER / runtime integration
```

---

# 91. Pourquoi

PyAccountingKit définit :

```text
command semantics
checkpoint semantics
idempotence
```

mais ne doit pas imposer :

```text
Celery
Redis
```

---

# 92. Observabilité

CFA FRA envisage :

```text
Sentry
Prometheus
Grafana
OpenTelemetry
structured logging
```

 *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Décision :

```text
runtime adapters/integration
```

---

# 93. Excel migration history

Le plan CFA FRA indique que le développement doit être conduit par comparaison avec Excel et que les règles doivent être formalisées fonctionnalité par fonctionnalité. *(→ source : [CFA FRA — Conception et MVP](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md))*

Cette méthode devient le modèle de migration :

```text
CFA FRA implementation
    ->
formal rule
    ->
golden fixture
    ->
PyAccountingKit implementation
    ->
parity check
```

---

# 94. Golden source hierarchy

```text
Formal PyAccountingKit invariant
    |
    v
Current regulatory dataset
    |
    v
CFA FRA Django behavior
    |
    v
Excel historical scenario
```

---

# 95. Catégories de golden fixtures

```text
ACCOUNTING_CORE

POSTING

REVERSAL

FEC

LEDGER

TRIAL_BALANCE

FINANCIAL_STATEMENTS

CONTROLS

CLOSING

AUDIT

ANALYSIS
```

---

# 96. Golden accounting fixture

Minimal :

```text
balanced 2-line entry
```

Expected :

```text
VALIDATED
POSTED
same debit/credit totals
audit trace
```

---

# 97. Golden invalid entry

```text
unbalanced entry
```

Expected :

```text
posting rejected
```

---

# 98. Golden reversal

```text
POSTED original
```

Expected :

```text
original immutable
new inverse entry
reversal link
net effect = 0
```

---

# 99. Golden FEC

Fixtures :

```text
valid minimal FEC
missing fields
invalid date
negative amount
debit+credit
unbalanced entry
global unbalanced
duplicate candidate
```

---

# 100. Golden Ledger

Input :

```text
OPENING
NORMAL
ADJUSTING
REVERSAL
CLOSING
```

Expected :

```text
stable ordered movements
BEFORE_ADJUSTMENTS
ADJUSTED
POST_CLOSING
```

---

# 101. Golden Financial Statements

Use CFA FRA:

```text
Income Statement
Balance Sheet
Cash Flow
mapping coverage
drill-down
```

---

# 102. Golden Ratios

Use CFA FRA starter ratios:

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

# 103. Golden Closing

Expected :

```text
blocking controls prevent close
closing entries generated
period becomes CLOSED
posting subsequently rejected
```

---

# 104. Evidence fixture format

```text
tests/fixtures/cfa_fra/
|
+-- manifest.json
+-- accounting/
+-- posting/
+-- fec/
+-- ledger/
+-- statements/
+-- closing/
+-- analysis/
```

---

# 105. `CFAFRAGoldenFixtureManifest`

```text
fixture_id
fixture_version
source_document
source_scenario
source_behavior
input_checksum
expected_output_checksum
notes
```

---

# 106. No runtime CFA FRA import

Golden tests must not do :

```python
from cfa_fra.apps.accounting import PostingService
```

during normal test execution.

---

# 107. Why

Otherwise :

```text
PyAccountingKit tests depend on CFA FRA runtime
```

which would reverse the desired dependency.

---

# 108. Correct golden capture

```text
CFA FRA
    ->
capture normalized inputs/outputs
    ->
fixture
    ->
PyAccountingKit test
```

---

# 109. Extraction matrix - accounting

| CFA FRA component | Target | Decision | Notes |
|---|---|---|---|
| Organization | AccountingEntity | REWRITE | Generic entity scope |
| FiscalYear | FiscalYear | EXTRACT | Keep semantics |
| AccountingPeriod | AccountingPeriod | EXTRACT | State machine expanded |
| ChartOfAccounts | CompanyChartOfAccounts | REWRITE | Versioned |
| Account | CompanyAccount | REWRITE | Binding separated |
| Journal | Journal | EXTRACT | Framework-neutral |
| JournalEntry | JournalEntry | EXTRACT | Canonical aggregate |
| JournalLine | JournalEntryLine | EXTRACT | Decimal |
| EntryValidator | Domain rules | REWRITE | No Django |
| PostingService | PostEntry application service | REWRITE | UoW |
| ReversalService | ReverseEntry application service | REWRITE | Immutable original |

---

# 110. Extraction matrix - imports

| CFA FRA component | Target | Decision |
|---|---|---|
| FECImport | AccountingImportBatch | REWRITE |
| original_file | SourceArtifact | EXTRACT |
| SHA256 | SourceFingerprint | EXTRACT |
| FECRawLine | RawImportRecord | REWRITE |
| FECParser | FEC adapter parser | ADAPTER |
| FECValidator | adapter + generic controls | SPLIT |
| grouping logic | ImportEntryGroupingStrategy | REWRITE |
| raw_data | raw preservation | EXTRACT |
| duplicate warning | DuplicateDetectionStrategy | EXTRACT |
| direct posted history | TRUSTED_POSTED_HISTORY_IMPORT | REWRITE |
| transaction.atomic | Django UoW adapter | ADAPTER |
| select_for_update | Django locking adapter | ADAPTER |

---

# 111. Extraction matrix - reporting

| CFA FRA component | Target | Decision |
|---|---|---|
| Journal report | LedgerAPI / JournalQuery | REWRITE |
| General Ledger | GeneralLedgerQuery | REWRITE |
| Trial Balance | TrialBalanceQuery | REWRITE |
| StatementDefinition | FinancialStatementDefinition | EXTRACT |
| StatementLine | StatementLineDefinition | EXTRACT |
| StatementAccountMapping | StatementAccountMapping | EXTRACT |
| IncomeStatementService | FinancialStatementEngine | REWRITE |
| BalanceSheetService | FinancialStatementEngine | REWRITE |
| CashFlowStatementService | CashFlowDefinition/Engine | REWRITE |
| mapping coverage | StatementMappingCoverage | EXTRACT |
| drill-down | StatementDrilldownQuery | EXTRACT |

---

# 112. Extraction matrix - controls/closing/audit

| CFA FRA component | Target | Decision |
|---|---|---|
| ControlResult | ControlResult / Finding | REWRITE |
| control codes | ControlDefinition seeds | EXTRACT |
| AuditEvent | AuditEvent | REWRITE |
| audit action list | starter vocabulary | GOLDEN |
| closing workflow | Closing application service | EXTRACT |
| close blockers | ControlGate | EXTRACT |
| period status | AccountingPeriod state | EXTRACT |
| Django audit middleware/context | Audit adapter | ADAPTER |

---

# 113. Extraction matrix - references

| CFA FRA component | Target | Decision |
|---|---|---|
| AccountingFramework | ReferenceStandard | REPLACE |
| FrameworkVersion | standard edition/snapshot | REPLACE |
| FrameworkAccount | ReferenceAccount | REPLACE |
| SYSCOHADA seed | regulatory provider | DROP AS AUTHORITY |
| IFRS seed | regulatory provider | DROP AS AUTHORITY |
| AccountMapping | RegulatoryAccountBinding | REWRITE |
| manual mapping UI | CFA FRA consumer | CONSUMER |

---

# 114. Extraction matrix - analytics

| CFA FRA component | Target | Decision |
|---|---|---|
| Dashboard KPI | FinancialIndicatorDefinition | SELECTIVE EXTRACT |
| Ratios | FinancialRatioDefinition | EXTRACT |
| N/N-1 | Trend/Comparison | EXTRACT |
| Chart.js | none | DROP |
| HTMX dashboard | CFA FRA consumer | CONSUMER |
| KPI rendering | AnalysisRenderer app layer | ADAPTER/CONSUMER |

---

# 115. Extraction matrix - infrastructure

| CFA FRA | Target | Decision |
|---|---|---|
| Django models | Django persistence adapter | REWRITE |
| Django services | Application services | REWRITE |
| selectors | Query ports + adapters | REWRITE |
| PostgreSQL | Production persistence backend | ADAPTER |
| transaction.atomic | Django UoW | ADAPTER |
| select_for_update | lock implementation | ADAPTER |
| Window/Sum | SQL read adapter | ADAPTER |
| Redis | optional runtime | DEFER |
| Celery | optional runtime | DEFER |
| HTMX | consumer UI | DROP from core |
| templates | consumer UI | DROP from core |

---

# 116. CFA FRA module disposition

```text
apps/accounting
    -> migrate semantics

apps/imports
    -> split generic imports + FEC adapter

apps/reporting
    -> query/report APIs

apps/financial_statements
    -> statement engine

apps/controls
    -> control bounded context

apps/closing
    -> closing bounded context

apps/referentials
    -> replace by regulatory provider

apps/analytics
    -> financial analysis selective extraction

apps/audit
    -> audit bounded context

apps/exports
    -> renderers/exporters

apps/users
apps/organizations
templates
static
    -> remain consumer application
```

---

# 117. Target dependency direction

Après migration :

```text
CFA FRA Django Application
        |
        v
PyAccountingKit Public API
        |
        v
Application Services
        |
        v
Domain
        |
        v
Ports
        ^
        |
Django/PostgreSQL Adapters
```

---

# 118. Interdit

```text
PyAccountingKit Domain
    ->
CFA FRA
```

---

# 119. Interdit

```text
PyAccountingKit Domain
    ->
Django models
```

---

# 120. Interdit

```text
PyAccountingKit
    ->
CFA FRA URL/view/forms
```

---

# 121. Migration strategy

La migration doit être incrémentale.

Pas :

```text
big-bang rewrite
```

---

# 122. Phase MIG-00 - Freeze CFA FRA baseline

Objectif :

```text
capture current executable behavior
```

Livrables :

```text
CFA_FRA_BASELINE_MANIFEST.md
CFA_FRA_GOLDEN_SCENARIO_INVENTORY.md
baseline git commit
test results
fixture checksums
```

---

# 123. MIG-00 gate

```text
CFA FRA current test suite green
```

---

# 124. Phase MIG-01 - Inventory

Inventorier :

```text
models
services
selectors
validators
controls
commands
migrations
tests
fixtures
```

---

# 125. MIG-01 output

```text
CFA_FRA_COMPONENT_INVENTORY.csv/md
```

Fields :

```text
component
module
responsibility
dependencies
decision
target
risk
golden scenario
```

---

# 126. Phase MIG-02 - Capture golden behavior

Capturer avant réécriture :

```text
posting
reversal
FEC
ledger
balance
statements
closing
audit
```

---

# 127. MIG-02 rule

Chaque behavior critique doit avoir :

```text
fixture input
expected output
source evidence
checksum
```

---

# 128. Phase MIG-03 - Extract pure domain primitives

Ordre :

```text
Money
IDs
FiscalYear
AccountingPeriod
CompanyAccount
Journal
JournalEntry
JournalEntryLine
```

---

# 129. MIG-03 no Django

Gate :

```text
import pyaccountingkit.domain
```

must succeed without Django.

---

# 130. Phase MIG-04 - Posting/Reversal parity

Implement :

```text
EntryValidator
PostEntry
ReverseEntry
```

Run :

```text
CFA FRA golden parity
```

---

# 131. MIG-04 exit criteria

```text
balanced behavior parity

immutability parity

closed-period parity

reversal parity
```

---

# 132. Phase MIG-05 - Django persistence adapter

Rewrite CFA FRA persistence knowledge into :

```text
Django repositories

DjangoUnitOfWork

Django query adapters
```

---

# 133. MIG-05

Use as reference :

```text
transaction.atomic
select_for_update
ORM constraints
```

but obey PyAccountingKit ports.

---

# 134. Phase MIG-06 - FEC extraction

Implement :

```text
generic AccountingImportBatch

FEC adapter

raw storage

mapping

validation

idempotence

trusted history mode
```

---

# 135. MIG-06 parity

Compare CFA FRA Sprint 4 :

```text
same file

same valid line count

same error classification where semantics intentionally retained

same entry totals

same imported entry grouping where configured
```

---

# 136. Intentional FEC divergence

Document cases where PyAccountingKit intentionally generalizes :

```text
JAN special handling

JOD classification

source key policy

closed-period historical import
```

---

# 137. Phase MIG-07 - Ledger

Implement :

```text
JournalQuery

GeneralLedgerQuery

TrialBalanceQuery
```

---

# 138. MIG-07 golden parity

Compare :

```text
movement order
opening balance
running balance
BEFORE_ADJUSTMENTS
ADJUSTED
POST_CLOSING
```

---

# 139. Phase MIG-08 - Statements

Implement :

```text
StatementDefinition
StatementMappingSet
FinancialStatementEngine
drill-down
```

---

# 140. MIG-08 parity

Compare :

```text
Income Statement
Balance Sheet
Cash Flow
mapping coverage
```

---

# 141. Phase MIG-09 - Controls/Audit

Implement :

```text
ControlDefinition
ControlRun
ControlGate
AuditEvent
```

---

# 142. Phase MIG-10 - Closing

Implement :

```text
ClosingRun
adjustments
closing entries
period transition
opening balances
```

---

# 143. Phase MIG-11 - Reference replacement

Remove CFA FRA's regulatory authority dependency.

Replace :

```text
local SYSCOHADA/IFRS tables as authority
```

with :

```text
AccountingReferenceProvider
```

---

# 144. MIG-11 important

CFA FRA may keep local cached/projection tables if needed for UI.

But source of truth becomes :

```text
regulatory-accounting-data-framework
```

---

# 145. Phase MIG-12 - Consumer conversion

Refactor CFA FRA Django services :

Old :

```python
post_entry(...)
```

New :

```python
accounting.entries.post(...)
```

---

# 146. CFA FRA views after migration

Views keep :

```text
HTTP
permissions
forms
HTMX
rendering
```

but delegate accounting to PyAccountingKit.

---

# 147. Phase MIG-13 - Remove duplicate engine

Only after parity is proven.

Delete/deprecate duplicate logic in :

```text
CFA FRA accounting services
FEC normalization services
statement calculation services
control implementations
```

---

# 148. MIG-13 gate

No deletion until :

```text
golden parity

production adapter qualification

consumer smoke tests
```

---

# 149. Strangler pattern

Recommended migration pattern :

```text
Old CFA FRA Service
        |
        +--> legacy implementation
        |
        +--> PyAccountingKit implementation
```

during transition.

---

# 150. Dual-run

For selected read operations :

```text
legacy result

vs

PyAccountingKit result
```

compare without changing user output.

---

# 151. Dual-run candidates

Safe :

```text
trial balance
statements
ratios
controls
```

---

# 152. Dual-write warning

Avoid dual-write on :

```text
posting
reversal
closing
```

because double side effects are dangerous.

---

# 153. Mutation migration

Use feature switch :

```text
legacy mutation
OR
PyAccountingKit mutation
```

never both.

---

# 154. `CFAFRACompatibilityAdapter`

Temporary facade possible :

```text
CFAFRACompatibilityAdapter
```

mapping old service signatures to PyAccountingKit public API.

---

# 155. Example

```python
def post_entry(*, entry_id, user):
    return accounting.entries.post(
        entry_id=entry_id,
        context=to_command_context(user),
    )
```

---

# 156. Adapter lifetime

Temporary.

Remove after consumer code migrates.

---

# 157. Data migration strategy

Existing CFA FRA database may contain :

```text
accounts
journals
entries
lines
FEC imports
raw lines
mappings
audit
```

---

# 158. Data migration principle

Do not rewrite posted history unnecessarily.

---

# 159. Options

### Option A - Existing DB tables remain

PyAccountingKit Django adapter maps directly to current tables initially.

### Option B - New PyAccountingKit tables

Run controlled migration/copy.

---

# 160. Recommended first step

Prefer :

```text
adapter over existing CFA FRA schema
```

where model compatibility allows.

This reduces migration risk.

---

# 161. Then evolve schema

Use :

```text
expand / contract
```

toward canonical adapter schema.

---

# 162. Entity IDs

Preserve CFA FRA IDs when possible through migration mapping.

---

# 163. JournalEntry identity

Historical JournalEntry IDs should remain traceable.

---

# 164. `LegacyIdentityMap`

Possible migration artifact :

```text
legacy_type
legacy_id
target_type
target_id
```

---

# 165. Account migration

Need separate :

```text
CompanyAccount identity

account code

reference binding
```

---

# 166. FrameworkAccount migration

Do not copy a CFA FRA `FrameworkAccount` as authoritative reference.

Instead :

```text
resolve to current ReferenceAccount
```

when unambiguous and reviewed.

---

# 167. Unresolved reference mapping

Remain :

```text
REVIEW_REQUIRED
```

---

# 168. FEC batch migration

Existing :

```text
FECImport
```

can map to :

```text
AccountingImportBatch
```

with original checksum/provenance preserved.

---

# 169. Raw line migration

Existing :

```text
FECRawLine
```

maps to :

```text
RawImportRecord
```

or remains external raw-store reference.

---

# 170. Reversal links

Preserve :

```text
reversal_of
```

exactly.

---

# 171. Closing history

Preserve :

```text
period status
close events
closing entry references
```

---

# 172. Audit migration

Preserve legacy audit as :

```text
LegacyAuditEvent
```

or normalized `AuditEvent` with source :

```text
CFA_FRA_LEGACY
```

---

# 173. Do not fabricate missing audit context

If old event has no correlation ID :

```text
None
```

not generated retrospective value.

---

# 174. Golden oracle vs source of truth

Important distinction :

```text
CFA FRA expected output
    can prove behavior parity

but

does not override a formalized corrected rule
```

---

# 175. Intentional divergence protocol

If PyAccountingKit differs intentionally :

```text
create ADR

document old CFA FRA behavior

document new behavior

add migration impact

update golden fixture
```

---

# 176. Divergence categories

```text
BUG_FIX

GENERALIZATION

REGULATORY_CORRECTION

PORTABILITY_CHANGE

SAFETY_HARDENING

API_REDESIGN
```

---

# 177. Example intentional divergence - FEC trusted history

Old :

```text
FEC import creates POSTED directly
```

New :

```text
TRUSTED_POSTED_HISTORY_IMPORT
```

This is :

```text
GENERALIZATION + SAFETY_HARDENING
```

---

# 178. Example intentional divergence - JOD

Old :

```text
JOD -> ADJUSTING
```

New :

```text
source policy decides
```

This is :

```text
GENERALIZATION
```

---

# 179. Example intentional divergence - reference data

Old :

```text
local FrameworkAccount authority
```

New :

```text
regulatory provider snapshot
```

This is :

```text
ARCHITECTURE / REGULATORY_SAFETY
```

---

# 180. Tests after migration

Test layers :

```text
PyAccountingKit unit/property
        +
PyAccountingKit adapter contract
        +
CFA FRA golden parity
        +
CFA FRA consumer integration
```

---

# 181. `tests/golden/cfa_fra`

Target :

```text
tests/golden/cfa_fra/
├── accounting/
├── posting/
├── reversal/
├── imports/
├── ledger/
├── statements/
├── controls/
├── closing/
└── analysis/
```

---

# 182. Consumer integration tests

CFA FRA retains :

```text
Django view tests
HTMX tests
permission tests
forms
```

They should validate the application, not PyAccountingKit internals.

---

# 183. Django adapter tests

PyAccountingKit owns :

```text
repository contract
UoW contract
locking/concurrency
query semantics
```

---

# 184. Responsibility after migration

| Responsibility | Owner |
|---|---|
| Accounting invariants | PyAccountingKit |
| Posting/Reversal | PyAccountingKit |
| Ledger/Balance | PyAccountingKit |
| FEC core pipeline | PyAccountingKit |
| FEC parsing | PyAccountingKit adapter |
| Regulatory data | regulatory-accounting-data-framework |
| Django UI | CFA FRA |
| RBAC | CFA FRA |
| HTMX | CFA FRA |
| PostgreSQL persistence impl | PyAccountingKit adapter |
| Consumer orchestration | CFA FRA |
| Golden historical scenarios | shared test assets |

---

# 185. API mapping old -> new

| CFA FRA concept | PyAccountingKit API |
|---|---|
| `create_entry` | `accounting.entries.create()` |
| `validate_entry` | `accounting.entries.validate()` |
| `post_entry` | `accounting.entries.post()` |
| `reverse_entry` | `accounting.entries.reverse()` |
| journal selector | `accounting.ledger.journal()` |
| ledger selector | `accounting.ledger.general_ledger()` |
| balance selector | `accounting.ledger.trial_balance()` |
| FEC upload/import | `accounting.imports.*` |
| statement services | `accounting.statements.*` |
| regulatory outputs | `accounting.reporting.*` |
| analytics ratios | `accounting.analysis.*` |
| close period | `accounting.closing.close()` |

---

# 186. Migration risk register

## RISK-CFA-001 - Copier Django dans le domaine

Réponse :

```text
ports/adapters boundary
```

---

## RISK-CFA-002 - Perdre les règles lors de la réécriture

Réponse :

```text
golden capture before refactor
```

---

## RISK-CFA-003 - Transformer une convention MVP en invariant universel

Exemples :

```text
JOD -> ADJUSTING
REV- prefix
fixed FEC grouping
```

Réponse :

```text
explicit policy
```

---

## RISK-CFA-004 - Dupliquer les référentiels

Réponse :

```text
replace local authority with AccountingReferenceProvider
```

---

## RISK-CFA-005 - Double posting pendant dual-run

Réponse :

```text
never dual-write accounting mutations
```

---

## RISK-CFA-006 - Modifier les IDs historiques

Réponse :

```text
LegacyIdentityMap / preserve IDs
```

---

## RISK-CFA-007 - Perdre raw FEC provenance

Réponse :

```text
raw artifact + checksums + line refs
```

---

## RISK-CFA-008 - Perdre audit history

Réponse :

```text
legacy audit migration without invention
```

---

## RISK-CFA-009 - Résultats reporting divergents

Réponse :

```text
golden statements + drill-down parity
```

---

## RISK-CFA-010 - Masquer une divergence légitime

Réponse :

```text
Intentional Divergence ADR
```

---

# 187. Definition of extraction complete

L'extraction CFA FRA est terminée lorsque :

```text
no accounting invariant exists only in CFA FRA code

all critical behaviors have PyAccountingKit tests

all golden scenarios are captured

CFA FRA can consume PyAccountingKit public API

CFA FRA Django-specific code no longer owns accounting semantics
```

---

# 188. Definition of migration complete

Migration complète lorsque :

```text
CFA FRA mutation services delegate to PyAccountingKit

CFA FRA read/reporting services delegate to PyAccountingKit

regulatory references come from the reference provider

Django adapter is production-qualified

golden parity gates are green

legacy accounting engine is removed/deactivated

historical data remains traceable
```

---

# 189. ADRs

| ID | Décision |
|---|---|
| ADR-CFA-001 | CFA FRA est une référence fonctionnelle, pas une dépendance runtime |
| ADR-CFA-002 | Les comportements critiques CFA FRA deviennent golden fixtures |
| ADR-CFA-003 | Les modèles Django ne sont pas copiés dans le domain |
| ADR-CFA-004 | `Organization` est généralisé en `AccountingEntity` |
| ADR-CFA-005 | `Account.framework_account` est remplacé par un binding explicite |
| ADR-CFA-006 | Le workflow DRAFT -> VALIDATED -> POSTED -> REVERSED est conservé |
| ADR-CFA-007 | Les invariants de validation CFA FRA sont extraits dans le domain |
| ADR-CFA-008 | `transaction.atomic` reste un détail du Django adapter |
| ADR-CFA-009 | `select_for_update` reste un détail du locking adapter |
| ADR-CFA-010 | Le Reversal comportemental est conservé, la convention de numéro est policy-driven |
| ADR-CFA-011 | `signed_balance = debit-credit` reste une convention de projection |
| ADR-CFA-012 | Les variantes de Trial Balance CFA FRA sont conservées |
| ADR-CFA-013 | `JOD -> ADJUSTING` n'est pas un invariant universel |
| ADR-CFA-014 | Le pipeline FEC est généralisé en Accounting Imports |
| ADR-CFA-015 | Les 18 colonnes FEC restent dans l'adapter FEC |
| ADR-CFA-016 | Les raw FEC lines restent auditables et reprocessables |
| ADR-CFA-017 | Le duplicate hash FEC reste un signal, pas une preuve économique |
| ADR-CFA-018 | Le direct POSTED FEC est remplacé par `TRUSTED_POSTED_HISTORY_IMPORT` |
| ADR-CFA-019 | Le rollback complet FEC est un comportement à préserver |
| ADR-CFA-020 | Le Ledger SQL est réimplémenté derrière des query ports |
| ADR-CFA-021 | Le Statement Engine CFA FRA est réécrit framework-neutral |
| ADR-CFA-022 | Statement mapping et Regulatory binding restent séparés |
| ADR-CFA-023 | Les diagnostics de mapping CFA FRA deviennent des controls/coverage metrics |
| ADR-CFA-024 | Le drill-down financier est conservé de bout en bout |
| ADR-CFA-025 | Les ratios Sprint 6 alimentent les golden Financial Analysis |
| ADR-CFA-026 | Le reporting réglementaire reste distinct des états financiers génériques |
| ADR-CFA-027 | Les controls CFA FRA deviennent des ControlDefinitions versionnées |
| ADR-CFA-028 | L'AuditEvent est extrait mais les champs HTTP restent contextuels |
| ADR-CFA-029 | Le workflow Closing CFA FRA est conservé et généralisé |
| ADR-CFA-030 | Les référentiels locaux CFA FRA cessent d'être source de vérité |
| ADR-CFA-031 | `regulatory-accounting-data-framework` devient la source réglementaire |
| ADR-CFA-032 | HTMX/templates/forms restent dans CFA FRA consumer |
| ADR-CFA-033 | RBAC reste une responsabilité de l'application consommatrice |
| ADR-CFA-034 | PostgreSQL reste un backend de référence, pas une dépendance du domain |
| ADR-CFA-035 | Celery/Redis restent optionnels |
| ADR-CFA-036 | La migration suit un strangler pattern |
| ADR-CFA-037 | Les mutations comptables ne sont jamais dual-written |
| ADR-CFA-038 | Toute divergence intentionnelle est documentée |
| ADR-CFA-039 | Les identités historiques restent traçables |
| ADR-CFA-040 | La suppression du moteur legacy n'intervient qu'après parity qualification |

---

# 190. Critères d'acceptation P1.7

```text
[ ] rôle de CFA FRA comme oracle défini

[ ] taxonomy EXTRACT/REWRITE/ADAPTER/GOLDEN définie

[ ] Accounting Core mapping défini

[ ] Organization -> AccountingEntity défini

[ ] Account -> CompanyAccount défini

[ ] framework_account migration définie

[ ] PostingService migration définie

[ ] transaction.atomic déplacé vers adapter

[ ] ReversalService migration définie

[ ] Ledger query migration définie

[ ] signed balance convention correctement limitée

[ ] Trial Balance variants migrées

[ ] JOD convention non universalisée

[ ] FECImport -> AccountingImportBatch défini

[ ] FECRawLine -> RawImportRecord défini

[ ] raw preservation conservée

[ ] FEC grouping traité comme strategy

[ ] duplicate warning conservé comme non-certitude

[ ] trusted posted history mapping défini

[ ] rollback complet FEC conservé

[ ] Statement Engine migration définie

[ ] StatementAccountMapping conservé séparément du regulatory binding

[ ] drill-down migration défini

[ ] ratios Sprint 6 capturés

[ ] Controls migration définie

[ ] Audit migration définie

[ ] Closing migration définie

[ ] local reference authority remplacée

[ ] HTMX/UI explicitement hors core

[ ] RBAC hors core

[ ] PostgreSQL specifics déplacés vers adapter

[ ] golden fixture architecture définie

[ ] migration phases MIG-00 -> MIG-13 définies

[ ] strangler strategy définie

[ ] no dual-write rule définie

[ ] legacy identity migration définie

[ ] intentional divergence protocol défini

[ ] completion gates définis
```

---

# 191. Ordre d'implémentation recommandé

```text
MIG-00  Freeze CFA FRA baseline

MIG-01  Component inventory

MIG-02  Capture golden behavior

MIG-03  Extract domain primitives

MIG-04  Posting / Reversal parity

MIG-05  Django persistence adapter

MIG-06  FEC extraction

MIG-07  Ledger / Trial Balance

MIG-08  Financial Statements

MIG-09  Controls / Audit

MIG-10  Closing

MIG-11  Regulatory reference replacement

MIG-12  CFA FRA consumer conversion

MIG-13  Legacy engine retirement
```

---

# 192. Premier lot concret recommandé

Avant tout déplacement de code, produire :

```text
01_CFA_FRA_COMPONENT_INVENTORY.md

02_CFA_FRA_GOLDEN_SCENARIO_INVENTORY.md

03_CFA_FRA_BEHAVIORAL_BASELINE.md
```

Puis implémenter :

```text
PyAccountingKit Core
    Money
    FiscalYear
    AccountingPeriod
    CompanyAccount
    Journal
    JournalEntry
    JournalEntryLine

Posting
    ValidateEntry
    PostEntry
    ReverseEntry
```

---

# 193. Premier gate de migration

Le premier gate réellement significatif est :

```text
CFA FRA:
    create
    validate
    post
    reverse

PyAccountingKit:
    create
    validate
    post
    reverse

Expected:
    same accounting semantics
```

---

# 194. Gate FEC

```text
same source fixture

CFA FRA
vs
PyAccountingKit FEC adapter
```

Comparer :

```text
source lines

validation findings

normalized groups

debit total

credit total

entry count

line count

lineage
```

---

# 195. Gate Ledger

Comparer :

```text
Journal ordering

General Ledger

opening balance

running balance

Trial Balance variants
```

---

# 196. Gate Statements

Comparer :

```text
P&L

Balance Sheet

Cash Flow

mapping coverage

drill-down
```

---

# 197. Gate Closing

Comparer :

```text
pre-close blockers

closing entry generation

post-closing balance

period status

opening balances
```

---

# 198. Gate Consumer

CFA FRA UI doit continuer à réussir :

```text
login

organization context

FEC import

journal

ledger

balance

financial statements

controls

closing

exports
```

même lorsque le calcul est délégué à PyAccountingKit.

---

# 199. Matrice finale - copier ou non

| Élément CFA FRA | Copier le code ? | Copier la sémantique ? |
|---|---:|---:|
| JournalEntry workflow | non | **oui** |
| PostingService Django | non | **oui** |
| Reversal behavior | non | **oui** |
| transaction.atomic | non core | **oui, atomicity** |
| select_for_update | non core | **oui, locking need** |
| FEC parser | adapter only | **oui, format semantics** |
| FECRawLine | non | **oui, raw preservation** |
| Ledger SQL Window | adapter only | **oui, result semantics** |
| Statement Engine | non | **oui** |
| Control catalog | non | **oui** |
| Closing workflow | non | **oui** |
| FrameworkAccount data | **non** | partiellement |
| HTMX/UI | **non** | non |
| RBAC roles | **non** | app-specific |
| Excel/Django scenarios | fixture | **oui, oracle** |

---

# 200. Conclusion

La migration CFA FRA vers PyAccountingKit n'est pas une extraction de fichiers Python.

Elle est une extraction de **contrats comportementaux**.

La cible est :

```text
CFA FRA
    |
    +--> functional evidence
    +--> golden behavior
    +--> Django adapter knowledge
    +--> consumer application
    |
    v
PyAccountingKit
    |
    +--> domain
    +--> application
    +--> ports
    +--> adapters
    +--> public API
```

Les règles finales sont :

```text
Keep the behavior

Rewrite the implementation

Preserve the evidence

Move framework-specific code to adapters

Replace local regulatory authority

Do not universalize MVP conventions

Do not dual-write accounting mutations

Do not delete the legacy engine before parity

Make CFA FRA a consumer of PyAccountingKit

Use CFA FRA as a golden oracle, never as a runtime dependency
```

---

**Prochain document recommandé :**

```text
19_PYACCOUNTINGKIT_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX.md
```


---

## Sources et références documentaires du projet

- 🏗️ [CFA FRA Django MVP Sprint 7 — Référence fonctionnelle](../../../resources/cfa_fra_django_mvp_sprint_7/)
- 📄 [CFA FRA — Document de conception](../../../resources/cfa_fra_django_mvp_sprint_7/docs/CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md)

---

## Plans d'implémentation principaux

Ce document est couvert par les plans suivants :

- [PLAN-06 — Migration CFA FRA & Hardening (1.0.0)](../../plans/PLAN-06_MIGRATION_CFA_FRA_HARDENING_1.0.0.md)
