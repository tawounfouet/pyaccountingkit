# 01 - PyAccountingKit - Vision du projet et architecture cible

> **Projet** : PyAccountingKit  
> **Document** : `01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`  
> **Document parent** : `00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`  
> **Statut** : Architecture cible - version de cadrage  
> **Langue** : Français  
> **Objet** : Définir la vision produit, les principes d'architecture, les frontières de responsabilité, la structure logique, les dépendances autorisées et la trajectoire d'extraction du moteur comptable PyAccountingKit.

---

# 1. Résumé exécutif

PyAccountingKit est destiné à devenir un **framework Python générique de comptabilité financière**.

Son objectif n'est pas de fournir une application comptable complète, un ERP, une interface utilisateur ou un plan comptable réglementaire codé en dur.

PyAccountingKit doit fournir un **moteur comptable réutilisable** capable de :

```text
charger un référentiel réglementaire
        |
        v
construire le modèle comptable d'une organisation
        |
        v
gérer comptes / journaux / périodes
        |
        v
valider et comptabiliser les écritures
        |
        v
reconstruire ledger / balance
        |
        v
exécuter les contrôles
        |
        v
produire les états financiers
        |
        v
appliquer les présentations réglementaires
        |
        v
conserver une trace reproductible et auditable
```

La conception repose sur deux actifs existants complémentaires :

```text
regulatory-accounting-data-framework
        = source de vérité réglementaire

cfa_fra_django_mvp_sprint_7
        = référence fonctionnelle exécutable
```

PyAccountingKit constitue la couche générique située entre ces deux mondes :

```text
           REGULATORY DATA
                  |
                  v
       +-----------------------+
       |    PyAccountingKit    |
       |  Accounting Engine    |
       +-----------------------+
                  ^
                  |
        EXECUTABLE BEHAVIOR
```

Le framework devra conserver les comportements comptables validés dans CFA FRA tout en supprimant leur couplage à Django, HTMX et l'ORM.

Il devra également consommer les référentiels issus de `regulatory-accounting-data-framework` sans recopier ni réinterpréter arbitrairement leurs données.

---

# 2. Vision du produit

## 2.1 Vision

La vision cible est :

> **Fournir une infrastructure Python de comptabilité financière permettant de construire des produits comptables fiables, auditables et multi-référentiels sans réimplémenter le moteur comptable à chaque projet.**

Le framework doit permettre à une application de se concentrer sur :

- son UX ;
- ses workflows métier spécifiques ;
- ses intégrations ;
- son stockage ;
- son orchestration ;

tout en déléguant à PyAccountingKit :

- les invariants comptables ;
- les transitions de cycle de vie ;
- le posting ;
- le reversal ;
- le ledger ;
- les balances ;
- les contrôles ;
- la logique générique de reporting ;
- les contrats de référentiels ;
- les contrats d'import ;
- l'audit métier.

---

## 2.2 Positionnement

PyAccountingKit n'est ni :

```text
ERP
logiciel comptable complet
Django application
moteur fiscal
base réglementaire
outil de consolidation complet
UI
```

PyAccountingKit est :

```text
Domain Library
+
Application Services
+
Ports
+
Reference Integration Contracts
+
Optional Adapters
```

---

## 2.3 Produits pouvant utiliser PyAccountingKit

Le moteur doit être utilisable par :

```text
ERP
Accounting SaaS
Fintech
Billing Platform
Association Management System
Cooperative Management System
Back-office Finance
Reconciliation Platform
Data / Finance Platform
Django Application
FastAPI Service
Batch / CLI
```

---

# 3. Sources architecturales

## 3.1 `regulatory-accounting-data-framework`

Ce projet fournit la couche réglementaire.

Les familles de données pertinentes sont notamment :

```text
structured
effective plans
account overlays
reporting
relations
crosswalks
concepts
validation
provenance
```

PyAccountingKit doit les traiter comme des **données externes versionnées**.

Le moteur ne doit pas :

- recopier les comptes réglementaires dans son code source ;
- reconstituer un plan effectif si un artefact effectif est déjà publié ;
- inférer un héritage réglementaire non déclaré ;
- considérer deux comptes de même code comme automatiquement équivalents ;
- exécuter un mapping candidat comme s'il était validé.

---

## 3.2 `cfa_fra_django_mvp_sprint_7`

Le projet CFA FRA apporte une référence d'exécution déjà éprouvée.

Les principes particulièrement importants à conserver sont :

```text
source comptable canonique
projections calculées
services pour les mutations
selectors pour les lectures
validation avant posting
immutabilité après posting
reversal au lieu de modification
transactions sur mutations critiques
audit des transitions
import avec provenance
ledger reconstruit depuis les lignes
reporting reconstruit depuis les balances et mappings
snapshots de reporting
```

Le projet démontre également que :

```text
JournalEntry
JournalLine
Account
AccountingPeriod
```

peuvent former le noyau minimal de la source comptable, les autres structures de restitution étant calculées.

---

# 4. Triangle architectural fondateur

L'architecture cible doit préserver trois responsabilités.

