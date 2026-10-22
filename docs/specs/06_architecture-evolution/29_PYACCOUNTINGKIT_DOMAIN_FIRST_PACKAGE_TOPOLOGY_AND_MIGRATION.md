# 29_PYACCOUNTINGKIT_DOMAIN_FIRST_PACKAGE_TOPOLOGY_AND_MIGRATION.md

# PyAccountingKit — Domain-First Package Topology & Migration

> **Projet** : PyAccountingKit  
> **Document** : `29_PYACCOUNTINGKIT_DOMAIN_FIRST_PACKAGE_TOPOLOGY_AND_MIGRATION.md`  
> **Statut** : Spécification d'architecture et plan de migration brownfield  
> **Version documentaire** : 1.0  
> **Date** : 22 octobre 2026  
> **Baseline observée** : PyAccountingKit `0.7.0rc1`  
> **Langue** : Français  

---

# 1. Objet du document

Ce document définit :

1. la **topologie de packages domain-first cible** de PyAccountingKit ;
2. la manière de préserver l'architecture :

```text
DDD
+
Hexagonal / Ports & Adapters
+
principes de Clean Architecture
```

3. la stratégie de migration depuis la topologie actuelle :

```text
core/
domain/
application/
ports/
adapters/
integrations/
public/
```

vers une organisation où les **bounded contexts et capabilities métier deviennent l'axe principal de navigation** ;

4. une migration **progressive, brownfield, sans big-bang**, sans casser prématurément :
   - l'API publique ;
   - les adapters PostgreSQL ;
   - les contract tests ;
   - les manifests ;
   - les golden/replay suites ;
   - les consumers existants.

---

# 2. Résumé exécutif

PyAccountingKit possède aujourd'hui une architecture saine mais principalement **layer-first** à la racine :

```text
pyaccountingkit/
├── core/
├── domain/
├── application/
├── ports/
├── adapters/
├── integrations/
└── public/
```

Cette organisation a été très utile pour établir les premières frontières :

```text
Domain != Application != Infrastructure
```

et protéger le cœur du couplage à :

```text
Django
SQLAlchemy
PostgreSQL
FEC
CFA FRA
```

Cependant, le framework est désormais suffisamment riche pour que le vocabulaire dominant devienne :

```text
ledger
closing
subledgers
reconciliation
reporting
analysis
consolidation
references
imports
```

plutôt que :

```text
domain
application
ports
adapters
```

La cible recommandée est donc une **Domain-First Hexagonal Topology** :

```text
pyaccountingkit/
├── shared/
├── ledger/
│   ├── domain/
│   ├── application/
│   ├── ports/
│   └── adapters/
├── closing/
├── subledgers/
├── reconciliation/
├── reporting/
├── analysis/
├── consolidation/
├── references/
├── charts/
├── imports/
├── controls/
├── infrastructure/
├── integrations/
├── public/
└── testing/
```

avec une nuance essentielle :

> **tous les adapters ne doivent pas obligatoirement être déplacés sous un bounded context.**

Les adapters purement locaux à une capability peuvent être colocalisés avec elle.

Les adapters réellement transverses, en particulier :

```text
Django/PostgreSQL UnitOfWork
SQLAlchemy/PostgreSQL UnitOfWork
shared transaction infrastructure
```

peuvent rester dans un package edge :

```text
infrastructure/
```

afin de ne pas casser artificiellement les frontières transactionnelles.

La migration doit être :

```text
OBSERVE
→ DEFINE
→ INTRODUCE NEW PACKAGES
→ MOVE ONE CONTEXT
→ COMPATIBILITY SHIMS
→ ENFORCE
→ REPEAT
→ REMOVE LEGACY PATHS
```

et non :

```text
rename everything in one PR
```

---

# 3. Baseline observée dans le dépôt

La racine actuelle contient :

```text
src/pyaccountingkit/
├── __init__.py
├── adapters/
├── application/
├── core/
├── domain/
├── integrations/
├── ports/
├── public/
└── py.typed
```

Cette structure est explicitement protégée par :

```text
scripts/validate_architecture.py
```

---

# 4. Baseline `domain/`

Le package `domain/` est déjà organisé par concepts métier :

```text
domain/
├── analysis/
├── audit/
├── charts/
├── closing/
├── consolidation/
├── controls/
├── identity/
├── imports/
├── journals/
├── ledger/
├── periods/
├── policies/
├── reconciliation/
├── references/
├── reporting/
├── subledgers/
└── traceability/
```

Ce point est important :

> PyAccountingKit n'est pas un monolithe métier non structuré.

La migration domain-first ne part donc pas de zéro.

---

# 5. Baseline `application/`

La couche application contient déjà plusieurs slices métier :

```text
application/
├── analysis/
├── charts/
├── closing/
├── consolidation/
├── controls/
├── entries/
├── imports/
├── ledger/
├── reconciliation/
├── references/
├── reporting/
└── subledgers/
```

Il existe donc déjà une **correspondance partielle** :

```text
domain/ledger
application/ledger

domain/closing
application/closing

domain/reconciliation
application/reconciliation
```

La migration consiste principalement à **rapprocher physiquement des responsabilités déjà conceptuellement liées**.

---

# 6. Baseline `ports/`

Les ports sont aujourd'hui centralisés :

```text
ports/
├── account_role_resolution.py
├── accounting_import.py
├── artifacts.py
├── audit.py
├── company_chart_resolution.py
├── control_account_resolution.py
├── exchange_rates.py
├── idempotency.py
├── outbox.py
├── queries.py
├── reconciliation.py
├── references.py
├── regulatory_reporting.py
├── repositories.py
├── unit_of_work.py
└── valuation.py
```

Cette centralisation a l'avantage de rendre la couche hexagonale visible.

Elle a aussi une limite :

> avec la croissance du projet, le package `ports/` commence à agréger des contrats appartenant à des bounded contexts différents.

---

# 7. Baseline `adapters/`

Les adapters sont aujourd'hui organisés principalement par technologie :

```text
adapters/
├── django/
├── imports/
├── in_memory/
├── reconciliation/
├── regulatory/
└── sqlalchemy/
```

C'est typiquement une organisation :

```text
technology-first
```

pour la couche infrastructure.

---

# 8. Baseline `integrations/`

Le dépôt contient :

```text
integrations/
├── cfa_fra/
└── regulatory_framework/
```

Ces packages représentent des frontières explicites avec des systèmes ou ressources externes.

Ils ne doivent pas être absorbés automatiquement dans les bounded contexts.

---

# 9. Baseline `public/`

L'API publique est déjà structurée par capabilities :

```text
public/
├── analysis.py
├── application.py
├── charts.py
├── closing.py
├── controls.py
├── entries.py
├── imports.py
├── ledger.py
├── references.py
├── reporting.py
├── statements.py
├── subledgers.py
├── dto/
└── protocols/
```

Le point d'entrée principal est :

