# Sprint 6 — Financial Statements Engine

## Statut

Sprint 6 implémenté sur la base des Sprints 0 à 5.

Le pipeline devient :

```text
JournalEntry / JournalLine POSTED
        ↓
Grand livre / Balance ajustée
        ↓
Mapping compte → rubrique d'état financier
        ↓
StatementDefinition / StatementLine
        ↓
Compte de résultat
Bilan
Flux de trésorerie
        ↓
Ratios
        ↓
Drill-down vers le Grand livre puis l'écriture source
```

---

## 1. Nouveau module

Application Django :

```text
apps/financial_statements/
```

Elle contient :

```text
models.py
forms.py
services.py
views.py
urls.py
admin.py
management/commands/
tests/
```

Route racine :

```text
/statements/
```

---

## 2. Configuration du moteur

Le modèle :

```text
FinancialStatementConfiguration
```

est lié 1:1 à une organisation.

Il conserve :

```text
framework_version
comparative_enabled
cash_account_prefixes
infer_cash_flow_categories
is_active
```

Par défaut :

```text
framework = CFA_FRA_MVP
version = 1.0
cash_account_prefixes = ["5"]
comparatifs N-1 = activés
inférence des flux = activée
```

Le framework `CFA_FRA_MVP` est explicitement un modèle interne de présentation.

Il ne remplace pas un format réglementaire SYSCOHADA ou IFRS.

---

## 3. StatementDefinition / StatementLine

Le Sprint 6 exploite les modèles de référentiel déjà présents :

```text
AccountingFramework
FrameworkVersion
StatementDefinition
StatementLine
```

Trois définitions sont bootstrapées :

```text
CFA_FRA_IS  → Compte de résultat
CFA_FRA_BS  → Bilan
CFA_FRA_CF  → Tableau des flux de trésorerie
```

---

## 4. Mapping compte → rubrique

Nouveau modèle :

```text
StatementAccountMapping
```

Relation :

```text
Account
   ↓
StatementAccountMapping
   ↓
StatementLine
```

Champs principaux :

```text
account
statement_line
balance_multiplier
mapping_type
confidence
validated_by
validated_at
notes
```

Les types de mapping sont :

```text
MANUAL
RULE
SUGGESTED
```

`StatementAccountMapping` est une couche de **présentation des états financiers**. Elle ne remplace pas le modèle existant `AccountMapping` qui relie un compte de l'entité à un `FrameworkAccount` de référentiel. Les deux couches pourront être reliées au Sprint réglementaire suivant.

---

## 5. Auto-mapping

Route :

```text
POST /statements/mappings/auto/
```

Le moteur conserve les mappings `MANUAL` et reconstruit les mappings automatiques.

Les principales règles du MVP sont :

```text
ASSET
  → actif courant / non courant

LIABILITY
  → passif courant / non courant

EQUITY
  → capitaux propres

REVENUE
  → produits

EXPENSE
  → catégorie de charge
```

Pour les charges, des sous-catégories sont inférées à partir des codes et libellés :

```text
60 / 61 → achats et coût des ventes
62 / 63 → services extérieurs
64      → impôts et taxes
66      → personnel
68      → amortissements / provisions
67      → charges financières
69      → impôt sur le résultat
autres  → autres charges
```

Cette classification est une aide de migration et doit être validée avant usage normatif.

---

## 6. Mapping manuel HTMX

Route :

```text
/statements/mappings/
```

Chaque compte peut être associé à une rubrique sans rechargement complet de page.

Un mapping manuel remplace les mappings automatiques du compte pour la version active.

Les mappings manuels sont ensuite préservés lors d'un nouvel auto-mapping.

---

## 7. Compte de résultat

Route :

```text
/statements/income-statement/
```

Périmètre comptable :

```text
NORMAL
ADJUSTING
REVERSAL
```

Sont exclus :

```text
OPENING
CLOSING
```

Cela évite de faire remonter les à-nouveaux dans le résultat de période et évite le double comptage après clôture.

### Lignes du modèle

```text
Produits / chiffre d'affaires

Achats et coût des ventes
Services extérieurs
Impôts et taxes
Charges de personnel
Dotations
Charges financières
Autres charges
Impôt sur le résultat

Résultat net
```

Le résultat net est calculé par hiérarchie :

```text
Produits
-
Charges
=
Résultat net
```

---

## 8. Bilan

Route :

```text
/statements/balance-sheet/
```

Périmètre :

```text
OPENING
NORMAL
ADJUSTING
REVERSAL
```

Les écritures `CLOSING` sont exclues.

Le bilan est donc calculé avant transfert du résultat vers les capitaux propres.

Pour préserver l'équation comptable, le moteur ajoute une ligne synthétique :

```text
BS_CURRENT_RESULT
=
Résultat net du compte de résultat
```

Structure :

```text
Actifs courants
Actifs non courants
Total actif

Passifs courants
Passifs non courants
Capitaux propres avant résultat
Résultat de l'exercice
Total passif et capitaux propres
```

Contrôle :

```text
Total actif
-
Total passif et capitaux propres
=
0
```

Un écart est affiché explicitement.

---

## 9. Flux de trésorerie

Route :

```text
/statements/cash-flow/
```

Le moteur fonctionne sur les lignes de comptes de trésorerie.

Par défaut :

```text
prefixes = ["5"]
```

Ils sont configurables, par exemple :

```text
52,57
```

### Classification

Priorité 1 :

```text
JournalLine.cash_flow_tag
```

