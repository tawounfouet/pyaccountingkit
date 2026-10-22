# 32_PYACCOUNTINGKIT_ARCHITECTURE_STYLE_DDD_HEXAGONAL_CLEAN_VS_MVC.md

# PyAccountingKit — Analyse du style d’architecture
## DDD + Hexagonal / Ports & Adapters + principes de Clean Architecture vs MVC

> **Projet** : PyAccountingKit  
> **Statut** : Note d’analyse architecturale  
> **Date** : 22 octobre 2026  
> **Langue** : Français  

---

# 1. Objet

Ce document analyse le choix architectural de PyAccountingKit :

```text
DDD
+
Hexagonal / Ports & Adapters
+
principes sélectionnés de Clean Architecture
```

et le compare à une architecture principalement organisée autour de :

```text
MVC / MVT
```

La question centrale est :

> Pourquoi cette combinaison est-elle mieux adaptée à PyAccountingKit qu’un MVC utilisé comme architecture principale du framework ?

---

# 2. Conclusion synthétique

Pour PyAccountingKit, la combinaison suivante est cohérente :

```text
DDD
+
Hexagonal / Ports & Adapters
+
Clean Architecture principles
```

car le projet est :

```text
un framework réutilisable
+
un domaine métier riche
+
multi-référentiels
+
multi-adapters
+
transactionnel
+
auditable
+
extensible
```

MVC reste parfaitement pertinent, mais à un autre niveau :

```text
PyAccountingKit
    = cœur métier réutilisable

MVC / MVT
    = architecture possible d’une application consommatrice
```

---

# 3. MVC et Hexagonal ne répondent pas au même problème

## MVC

MVC répond principalement à :

> Comment organiser l’interaction entre interface, traitement et présentation ?

Schéma classique :

```text
User
  ↓
Controller
  ↓
Model
  ↓
View
```

MVC est particulièrement adapté à :

```text
application web
back-office
CRUD
interface métier
```

---

## Hexagonal / Ports & Adapters

Hexagonal répond principalement à :

> Comment isoler le métier des technologies externes ?

Schéma :

```text
External World
      │
   Adapters
      │
    Ports
      │
Application
      │
   Domain
```

---

## DDD

DDD répond principalement à :

> Comment modéliser correctement un domaine métier complexe ?

Il structure notamment :

```text
Entities
Value Objects
Aggregates
Domain Services
Domain Events
Bounded Contexts
Ubiquitous Language
Invariants
```

---

## Clean Architecture

Clean Architecture apporte une règle structurante :

> Les dépendances doivent pointer vers les règles métier, jamais vers l’infrastructure.

---

# 4. Besoin réel de PyAccountingKit

PyAccountingKit n’est pas une application web unique.

Le framework doit pouvoir être consommé depuis :

```text
Django
FastAPI
CLI
Notebook
Batch
Worker
ERP
ETL
BI
tests in-memory
```

et fonctionner avec plusieurs infrastructures :

```text
PostgreSQL
SQLite
Django ORM
SQLAlchemy
InMemory
Object Storage
External APIs
```

Le cœur comptable ne doit donc pas connaître ces technologies.

---

# 5. Exemple : posting

Règle métier :

> Une écriture ne peut être postée que si elle est équilibrée et si sa période est ouverte.

Avec un MVC fortement couplé à Django :

```python
class JournalEntryController:

    def post(self, request):

        entry = JournalEntryModel.objects.get(...)

        if entry.debit != entry.credit:
            ...

        period = AccountingPeriodModel.objects.get(...)

        if period.closed:
            ...

        entry.status = "POSTED"
        entry.save()
```

Cette implémentation fonctionne, mais elle couple :

```text
business rule
+
controller
+
Django Model
+
ORM
```

La même règle devient ensuite difficile à réutiliser dans :

```text
FastAPI
CLI
SQLAlchemy
InMemory tests
```

---

# 6. Même règle avec PyAccountingKit

La cible est :

```text
JournalEntry
      ↓
PostingService
      ↓
Application Use Case
      ↓
Repository Port
      ↓
Adapter
```

Exemple :

```python
posted = posting_service.post(
    entry,
    period,
    actor_id,
)
```

Le domaine ignore si les données sont stockées via :

```text
Django
SQLAlchemy
SQLite
PostgreSQL
InMemory
```

---

# 7. Pourquoi DDD est pertinent

PyAccountingKit contient de nombreux concepts proches mais non équivalents :