```text
+------------------------------------------------------+
| regulatory-accounting-data-framework                 |
|                                                      |
| Standards / structures / reporting / provenance      |
| relations / crosswalks / validation                  |
+-------------------------+----------------------------+
                          |
                          | reference datasets
                          v
+------------------------------------------------------+
| PyAccountingKit                                      |
|                                                      |
| Generic accounting domain                           |
| application services                                |
| ports                                                |
| accounting controls                                 |
| reporting engine                                    |
| reference contracts                                 |
+-------------------------+----------------------------+
                          ^
                          |
                          | behavioral reference
+-------------------------+----------------------------+
| cfa_fra_django_mvp_sprint_7                          |
|                                                      |
| implemented workflows / scenarios / tests / UX       |
| Django integration / FEC / ledger / statements       |
+------------------------------------------------------+
```

Règle :

```text
regulatory framework
    -> fournit les données de référence

CFA FRA
    -> fournit des comportements éprouvés

PyAccountingKit
    -> définit l'abstraction générique
```

---

# 5. Principes d'architecture

## ARCH-001 - Domain-first

La logique comptable doit être définie avant les préoccupations :

```text
HTTP
ORM
database
framework web
UI
message broker
```

Le domaine ne doit pas importer Django ou SQLAlchemy.

---

## ARCH-002 - Framework agnostic

Le coeur doit pouvoir fonctionner dans un simple script :

```python
entry = JournalEntry.create(...)
entry.validate(...)
posting_engine.post(entry)
```

sans initialisation Django.

---

## ARCH-003 - Persistence agnostic

Le domaine ne doit pas connaître :

```text
PostgreSQL
SQLite
Django ORM
SQLAlchemy
Redis
```

Il doit connaître des ports :

```text
AccountRepository
JournalEntryRepository
UnitOfWork
ReferenceProvider
AuditPort
```

---

## ARCH-004 - Reference-data-driven

Les standards comptables ne sont pas des constantes Python.

Ils sont chargés par :

```text
AccountingReferenceProvider
        |
        v
ReferenceCatalog
```

---

## ARCH-005 - Source canonique unique

Les écritures et lignes postées constituent la base des projections comptables.

Les objets suivants ne doivent pas devenir des sources primaires indépendantes :

```text
General Ledger
Trial Balance
Balance Sheet
Income Statement
Cash Flow
```

---

## ARCH-006 - Append-oriented accounting

Une opération postée est immuable.

Les corrections passent par de nouveaux événements comptables :

```text
original entry
    +
reversal entry
    +
replacement entry
```

---

## ARCH-007 - Deterministic projections

A données identiques, paramètres identiques et référentiel identique :

```text
ledger
balance
financial statements
controls
```

doivent produire les mêmes résultats.

---

## ARCH-008 - Explicit policies

Les variations organisationnelles doivent être des politiques explicites.

Exemples :

```text
AccountCodePolicy
AuxiliaryAccountingPolicy
PostingPolicy
PeriodPolicy
NumberingPolicy
MappingPolicy
```

Elles ne doivent pas être cachées dans des conditions dispersées.

---

## ARCH-009 - Fail closed

Une ambiguïté réglementaire ou métier ne doit pas être résolue silencieusement.

```text
unknown mapping
    -> explicit error / candidate

unvalidated regulatory rule
    -> non executable
```

---

## ARCH-010 - Audit by design

Les opérations sensibles doivent produire suffisamment d'information pour reconstruire :

```text
qui
quoi
quand
sur quel objet
avant
après
pourquoi
avec quelle source
```

---

# 6. Style architectural cible

PyAccountingKit adopte une architecture inspirée de :

```text
Domain-Driven Design
Hexagonal Architecture
Ports and Adapters
Application Services
CQRS-lite
```

Le terme `CQRS-lite` signifie ici une séparation claire entre :

```text
commands / mutations
        !=
queries / projections
```

sans imposer :

- Event Sourcing ;
- bus distribué ;
- base séparée ;
- infrastructure complexe.

---

# 7. Architecture en couches

```text
+------------------------------------------------------+
|                 Public API                          |
|  pyaccountingkit.* imports / facades / commands     |
+------------------------------------------------------+
                         |
                         v
+------------------------------------------------------+
|              Application Layer                     |
| Commands / Queries / Use Cases / Orchestration      |
+------------------------------------------------------+
                         |
                         v
+------------------------------------------------------+
|                  Domain Layer                      |
| Entities / Aggregates / VO / Policies / Rules       |
+------------------------------------------------------+
                         ^
                         |
+------------------------------------------------------+
|                     Ports                           |
| Repositories / UoW / Reference / Audit / Clock      |
+------------------------------------------------------+
                         ^
                         |
+------------------------------------------------------+
|                    Adapters                         |
| InMemory / SQLAlchemy / Django / FEC / HTTP Ref     |
+------------------------------------------------------+
```

---

# 8. Règles de dépendance

La règle fondamentale :

```text
adapters
    -> application
        -> domain
```

et :

```text
domain
    X-> adapters
domain
    X-> Django
domain
    X-> SQLAlchemy
domain
    X-> FastAPI
```

