# 00 - PyAccountingKit - Analyse des besoins

> **Projet** : PyAccountingKit  
> **Document** : `00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`  
> **Statut** : Cadrage enrichi - sources réglementaires, référence fonctionnelle et corpus doctrinal
> **Langue** : Français  
> **Objet** : Formaliser les besoins fonctionnels, non fonctionnels, réglementaires, doctrinaux et architecturaux de PyAccountingKit, en intégrant `regulatory-accounting-data-framework`, `cfa_fra_django_mvp_sprint_7`, ainsi que les apports des ouvrages de comptabilité générale et de gestion financière.

---

# 1. Résumé exécutif

**PyAccountingKit** est un framework Python de comptabilité destiné à fournir un moteur comptable :

- réutilisable ;
- fortement typé ;
- auditable ;
- déterministe ;
- extensible ;
- indépendant des frameworks applicatifs ;
- indépendant d'un ORM ;
- indépendant d'un référentiel national particulier.

PyAccountingKit ne doit ni embarquer en dur le PCG, SYSCOHADA, OHADA EBNL ou un autre plan réglementaire, ni recopier les règles issues d'une application Django existante.

Le cadrage repose désormais sur quatre sources complémentaires.

```text
regulatory-accounting-data-framework
    -> source de vérité réglementaire structurée

cfa_fra_django_mvp_sprint_7
    -> référence fonctionnelle exécutable

Comptabilité générale - Système français et normes IFRS
    -> source doctrinale comptable et conceptuelle

Maxi fiches de Gestion financière de l'entreprise
    -> source doctrinale d'analyse financière

PyAccountingKit
    -> abstraction générique et moteur comptable cible
```

La frontière de responsabilité est la suivante :

```text
regulatory-accounting-data-framework
    décrit CE QU'EST le référentiel réglementaire
                    |
                    v
              PyAccountingKit
    fournit le moteur comptable générique,
    instancie le référentiel dans l'organisation
    et exécute les workflows comptables
                    ^
                    |
cfa_fra_django_mvp_sprint_7
    fournit des comportements déjà implémentés
    servant de référence de conception et de tests
```

Le besoin central est désormais quintuple :

1. fournir un moteur de comptabilité en partie double robuste ;
2. transformer un référentiel réglementaire versionné en plan comptable d'entreprise opérationnel, sans supposer une longueur fixe des comptes ;
3. formaliser les politiques de reconnaissance, d'évaluation et de traitement comptable sans transformer une méthode particulière en invariant universel ;
4. extraire et généraliser les invariants, workflows et scénarios validés dans le MVP Django sans importer Django, HTMX ou son ORM dans le coeur ;
5. fournir un read-side d'analyse financière dérivé de la comptabilité, sans transformer PyAccountingKit en framework complet de corporate finance.

---

# 2. Contexte

## 2.1 Besoin métier

Les applications comptables ont besoin de briques communes :

- organisations et entités comptables ;
- exercices et périodes ;
- plans comptables ;
- comptes ;
- journaux ;
- écritures ;
- lignes débit/crédit ;
- posting ;
- extourne ;
- grand livre ;
- balance ;
- clôture ;
- reporting financier ;
- contrôles ;
- audit ;
- imports comptables ;
- rapprochement ;
- référentiels réglementaires ;
- multi-entité ;
- multi-devise.

Ces fonctions sont souvent réimplémentées projet par projet avec des hypothèses implicites sur :

- la longueur des comptes ;
- les préfixes ;
- le format du plan ;
- le stockage ;
- le framework web ;
- la structure du reporting.

PyAccountingKit doit fournir un socle générique.

---

## 2.2 Source réglementaire amont

`regulatory-accounting-data-framework` fournit déjà des artefacts structurés couvrant notamment :

- PCG France 2026 ;
- SYSCOHADA 2017 ;
- référentiel français non lucratif 2026 ;
- OHADA EBNL 2023 ;
- structures hiérarchiques ;
- plans effectifs ;
- overlays ;
- relations entre standards ;
- reporting réglementaire ;
- concepts comptables neutres ;
- crosswalks ;
- provenance ;
- statuts de validation.

PyAccountingKit ne doit pas recréer ces données.

Il doit les consommer via un contrat d'intégration stable.

---

## 2.3 Référence fonctionnelle exécutable

`cfa_fra_django_mvp_sprint_7` fournit une implémentation verticale déjà avancée.

Pipeline fonctionnel observé :

```text
Organizations / Fiscal Years / Periods
        |
        v
ChartOfAccounts / Account / Journal
        |
        v
JournalEntry / JournalLine
        |
        v
Validation / Posting / Reversal
        |
        v
Audit
        |
        v
FEC Import
        |
        v
Journal / General Ledger / Trial Balance
        |
        v
Financial Statements
        |
        v
Regulatory Statement Mapping
        |
        v
Snapshots / Exports
```

Le projet doit être traité comme :

```text
Executable Functional Reference
Reference Implementation Source
Behavioral Evidence
Golden Scenario Source
```

Il ne doit pas être traité comme :

```text
runtime dependency
Django architecture template
regulatory source of truth
universal accounting semantics
```

---

## 2.4 Source doctrinale comptable

L'ouvrage `Comptabilité générale - Système français et normes IFRS` est utilisé pour approfondir :

- les principes comptables ;
- le journal et le grand livre ;
- la séparation des exercices et le rattachement ;
- la codification des comptes ;
- la reconnaissance des actifs, passifs, charges et produits ;
- les méthodes d'évaluation ;
- les immobilisations, amortissements et dépréciations ;
- les stocks ;
- les achats et ventes ;
- les créances et règlements ;
- les provisions et régularisations ;
- les états financiers ;
- la consolidation.

Ce corpus est une source doctrinale. Il ne remplace pas un référentiel réglementaire versionné et actuel.

---

## 2.5 Source doctrinale d'analyse financière