```text
Invoice
!=
Receivable

Payment
!=
Settlement

Match
!=
Reconciliation

JournalEntry
!=
BusinessTransaction

AccountId
!=
AccountCode
```

MVC ne protège presque pas ces distinctions.

DDD pousse au contraire à expliciter :

```text
identity
meaning
ownership
invariants
lifecycle
transaction boundaries
```

---

# 8. Richesse du domaine

PyAccountingKit couvre ou prépare notamment :

```text
double-entry accounting
posting
reversal
closing
subledgers
settlements
matching
reconciliation
accounting policies
financial statements
financial analysis
consolidation
regulatory references
semantic layer
```

Ce niveau de complexité dépasse un simple modèle CRUD.

---

# 9. Multi-référentiels

Le framework doit pouvoir fonctionner avec :

```text
PCG
PCEMF
SYSCOHADA
OHADA EBNL
IFRS
custom references
```

Le domaine ne doit donc pas être lié à :

```text
one database schema
one Django model
one account numbering convention
one regulatory provider
```

---

# 10. Pourquoi Ports & Adapters convient

Le pattern central est :

```text
Application / Domain
        │
        ▼
       Port
        ▲
        │
     Adapter
```

Exemple :

```python
class JournalEntryRepositoryProtocol(Protocol):
    def get(self, entry_id: EntryId) -> JournalEntry: ...
    def save(self, entry: JournalEntry) -> None: ...
```

Le cœur exprime :

> J’ai besoin d’un repository capable de charger et sauvegarder une écriture.

Il ne dit pas :

> J’ai besoin de Django ORM.

---

# 11. Plusieurs adapters

```text
JournalEntryRepositoryPort
          ▲
          │
 ┌────────┼─────────┐
 │        │         │
 ▼        ▼         ▼
Django  SQLAlchemy  InMemory
```

La logique métier reste unique.

---

# 12. Ports entrants et sortants

## Inbound / Driving Ports

Ils représentent ce que l’extérieur peut demander :

```text
PostJournalEntry
ClosePeriod
AllocateSettlement
GenerateFinancialStatement
```

Ils sont souvent matérialisés par :

```text
Application Services
Commands
Use Cases
Public Facades
```

## Outbound / Driven Ports

Ils représentent ce dont le cœur a besoin :

```text
Repository
Clock
Outbox
Audit Sink
Reference Provider
FX Provider
Object Storage
```

---

# 13. Clean Architecture et direction des dépendances

Principe :

```text
Frameworks
    ↓
Adapters
    ↓
Application
    ↓
Domain
```

Interdit :

```text
Domain
  ↓
Django
```

Interdit :

```text
Application
  ↓
SqlAlchemyJournalRepository
```

Autorisé :

```text
SQLAlchemy Adapter
  ↓
Repository Port
```

---

# 14. Architecture Fitness Functions

Le document :

```text
24_PYACCOUNTINGKIT_ARCHITECTURE_FITNESS_FUNCTIONS.md
```

permet de transformer ces principes en règles CI.

Exemples :

```text
domain X adapters
domain X django
domain X sqlalchemy
application X adapters
ports X adapters
```

---

# 15. Où MVC reste pertinent

MVC/MVT est pertinent dans une application consommatrice.

Exemple Django :

```text
Browser
   ↓
Django View / Controller
   ↓
AccountingApplication
   ↓
Application Use Case
   ↓
Domain
   ↓
Repository Port
   ↓
Django ORM Adapter
```

MVC gère :

```text
request
routing
forms
presentation
response
```

PyAccountingKit gère :

```text
accounting rules
posting
settlement
closing
ledger
reporting
```

---

# 16. Architecture complète recommandée

```text
┌────────────────────────────────────────────┐
│                CONSUMERS                   │
│                                            │
│ Django MVC/MVT                             │
│ FastAPI                                    │
│ CLI                                        │
│ Notebook                                   │
│ ERP                                        │
└──────────────────────┬─────────────────────┘
                       │
                INBOUND ADAPTERS
                       │
                       ▼
┌────────────────────────────────────────────┐
│              APPLICATION                   │
│                                            │
│ Commands                                   │
│ Queries                                    │
│ Use Cases                                  │
│ Orchestration                              │
└──────────────────────┬─────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────┐
│                 DOMAIN                     │
│                                            │
│ Entities                                   │
│ Value Objects                              │
│ Aggregates                                 │
│ Domain Services                            │
│ Invariants                                 │
│ Domain Events                              │
└──────────────────────┬─────────────────────┘
                       │
                 OUTBOUND PORTS
                       │
        ┌──────────────┼───────────────┐
        ▼              ▼               ▼
   Django ORM      SQLAlchemy       InMemory
    Adapter         Adapter          Adapter
```

