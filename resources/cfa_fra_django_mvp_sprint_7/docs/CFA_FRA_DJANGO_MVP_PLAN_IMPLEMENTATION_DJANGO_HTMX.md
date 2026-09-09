# CFA FRA — Plan d’implémentation du MVP Django + HTMX

## Application cible : moteur comptable, import FEC, reporting financier et dashboard

**Projet :** CFA FRA — Accounting & Financial Reporting Engine  
**Document parent :** `CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md`  
**Frontend MVP :** Django Templates + HTMX  
**Backend :** Django  
**Base de données :** PostgreSQL  
**Version du document :** 1.0  
**Date :** 25 août 2026

---

# 1. Objectif du MVP

Le MVP doit transformer le prototype Excel CFA FRA en une application web utilisable sans chercher à reproduire Excel cellule par cellule.

Le MVP doit couvrir la chaîne métier suivante :

```text
Création d'une organisation
        |
        v
Création / import du plan comptable
        |
        v
Import d'un FEC
        |
        v
Contrôles et normalisation
        |
        v
Journal comptable
        |
        v
Grand livre
        |
        v
Balance
        |
        v
Compte de résultat
        |
        v
Bilan
        |
        v
Flux de trésorerie
        |
        v
Contrôles comptables
        |
        v
Dashboard
```

Le MVP doit être suffisamment robuste pour reproduire les résultats des scénarios Excel déjà construits.

---

# 2. Principes structurants du MVP

Le MVP doit respecter les principes du document de conception.

## 2.1 Source comptable unique

Les données canoniques sont :

```text
JournalEntry
+
JournalLine
+
Account
+
AccountingPeriod
```

Le grand livre, les balances et les états financiers sont des **projections calculées**.

Ils ne doivent pas être stockés comme des copies indépendantes.

---

## 2.2 Partie double obligatoire

Toute écriture postée doit respecter :

```text
Total Débit = Total Crédit
```

---

## 2.3 Immutabilité des écritures postées

Workflow :

```text
DRAFT
   |
   v
VALIDATED
   |
   v
POSTED
```

Une écriture `POSTED` ne peut plus être modifiée directement.

Correction :

```text
POSTED ENTRY
     |
     v
REVERSAL
     |
     v
NEW CORRECT ENTRY
```

---

## 2.4 Multi-entités dès le MVP

Toutes les données métier doivent être rattachées à une organisation.

```text
organization_id
```

---

## 2.5 PostgreSQL dès le départ

Le MVP utilise PostgreSQL.

SQLite n’est utilisé que pour certains tests unitaires éventuels, jamais comme base de référence de l’environnement applicatif.

---

## 2.6 Frontend volontairement simple

Le MVP utilise :

```text
Django Templates
+
HTMX
```

React est explicitement hors périmètre du MVP.

---

# 3. Pourquoi Django Templates + HTMX pour le MVP

Cette combinaison est adaptée au projet car elle permet :

- de conserver toute la logique métier côté Django ;
- de limiter la duplication entre frontend et backend ;
- de construire rapidement des workflows métier ;
- de mettre à jour des fragments de page sans SPA ;
- de créer des formulaires riches sans React ;
- de simplifier la sécurité CSRF ;
- de simplifier l’authentification ;
- de livrer rapidement les écrans FEC et comptables ;
- de garder une architecture facilement testable.

Architecture :

```text
Browser
   |
   | HTML / HTMX
   v
Django Views
   |
   v
Services métier
   |
   v
Selectors
   |
   v
Django ORM
   |
   v
PostgreSQL
```

---

# 4. Périmètre fonctionnel du MVP

## Inclus

### Administration

- authentification ;
- utilisateurs ;
- organisations ;
- exercices ;
- périodes comptables ;
- paramètres de base.

### Comptabilité

- plan comptable ;
- journaux ;
- écritures ;
- lignes débit / crédit ;
- validation ;
- posting ;
- extourne.

### FEC

- upload ;
- parsing ;
- contrôle de format ;
- prévisualisation ;
- normalisation ;
- détection de comptes ;
- détection de journaux ;
- création des écritures ;
- rapport d’import.

### Reporting

- journal ;
- grand livre ;
- balance ;
- balance avant ajustements ;
- balance ajustée ;
- compte de résultat ;
- bilan ;
- cash-flow.

### Contrôles

- équilibre des écritures ;
- équilibre de la balance ;
- bilan équilibré ;
- cash-flow réconcilié ;
- comptes inconnus ;
- période fermée ;
- lignes invalides ;
- doublons FEC.

### Référentiels

- SYSCOHADA en lecture ;
- IFRS en lecture ;
- mapping manuel compte client → compte de référentiel.

### Dashboard

- chiffre d’affaires ;
- résultat net ;
- EBITDA ;
- cash ;
- CFO ;
- total actif ;
- tendances mensuelles ;
- structure des charges ;
- contrôles en anomalie.