Matrice :

| Couche | Peut dépendre de |
|---|---|
| `core` | stdlib / abstractions internes |
| `domain` | `core` |
| `application` | `domain`, `ports`, `core` |
| `ports` | `domain`, `core` |
| `adapters` | `application`, `ports`, `domain` |
| `integrations` | adapters et libs externes |
| applications clientes | API publique PyAccountingKit |

---

# 9. Architecture logique du domaine

Le découpage de haut niveau proposé est :

```text
Accounting Identity & Organization
Chart of Accounts
Journal & Entries
Posting & Reversal
Periods & Closing
Ledger & Balances
Accounting Imports
Controls
Audit
Financial Statements
Regulatory References
Regulatory Reporting
Reconciliation
```

Le détail des bounded contexts sera défini dans :

```text
02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md
```

---

# 10. Noyau comptable canonique

Le noyau minimal cible reprend le principe éprouvé dans CFA FRA :

```text
AccountingEntity
        |
        +-- AccountingPeriod
        |
        +-- CompanyChartOfAccounts
        |       |
        |       +-- Account
        |
        +-- Journal
                |
                +-- JournalEntry
                        |
                        +-- JournalEntryLine
```

Les objets suivants sont des projections :

```text
Journal Report
General Ledger
Trial Balance
Financial Statements
Analytics
```

---

# 11. Architecture proposée du package

```text
pyaccountingkit/
|
+-- src/
|   |
|   +-- pyaccountingkit/
|       |
|       +-- core/
|       |   +-- ids.py
|       |   +-- money.py
|       |   +-- currency.py
|       |   +-- clock.py
|       |   +-- errors.py
|       |   +-- result.py
|       |
|       +-- domain/
|       |   |
|       |   +-- entities/
|       |   +-- accounts/
|       |   +-- journals/
|       |   +-- entries/
|       |   +-- periods/
|       |   +-- posting/
|       |   +-- ledger/
|       |   +-- controls/
|       |   +-- reporting/
|       |   +-- references/
|       |   +-- audit/
|       |
|       +-- application/
|       |   |
|       |   +-- commands/
|       |   +-- queries/
|       |   +-- services/
|       |   +-- dto/
|       |
|       +-- ports/
|       |   |
|       |   +-- repositories/
|       |   +-- unit_of_work.py
|       |   +-- references.py
|       |   +-- audit.py
|       |   +-- clock.py
|       |   +-- storage.py
|       |
|       +-- adapters/
|       |   |
|       |   +-- memory/
|       |   +-- regulatory/
|       |   +-- imports/
|       |
|       +-- integrations/
|       |   |
|       |   +-- sqlalchemy/
|       |   +-- django/
|       |   +-- fec/
|       |   +-- fastapi/
|       |
|       +-- public/
|           +-- accounting.py
|           +-- references.py
|           +-- reporting.py
|
+-- tests/
|   +-- unit/
|   +-- contract/
|   +-- integration/
|   +-- golden/
|
+-- examples/
+-- docs/
+-- pyproject.toml
+-- README.md
```

Cette structure reste une cible logique. Les détails de packaging seront figés lors du bootstrap du repository.

---

# 12. `core`

`core` contient uniquement des primitives transverses sans connaissance d'un domaine réglementaire particulier.

Exemples :

```text
Typed IDs
Money
Currency
Clock
Decimal policies
Errors
Result
Date primitives
```

Contraintes :

```text
core
    X-> domain business modules
    X-> Django
    X-> SQLAlchemy
```

---

# 13. `domain`

`domain` porte les règles comptables.

Exemples :

```text
Account
CompanyChartOfAccounts
Journal
JournalEntry
JournalEntryLine
AccountingPeriod
FiscalYear
PostingPolicy
ReversalPolicy
ControlRule
StatementDefinition
```

Le domaine décide :

```text
peut-on valider ?
peut-on poster ?
peut-on reverser ?
l'écriture est-elle équilibrée ?
le compte est-il postable ?
la période accepte-t-elle le posting ?
```

Il ne décide pas :

```text
comment écrire dans PostgreSQL ?
quelle route HTTP appeler ?
quel formulaire afficher ?
```

---

# 14. `application`

La couche application orchestre les cas d'usage.

Exemples :

```text
CreateJournalEntry
ValidateJournalEntry
PostJournalEntry
ReverseJournalEntry
BuildGeneralLedger
BuildTrialBalance
LoadAccountingReference
CreateCompanyChart
RunAccountingControls
GenerateFinancialStatements
```

Elle peut utiliser :

```text
repositories
UnitOfWork
Clock
AuditPort
ReferenceProvider
```

---

# 15. Commands et queries

La séparation expérimentée dans CFA FRA entre services et selectors est généralisée.

## Commands

Mutations :

```text
create
validate
post
reverse
close
import
map
```

## Queries

Lectures :

```text
journal
ledger
trial balance
statement
audit history
reference lookup
```

Règle :

```text
query
    -> ne modifie pas le domaine

command
    -> mutation contrôlée et transactionnelle
```

---

# 16. Ports