---

# 17. Capacités transversales

```text
Unit of Work
Audit
Outbox
Idempotency
Reference Providers
Event Envelope
Architecture Fitness Functions
```

---

# 18. Pourquoi MVC comme cœur serait limitant

Une structure :

```text
pyaccountingkit/
├── models/
├── views/
└── controllers/
```

répond mal à des questions telles que :

```text
Où va Settlement ?
Où va PostingService ?
Où va ReconciliationEngine ?
Où va SYSCOHADAProvider ?
Où va StatementMapping ?
Où va ConsolidationEngine ?
```

Le dossier `models` finirait par agréger des responsabilités très différentes.

---

# 19. DDD exprime mieux les frontières

DDD permet d’identifier explicitement :

```text
ledger
subledgers
settlements
reconciliation
references
reporting
consolidation
semantic
```

Chaque bounded context possède :

```text
responsibility
language
invariants
ownership
contracts
```

---

# 20. Risques d’un MVC utilisé pour le domaine

Un MVC mal utilisé peut conduire à :

```text
Fat Models
Fat Controllers
Anemic Domain
ORM-driven design
```

et faire dériver l’architecture vers :

```text
database schema
    ↓
domain model
```

alors que PyAccountingKit recherche :

```text
domain model
    ↓
persistence mapping
```

---

# 21. MVC n’est pas mauvais

MVC est souvent excellent pour :

```text
simple CRUD
back-office
small business application
UI-centric system
```

Avantages :

```text
moins de couches
moins de boilerplate
développement rapide
courbe d’apprentissage faible
```

---

# 22. Coût de l’architecture choisie

DDD + Hexagonal implique davantage de :

```text
Protocols
DTOs
Repositories
Mappers
Application Services
Adapters
Factories
Tests
Architecture Rules
```

Cette complexité n’est acceptable que si elle apporte une vraie valeur.

---

# 23. Pourquoi ce coût est justifié

PyAccountingKit possède précisément les caractéristiques qui le justifient :

```text
framework réutilisable
+
domaine comptable complexe
+
règles critiques
+
multi-référentiels
+
multi-adapters
+
transactions
+
concurrence
+
audit
+
longue durée de vie
```

---

# 24. Comparaison synthétique

| Critère | MVC comme cœur | DDD + Hexagonal |
|---|---:|---:|
| Application web simple | Excellent | Souvent excessif |
| Framework réutilisable | Limité | Excellent |
| Domaine métier complexe | Moyen | Excellent |
| Plusieurs ORM | Difficile | Naturel |
| Plusieurs interfaces | Couplage fréquent | Naturel |
| Multi-référentiels | Peu structurant | Très adapté |
| Tests sans infrastructure | Plus difficile | Naturel |
| Invariants métier | Souvent dispersés | Centraux |
| Audit / événements métier | Ajout secondaire | Naturel |
| Évolution long terme | Variable | Forte |
| Boilerplate | Faible | Plus élevé |
| Courbe d’apprentissage | Faible | Plus importante |

---

# 25. Les patterns ne sont pas concurrents directs

```text
DDD
    "Comment modéliser le métier ?"
```

```text
Hexagonal
    "Comment isoler le métier du monde extérieur ?"
```

```text
Clean Architecture
    "Dans quel sens les dépendances doivent-elles aller ?"
```

```text
MVC
    "Comment organiser interaction et présentation ?"
```

Ils peuvent coexister.

---

# 26. Combinaison recommandée

```text
DDD
    pour le modèle métier

Hexagonal / Ports & Adapters
    pour l’isolation

Clean Architecture principles
    pour la direction des dépendances

MVC / MVT
    pour les applications web consommatrices
```

---

# 27. Exemple Django

```text
HTTP Request
     ↓
Django View
     ↓
Form / Serializer
     ↓
AccountingApplication.entries.post(...)
     ↓
PostJournalEntryUseCase
     ↓
PostingService
     ↓
JournalEntry
     ↓
JournalEntryRepositoryPort
     ↓
DjangoJournalEntryRepository
     ↓
PostgreSQL
```

Le domaine ne voit jamais :

```text
request
response
QuerySet
ModelForm
Template
```

---

# 28. Exemple CLI