### Audit

- utilisateur ;
- action ;
- date ;
- objet ;
- avant / après pour les mutations sensibles.

---

# 5. Hors périmètre du MVP

Les fonctionnalités suivantes sont reportées :

```text
React / SPA

application mobile

IA de mapping automatique

RAG

consolidation multi-groupe avancée

multi-devises avancé

budget / forecast avancé

comptabilité analytique complète

ERP achats / ventes

facturation client

banque automatique

OCR de factures

connecteurs bancaires

microservices

Kafka

data warehouse

BI externe

workflow BPM complexe
```

Celery et Redis peuvent être préparés dans l’architecture mais ne sont obligatoires dans le MVP que si l’import des gros FEC rend les traitements synchrones insuffisants.

---

# 6. Stack technique MVP

```text
Python 3.13

Django 5.x

PostgreSQL 17

HTMX

Django Templates

Bootstrap 5
ou
Tailwind CSS

Chart.js

pytest

pytest-django

ruff

mypy

django-stubs

Docker

docker compose
```

Optionnel dès le MVP :

```text
django-filter

django-tables2

django-crispy-forms

crispy-bootstrap5

django-htmx

django-environ

whitenoise

sentry-sdk
```

---

# 7. Architecture du repository

```text
cfa-fra/
|
+-- backend/
|   |
|   +-- manage.py
|   |
|   +-- config/
|   |   |
|   |   +-- settings/
|   |   |   +-- base.py
|   |   |   +-- local.py
|   |   |   +-- test.py
|   |   |   +-- production.py
|   |   |
|   |   +-- urls.py
|   |   +-- wsgi.py
|   |   +-- asgi.py
|   |
|   +-- apps/
|   |   |
|   |   +-- users/
|   |   +-- organizations/
|   |   +-- accounting/
|   |   +-- imports/
|   |   +-- reporting/
|   |   +-- controls/
|   |   +-- closing/
|   |   +-- referentials/
|   |   +-- analytics/
|   |   +-- audit/
|   |   +-- exports/
|   |
|   +-- templates/
|   |   |
|   |   +-- base.html
|   |   +-- components/
|   |   +-- partials/
|   |
|   +-- static/
|       +-- css/
|       +-- js/
|
+-- docker/
|
+-- docs/
|
+-- tests/
|
+-- .env.example
+-- docker-compose.yml
+-- pyproject.toml
+-- README.md
```

---

# 8. Structure interne d’une app métier

Exemple :

```text
apps/accounting/
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
|   +-- accounts.py
|   +-- entries.py
|   +-- journal.py
|
+-- validators/
|
+-- forms/
|
+-- views/
|
+-- urls.py
|
+-- templates/accounting/
|
+-- admin.py
|
+-- tests/
```

---

# 9. Convention d’architecture

## Models

Responsables uniquement de :

```text
structure de données

contraintes locales

relations

petites propriétés
```

---

## Services

Responsables des mutations métier :

```text
create

validate

post

reverse

close

import
```

---

## Selectors

Responsables des lectures :

```text
journal

ledger

trial balance

financial statements

dashboard
```

---

## Views

Responsables de :

```text
HTTP

permissions

forms

rendering

HTMX
```

Les Views ne contiennent pas les calculs comptables.

---

# 10. Phase 0 — Initialisation du projet

## Objectif

Créer une base technique reproductible.

## Tâches

```text
[ ] créer le repository Git

[ ] initialiser pyproject.toml

[ ] créer le projet Django

[ ] créer config/settings

[ ] connecter PostgreSQL

[ ] créer docker-compose.yml

[ ] intégrer HTMX

[ ] intégrer le framework CSS

[ ] configurer pytest

[ ] configurer ruff

[ ] configurer mypy

[ ] configurer .env

[ ] créer README.md

[ ] créer Makefile ou scripts de commandes
```

## Docker compose minimal

```text
django
postgres
```

Option :

```text
redis
```

## Critère de sortie

```text
docker compose up
```

doit permettre d’accéder à :

```text
http://localhost:8000/
```

avec une page Django fonctionnelle.

---

# 11. Phase 1 — Authentification et organisations

## Modèles

```text
User

Organization

OrganizationMembership
```

## Rôles MVP

```text
ADMIN
ACCOUNTANT
REVIEWER
AUDITOR
READ_ONLY
```

## Écrans

```text
/login/

/logout/

/organizations/

/organizations/<id>/
```

## HTMX

Le changement d’organisation active peut être réalisé via HTMX.

Exemple :

```html
<select
    hx-post="/context/switch-organization/"
    hx-trigger="change"
    hx-target="#app-context"
>
```

## Critères d’acceptation

```text
[ ] un utilisateur peut se connecter

[ ] un utilisateur ne voit que ses organisations

[ ] les requêtes métier sont filtrées par organisation

[ ] un utilisateur peut changer d’organisation active
```

---