Valeurs supportées :

```text
OPERATING
INVESTING
FINANCING
```

Priorité 2, si activée :

```text
inférence à partir des contreparties
```

Exemples :

```text
contrepartie classe 2
  → INVESTING

passif / equity avec logique dette-capital
  → FINANCING

reste
  → OPERATING
```

Les mouvements non classés sont affichés séparément.

---

## 10. Saisie manuelle et cash-flow tags

Le Sprint 6 enrichit la saisie comptable du Sprint 3.

Chaque ligne d'écriture peut maintenant renseigner :

```text
cash_flow_tag
```

Le champ est disponible dans l'écran dynamique HTMX de saisie d'écriture.

Le service de création / modification de brouillon persiste ce tag.

---

## 11. Rapprochement de trésorerie

Le tableau de flux calcule :

```text
Trésorerie d'ouverture

+ CFO
+ CFI
+ CFF
+ Flux non classés

= Trésorerie théorique de clôture
```

Puis :

```text
Écart de rapprochement
=
Trésorerie comptable
-
Trésorerie théorique
```

Le moteur expose donc explicitement les anomalies de classification.

---

## 12. Ratios financiers

Route :

```text
/statements/ratios/
```

Ratios livrés :

```text
NET_MARGIN
ROA
CURRENT_RATIO
DEBT_TO_ASSETS
EQUITY_RATIO
CFO_TO_REVENUE
ASSET_TURNOVER
```

Exemples :

```text
Marge nette
=
Résultat net / chiffre d'affaires

Current ratio
=
Actifs courants / passifs courants

Debt to assets
=
Passifs / actif total

CFO to revenue
=
Flux opérationnel / chiffre d'affaires
```

Ces ratios sont analytiques et non réglementaires.

---

## 13. Comparatifs N-1

Si un exercice précédent existe dans la même organisation :

```text
N
vs
N-1
```

est calculé automatiquement pour :

```text
Compte de résultat
Bilan
Flux de trésorerie
```

La fonctionnalité peut être désactivée dans :

```text
/statements/configuration/
```

---

## 14. Drill-down

Depuis une rubrique d'état financier :

```text
StatementLine
   ↓
StatementAccountMapping
   ↓
Account
   ↓
Grand livre
   ↓
JournalEntry
   ↓
JournalLine source
```

Route :

```text
/statements/lines/<uuid>/
```

Le détail liste les comptes contributeurs et propose un lien vers le grand livre.

---

## 15. Diagnostics de mapping

Le moteur calcule :

```text
nombre total de comptes
nombre de comptes mappés
nombre non mappés
couverture %
```

Le compte de résultat et le bilan signalent aussi les comptes avec montant non nul mais sans mapping.

Cela évite un état financier silencieusement incomplet.

---

## 16. Audit

Le Sprint 6 produit notamment :

```text
FINANCIAL_STATEMENTS_BOOTSTRAP
FINANCIAL_STATEMENTS_CONFIG_UPDATE
STATEMENT_AUTO_MAPPING
STATEMENT_MAPPING_UPDATE
```

Ils sont consultables dans :

```text
/audit/
```

---

## 17. Commande CLI

Initialisation :

```bash
python manage.py bootstrap_financial_statements "CFA FRA Demo"
```

Avec auto-mapping :

```bash
python manage.py bootstrap_financial_statements   "CFA FRA Demo"   --username admin   --auto-map
```

---

## 18. Tests

Fichier :

```text
apps/financial_statements/tests/test_sprint6_financial_statements.py
```

Couverture prévue :

```text
bootstrap des 3 états
auto-mapping
mapping manuel préservé

compte de résultat
résultat net

bilan
résultat courant synthétique
équilibre actif = passif

flux opérationnels
flux d'investissement
flux de financement
rapprochement de trésorerie

ratios financiers

UI états financiers
drill-down rubrique → grand livre
```

---

## 19. Architecture finale du Sprint 6

```text
Account
  │
  ├─────────────┐
  │             │
  v             v
JournalLine   StatementAccountMapping
  │             │
  v             v
Trial Balance StatementLine
  │             │
  └──────┬──────┘
         v
Financial Statements Engine
         │
   ┌─────┼───────────┐
   │     │           │
   v     v           v
Income  Balance    Cash Flow
   │     │           │
   └─────┼───────────┘
         v
       Ratios
         │
         v
      Drill-down
```

---

## 20. Démarrage

```bash
cp .env.example .env
docker compose up --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py bootstrap_demo
docker compose exec web python manage.py bootstrap_financial_statements   "CFA FRA Demo"   --username admin   --auto-map
```

Puis :

```text
http://localhost:8000/statements/
```

---

## 21. Vérifications Docker / CI

```bash
docker compose exec web python manage.py check

docker compose exec web pytest apps/financial_statements -q

docker compose exec web pytest apps/reporting -q

docker compose exec web ruff check .

docker compose exec web python manage.py makemigrations --check --dry-run
```

---

## 22. Frontière du Sprint 6

Le Sprint 6 fournit un moteur d'états financiers dynamique.

Il reste volontairement distinct des formats réglementaires officiels.

La suite logique est :

```text
Sprint 7 — Regulatory Statement Mapping & Exports
```

avec par exemple :

```text
CFA_FRA_MVP
        ↓
SYSCOHADA presentation mapping
IFRS presentation mapping
        ↓
exports Excel / PDF
        ↓
snapshots
        ↓
comparatifs multi-exercices
        ↓
contrôles réglementaires
```