```text
AccountingApplication
```

qui compose :

```text
references
charts
entries
ledger
closing
controls
imports
statements
reporting
analysis
subledgers
```

Cette façade constitue un **stabilisateur majeur** pour la migration.

---

# 10. Architecture validation actuelle

`scripts/validate_architecture.py` protège aujourd'hui :

```text
core
domain
ports
```

contre des imports vers :

```text
aiohttp
django
fastapi
flask
psycopg
requests
sqlalchemy

pyaccountingkit.adapters
pyaccountingkit.application
pyaccountingkit.integrations
pyaccountingkit.public
```

Cette règle est saine mais **layer-first**.

Elle répond :

> le domaine dépend-il de l'infrastructure ?

Elle ne répond pas encore :

> le bounded context `ledger` dépend-il illégalement de l'implémentation interne de `reconciliation` ?

---

# 11. Exemple de couplage à surveiller

La baseline contient actuellement :

```text
domain/ledger/reversal.py
```

qui importe :

```text
AuditLogSinkProtocol
```

depuis :

```text
pyaccountingkit.ports.audit
```

Le service est annoncé persistence-free, mais reçoit directement un port d'audit.

Cette dépendance n'est pas nécessairement catastrophique dans l'architecture actuelle.

Elle illustre cependant une question que la migration domain-first doit clarifier :

```text
le domaine produit-il un fait métier
ou
effectue-t-il lui-même un side effect d'audit ?
```

La cible recommandée est plutôt :

```text
Domain
    → returns state + DomainEvent/fact

Application
    → records audit
    → stages outbox
    → commits
```

lorsque cela permet de rendre le domaine plus pur.

---

# 12. Autre exemple : Chart Generation

`domain/charts/generation.py` dépend actuellement de :

```text
AccountingReferenceProviderProtocol
```

situé dans :

```text
ports/references.py
```

Cette dépendance peut être reclassifiée de deux façons :

```text
charts/ports/reference_provider.py
```

si la génération est réellement une capability applicative de `charts` ;

ou :

```text
charts/application/generation.py
```

si elle orchestre un provider externe.

Ce type de décision est précisément facilité par la topologie domain-first.

---

# 13. Pourquoi la topologie actuelle reste valide

Il ne faut pas considérer l'architecture actuelle comme une erreur.

Elle a offert plusieurs bénéfices :

```text
séparation visible des couches
simplicité de bootstrap
règles d'import faciles à expliquer
adapters centralisés
UoW centralisée
bonne lisibilité pour une codebase initiale
```

La migration est justifiée par la **croissance du domaine**, pas par un échec architectural initial.

---

# 14. Limite 1 — navigation par couche

Pour comprendre le posting, un développeur doit naviguer entre :

```text
domain/ledger/
application/ledger/
ports/
adapters/
public/entries.py
```

Le use case métier est physiquement dispersé.

---

# 15. Limite 2 — croissance des ports transverses

Le package :

```text
ports/
```

risque progressivement de devenir :

```text
miscellaneous_interfaces/
```

si tous les bounded contexts y ajoutent leurs contrats.

---

# 16. Limite 3 — ownership moins visible

Un fichier :

```text
ports/exchange_rates.py
```

ne dit pas immédiatement qui en est propriétaire :

```text
valuation ?
reporting ?
consolidation ?
shared ?
```

---

# 17. Limite 4 — technologie comme axe de navigation

Avec :

```text
adapters/django/
adapters/sqlalchemy/
```

on trouve facilement :

> tout ce qui concerne Django.

Mais moins facilement :

> tout ce qui concerne Ledger.

---

# 18. Limite 5 — context boundaries difficiles à automatiser

Le validator actuel protège :

```text
domain vs infrastructure
```

mais pas encore :

```text
analysis read-only
reconciliation no posting
consolidation no entity-ledger mutation
reporting no write path
```

---

# 19. Inspiration PyTradeKit

PyTradeKit formalise une décision :

```text
Domain-First Package Topology
```

avec le principe :

> package organization follows domain responsibilities before infrastructure technologies.

Il formalise aussi un :

```text
Minimal Shared Kernel
```

afin d'éviter qu'un package partagé devienne une zone de couplage caché.

PyAccountingKit peut réutiliser ces principes sans copier sa structure mécaniquement.

---

# 20. Décision cible

La topologie cible de PyAccountingKit est :

> **Domain-First Hexagonal Modular Monolith**

C'est-à-dire :

```text
bounded contexts first
+
hexagonal layers inside contexts
+
minimal shared kernel
+
explicit integration edge
+
stable public facade
```

---

# 21. Macro-architecture cible

```text
pyaccountingkit/
│
├── shared/
│
├── identity/
├── references/
├── policies/
├── charts/
├── ledger/
├── closing/
├── subledgers/
├── imports/
├── controls/
├── reconciliation/
├── reporting/
├── analysis/
├── consolidation/
│
├── infrastructure/
├── integrations/
├── public/
└── testing/
```

---

# 22. Principe : Domain First

Le premier niveau de package répond :

> **Quelle capability métier est concernée ?**

et non :

> quelle couche technique est concernée ?

---

# 23. Structure interne d'un bounded context

Une capability suffisamment riche peut utiliser :

```text
ledger/
├── domain/
├── application/
├── ports/
├── adapters/
└── __init__.py
```

---

# 24. Tous les contexts n'ont pas besoin des quatre couches

Exemple :

```text
analysis/
├── domain/
├── application/
└── ports/
```

si aucune infrastructure spécifique n'existe.

Éviter :

```text
empty adapters/
empty ports/
```

créés uniquement pour respecter un template.

---

# 25. Vertical slice minimal

Une petite capability peut être :

```text
controls/
├── model.py
├── application.py
└── ports.py
```

si la séparation en sous-packages n'apporte rien.

La topologie cible doit rester pragmatique.

---

# 26. Shared Kernel cible

Le package actuel :

```text
core/
```

doit être réévalué.

La cible conceptuelle est :

```text
shared/
```

contenant uniquement les primitives réellement transverses.

---

# 27. Contenu recommandé de `shared/`

Exemples :

```text
Money
Currency
typed IDs génériques
Clock abstractions
Revision
Correlation/Event primitives
canonical checksum helpers
generic entity scope helpers
```

---

# 28. Ce qui ne doit pas devenir shared

Interdit de déplacer automatiquement dans `shared/` :

```text
JournalEntry
Receivable
ReconciliationMatch
FinancialStatement
AccountingPolicySet
ReferenceNode
```

---

# 29. Minimal Shared Kernel

Principe :

> **si un concept possède un propriétaire métier évident, il ne doit pas être dans shared.**

---

# 30. `core/errors.py`

Les erreurs réellement transverses peuvent rester partagées.

Mais les erreurs métier spécifiques doivent progressivement revenir à leur context.

Exemple :

```text
PeriodClosedError
```