L'ouvrage `Maxi fiches de Gestion financière de l'entreprise` apporte le vocabulaire et les méthodes du read-side analytique :

```text
SIG
EBE / EBITDA
CAF
FRNG
BFR / BFRE / BFRHE
trésorerie nette
ratios
scores
diagnostic financier
tableaux de financement
tableaux de flux
```

Ces concepts sont calculés à partir du ledger, des balances et des états financiers. Ils ne modifient jamais les écritures.

La VAN, le TRI, le coût du capital, la stratégie de financement, le risque d'investissement et la valorisation d'entreprise constituent une frontière avec la corporate finance et restent hors du coeur obligatoire.

---

# 3. Sources de cadrage analysées

## 3.1 `regulatory-accounting-data-framework`

Artefacts principaux :

```text
datasets/
├── structured/
│   ├── syscohada_2017_v1_structure.json
│   ├── pcg_2026_v1_structure.json
│   ├── nonprofit_2026_v1_effective_plan.json
│   ├── nonprofit_2026_v1_account_overlay.json
│   └── ebnl_2023_v1_structure.json
│
├── reporting/
│   ├── syscohada_2017_v3_reporting.json
│   ├── pcg_2026_v3_reporting.json
│   ├── nonprofit_2026_v3_reporting.json
│   └── ebnl_2023_v3_reporting.json
│
├── relations/
├── raw/
├── prudential/
├── crosswalk/
└── concepts/
```

Propriétés structurantes :

- standards identifiés explicitement ;
- éditions versionnées ;
- identifiants de noeuds stables ;
- hiérarchie parent/enfants explicite ;
- provenance conservée ;
- plans effectifs et overlays ;
- relations n'impliquant pas automatiquement de l'héritage ;
- reporting réglementaire structuré ;
- distinction entre mappings exécutables et candidats ;
- concepts comptables neutres ;
- égalité de code non suffisante pour établir une équivalence sémantique.

---

## 3.2 `cfa_fra_django_mvp_sprint_7`

Documents de référence :

```text
README.md
ARCHITECTURE.md
ACCOUNTING_RULES.md

CFA_FRA_DJANGO_DOCUMENT_CONCEPTION_TECHNICO_FONCTIONNELLE.md
CFA_FRA_DJANGO_MVP_PLAN_IMPLEMENTATION_DJANGO_HTMX.md
REGULATORY_FRAMEWORK_SCHEMA.md

SPRINT_0_1_README.md
SPRINT_2_README.md
SPRINT_3_README.md
SPRINT_4_README.md
SPRINT_5_README.md
SPRINT_6_README.md
SPRINT_7_README.md
```

Matrice des capacités utiles :

| Domaine | Capacités déjà éprouvées |
|---|---|
| Source comptable | `Account`, `AccountingPeriod`, `JournalEntry`, `JournalLine` |
| Organisation | multi-organisation, exercices, périodes |
| Accounting Core | plans, comptes, journaux, écritures |
| Workflow | `DRAFT -> VALIDATED -> POSTED -> REVERSED` |
| Validation | partie double, période ouverte, comptes cohérents |
| Mutation | posting, immutabilité, reversal |
| Concurrence | transactions atomiques, verrouillage |
| Audit | événements, snapshots before/after |
| Import | FEC brut, SHA-256, validation, mapping, normalisation |
| Ledger | journal, grand livre, running balance |
| Balance | avant ajustements, ajustée, post-clôture |
| Reporting | résultat, bilan, cash-flow |
| Mapping | compte -> rubrique -> ligne réglementaire |
| Réglementaire | profil, mapping, warnings, contrôles |
| Snapshot | contexte complet d'un export |
| Exports | XLSX, PDF, CSV, JSON |
| Tests | scénarios de non-régression |

---

## 3.3 Règle d'arbitrage

```text
Sujet réglementaire
    -> regulatory-accounting-data-framework

Comportement déjà implémenté
    -> cfa_fra_django_mvp_sprint_7

Abstraction générique
    -> PyAccountingKit
```

Une décision spécifique du MVP Django ne devient jamais automatiquement une règle universelle.

---


## 3.3 `Comptabilité générale - Système français et normes IFRS`

Apports doctrinaux à exploiter :

```text
principes comptables
partie double
grand livre / journal
monisme / dualisme
codification des comptes
séparation des exercices
coût / valeur / juste valeur
immobilisations
stocks
achats / ventes
créances / règlements
provisions / dépréciations
régularisations
bilan / compte de résultat
consolidation
```

Les conventions propres au PCG, à l'IFRS ou à une présentation particulière sont classées comme `REFERENCE_SPECIFIC_RULE`, `ACCOUNTING_METHOD` ou `PRESENTATION_RULE`, pas comme invariants universels.

---

## 3.4 `Maxi fiches de Gestion financière de l'entreprise`

Apports analytiques :

```text
SIG
EBE
EBITDA
CAF
analyse fonctionnelle
FRNG
BFR
trésorerie nette
ratios
scores
tableaux de financement
tableaux de flux
diagnostic
```

Ces définitions alimentent un bounded context `Financial Analysis` downstream et read-only.

---

## 3.5 Hiérarchie d'autorité

En cas de divergence :

```text
1. Référentiel réglementaire versionné et validé
2. Configuration / AccountingPolicySet de l'organisation
3. Invariant comptable générique démontré
4. Référence fonctionnelle CFA FRA
5. Sources doctrinales
6. Heuristiques et suggestions
```

Une source doctrinale sert à comprendre et modéliser ; elle ne remplace pas une règle réglementaire actuelle.

---

# 4. Vision produit

PyAccountingKit doit devenir un framework Python générique de comptabilité financière utilisable dans :

- ERP ;
- logiciel comptable ;
- SaaS ;
- fintech ;
- système de facturation ;
- application associative ;
- back-office financier ;
- système de consolidation ;
- Django ;
- FastAPI ;
- CLI ;
- service métier indépendant.

Principes :

```text
Domain-first
Framework-agnostic
Persistence-agnostic
Reference-data-driven
Auditable
Deterministic
Extensible
Strongly typed
Fail-closed on ambiguous accounting rules
```

---

# 5. Principes directeurs

## P-001 - Séparation réglementation / organisation / exécution

```text
Référentiel réglementaire
        !=
Plan comptable entreprise
        !=
Ledger
```

---

## P-002 - Aucune longueur de compte codée en dur

Un compte doit être manipulé comme chaîne :

```python
AccountCode("51200001")
```

Jamais comme entier.

---

## P-003 - La sémantique ne découle pas uniquement du numéro

Interdit dans le coeur :

```python
if account.code.startswith("512"):
    ...
```

La sémantique doit venir :

- du référentiel ;
- de mappings qualifiés ;
- de concepts liés ;
- d'une configuration entreprise explicite.

---

## P-004 - Immutabilité après posting

Une écriture `POSTED` ne peut être modifiée directement.

```text
POSTED
  |
  v
REVERSAL
  |
  v
NEW CORRECT ENTRY
```

---

## P-005 - Partie double obligatoire

```text
SUM(debit) = SUM(credit)
```

avant tout posting.

---

## P-006 - Traçabilité complète

Toute donnée dérivée doit pouvoir conserver :

- standard ;
- édition ;
- version dataset ;
- checksum ;
- compte de référence ;
- provenance ;
- mapping ;
- validation.

---

## P-007 - Pas d'inférence réglementaire non validée

```text
même code
    !=
même sens

structure similaire
    !=
équivalence réglementaire
```

---

## P-008 - Source comptable canonique minimale