Les ports décrivent les capacités externes requises.

Exemple :

```python
class JournalEntryRepository(Protocol):
    def get(self, entry_id): ...
    def save(self, entry): ...

class UnitOfWork(Protocol):
    def __enter__(self): ...
    def commit(self): ...
    def rollback(self): ...

class AccountingReferenceProvider(Protocol):
    def get_standard(self, standard_id, edition): ...
```

Ports principaux prévus :

```text
AccountRepository
JournalRepository
JournalEntryRepository
AccountingPeriodRepository
CompanyChartRepository

UnitOfWork
AuditPort
AccountingReferenceProvider
Clock
IdFactory
ObjectStoragePort
```

---

# 17. Adapters

Les adapters implémentent les ports.

```text
ports
  ^
  |
adapters
```

Exemples :

```text
InMemoryJournalEntryRepository
SQLAlchemyJournalEntryRepository
DjangoJournalEntryRepository

FilesystemReferenceProvider
HttpReferenceProvider
S3ReferenceProvider

InMemoryAuditAdapter
DatabaseAuditAdapter
```

---

# 18. Intégration avec `regulatory-accounting-data-framework`

## 18.1 Principe

PyAccountingKit ne doit pas dépendre des chemins physiques du repository réglementaire.

Eviter :

```python
Path("../regulatory-accounting-data-framework/datasets")
```

dans le domaine.

Utiliser :

```text
AccountingReferenceProvider
```

---

## 18.2 Flux

```text
regulatory-accounting-data-framework
        |
        v
published dataset
        |
        v
AccountingReferenceProvider
        |
        v
ReferenceCatalog
        |
        v
ReferenceStandard
        |
        v
CompanyChartBuilder
        |
        v
CompanyChartOfAccounts
```

---

## 18.3 Types d'adapters

```text
LocalFilesystemReferenceProvider
PackageReferenceProvider
HttpReferenceProvider
ObjectStorageReferenceProvider
InMemoryReferenceProvider
```

---

## 18.4 Snapshot

Toute instanciation importante doit pouvoir enregistrer :

```text
standard_id
edition
dataset_version
checksum
loaded_at
provider metadata
```

---

# 19. Référentiel vs plan entreprise

Le modèle cible sépare explicitement :

```text
ReferenceAccount
        |
        | instantiated / mapped
        v
CompanyAccount
```

Exemple :

```text
Reference
    fr-pcg:2026:512
            |
            +----------------------+
            |                      |
            v                      v
Company A                   Company B
512001                      512000001
```

Les deux comptes peuvent référencer le même concept réglementaire tout en ayant des politiques de codification différentes.

---

# 20. Architecture de génération du plan entreprise

```text
ReferenceChart
       |
       +
CompanyAccountingProfile
       |
       +-- AccountCodePolicy
       +-- segmentation
       +-- auxiliary policy
       +-- custom accounts
       +-- exclusions
       |
       v
CompanyChartBuilder
       |
       v
CompanyChartOfAccounts
```

Le détail sera traité dans :

```text
05_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md
```

---

# 21. Architecture des écritures

Pipeline conceptuel :

```text
Create
  |
  v
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

Une transition critique doit être exécutée dans une frontière transactionnelle.

---

# 22. Posting Engine

Le `PostingEngine` doit rester une capacité métier indépendante de la persistance.

Pseudo-flux :

```text
load entry
    |
    v
verify current state
    |
    v
verify period
    |
    v
verify accounts
    |
    v
verify lines
    |
    v
verify debit = credit
    |
    v
transition to POSTED
    |
    v
audit
    |
    v
commit
```

---

# 23. Concurrence

Le projet CFA FRA montre qu'un besoin de verrouillage existe autour des transitions critiques.

PyAccountingKit doit formaliser le besoin sans imposer l'outil.

```text
Domain / Application
    -> expects atomic state transition

Django adapter
    -> transaction.atomic + select_for_update

SQLAlchemy adapter
    -> transaction + SELECT FOR UPDATE

other adapter
    -> equivalent mechanism
```

Cas à protéger :

```text
double validate
double post
double reverse
double close
double import
```

---

# 24. Ledger

Le ledger est reconstruit depuis les lignes postées.

```text
POSTED JournalEntryLine
        |
        v
General Ledger Query
        |
        v
running balances
        |
        v
Trial Balance
```

Le framework pourra optimiser le calcul, mais toute optimisation doit rester reconstruisible depuis la source canonique.

---

# 25. Variantes de balance

Les variantes identifiées dans CFA FRA deviennent des concepts du moteur :

```text
BEFORE_ADJUSTMENTS
ADJUSTED
POST_CLOSING
```

Leur définition exacte sera documentée dans :

```text
06_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md
```

---

# 26. Imports

Le coeur ne connaît pas FEC.

Il connaît un pipeline générique :

```text
External Source
      |
      v
Raw Accounting Records
      |
      v
Parser
      |
      v
Validation
      |
      v
Mapping
      |
      v
Normalization
      |
      v
