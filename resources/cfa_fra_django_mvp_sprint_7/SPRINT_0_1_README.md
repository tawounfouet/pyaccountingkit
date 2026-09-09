# Sprint 0 / Sprint 1 — Exécutable

## Ce qui est terminé

### Sprint 0

- projet Django ;
- settings local / test / production ;
- PostgreSQL ;
- Docker / Docker Compose ;
- entrypoint avec attente PostgreSQL ;
- migrations automatiques au démarrage ;
- collectstatic ;
- endpoint `/health/` ;
- Django Templates ;
- HTMX ;
- Bootstrap ;
- Chart.js ;
- pytest / ruff / mypy ;
- CI GitHub Actions.

### Sprint 1

- custom `User` ;
- `Organization` ;
- `OrganizationMembership` ;
- RBAC initial ;
- organisation active en session ;
- switch d’organisation dans la navbar ;
- `FiscalYear` ;
- `AccountingPeriod` ;
- `AccountingSettings` ;
- création d'organisation ;
- création d'exercice ;
- génération automatique des périodes mensuelles ;
- commande `bootstrap_demo` ;
- tests de services et de views.

## Démarrage

```bash
cp .env.example .env
docker compose up --build
```

Le container web exécute automatiquement :

```text
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Puis :

```bash
docker compose exec web python manage.py bootstrap_demo
```

Identifiants de démo par défaut :

```text
admin
admin1234
```

À changer immédiatement hors environnement de développement.

Ouvrir :

```text
http://localhost:8000/
http://localhost:8000/admin/
http://localhost:8000/health/
```

## Tests

```bash
docker compose exec web pytest
```

Les tests utilisent SQLite en mémoire afin de rester rapides et indépendants du PostgreSQL de développement.

## Suite

Sprint 2 :

```text
ChartOfAccounts
Account
Journal
JournalEntry
JournalLine
```

Sprint 3 :

```text
Saisie HTMX
Validation
Posting
Extourne
Audit
```