peut appartenir à :

```text
closing/periods
```

ou être exposée via une public error translation.

---

# 31. Identifiers

Les IDs peuvent être divisés entre :

```text
shared primitive ID mechanism
```

et :

```text
context-owned semantic IDs
```

Exemple :

```text
EntryId
```

peut être possédé par `ledger`.

---

# 32. Public API reste séparée

La cible conserve :

```text
public/
```

comme façade stable.

Raison :

```text
internal package topology
!=
consumer API
```

---

# 33. Public API as anti-corruption boundary

Un consumer doit continuer à utiliser :

```python
AccountingApplication(...)
```

plutôt que dépendre de :

```text
ledger.application.posting_orchestrator
```

---

# 34. Règle fondamentale de migration

Le chemin public :

```text
pyaccountingkit.public
```

doit être plus stable que les chemins internes.

---

# 35. Target — Ledger

Topologie possible :

```text
ledger/
├── domain/
│   ├── journal.py
│   ├── journal_entry.py
│   ├── journal_line.py
│   ├── posting.py
│   ├── reversal.py
│   └── events.py
├── application/
│   ├── posting.py
│   ├── reversal.py
│   └── queries.py
├── ports/
│   ├── repositories.py
│   ├── chart_resolver.py
│   └── uow.py
└── adapters/
    └── in_memory/
```

---

# 36. Journals + Ledger

La baseline sépare aujourd'hui :

```text
domain/journals
domain/ledger
```

La migration doit décider si :

```text
Journals
```

est un submodule du bounded context `ledger`, ou un context séparé.

Recommandation initiale :

```text
ledger/
    journal/
    posting/
    projections/
```

car `JournalEntry` et posting forment un même cœur transactionnel.

---

# 37. Periods ownership

Aujourd'hui :

```text
domain/periods
domain/closing
```

La période comptable est utilisée par posting et closing.

Deux options :

```text
A. periods as shared domain context
B. closing owns lifecycle, ledger consumes a port/read contract
```

Recommandation :

```text
periods/
```
comme capability métier de premier niveau si son lifecycle reste suffisamment autonome.

Ne pas la mettre dans `shared`.

---

# 38. Target — Closing

```text
closing/
├── domain/
│   ├── closing_run.py
│   ├── opening.py
│   ├── adjustments.py
│   └── controls.py
├── application/
│   └── close_period.py
├── ports/
│   └── ...
└── events.py
```

---

# 39. Target — Subledgers

```text
subledgers/
├── domain/
│   ├── receivable.py
│   ├── payable.py
│   ├── due_item.py
│   ├── settlement.py
│   ├── allocation.py
│   ├── matching.py
│   └── aging.py
├── application/
├── ports/
└── adapters/
```

---

# 40. Target — Reconciliation

```text
reconciliation/
├── domain/
├── application/
├── ports/
└── adapters/
```

Le bounded context reste distinct de :

```text
Settlement
AccountingMatch
Posting
Consolidation elimination
```

---

# 41. Target — References

```text
references/
├── domain/
├── application/
├── ports/
└── adapters/
    └── regulatory/
```

Le provider regulatory peut être local à ce context si sa seule responsabilité est la Reference Data.

---

# 42. Target — Policies

```text
policies/
├── domain/
├── application/
└── ports/
```

Les policies de reconnaissance/measurement restent explicitement distinctes du posting.

---

# 43. Target — Charts

```text
charts/
├── domain/
├── application/
├── ports/
└── adapters/
```

Les bindings réglementaires restent visibles dans ce context.

---

# 44. Target — Imports

Le domaine Import est un excellent candidat vertical.

```text
imports/
├── domain/
│   ├── batch.py
│   ├── plan.py
│   ├── issues.py
│   └── provenance.py
├── application/
│   ├── execution.py
│   └── preflight.py
├── ports/
│   ├── parser.py
│   └── artifact_store.py
└── adapters/
    └── fec/
```

---

# 45. FEC colocalisé avec Imports

La baseline :

```text
adapters/imports/fec/
```

peut devenir :

```text
imports/adapters/fec/
```

car FEC est clairement un adapter de l'Accounting Import capability.

---

# 46. Target — Reporting

```text
reporting/
├── domain/
│   ├── statements/
│   ├── snapshots/
│   ├── regulatory/
│   └── evidence/
├── application/
├── ports/
└── adapters/
```

---

# 47. Statements vs Reporting

La public API expose actuellement :

```text
statements
reporting
```

Cette distinction peut rester publique même si l'implémentation interne appartient au même bounded context `reporting`.

---

# 48. Target — Analysis

```text
analysis/
├── domain/
├── application/
└── ports/
```

Règle :

```text
analysis
    → reads reporting/ledger contracts
    X writes ledger
```

---

# 49. Target — Consolidation

```text
consolidation/
├── domain/
├── application/
├── ports/
└── adapters/
```

Règle :

```text
consolidation
    → consumes entity snapshots
    → owns group adjustments/eliminations
    X mutates entity ledger
```

---

# 50. Target — Controls / Audit / Traceability

Trois concepts existent aujourd'hui :

```text
domain/controls
domain/audit
domain/traceability
```

Ils ne doivent pas être fusionnés automatiquement.

---

# 51. Controls

`controls/` peut être un bounded context supporting :

```text
control definitions
control runs
gates
sign-off support
```

---

# 52. Audit

Audit est transversal mais possède une sémantique distincte.

Options :

```text
audit/
```

au premier niveau,

ou :

```text
shared/audit primitives
```

uniquement pour les contrats minimaux.

Recommandation :

```text
audit/
```

reste une capability explicite.

---

# 53. Traceability

Traceability peut devenir :

```text
lineage/
```

ou rester `traceability/`.

Elle doit éviter de devenir un simple dossier de helpers.

---

# 54. Infrastructure edge

Une pure topologie :

```text
ledger/adapters/django
closing/adapters/django
subledgers/adapters/django
...
```

semble séduisante, mais peut devenir contre-productive lorsque plusieurs contexts partagent :

```text
one SQL transaction
one UnitOfWork
one Django app
one SQLAlchemy metadata
```

---

# 55. Décision hybride

Conserver un package :

```text
infrastructure/
```

pour les adapters véritablement transverses.

---

# 56. Target infrastructure

```text
infrastructure/
├── django/
│   ├── models/
│   ├── repositories/
│   ├── unit_of_work.py
│   └── mappers/
├── sqlalchemy/
│   ├── models/
│   ├── repositories/
│   ├── unit_of_work.py
│   └── mappers/
└── in_memory/
```

---

# 57. Domain-owned adapter vs infrastructure-owned adapter

Règle :

```text
adapter belongs to one context only
    → colocate under context/adapters

adapter implements cross-context technical boundary
    → infrastructure/
```

---

# 58. Exemple

```text
FEC parser
```

appartient à :

```text
imports/adapters/fec
```

Mais :