# 12. Phase 2 — Exercices et périodes comptables

## Modèles

```text
FiscalYear

AccountingPeriod

AccountingSettings
```

## Exemple

```text
FiscalYear

2025

01/01/2025
31/12/2025
```

Périodes :

```text
2025-01
2025-02
...
2025-12
```

## Statuts

```text
OPEN

CLOSING

CLOSED
```

## Écrans

```text
/settings/fiscal-years/

/settings/periods/
```

## Critères

```text
[ ] création d’un exercice

[ ] génération automatique des 12 périodes

[ ] fermeture d’une période

[ ] interdiction de posting dans une période fermée
```

---

# 13. Phase 3 — Plan comptable

## Modèles

```text
ChartOfAccounts

Account
```

## Account

Champs MVP :

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

## Écrans

```text
/accounts/

/accounts/create/

/accounts/<id>/

/accounts/<id>/edit/
```

## UX

Table :

```text
Code

Libellé

Nature

Solde normal

Référentiel

Actif
```

Filtres HTMX :

```text
recherche code

recherche libellé

type

actif/inactif
```

Exemple :

```html
<input
    type="search"
    name="q"
    hx-get="/accounts/"
    hx-trigger="keyup changed delay:400ms"
    hx-target="#accounts-table"
>
```

## Critères

```text
[ ] création de comptes

[ ] hiérarchie parent/enfant

[ ] recherche dynamique

[ ] pagination

[ ] unicité du code par plan
```

---

# 14. Phase 4 — Journaux comptables

## Modèle

```text
Journal
```

Types :

```text
PURCHASE

SALES

BANK

CASH

PAYROLL

TAX

GENERAL

OPENING
```

## Écrans

```text
/journals/

/journals/create/
```

## Critères

```text
[ ] création des journaux

[ ] code unique par organisation

[ ] activation / désactivation
```

---

# 15. Phase 5 — Saisie des écritures comptables

Cette phase est le cœur du MVP.

## Modèles

```text
JournalEntry

JournalLine
```

---

# 16. Écran de création d’écriture

Route :

```text
/entries/create/
```

Structure :

```text
Date

Journal

Référence

Description

---------------------------------------

Compte | Libellé | Débit | Crédit

---------------------------------------

Total débit

Total crédit

Écart
```

---

# 17. Ajout dynamique de lignes avec HTMX

Bouton :

```text
+ Ajouter une ligne
```

HTMX :

```text
GET /entries/line-form/
```

retourne :

```html
<tr>
    ...
</tr>
```

qui est ajouté à la table.

---

# 18. Suppression de ligne

Chaque ligne possède :

```text
Supprimer
```

sans rechargement de page.

---

# 19. Contrôle temps réel débit / crédit

Après modification d’une ligne :

```text
hx-post
```

vers :

```text
/entries/calculate-totals/
```

Retour :

```text
Total Débit

Total Crédit

Écart

Statut
```

Affichage :

```text
ÉQUILIBRÉ
```

ou :

```text
NON ÉQUILIBRÉ
```

---

# 20. Workflow de l’écriture

Boutons :

```text
Enregistrer brouillon

Valider

Poster

Annuler
```

## Règles

### DRAFT

modifiable.

### VALIDATED

validée mais pas encore comptabilisée.

### POSTED

immuable.

---

# 21. PostingService

Pseudo-code :

```python
@transaction.atomic
def post_entry(*, entry, user):

    validate_period(entry.period)

    validate_entry(entry)

    entry.status = POSTED

    entry.posted_at = timezone.now()

    entry.save()

    create_audit_event(...)
```

---

# 22. Validation de l’écriture

Contrôles :

```text
au moins 2 lignes

débit >= 0

crédit >= 0

débit et crédit simultanés interdits

compte actif

période ouverte

journal actif

total débit = total crédit
```

---

# 23. Phase 6 — Extourne

Route :

```text
/entries/<id>/reverse/
```

Le système crée :

```text
REVERSAL ENTRY
```

avec :

```text
debit ↔ credit
```

Référence :

```text
REV-<entry_number>
```

Lien :

```text
reversal_of
```

## Critères

```text
[ ] l'écriture originale demeure inchangée

[ ] une écriture de contre-passation est créée

[ ] l'audit trail enregistre l'opération
```

---

# 24. Phase 7 — Import FEC

## Routes

```text
/imports/fec/

/imports/fec/new/

/imports/fec/<id>/
```

## Étapes UX

```text
1. Upload

2. Analyse

3. Preview

4. Contrôles

5. Mapping

6. Confirmation

7. Import
```

---

# 25. Upload FEC

Formulaire :

```text
Fichier

Organisation

Exercice

Encodage optionnel
```

Formats acceptés :

```text
.txt

.tsv
```

---

# 26. Conservation du fichier original

Créer :

```text
FECImport
```

avec :

```text
original_file

filename

sha256

uploaded_by

uploaded_at

status
```

---