```text
CLI Command
     ↓
AccountingApplication.entries.post(...)
     ↓
Use Case
     ↓
Domain
     ↓
Repository Port
     ↓
SQLAlchemy Adapter
```

Même cœur métier.

---

# 29. Exemple de test

```text
pytest
   ↓
Use Case
   ↓
Domain
   ↓
Repository Port
   ↓
InMemory Adapter
```

Encore le même cœur.

---

# 30. Principe pragmatique

Règle recommandée :

```text
Use DDD
where the business model is complex.

Use Ports & Adapters
where infrastructure variability exists.

Use Clean Architecture principles
to protect dependency direction.

Use MVC
where there is actually a presentation layer.
```

---

# 31. Anti-patterns à éviter

## Architecture cérémonielle

Ne pas créer systématiquement :

```text
Protocol
DTO
Mapper
Factory
Service
Repository
```

si aucune frontière réelle ne le justifie.

## Abstraction prématurée

Un port est utile lorsqu’il protège :

```text
une technologie variable
une dépendance externe
un contrat testable
une frontière métier
```

## ORM phobia

Le but n’est pas d’éviter l’ORM.

Le but est d’éviter que :

```text
ORM semantics
=
domain semantics
```

## DDD partout

Tous les objets n’ont pas besoin d’être des Aggregates.

## MVC interdit

PyAccountingKit ne doit pas interdire à un consumer d’utiliser MVC/MVT.

---

# 32. Décision architecturale

Décision recommandée :

> **PyAccountingKit conserve DDD + Hexagonal / Ports & Adapters comme structure principale, applique les principes de dépendance de Clean Architecture et considère MVC/MVT comme un style de présentation possible chez les consommateurs, non comme l’architecture du cœur.**

---

# 33. ADR proposées

| ADR | Décision |
|---|---|
| ADR-STYLE-001 | PyAccountingKit utilise DDD pour modéliser le domaine comptable |
| ADR-STYLE-002 | Ports & Adapters constitue le modèle principal d’isolation infrastructurelle |
| ADR-STYLE-003 | La Dependency Rule de Clean Architecture est adoptée |
| ADR-STYLE-004 | MVC/MVT n’est pas l’architecture du core PyAccountingKit || ADR-STYLE-005 | MVC/MVT est autorisé dans les applications consommatrices |
| ADR-STYLE-006 | Les invariants comptables ne résident pas dans les controllers/views |
| ADR-STYLE-007 | Les ORM restent confinés aux adapters |
| ADR-STYLE-008 | Les inbound adapters dépendent de la public/application API |
| ADR-STYLE-009 | Les outbound adapters implémentent des ports |
| ADR-STYLE-010 | Les abstractions sont introduites uniquement lorsqu’elles protègent une frontière réelle |

---

# 34. Critères d’acceptation

```text
[ ] le domaine fonctionne sans Django
[ ] le domaine fonctionne sans SQLAlchemy
[ ] les mêmes use cases fonctionnent avec InMemory et PostgreSQL
[ ] les controllers/views ne portent pas les invariants comptables
[ ] les adapters ORM implémentent les ports
[ ] les public use cases restent framework-neutral
[ ] les applications MVC/MVT peuvent consommer PyAccountingKit sans contournement
[ ] les Architecture Fitness Functions protègent les dépendances
```

---

# 35. Positionnement final

```text
                    APPLICATIONS
       ┌──────────────┼──────────────┐
       │              │              │
   Django MVC       FastAPI         CLI
       │              │              │
       └──────────────┼──────────────┘
                      │
               Inbound Adapters
                      │
                      ▼
              Public / Application
                      │
                      ▼
                   Domain
                      │
                 Outbound Ports
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
   Django ORM      SQLAlchemy      InMemory
```

---

# 36. Conclusion

MVC et Hexagonal ne doivent pas être vus comme deux architectures qu’il faudrait choisir exclusivement.

Dans PyAccountingKit :

```text
DDD
```

structure le langage et les invariants métier.

```text
Hexagonal / Ports & Adapters
```

isole ces règles de l’infrastructure.

```text
Clean Architecture
```

protège la direction des dépendances.

```text
MVC / MVT
```

reste disponible pour organiser la présentation des applications qui utilisent le framework.

La recommandation finale est donc :

> **conserver DDD + Hexagonal / Ports & Adapters + principes ciblés de Clean Architecture pour PyAccountingKit, et utiliser MVC/MVT là où il excelle : dans la couche de présentation des applications consommatrices.**