Le noyau canonique est :

```text
Account
AccountingPeriod
JournalEntry
JournalEntryLine
```

Le grand livre, la balance et les états financiers sont des projections.

---

## P-009 - Extraction comportementale du MVP

Le projet CFA FRA fournit des comportements et scénarios.

PyAccountingKit ne doit pas dépendre de :

- Django Models ;
- Django ORM ;
- Django Views ;
- HTMX ;
- templates ;
- sessions ;
- admin.

---

## P-010 - Atomicité des mutations critiques

Doivent pouvoir être atomiques :

```text
validate
post
reverse
close
import
```

Le domaine exprime la cohérence attendue ; l'adapter fournit la transaction et le verrouillage.

---


## P-011 - Les méthodes comptables sont des policies

```text
AccountingPolicySet
RecognitionPolicy
MeasurementPolicy
DepreciationPolicy
ImpairmentPolicy
InventoryValuationPolicy
AccrualPolicy
ProvisionPolicy
```

Une méthode particulière ne devient pas un invariant global.

---

## P-012 - Séparer reconnaissance, mesure, posting, présentation et analyse

```text
Recognition -> faut-il comptabiliser ?
Measurement -> pour quel montant ?
Posting -> comment enregistrer l'écriture ?
Presentation -> où présenter le solde ?
Analysis -> quel indicateur en dérive ?
```

---

## P-013 - `Financial Analysis` est downstream et read-only

```text
JournalEntryLine
    -> Ledger
    -> Trial Balance
    -> Financial Statements
    -> Financial Analysis
```

---

## P-014 - Corporate finance hors coeur par défaut

VAN, TRI, WACC, choix d'investissement, choix de financement, Monte Carlo et valorisation ne sont pas des capacités obligatoires du coeur.

---

# 6. Périmètre fonctionnel

## 6.1 Inclus

### Comptabilité générale

- entités comptables ;
- exercices ;
- périodes ;
- plan comptable entreprise ;
- comptes ;
- journaux ;
- écritures ;
- lignes ;
- validation ;
- posting ;
- reversal ;
- grand livre ;
- balance ;
- clôture ;
- ouverture.


### Accounting Policies & Measurement

- reconnaissance comptable ;
- mesure initiale et ultérieure ;
- amortissement ;
- dépréciation ;
- provisions ;
- rattachement des charges et produits ;
- valorisation des stocks ;
- traçabilité de la policy appliquée.

### Référentiels

- chargement ;
- sélection standard/édition ;
- plan effectif ;
- filiation ;
- règles de codification ;
- extensions entreprise ;
- mappings.

### Import

- contrat générique d'import ;
- raw records ;
- provenance ;
- validation ;
- normalisation ;
- mapping ;
- idempotence ;
- atomicité ;
- FEC via adapter optionnel.

### Contrôles

- partie double ;
- compte actif ;
- période ouverte ;
- balance ;
- bilan ;
- cash-flow ;
- clôture ;
- import.

### Reporting

- balance ;
- résultat ;
- bilan ;
- cash-flow ;
- modèles réglementaires ;
- mappings ;
- snapshots.

### Sous-ledgers à terme

- clients ;
- fournisseurs ;
- banque ;
- immobilisations ;
- taxes ;
- rapprochement.

---

## 6.2 Hors du coeur

- parsing de PDF réglementaire ;
- maintenance des textes officiels ;
- validation juridique ;
- UI ;
- Django ;
- FastAPI ;
- ORM imposé ;
- base imposée ;
- inférences normatives à partir de préfixes ;
- logique FEC dans le coeur universel ;
- VAN / TRI / WACC / valorisation dans le coeur obligatoire ;
- décisions d'investissement et de financement dans le write-side comptable.

---

# 7. Utilisateurs cibles

## 7.1 Développeur Python

Attentes :

- API typée ;
- objets métier testables ;
- ports/adapters ;
- documentation ;
- faible couplage.

## 7.2 Editeur ERP / logiciel comptable

Attentes :

- moteur fiable ;
- multi-référentiel ;
- auditabilité ;
- plan configurable ;
- reporting reproductible.

## 7.3 Comptable / responsable financier

Attentes :

- règles de posting sûres ;
- plan adapté à l'entreprise ;
- historique ;
- balance et états fiables.

## 7.4 Auditeur / contrôleur

Attentes :

- provenance ;
- version du référentiel ;
- drill-down ;
- historique ;
- snapshots reproductibles.

---


## 7.5 Analyste financier / contrôleur de gestion

Attentes :

- indicateurs calculés depuis une source comptable traçable ;
- définitions explicites et versionnées ;
- comparatifs temporels ;
- drill-down jusqu'au compte et à l'écriture ;
- séparation entre indicateurs comptables, analytiques et réglementaires.

---

# 8. Architecture fonctionnelle cible

```text
                 regulatory-accounting-data-framework
                              |
                              v
                  AccountingReferenceProvider
                              |
                              v
                       ReferenceCatalog
                              |
                              v
                       SelectedStandard
                              |
                              +
                              |
                 CompanyAccountingProfile
                              |
                              v
                   CompanyChartBuilder
                              |
                              v
                  CompanyChartOfAccounts
                              |
                              v
                   Accounting Domain Core
        +---------------------+---------------------+
        |                     |                     |
        v                     v                     v
 Journal / Entries        Ledger / Balance      Controls
        |                     |                     |
        +---------------------+---------------------+
                              |
                              v
                    Financial Statements
                              |
                              v
                   Regulatory Reporting
                              |
                              v
                     ReportSnapshot

Reference comportementale :
cfa_fra_django_mvp_sprint_7
        -> scénarios
        -> invariants
        -> golden tests
```

---


Extension de la cible :

```text
ReferenceCatalog
      -> AccountingPolicySet
      -> CompanyChartOfAccounts
      -> Journal / Posting
      -> Ledger / Trial Balance
      -> Financial Statements
          +-> Regulatory Reporting
          +-> Financial Analysis
                +-> SIG / EBE / CAF
                +-> FRNG / BFR
                +-> Ratios / Diagnostics
```

---

# 9. Exigences - Référentiels

## REQ-REF-001 - Provider

```python
class AccountingReferenceProvider(Protocol):
    ...
```

Implémentations possibles :

```text
LocalFilesystemReferenceProvider
PackageReferenceProvider
HttpReferenceProvider
S3ReferenceProvider
InMemoryReferenceProvider
```

**Priorité : P0**

---

## REQ-REF-002 - Chargement standard / édition

```python
catalog.get("fr-pcg", "2026")
catalog.get("ohada-syscohada", "2017")
```

**P0**

---

## REQ-REF-003 - Identifiants réglementaires conservés

Exemples :