JournalEntry
```

FEC devient :

```text
FECAdapter
```

---

# 27. FEC adapter

Le module FEC pourra reprendre les comportements éprouvés dans CFA FRA :

```text
file preservation
SHA-256
raw lines
column validation
account mapping
journal mapping
normalized entry keys
idempotence
atomic import
source traceability
```

Mais il reste optionnel.

---

# 28. Contrôles

Architecture :

```text
AccountingContext
       |
       v
AccountingControl
       |
       v
ControlResult
```

Exemples :

```text
ENTRY_BALANCED
ACCOUNT_ACTIVE
PERIOD_OPEN
TRIAL_BALANCE_BALANCED
BALANCE_SHEET_BALANCED
CASHFLOW_RECONCILED
```

Les contrôles peuvent intervenir :

```text
before validation
before posting
before closing
before import
before export
diagnostic only
```

---

# 29. Audit

L'audit doit être un service transversal.

```text
Domain Mutation
      |
      +--> Domain result
      |
      +--> AuditEvent
```

Données minimales :

```text
event type
entity type
entity id
actor
timestamp
before
after
metadata
source
correlation id
```

---

# 30. Financial Statements Engine

Le moteur d'états financiers est une projection de données comptables.

```text
POSTED lines
    |
    v
Trial Balance
    |
    +
StatementAccountMapping
    |
    v
StatementDefinition
    |
    v
Financial Statement
```

Les états principaux :

```text
Income Statement
Balance Sheet
Cash Flow
```

Le support des changements de capitaux propres pourra être ajouté ultérieurement.

---

# 31. Séparation des mappings

Deux relations distinctes sont nécessaires.

## 31.1 Regulatory account binding

```text
CompanyAccount
      |
      v
ReferenceAccount
```

Question :

> A quel compte/concept réglementaire ce compte entreprise est-il rattaché ?

## 31.2 Statement mapping

```text
CompanyAccount / Balance
      |
      v
StatementLine
```

Question :

> Dans quelle rubrique de l'état financier ce solde doit-il être présenté ?

Ces relations ne doivent pas être fusionnées.

---

# 32. Regulatory Reporting

Pipeline :

```text
Financial Statement
        |
        v
RegulatoryStatementMapping
        |
        v
Target Regulatory Statement
        |
        v
Controls
        |
        v
ReportSnapshot
        |
        v
Export Adapter
```

Les mappings doivent pouvoir porter :

```text
mapping type
multiplier
confidence
validation
notes
```

---

# 33. ReportSnapshot

Un snapshot doit être un objet immuable représentant le contexte exact de publication.

```text
ReportSnapshot
|
+-- entity
+-- fiscal year / period
+-- chart version
+-- accounting reference snapshot
+-- statement definition
+-- mappings
+-- lines / values
+-- warnings
+-- controls
+-- comparatives
+-- parameters
+-- checksum
```

Il constitue une trace fonctionnelle reproductible.

---

# 34. Public API

L'API publique doit être plus stable que l'organisation interne.

Exemple visé :

```python
from pyaccountingkit import AccountingEngine
from pyaccountingkit.money import Money

engine = AccountingEngine(...)

entry = engine.entries.create(...)
engine.entries.validate(entry.id)
engine.entries.post(entry.id)

balance = engine.ledger.trial_balance(...)
```

Une façade haut niveau peut coexister avec des APIs domain/application plus fines.

Le design précis sera traité dans :

```text
16_PYACCOUNTINGKIT_PUBLIC_API_DESIGN.md
```

---

# 35. Gestion des dépendances optionnelles

Le package principal doit éviter les dépendances lourdes.

Proposition conceptuelle :

```text
pyaccountingkit
    -> core runtime

pyaccountingkit[sqlalchemy]
pyaccountingkit[django]
pyaccountingkit[fec]
pyaccountingkit[fastapi]
```

La stratégie exacte sera décidée lors du packaging.

Principe :

```text
optional integration
    !=
mandatory dependency
```

---

# 36. Stratégie d'extraction de CFA FRA

Le projet CFA FRA ne doit pas être réécrit d'un seul bloc.

Une extraction progressive est préférable.

```text
CFA FRA Django
      |
      v
identify behavior
      |
      v
create PyAccountingKit abstraction
      |
      v
golden test
      |
      v
implement framework
      |
      v
create Django adapter
      |
      v
switch CFA FRA to framework
```

---

# 37. Ordre d'extraction recommandé

## Lot A - primitives

```text
Money
AccountCode
Typed IDs
Clock
Errors
```

## Lot B - entries

```text
JournalEntry
JournalEntryLine
validation
```

## Lot C - posting

```text
PostingEngine
ReversalEngine
```

## Lot D - ledger

```text
GeneralLedgerQuery
TrialBalanceQuery
```

## Lot E - imports

```text
generic import
FEC adapter
```

## Lot F - controls

```text
AccountingControl
ControlResult
```

## Lot G - reporting

```text
StatementDefinition
StatementMapping
FinancialStatements
```

## Lot H - regulatory integration

```text
ReferenceProvider
RegulatoryReporting
ReportSnapshot
```

---

# 38. Golden tests

Chaque extraction importante doit disposer d'une preuve de parité.

Exemple :

```text
CFA FRA scenario
       |
       +--> revenue
       +--> net income
       +--> ending cash
       +--> total assets
       |
       v
