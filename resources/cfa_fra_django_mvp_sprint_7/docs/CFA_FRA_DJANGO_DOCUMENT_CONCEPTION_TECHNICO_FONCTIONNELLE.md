# CFA FRA — Transformation du modèle Excel en application Django

## Document de conception technico-fonctionnelle

**Projet :** CFA FRA — Accounting & Financial Reporting Engine  
**Source fonctionnelle :** `CFA_FRA_Cycle_Comptable_FEC_2025_Petit_Dossier_Dashboard_Pro_Annexes_IFRS_OHADA.xlsx`  
**Cible :** application web Django / PostgreSQL avec API REST, moteur comptable et reporting financier  
**Version :** 1.0  
**Date :** 25 août 2026

---

# 1. Objet du document

Ce document décrit la transformation du classeur Excel CFA FRA en une application Django industrialisable.

L'objectif n'est pas de reproduire Excel feuille par feuille ou cellule par cellule. Le classeur doit être considéré comme un **prototype fonctionnel du moteur comptable**. L'application cible doit reprendre ses concepts métier, ses règles de gestion, ses contrôles et ses états financiers dans une architecture logicielle durable.

La cible doit pouvoir :

- importer un FEC ;
- gérer plusieurs entités comptables ;
- gérer plusieurs exercices et périodes ;
- gérer plusieurs référentiels comptables ;
- enregistrer des écritures en partie double ;
- produire journal, grand livre et balances ;
- générer compte de résultat, bilan et tableau de flux de trésorerie ;
- gérer ajustements, clôture et réouverture ;
- exécuter des contrôles comptables ;
- fournir un audit trail complet ;
- rapprocher les comptes de l'entreprise avec SYSCOHADA et IFRS ;
- exposer les données via API ;
- alimenter un dashboard professionnel.

---

# 2. Vision fonctionnelle

```text
FEC / Transactions
        |
        v
Plan comptable de l'entité
        |
        v
Écritures comptables
        |
        v
Journal
        |
        v
Grand livre
        |
        v
Balance avant ajustements
        |
        v
Ajustements
        |
        v
Balance ajustée
        |
        +----------------+----------------+
        |                |                |
        v                v                v
   Compte de           Bilan          Flux de
    résultat                          trésorerie
        |                |                |
        +----------------+----------------+
                         |
                         v
                      Clôture
                         |
                         v
               Balance post-clôture
                         |
                         v
                     Analytics
                         |
                         v
                     Dashboard
```

Le produit devient ainsi un **Accounting Engine** plutôt qu'une simple transposition d'Excel.

---

# 3. Principe d'architecture fondamental

## 3.1 Ne pas faire « une feuille Excel = une table Django »

Cette approche serait une erreur de modélisation.

Le grand livre, les balances, le bilan, le compte de résultat ou les flux de trésorerie ne doivent pas être considérés comme des sources de données indépendantes. Ils sont principalement des **projections calculées** à partir d'une source comptable canonique.

Le cœur du domaine repose sur :

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

Le reste est produit par des services, selectors, vues analytiques ou matérialisations destinées à la performance.

---

# 4. Correspondance Excel → Django

| Feuille Excel | Cible Django |
|---|---|
| `00_Accueil` | Dashboard / Home |
| `01_Parametres` | `organizations`, `accounting_settings` |
| `02_Plan_Comptable` | `ChartOfAccounts`, `Account` |
| `03_Entetes_Ecritures` | `JournalEntry` |
| `04_Journal` | `JournalEntry` + `JournalLine` |
| `05_Grand_Livre` | `GeneralLedgerService` |
| `06_Balance_Avant_Ajust` | `TrialBalanceService` |
| `07_Balance_Ajustee` | `TrialBalanceService` avec filtres |
| `08_Resultat_2025` | `IncomeStatementService` |
| `09_Bilan_2025` | `BalanceSheetService` |
| `10_Flux_2025` | `CashFlowStatementService` |
| `11_Cloture_2025` | `ClosingService` |
| `12_Controles` | `AccountingValidationService` |
| `13_Dashboard` | `analytics` |
| `14_Scenario_FEC` | `imports`, `scenarios` |
| `15_FEC_Brut` | `FECImport`, `FECRawLine` |
| `16_Annexe_Comptes_IFRS` | `AccountingFramework`, `FrameworkAccount` |
| `17_Annexe_Plan_OHADA` | `AccountingFramework`, `FrameworkAccount` |
| `99_Synthese_Comptes` | reporting / vues analytiques |

