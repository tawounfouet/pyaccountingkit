# Architecture du starter

## Source de vérité

```text
JournalEntry
+
JournalLine
+
Account
+
AccountingPeriod
```

## Projections

```text
Journal
Grand livre
Balance
Compte de résultat
Bilan
Cash-flow
```

## Frontend MVP

```text
Django Templates
+
HTMX
+
Chart.js
```

## Règle de mutation

Les écritures doivent passer par les services de `apps/accounting/services.py`.

Les views ne doivent pas contenir de logique comptable.
