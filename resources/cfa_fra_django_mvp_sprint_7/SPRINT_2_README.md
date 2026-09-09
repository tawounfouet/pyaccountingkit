# Sprint 2 — Accounting Core

## Statut

Sprint 2 implémenté sur la base exécutable Sprint 0 / Sprint 1.

## Périmètre livré

```text
ChartOfAccounts
Account
Journal
Counterparty
CostCenter
JournalEntry
JournalLine
```

Le Sprint 2 rend ces objets réellement utilisables dans l'application.

## 1. Initialisation automatique

Toute nouvelle organisation reçoit :

```text
Plan comptable ENTITY
+
JAN   À-nouveaux
JACH  Achats
JVTE  Ventes
BNQ   Banque
CAI   Caisse
PAIE  Paie
TAX   Fiscal
JOD   Opérations diverses
```

Le bootstrap est idempotent.

Commande manuelle :

```bash
python manage.py bootstrap_accounting_core "CFA FRA Demo"
```

## 2. Plans comptables

Routes :

```text
/accounting/charts/
/accounting/charts/new/
/accounting/charts/<uuid>/
```

Fonctionnalités :

- création ;
- plan par défaut ;
- compte du nombre de comptes ;
- consultation des comptes du plan.

## 3. Comptes

Routes :

```text
/accounting/accounts/
/accounting/accounts/new/
/accounting/accounts/<uuid>/edit/
```

Fonctionnalités :

- CRUD de base ;
- recherche HTMX ;
- filtres par plan, type et statut ;
- hiérarchie parent/enfant ;
- validation d'appartenance organisation / plan ;
- pagination.

## 4. Journaux

Routes :

```text
/accounting/journals/
/accounting/journals/new/
/accounting/journals/<uuid>/edit/
```

Fonctionnalités :

- CRUD de base ;
- recherche HTMX ;
- filtrage type / statut ;
- scoping organisation.

## 5. Écritures et lignes

Routes :

```text
/accounting/entries/
/accounting/entries/new/
/accounting/entries/<uuid>/
/accounting/entries/<uuid>/edit/
```

Le Sprint 2 fournit une première saisie serveur classique :

```text
Entête
+
minimum 2 lignes
```

Le résultat est enregistré en :

```text
DRAFT
```

La saisie dynamique HTMX, la validation workflow, le posting, l'extourne UI et l'audit automatique restent le périmètre du Sprint 3.

## 6. Règles de domaine renforcées

- un compte appartient au même plan et à la même organisation que son parent ;
- un journal d'une écriture appartient à la même organisation ;
- une période appartient à la même organisation ;
- la date de comptabilisation doit être comprise dans la période ;
- un compte d'une ligne appartient à la même organisation que l'écriture ;
- un tiers et un centre de coûts doivent appartenir à la même organisation ;
- une ligne ne peut pas avoir débit et crédit simultanément ;
- une ligne ne peut pas être nulle.

## 7. Architecture

```text
Views
   |
   v
Forms
   |
   v
Services
   |
   v
Models

Selectors
   ^
   |
Views
```

Les listes et recherches passent par les selectors.

Les mutations importantes de brouillon passent par les services.

## 8. HTMX livré dans le Sprint 2

HTMX est actif sur :

```text
recherche comptes
filtres comptes
pagination comptes
recherche journaux
filtres journaux
recherche écritures
filtres écritures
```

La manipulation dynamique des lignes d'écriture sera ajoutée au Sprint 3.

## 9. Tests ajoutés

- bootstrap idempotent ;
- isolation entre organisations ;
- validation de hiérarchie de comptes ;
- création d'une écriture brouillon équilibrée ;
- validation date / période ;
- scoping des listes ;
- création de journal via UI.

## 10. Démarrage

```bash
cp .env.example .env
docker compose up --build
docker compose exec web python manage.py bootstrap_demo
```

Puis :

```text
http://localhost:8000/
```

Le compte de démonstration créé par défaut reste :

```text
admin
admin1234
```

à utiliser uniquement en développement.

## 11. Suite — Sprint 3

```text
Saisie HTMX des lignes

Calcul temps réel Débit / Crédit / Écart

DRAFT → VALIDATED → POSTED

Extourne

Immutabilité UI des écritures postées

AuditEvent automatique

RBAC posting / reversal
```
