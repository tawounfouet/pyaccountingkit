# CFA FRA — Django MVP

Starter Django/HTMX pour transformer le modèle Excel **CFA FRA Cycle Comptable** en application web.

## Statut

**Sprint 0 / Sprint 1 / Sprint 2 / Sprint 3 / Sprint 4 / Sprint 5 / Sprint 6 / Sprint 7 implémentés.**

Le projet démarre avec Docker, applique les migrations, expose un endpoint de santé et fournit un parcours fonctionnel :

```text
Login
→ création organisation
→ organisation active
→ création exercice
→ génération périodes mensuelles
```

Voir `SPRINT_0_1_README.md`, `SPRINT_2_README.md`, `SPRINT_3_README.md`, `SPRINT_4_README.md`, `SPRINT_5_README.md`, `SPRINT_6_README.md` et `SPRINT_7_README.md`.

## Objectifs du starter

Le projet fournit la base technique et métier pour :

- gérer plusieurs organisations ;
- gérer exercices et périodes comptables ;
- gérer plans comptables, comptes et journaux ;
- saisir des écritures en partie double ;
- valider, poster et extourner des écritures ;
- importer un FEC en conservant les lignes brutes ;
- calculer journal, grand livre et balance ;
- structurer les états financiers ;
- exécuter des contrôles comptables ;
- gérer la clôture ;
- charger des référentiels SYSCOHADA / IFRS ;
- mapper les comptes d'une entité vers des référentiels ;
- alimenter un dashboard Django Templates + HTMX ;
- conserver un audit trail.

## Architecture

```text
Browser
  |
  | HTML + HTMX
  v
Django Views
  |
  v
Services métier
  |
  +--> Selectors / Reporting
  |
  v
Django ORM
  |
  v
PostgreSQL
```

Le modèle comptable canonique repose principalement sur :

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

Le grand livre, la balance et les états financiers sont des projections calculées : ils ne constituent pas la source de vérité.

## Apps

```text
users
organizations
accounting
imports
reporting
financial_statements
controls
closing
referentials
analytics
audit
exports
scenarios
```

## Démarrage local

1. Copier les variables d'environnement :

```bash
cp .env.example .env
```

2. Démarrer PostgreSQL + Django :

```bash
docker compose up --build
```

3. Dans un autre terminal :

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

4. Ouvrir :

```text
http://localhost:8000/
http://localhost:8000/admin/
```

## Commandes utiles

```bash
make up
make migrate
make superuser
make test
make lint
make format
make check
```

## Référentiels

Deux commandes de seed sont préparées :

```bash
python manage.py seed_syscohada path/to/syscohada.json
python manage.py seed_ifrs path/to/ifrs.json
```

Le JSON attendu est documenté dans `apps/referentials/management/commands/_seed_framework.py`.

## Principes comptables implémentés dans le starter

- `Decimal`, jamais `float`, pour les montants ;
- une écriture `POSTED` est immuable par convention de service ;
- une correction passe par une extourne ;
- `Total débit = Total crédit` avant posting ;
- une période fermée bloque le posting ;
- les imports FEC conservent le fichier original et les lignes brutes ;
- les états financiers doivent être calculés depuis les lignes comptables ;
- les référentiels comptables sont distincts du plan comptable réel d'une organisation.

## Documents

Voir `docs/` pour le document de conception et le plan d'implémentation MVP.


## Démo

```bash
docker compose exec web python manage.py bootstrap_demo
```


## Workflow Sprint 3

```text
DRAFT
  -> VALIDATED
  -> POSTED
  -> REVERSED
```

La saisie des lignes est désormais dynamique avec HTMX et les transitions critiques sont auditées automatiquement.


## FEC Sprint 4

```text
Upload
→ Parsing
→ Raw Lines
→ Controls
→ Mapping
→ Normalization
→ Transactional JournalEntry / JournalLine import
```

Le pipeline est accessible depuis `/imports/fec/`.


## Ledger Sprint 5

```text
POSTED JournalLine
→ Journal
→ General Ledger + SQL Window running balance
→ Trial Balance
→ BEFORE_ADJUSTMENTS / ADJUSTED / POST_CLOSING
→ source drill-down
```


## Financial Statements Sprint 6

```text
Adjusted accounting data
→ account-to-statement mapping
→ Income Statement
→ Balance Sheet
→ Cash Flow
→ Ratios
→ drill-down
```

Entrée UI : `/statements/`.


## Regulatory Mapping Sprint 7

```text
CFA_FRA_MVP statements
→ regulatory line mapping
→ SYSCOHADA / IFRS / custom target
→ preview & controls
→ snapshot
→ XLSX / PDF / CSV / JSON
```

Entrées UI :

```text
/statements/regulatory/
/exports/
```
