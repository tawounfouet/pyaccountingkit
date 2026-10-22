# 24_PYACCOUNTINGKIT_ARCHITECTURE_FITNESS_FUNCTIONS.md

# PyAccountingKit — Architecture Fitness Functions

> **Projet** : PyAccountingKit  
> **Document** : `24_PYACCOUNTINGKIT_ARCHITECTURE_FITNESS_FUNCTIONS.md`  
> **Statut** : Spécification d'architecture et de gouvernance exécutable  
> **Version documentaire** : 1.0  
> **Date** : 22 octobre 2026  
> **Baseline observée** : PyAccountingKit `0.7.0rc1`  
> **Langue** : Français  

---

# 1. Objet

Ce document définit les **Architecture Fitness Functions** de PyAccountingKit.

Une fitness function est un contrôle automatisé qui vérifie qu'une propriété architecturale reste vraie au fil de l'évolution du code.

Objectif :

```text
ARCHITECTURE DOCUMENTED
        +
ARCHITECTURE TESTED
        +
ARCHITECTURE ENFORCED
```

Il s'agit notamment de transformer :

```text
"le domaine ne dépend pas de Django"
```

en :

```text
une règle exécutable en CI
```

---

# 2. Contexte

PyAccountingKit dispose déjà d'une baseline architecturale riche :

```text
Reference
→ Accounting Policies & Measurement
→ Accounting Core
→ Ledger
→ Reporting
→ Financial Analysis
```

avec :

```text
Controls
Audit
Traceability
Imports
Persistence
Concurrency
Adapters
```

La structure actuelle est principalement organisée par couches :

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

Le repository possède déjà :

- pytest ;
- mypy strict ;
- Ruff ;
- tests d'intégration ;
- tests de concurrence ;
- manifests ;
- ADR ;
- release qualification ;
- adapter contracts ;
- public API qualification.

Cependant, plusieurs frontières restent principalement documentées ou testées ponctuellement.

La cible est de rendre ces frontières **exécutables**.

---

# 3. Inspiration

Le pattern retenu de PyTradeKit est :

```text
architecture decisions
        ↓
import contracts
        ↓
CI
```

Principe :

> Une frontière importante ne doit pas dépendre uniquement de la discipline humaine.

---

# 4. Types de fitness functions

```text
STATIC
STRUCTURAL
SEMANTIC
CONTRACTUAL
RUNTIME
RELEASE
```

Exemples :

```text
domain X adapters
```

```text
Financial Analysis cannot mutate JournalEntry
```

```text
clean wheel install must succeed without Django
```

---

# 5. Défense en profondeur

```text
Specification
    ↓
ADR
    ↓
Import Contracts
    ↓
Static Analysis
    ↓
Architecture Tests
    ↓
Integration Tests
    ↓
Release Qualification
```

Les fitness functions ne remplacent pas :

```text
unit tests
integration tests
property-based tests
concurrency tests
consumer tests
regulatory evidence
code review
```

---

# 6. Taxonomie

Les règles sont regroupées en :

```text
AFF-CORE
AFF-DOMAIN
AFF-APPLICATION
AFF-PORTS
AFF-ADAPTERS
AFF-REFERENCE
AFF-REPORTING
AFF-ANALYSIS
AFF-RECONCILIATION
AFF-CONSOLIDATION
AFF-SEMANTIC
AFF-PUBLIC
AFF-PACKAGING
AFF-REGULATORY
AFF-SCOPE
```

---

# 7. Architecture logique

```text
Core Primitives
      ↓
Domain
      ↓
Application
      ↓
Ports
      ↑
Adapters
```

Les adapters implémentent les ports.

Les abstractions ne dépendent jamais de leurs implémentations.

---

# 8. Core minimal

`pyaccountingkit.core` contient uniquement des primitives transverses stables.

Exemples :

```text
Clock
Money
Currency
Typed IDs
Revision
Idempotency primitives
shared errors
```

Il ne doit pas devenir un package générique de dumping.