# 27. Parsing FEC

Créer :

```text
FECParser
```

Responsabilités :

```text
détection encodage

lecture colonnes

conversion dates

conversion Decimal

validation des colonnes FEC

numéro de ligne source
```

---

# 28. FECRawLine

Toutes les lignes sont conservées avant transformation.

Cela permet :

```text
audit

reprocessing

debug

preuve de source
```

---

# 29. Preview FEC HTMX

L’écran doit afficher :

```text
Nombre de lignes

Nombre de journaux

Nombre de comptes

Total débit

Total crédit

Écart

Nombre d'erreurs
```

Puis une table paginée.

---

# 30. Contrôles FEC

Minimum :

```text
FEC_REQUIRED_COLUMNS

FEC_REQUIRED_VALUES

FEC_INVALID_DATE

FEC_INVALID_AMOUNT

FEC_DEBIT_AND_CREDIT

FEC_ZERO_LINE

FEC_DUPLICATE_LINE

FEC_UNBALANCED_ENTRY

FEC_UNKNOWN_ACCOUNT
```

---

# 31. Rapport d’import

Affichage :

```text
OK          1 500

Warning        25

Error           3
```

Drill-down HTMX :

```text
cliquer sur Error
```

affiche les lignes concernées.

---

# 32. Import transactionnel

L'import final ne doit pas laisser une comptabilité partiellement créée.

Utiliser :

```python
@transaction.atomic
```

---

# 33. Idempotence

Calcul :

```text
SHA256(file)
```

Avant import :

```text
Ce fichier a-t-il déjà été importé ?
```

---

# 34. Phase 8 — Journal comptable

Route :

```text
/reports/journal/
```

Filtres :

```text
date début

date fin

journal

compte

référence

statut
```

HTMX met à jour uniquement :

```text
#journal-results
```

---

# 35. Phase 9 — Grand livre

Route :

```text
/reports/general-ledger/
```

Filtres :

```text
compte

période

date

journal
```

Colonnes :

```text
Date

Journal

Entry

Description

Débit

Crédit

Mouvement

Solde cumulé
```

Le solde cumulé doit idéalement être calculé avec une window function PostgreSQL.

---

# 36. Phase 10 — Balance

Route :

```text
/reports/trial-balance/
```

Colonnes :

```text
Compte

Libellé

Débit

Crédit

Solde débiteur

Solde créditeur
```

Options :

```text
Avant ajustements

Ajustée

Post-clôture
```

---

# 37. Contrôle de balance

Afficher en bas :

```text
Total débit

Total crédit

Écart
```

Statut :

```text
OK
```

ou :

```text
ERREUR
```

---

# 38. Phase 11 — Compte de résultat

Route :

```text
/reports/income-statement/
```

Période :

```text
01/01/2025
→
31/12/2025
```

Rubriques MVP :

```text
Revenue

Operating expenses

EBITDA

Depreciation

Operating profit

Finance costs

Profit before tax

Income tax

Net income
```

---

# 39. Phase 12 — Bilan

Route :

```text
/reports/balance-sheet/
```

Structure :

```text
ASSETS

    Current Assets

    Non-current Assets

LIABILITIES

    Current Liabilities

    Non-current Liabilities

EQUITY
```

Contrôle :

```text
Assets
=
Liabilities + Equity
```

---

# 40. Phase 13 — Cash-flow

Route :

```text
/reports/cash-flow/
```

Méthode MVP :

```text
directe
```

Classification :

```text
OPERATING

INVESTING

FINANCING

TRANSFER

OPENING
```

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

# 41. Phase 14 — Moteur de contrôles

## Modèles

```text
AccountingControl

ControlRun

ControlResult
```

## Écran

```text
/controls/
```

Carte :

```text
Contrôles exécutés : 12

OK : 10

Warnings : 1

Errors : 1
```

---

# 42. Contrôles MVP

```text
ENTRY_BALANCED

TRIAL_BALANCE_BALANCED

BALANCE_SHEET_BALANCED

CASHFLOW_RECONCILED

UNKNOWN_ACCOUNT

INVALID_ACCOUNT

CLOSED_PERIOD_ENTRY

DUPLICATE_FEC

INVALID_FEC_LINE

TEMPORARY_ACCOUNT_AFTER_CLOSE
```

---

# 43. Phase 15 — Référentiel SYSCOHADA

Importer le référentiel provenant de l’annexe actuelle.

Modèles :

```text
AccountingFramework

FrameworkVersion

FrameworkAccount
```

Valeurs :

```text
SYSCOHADA

2017
```

Écran :

```text
/referentials/syscohada/
```

Recherche HTMX :

```text
code

intitulé

classe
```

---

# 44. Phase 16 — Référentiel IFRS

Même modèle.

```text
AccountingFramework

IFRS
```

Écran :

```text
/referentials/ifrs/
```

---

# 45. Phase 17 — Mapping de comptes

Route :