```text
account:fr-pcg:2026:512
account:ohada-syscohada:2017:7721
```

**P0**

---

## REQ-REF-004 - `ReferenceAccount` distinct de `CompanyAccount`

```text
ReferenceAccount
        |
        v
CompanyAccount
```

**P0**

---

## REQ-REF-005 - Plans effectifs

Lorsqu'un plan effectif est publié en amont, PyAccountingKit le consomme sans le recalculer arbitrairement.

**P0**

---

## REQ-REF-006 - Overlays

Les overlays restent disponibles pour :

- audit ;
- diagnostic ;
- explication ;
- migration.

**P1**

---

## REQ-REF-007 - Relations entre standards

Supporter sans confusion :

```text
member_of_family
specialized_standard_within_family
sector_specialization_within_family
crosswalk
inheritance
```

L'héritage doit être explicite.

**P0**

---

## REQ-REF-008 - Concepts neutres

Support de concepts tels que :

```text
concept:cash
concept:inventory
concept:trade_receivables
concept:trade_payables
concept:operating_expense
concept:operating_revenue
```

Un concept neutre n'est pas une règle comptable.

**P1**

---

# 10. Exigences - Plan comptable d'entreprise

## REQ-COA-001 - Génération depuis référentiel

```python
chart = ChartOfAccounts.from_reference(
    reference=reference,
    entity=entity,
    profile=profile,
)
```

**P0**

---

## REQ-COA-002 - Longueur variable

Support :

```text
6 chiffres
8 chiffres
9 chiffres
12 caractères
longueur variable
alphanumérique
```

**P0**

---

## REQ-COA-003 - `AccountCode` est une chaîne

```python
AccountCode.value: str
```

**P0**

---

## REQ-COA-004 - `AccountCodePolicy`

```python
class AccountCodePolicy(Protocol):
    def validate(self, code: AccountCode) -> None: ...
    def normalize(self, code: str) -> AccountCode: ...
```

Stratégies :

```text
NumericFixedLengthPolicy
NumericVariableLengthPolicy
SegmentedNumericPolicy
AlphanumericPolicy
CustomAccountCodePolicy
```

**P0**

---

## REQ-COA-005 - Schémas segmentés

Exemple :

```text
512 | 01 | 0001
```

Segments possibles :

- compte général ;
- banque ;
- agence ;
- activité ;
- produit ;
- séquence.

**P1**

---

## REQ-COA-006 - Règles par famille

Exemple :

```text
general       -> 6
customer      -> 9
supplier      -> 9
bank          -> 8
fixed_asset   -> 10
```

**P1**

---

## REQ-COA-007 - Modes de génération

```text
REFERENCE_ONLY
PAD_TO_LENGTH
TEMPLATE_EXPANSION
CUSTOM
```

`REFERENCE_ONLY` est le mode prudent par défaut.

**P0**

---

## REQ-COA-008 - Comptes spécifiques entreprise

Les comptes personnalisés doivent conserver :

- provenance ;
- parent ;
- statut custom ;
- éventuelle référence réglementaire.

**P0**

---

## REQ-COA-009 - Filiation

```text
51200101
    -> account:fr-pcg:2026:512
```

**P0**

---

## REQ-COA-010 - Collisions

Refuser :

- doublons ;
- code invalide ;
- parent invalide ;
- subdivision interdite.

**P0**

---


# 10A. Exigences - Accounting Policies, Recognition & Measurement

## REQ-POL-001 - `AccountingPolicySet`

Chaque entité ou ledger doit pouvoir référencer un ensemble versionné de policies.

**Priorité : P0**

## REQ-POL-002 - Reconnaissance distincte du posting

```text
economic event
    -> recognition decision
    -> measurement
    -> journal entry
    -> posting
```

**P0**

## REQ-POL-003 - Mesure explicite

Toute mesure dépendante d'une méthode doit exposer sa base de mesure, ses entrées, la version de policy, le résultat, l'arrondi et la provenance.

**P0**

## REQ-POL-004 - Méthodes spécifiques au référentiel

Une même catégorie peut avoir des traitements différents selon le standard, l'édition, la juridiction, le secteur, la policy entreprise et la date d'effet.

**P0**

## REQ-POL-005 - Policies d'inventaire et de clôture

Le modèle doit accueillir amortissements, dépréciations, provisions, charges/produits constatés d'avance, charges à payer, produits à recevoir et variations de stocks.

**P1**

## REQ-POL-006 - Explicabilité

Une écriture générée automatiquement doit conserver une trace de la policy et des données ayant conduit au montant.

**P1**

---

# 11. Comptes collectifs et auxiliaires

## REQ-AUX-001

Support :

```text
411000 Clients
401000 Fournisseurs
```

## REQ-AUX-002

Modes :

```text
SUBLEDGER
EXTENDED_ACCOUNT_CODE
HYBRID
```

Exemple sous-ledger :

```text
411000
  -> CUSTOMER:C000001
```

Exemple étendu :

```text
411000001
```

**P1**

---

# 12. Exigences - Ecritures comptables

## REQ-ENT-001 - Equilibre

```text
total_debit = total_credit
```

**P0**

---

## REQ-ENT-002 - Workflow

```text
DRAFT
  |
  v
VALIDATED
  |
  v
POSTED
  |
  v
REVERSED
```

`DRAFT -> POSTED` est interdit.

**P0**

---

## REQ-ENT-003 - Validation

Avant `VALIDATED` :

- au moins deux lignes ;
- montant total non nul ;
- débit/crédit exclusifs par ligne ;
- compte valide ;
- date valide ;
- période valide ;
- écriture équilibrée.

**P0**

---

## REQ-ENT-004 - Posting

Précondition :

```text
status == VALIDATED
```

Résultat :

```text
VALIDATED -> POSTED
```

**P0**

---

## REQ-ENT-005 - Immutabilité

Une écriture `POSTED` ou `REVERSED` n'est plus éditable.

**P0**

---

## REQ-ENT-006 - Reversal

L'extourne :

- inverse débit/crédit ;
- crée une nouvelle écriture ;
- conserve `reversal_of` ;
- ne modifie pas l'écriture d'origine.

**P0**

---

## REQ-ENT-007 - Période ouverte

Une période fermée bloque le posting.

**P0**

---

## REQ-ENT-008 - Concurrence

Le contrat doit empêcher :

```text
double validate
double post
double reverse
```

**P0**

---

# 13. Exigences - Import et ingestion comptable

## REQ-IMP-001 - Pipeline générique

```text
Source
  |
  v
RawRecord
  |
  v
Parse
  |
  v
Validate
  |
  v
Map
  |
  v
Normalize
  |
  v
JournalEntry / JournalEntryLine
```

**P1**

---

## REQ-IMP-002 - Provenance

