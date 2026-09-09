# Sprint 5 — Ledger & Trial Balance

## Statut

Sprint 5 implémenté sur la base des Sprints 0 à 4.

Le pipeline comptable devient :

```text
FEC / saisie manuelle
        ↓
JournalEntry / JournalLine
        ↓
POSTED / REVERSED
        ↓
Journal comptable
        ↓
Grand livre
        ↓
Soldes cumulés SQL
        ↓
Balance avant ajustements
Balance ajustée
Balance post-clôture
        ↓
Drill-down jusqu'à l'écriture source
```

## 1. Journal comptable finalisé

Route :

```text
/reporting/journal/
```

La vue travaille exclusivement sur les écritures :

```text
POSTED
REVERSED
```

Une écriture `REVERSED` reste volontairement incluse : l'écriture originale et son écriture d'extourne se compensent dans les agrégats.

Filtres disponibles :

```text
exercice
date début
date fin
journal
type d'écriture
recherche texte
```

Chaque ligne permet un drill-down vers :

```text
/accounting/entries/<uuid>/
```

Le journal affiche également :

```text
total débit
total crédit
source MANUAL / FEC / REVERSAL
```

## 2. Grand livre finalisé

Route :

```text
/reporting/general-ledger/
```

Filtres :

```text
exercice
compte
date début
date fin
périmètre comptable
```

Le grand livre calcule :

```text
solde d'ouverture
mouvements débit
mouvements crédit
solde cumulé ligne par ligne
solde final
```

## 3. Soldes cumulés PostgreSQL

Le cumul n'est pas recalculé en JavaScript ou dans le template.

Il est construit avec l'ORM Django via :

```text
Window
+
Sum
+
ORDER BY posting_date, created_at, entry_id, line_number
```

Conceptuellement :

```sql
SUM(debit - credit)
OVER (
    PARTITION BY account_id
    ORDER BY posting_date, created_at, entry_id, line_number
)
```

Le solde d'ouverture est calculé en SQL avant la date de début puis ajouté au cumul de période.

Cela permet une pagination sans perdre la cohérence du solde courant.

## 4. Convention de solde

Le moteur conserve en interne un solde signé :

```text
signed_balance = debit - credit
```

Puis présente :

```text
signed_balance >= 0
    → solde débiteur

signed_balance < 0
    → solde créditeur = abs(signed_balance)
```

## 5. Balance avant ajustements

Valeur :

```text
BEFORE_ADJUSTMENTS
```

Types d'écritures inclus :

```text
OPENING
NORMAL
REVERSAL
```

Types exclus :

```text
ADJUSTING
CLOSING
```

Cette vue représente la balance avant écritures d'ajustement.

> Note MVP : depuis le Sprint 4, les écritures FEC du journal `JOD` sont normalisées en `ADJUSTING`. Elles sont donc exclues de `BEFORE_ADJUSTMENTS` et incluses dans `ADJUSTED`. Cette convention devra être affinée si un système source utilise `JOD` pour des opérations diverses non-ajustantes.

## 6. Balance ajustée

Valeur :

```text
ADJUSTED
```

Types inclus :

```text
OPENING
NORMAL
ADJUSTING
REVERSAL
```

Type exclu :

```text
CLOSING
```

C'est le périmètre destiné à alimenter les états financiers avant clôture des comptes temporaires.

## 7. Balance post-clôture

Valeur :

```text
POST_CLOSING
```

Types inclus :

```text
OPENING
NORMAL
ADJUSTING
CLOSING
REVERSAL
```

Par défaut, les comptes dont le solde final est nul sont masqués.

L'option :

```text
Afficher les comptes à solde nul
```

permet de les réafficher, notamment pour vérifier la fermeture des comptes de charges et produits.

## 8. Calcul de la balance

Pour chaque compte :

```text
Mouvements Débit = SUM(JournalLine.debit)
Mouvements Crédit = SUM(JournalLine.credit)

Solde signé =
Mouvements Débit - Mouvements Crédit

Solde débiteur =
MAX(Solde signé, 0)

Solde créditeur =
MAX(-Solde signé, 0)
```