```text
DjangoUnitOfWork
```

qui groupe :

```text
entries
periods
journals
audit
outbox
idempotency
```

reste raisonnablement :

```text
infrastructure/django
```

---

# 59. Integrations edge

Conserver :

```text
integrations/
```

pour les systèmes externes qui dépassent un seul context.

---

# 60. CFA FRA

```text
integrations/cfa_fra
```

reste séparé car il représente :

```text
migration
compatibility
cutover
behavioral oracle
```

et non une capability comptable canonique.

---

# 61. Regulatory framework

`integrations/regulatory_framework` peut être progressivement réduit si sa responsabilité devient entièrement celle de :

```text
references/adapters/regulatory
```

Mais cette décision doit être prise après inventaire précis.

---

# 62. Testing package

Le document `28` introduit :

```text
pyaccountingkit.testing
```

Cette topologie s'intègre naturellement dans la cible.

---

# 63. Reproducibility

Les primitives transverses de `26` peuvent suivre deux niveaux :

```text
shared/reproducibility primitives
```

et manifests spécialisés dans chaque context.

Exemple :

```text
reporting/domain/statement_manifest.py
reconciliation/domain/manifest.py
```

---

# 64. Events

Les event primitives génériques peuvent être :

```text
shared/events
```

Mais les événements eux-mêmes restent context-owned :

```text
ledger/events.py
closing/events.py
reconciliation/events.py
```

---

# 65. Causality

```text
EventId
CorrelationId
CausationId
```

peuvent appartenir au minimal shared kernel.

---

# 66. Target high-level tree

```text
src/pyaccountingkit/
│
├── shared/
│   ├── money.py
│   ├── currency.py
│   ├── clock.py
│   ├── revision.py
│   ├── events.py
│   └── checksums.py
│
├── identity/
├── references/
├── policies/
├── charts/
├── periods/
├── ledger/
├── closing/
├── subledgers/
├── imports/
├── controls/
├── audit/
├── traceability/
├── reconciliation/
├── reporting/
├── analysis/
├── consolidation/
│
├── infrastructure/
│   ├── in_memory/
│   ├── django/
│   └── sqlalchemy/
│
├── integrations/
│   ├── cfa_fra/
│   └── regulatory_framework/
│
├── public/
├── testing/
└── py.typed
```

---

# 67. Dependency rule — target

La règle de base devient :

```text
context.domain
    X context.application
    X infrastructure
    X public
```

---

# 68. Application dependency

```text
context.application
    → context.domain
    → context.ports
```

et peut dépendre de **published contracts** d'autres contexts.

---

# 69. Adapter dependency

```text
adapter
    → port
    → canonical models
```

Jamais l'inverse.

---

# 70. Cross-context dependency

Un context ne doit pas importer arbitrairement les internals d'un autre.

Interdit :

```text
analysis
    → reporting.domain._internal_formula_parser
```

Préférer :

```text
analysis
    → reporting.public_contracts.ReportSnapshot
```

---

# 71. Published language

Chaque bounded context peut exposer une petite surface :

```text
<ctx>/contracts.py
<ctx>/api.py
<ctx>/events.py
```

selon le besoin.

---

# 72. Internal by default

Tous les modules internes ne sont pas des APIs cross-context.

---

# 73. Cross-context imports

Autoriser uniquement :

```text
shared stable primitives
published context contracts
public/application service boundary
```

---

# 74. No circular bounded-context graph

Le graphe de dépendances doit rester acyclique autant que possible.

---

# 75. Exemple cible

```text
ledger
   ↓
periods contract
   ↓
shared
```

et :

```text
reporting
   ↓
ledger read contract
   ↓
shared
```

---

# 76. Read-side dependencies

Les downstream contexts doivent préférer :

```text
snapshots
DTOs
query protocols
```

à :

```text
aggregate internals
```

---

# 77. Analysis boundary

```text
analysis
    → ReportSnapshot / TrialBalanceSnapshot

analysis
    X JournalEntryRepository mutation
```

---

# 78. Reconciliation boundary

```text
reconciliation
    → source snapshots

reconciliation
    X direct PostingService invocation for silent corrections
```

---

# 79. Consolidation boundary

```text
consolidation
    → entity-level snapshots

consolidation
    X mutate entity JournalEntry
```

---

# 80. Shared kernel dependency

Tous les contexts peuvent dépendre de :

```text
shared
```

Mais :

```text
shared
```

ne dépend d'aucun bounded context.

---

# 81. Public dependency

```text
public
    → application APIs/contracts
```

Le domaine ne dépend jamais de `public`.

---

# 82. Infrastructure dependency

```text
infrastructure
    → ports/contracts
```

Le domaine/application n'importe jamais une implémentation infrastructure.

---

# 83. Integrations dependency

```text
integrations
    → public/context contracts
```

selon le rôle de l'intégration.

Éviter qu'une integration devienne une backdoor vers les internals.

---

# 84. Architecture Fitness Functions — évolution

Le validator actuel doit évoluer de :

```text
layer boundary rules
```

vers :

```text
layer + context boundary rules
```

---

# 85. Transitional validator

Pendant migration, supporter simultanément :

```text
legacy layer-first paths
new domain-first paths
```

---

# 86. Migration state

Introduire un registry :

```text
ARCHITECTURE_MIGRATION_MAP.json
```

ou équivalent.

---

# 87. Registry example

```json
{
  "ledger": {
    "state": "MIGRATING",
    "legacy_paths": [
      "domain/ledger",
      "domain/journals",
      "application/ledger"
    ],
    "target_path": "ledger"
  }
}
```

---

# 88. Context migration states

```text
LEGACY
MIGRATING
DOMAIN_FIRST
DEPRECATED_LEGACY_PATH
COMPLETE
```

---

# 89. Brownfield principle

Une migration de topologie n'est pas une réécriture métier.

Interdit de mélanger dans la même PR :

```text
mass package move
+
major business behavior redesign
+
new public API
```

sauf nécessité démontrée.

---

# 90. Preserve semantics

Pour chaque slice déplacé :

```text
same golden outputs
same public behavior
same contract tests
same replay checksums
```

---

# 91. Preserve public facade

Pendant toute la migration :

```text
AccountingApplication
```

reste stable autant que possible.

---

# 92. Preserve manifests

Ne pas changer les schemas ou checksums simplement parce qu'un module Python a changé de chemin.

---

# 93. Module path != business identity

Un :

```text
ReportSnapshot
```

ne change pas de sens parce que son implémentation passe de :

```text
domain/reporting/report_snapshot.py
```

à :

```text
reporting/domain/report_snapshot.py
```

---

# 94. Pickle warning

Si des consumers sérialisent directement des objets Python avec :

```text
pickle
```

un changement de module path peut être breaking.

PyAccountingKit ne doit pas promettre la stabilité pickle des internals sans contrat explicite.

---

# 95. JSON/public DTO stability