---

# 9. Règles Core

## AFF-CORE-001

```text
pyaccountingkit.core
MUST NOT import
pyaccountingkit.domain
```

## AFF-CORE-002

```text
pyaccountingkit.core
MUST NOT import
pyaccountingkit.application
```

## AFF-CORE-003

```text
pyaccountingkit.core
MUST NOT import
pyaccountingkit.adapters
```

## AFF-CORE-004

```text
pyaccountingkit.core
MUST NOT import
django
sqlalchemy
psycopg
```

---

# 10. Domaine framework-neutral

Le domaine ne doit connaître aucun ORM ou framework web.

Interdit :

```python
from django.db import models
```

ou :

```python
from sqlalchemy.orm import Session
```

dans `pyaccountingkit.domain`.

---

# 11. Règles Domain

## AFF-DOMAIN-001

```text
pyaccountingkit.domain
MUST NOT import
pyaccountingkit.adapters
```

## AFF-DOMAIN-002

```text
pyaccountingkit.domain
MUST NOT import
django
```

## AFF-DOMAIN-003

```text
pyaccountingkit.domain
MUST NOT import
sqlalchemy
```

## AFF-DOMAIN-004

```text
pyaccountingkit.domain
MUST NOT import
psycopg
```

## AFF-DOMAIN-005

Le domaine ne dépend pas de :

```text
FastAPI
Flask
Celery
Pandas
Power BI SDK
cloud SDK
```

sauf ADR explicite.

---

# 12. Application

L'application orchestre :

```text
domain
ports
commands
queries
transactions
```

Elle ne dépend pas directement d'un adapter concret.

## AFF-APPLICATION-001

```text
pyaccountingkit.application
MUST NOT import
pyaccountingkit.adapters
```

## AFF-APPLICATION-002

L'application n'expose pas :

```text
Django QuerySet
SQLAlchemy Session
```

dans ses contrats métier.

---

# 13. Ports

Les ports définissent :

```text
Repository Protocols
UnitOfWork
Reference Providers
Storage Providers
Exporters
Renderers
Clock
Audit
Outbox
Idempotency
```

## AFF-PORTS-001

```text
pyaccountingkit.ports
MUST NOT import
pyaccountingkit.adapters
```

## AFF-PORTS-002

Les signatures de ports n'exposent aucun objet ORM.

---

# 14. Adapters

Les adapters peuvent dépendre :

```text
domain contracts
application DTOs
ports
external frameworks
```

mais pas l'inverse.

## AFF-ADAPTERS-001

```text
adapter → port
```

autorisé.

```text
port → adapter
```

interdit.

## AFF-ADAPTERS-002

Django reste dans une frontière adapter dédiée.

## AFF-ADAPTERS-003

SQLAlchemy reste dans une frontière adapter dédiée.

## AFF-ADAPTERS-004

```python
import pyaccountingkit
```

doit fonctionner sans Django ou SQLAlchemy installés.

---

# 15. Packaging

Le `pyproject.toml` actuel sépare déjà les extras :

```text
django
sqlalchemy
dev
```

des dépendances core.

Cette propriété devient un contrat.

## AFF-PACKAGING-001

```text
pip install pyaccountingkit
```

ne doit pas installer obligatoirement :

```text
Django
SQLAlchemy
psycopg
```

## AFF-PACKAGING-002

```text
python -c "import pyaccountingkit"
```

doit fonctionner en environnement core-only.

## AFF-PACKAGING-003

Le core runtime ne dépend pas d'un fichier présent uniquement dans :

```text
resources/
data/
```

si ces répertoires sont exclus des artifacts distribués.

## AFF-PACKAGING-004

Les smoke tests de wheel doivent fonctionner hors checkout Git.

---

# 16. Reference architecture

Direction cible :

```text
Accounting Domain
      ↓
Reference Port
      ↑
Concrete Provider
```

## AFF-REFERENCE-001

Le domaine de référence ne dépend pas d'un provider réglementaire concret.