Ces agrégats sont calculés côté base de données.

## 9. Contrôle d'équilibre

La vue contrôle :

```text
SUM(soldes débiteurs)
=
SUM(soldes créditeurs)
```

et affiche explicitement :

```text
Balance équilibrée
```

ou l'écart résiduel.

## 10. Drill-down

Depuis la balance :

```text
Compte
  ↓
Grand livre du compte
  ↓
Mouvement
  ↓
JournalEntry source
  ↓
JournalLine
```

Le lien conserve :

```text
exercice
date d'arrêté
variant de balance
compte
```

Il est donc possible de remonter d'un total agrégé jusqu'à l'écriture comptable d'origine.

## 11. Source de vérité

Les trois rapports reposent sur :

```text
JournalEntry
JournalLine
```

et jamais directement sur :

```text
FECRawLine
Excel
JSON intermédiaire
```

Le FEC du Sprint 4 alimente d'abord la source comptable canonique.

## 12. Performance

Le Sprint 5 ajoute des index :

```text
JournalEntry(
    organization,
    status,
    entry_type,
    posting_date
)

JournalLine(
    entry,
    account,
    line_number
)
```

Ils complètent les index déjà présents sur :

```text
organization + posting_date
organization + status + posting_date
account + entry
```

## 13. Pagination

Journal :

```text
100 lignes / page
```

Grand livre :

```text
100 lignes / page
```

Balance :

```text
100 comptes / page
```

Le calcul fenêtre du grand livre est effectué avant la pagination SQL, afin que le solde cumulé reste correct sur les pages suivantes.

## 14. Tests Sprint 5

Le fichier :

```text
apps/reporting/tests/test_sprint5_ledger_trial_balance.py
```

couvre notamment :

```text
exclusion des DRAFT du journal
égalité débit / crédit du journal
solde d'ouverture du grand livre
Window SUM du grand livre
solde cumulé
balance avant ajustements
balance ajustée
balance post-clôture
masquage des comptes temporaires soldés
affichage optionnel des comptes à solde nul
drill-down Journal → écriture
drill-down Balance → Grand livre
drill-down Grand livre → écriture
```

## 15. Exemple de différence entre les trois balances

Avec :

```text
Opening:
Cash      Dr 1 000
Capital   Cr 1 000

Normal:
Rent      Dr   200
Cash      Cr   200

Adjusting:
Rent      Dr    50
Accrued   Cr    50

Closing:
Capital   Dr   250
Rent      Cr   250
```

### Avant ajustements

```text
Cash       Dr 800
Rent       Dr 200
Capital    Cr 1 000
```

### Ajustée

```text
Cash       Dr 800
Rent       Dr 250
Capital    Cr 1 000
Accrued    Cr 50
```

### Post-clôture

```text
Cash       Dr 800
Capital    Cr 750
Accrued    Cr 50
Rent       0
```

Le compte `Rent` disparaît par défaut de la balance post-clôture.

## 16. Démarrage

```bash
cp .env.example .env
docker compose up --build
docker compose exec web python manage.py bootstrap_demo
```

Puis :

```text
http://localhost:8000/reporting/journal/
http://localhost:8000/reporting/general-ledger/
http://localhost:8000/reporting/trial-balance/
```

## 17. Vérifications Docker

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py check
docker compose exec web pytest apps/reporting
docker compose exec web ruff check .
```

## 18. Frontière du Sprint 5

Le Sprint 5 fournit la couche comptable agrégée fiable :

```text
Journal
Grand livre
Balance
```

La suite logique devient :

```text
Sprint 6 — Financial Statements Engine
```

avec :

```text
Balance ajustée
        ↓
AccountMapping
        ↓
StatementDefinition / StatementLine
        ↓
Compte de résultat
Bilan
Flux de trésorerie
        ↓
comparatifs / ratios / drill-down
```