Conserver si disponible :

```text
source_file
source_line
source_record_id
source_account
source_journal
piece_reference
auxiliary_number
auxiliary_label
```

**P1**

---

## REQ-IMP-003 - Idempotence

Stratégies possibles :

```text
file checksum
batch id
source key
normalized entry key
```

**P1**

---

## REQ-IMP-004 - Atomicité

Un import final est all-or-nothing.

Aucune comptabilité partielle.

**P0**

---

## REQ-IMP-005 - Erreurs et warnings

```text
ERROR
WARNING
INFO
```

Les erreurs bloquantes doivent empêcher l'exécution.

**P1**

---

## REQ-IMP-006 - Adapter FEC

Le package FEC optionnel doit pouvoir gérer :

- 18 colonnes réglementaires ;
- encodage ;
- raw lines ;
- SHA-256 ;
- débit/crédit ;
- regroupement des écritures ;
- mappings ;
- provenance ;
- import atomique.

Le FEC n'est pas le modèle universel d'import.

**P1**

---

# 14. Ledger et périodes

## REQ-LED-001 - Ledger par entité

Chaque ledger appartient à une entité.

## REQ-LED-002 - Plan associé

Le ledger référence une version déterminée du plan d'entreprise.

## REQ-LED-003 - Reconstruction

Les soldes sont reconstruisibles depuis les mouvements postés.

## REQ-LED-004 - Grand livre

Le grand livre expose :

```text
opening balance
debit
credit
running balance
closing balance
```

Il s'agit d'une projection.

## REQ-LED-005 - Variantes de balance

```text
BEFORE_ADJUSTMENTS
ADJUSTED
POST_CLOSING
```

La sélection des types d'écriture est explicite et testable.

---

## REQ-PER-001 - FiscalYear

Support d'un exercice comptable.

## REQ-PER-002 - AccountingPeriod

Statuts à préciser, par exemple :

```text
OPEN
CLOSING
CLOSED
LOCKED
```

---

# 15. Exigences - Contrôles comptables

## REQ-CTL-001 - Contrat de contrôle

```python
class AccountingControl(Protocol):
    code: str
    severity: ControlSeverity

    def evaluate(self, context) -> ControlResult:
        ...
```

---

## REQ-CTL-002 - Résultat structuré

```text
control_code
severity
status
expected
actual
details
evidence
```

---

## REQ-CTL-003 - Contrôles de base

```text
ENTRY_BALANCED
ACCOUNT_EXISTS
ACCOUNT_ACTIVE
PERIOD_OPEN
DEBIT_OR_CREDIT_ONLY
ENTRY_HAS_AT_LEAST_TWO_LINES
TRIAL_BALANCE_BALANCED
BALANCE_SHEET_BALANCED
CASHFLOW_RECONCILED
TEMPORARY_ACCOUNTS_CLOSED
```

---

## REQ-CTL-004 - Bloquant vs diagnostic

Un contrôle doit indiquer s'il bloque :

- validation ;
- posting ;
- clôture ;
- import ;
- export.

---

## REQ-CTL-005 - Explicabilité

Toute anomalie doit pouvoir exposer :

- règle ;
- objet ;
- attendu ;
- observé ;
- preuve ;
- provenance.

---

# 16. Exigences - Reporting

## REQ-REP-001 - Modèles réglementaires

Support de `v3_reporting`.

## REQ-REP-002 - Structure distincte du mapping

Une structure officielle peut être valide même si tous les mappings de comptes ne sont pas exécutables.

## REQ-REP-003 - Statut d'exécution

```text
EXECUTABLE
CANDIDATE
NOT_AVAILABLE
FORBIDDEN
```

## REQ-REP-004 - Fail closed

Un mapping avec validation humaine requise ne peut pas être exécuté automatiquement.

## REQ-REP-005 - Reproductibilité

Un état doit conserver :

- ledger ;
- période ;
- plan ;
- standard ;
- édition ;
- dataset ;
- mapping ;
- paramètres.

## REQ-REP-006 - Deux mappings distincts

```text
CompanyAccount
    -> RegulatoryAccountBinding
    -> ReferenceAccount
```

est différent de :

```text
CompanyAccount
    -> StatementAccountMapping
    -> StatementLine
```

## REQ-REP-007 - Mapping réglementaire de lignes

Un mapping de ligne doit pouvoir contenir :

```text
source_line
target_line
multiplier
mapping_type
confidence
validation
notes
```

Aucune similarité floue ne devient normative sans validation.

## REQ-REP-008 - ReportSnapshot

Un snapshot doit pouvoir conserver :

```text
entity
fiscal_year / period
chart_version
reference_snapshot
statement_definition
values
mappings
warnings
controls
comparatives
parameters
checksum
```

---


# 16A. Exigences - Financial Analysis & Indicators

## REQ-FIN-001 - Read-side uniquement

`Financial Analysis` ne peut pas modifier le write model comptable.

**Priorité : P1**

## REQ-FIN-002 - Définitions d'indicateurs

```text
FinancialIndicatorDefinition
    code
    label
    category
    formula / computation strategy
    dependencies
    version
    applicability
    provenance
```

**P1**

## REQ-FIN-003 - SIG

Support progressif de la marge commerciale, production, valeur ajoutée, EBE, résultat d'exploitation, RCAI, résultat exceptionnel et résultat net.

**P1**

## REQ-FIN-004 - CAF

La CAF doit pouvoir disposer de plusieurs stratégies de calcul qualifiées.

**P1**

## REQ-FIN-005 - Analyse fonctionnelle

Support de FRNG, BFRE, BFRHE, BFR et trésorerie nette à partir d'une classification fonctionnelle explicite.

**P1**

## REQ-FIN-006 - Ratios

Support de définitions versionnées pour activité, rentabilité, liquidité, structure financière et cash-flow.

**P1**

## REQ-FIN-007 - Scores et diagnostics

Une méthode de score est analytique, pas une règle comptable normative.

**P2**

## REQ-FIN-008 - Drill-down

```text
Indicator
    -> Statement / Balance components
    -> Trial Balance rows
    -> Ledger rows
    -> JournalEntryLine
```

**P1**

## REQ-FIN-009 - Frontière corporate finance

VAN, TRI, WACC, valorisation, choix d'investissement et stratégie de financement restent hors du coeur stable.

---

# 17. Crosswalks et consolidation

## REQ-XW-001

```text
code A == code B
```

ne signifie pas :

```text
semantic(A) == semantic(B)
```

## REQ-XW-002

Un crosswalk porte :

- source ;
- cible ;
- statut ;
- méthode ;
- confiance ;
- validation.

## REQ-XW-003

A terme :