## AFF-REFERENCE-002

Interdit comme architecture universelle :

```python
if standard == "PCG":
    ...
elif standard == "SYSCOHADA":
    ...
```

lorsque la règle doit venir d'un provider ou d'une policy.

Cette règle est sémantique et doit être testée par pytest/review.

## AFF-REFERENCE-003

```text
canonical identity != provider identity
```

Exemples :

```text
AccountId != PCG AccountCode
PartyId != CustomerNumber
JournalEntryId != EntryNumber
```

---

# 17. Reporting

Le reporting est downstream.

## AFF-REPORTING-001

Reporting ne poste jamais directement une écriture.

## AFF-REPORTING-002

Reporting consomme :

```text
ledger queries
trial balance snapshots
statement mappings
```

et non les write repositories lorsque la séparation est applicable.

---

# 18. Financial Analysis

La baseline définit Financial Analysis comme :

```text
downstream
read-only
```

## AFF-ANALYSIS-001

Financial Analysis ne peut pas :

```text
post
reverse
close period
mutate account
allocate settlement
```

## AFF-ANALYSIS-002

Financial Analysis consomme :

```text
Ledger
Trial Balance
Financial Statements
Snapshots
```

via des read contracts.

---

# 19. Reconciliation

Principe :

```text
Reconciliation
matches and explains
but never becomes a second posting engine
```

## AFF-RECONCILIATION-001

Toute correction passe par :

```text
Reconciliation
      ↓
JournalEntryProposal
      ↓
normal Posting workflow
```

## AFF-RECONCILIATION-002

Reconciliation ne modifie pas directement une `JournalEntry`.

## AFF-RECONCILIATION-003

Les adapters bancaires restent hors du domaine de matching.

---

# 20. Consolidation

## AFF-CONSOLIDATION-001

```text
Consolidation
MUST NOT mutate
entity-level ledger
```

## AFF-CONSOLIDATION-002

Les éliminations restent dans le contexte groupe.

---

# 21. Corporate Finance boundary

Le core n'inclut pas :

```text
NPV
IRR
WACC
DCF
CAPM
Beta
Market Risk
Monte Carlo
```

## AFF-SCOPE-001

Aucun package Corporate Finance ou Valuation ne devient dépendance du core sans ADR.

## AFF-SCOPE-002

Aucun SDK de market data ne devient une dépendance obligatoire.

---

# 22. Financial Semantic Layer

La Financial Semantic Layer reste :

```text
downstream
read-only
framework-neutral
```

## AFF-SEMANTIC-001

Le domaine sémantique ne dépend pas de :

```text
Django
SQLAlchemy
Power BI SDK
Tableau SDK
```

## AFF-SEMANTIC-002

Le semantic core ne dépend d'aucun adapter BI.

## AFF-SEMANTIC-003

La semantic layer ne mute jamais le ledger.

## AFF-SEMANTIC-004

Les adapters BI dépendent des contrats sémantiques, jamais l'inverse.

---

# 23. Shared Kernel

Si `pyaccountingkit.shared` est introduit :

## AFF-SHARED-001

```text
shared
MUST NOT import
bounded contexts
```

## AFF-SHARED-002

Ne doivent pas migrer dans `shared` :

```text
JournalEntry
Settlement
FinancialStatement
ReferenceAccount
```

---

# 24. Unit of Work

Le `UnitOfWorkProtocol` actuel groupe notamment :

```text
entries
periods
journals
audit
idempotency
outbox
clock
```

## AFF-UOW-001

Les adapters implémentent le contrat UoW sans changer sa sémantique.

## AFF-UOW-002

Les opérations critiques ne contournent pas le UoW.

Propriété transactionnelle :

```text
domain mutation
+
audit
+
idempotency
+
outbox
=
single atomic commit
```

Cette propriété relève des tests d'intégration.

---

# 25. Outbox

## AFF-OUTBOX-001

Le domaine ne dépend pas de :

