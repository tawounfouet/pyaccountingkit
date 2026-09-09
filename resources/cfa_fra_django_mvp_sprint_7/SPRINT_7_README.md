# Sprint 7 — Regulatory Statement Mapping & Exports

## Statut

Sprint 7 implémenté sur la base des Sprints 0 à 6.

Pipeline :

```text
Journal / Balance / Financial Statements Engine
        ↓
CFA_FRA_MVP StatementLine
        ↓
RegulatoryStatementProfile
        ↓
RegulatoryStatementLineMapping
        ↓
SYSCOHADA / IFRS / autre FrameworkVersion
        ↓
StatementDefinition / StatementLine réglementaires
        ↓
Preview + contrôles
        ↓
ReportSnapshot
        ↓
ExportJob
        ↓
XLSX / PDF / CSV / JSON
```

## 1. Principe

Le moteur interne `CFA_FRA_MVP` reste la couche de calcul.

Le Sprint 7 ajoute une couche de présentation réglementaire distincte. Il ne remplace pas les calculs comptables et n'invente pas de nomenclature officielle.

Les lignes réglementaires doivent être chargées depuis un JSON validé par l'organisation.

## 2. Nouveau modèle de profil

`RegulatoryStatementProfile` relie :

```text
Organization
+ source FrameworkVersion (CFA_FRA_MVP)
+ target FrameworkVersion (SYSCOHADA / IFRS / autre)
```

Le MVP accepte au maximum une `StatementDefinition` par type d'état dans une même version cible.

Types gérés pour l'export :

```text
INCOME_STATEMENT
BALANCE_SHEET
CASH_FLOW
```

## 3. Mapping ligne à ligne

`RegulatoryStatementLineMapping` relie :

```text
StatementLine source
→ StatementLine réglementaire cible
```

avec :

```text
multiplier
mapping_type
confidence
validated_by
validated_at
notes
```

Le mapping cible toujours une ligne non-total du même type d'état.

## 4. Auto-mapping

Priorité :

```text
1. code exact
2. metadata.source_code
3. metadata.source_codes
4. metadata.role
5. libellé normalisé exact
```

Aucune similarité floue n'est appliquée automatiquement.

Les mappings `MANUAL` sont conservés lors d'un nouvel auto-mapping.

## 5. Métadonnées réglementaires

`StatementLine` reçoit :

```text
is_required
standard_reference
metadata
```

Exemples de `metadata.role` :

```text
revenue
current_assets
current_liabilities
equity
current_result
operating_cash_flow
investing_cash_flow
financing_cash_flow
total_assets
total_liabilities_equity
cash_reconciliation_gap
```

## 6. Contrôles

Le package réglementaire contrôle notamment :

```text
source non mappée avec montant non nul
ligne réglementaire obligatoire non mappée
équation du bilan si les rôles de total sont fournis
rapprochement de trésorerie si le rôle est fourni
```

L'aperçu reste disponible avec warnings.

L'export est bloqué tant que le package n'est pas prêt.

## 7. Seed réglementaire enrichi

Le loader historique de comptes reste compatible.

Le format Sprint 7 peut contenir :

```json
{
  "framework": {},
  "accounts": [],
  "statements": []
}
```

Documentation :

```text
docs/REGULATORY_FRAMEWORK_SCHEMA.md
```

Commande générique :

```bash
python manage.py seed_regulatory_framework   path/to/framework.json
```

Les commandes existantes restent disponibles :

```bash
python manage.py seed_syscohada path/to/syscohada.json
python manage.py seed_ifrs path/to/ifrs.json
```

Elles acceptent désormais également les définitions d'états.

## 8. Interface

Routes :

```text
/statements/regulatory/
/statements/regulatory/new/
/statements/regulatory/<uuid>/
/statements/regulatory/<uuid>/mappings/
```

Fonctions :

```text
création de profil
couverture mapping
auto-mapping
mapping manuel HTMX
preview réglementaire
warnings
contrôles
export
```

## 9. Snapshot

Chaque export réglementaire crée un `ReportSnapshot` :

```text
report_type = REGULATORY_PACKAGE
```

Le snapshot conserve :

```text
organisation
profil
framework cible
version
exercice
date d'arrêté
lignes des états
comparatifs
références
warnings
validations
mappings
```

Le snapshot est JSON-serialisable et constitue la trace fonctionnelle de l'export.

## 10. ExportJob

`ExportJob` est enrichi avec :

```text
format
mime_type
content_sha256
snapshot
regulatory_profile
status
file
completed_at
error_message
```

Formats :

```text
XLSX
PDF
CSV
JSON
```

Un export en erreur reste enregistré avec le statut `FAILED`.

## 11. Excel

Le classeur contient :

```text
Metadata
1 feuille par état réglementaire
Mapping
Warnings
```

Les feuilles d'états incluent :

```text
Code
Rubrique
N
N-1
Référence réglementaire
Obligatoire
```

## 12. PDF

Le PDF contient les états réglementaires sous forme de tableaux paginés.

La génération utilise `reportlab`.

## 13. CSV / JSON

CSV :

```text
UTF-8 BOM
séparateur ;
sections par état
```

JSON :

```text
snapshot réglementaire complet
```

## 14. Traçabilité

Chaque fichier final reçoit :

```text
SHA-256
```

Audit :

```text
REGULATORY_PROFILE_CREATE
REGULATORY_AUTO_MAPPING
REGULATORY_MAPPING_UPDATE
REGULATORY_EXPORT_CREATE
```

## 15. Téléchargement

Routes :

```text
/exports/
/exports/<uuid>/
/exports/<uuid>/download/
```

Le téléchargement passe par une vue authentifiée et scopée à l'organisation active.

## 16. Dépendances

Sprint 7 ajoute :

```text
XlsxWriter
reportlab
```

## 17. Tests

Fichier principal :

```text
apps/financial_statements/tests/test_sprint7_regulatory_exports.py
```

Il couvre :

```text
auto-mapping par role
mapping manuel préservé
package réglementaire
équation du bilan
flux de trésorerie
ligne obligatoire manquante
snapshot
ExportJob
SHA-256
JSON
XLSX
PDF
download sécurisé par organisation
```

## 18. Exemple technique

Un exemple volontairement non officiel est fourni :

```text
examples/regulatory_framework_template.json
```

Il sert uniquement à illustrer le schéma d'ingestion.

## 19. Démarrage

```bash
docker compose up --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py bootstrap_demo
```

Puis charger un référentiel réglementaire validé :

```bash
docker compose exec web python manage.py seed_regulatory_framework   path/to/framework.json
```

Ouvrir :

```text
http://localhost:8000/statements/regulatory/
```

## 20. Vérifications

```bash
docker compose exec web python manage.py check

docker compose exec web python manage.py makemigrations --check --dry-run

docker compose exec web pytest apps/financial_statements -q

docker compose exec web pytest apps/exports -q

docker compose exec web ruff check .
```

## 21. Frontière du Sprint 7

Le Sprint 7 fournit l'infrastructure de mapping réglementaire et les exports traçables.

Il ne livre pas une nomenclature officielle SYSCOHADA/IFRS codée en dur.

La suite logique est :

```text
Sprint 8 — Regulatory Controls & Closing Package
```

avec :

```text
contrôles réglementaires
checklists de clôture
sign-off
versioning des snapshots
comparatifs multi-exercices
package de clôture
workflow reviewer / approver
```
