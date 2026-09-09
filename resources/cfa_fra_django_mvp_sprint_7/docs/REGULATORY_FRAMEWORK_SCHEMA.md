# Regulatory Framework JSON Schema — Sprint 7

Sprint 7 accepte désormais deux formats de seed.

## 1. Format historique

Une liste JSON de comptes :

```json
[
  {
    "code": "101",
    "name": "Capital"
  }
]
```

Ce format reste compatible avec `seed_syscohada` et `seed_ifrs`.

## 2. Format complet Sprint 7

```json
{
  "framework": {
    "code": "REG_CODE",
    "name": "Nom du référentiel",
    "version": "2026",
    "description": "Description",
    "source_url": "https://source-officielle.example",
    "is_current": true
  },
  "accounts": [],
  "statements": [
    {
      "code": "REG_BS",
      "name": "Bilan réglementaire",
      "statement_type": "BALANCE_SHEET",
      "lines": [
        {
          "code": "REG_ASSETS",
          "label": "Total actif",
          "order": 100,
          "sign": 1,
          "is_total": true,
          "is_required": false,
          "standard_reference": "Référence officielle",
          "metadata": {
            "role": "total_assets"
          }
        },
        {
          "code": "REG_CURRENT_ASSETS",
          "label": "Actifs courants",
          "parent_code": "REG_ASSETS",
          "order": 10,
          "sign": 1,
          "is_total": false,
          "is_required": true,
          "standard_reference": "Référence officielle",
          "metadata": {
            "role": "current_assets",
            "source_codes": ["BS_CURRENT_ASSETS"]
          }
        }
      ]
    }
  ]
}
```

## Types d'états supportés

```text
BALANCE_SHEET
INCOME_STATEMENT
CASH_FLOW
EQUITY_CHANGES
```

Le moteur Sprint 7 exporte actuellement :

```text
BALANCE_SHEET
INCOME_STATEMENT
CASH_FLOW
```

## Métadonnées utiles au mapping

Les clés suivantes sont reconnues :

```text
metadata.source_code
metadata.source_codes[]
metadata.role
```

Priorité de l'auto-mapping :

```text
1. code cible = code source
2. metadata.source_code
3. metadata.source_codes
4. metadata.role
5. égalité exacte des libellés normalisés
```

Aucune similarité floue n'est appliquée automatiquement.

## Roles reconnus

Exemples :

```text
revenue
cost_of_sales
external_services
taxes
personnel_expenses
depreciation
finance_expenses
other_expenses
income_tax

current_assets
noncurrent_assets
current_liabilities
noncurrent_liabilities
equity
current_result

opening_cash
operating_cash_flow
investing_cash_flow
financing_cash_flow
unclassified_cash_flow
ending_cash
cash_reconciliation_gap

total_assets
total_liabilities_equity
```

Les rôles `total_assets` et `total_liabilities_equity` permettent le contrôle automatique de l'équation du bilan.

Le rôle `cash_reconciliation_gap` permet le contrôle automatique du rapprochement de trésorerie.

## Important

Ce schéma est un **format technique d'ingestion**.

Il ne contient pas, par lui-même, la nomenclature officielle SYSCOHADA ou IFRS.

Les lignes, libellés, références et règles réglementaires doivent être alimentés à partir d'une source officielle ou validée par l'organisation.