```text
Kafka SDK
RabbitMQ SDK
Azure Service Bus SDK
AWS SNS/SQS SDK
```

---

# 26. Public API

La public API masque :

```text
ORM
repositories
transactions
```

## AFF-PUBLIC-001

Aucun objet ORM n'est retourné comme contrat public.

## AFF-PUBLIC-002

Les exemples utilisateurs passent par :

```text
AccountingApplication
public facades
```

## AFF-PUBLIC-003

Les symbols publics sont déclarés explicitement.

---

# 27. Regulatory fail-closed

## AFF-REGULATORY-001

Un provider ne transmet pas du JSON brut dans le domaine lorsque des DTO/contracts canoniques existent.

## AFF-REGULATORY-002

Un statut :

```text
candidate
draft
partial
unknown
```

ne devient jamais implicitement exécutable.

## AFF-FAILCLOSED-001

Toute résolution critique ambiguë échoue explicitement.

---

# 28. Capability model

Les adapters peuvent exposer :

```text
supports_pessimistic_locking
supports_transactional_outbox
supports_advisory_locks
```

## AFF-CAP-001

Une capability absente n'est jamais simulée silencieusement comme disponible.

---

# 29. Security context

## AFF-SEC-001

Le domaine ne dépend pas de :

```text
Django auth
Azure AD SDK
Auth0 SDK
```

Un contexte métier minimal peut utiliser :

```text
ActorId
TenantId
```

---

# 30. Testing Toolkit

Le futur `pyaccountingkit.testing` reste downstream.

## AFF-TESTING-001

```text
core/domain
MUST NOT import
pyaccountingkit.testing
```

---

# 31. Import-time behavior

## AFF-IMPORT-001

```python
import pyaccountingkit
```

ne doit pas :

```text
connect database
read secrets
perform network calls
run migrations
discover plugins destructively
```

---

# 32. Outil principal : import-linter

Le principal outil recommandé pour les dépendances internes est :

```text
import-linter
```

Il permet :

```text
forbidden imports
independence contracts
layer contracts
```

---

# 33. Dépendance de développement

Proposition :

```toml
[project.optional-dependencies]
dev = [
    ...
    "import-linter>=2,<3",
]
```

La version exacte doit être validée lors de l'implémentation.

---

# 34. Configuration indicative

```toml
[tool.importlinter]
root_package = "pyaccountingkit"
```

---

# 35. Contrat Core

Exemple indicatif :

```toml
[[tool.importlinter.contracts]]
name = "Core primitives are independent"
type = "forbidden"
source_modules = [
    "pyaccountingkit.core",
]
forbidden_modules = [
    "pyaccountingkit.domain",
    "pyaccountingkit.application",
    "pyaccountingkit.ports",
    "pyaccountingkit.adapters",
    "pyaccountingkit.integrations",
]
```

La syntaxe exacte doit être vérifiée avec la version d'import-linter retenue.

---
# 36. Contrat Domain

```toml
[[tool.importlinter.contracts]]
name = "Domain does not depend on adapters"
type = "forbidden"
source_modules = [
    "pyaccountingkit.domain",
]
forbidden_modules = [
    "pyaccountingkit.adapters",
]
```

---

# 37. Contrat Application

```toml
[[tool.importlinter.contracts]]
name = "Application does not depend on adapters"
type = "forbidden"
source_modules = [
    "pyaccountingkit.application",
]
forbidden_modules = [
    "pyaccountingkit.adapters",
]
```

---

# 38. Contrat Ports

```toml
[[tool.importlinter.contracts]]
name = "Ports do not depend on adapters"
type = "forbidden"
source_modules = [
    "pyaccountingkit.ports",
]
forbidden_modules = [
    "pyaccountingkit.adapters",
]
```

---

# 39. AST checks

Import-linter protège principalement le graphe interne.

Des tests AST complémentaires doivent vérifier :

```text
django
sqlalchemy
psycopg
```

dans les chemins protégés.

---