```text
PCG entity
SYSCOHADA entity
EBNL entity
      |
      v
Group Chart
      |
      v
Consolidation
```

**P2**

---

# 18. Provenance et audit

## REQ-AUD-001 - Snapshot réglementaire

```python
AccountingReferenceSnapshot(
    standard_id="fr-pcg",
    edition="2026",
    dataset_version="...",
    checksum="...",
)
```

## REQ-AUD-002 - Provenance compte

```text
CompanyAccount
   -> ReferenceAccount
   -> Dataset
   -> Regulatory source
```

## REQ-AUD-003 - Audit des mutations

Conserver notamment :

```text
actor
action
entity_type
entity_id
before
after
metadata
timestamp
```

## REQ-AUD-004 - Audit des écritures

Evénements minimum :

```text
ENTRY_CREATE
ENTRY_UPDATE
ENTRY_VALIDATE
ENTRY_POST
ENTRY_REVERSE
```

Les snapshots d'écriture doivent inclure les lignes.

---

# 19. Versioning

Distinguer :

```text
PyAccountingKit version
Reference dataset release
Standard edition
Company chart version
Reporting mapping version
```

Exemple :

```text
PyAccountingKit          0.8.0
dataset release          0.7.1
standard                 fr-pcg
edition                  2026
company chart            3
report mapping           2
```

---

# 20. Exigences non fonctionnelles

## NFR-001 - Déterminisme

Même entrée => même résultat.

## NFR-002 - Idempotence

Rejouer une opération idempotente ne crée pas de doublons.

## NFR-003 - Typage fort

Privilégier :

- dataclasses ;
- enums ;
- protocols ;
- value objects ;
- objets immuables.

## NFR-004 - Framework agnostic

Le coeur ne dépend pas de Django/FastAPI.

## NFR-005 - Persistence agnostic

Ports de repositories et Unit of Work.

Adapters :

```text
InMemory
SQLAlchemy
Django ORM
PostgreSQL
```

## NFR-006 - Testabilité

Le domaine est testable sans base.

## NFR-007 - Auditabilité

Toute décision importante est explicable.

## NFR-008 - Fail closed

Une ambiguïté réglementaire ne doit jamais être transformée silencieusement en règle exécutable.

## NFR-009 - Compatibilité Python

Définie dans la stratégie de release.

## NFR-010 - Performance

Le posting ne reparcourt pas tout le référentiel.

Le ledger doit supporter des volumes importants.

## NFR-011 - Concurrence

Prévenir :

```text
double validation
double posting
double reversal
double closing
double import
```

## NFR-012 - Atomicité

Posting, reversal, closing et import doivent être all-or-nothing.

---


## NFR-013 - Versioning des policies

Toute policy ayant produit une écriture, un montant ou un indicateur doit être identifiable par une version stable.

## NFR-014 - Reproductibilité analytique

Un indicateur doit être recalculable à partir du snapshot source, de la version de définition, des mappings et des paramètres.

---

# 21. Contrats avec les sources de référence

## 21.1 `regulatory-accounting-data-framework` - runtime

Prioritaires :

```text
v1_structure
effective_plan
v3_reporting
relations
validated concepts/bindings
```

Diagnostic / audit :

```text
v0_raw
account_overlay
crosswalk
provenance
validation
```

---

## 21.2 Données non exécutables par défaut

Ne pas exécuter automatiquement :

- hints ;
- candidates ;
- similarités ;
- relations sans héritage ;
- correspondances nécessitant revue.

---

## 21.3 Métadonnées de confiance

Le provider doit exposer si disponibles :

```text
review_status
confidence
human_validation_required
auto_inference_allowed
mapping_status
provenance
```

---

## 21.4 `cfa_fra_django_mvp_sprint_7` - référence fonctionnelle

A extraire :

```text
JournalEntry / JournalLine semantics
DRAFT -> VALIDATED -> POSTED -> REVERSED
Posting
Reversal
Audit
FEC import semantics
General Ledger
Trial Balance
Financial Statements
Regulatory Statement Mapping
ReportSnapshot
golden scenarios
```

A ne pas extraire dans le coeur :

```text
Django models
Django views
Django forms
HTMX
templates
URLs
sessions
Django admin
Django ORM APIs
```

Les appels tels que `transaction.atomic` ou `select_for_update` sont des preuves d'un besoin de transaction/verrouillage, pas des APIs du domaine.

---


## 21.5 Sources doctrinales - contrat d'utilisation

Les ouvrages servent à identifier les concepts, formaliser le langage métier, recenser les traitements, construire les cas de test et détecter les frontières de sous-domaines.

Ils ne servent pas à remplacer un standard réglementaire versionné ni à autoriser une inférence normative.

Toute règle issue d'un ouvrage doit être classée parmi :

```text
UNIVERSAL_ACCOUNTING_INVARIANT
DOMAIN_POLICY
REGULATORY_RULE
REFERENCE_SPECIFIC_RULE
ACCOUNTING_METHOD
PRESENTATION_RULE
ANALYTICAL_DEFINITION
CONTROL
HEURISTIC
```

---

# 22. Modèle conceptuel initial

```text
AccountingEntity
    |
    +-- CompanyAccountingProfile
    |
    +-- Ledger
          |
          +-- CompanyChartOfAccounts
          |       |
          |       +-- CompanyAccount
          |              |
          |              +-- ReferenceAccount
          |
          +-- Journal
          |       |
          |       +-- JournalEntry
          |              |
          |              +-- JournalEntryLine
          |
          +-- AccountingPeriod
```

Imports :

```text
AccountingImportBatch
    |
    +-- SourceRecord
            |
            +-- provenance -> JournalEntryLine
```

Contrôles :

```text
AccountingControl
    |
    +-- ControlResult
```

Reporting :

```text
StatementDefinition
    |
    +-- StatementLine
            |
            +-- ReportSnapshot
```

---


Analyse financière :

```text
FinancialAnalysisDefinition
    +-- FinancialIndicatorDefinition
    +-- RatioDefinition
    +-- ScoreDefinition

AnalysisSnapshot
    +-- IndicatorValue
    +-- RatioValue
    +-- Diagnostic
```

---

# 23. Value Objects initiaux

```text
AccountId
AccountCode
ReferenceAccountId
StandardId
StandardEdition
ReferenceDatasetVersion

LedgerId
JournalId
JournalEntryId
JournalEntryLineId
AccountingEntityId

Money
Currency
ExchangeRate

DebitCredit
AccountType
AccountKind
JournalType
EntryStatus
PeriodStatus

FiscalYear
AccountingDate
PostingDate
DocumentReference

ImportBatchId
SourceRecordId
SourceReference

ControlCode
ControlSeverity

ReportSnapshotId

AccountingPolicySetId
PolicyId
PolicyVersion
MeasurementBasis
IndicatorCode
IndicatorDefinitionVersion
AnalysisSnapshotId
```

