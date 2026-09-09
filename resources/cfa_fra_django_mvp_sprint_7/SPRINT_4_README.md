# Sprint 4 — FEC Import end-to-end

## Statut

Sprint 4 implémenté sur la base :

```text
Sprint 0 — Bootstrap Django / PostgreSQL / Docker
Sprint 1 — Organizations / Fiscal Years / Periods
Sprint 2 — Accounting Core
Sprint 3 — HTMX Entry Workflow / Posting / Reversal / Audit
Sprint 4 — FEC Import end-to-end
```

---

# 1. Objectif du Sprint 4

Le Sprint 4 couvre désormais le pipeline :

```text
Upload
  |
  v
SHA-256 / idempotence
  |
  v
Parsing
  |
  v
Conservation des lignes brutes
  |
  v
Contrôles FEC
  |
  v
Mapping comptes / journaux
  |
  v
Normalisation des écritures
  |
  v
Import transactionnel
  |
  v
JournalEntry / JournalLine POSTED
```

---

# 2. Routes principales

```text
GET  /imports/fec/
GET  /imports/fec/new/
POST /imports/fec/new/

GET  /imports/fec/<uuid>/
POST /imports/fec/<uuid>/parse/

GET  /imports/fec/<uuid>/mappings/
POST /imports/fec/<uuid>/mappings/auto/

POST /imports/fec/<uuid>/mappings/accounts/<mapping_uuid>/
POST /imports/fec/<uuid>/mappings/journals/<mapping_uuid>/

POST /imports/fec/<uuid>/execute/
```

---

# 3. Upload

L'upload conserve :

```text
fichier original
nom du fichier
organisation
exercice comptable
utilisateur
SHA-256
timestamp
```

Le SHA-256 sert de clé d'idempotence fonctionnelle :

```text
organization
+
fiscal_year
+
sha256
```

Le même fichier ne peut donc pas être chargé deux fois sur le même exercice.

---

# 4. Formats FEC attendus

Le parser attend les 18 colonnes standards :

```text
JournalCode
JournalLib
EcritureNum
EcritureDate
CompteNum
CompteLib
CompAuxNum
CompAuxLib
PieceRef
PieceDate
EcritureLib
Debit
Credit
EcritureLet
DateLet
ValidDate
Montantdevise
Idevise
```

Séparateur :

```text
TAB
```

Encodages essayés :

```text
UTF-8 BOM
CP1252
Latin-1
```

---

# 5. Conservation des lignes brutes

Chaque ligne du fichier devient :

```text
FECRawLine
```

Les données normalisées utiles sont stockées dans des champs typés.

Les données sources intégrales restent également disponibles dans :

```text
raw_data JSON
```

Chaque ligne conserve :

```text
line_number
row_hash
normalized_entry_key
is_valid
```

Cette stratégie permet :

```text
audit
debug
reprocessing
rapprochement source -> écriture
preuve d'origine
```

---

# 6. Contrôles FEC

Le parser crée des `ImportError`.

## Contrôles bloquants

```text
FEC_REQUIRED_COLUMNS

FEC_MISSING_JOURNAL_CODE

FEC_MISSING_ENTRY_NUMBER

FEC_MISSING_ACCOUNT_NUMBER

FEC_MISSING_ACCOUNT_LABEL

FEC_INVALID_ENTRY_DATE

FEC_DATE_OUTSIDE_FISCAL_YEAR

FEC_INVALID_DEBIT

FEC_INVALID_CREDIT

FEC_DEBIT_AND_CREDIT

FEC_ZERO_LINE

FEC_NEGATIVE_AMOUNT

FEC_UNBALANCED_ENTRY

FEC_GLOBAL_UNBALANCED
```

## Warnings

```text
FEC_DUPLICATE_LINE

FEC_INVALID_CURRENCY_AMOUNT
```

Un doublon potentiel est donc signalé sans être supprimé automatiquement.

---

# 7. Hash de ligne

Chaque ligne reçoit un SHA-256 calculé à partir des 18 colonnes FEC.

Cela permet de détecter les lignes strictement identiques.

Le contrôle reste volontairement un :

```text
WARNING
```

car certaines répétitions peuvent être légitimes selon le système source.

---

# 8. Normalisation des écritures

Le regroupement du MVP reprend la logique utilisée dans les scénarios Excel CFA FRA.

## JAN

```text
toutes les lignes JAN
->
OPENING-<FiscalYear>
```

Clé :

```text
JAN|OPENING|2025
```