# 40. Pourquoi plusieurs outils

```text
import-linter
    = dependency graph

AST / pytest
    = forbidden external imports

mypy
    = type boundaries

contract tests
    = behavior boundaries

clean install
    = packaging boundaries
```

---

# 41. Tests d'architecture

Créer :

```text
tests/architecture/
```

Structure possible :

```text
tests/architecture/
├── test_import_boundaries.py
├── test_external_framework_isolation.py
├── test_public_api_boundaries.py
├── test_bounded_context_write_capabilities.py
├── test_package_optional_dependencies.py
├── test_reference_provider_boundaries.py
└── test_architecture_manifest.py
```

---

# 42. Naming

Chaque test doit référencer la règle :

```python
def test_aff_domain_001_domain_does_not_import_adapters():
    ...
```

---

# 43. Règles sémantiques

Certaines frontières ne sont pas exprimables par import graph.

Exemple :

```text
Financial Analysis imports a public query port
```

est autorisé.

Mais :

```text
Financial Analysis calls PostingService
```

est interdit.

Ces règles nécessitent :

```text
pytest architecture tests
contract tests
code review
```

---

# 44. Mutation capability model

Les ports peuvent être classés :

```text
READ_PORT
WRITE_PORT
POSTING_PORT
ADMIN_PORT
```

Cela permet de vérifier les capacités autorisées par contexte.

---

# 45. Exemple Financial Analysis

Autorisé :

```text
TrialBalanceQueryPort
FinancialStatementQueryPort
```

Interdit :

```text
JournalEntryWriteRepository
PeriodCloseCommandPort
```

---

# 46. Exemple Semantic Layer

Autorisé :

```text
FinancialAnalysisQueryPort
StatementSnapshotQueryPort
TrialBalanceQueryPort
```

Interdit :

```text
PostingService
JournalEntryWriteRepository
```

---

# 47. Import graph artifact

La CI peut produire :

```text
architecture-import-graph.json
architecture-import-graph.dot
```

Utilités :

```text
review
cycle detection
domain-first migration
debt analysis
```

---

# 48. Cycles

## AFF-GRAPH-001

Aucun cycle inter-layer critique.

## AFF-GRAPH-002

Les cycles internes à un bounded context sont surveillés et justifiés.

---

# 49. Architecture Contract Manifest

Artifact recommandé :

```text
ARCHITECTURE_CONTRACT_MANIFEST.json
```

Exemple :

```json
{
  "version": "1",
  "rules": [
    {
      "id": "AFF-DOMAIN-001",
      "type": "forbidden_import",
      "source": "pyaccountingkit.domain",
      "target": "pyaccountingkit.adapters",
      "severity": "blocking"
    }
  ]
}
```

---

# 50. Métadonnées de règle

Chaque règle porte :

```text
id
description
owner
source ADR
source spec
severity
implementation
status
introduced version
```

---

# 51. Lifecycle

```text
PROPOSED
OBSERVE
BASELINED
ENFORCED
DEPRECATED
```

---

# 52. Brownfield strategy

PyAccountingKit est un projet mature.

Il ne faut pas introduire une règle qui rend immédiatement la CI rouge à cause de dette historique connue.

Processus :

```text
OBSERVE
→ BASELINE
→ WARN
→ ENFORCE
```

---

# 53. Étape Observe

Mesurer :

```text
current internal imports
external imports by layer
cycles
violations
```

sans bloquer.

---

# 54. Étape Baseline

Classer :

```text
true violation
intentional dependency
transitional debt
false positive
```

---

# 55. Étape No-new-debt

Une fois la baseline créée :

```text
new violation = CI failure
```

---

# 56. Étape Burn-down

Réduire progressivement les exceptions.

---

# 57. Exception registry

Artifact possible :

```text
architecture_exceptions.yaml
```

Exemple :

```yaml
- id: ARCH-EXC-001
  rule: AFF-APPLICATION-001
  path: pyaccountingkit.application.legacy_x
  reason: legacy migration
  expires: 2027-01-31
  owner: architecture
```

