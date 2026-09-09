# Sprint 3 — HTMX, workflow comptable, extourne et audit automatique

## Statut

Sprint 3 implémenté sur la base :

```text
Sprint 0 — Bootstrap
Sprint 1 — Organizations & Periods
Sprint 2 — Accounting Core
```

Le Sprint 3 transforme la saisie d'écritures en un véritable workflow comptable contrôlé.

---

## 1. Saisie dynamique HTMX

L'écran :

```text
/accounting/entries/new/
```

permet maintenant de :

```text
ajouter une ligne
retirer une ligne
modifier Débit / Crédit
recalculer les totaux sans recharger la page
```

Flux :

```text
JournalEntryHeader
        |
        v
JournalLine 1
JournalLine 2
JournalLine N
        |
        v
HTMX totals endpoint
        |
        v
Total Débit
Total Crédit
Écart
Statut d'équilibre
```

Endpoints HTMX :

```text
GET  /accounting/entries/line-form/
POST /accounting/entries/line-form/<index>/remove/
POST /accounting/entries/totals/
```

Le `TOTAL_FORMS` du formset est maintenu lors de l'ajout de lignes.

La suppression conserve un tombstone `DELETE=on`, afin que le formset Django puisse reconstruire correctement les indices lors du submit final.

---

## 2. Totaux temps réel

Chaque modification d'un champ :

```text
debit
credit
```

déclenche un calcul HTMX différé.

Le fragment retourné affiche :

```text
Lignes actives
Total débit
Total crédit
Écart
ÉQUILIBRÉ / À équilibrer
```

Une écriture n'est considérée comme équilibrée que si :

```text
nombre de lignes actives >= 2

ET

Total Débit > 0

ET

Total Débit = Total Crédit
```

---

## 3. Workflow strict

Le workflow devient :

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

Il n'est plus possible de passer directement :

```text
DRAFT -> POSTED
```

Le service de posting exige :

```text
status == VALIDATED
```

---

## 4. Permissions

### Création / modification de brouillons

Autorisée pour :

```text
ADMIN
ACCOUNTANT
REVIEWER
```

### Validation / posting / extourne

Autorisée uniquement pour :

```text
ADMIN
REVIEWER
```

### Audit / lecture

Les rôles disposant d'un accès à l'organisation peuvent consulter les écrans en lecture selon leur membership.

---

## 5. Validation

Bouton disponible pour une écriture :

```text
DRAFT
```

Route :

```text
POST /accounting/entries/<uuid>/validate/
```

Contrôles exécutés :

```text
période ouverte
date dans la période
minimum deux lignes
comptes cohérents avec l'organisation
aucune ligne nulle
aucune ligne débit + crédit
Total Débit = Total Crédit
montant total non nul
```

Résultat :

```text
DRAFT -> VALIDATED
```

avec :

```text
validated_by
validated_at
```

---

## 6. Posting

Route :

```text
POST /accounting/entries/<uuid>/post/
```

Précondition :

```text
status == VALIDATED
```

Résultat :

```text
VALIDATED -> POSTED
```

avec :

```text
posted_by
posted_at
```

Une écriture `POSTED` ne peut plus être modifiée depuis l'interface.

---

## 7. Immutabilité

Les routes d'édition n'acceptent que :

```text
DRAFT
```

Les écritures :

```text
POSTED
REVERSED
```

sont considérées comme immuables.

L'admin Django protège également ces objets contre les modifications / suppressions accidentelles.

Une correction doit utiliser :

```text
REVERSAL
```

---

## 8. Extourne

Route :

```text
GET/POST /accounting/entries/<uuid>/reverse/
```

L'utilisateur sélectionne :

```text
période ouverte
date d'extourne
motif
```

Le moteur crée automatiquement une nouvelle écriture :

```text
REV-<entry_number>
```

avec inversion :

```text
Débit original  -> Crédit extourne
Crédit original -> Débit extourne
```

La nouvelle écriture suit automatiquement :

```text
DRAFT
-> VALIDATED
-> POSTED
```

L'écriture originale devient :

```text
REVERSED
```

La relation :

```text
reversal.reversal_of
```

conserve le lien entre les deux écritures.

---

## 9. Audit automatique

Actions enregistrées :

```text
ENTRY_CREATE
ENTRY_UPDATE
ENTRY_VALIDATE
ENTRY_POST
ENTRY_REVERSE
```

Chaque événement contient :

```text
organization
actor
action
entity_type
entity_id
before
after
metadata
source_ip
timestamp
```

Pour les écritures, les snapshots `before` / `after` comprennent également les lignes comptables.

---

## 10. Audit trail UI

Route :

```text
/audit/
```

Fonctionnalités :

```text
scoping organisation
recherche HTMX
filtre action
pagination
acteur
type d'objet
identifiant
contexte / motif
```

---

## 11. Concurrence

Les transitions critiques utilisent :

```text
transaction.atomic
+
select_for_update
```

pour éviter :

```text
double validation
double posting
double extourne
```

sur la même écriture en concurrence.

---

## 12. Dashboard

Le Dashboard affiche maintenant :

```text
nombre de comptes
nombre de journaux
nombre d'écritures
nombre d'événements d'audit
```

ainsi que la répartition :

```text
DRAFT
VALIDATED
POSTED
REVERSED
```

---

## 13. Tests du Sprint 3

Le fichier :

```text
apps/accounting/tests/test_sprint3_workflow.py
```

couvre notamment :

```text
DRAFT -> VALIDATED -> POSTED

interdiction DRAFT -> POSTED

extourne et inversion Débit / Crédit

audit automatique

HTMX totals

HTMX add line

HTMX remove line

RBAC validation

RBAC posting

immutabilité de l'édition après posting
```

---

## 14. Démarrage

```bash
cp .env.example .env
docker compose up --build
```

Puis :

```bash
docker compose exec web python manage.py bootstrap_demo
```

Accès :

```text
http://localhost:8000/
http://localhost:8000/accounting/entries/
http://localhost:8000/audit/
http://localhost:8000/admin/
http://localhost:8000/health/
```

Compte de développement :

```text
admin
admin1234
```

À modifier hors environnement local.

---

## 15. Vérifications

Dans Docker :

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py check
docker compose exec web pytest
docker compose exec web ruff check .
```

Le pipeline GitHub Actions exécute également :

```text
ruff
makemigrations --check --dry-run
django check
pytest + coverage
```

---

## 16. Frontière du Sprint 3

Le Sprint 3 termine le workflow manuel d'écriture.

Il ne couvre pas encore :

```text
import FEC end-to-end
mapping automatique des comptes FEC
journal / grand livre finalisés
balance calculée complète
états financiers dynamiques
moteur de contrôles consolidé
```

Ces sujets appartiennent aux sprints suivants.

---

## 17. Suite recommandée — Sprint 4

```text
FEC Upload
        |
        v
Parsing
        |
        v
Raw Lines
        |
        v
Preview
        |
        v
Validation
        |
        v
Mapping comptes / journaux
        |
        v
Normalisation
        |
        v
JournalEntry / JournalLine
        |
        v
Import transactionnel
```

Le FEC doit conserver :

```text
fichier original
SHA-256
numéro de ligne source
valeurs brutes
erreurs
warnings
rapport d'import
```