PyAccountingKit
       |
       v
same expected results
```

Les scénarios existants doivent être transformés en fixtures de référence lorsque les données sont disponibles.

---

# 39. Ce que PyAccountingKit doit conserver de CFA FRA

A conserver conceptuellement :

```text
services for mutations
selectors / queries for projections
strict entry workflow
reversal
audit
transactional critical mutations
source traceability
ledger reconstruction
financial statement mappings
regulatory mapping
snapshots
golden tests
```

---

# 40. Ce que PyAccountingKit ne doit pas conserver dans le coeur

```text
Django Models
Django Forms
Django Views
HTMX
URL routing
templates
admin
sessions
PostgreSQL-specific API
request objects
CSS / JS
```

Ces éléments restent dans des applications ou adapters.

---

# 41. Héritage des heuristiques

Certaines règles de CFA FRA utilisent des codes ou préfixes pour faciliter le mapping.

Ces heuristiques ne sont pas universelles.

Elles doivent être converties en :

```text
SuggestionStrategy
MigrationHeuristic
ConfigurableMappingRule
```

et jamais en invariant global.

---

# 42. Déploiement

PyAccountingKit étant une bibliothèque, il n'impose pas une topologie de déploiement.

Topologies possibles :

```text
Django monolith
FastAPI service
worker
batch job
CLI
notebook / data workflow
```

---

# 43. Observabilité

Le coeur ne doit pas imposer une stack d'observabilité mais doit fournir des points d'intégration.

Exemples :

```text
domain events
structured audit events
operation identifiers
timing hooks
error taxonomy
```

Une application peut ensuite utiliser :

```text
OpenTelemetry
Prometheus
Sentry
structured logging
```

---

# 44. Sécurité

Le framework ne gère pas directement :

```text
login
cookies
CSRF
MFA
```

mais doit faciliter :

```text
actor propagation
authorization context
audit evidence
organization scoping
immutable posted data
idempotence
safe error handling
```

Les adapters web restent responsables de l'authentification et de l'autorisation applicative.

---

# 45. Multi-entité

Tout objet métier doit être rattachable à une entité comptable.

```text
AccountingEntityId
```

doit être utilisé dans les frontières de repository et de requête afin d'éviter les fuites entre organisations.

Le scoping ne doit pas dépendre uniquement de filtres UI.

---

# 46. Monnaie

Les montants doivent utiliser :

```text
Decimal
```

et une abstraction :

```text
Money(amount, currency)
```

Le `float` est interdit pour les montants comptables.

La multi-devise avancée sera traitée progressivement.

---

# 47. Temps

Les opérations métier ne doivent pas appeler directement :

```python
datetime.now()
```

dans les composants testables.

Utiliser :

```text
Clock
SystemClock
FixedClock
```

afin de garantir :

- tests déterministes ;
- audit ;
- reproductibilité.

---

# 48. Identifiants

Les entités opérationnelles peuvent utiliser des identifiants typés :

```text
AccountId
JournalId
JournalEntryId
LedgerId
AccountingEntityId
```

Les identifiants réglementaires externes sont conservés tels quels lorsque cela est nécessaire :

```text
account:fr-pcg:2026:512
```

Ils ne doivent pas être remplacés arbitrairement par un UUID interne.

---

# 49. Gestion des erreurs

Une taxonomie d'erreurs métier est nécessaire.

Exemples :

```text
AccountingError
|
+-- ValidationError
|   +-- UnbalancedEntryError
|   +-- InvalidJournalLineError
|
+-- PostingError
|   +-- ClosedPeriodError
|   +-- InvalidEntryStateError
|
+-- ReferenceError
|   +-- UnknownStandardError
|   +-- NonExecutableMappingError
|
+-- ImportError
```

Les erreurs techniques des adapters doivent être traduites aux frontières appropriées.

---

# 50. Transactions

Le domaine ne démarre pas une transaction SQL.

L'application définit une unité de travail :

```python
with unit_of_work:
    ...
    unit_of_work.commit()
```

L'adapter choisit l'implémentation.

---

# 51. Architecture de lecture

Les projections complexes doivent avoir des APIs dédiées.

```text
LedgerQueryService
TrialBalanceQueryService
FinancialStatementQueryService
AuditQueryService
```

Le domaine n'a pas besoin de charger des milliers de lignes dans un aggregate pour produire une balance.

Cette séparation permettra des implémentations efficaces en base de données.

---

# 52. Performance

Principes :

```text
correctness first
then optimize projections
```

Optimisations admissibles :

```text
indexes
window functions
bulk operations
streaming
cached reference data
materialized read models
```

Condition :

> Toute optimisation doit rester cohérente avec la source canonique et être reconstructible.

---

# 53. Idempotence

L'idempotence doit être considérée comme une capacité transversale pour :

```text
imports
external commands
reference loading
report generation
migration operations
```

Le framework doit accepter des clés d'idempotence fournies par l'application ou l'adapter.

---

# 54. Extensibilité

Les extensions doivent être possibles sans modifier le coeur.

Exemples :

```text
new reference provider
new import format
new persistence adapter
new control
new report
new numbering policy
new reconciliation strategy
```

L'extension par composition est préférée aux gros blocs conditionnels.

---

# 55. Anti-patterns à éviter

## 55.1 Standard codé en dur

```python
if country == "FR":
    ...