---

# 58. Pas de blanket ignore

Interdit :

```text
ignore entire package
```

sans justification précise.

---

# 59. CI pipeline

Pipeline cible :

```text
ruff
  ↓
mypy
  ↓
architecture-import-contracts
  ↓
architecture-semantic-tests
  ↓
unit tests
  ↓
property tests
  ↓
integration tests
  ↓
concurrency tests
  ↓
package build
  ↓
clean-install qualification
```

---

# 60. Job dédié

Nom recommandé :

```text
architecture
```

Artifacts :

```text
import contract result
architecture test result
exception report
dependency graph
fitness report
```

---

# 61. PR gate

Un PR ne peut être mergé si :

```text
new BLOCKING architecture violation
```

est introduite.

---

# 62. Diagnostic attendu

Exemple :

```text
AFF-DOMAIN-001 FAILED

pyaccountingkit.domain.reporting.metrics
    imports
pyaccountingkit.adapters.sqlalchemy.models

Domain must not depend on adapters.
```

---

# 63. Developer Experience

Commande locale cible :

```bash
lint-imports
```

et éventuellement :

```bash
pytest tests/architecture
```

ou :

```bash
make architecture
```

---

# 64. Pre-commit

Les checks rapides peuvent être intégrés à pre-commit.

Les checks lourds restent CI.

---

# 65. Architecture evidence

Artifact possible :

```text
architecture-fitness-report.json
```

Exemple :

```json
{
  "commit": "...",
  "architecture_contract_version": "1",
  "rules": {
    "AFF-DOMAIN-001": "PASS",
    "AFF-PORTS-001": "PASS"
  },
  "exceptions": [],
  "result": "PASS"
}
```

---

# 66. Release gate

Une RC stable doit satisfaire :

```text
all BLOCKING rules green
no expired exception
no undocumented architecture change
```

---

# 67. Architecture contract version

À distinguer de :

```text
package version
public API version
adapter contract version
```

Exemple :

```text
architecture_contract_version = 1
```

---

# 68. Initial rule set

Première livraison recommandée :

```text
AFF-CORE-001
AFF-CORE-002
AFF-CORE-003
AFF-DOMAIN-001
AFF-DOMAIN-002
AFF-DOMAIN-003
AFF-APPLICATION-001
AFF-PORTS-001
AFF-PACKAGING-001
AFF-PACKAGING-002
```

---

# 69. Semantic rules phase

Puis :

```text
AFF-ANALYSIS-001
AFF-RECONCILIATION-001
AFF-CONSOLIDATION-001
AFF-SEMANTIC-001
AFF-SEMANTIC-003
```

---

# 70. Roadmap

## AFF-00 — Tooling bootstrap

```text
add import-linter
create tests/architecture
```

## AFF-01 — Core/domain boundaries

```text
core isolation
domain X adapters
```

## AFF-02 — Application/ports

```text
application X adapters
ports X adapters
```

## AFF-03 — External frameworks

```text
domain X Django/SQLAlchemy
```

## AFF-04 — Packaging

```text
core-only
clean install
```

## AFF-05 — Semantic ownership

```text
analysis
reconciliation
consolidation
semantic layer
```

## AFF-06 — Manifest

```text
rule registry
release evidence
```

## AFF-07 — Domain-first support

```text
bounded-context contracts
public/internal boundaries
```

---

# 71. Priorités

| Lot | Priorité |
|---|---:|
| AFF-00 | P0 |
| AFF-01 | P0 |
| AFF-02 | P0 |
| AFF-03 | P0 |
| AFF-04 | P0 |
| AFF-05 | P1 |
| AFF-06 | P1 |
| AFF-07 | P2 |

---

# 72. Definition of Done — infrastructure