## JOD / TAX / PAIE

Clé :

```text
JournalCode
+
EcritureNum
+
EcritureDate
```

## Autres journaux

Clé :

```text
JournalCode
+
EcritureNum
+
EcritureDate
+
PieceRef
```

Cette stratégie réduit les collisions lorsqu'un même numéro d'écriture est réutilisé sur plusieurs pièces.

---

# 9. Contrôle de partie double

Chaque groupe normalisé doit vérifier :

```text
SUM(Debit)
=
SUM(Credit)
```

Le FEC global doit également vérifier :

```text
SUM(All Debit)
=
SUM(All Credit)
```

Toute anomalie bloque l'import final.

---

# 10. Mapping des comptes

Le parsing crée un `ImportMapping` pour chaque :

```text
CompteNum distinct
```

Le mapping contient :

```text
source_account_number
source_account_label
occurrence_count
account
created_automatically
```

---

# 11. Mapping des journaux

Le Sprint 4 ajoute :

```text
JournalImportMapping
```

pour chaque :

```text
JournalCode distinct
```

Champs :

```text
source_journal_code
source_journal_label
occurrence_count
journal
created_automatically
```

---

# 12. Mapping exact automatique

Lors du parsing, le moteur recherche automatiquement :

```text
CompteNum == Account.code

JournalCode == Journal.code
```

dans l'organisation active.

Les mappings exacts sont immédiatement renseignés.

---

# 13. Mapping manuel HTMX

L'écran :

```text
/imports/fec/<uuid>/mappings/
```

permet de modifier chaque mapping sans recharger la page.

Les sélecteurs sont strictement limités à :

```text
organization active
```

Après chaque mapping, le statut de préparation du FEC est recalculé.

---

# 14. Auto-création des références manquantes

Le bouton :

```text
Créer automatiquement les références manquantes
```

crée :

```text
Account
Journal
```

pour les codes source encore non mappés.

## Comptes

Le compte est créé dans le plan comptable actif/par défaut.

Une première classification est inférée depuis le code :

```text
classe 1 -> Equity / Liability
classe 2 -> Asset
classe 3 -> Asset
classe 4 -> Asset / Liability selon préfixe
classe 5 -> Asset
classe 6 -> Expense
classe 7 -> Revenue
autres   -> Other
```

Cette classification est une aide de migration.

Elle ne remplace pas une validation réglementaire SYSCOHADA / IFRS.

---

# 15. Journaux créés automatiquement

Le moteur tente d'inférer :

```text
OPENING
PURCHASE
SALES
BANK
CASH
PAYROLL
TAX
GENERAL
```

à partir du code et du libellé source.

---

# 16. Statuts de l'import

Le workflow FEC devient :

```text
UPLOADED
   |
   v
PARSED
   |
   +------ erreurs bloquantes ------> PARSED
   |
   +------ mappings incomplets -----> MAPPING
   |
   +------ mappings complets -------> READY
                                        |
                                        v
                                    IMPORTING
                                        |
                              +---------+---------+
                              |                   |
                              v                   v
                           IMPORTED             FAILED
```

---

# 17. Condition READY

Un import devient `READY` uniquement si :

```text
0 erreur bloquante

ET

0 compte non mappé

ET

0 journal non mappé
```

---

# 18. RBAC

## Upload / parsing / mapping

Autorisés pour :

```text
ADMIN
ACCOUNTANT
REVIEWER
```

## Import final

Autorisé uniquement pour :

```text
ADMIN
REVIEWER
```

L'import final crée directement des écritures `POSTED`, car le FEC représente une comptabilité déjà validée dans le système source.

---

# 19. Import transactionnel

L'import final utilise :

```text
transaction.atomic
```

et un verrou :

```text
select_for_update
```

sur le `FECImport`.

Il crée :

```text
JournalEntry
+
JournalLine
```

en bulk.

Si une étape échoue :

```text
ROLLBACK complet
```

Aucune comptabilité partielle n'est conservée.

---

# 20. JournalEntry générées

Les écritures FEC sont créées avec :

```text
source = "FEC"

source_reference =
"<fec_import_id>:<normalized_entry_key>"

status = POSTED

created_by = import user
validated_by = import user
posted_by = import user
```

Les timestamps de validation et de posting sont enregistrés.

---

# 21. JournalLine générées

Chaque ligne conserve :

```text
source_line_number
```

ainsi que dans `metadata` :

```text
fec_import_id
fec_raw_line_id
source_account_number
source_journal_code
piece_reference
auxiliary_number
auxiliary_label
```