Préférer les formats publics versionnés aux module paths internes comme contrat de persistance externe.

---

# 96. Migration strategy

La migration cible se déroule en phases.

---

# 97. Phase DFT-00 — Inventory

Produire une cartographie complète :

```text
module
owner context
current layer
incoming imports
outgoing imports
public exposure
test coverage
```

---

# 98. DFT-00 deliverable

Artifact recommandé :

```text
PACKAGE_TOPOLOGY_BASELINE.json
```

---

# 99. Phase DFT-01 — Context ownership

Pour chaque module actuel :

```text
domain/*
application/*
ports/*
adapters/*
```

assigner :

```text
owner context
```

ou :

```text
shared/infrastructure/integration
```

---

# 100. Example ownership mapping

```text
domain/ledger/*            → ledger
domain/journals/*          → ledger
application/ledger/*       → ledger
ports/repositories.py      → split by owner
ports/reconciliation.py    → reconciliation
adapters/imports/fec/*     → imports
```

---

# 101. Phase DFT-02 — Shared Kernel hardening

Avant les moves massifs :

```textinventory core/
classify shared vs context-owned
prevent shared growth
```

---

# 102. DFT-02 rule

Aucun nouveau concept métier contextuel dans :

```text
core/
shared/
```

sans ADR.

---

# 103. Phase DFT-03 — Introduce target package for one pilot context

Choisir un context à forte cohésion et faible risque.

---

# 104. Pilot recommandé

Premier candidat :

```text
reconciliation
```

ou :

```text
analysis
```

car ces contexts sont relativement downstream et possèdent moins de responsabilités transactionnelles centrales que Ledger.

---

# 105. Pourquoi pas Ledger en premier

Ledger est :

```text
central
highly referenced
transaction critical
publicly visible
```

Le migrer en premier maximise le blast radius.

---

# 106. Phase DFT-04 — Move internals, preserve imports

Créer le nouveau path :

```text
pyaccountingkit.reconciliation
```

puis conserver temporairement :

```text
pyaccountingkit.domain.reconciliation
```

comme compatibility forwarding layer si nécessaire.

---

# 107. Compatibility shim

Exemple :

```python
# legacy module
from pyaccountingkit.reconciliation.domain.match import ReconciliationMatch

__all__ = ["ReconciliationMatch"]
```

---

# 108. Shim policy

Un shim doit être :

```text
thin
behavior-free
temporary
documented
```

---

# 109. Deprecation warning

Ne pas nécessairement émettre un warning sur chaque internal import si ces paths n'ont jamais été publics.

Mais si des chemins ont été documentés ou utilisés par consumers :

```text
DeprecationWarning
```

peut être approprié.

---

# 110. Phase DFT-05 — Update internal imports

Une fois le package cible créé :

```text
internal code uses new path
```

Les legacy paths ne servent plus qu'aux compatibility shims.

---

# 111. Phase DFT-06 — Context-specific fitness rules

Exemple :

```text
reconciliation.domain
    X infrastructure
    X ledger write internals
```

---

# 112. Phase DFT-07 — Move tests

Réorganiser progressivement :

```text
tests/unit/reconciliation
tests/integration/reconciliation
```

sans exiger que tous les tests suivent exactement la structure source.

---

# 113. Phase DFT-08 — Qualify

Exécuter :

```text
unit
property
contract
integration
golden
replay
concurrency
architecture
```

selon le context.

---

# 114. Phase DFT-09 — Mark context DOMAIN_FIRST

Après qualification :

```text
migration state = DOMAIN_FIRST
```

---

# 115. Phase DFT-10 — Repeat

Ordre recommandé initial :

```text
analysis
reconciliation
imports
reporting
subledgers
closing
references
charts/policies
ledger
```

L'ordre exact doit être adapté au graphe d'import réel.

---

# 116. Ledger migration late

Ledger doit être migré après :

```text
fitness framework mature
compat shims proven
public facade proven stable
testing toolkit available
```

---

# 117. Phase DFT-11 — Infrastructure rename

Une fois suffisamment de contexts migrés :

```text
adapters/
```

peut être réduit ou renommé :

```text
infrastructure/
```

pour les adapters réellement cross-context.

---

# 118. Phase DFT-12 — Remove legacy root layers

Seulement lorsque :

```text
domain/
application/
ports/
adapters/
```

ne contiennent plus que des shims ou plus rien.

---

# 119. No empty-layer forever

L'objectif n'est pas de conserver éternellement deux architectures.

Une date/milestone de suppression doit être définie après migration.

---

# 120. Import compatibility matrix

Pendant transition :

| Import | État |
|---|---|
| `pyaccountingkit.public.*` | Stable |
| `pyaccountingkit.domain.*` | Legacy internal / compatibility |
| `pyaccountingkit.application.*` | Legacy internal / compatibility |
| `pyaccountingkit.ports.*` | Legacy internal / compatibility |
| `pyaccountingkit.<context>.*` | New canonical internal topology |

---

# 121. Public internal boundary

Documenter clairement :

```text
supported public imports
```

afin d'éviter que les consumers prennent la topologie interne comme API officielle.

---

# 122. `PUBLIC_API_MANIFEST.json`

La migration doit vérifier que :

```text
PUBLIC_API_MANIFEST.json
```

ne change pas involontairement.

---

# 123. Public error codes

Même principe pour :

```text
PUBLIC_ERROR_CODES.json
```

---

# 124. Adapter contracts

Ne pas casser :

```text
ADAPTER_CONTRACT_MANIFEST.json
```

pour une simple migration de package.

---

# 125. Snapshot schema

Ne pas casser :

```text
SNAPSHOT_SCHEMA_MANIFEST.json
```

pour une relocalisation Python.

---

# 126. Event manifest

Après `25`, même règle pour :

```text
DOMAIN_EVENT_MANIFEST.json
```

---

# 127. Computation manifests

Après `26`, les manifests doivent continuer à identifier :

```text
business definitions
```

pas des chemins Python internes non stables.

---

# 128. Migration tests

Chaque move doit ajouter au minimum :

```text
old public import still works if promised
new canonical internal import works
same semantic output
```

---

# 129. Import graph snapshot

Générer un artifact :

```text
PACKAGE_DEPENDENCY_GRAPH.json
```

avant et après chaque étape majeure.

---

# 130. Context cycles

CI doit refuser les nouveaux cycles entre bounded contexts.

---

# 131. Allowed dependency map

Artifact possible :

```text
CONTEXT_DEPENDENCY_RULES.toml
```

---

# 132. Example

```toml
[contexts.analysis]
may_depend_on = ["reporting", "shared"]

[contexts.reporting]
may_depend_on = ["ledger", "references", "shared"]

[contexts.ledger]
may_depend_on = ["periods", "charts", "shared"]
```

---

# 133. Forbidden dependency example

```text
ledger
    → analysis
```

doit être interdit.