---

# 5. Architecture technique cible

## 5.1 Stack recommandée

```text
Python 3.13
Django 5.x
Django REST Framework
PostgreSQL 17
Redis
Celery
Docker
```

Qualité et tests :

```text
pytest
pytest-django
ruff
mypy
django-stubs
coverage
```

Documentation API :

```text
drf-spectacular
OpenAPI
```

Frontend :

```text
Phase 1 : Django Templates + HTMX
Phase 2 : React + TypeScript si les besoins analytiques l'exigent
```

---

# 6. Découpage des applications Django

```text
backend/
|
+-- config/
|
+-- apps/
|   |
|   +-- users/
|   +-- organizations/
|   +-- accounting/
|   +-- referentials/
|   +-- imports/
|   +-- reporting/
|   +-- closing/
|   +-- controls/
|   +-- analytics/
|   +-- audit/
|   +-- exports/
|   +-- scenarios/
|
+-- tests/
|
+-- manage.py
```

---

# 7. Responsabilités des modules

## 7.1 `users`

- utilisateurs ;
- authentification ;
- profils ;
- rôles ;
- permissions.

Rôles typiques :

```text
ADMIN
ACCOUNTANT
REVIEWER
AUDITOR
ANALYST
READ_ONLY
```

## 7.2 `organizations`

- entités juridiques ;
- devises ;
- exercices ;
- périodes ;
- paramètres comptables.

Entités :

```text
Organization
FiscalYear
AccountingPeriod
AccountingSettings
```

## 7.3 `accounting`

Cœur du moteur :

```text
ChartOfAccounts
Account
Journal
JournalEntry
JournalLine
Counterparty
CostCenter
```

Services :

```text
create_entry
validate_entry
post_entry
reverse_entry
lock_period
unlock_period
```

## 7.4 `imports`

- upload FEC ;
- parsing ;
- stockage du fichier original ;
- normalisation ;
- contrôle ;
- création des écritures ;
- rapport d'import.

Entités :

```text
FECImport
FECRawLine
ImportError
ImportMapping
ImportReport
```

## 7.5 `referentials`

- SYSCOHADA ;
- IFRS ;
- versions ;
- comptes standard ;
- mappings ;
- définition des états financiers.

Entités :

```text
AccountingFramework
FrameworkVersion
FrameworkAccount
FrameworkAccountRelation
AccountMapping
StatementDefinition
StatementLine
```

## 7.6 `reporting`

Services :

```text
GeneralLedgerService
TrialBalanceService
IncomeStatementService
BalanceSheetService
CashFlowStatementService
RatioService
```

## 7.7 `closing`

- ajustements ;
- clôture de période ;
- clôture annuelle ;
- report à nouveau ;
- réouverture.

## 7.8 `controls`

- partie double ;
- conformité structurelle ;
- contrôles FEC ;
- cohérence bilan ;
- réconciliation cash-flow ;
- qualité des données.

## 7.9 `analytics`

- KPI ;
- dashboard ;
- tendances ;
- structure des coûts ;
- concentration clients/fournisseurs ;
- alertes.

## 7.10 `audit`

- journal d'audit ;
- historique ;
- traçabilité complète des mutations.

---

# 8. Modèle conceptuel de données

```text
Organization
|
+-- FiscalYear
|   |
|   +-- AccountingPeriod
|
+-- ChartOfAccounts
|   |
|   +-- Account
|
+-- Journal
|   |
|   +-- JournalEntry
|       |
|       +-- JournalLine
|
+-- FECImport
|   |
|   +-- FECRawLine
|
+-- AccountingSettings
```

Référentiels :

```text
AccountingFramework
|
+-- FrameworkVersion
    |
    +-- FrameworkAccount
        |
        +-- AccountMapping
```

---

# 9. Modèles Django principaux

## 9.1 `Organization`