```text
[ ] import-linter ajouté aux dépendances dev
[ ] graphe actuel capturé
[ ] contrats initiaux encodés
[ ] tests/architecture créé
[ ] forbidden external imports test créé
[ ] job architecture créé
[ ] commande locale documentée
[ ] IDs AFF documentés
[ ] exception registry documenté
[ ] toute nouvelle violation bloque le merge
```

---

# 73. Definition of Done — hardened release

```text
[ ] core isolation enforced
[ ] domain/adapters separation enforced
[ ] application/adapters separation enforced
[ ] ports/adapters separation enforced
[ ] core-only import green
[ ] Financial Analysis read-only boundary green
[ ] Reconciliation no-direct-posting green
[ ] Consolidation no-entity-ledger-mutation green
[ ] public API manifest green
[ ] adapter contract manifest green
[ ] architecture evidence generated
```

---

# 74. ADR proposées

| ADR | Décision |
|---|---|
| ADR-AFF-001 | Architecture Fitness Functions deviennent une capacité de gouvernance de première classe |
| ADR-AFF-002 | Les dépendances internes sont principalement vérifiées avec import-linter |
| ADR-AFF-003 | Les dépendances externes interdites sont vérifiées par analyse statique complémentaire |
| ADR-AFF-004 | Les frontières sémantiques sont vérifiées avec pytest/contract tests |
| ADR-AFF-005 | Aucune nouvelle dette architecturale n'est acceptée après baseline |
| ADR-AFF-006 | Les violations historiques peuvent être baselinées temporairement |
| ADR-AFF-007 | Toute exception est identifiée, documentée et idéalement expirante |
| ADR-AFF-008 | Le domaine reste indépendant des ORM |
| ADR-AFF-009 | Les ports ne dépendent jamais des adapters |
| ADR-AFF-010 | L'application ne dépend pas d'un adapter concret |
| ADR-AFF-011 | `core` reste minimal |
| ADR-AFF-012 | La public API ne retourne aucun objet ORM |
| ADR-AFF-013 | Financial Analysis reste downstream et read-only |
| ADR-AFF-014 | Reconciliation ne devient jamais un posting engine |
| ADR-AFF-015 | Consolidation ne modifie jamais le ledger individuel |
| ADR-AFF-016 | Financial Semantic Layer reste indépendante des BI adapters |
| ADR-AFF-017 | Les providers réglementaires dépendent des contrats canoniques |
| ADR-AFF-018 | Le package core reste installable sans ORM |
| ADR-AFF-019 | Les règles bloquantes participent aux release gates |
| ADR-AFF-020 | Un manifest machine-readable d'architecture est recommandé |

---

# 75. Matrice règle / outil

| Règle | Outil |
|---|---|
| `core X domain` | import-linter |
| `domain X adapters` | import-linter |
| `application X adapters` | import-linter |
| `ports X adapters` | import-linter |
| `domain X django/sqlalchemy` | AST / pytest |
| core-only import | clean venv |
| Financial Analysis read-only | pytest architecture |
| Reconciliation no direct posting | contract test |
| Consolidation no entity-ledger mutation | integration |
| Semantic no ledger mutation | pytest architecture |
| public API no ORM | public API tests |
| adapter parity | contract tests |
| fail-closed reference resolution | domain tests |
| release architecture diff | manifest diff |

---

# 76. Exemples de violations

## Violation

```python
from pyaccountingkit.adapters.sqlalchemy import EntryModel
```

dans :

```text
pyaccountingkit.domain
```

Échec :

```text
AFF-DOMAIN-001
```

---

## Violation

```python
from pyaccountingkit.adapters.django.repositories import JournalRepository
```

dans :

```text
pyaccountingkit.application
```

Échec :

```text
AFF-APPLICATION-001
```

---

## Violation

```python
posting_service.post(...)
```

dans Financial Analysis.

Échec :

```text
AFF-ANALYSIS-001
```

---

# 77. Correction type

Au lieu de :

```python
from pyaccountingkit.adapters.sqlalchemy import SqlAlchemyEntryRepository
```

dans l'application :