---

# 24. Cas d'usage prioritaires

## UC-001 - Charger PCG

```python
catalog.get("fr-pcg", "2026")
```

## UC-002 - Plan 8 chiffres

```text
reference 512
    |
    +-> 51200001
    +-> 51200002
```

## UC-003 - SYSCOHADA

```python
catalog.get("ohada-syscohada", "2017")
```

## UC-004 - Non-profit effectif

```python
catalog.get("fr-nonprofit", "2026")
```

## UC-005 - Poster une écriture

```text
DRAFT
 -> VALIDATED
 -> POSTED
```

## UC-006 - Extourner

```text
POSTED
 -> REVERSAL ENTRY
 -> original becomes REVERSED
```

## UC-007 - Import FEC

```text
FEC
 -> Raw
 -> Validation
 -> Mapping
 -> Normalization
 -> Atomic Journal Import
```

## UC-008 - Grand livre et balance

```text
POSTED lines
 -> General Ledger
 -> Trial Balance
```

## UC-009 - Etat réglementaire

Appliquer uniquement les mappings exécutables.

## UC-010 - Snapshot

Produire un package de reporting sérialisable et reproductible.

---


## UC-011 - Appliquer une policy d'évaluation

```text
Accounting Event
    -> RecognitionPolicy
    -> MeasurementPolicy
    -> generated JournalEntry
    -> Posting
```

## UC-012 - Calculer des SIG et ratios

```text
POSTED lines
    -> Trial Balance
    -> Financial Statements
    -> Financial Analysis
    -> SIG / CAF / FRNG / BFR / Ratios
```

Le calcul ne modifie aucune donnée comptable.

---

# 25. Critères d'acceptation du premier socle stable

Le premier socle doit démontrer qu'il est possible de :

- charger PCG 2026 ;
- charger SYSCOHADA 2017 ;
- représenter leur hiérarchie ;
- conserver les IDs réglementaires ;
- créer deux plans entreprise de longueurs différentes ;
- créer des comptes custom ;
- conserver leur filiation ;
- créer un journal ;
- créer une écriture ;
- refuser une écriture déséquilibrée ;
- imposer `DRAFT -> VALIDATED -> POSTED` ;
- empêcher la modification après posting ;
- extourner en conservant le lien d'origine ;
- produire un grand livre ;
- produire une balance ;
- produire les trois variantes de balance ;
- reconstruire les soldes ;
- enregistrer un snapshot réglementaire ;
- refuser un mapping candidat ;
- conserver la provenance d'un import ;
- garantir atomicité d'une opération critique ;
- exécuter au moins un golden scenario issu de CFA FRA ;
- générer un `ReportSnapshot` ;
- sélectionner un `AccountingPolicySet` versionné ;
- démontrer une policy de mesure produisant une écriture traçable ;
- calculer au moins un indicateur financier depuis une projection sans mutation du ledger ;
- distinguer une définition analytique d'une règle réglementaire.

---

# 26. Risques

## RISK-001 - Confusion référentiel / plan entreprise

Réponse : `ReferenceAccount` != `CompanyAccount`.

## RISK-002 - Longueur figée

Réponse : `AccountCodePolicy`.

## RISK-003 - Inférence par préfixe

Réponse : mapping/configuration explicite.

## RISK-004 - Duplication réglementaire

Réponse : provider externe.

## RISK-005 - Mapping candidat exécuté

Réponse : statut d'exécution et fail closed.

## RISK-006 - Migration d'édition

Réponse : migration explicite et versionnée.

## RISK-007 - Couplage à Django

Réponse : domain/application/ports/adapters.

## RISK-008 - Généralisation abusive de CFA FRA

Réponse : les heuristiques deviennent `SuggestionStrategy` ou `MigrationHeuristic`.

## RISK-009 - Confusion des mappings

Réponse : `RegulatoryAccountBinding` distinct de `StatementAccountMapping`.

## RISK-010 - Divergence par rapport au moteur de référence

Réponse : golden tests et scénarios de non-régression.

---


## RISK-011 - Méthode comptable transformée en invariant universel

**Réponse** : `AccountingPolicySet` + qualification de la portée de chaque règle.

## RISK-012 - Analyse financière contaminant le write-side

**Réponse** : `Financial Analysis` reste downstream et read-only.

## RISK-013 - Périmètre dérivant vers toute la corporate finance

**Réponse** : frontière explicite et extensions optionnelles.

---

# 27. Questions ouvertes

1. format canonique de `ReferenceCatalog` ;
2. distribution des datasets ;
3. cache local ;
4. checksum/signature ;
5. version du plan entreprise ;
6. migration d'édition ;
7. modèle auxiliaire par défaut ;
8. multi-devise initiale ;
9. séquence des écritures ;
10. événements de domaine ;
11. crosswalks en 1.0 ;
12. consolidation ;
13. bindings de concepts ;
14. frontière import générique / FEC ;
15. contrat de `UnitOfWork` ;
16. stratégie de concurrence ;
17. sémantique définitive des variantes de balance ;
18. niveau de compatibilité CFA FRA ;
19. format canonique `ReportSnapshot` ;
20. stratégie de golden tests ;
21. modèle exact de `AccountingPolicySet` ;
22. matrice `standard -> policy` ;
23. versioning des méthodes d'évaluation ;
24. format du `PolicyExecutionTrace` ;
25. définition canonique des indicateurs analytiques ;
26. périmètre exact entre Financial Analysis et Corporate Finance.

---


# 28. Priorisation

## P0 - Fondations indispensables

```text
Core primitives
ReferenceProvider / ReferenceCatalog / ReferenceAccount
AccountingPolicySet / RecognitionPolicy / MeasurementPolicy
CompanyAccount / CompanyChartOfAccounts / CompanyAccountingProfile
AccountCodePolicy
Journal / JournalEntry / JournalEntryLine
EntryValidator / PostingEngine / ReversalEngine
Ledger / AccountingPeriod / GeneralLedgerQuery / TrialBalanceQuery
AccountingControl / ControlResult
Audit snapshot / transaction boundaries
```

## P1 - Capacités structurantes

```text
accruals / provisions / adjustments
segmented account codes / auxiliary accounting
generic import contracts / FEC adapter
financial statements / regulatory reporting / report snapshots
Financial Analysis
SIG / EBE / CAF
FRNG / BFR / Net Treasury / ratios
concept bindings / multi-currency
SQLAlchemy / Django / FastAPI adapters
```

## P2 - Capacités avancées

```text
financial scoring
crosswalks / group chart / multi-standard consolidation
fixed assets / inventory specialization / tax engine
advanced reconciliation
migration assistance
corporate-finance extensions
```