---

# 134. Another forbidden example

```text
reporting
    → consolidation
```

si reporting est upstream de consolidation.

---

# 135. Context map

Le graphe cible doit refléter le flux métier :

```text
references
    ↓
policies
    ↓
charts
    ↓
ledger
    ↓
reporting
    ↓
analysis
```

avec branches :

```text
imports → ledger
subledgers → ledger
closing → ledger/periods
reconciliation ← snapshots/read models
consolidation ← entity reporting snapshots
```

---

# 136. Commands and queries

Chaque context peut séparer :

```text
application/commands
application/queries
```

si la complexité le justifie.

Ne pas imposer CQRS structurel partout.

---

# 137. Ports ownership

Le port appartient normalement au **consumer du port**.

Exemple :

```text
ledger needs CompanyChartResolver
```

donc le contract peut appartenir à :

```text
ledger/ports/chart_resolution.py
```

même si l'implémentation vient du context `charts`.

---

# 138. Provider inversion

```text
ledger
defines what it needs
```

et :

```text
charts/infrastructure adapter
```

ou composition root l'implémente.

---

# 139. Shared ports

Certains ports réellement transverses peuvent rester communs :

```text
Clock
ArtifactStore
```

mais ils doivent être rares.

---

# 140. UnitOfWork problem

La UoW actuelle regroupe :

```text
entries
periods
journals
audit
idempotency
outbox
clock
```

Elle traverse plusieurs concepts.

---

# 141. UnitOfWork target

Deux options futures :

```text
A. ledger owns transaction boundary
B. application transaction port remains infrastructure-shared
```

Recommandation brownfield :

> conserver une UoW transverse pendant la migration.

Ne pas fragmenter artificiellement les transactions avant d'avoir redéfini les aggregate boundaries.

---

# 142. Future UoW refinement

Une phase ultérieure pourra distinguer :

```text
LedgerUnitOfWork
ImportExecutionUnitOfWork
```

si cela réduit réellement le couplage.

Pas dans la première migration topologique.

---

# 143. InMemory adapter

L'InMemory adapter peut rester :

```text
infrastructure/in_memory
```

pour les transactions core partagées.

Les fakes spécialisés peuvent vivre dans :

```text
testing/
```

---

# 144. Django adapter

Ne pas créer :

```text
12 Django apps
```

uniquement pour refléter les bounded contexts.

La topologie Python et la structure Django n'ont pas besoin d'être identiques.

---

# 145. SQLAlchemy adapter

Même principe :

```text
one metadata / transaction boundary
```

peut supporter plusieurs contexts.

---

# 146. Migration anti-pattern — Big Bang

Interdit :

```text
move 300 files
fix imports
merge
```

sans qualification contextuelle.

---

# 147. Migration anti-pattern — package purity over semantics

Ne pas casser une transaction métier valide uniquement pour obtenir une arborescence esthétique.

---

# 148. Migration anti-pattern — Shared dump

Ne pas résoudre les cycles avec :

```text
move everything to shared
```

---

# 149. Migration anti-pattern — Re-export forever

Les shims sont temporaires.

Sinon le projet supporte indéfiniment deux topologies.

---

# 150. Migration anti-pattern — Public internals

Ne pas exposer soudainement :

```text
pyaccountingkit.ledger.domain.*
```

comme API publique stable par accident.

---

# 151. Migration anti-pattern — Context per noun

Tous les noms métier ne deviennent pas un bounded context.

Exemple :

```text
Journal
Entry
Line
```

n'ont pas besoin de trois contexts.

---

# 152. Migration anti-pattern — Context per folder size

Le bounded context est défini par :

```text
language
ownership
invariants
change reasons
```

pas par le nombre de fichiers.

---

# 153. Migration anti-pattern — duplicating models

Pendant transition, éviter :

```text
LegacyJournalEntry
NewJournalEntry
```

si le but est seulement de changer le package.

---

# 154. Source movement strategy

Préférer :

```text
git mv
```

ou commits clairement dédiés à la relocalisation.

Séparer :

```text
move-only commit
```

de :

```text
behavioral change commit
```

lorsque possible.

---

# 155. Reviewability

Chaque PR de migration doit rester :

```text
reviewable
bisectable
revertable
```

---

# 156. Recommended PR size

Un PR peut migrer :

```text
one bounded context
```

ou une slice cohérente.

Pas toute la codebase.

---

# 157. Migration checklist — before

```text
[ ] owner context identified
[ ] import graph captured
[ ] public exposure identified
[ ] tests green before move
[ ] golden baseline captured
[ ] adapter contracts known
```

---

# 158. Migration checklist — during

```text
[ ] target package created
[ ] files moved without semantic redesign
[ ] imports updated
[ ] compatibility shim added if required
[ ] architecture rule added
```

---

# 159. Migration checklist — after

```text
[ ] unit tests green
[ ] property tests green
[ ] contract tests green
[ ] integration tests green
[ ] golden/replay green
[ ] public API manifest unchanged where expected
[ ] no new context cycle
```

---

# 160. Target architecture validation

Le nouveau validator doit pouvoir exprimer :

```text
shared cannot import contexts

domain cannot import application/adapters

context A can import only allowed published contracts of context B

infrastructure can depend on ports

public can depend on application surfaces
```

---

# 161. Import-linter

Le document `24` recommande :

```text
import-linter
```

Il est particulièrement adapté à la topologie cible.

---

# 162. Example contracts

Conceptuellement :

```text
Layer contract:
ledger.domain
must not import
ledger.application
```

---

# 163. Context contract

```text
analysis
may depend on
reporting
shared

analysis
must not depend on
ledger adapters
```

---

# 164. Independence contract

```text
shared
must remain independent
```

---

# 165. Technology contract

```text
django
sqlalchemy
psycopg
```

restent interdits dans les domain packages.

---

# 166. Testing contract

Après `28` :

```text
production packages
X pyaccountingkit.testing
```

---

# 167. Semantic layer placement

Le futur bounded context semantic défini dans `31` pourra devenir :

```text
semantic/
├── domain/
├── application/
├── ports/
└── adapters/
```

lorsque l'implémentation commencera.

---

# 168. Reproducibility ownership

Les manifests spécialisés restent avec leur capability :

```text
closing
reporting
analysis
reconciliation
consolidation
semantic
```

---

# 169. Domain events ownership

Même logique :

```text
ledger.events
closing.events
subledgers.events
```

---

# 170. Public event schemas

Les events exposés à l'extérieur peuvent être regroupés dans un registry public sans déplacer leur ownership.

---

# 171. Migration versions

La migration peut s'étendre sur plusieurs pre-releases.

Il n'est pas nécessaire d'attendre une seule version majeure si :

```text
public API remains compatible
```

---

# 172. Breaking change policy

La suppression de chemins internes non publics peut être considérée non-breaking selon la policy.

Mais toute import path documentée comme publique doit suivre SemVer.