Le lien :

```text
FEC line
->
JournalLine
```

reste donc reconstructible.

---

# 22. Idempotence de l'import transactionnel

Avant création, le moteur recherche :

```text
JournalEntry.source = FEC

AND

source_reference startswith FECImport.id
```

Si des écritures existent déjà :

```text
IMPORT REFUSÉ
```

Cela complète la protection SHA-256 du fichier.

---

# 23. Périodes comptables

Chaque date FEC doit être couverte par une `AccountingPeriod`.

Le Sprint 4 exige pour l'import final :

```text
AccountingPeriod.status = OPEN
```

Une période fermée bloque la migration.

---

# 24. Écritures d'ouverture

Pour `JAN`, l'écriture normalisée utilise :

```text
entry_type = OPENING

entry_number = OPENING-<FiscalYear>
```

---

# 25. Écritures JOD

Pour `JOD` :

```text
entry_type = ADJUSTING
```

Les autres journaux sont importés en :

```text
NORMAL
```

hors `JAN`.

---

# 26. Audit trail FEC

Le pipeline produit les événements :

```text
FEC_UPLOAD

FEC_PARSE

FEC_ACCOUNT_MAPPING_UPDATE

FEC_JOURNAL_MAPPING_UPDATE

FEC_AUTO_MAPPING

FEC_IMPORT
```

Ils sont consultables dans :

```text
/audit/
```

---

# 27. Interface de preview

L'écran d'import affiche :

```text
fichier
exercice
encodage
SHA-256
statut

nombre de lignes
nombre de groupes d'écritures
nombre de comptes
nombre de journaux

total débit
total crédit
écart

erreurs bloquantes
warnings

100 premières lignes brutes
```

---

# 28. Commande CLI

Le Sprint 4 ajoute :

```bash
python manage.py import_fec   path/to/FEC.txt   --organization "CFA FRA Demo"   --fiscal-year 2025   --username admin
```

Parsing + auto-mapping :

```bash
python manage.py import_fec   path/to/FEC.txt   --organization "CFA FRA Demo"   --fiscal-year 2025   --username admin   --auto-map
```

Pipeline complet :

```bash
python manage.py import_fec   path/to/FEC.txt   --organization "CFA FRA Demo"   --fiscal-year 2025   --username admin   --auto-map   --execute
```

---

# 29. Dashboard

Le dashboard ajoute :

```text
FEC total
FEC en mapping
FEC ready
FEC imported
FEC failed
```

---

# 30. Tests Sprint 4

Le fichier :

```text
apps/imports/tests/test_sprint4_fec_pipeline.py
```

couvre :

```text
upload + parsing CP1252

conservation raw_data

normalisation en groupes

totaux débit / crédit

mapping exact des journaux

auto-création des comptes

READY state

import transactionnel

JournalEntry POSTED

traçabilité source_line_number

audit FEC_IMPORT

idempotence SHA-256

FEC déséquilibré bloqué

upload UI

RBAC import final
```

---

# 31. Démarrage

```bash
cp .env.example .env

docker compose up --build

docker compose exec web python manage.py bootstrap_demo
```

Puis :

```text
http://localhost:8000/imports/fec/
```

---

# 32. Vérifications Docker

```bash
docker compose exec web python manage.py migrate

docker compose exec web python manage.py check

docker compose exec web pytest

docker compose exec web ruff check .
```

---

# 33. Frontière du Sprint 4

Le Sprint 4 reconstruit désormais le journal comptable depuis un FEC.

Les écrans de reporting existent encore principalement sous forme de starter.

La suite logique est :

```text
Sprint 5
Ledger & Trial Balance
```

Pipeline :

```text
POSTED JournalLine
        |
        +----------------------+
        |                      |
        v                      v
Journal report            General Ledger
                               |
                               v
                         Trial Balance
                               |
                    +----------+----------+
                    |                     |
                    v                     v
               Controls              Drill-down
```

---

# Conclusion

Le Sprint 4 transforme l'application d'un moteur de saisie comptable en un véritable moteur d'ingestion comptable.

Le fichier FEC n'est jamais directement converti en états financiers.

Il passe désormais par :

```text
Source brute
   |
   v
Validation
   |
   v
Mapping
   |
   v
Normalisation
   |
   v
JournalEntry / JournalLine
   |
   v
Source comptable canonique
```

Cette architecture permet désormais d'aborder le Sprint 5 avec une source de vérité comptable fiable et traçable.