---


# 29. Architecture documentaire proposée

```text
00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md
    [MAJ P0.1 - présent document]

01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md
    [MAJ P0.2]

02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md
    [MAJ P0.3]

03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md
04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md
05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md
06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md
07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md
08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md
09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md
10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md
11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md

12_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md
13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md
14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md
15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md
16_PYACCOUNTINGKIT_PUBLIC_API_DESIGN.md
17_PYACCOUNTINGKIT_RELEASE_AND_VERSIONING_STRATEGY.md
18_PYACCOUNTINGKIT_CFA_FRA_EXTRACTION_AND_MIGRATION_MAP.md
19_PYACCOUNTINGKIT_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX.md
20_PYACCOUNTINGKIT_ADR_REGISTER.md
21_PYACCOUNTINGKIT_CONSOLIDATION_ARCHITECTURE.md
22_PYACCOUNTINGKIT_RECONCILIATION_ARCHITECTURE.md
23_PYACCOUNTINGKIT_ADVANCED_FINANCIAL_ANALYSIS_BOUNDARIES.md
```

Séquence P0 :

```text
MAJ 00
  -> MAJ 01
  -> MAJ 02
  -> 03 Rules & Invariants
  -> 04 Accounting Policies / Recognition / Measurement
  -> 05 Reference Data
  -> 06 Company COA
  -> 07 Ledger / Posting / Reversal
  -> 08 Closing / Accruals / Provisions
  -> 09 Controls / Audit
  -> 10 Persistence / Concurrency
  -> 11 Testing
```

---

# 30. Décisions architecturales actées

| ID | Décision |
|---|---|
| ADR-REQ-001 | `regulatory-accounting-data-framework` est la source réglementaire amont |
| ADR-REQ-002 | PyAccountingKit ne duplique pas les plans réglementaires |
| ADR-REQ-003 | `ReferenceAccount` et `CompanyAccount` sont distincts |
| ADR-REQ-004 | `AccountCode` est une chaîne |
| ADR-REQ-005 | La longueur des comptes est configurable |
| ADR-REQ-006 | La longueur peut varier selon la famille |
| ADR-REQ-007 | La sémantique ne découle pas uniquement du code |
| ADR-REQ-008 | Les mappings non validés ne sont pas exécutables |
| ADR-REQ-009 | Les écritures postées sont immuables |
| ADR-REQ-010 | Toute écriture postée est équilibrée |
| ADR-REQ-011 | Egalité de code != équivalence sémantique |
| ADR-REQ-012 | L'héritage réglementaire doit être explicite |
| ADR-REQ-013 | Le plan entreprise conserve un snapshot du référentiel |
| ADR-REQ-014 | CFA FRA Sprint 7 est une référence fonctionnelle, pas une dépendance |
| ADR-REQ-015 | Le noyau canonique minimal repose sur Account/Period/Entry/Line |
| ADR-REQ-016 | Ledger, balance et états sont des projections |
| ADR-REQ-017 | Les transitions critiques sont transactionnelles et sûres en concurrence |
| ADR-REQ-018 | FEC est un adapter optionnel |
| ADR-REQ-019 | Les heuristiques de préfixe sont non normatives |
| ADR-REQ-020 | Mapping réglementaire et mapping d'état sont distincts |
| ADR-REQ-021 | Les publications de reporting peuvent être figées dans un snapshot |
| ADR-REQ-022 | Les ouvrages sont des sources doctrinales, non des sources réglementaires actuelles |
| ADR-REQ-023 | Les règles dépendantes d'une méthode sont modélisées via `AccountingPolicySet` |
| ADR-REQ-024 | Reconnaissance, mesure, posting, présentation et analyse sont distincts |
| ADR-REQ-025 | `Financial Analysis` est downstream et read-only |
| ADR-REQ-026 | SIG, CAF, FRNG, BFR et ratios sont des définitions analytiques versionnables |
| ADR-REQ-027 | VAN, TRI, WACC et valorisation sont hors du coeur obligatoire |

---

# 31. Définition de succès

PyAccountingKit doit permettre :

```text
1 moteur comptable
        +
N référentiels réglementaires
        +
N plans entreprise
        +
N politiques de codification
        +
N AccountingPolicySets / méthodes de mesure
        +
N formats d'import
        +
N adapters techniques
        +
une suite de scénarios comptables reproductibles
        +
un read-side d'analyse financière traçable
```

sans couplage structurel entre ces dimensions.

La chaîne cible :

```text
Regulatory Reference
        |
        v
Company Accounting Model
        |
        v
Accounting Execution
        |
        v
Ledger / Controls
        |
        v
Financial / Regulatory Reporting
        |
        v
Application Adapters
```

---


# 32. Conclusion

PyAccountingKit n'a pas vocation à créer un nouveau plan comptable ni à devenir une suite universelle de corporate finance.

Il doit fournir le moteur qui permet :

1. de consommer des référentiels réglementaires externes, versionnés et qualifiés ;
2. de transformer ces référentiels en plans opérationnels propres aux organisations ;
3. d'appliquer des policies explicites de reconnaissance et de mesure ;
4. d'exécuter des écritures en partie double avec des invariants stricts ;
5. de reconstruire ledger, balances et états depuis la source canonique ;
6. de tracer imports, mutations, policies et publications ;
7. de généraliser les comportements déjà éprouvés dans `cfa_fra_django_mvp_sprint_7` ;
8. de dériver des indicateurs d'analyse financière sans contaminer le write-side comptable.

La cible devient :

```text
NIVEAU 1 - REGULATORY REFERENCE
    regulatory-accounting-data-framework

NIVEAU 2 - ACCOUNTING POLICIES & MEASUREMENT
    recognition / measurement / depreciation / impairment / accruals

NIVEAU 3 - COMPANY ACCOUNTING MODEL
    CompanyChartOfAccounts / CompanyAccount / policies

NIVEAU 4 - ACCOUNTING EXECUTION
    Journal / Entry / Posting / Reversal / Ledger / Closing

NIVEAU 5 - REPORTING & CONTROL
    Financial Statements / Regulatory Reporting / Controls / Audit

NIVEAU 6 - FINANCIAL ANALYSIS
    SIG / EBE / CAF / FRNG / BFR / Ratios / Diagnostics

NIVEAU 7 - APPLICATION ADAPTERS
    Django / FastAPI / SQLAlchemy / PostgreSQL / FEC / CLI
```

La corporate finance avancée reste une extension possible au-delà de ce périmètre.

---

**Prochaine action recommandée :**

```text
MAJ 01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md
```

afin d'aligner la macro-architecture avec `Accounting Policies & Measurement` et `Financial Analysis`.