---

# 173. Compatibility window

Pour les imports publiquement consommés :

```text
new path introduced
old path deprecated
one documented compatibility window
old path removed at declared version
```

---

# 174. Release notes

Chaque context migré doit apparaître dans :

```text
CHANGELOG
migration notes
```

si les consumers sont affectés.

---

# 175. Documentation topology

Les specs restent organisées par thèmes métier et gouvernance.

Elles ne doivent pas être renommées mécaniquement avec les packages.

---

# 176. Code owners

Une future configuration CODEOWNERS peut refléter :

```textledger
reporting
reconciliation
```

si l'équipe grandit.

---

# 177. Build/package implications

La migration reste dans :

```text
one Python distribution
```

Il ne s'agit pas d'un passage en micro-packages.

---

# 178. Modular monolith

La cible reste :

```text
one installable package
one version
one release train
```

avec modules internes fortement délimités.

---

# 179. Pas de microservices

Domain-first ne signifie pas :

```text
one service per context
```

La séparation de déploiement est une décision future indépendante.

---

# 180. Pas de multi-repo

La migration n'impose pas :

```text
one repository per bounded context
```

---

# 181. Performance

Changer la topologie de package ne doit pas modifier les hot paths.

---

# 182. Import-time behavior

La migration doit préserver :

```text
import pyaccountingkit
```

sans side effect infrastructure.

---

# 183. Optional dependencies

Django/SQLAlchemy restent optionnels.

La nouvelle topologie ne doit pas les rendre obligatoires.

---

# 184. `py.typed`

Reste à la racine.

---

# 185. Type checking

Les moves doivent préserver :

```text
strict mypy
```

ou la baseline de typing active.

---

# 186. Circular import risk

Domain-first peut révéler des cycles auparavant masqués par les layers.

C'est un bénéfice :

> le cycle signale souvent une frontière métier mal définie.

---

# 187. Résolution des cycles

Ordre de préférence :

```text
1. published contract
2. invert dependency through port
3. event / snapshot
4. application orchestration
5. shared primitive only if genuinely shared
```

---

# 188. Ne pas résoudre par import local par défaut

Les imports locaux peuvent masquer le cycle mais ne règlent pas le problème architectural.

---

# 189. Pilot success criteria

Un context pilote est réussi si :

```text
new package is canonical
legacy paths are shims only
public behavior unchanged
all tests green
new context fitness rules active
no additional shared coupling
```

---

# 190. Proposed migration roadmap

## DFT-00 — Inventory & dependency graph

```text
PACKAGE_TOPOLOGY_BASELINE.json
```

---

## DFT-01 — Context ownership registry

```text
CONTEXT_OWNERSHIP.json
```

---

## DFT-02 — Minimal shared kernel

```text
core review
shared target
no domain dumping
```

---

## DFT-03 — Analysis pilot

```text
analysis/domain
analysis/application
analysis/ports
```

---

## DFT-04 — Reconciliation

```text
reconciliation vertical slice
```

---

## DFT-05 — Imports

```text
imports + FEC adapter
```

---

## DFT-06 — Reporting

```text
statements
regulatory
snapshots
```

---

## DFT-07 — Subledgers

```text
receivables
payables
settlements
aging
```

---

## DFT-08 — Closing / Periods

Clarify ownership before move.

---

## DFT-09 — References / Policies / Charts

Migrate reference authority chain.

---

## DFT-10 — Ledger

Central high-risk migration.

---

## DFT-11 — Infrastructure consolidation

```text
Django
SQLAlchemy
InMemory
```

---

## DFT-12 — Remove legacy layer roots

After compatibility window.

---

# 191. Priorities

| Lot | Priorité |
|---|---:|
| DFT-00 | P0 |
| DFT-01 | P0 |
| DFT-02 | P0 |
| DFT-03 | P0 |
| DFT-04 | P0 |
| DFT-05 | P1 |
| DFT-06 | P1 |
| DFT-07 | P1 |
| DFT-08 | P1 |
| DFT-09 | P1 |
| DFT-10 | P1 / high-risk |
| DFT-11 | P2 |
| DFT-12 | P2 |

---

# 192. ADR proposées

| ADR | Décision |
|---|---|
| ADR-DFT-001 | PyAccountingKit adopte progressivement une topologie domain-first |
| ADR-DFT-002 | La migration reste un modular monolith, pas un passage microservices |
| ADR-DFT-003 | Les bounded contexts deviennent l'axe principal d'organisation |
| ADR-DFT-004 | L'architecture Hexagonal reste valide à l'intérieur de chaque context |
| ADR-DFT-005 | `shared` reste minimal |
| ADR-DFT-006 | Les objets avec owner métier clair ne vont pas dans `shared` |
| ADR-DFT-007 | L'API `public/` reste séparée et stable |
| ADR-DFT-008 | Les context internals ne deviennent pas public API par défaut |
| ADR-DFT-009 | Les ports sont progressivement rapprochés de leur consumer context |
| ADR-DFT-010 | Les adapters mono-context sont colocalisés avec leur context |
| ADR-DFT-011 | Les adapters transactionnels cross-context peuvent rester dans `infrastructure/` |
| ADR-DFT-012 | FEC devient un adapter du context Imports |
| ADR-DFT-013 | CFA FRA reste une integration/migration boundary |
| ADR-DFT-014 | La UoW transverse n'est pas fragmentée durant la première migration |
| ADR-DFT-015 | Les moves de package évitent les changements métier simultanés |
| ADR-DFT-016 | La migration est context-by-context, jamais big-bang |
| ADR-DFT-017 | Les legacy shims sont behavior-free et temporaires |
| ADR-DFT-018 | Les context dependency rules sont exécutables en CI |
| ADR-DFT-019 | Les cycles entre contexts sont refusés sauf exception documentée |
| ADR-DFT-020 | Cross-context access utilise published contracts, ports ou snapshots |
| ADR-DFT-021 | Analysis reste downstream/read-only |
| ADR-DFT-022 | Reconciliation ne devient pas un posting engine |
| ADR-DFT-023 | Consolidation ne modifie pas les entity ledgers |
| ADR-DFT-024 | Public API manifests ne doivent pas dériver à cause d'un simple move |
| ADR-DFT-025 | Snapshot schemas ne changent pas pour une simple relocalisation |
| ADR-DFT-026 | Event identities ne dépendent pas des module paths |
| ADR-DFT-027 | Computation manifests ne pinent pas des internals Python inutilement |
| ADR-DFT-028 | `import pyaccountingkit` reste infrastructure-free |
| ADR-DFT-029 | Django/SQLAlchemy restent optionnels |
| ADR-DFT-030 | La topologie Python n'impose pas une Django app par bounded context |
| ADR-DFT-031 | Les adapters tiers continuent d'être qualifiés par contract suites |
| ADR-DFT-032 | La migration doit préserver golden et replay semantics |
| ADR-DFT-033 | Le graphe des imports est capturé avant et après les moves majeurs |
| ADR-DFT-034 | Ledger est migré tardivement compte tenu de son blast radius |
| ADR-DFT-035 | Un context pilote valide la méthode avant généralisation |
| ADR-DFT-036 | Les paths legacy promis publiquement suivent une deprecation window |
| ADR-DFT-037 | Les paths purement internes peuvent évoluer selon la release policy |
| ADR-DFT-038 | `testing/` ne peut jamais être importé par la production domain layer |
| ADR-DFT-039 | Le validator architecture évolue vers layer + context fitness |
| ADR-DFT-040 | La topologie cible doit refléter le langage métier avant la technologie |