```

dans le coeur réglementaire.

## 55.2 Numéro de compte interprété universellement

```python
if code.startswith("7"):
    revenue = True
```

## 55.3 Etat financier stocké comme source primaire

```text
BalanceSheetTable as source of truth
```

## 55.4 Modification d'une écriture postée

```text
UPDATE posted_entry
```

## 55.5 Domaine dépendant de l'ORM

```python
from django.db import models
```

dans `domain`.

## 55.6 Import partiel

Un échec ne doit pas laisser la moitié des écritures créées.

## 55.7 Mapping candidat exécuté silencieusement

Une suggestion n'est pas une règle validée.

---

# 56. Architecture d'intégration Django

Une application Django utilisant PyAccountingKit pourrait adopter :

```text
Django View / DRF
       |
       v
Application Adapter
       |
       v
PyAccountingKit command/query
       |
       v
Django Repository Adapter
       |
       v
Django ORM
       |
       v
PostgreSQL
```

Le `cfa_fra_django_mvp_sprint_7` pourra évoluer progressivement vers cette organisation.

---

# 57. Architecture d'intégration FastAPI

```text
FastAPI Router
      |
      v
Dependency Injection
      |
      v
PyAccountingKit Application Service
      |
      v
SQLAlchemy Adapter
      |
      v
Database
```

Aucune logique comptable ne doit vivre dans le router.

---

# 58. Architecture d'intégration CLI / Batch

```text
CLI
 |
 v
Application Command
 |
 v
PyAccountingKit
 |
 v
Adapters
```

Cette topologie est importante pour les imports, migrations et traitements de masse.

---

# 59. Architecture de test

Pyramide :

```text
                 Golden / E2E
                     /\
                    /  \
             Integration
                /      \
             Contract Tests
              /        \
           Unit / Property
```

Le domaine doit avoir la majorité de ses règles testées sans infrastructure.

---

# 60. Contract tests

Les ports importants doivent disposer de suites de contrat.

Exemple :

```text
JournalEntryRepository contract suite
```

Elle doit être exécutable sur :

```text
InMemory
SQLAlchemy
Django
```

pour garantir un comportement équivalent.

---

# 61. Qualité

Cibles générales :

```text
ruff
mypy
pytest
coverage
```

Les seuils précis seront définis dans :

```text
11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md
```

---

# 62. Stratégie de versioning architectural

Les versions suivantes sont indépendantes :

```text
PyAccountingKit
regulatory dataset
standard edition
company chart
reporting mapping
```

Le runtime doit pouvoir enregistrer ces informations ensemble dans les snapshots.

---

# 63. Compatibilité ascendante

A partir des premières releases publiques :

```text
public API
    -> explicit versioning discipline