```text
/accounts/<id>/mapping/
```

Interface :

```text
Compte entreprise

40110000
FOURNISSEUR X

            |
            +--> SYSCOHADA : 4011 Fournisseurs

            |
            +--> IFRS : Trade and other payables
```

MVP :

```text
mapping manuel
```

Pas d'IA.

---

# 46. Phase 18 — Dashboard

Route :

```text
/dashboard/
```

KPI :

```text
Revenue

EBITDA

Net Income

CFO

Cash

Total Assets
```

Graphiques :

```text
Revenue by month

Expenses by month

Net income by month

Cash flow

Expense breakdown

Accounting control status
```

---

# 47. Graphiques

Le MVP peut utiliser :

```text
Chart.js
```

HTMX recharge les données / fragments sans introduire React.

Architecture :

```text
HTMX

      |
      v

Django partial

      |
      v

data-* / json_script

      |
      v

Chart.js
```

---

# 48. Dashboard drill-down

Exemple :

```text
Carte CFO
```

clic :

```text
/dashboard/cfo-details/
```

retourne un panneau HTMX.

---

# 49. Phase 19 — Audit Trail

Modèle :

```text
AuditEvent
```

Actions MVP :

```text
LOGIN

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

---

# 50. Écran Audit

Route :

```text
/audit/
```

Filtres :

```text
utilisateur

action

date

objet
```

---

# 51. Phase 20 — Clôture

Route :

```text
/closing/
```

Workflow :

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

---

# 52. Conditions de clôture

Impossible de clôturer si :

```text
balance non équilibrée

cash-flow non réconcilié

écritures DRAFT restantes

contrôles bloquants
```

---

# 53. Phase 21 — Export

Exports MVP :

```text
Journal.csv

Grand_Livre.csv

Balance.csv

Financial_Statements.xlsx
```

L'export Excel complet identique au prototype peut être traité dans une itération ultérieure.

---

# 54. Templates MVP

Structure recommandée :

```text
templates/
|
+-- base.html
|
+-- layout/
|   +-- sidebar.html
|   +-- navbar.html
|
+-- components/
|   +-- card.html
|   +-- badge.html
|   +-- pagination.html
|   +-- filters.html
|   +-- modal.html
|
+-- accounting/
|
+-- imports/
|
+-- reporting/
|
+-- controls/
|
+-- referentials/
|
+-- analytics/
```

---

# 55. Convention HTMX

Utiliser un suffixe :

```text
_partial.html
```

Exemple :

```text
accounts/list.html

accounts/_table.html
```

View :

```python
if request.htmx:
    return render(
        request,
        "accounts/_table.html",
        context,
    )

return render(
    request,
    "accounts/list.html",
    context,
)
```

---

# 56. Loading indicators

Tous les appels HTMX longs doivent afficher :

```text
spinner

loading

progress
```

Exemple :

```html
<span
    class="htmx-indicator"
>
    Chargement...
</span>
```

---

# 57. Messages utilisateur

Convention :

```text
SUCCESS

INFO

WARNING

ERROR
```

Exemples :

```text
Écriture postée avec succès.

Le FEC contient 14 avertissements.

La période est fermée.
```

---

# 58. Pagination

Toute table potentiellement volumineuse doit être paginée :

```text
Journal

Grand livre

FEC

Audit

Accounts
```

Pagination recommandée :

```text
50 lignes
```

par défaut.

---

# 59. Recherche

HTMX :

```text
delay:300ms
```

ou :

```text
delay:400ms
```

pour éviter un appel serveur à chaque frappe.

---

# 60. Sécurité MVP

Minimum :

```text
CSRF

secure cookies

HTTPS production

RBAC

organization scoping

audit trail

validation fichiers uploadés

taille maximale FEC

MIME / extension control

rate limiting login

secrets dans variables d'environnement
```

---

# 61. Tests unitaires

Cœur métier :

```text
Account

JournalEntry

JournalLine

EntryValidator

PostingService

ReversalService

FECParser

FECValidator

TrialBalanceService

IncomeStatementService

BalanceSheetService

CashFlowStatementService
```

---

# 62. Tests de non-régression avec les classeurs Excel

Le modèle Excel constitue l’oracle initial.

Exemple Petit dossier :

```python
def test_petit_dossier_reference():

    assert revenue == Decimal("2465000")

    assert net_income == Decimal("-990772")

    assert closing_cash == Decimal("85000")
```

Il faut créer aussi les scénarios :

```text
Petit dossier

Moyen dossier

Gros dossier

Agence logicielle 3 ans
```

---

# 63. Fixtures de référence

Créer :

```text
tests/fixtures/

    fec_petit_dossier.txt

    fec_moyen_dossier.txt

    fec_gros_dossier.txt
```

et :

```text
expected_results.json
```

Exemple :

```json
{
  "petit_dossier": {
    "revenue": "2465000",
    "net_income": "-990772",
    "cash": "85000"
  }
}
```

---

# 64. Tests HTMX

Tester notamment :

```text
search account