---

# 193. Architecture Fitness Functions associées

```text
AFF-DFT-001
shared MUST NOT import bounded contexts

AFF-DFT-002
<context>.domain MUST NOT import infrastructure

AFF-DFT-003
<context>.domain MUST NOT import <context>.application

AFF-DFT-004
production contexts MUST NOT import pyaccountingkit.testing

AFF-DFT-005
cross-context imports MUST respect declared context dependency map

AFF-DFT-006
analysis MUST NOT import ledger write adapters

AFF-DFT-007
reconciliation MUST NOT directly mutate ledger internals

AFF-DFT-008
consolidation MUST NOT mutate entity-ledger aggregates
```

---

# 194. Definition of Done — architecture model

```text
[ ] target contexts defined
[ ] shared kernel policy defined
[ ] infrastructure edge policy defined
[ ] public facade policy defined
[ ] integration edge policy defined
[ ] context dependency map defined
```

---

# 195. Definition of Done — inventory

```text
[ ] every domain module has an owner
[ ] every application module has an owner
[ ] every port has an owner
[ ] every adapter has an owner or infrastructure classification
[ ] public exposure identified
[ ] import graph generated
```

---

# 196. Definition of Done — pilot context

```text
[ ] target package created
[ ] business behavior unchanged
[ ] new path canonical internally
[ ] compatibility shim added if required
[ ] tests green
[ ] architecture rules active
[ ] no new cycles
[ ] public manifest unchanged where expected
```

---

# 197. Definition of Done — full migration

```text
[ ] all bounded contexts domain-first
[ ] old domain/application roots removed or compatibility-only
[ ] old ports root removed or reduced to deliberate shared contracts
[ ] adapters root replaced/reduced appropriately
[ ] infrastructure package explicit
[ ] public API stable
[ ] testing package operational
[ ] architecture CI validates context map
[ ] all golden/replay/concurrency gates green
```

---

# 198. Example — before

```text
pyaccountingkit/
├── domain/
│   ├── journals/
│   └── ledger/
├── application/
│   └── ledger/
├── ports/
│   ├── repositories.py
│   └── unit_of_work.py
└── adapters/
    ├── django/
    └── sqlalchemy/
```

---

# 199. Example — after

```text
pyaccountingkit/
├── ledger/
│   ├── domain/
│   │   ├── journal_entry.py
│   │   ├── journal_line.py
│   │   ├── posting.py
│   │   └── reversal.py
│   ├── application/
│   │   ├── post.py
│   │   └── reverse.py
│   └── ports/
│       ├── repositories.py
│       └── chart_resolution.py
│
└── infrastructure/
    ├── django/
    └── sqlalchemy/
```

---

# 200. Example — Imports

Avant :

```text
domain/imports
application/imports
ports/accounting_import.py
adapters/imports/fec
```

Après :

```text
imports/
├── domain/
├── application/
├── ports/
└── adapters/
    └── fec/
```

C'est l'exemple le plus naturel de vertical slice.

---

# 201. Example — Analysis

Avant :

```text
domain/analysis
application/analysis
public/analysis.py
```

Après :

```text
analysis/
├── domain/
├── application/
└── contracts.py

public/analysis.py
```

La public façade reste séparée.

---

# 202. Example — Reconciliation

Avant :

```text
domain/reconciliation
application/reconciliation
ports/reconciliation.py
adapters/reconciliation
```

Après :

```text
reconciliation/
├── domain/
├── application/
├── ports/
└── adapters/
```

---

# 203. Migration risk matrix

| Risque | Impact | Mitigation |
|---|---:|---|
| Circular imports | élevé | context dependency map |
| Public import break | élevé | façade + shims |
| Broken pickle paths | moyen | no internal pickle guarantee |
| Adapter break | élevé | contract suites |
| Golden drift | critique | golden/replay gates |
| UoW fragmentation | critique | defer transactional redesign |
| Shared kernel growth | élevé | ADR + fitness |
| Giant refactor PR | élevé | context-by-context |
| Duplicate models | élevé | move, don't rewrite |
| Test path churn | moyen | migrate progressively |

---

# 204. Why not keep Layer-First forever?

Layer-first remains viable for small and medium systems.

But as PyAccountingKit grows, domain-first provides:

```text
better cohesion
clearer ownership
easier bounded-context navigation
stronger context-level architecture tests
lower accidental coupling
more autonomous feature evolution
```

---

# 205. Why not pure Domain-First everywhere?

Because some technical responsibilities are genuinely cross-context:

```text
transaction manager
Django ORM
SQLAlchemy metadata
database connection
migration tooling
```

Forcing them into one context would create false ownership.

Hence the **hybrid domain-first** recommendation.

---

# 206. Why this remains Hexagonal

Inside each context:

```text
Domain
    ↓
Application
    ↓
Ports
    ↑
Adapters
```

The organizing axis changes.

The dependency inversion does not.

---

# 207. Why this remains Clean Architecture compatible

The rule remains:

```text
dependencies point inward
```

The package tree simply reflects:

```text
business ownership first
```

rather than grouping every layer globally.

---

# 208. Why this strengthens DDD

A bounded context becomes visible in code as :

```text
one navigable package
```

rather than a concept spread across four roots.

---

# 209. Final target principle

```text
BUSINESS CAPABILITY
        first

TECHNICAL LAYER
        second
```

---

# 210. Conclusion

PyAccountingKit a atteint un stade où sa structure métier est plus riche que sa structure de packages racine.

L'architecture actuelle :

```text
core
domain
application
ports
adapters
```

a correctement protégé les frontières techniques.

La prochaine évolution doit rendre visibles les frontières métier déjà présentes dans les specs et le code.

La cible est donc :

```text
Domain-First
    +
Hexagonal inside each context
    +
Minimal Shared Kernel
    +
Explicit Infrastructure Edge
    +
Stable Public Facade
```

avec une migration :

```text
context by context
```

et non :

```text
big bang
```

Le principe final est :

> **PyAccountingKit doit être navigable d'abord par langage comptable et capacités métier, tout en conservant Ports & Adapters comme mécanisme d'isolation interne et une infrastructure transversale uniquement là où la transaction ou la technologie l'exige réellement.**