```

Les classes internes peuvent évoluer plus librement que :

```text
public facades
ports
serialized snapshots
reference contracts
```

---

# 64. Architecture de repository recommandée

Au niveau repository :

```text
pyaccountingkit/
|
+-- src/
+-- tests/
+-- docs/
+-- examples/
+-- scripts/
+-- pyproject.toml
+-- README.md
+-- CHANGELOG.md
+-- LICENSE
```

Les adapters complexes peuvent rester dans le même repository au départ, puis être extraits si le besoin de release indépendante apparaît.

---

# 65. Monorepo vs packages séparés

La décision proposée pour le démarrage est :

```text
un repository
+
un package principal
+
extras / modules optionnels
```

afin d'éviter un découpage prématuré.

Une extraction ultérieure pourra créer par exemple :

```text
pyaccountingkit-fec
pyaccountingkit-django
pyaccountingkit-sqlalchemy
```

si leurs cycles de release divergent réellement.

---

# 66. ADRs structurants

Les décisions suivantes sont actées au niveau de ce document.

| ID | Décision |
|---|---|
| ADR-ARCH-001 | Architecture domain-first et ports/adapters |
| ADR-ARCH-002 | Django et SQLAlchemy restent hors du domaine |
| ADR-ARCH-003 | `regulatory-accounting-data-framework` est consommé via provider |
| ADR-ARCH-004 | CFA FRA est une référence comportementale, pas une dépendance |
| ADR-ARCH-005 | Entries/lines/accounts/periods forment la source canonique minimale |
| ADR-ARCH-006 | Ledger et états financiers sont des projections |
| ADR-ARCH-007 | Les mutations critiques passent par Application Services |
| ADR-ARCH-008 | Les queries peuvent être optimisées sans charger des aggregates géants |
| ADR-ARCH-009 | Posting et reversal sont transactionnels |
| ADR-ARCH-010 | Les standards comptables ne sont pas codés dans le coeur |
| ADR-ARCH-011 | FEC est un adapter optionnel |
| ADR-ARCH-012 | Mapping réglementaire et mapping de présentation sont distincts |
| ADR-ARCH-013 | Les publications peuvent être figées dans `ReportSnapshot` |
| ADR-ARCH-014 | Les heuristiques sont des suggestions/configurations, pas des invariants |
| ADR-ARCH-015 | Le package démarre comme repository unique avec extensions optionnelles |

---

# 67. Critères d'architecture

L'architecture sera considérée conforme lorsque :

```text
[ ] le domaine peut être importé sans Django
[ ] les tests du domaine fonctionnent sans base de données
[ ] un repository InMemory peut implémenter les ports principaux
[ ] un standard peut être chargé via ReferenceProvider
[ ] un compte entreprise garde sa référence réglementaire
[ ] le posting fonctionne via UnitOfWork
[ ] une écriture postée ne peut pas être modifiée
[ ] une reversal est traçable
[ ] le ledger est reconstruit depuis les lignes
[ ] les balances sont des projections
[ ] le FEC peut être branché comme adapter
[ ] les mappings réglementaires ont un statut explicite
[ ] un ReportSnapshot peut être sérialisé
[ ] CFA FRA peut être migré progressivement vers le framework
```

---

# 68. Roadmap architecturale

## Phase 1 - Foundation

```text
core primitives
typed IDs
Money
Clock
errors
```

## Phase 2 - Accounting Domain

```text
accounts
journals
entries
periods
validation
```

## Phase 3 - Posting

```text
commands
posting
reversal
audit events
```

## Phase 4 - Ledger

```text
general ledger
trial balance
projections
```

## Phase 5 - References

```text
provider
catalog
reference accounts
company chart builder
```

## Phase 6 - Import

```text
generic import
FEC adapter
```

## Phase 7 - Controls

```text
control engine
control results
```

## Phase 8 - Reporting

```text
statement definitions
statement mappings
financial statements
```

## Phase 9 - Regulatory Reporting

```text
regulatory mappings
snapshots
exports contract
```

## Phase 10 - Integrations

```text
SQLAlchemy
Django
FastAPI
```

---

# 69. Relation avec les prochains documents

Ce document fixe la **macro-architecture**.

Les détails sont volontairement délégués aux documents suivants :

```text
02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md
    -> aggregates, entities, value objects, boundaries

03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md
    -> invariants et policies

04_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md
    -> integration regulatory-accounting-data-framework

05_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md
    -> plan entreprise et codification

06_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md
    -> execution comptable

07_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md
    -> imports

08_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md
    -> controles et audit

09_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md
    -> reporting

10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md
    -> persistence et transactions

11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md
    -> tests et golden scenarios

12_PYACCOUNTINGKIT_RELEASE_AND_VERSIONING_STRATEGY.md
    -> releases
```

---

# 70. Architecture cible synthétique

```text
                  EXTERNAL REGULATORY DATA
                           |
                           v
                +----------------------+
                | Reference Adapters   |
                +----------+-----------+
                           |
                           v
+----------------------------------------------------------+
|                    PyAccountingKit                       |
|                                                          |
|  +------------------- Public API ----------------------+ |
|  |                                                     | |
|  +---------------- Application ------------------------+ |
|  | Commands | Queries | Use Cases                      | |
|  +-----------------------------------------------------+ |
|  | Domain                                              | |
|  | Accounts | Entries | Periods | Ledger | Reporting   | |
|  +-----------------------------------------------------+ |
|  | Ports                                               | |
|  | Repositories | UoW | Reference | Audit | Clock      | |
|  +-----------------------------------------------------+ |
+-------------------------+--------------------------------+
                          |
              +-----------+-----------+
              |                       |
              v                       v
        Persistence              Import / Export
         Adapters                  Adapters
              |                       |
              v                       v
      SQLAlchemy / Django          FEC / Files
```

Applications clientes :

```text
Django
FastAPI
CLI
ERP
SaaS
Batch
```

---

# 71. Conclusion

PyAccountingKit doit être construit comme une **infrastructure comptable générique**, et non comme la migration directe de CFA FRA ni comme un wrapper autour de `regulatory-accounting-data-framework`.

Les trois systèmes ont des responsabilités distinctes :

```text
regulatory-accounting-data-framework
    = connaissance réglementaire

PyAccountingKit
    = moteur comptable générique

cfa_fra_django_mvp_sprint_7
    = référence fonctionnelle et futur consommateur
```

La cible doit permettre de conserver ce qui fonctionne déjà dans CFA FRA :

- invariants ;
- posting ;
- reversal ;
- audit ;
- import ;
- ledger ;
- reporting ;
- snapshots ;

tout en éliminant le couplage applicatif.

Le résultat attendu est un framework suffisamment indépendant pour que :

```text
Django
FastAPI
CLI
ERP
```

puissent utiliser le même moteur comptable, avec les mêmes règles et les mêmes résultats.

---

**Prochain document recommandé :**

```text
02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md
```

Ce document devra préciser les aggregates, entities, value objects, bounded contexts, invariants de frontière et relations entre les différents sous-domaines.