```python
from pyaccountingkit.ports.repositories import JournalEntryRepositoryProtocol
```

puis injection dans la composition root.

---

# 78. Composition Root

Les adapters concrets sont assemblés dans des points prévus :

```text
application factory
consumer bootstrap
Django composition
CLI composition
test composition
```

## AFF-COMPOSITION-001

Les imports d'adapters concrets sont concentrés dans les composition roots autorisées.

---

# 79. Domain-first migration

Si le projet évolue vers :

```text
ledger/
    domain/
    application/
    ports/
    adapters/
```

les fitness functions doivent continuer à fonctionner pendant la coexistence avec la topologie actuelle.

Principe :

```text
new contexts → domain-first
legacy contexts → opportunistic migration
```

---

# 80. Bounded-context rules

## AFF-BC-001

Un bounded context ne doit pas importer les internals d'un autre bounded context.

Collaboration autorisée via :

```text
public contracts
ports
events
read models
```

---

# 81. Events

Un consommateur peut importer un event contract public.

Il ne doit pas importer l'implémentation interne du producteur.

---

# 82. Database ownership

Aucun bounded context ne doit requêter directement les tables internes d'un autre context comme contrat métier.

Cette propriété nécessite :

```text
repository ownership
integration tests
review
```

---

# 83. Read model exception

Les read models partagés restent autorisés s'ils sont explicitement contractuels.

---

# 84. Documentation parity

## AFF-DOC-001

Toute règle bloquante référence :

```text
spec
ou ADR
```

## AFF-DOC-002

Toute exception est documentée.

---

# 85. Metrics

La CI peut suivre :

```text
architecture_violations_total
architecture_exceptions_total
architecture_cycles_total
architecture_rules_enforced
```

KPI simple :

```text
Architecture Debt = active exceptions
```

Cible :

```text
new architecture debt = 0
```

---

# 86. Maturity model

## Level 0

```text
architecture in people's heads
```

## Level 1

```text
documented
```

## Level 2

```text
partially tested
```

## Level 3

```text
dependency architecture enforced
```

## Level 4

```text
semantic boundaries enforced
```

## Level 5

```text
architecture evidence integrated into releases
```

PyAccountingKit vise :

```text
Level 5
```

---

# 87. Architecture cible protégée

```text
                    ┌────────────────────┐
                    │       CORE         │
                    │ primitives only    │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │       DOMAIN       │
                    │ framework-neutral  │
                    └─────────┬──────────┘                              │
                              ▼
                    ┌────────────────────┐
                    │    APPLICATION     │
                    │ orchestration      │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │       PORTS        │
                    │ contracts          │
                    └─────────▲──────────┘
                              │
                    ┌─────────┴──────────┐
                    │      ADAPTERS      │
                    │ implementations    │
                    └────────────────────┘
```

Avec :

```text
Reporting
Financial Analysis
Reconciliation
Consolidation
Financial Semantic Layer
```

comme consommateurs respectant leurs frontières de mutation.

---

# 88. Principe final

> **Une décision architecturale importante qui peut être vérifiée automatiquement ne doit pas rester uniquement dans un document.**

La trajectoire est :

```text
DOCUMENT
   ↓
ADR
   ↓
RULE
   ↓
AUTOMATED CHECK
   ↓
CI GATE
   ↓
RELEASE EVIDENCE
```

---

# 89. Conclusion

Les Architecture Fitness Functions ne changent pas le modèle métier de PyAccountingKit.

Elles empêchent son érosion.

Elles garantissent progressivement que :

```text
the domain stays clean
the public API stays stable
adapters remain replaceable
regulatory providers remain external
read-side contexts remain read-only
financial mutations stay owned by the correct context
optional dependencies stay optional
semantic and BI layers do not contaminate accounting core
```

L'objectif final est de passer de :

```text
architecture by convention
```

à :

```text
architecture by executable contract
```

et ainsi rendre :

```text
les bonnes frontières faciles à respecter
et
les mauvaises dépendances difficiles à introduire
```