add journal line

remove journal line

calculate totals

FEC preview

FEC error drilldown

dashboard period switch
```

---

# 65. Tests d’intégration

Scénario principal :

```text
create organization

→ create fiscal year

→ import FEC

→ validate

→ post

→ journal

→ ledger

→ trial balance

→ income statement

→ balance sheet

→ cash-flow

→ controls
```

---

# 66. CI minimale

Pipeline :

```text
ruff

mypy

pytest

coverage
```

Puis :

```text
docker build
```

---

# 67. Qualité minimale avant merge

```text
ruff = 0 erreurs

mypy = 0 erreurs bloquantes

pytest = vert

coverage métier >= 80 %
```

Cible souhaitée pour les services comptables :

```text
>= 90 %
```

---

# 68. Gestion des migrations

Règle :

```text
1 fonctionnalité de données
=
migration Django versionnée
```

Ne jamais modifier la base manuellement en production.

---

# 69. Seeds / données initiales

Management commands :

```text
python manage.py seed_syscohada

python manage.py seed_ifrs

python manage.py seed_demo
```

---

# 70. Commandes métier utiles

Créer :

```text
python manage.py import_fec <file>

python manage.py run_controls

python manage.py rebuild_trial_balance

python manage.py seed_referentials
```

---

# 71. Milestones recommandés

## Milestone M0 — Bootstrap

Livrable :

```text
Django + PostgreSQL + HTMX opérationnels
```

---

## Milestone M1 — Accounting Core

Livrable :

```text
Organizations
Periods
Accounts
Journals
Entries
Posting
```

---

## Milestone M2 — FEC

Livrable :

```text
Upload
Parse
Validate
Preview
Import
```

---

## Milestone M3 — Reporting

Livrable :

```text
Journal
Ledger
Trial Balance
P&L
Balance Sheet
Cash Flow
```

---

## Milestone M4 — Quality

Livrable :

```text
Controls
Audit
Closing
```

---

## Milestone M5 — Referentials

Livrable :

```text
SYSCOHADA
IFRS
Manual Mapping
```

---

## Milestone M6 — UX / Dashboard

Livrable :

```text
Dashboard Pro
HTMX interactions
Exports
```

---

# 72. Découpage en sprints

Une approche réaliste est de travailler en sprints d’une semaine ou deux semaines.

## Sprint 0 — Bootstrap

```text
Repository

Docker

Django

PostgreSQL

HTMX

CI

Quality tooling
```

---

## Sprint 1 — Organizations & Periods

```text
Users

Organization

RBAC initial

FiscalYear

AccountingPeriod
```

---

## Sprint 2 — Accounting Core

```text
ChartOfAccounts

Account

Journal

JournalEntry

JournalLine
```

---

## Sprint 3 — Posting

```text
Entry forms

HTMX line forms

Validation

Posting

Reversal

Audit
```

---

## Sprint 4 — FEC Import

```text
Upload

Parser

Raw lines

Preview

Validation

Import
```

---

## Sprint 5 — Ledger & Balance

```text
Journal report

Grand ledger

Trial balance

Filters HTMX
```

---

## Sprint 6 — Financial Statements

```text
P&L

Balance Sheet

Cash Flow

Reconciliations
```

---

## Sprint 7 — Controls & Closing

```text
Control engine

Control dashboard

Period closing

Opening balances
```

---

## Sprint 8 — Referentials

```text
SYSCOHADA

IFRS

Manual mappings
```

---

## Sprint 9 — Dashboard

```text
KPIs

Charts

Drill-down

Alerts
```

---

## Sprint 10 — Stabilisation

```text
Tests

Performance

Security

Documentation

Demo

Release candidate
```

---

# 73. Définition de Done du MVP

Le MVP est terminé lorsque le scénario suivant fonctionne de bout en bout :

```text
Utilisateur
   |
   v
Connexion
   |
   v
Organisation
   |
   v
Exercice 2025
   |
   v
Import FEC
   |
   v
Preview
   |
   v
Contrôles
   |
   v
Import validé
   |
   v
Journal
   |
   v
Grand livre
   |
   v
Balance
   |
   +--------------+--------------+
   |              |              |
   v              v              v
Résultat         Bilan        Cash Flow
   |              |              |
   +--------------+--------------+
                  |
                  v
               Controls
                  |
                  v
               Dashboard
```

---

# 74. Critères d’acceptation fonctionnels finaux

## FEC

```text
[ ] import du Petit dossier

[ ] import du Moyen dossier

[ ] import du Gros dossier

[ ] réimport du même fichier détecté

[ ] lignes sources consultables

[ ] erreurs d'import consultables
```

---

## Comptabilité

```text
[ ] une écriture déséquilibrée ne peut pas être postée

[ ] une écriture postée ne peut pas être modifiée