```python
class Organization(models.Model):
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    base_currency = models.CharField(max_length=3)
    country_code = models.CharField(max_length=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## 9.2 `FiscalYear`

```python
class FiscalYear(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="fiscal_years",
    )
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20)
```

Statuts :

```text
OPEN
CLOSING
CLOSED
```

## 9.3 `AccountingPeriod`

```python
class AccountingPeriod(models.Model):
    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.CASCADE,
        related_name="periods",
    )
    period_number = models.PositiveSmallIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, default="OPEN")
```

## 9.4 `ChartOfAccounts`

```python
class ChartOfAccounts(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    is_default = models.BooleanField(default=False)
```

## 9.5 `Account`

```python
class Account(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    chart = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.CASCADE,
        related_name="accounts",
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=30)
    normal_balance = models.CharField(max_length=10)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    framework_account = models.ForeignKey(
        "referentials.FrameworkAccount",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    is_active = models.BooleanField(default=True)
```

Contrainte :

```text
UNIQUE (organization, chart, code)
```

## 9.6 `Journal`

```python
class Journal(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    journal_type = models.CharField(max_length=30)
```

Types :

```text
SALES
PURCHASE
BANK
CASH
PAYROLL
TAX
GENERAL
OPENING
```

## 9.7 `JournalEntry`

```python
class JournalEntry(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    journal = models.ForeignKey(Journal, on_delete=models.PROTECT)
    period = models.ForeignKey(AccountingPeriod, on_delete=models.PROTECT)

    entry_number = models.CharField(max_length=100)
    posting_date = models.DateField()
    description = models.TextField()

    source = models.CharField(max_length=50)
    source_reference = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=20, default="DRAFT")

    created_at = models.DateTimeField(auto_now_add=True)
    posted_at = models.DateTimeField(null=True, blank=True)
```

Statuts :

```text
DRAFT
VALIDATED
POSTED
REVERSED
```

## 9.8 `JournalLine`

`JournalLine` est l'unité atomique du système comptable.

```python
class JournalLine(models.Model):
    entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    account = models.ForeignKey(Account, on_delete=models.PROTECT)

    debit = models.DecimalField(
        max_digits=24,
        decimal_places=4,
        default=0,
    )
    credit = models.DecimalField(
        max_digits=24,
        decimal_places=4,
        default=0,
    )

    description = models.CharField(max_length=500, blank=True)
    counterparty = models.ForeignKey(
        "accounting.Counterparty",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    cost_center = models.ForeignKey(
        "accounting.CostCenter",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    cash_flow_tag = models.CharField(max_length=30, blank=True)
```

Contraintes :

```text
debit >= 0
credit >= 0
NOT (debit > 0 AND credit > 0)
```

---

# 10. Règle de partie double

Une écriture est valide lorsque :

```text
SUM(debit) = SUM(credit)
```

Exemple de validateur :

```python
class JournalEntryValidator:
    def validate_balance(self, entry):
        debit = sum(line.debit for line in entry.lines.all())
        credit = sum(line.credit for line in entry.lines.all())
        return debit == credit
```

---

# 11. Cycle de vie d'une écriture

```text
DRAFT
   |
   v
VALIDATED
   |
   v
POSTED
```

Une écriture `POSTED` doit devenir immuable.

Pour corriger :

```text
Écriture originale
       |
       v
ReversalEntry
       |
       v
Nouvelle écriture correcte
```

Cette règle garantit un audit trail comptable propre.

---

# 12. Audit trail

Chaque mutation comptable doit être enregistrée.

Exemple d'événements :

```text
ENTRY_CREATED
ENTRY_VALIDATED
ENTRY_POSTED
ENTRY_REVERSED
FEC_IMPORTED
ACCOUNT_CREATED
ACCOUNT_UPDATED
PERIOD_CLOSED
PERIOD_REOPENED
```

Modèle conceptuel :

```text
AuditEvent
- user
- organization
- action
- entity_type
- entity_id
- timestamp
- before
- after
- source_ip
- request_id
```

---

# 13. Import FEC

Pipeline cible :

```text
Upload FEC
   |
   v
Stockage du fichier original
   |
   v
Parsing
   |
   v
FECRawLine
   |
   v
Validation format
   |
   v
Détection comptes / journaux
   |
   v
Détection doublons
   |
   v
Normalisation
   |
   v
JournalEntry + JournalLine
   |
   v
Contrôles de partie double
   |
   v
POSTED
```

## 13.1 `FECImport`

```python
class FECImport(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT)
    original_filename = models.CharField(max_length=255)
    original_file = models.FileField(upload_to="fec/")
    sha256 = models.CharField(max_length=64)
    status = models.CharField(max_length=30)
    imported_at = models.DateTimeField(auto_now_add=True)
```

## 13.2 `FECRawLine`

```python
class FECRawLine(models.Model):
    import_batch = models.ForeignKey(
        FECImport,
        on_delete=models.CASCADE,
        related_name="raw_lines",
    )
    line_number = models.PositiveIntegerField()

    journal_code = models.CharField(max_length=50)
    journal_label = models.CharField(max_length=255)
    entry_number = models.CharField(max_length=255)
    entry_date = models.DateField()
    account_number = models.CharField(max_length=50)
    account_label = models.CharField(max_length=255)

    auxiliary_number = models.CharField(max_length=255, blank=True)
    auxiliary_label = models.CharField(max_length=255, blank=True)

    piece_reference = models.CharField(max_length=255, blank=True)
    piece_date = models.DateField(null=True, blank=True)
    entry_label = models.TextField()

    debit = models.DecimalField(max_digits=24, decimal_places=4)
    credit = models.DecimalField(max_digits=24, decimal_places=4)

    raw_data = models.JSONField()
```

---

# 14. Idempotence de l'import

Importer deux fois le même FEC ne doit jamais générer deux fois les mêmes écritures.

Clé possible :

```text
organization
+
fiscal_year
+
SHA256 du fichier
```

Détection complémentaire :

```text
journal
entry_number
entry_date
piece_reference
```

---

# 15. Moteur de contrôles

Les contrôles Excel deviennent des règles métier Python.

Exemples :

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

Modèle de résultat :

```python
class ControlResult(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    control_code = models.CharField(max_length=100)
    severity = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    expected_value = models.JSONField(null=True)
    actual_value = models.JSONField(null=True)
    details = models.JSONField(default=dict)
```

---

# 16. Grand livre

Le grand livre n'est pas une table primaire.

Il est reconstruit depuis :

```text
JournalEntry
+
JournalLine
+
Account
```

Requête conceptuelle :

```sql
SELECT
    posting_date,
    entry_number,
    account_code,
    debit,
    credit
FROM journal_lines
JOIN journal_entries
WHERE status = 'POSTED'
ORDER BY account_code, posting_date;
```

Pour le solde cumulé, PostgreSQL permet :

```sql
SUM(debit - credit)
OVER (
    PARTITION BY account_id
    ORDER BY posting_date, entry_id
)
```

---

# 17. Balance comptable

```text
JournalLine
     |
     v
GROUP BY Account
     |
     +-- SUM(Debit)
     +-- SUM(Credit)
     |
     v
Trial Balance
```

Service :

```text
TrialBalanceService
```

Méthodes :

```text
build_before_adjustment()
build_adjusted()
build_post_closing()
```

---

# 18. États financiers

Les états financiers doivent être générés depuis :

```text
Accounts
+
Balances
+
Mappings
+
StatementDefinitions
```

Définitions :

```text
BALANCE_SHEET
INCOME_STATEMENT
CASH_FLOW_STATEMENT
STATEMENT_OF_CHANGES_IN_EQUITY
```

---

# 19. `StatementLine`

```python
class StatementLine(models.Model):
    definition = models.ForeignKey(
        StatementDefinition,
        on_delete=models.CASCADE,
    )
    code = models.CharField(max_length=100)
    label = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    order = models.PositiveIntegerField()
```

Mapping :

```text
Account
    |
    v
StatementMapping
    |
    v
StatementLine
```

---

# 20. Référentiel SYSCOHADA

L'annexe `17_Annexe_Plan_OHADA` devient un référentiel versionné :

```text
AccountingFramework
    name = SYSCOHADA

FrameworkVersion
    version = 2017

FrameworkAccount
    10
    101
    1011
    ...
```

---

# 21. Référentiel IFRS

L'annexe `16_Annexe_Comptes_IFRS` devient :

```text
AccountingFramework
    name = IFRS

FrameworkVersion
    version = 2025

FrameworkAccount
    Cash and cash equivalents
    Trade receivables
    Revenue
    PPE
    ...
```

---

# 22. Distinction essentielle : référentiel vs plan de l'entreprise

```text
Référentiel réglementaire
        |
        v
FrameworkAccount

Plan comptable réel de l'entreprise
        |
        v
Account
```

Exemple :

```text
40110000  Microsoft
40110001  AWS
40110002  Orange

       |
       v

SYSCOHADA
4011 Fournisseurs

       |
       v

IFRS
Trade and other payables
```

---

# 23. `AccountMapping`

```python
class AccountMapping(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    framework_account = models.ForeignKey(
        FrameworkAccount,
        on_delete=models.PROTECT,
    )
    mapping_type = models.CharField(max_length=30)
    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
```

Évolution possible :

```text
Account
   |
   v
Rule-based mapping
   |
   v
Candidate mappings
   |
   v
Embeddings / IA
   |
   v
Suggested mapping
   |
   v
Human validation
```

---

# 24. Cash-flow

Tags :

```text
OPERATING
INVESTING
FINANCING
TRANSFER
OPENING
```

Réconciliation :

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

Service :

```text
CashFlowStatementService
```

---

# 25. Clôture

Workflow :

```text
OPEN
   |
   v
REVIEW
   |
   v
CLOSING
   |
   v
CLOSED
```

Après fermeture :

```text
POST interdit
```

La clôture annuelle doit :

```text
clôturer les comptes temporaires
+
transférer le résultat
+
générer les à-nouveaux
```

---

# 26. Dashboard et Analytics

Endpoints possibles :

```text
GET /api/dashboard/kpis/
GET /api/dashboard/revenue-trend/
GET /api/dashboard/cash-flow/
GET /api/dashboard/expenses/
GET /api/dashboard/balance-structure/
GET /api/dashboard/journals/
GET /api/dashboard/accounts/
GET /api/dashboard/controls/
```

KPI :

```text
Revenue
EBITDA
Operating Profit
Net Income
Cash
CFO
CFI
CFF
Total Assets
Total Liabilities
Total Equity
Current Ratio
Debt / Equity
Net Margin
CFO / Net Income
```

---

# 27. API REST

Routes :

```text
/api/v1/organizations/
/api/v1/accounts/
/api/v1/journals/
/api/v1/entries/
/api/v1/imports/fec/
/api/v1/reports/trial-balance/
/api/v1/reports/income-statement/
/api/v1/reports/balance-sheet/
/api/v1/reports/cash-flow/
/api/v1/referentials/
/api/v1/mappings/
/api/v1/controls/
```

Architecture mutation :

```text
APIView
  |
  v
Serializer
  |
  v
Service
  |
  v
Domain validation
  |
  v
Database transaction
```

---

# 28. Organisation du code

```text
accounting/
|
+-- models/
|   +-- account.py
|   +-- journal.py
|   +-- entry.py
|   +-- line.py
|
+-- services/
|   +-- create_entry.py
|   +-- validate_entry.py
|   +-- post_entry.py
|   +-- reverse_entry.py
|
+-- selectors/
|   +-- entries.py
|   +-- balances.py
|
+-- validators/
|
+-- api/
    +-- serializers.py
    +-- views.py
    +-- urls.py
```

Principe :

```text
models/    = stockage
services/  = mutations métier
selectors/ = lectures et requêtes complexes
validators/= règles comptables
api/       = exposition HTTP
```

---

# 29. PostgreSQL

PostgreSQL doit être utilisé dès le départ.

Atouts :

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

Indexes :

```text
organization_id
posting_date
account_id
journal_id
period_id
status
entry_number
```

Indexes composites :

```text
organization_id + posting_date
organization_id + account_id + posting_date
organization_id + fiscal_year_id
```

---

# 30. Précision monétaire

Ne jamais utiliser `float` pour les montants comptables.

Utiliser :

```python
Decimal
```

Exemple :

```python
models.DecimalField(
    max_digits=24,
    decimal_places=4,
)
```

---

# 31. Transactions atomiques

Le posting doit être transactionnel :

```python
@transaction.atomic
```

Ainsi :

```text
validation
+
posting
+
audit
```

sont enregistrés ensemble.

---

# 32. Multi-entités

Chaque objet métier doit être rattaché directement ou indirectement à :

```text
organization_id
```

Toutes les requêtes doivent être scoppées par organisation.

---

# 33. RBAC

| Action | Accountant | Reviewer | Auditor | Admin |
|---|---:|---:|---:|---:|
| créer brouillon | oui | oui | non | oui |
| valider | non | oui | non | oui |
| poster | non | oui | non | oui |
| consulter | oui | oui | oui | oui |
| reverser | non | oui | non | oui |
| clôturer | non | oui | non | oui |

---

# 34. Exports

L'application doit continuer à exporter :

```text
Journal.xlsx
Grand_Livre.xlsx
Balance.xlsx
Financial_Statements.xlsx
FEC_Controls.xlsx
```

Le classeur Excel actuel peut donc devenir un **format de sortie**, même après la migration Django.

Une cible ultérieure est également l'export FEC :

```text
JournalEntry / JournalLine
        |
        v
FEC Export Engine
        |
        v
Fichier FEC conforme
```

---

# 35. Tests de non-régression

Le classeur Excel devient un oracle de comparaison.

```text
                         Excel        Django
Revenue                  X            X
Net Income               X            X
Cash                     X            X
Total Assets             X            X
```

Exemple pour le Petit dossier :

```python
def test_petit_dossier_scenario():
    assert revenue == Decimal("2465000")
    assert net_income == Decimal("-990772")
    assert ending_cash == Decimal("85000")
```

Tests fondamentaux :

```python
def test_entry_is_balanced():
    ...

def test_trial_balance_is_balanced():
    ...

def test_balance_sheet_balances():
    ...

def test_cash_flow_reconciles():
    ...

def test_fec_import_is_idempotent():
    ...

def test_posted_entry_is_immutable():
    ...

def test_closed_period_rejects_posting():
    ...
```

---

# 36. Performance

Pour de gros FEC :

```text
bulk_create
PostgreSQL COPY
indexes
batch processing
Celery
materialized views
```

Celery :

```text
parse FEC
validate FEC
import FEC
generate large exports
refresh analytics
generate annual reports
```

Redis :

```text
dashboard KPIs
statement summaries
referentials
lookup data
```

---

# 37. Frontend

## MVP

```text
Django Templates
+
HTMX
```

Puis React seulement si nécessaire pour :

```text
dashboard complexe
drill-down interactif
data grids massives
drag-and-drop
workflow avancé
visualisations riches
```

Architecture possible :

```text
React
   |
   v
DRF
   |
   v
Django Services
   |
   v
PostgreSQL
```

---

# 38. Observabilité et sécurité

Observabilité :

```text
Sentry
Prometheus
Grafana
OpenTelemetry
structured logging
```

Sécurité :

```text
HTTPS
CSRF
CSP
rate limiting
RBAC
audit trail
encryption at rest
secret management
backups
MFA pour rôles sensibles
```

---

# 39. Docker

```text
docker-compose
|
+-- django
+-- postgres
+-- redis
+-- celery-worker
+-- celery-beat
+-- nginx
```

---

# 40. CI/CD

```text
lint
  |
  v
unit tests
  |
  v
integration tests
  |
  v
security scan
  |
  v
build
  |
  v
deploy staging
  |
  v
smoke tests
  |
  v
production
```

---

# 41. Roadmap d'implémentation

## Phase 0 — Reverse Engineering

Figer les règles du classeur.

Livrables :

```text
ACCOUNTING_RULES.md
EXCEL_TO_DOMAIN_MAPPING.md
REFERENCE_TEST_CASES.md
```

## Phase 1 — Foundation

Créer :

```text
users
organizations
FiscalYear
AccountingPeriod
```

## Phase 2 — Accounting Core

Créer :

```text
ChartOfAccounts
Account
Journal
JournalEntry
JournalLine
```

## Phase 3 — Posting Engine

Créer :

```text
EntryValidator
PostingService
ReversalService
```

## Phase 4 — FEC

Créer :

```text
FECImport
FECRawLine
FECParser
FECValidator
FECNormalizationService
```

## Phase 5 — Ledger

Créer :

```text
GeneralLedgerService
TrialBalanceService
```

## Phase 6 — Financial Statements

Créer :

```text
IncomeStatementService
BalanceSheetService
CashFlowStatementService
```

## Phase 7 — Controls

Créer :

```text
AccountingControl
ControlRun
ControlResult
```

## Phase 8 — Closing

Créer :

```text
ClosingService
OpeningBalanceService
```

## Phase 9 — Referentials

Importer :

```text
SYSCOHADA 2017
IFRS
```

## Phase 10 — Mapping

Créer :

```text
AccountMapping
MappingRule
MappingSuggestion
```

## Phase 11 — Analytics

Créer :

```text
KPIs
Dashboard
Trends
Alerts
```

## Phase 12 — API

Créer :

```text
DRF API v1
```

## Phase 13 — UI

Créer :

```text
Accounting dashboard
FEC import UI
Journal explorer
Ledger explorer
Financial statements
Mapping interface
```

## Phase 14 — Production Readiness

Ajouter :

```text
RBAC
audit
monitoring
backups
CI/CD
performance
security
```

---

# 42. Priorité d'implémentation

```text
1. Modèle de données
2. Partie double
3. Posting
4. Import FEC
5. Grand livre
6. Balance
7. États financiers
8. Contrôles
9. Clôture
10. Référentiels
11. Mapping
12. Dashboard
13. Frontend avancé
```

---

# 43. Ce qu'il ne faut pas faire

## Ne pas stocker les états financiers comme sources primaires

Éviter :

```text
BalanceSheetTable
IncomeStatementTable
GeneralLedgerTable
```

## Ne pas coder les états dans les vues

Éviter :

```python
revenue = Account.objects.filter(code__startswith="7")
```

Utiliser :

```text
selectors
services
statement mappings
```

## Ne jamais modifier une écriture postée

Toujours utiliser :

```text
reversal + replacement
```

## Ne jamais utiliser `float`

Toujours utiliser `Decimal`.

---

# 44. Architecture produit finale

```text
                     ACCOUNTING ENGINE
                           |
          +----------------+----------------+
          |                |                |
      FEC Import       Manual Entry        API
          |                |                |
          +----------------+----------------+
                           |
                           v
                    Journal Entries
                           |
                    Journal Lines
                           |
             +-------------+-------------+
             |                           |
             v                           v
      General Ledger                  Controls
             |
             v
        Trial Balance
             |
      +------+------+------+
      |      |             |
      v      v             v
     P&L   Balance       Cash Flow
      |      |             |
      +------+-------------+
             |
             v
          Closing
             |
             v
         Analytics
             |
             v
         Dashboard
```

Référentiels :

```text
              REFERENTIAL ENGINE

        +----------+-----------+
        |          |           |
        v          v           v
    SYSCOHADA     IFRS       Future
        |          |
        +-----+----+
              |
              v
       Account Mapping
              |
              v
     Financial Reporting
```

---

# 45. Conclusion

Le classeur Excel constitue déjà une preuve fonctionnelle riche du futur produit.

La migration recommandée consiste à :

1. conserver Excel comme **référence fonctionnelle et jeu de tests** ;
2. reconstruire le domaine autour de `JournalEntry` et `JournalLine` ;
3. faire du journal comptable la source canonique ;
4. industrialiser l'import FEC ;
5. reconstruire grand livre, balances et états financiers par calcul ;
6. transformer les annexes OHADA et IFRS en référentiels versionnés ;
7. mettre en place un moteur de mappings ;
8. transformer les contrôles Excel en règles métier Python ;
9. rendre les écritures postées immuables ;
10. assurer un audit trail complet ;
11. exposer le moteur via Django REST Framework ;
12. ajouter progressivement dashboard et frontend riche.

La cible n'est donc pas une simple copie web du classeur mais un **système comptable, analytique et de normalisation multi-référentiels**, traçable, testable, multi-entités et extensible.