[ ] une extourne peut être générée

[ ] une période fermée bloque le posting
```

---

## Reporting

```text
[ ] journal cohérent

[ ] grand livre cohérent

[ ] balance débit = crédit

[ ] bilan équilibré

[ ] cash-flow réconcilié
```

---

## Référentiels

```text
[ ] recherche SYSCOHADA

[ ] recherche IFRS

[ ] mapping manuel d’un compte entreprise
```

---

## UX

```text
[ ] aucune action principale ne nécessite React

[ ] recherches dynamiques HTMX

[ ] pagination HTMX

[ ] formulaires d'écriture dynamiques

[ ] dashboard exploitable
```

---

# 75. Critères de performance MVP

Pour un FEC de taille comparable au Gros dossier :

```text
8 000 à 10 000 lignes
```

Objectifs :

```text
preview < 5 s

liste journal < 2 s

grand livre filtré < 2 s

balance < 2 s

dashboard < 2 s
```

Ces objectifs sont à mesurer en staging.

---

# 76. Optimisations possibles si nécessaires

```text
select_related

prefetch_related

database indexes

bulk_create

bulk_update

PostgreSQL window functions

server-side pagination

cache dashboard
```

Celery n'est ajouté au MVP que si l’import bloque réellement l’expérience utilisateur.

---

# 77. Index PostgreSQL prioritaires

```text
organization_id

posting_date

period_id

journal_id

account_id

status
```

Composites :

```text
(organization_id, posting_date)

(organization_id, account_id, posting_date)

(organization_id, period_id, status)
```

---

# 78. ADR à créer

Créer au minimum :

```text
ADR-001-MODULAR-MONOLITH.md

ADR-002-DJANGO-TEMPLATES-HTMX.md

ADR-003-POSTGRESQL.md

ADR-004-POSTED-ENTRY-IMMUTABILITY.md

ADR-005-CALCULATED-FINANCIAL-STATEMENTS.md

ADR-006-FEC-RAW-DATA-PRESERVATION.md
```

---

# 79. Documentation à maintenir

```text
README.md

ARCHITECTURE.md

ACCOUNTING_RULES.md

FEC_IMPORT_SPEC.md

RBAC_MATRIX.md

TEST_STRATEGY.md

DEPLOYMENT.md

RUNBOOK.md
```

---

# 80. Première arborescence de templates

```text
templates/
|
+-- base.html
|
+-- dashboard/
|   +-- index.html
|   +-- _kpis.html
|   +-- _charts.html
|
+-- accounts/
|   +-- list.html
|   +-- _table.html
|   +-- form.html
|
+-- entries/
|   +-- list.html
|   +-- form.html
|   +-- detail.html
|   +-- _line_form.html
|   +-- _totals.html
|
+-- imports/
|   +-- list.html
|   +-- upload.html
|   +-- preview.html
|   +-- _errors.html
|
+-- reports/
|   +-- journal.html
|   +-- ledger.html
|   +-- trial_balance.html
|   +-- income_statement.html
|   +-- balance_sheet.html
|   +-- cash_flow.html
|
+-- controls/
|   +-- index.html
|   +-- _results.html
|
+-- referentials/
    +-- accounts.html
    +-- mapping.html
```

---

# 81. Navigation principale MVP

```text
Dashboard

Comptabilité
    - Écritures
    - Journaux
    - Plan comptable

Imports
    - FEC

Reporting
    - Journal
    - Grand livre
    - Balance
    - Résultat
    - Bilan
    - Cash-flow

Contrôles

Référentiels
    - SYSCOHADA
    - IFRS
    - Mappings

Clôture

Administration
```

---

# 82. Stratégie de migration Excel → Django

Le développement doit être conduit par comparaison avec Excel.

Pour chaque fonctionnalité :

```text
1. identifier la règle Excel

2. formaliser la règle

3. écrire un test

4. implémenter le service Django

5. comparer avec Excel

6. valider

7. intégrer à l'UI
```

---

# 83. Ordre de développement recommandé

```text
Domain model

      |
      v

Accounting services

      |
      v

Tests

      |
      v

FEC import

      |
      v

Reporting

      |
      v

Controls

      |
      v

HTMX UI

      |
      v

Dashboard
```

Le dashboard ne doit pas être développé avant que les données sous-jacentes soient fiables.

---

# 84. Risques principaux

## Risque 1 — reproduire les feuilles Excel comme tables

Mitigation :

```text
journal source unique
+
services calculés
```

---

## Risque 2 — logique métier dans les Views

Mitigation :

```text
services
+
selectors
```

---

## Risque 3 — FEC importé sans traçabilité

Mitigation :

```text
original file
+
raw lines
+
line number
+
SHA256
```

---

## Risque 4 — différences Excel / Django

Mitigation :

```text
golden datasets
+
non-regression tests
```

---

## Risque 5 — frontend trop complexe trop tôt

Mitigation :

```text
Django Templates
+
HTMX
```

---

## Risque 6 — erreurs financières dues aux floats

Mitigation :

```text
Decimal
```

partout.

---

# 85. Backlog MVP — Epics

```text
EPIC-01 Foundation

EPIC-02 Organizations & RBAC

EPIC-03 Accounting Core

EPIC-04 Journal Entry Workflow

EPIC-05 FEC Import

EPIC-06 Ledger & Trial Balance

EPIC-07 Financial Statements

EPIC-08 Accounting Controls

EPIC-09 Closing

EPIC-10 SYSCOHADA / IFRS

EPIC-11 Account Mapping

EPIC-12 Dashboard

EPIC-13 Audit

EPIC-14 Export

EPIC-15 Production Readiness
```

---

# 86. Backlog MVP — User Stories majeures

## US-001

En tant qu’administrateur, je veux créer une organisation afin de séparer les comptabilités.

## US-002

En tant que comptable, je veux créer un exercice comptable afin de saisir des écritures sur une période définie.

## US-003

En tant que comptable, je veux gérer un plan comptable afin de rattacher chaque écriture à un compte.

## US-004

En tant que comptable, je veux saisir une écriture équilibrée afin de comptabiliser une opération.

## US-005

En tant que reviewer, je veux poster une écriture validée afin qu’elle devienne définitive.

## US-006

En tant que reviewer, je veux extourner une écriture afin de corriger une erreur sans modifier l’historique.

## US-007

En tant que comptable, je veux importer un FEC afin de reconstruire rapidement une comptabilité existante.

## US-008

En tant que comptable, je veux voir les erreurs d’un FEC avant import afin de les comprendre.

## US-009

En tant qu’analyste, je veux consulter le grand livre afin d’analyser les mouvements d’un compte.

## US-010

En tant qu’analyste, je veux consulter une balance afin de vérifier l’équilibre comptable.

## US-011

En tant qu’analyste, je veux consulter le compte de résultat afin d’évaluer la performance.

## US-012

En tant qu’analyste, je veux consulter le bilan afin d’évaluer la structure financière.

## US-013

En tant qu’analyste, je veux consulter les flux de trésorerie afin d’évaluer la génération de cash.

## US-014

En tant qu’auditeur, je veux consulter les contrôles afin d’identifier les anomalies.

## US-015

En tant qu’analyste, je veux visualiser un dashboard afin de piloter rapidement l’activité.

## US-016

En tant que comptable, je veux mapper un compte entreprise vers SYSCOHADA et IFRS afin de préparer le reporting normalisé.

---

# 87. Priorités MoSCoW

## MUST

```text
Organization

FiscalYear

AccountingPeriod

Account

Journal

JournalEntry

JournalLine

Posting

Reversal

FEC Import

Journal report

General Ledger

Trial Balance

Income Statement

Balance Sheet

Cash Flow

Controls

Audit trail

Basic Dashboard
```

## SHOULD

```text
SYSCOHADA

IFRS

Manual mapping

Closing

Exports
```

## COULD

```text
Celery

advanced charts

advanced drill-down

custom report builder
```

## WON'T — MVP

```text
React

AI mapping

RAG

mobile app

bank connectors

OCR
```

---

# 88. Release MVP

Version recommandée :

```text
v0.1.0
```

Statut :

```text
MVP / Beta
```

Environnements :

```text
local

test

staging

production
```

---

# 89. Résultat attendu

À la fin du MVP, le classeur Excel n’est plus le moteur d’exécution principal.

Il devient :

```text
référence fonctionnelle

+

golden dataset

+

support de comparaison

+

format d'export éventuel
```

L’application Django devient :

```text
source opérationnelle

+

moteur comptable

+

moteur FEC

+

moteur de reporting

+

moteur de contrôles

+

interface utilisateur
```

---

# 90. Vision d’évolution après MVP

Une fois le MVP stabilisé :

```text
Django Templates + HTMX
          |
          v
Accounting Engine stable
          |
          +-------------------+
          |                   |
          v                   v
      DRF API             Celery
          |
          v
React / Apps tierces
```

La décision d’introduire React doit être prise uniquement lorsqu’un besoin réel le justifie :

```text
data grids massives

drill-down complexes

drag-and-drop

workflows très interactifs

visualisations avancées
```

---

# Conclusion

Le MVP doit privilégier la fiabilité du moteur comptable à la sophistication du frontend.

L’ordre de priorité est :

```text
Exactitude comptable
        |
        v
Traçabilité
        |
        v
Import FEC
        |
        v
Reporting
        |
        v
Contrôles
        |
        v
UX HTMX
        |
        v
Dashboard
```

Le choix :

```text
Django Templates
+
HTMX
```

permet d’obtenir rapidement une application cohérente avec le prototype Excel, tout en conservant une architecture suffisamment propre pour évoluer ensuite vers DRF, Celery ou React sans réécrire le moteur métier.
