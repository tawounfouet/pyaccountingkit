# 28_PYACCOUNTINGKIT_TESTING_TOOLKIT_ARCHITECTURE.md

# PyAccountingKit — Testing Toolkit Architecture

> **Projet** : PyAccountingKit  
> **Document** : `28_PYACCOUNTINGKIT_TESTING_TOOLKIT_ARCHITECTURE.md`  
> **Statut** : Spécification d'architecture — Developer Experience, tests et qualification consommateur  
> **Version documentaire** : 1.0  
> **Date** : 22 octobre 2026  
> **Baseline observée** : PyAccountingKit `0.7.0rc1`  
> **Langue** : Français  

---

# 1. Objet du document

Ce document définit l'architecture cible d'un **Testing Toolkit officiel** pour PyAccountingKit.

L'objectif est de fournir aux :

```text
maintainers
contributors
consumer applications
adapter authors
integrators
```

une surface de test cohérente, stable et réutilisable permettant de tester le comportement comptable sans réécrire à chaque projet :

```text
fixtures
builders
fakes
clocks
ID factories
in-memory adapters
assertions métier
Hypothesis strategies
scenario harnesses
contract suites
golden helpers
concurrency helpers
```

La cible est :

```text
pyaccountingkit.testing
```

comme **API de Developer Experience**, distincte du runtime métier.

---

# 2. Pourquoi un toolkit dédié

PyAccountingKit possède déjà une stratégie de tests avancée.

Le dépôt contient notamment :

```text
unit tests
property-based tests
contract tests
integration tests
concurrency tests
golden tests
replay tests
```

Il contient aussi plusieurs primitives déjà utiles :

```text
FrozenClock
InMemoryUnitOfWork
InMemoryUnitOfWorkFactory
InMemoryAuditLogSink
InMemoryIdempotencyStore
InMemoryOutboxPublisher
Hypothesis strategies locales aux tests
```

Cependant, ces éléments sont encore répartis entre :

```text
core
adapters/in_memory
tests/*
```

et ne forment pas encore une **surface publique de testing cohérente**.

---

# 3. Baseline observée

## 3.1 `FrozenClock`

Le code possède déjà :

```text
pyaccountingkit.core.clock.FrozenClock
```

avec :

```text
timezone-aware datetime
deterministic now()
```

Ce composant est déjà correctement placé dans le core, car il sert aussi aux replays et à la déterminisme.

Il ne doit pas être dupliqué dans `pyaccountingkit.testing`.

Le toolkit peut simplement le réexporter.

---

# 4. `InMemoryUnitOfWork`

La baseline possède déjà :

```text
pyaccountingkit.adapters.in_memory.InMemoryUnitOfWork
```

avec :

```text
isolated working copy
optimistic revision checks
audit
idempotency
outbox
rollback
commit
```

C'est un composant important pour :

```text
unit/integration-light tests
consumer tests
examples
golden tests
```

Le toolkit ne doit pas réimplémenter une fausse UoW simplifiée.

Il doit utiliser l'adapter InMemory officiel.

---

# 5. Property-based tests

Le repository utilise déjà :

```text
Hypothesis
```

pour :

```text
Money
balance invariants
subledger properties
settlement properties
financial analysis
```

Le gap actuel n'est donc pas l'outil.

Le gap est :

> **l'absence d'un catalogue réutilisable de strategies PyAccountingKit.**

---

# 6. Contract suites

Le repository possède déjà des contract tests pour :

```text
repositories
reference providers
UnitOfWork
queries
adapters
```

Le toolkit doit rendre certains de ces contrats réutilisables par des auteurs d'adapters externes.

---

# 7. Gap principal

Il n'existe pas encore de package officiel :

```text
pyaccountingkit.testing
```

fournissant une API stable pour :

```text
consumer tests
adapter certification
scenario setup
business assertions
deterministic IDs
domain builders
```

---

# 8. Vision

Le toolkit doit permettre d'écrire :

```python
from pyaccountingkit.testing import (
    AccountingScenario,
    FrozenClock,
    JournalEntryBuilder,
    assert_balanced,
)
```

puis :

```python
scenario = AccountingScenario.minimal()
entry = (
    JournalEntryBuilder()
    .debit("512000", "1000.00", "EUR")
    .credit("101000", "1000.00", "EUR")
    .validated()
    .build()
)

result = scenario.post(entry)

assert_balanced(result.posted_entry)
```

sans reproduire toute l'infrastructure de bootstrap.

---

# 9. Principes fondamentaux

## TKT-001 — Test toolkit != second runtime

`pyaccountingkit.testing` ne doit pas dupliquer les comportements métier.

Il assemble :

```text
canonical domain
canonical application services
official in-memory adapters
test-only helpers
```

---

# 10. TKT-002 — Fakes implement real contracts

Un fake ou in-memory adapter doit implémenter le même port que l'adapter production.

Interdit :

```text
FakeRepository with a custom API unrelated to RepositoryProtocol
```

---

# 11. TKT-003 — Builders create domain-valid objects by default

Un builder doit produire :

```text
valid object by default
```

et nécessiter une action explicite pour créer un cas invalide.

---

# 12. TKT-004 — Invalid fixtures are intentional

Exemple :

```python
JournalEntryBuilder().unbalanced(...)
```

doit être explicite.

---

# 13. TKT-005 — Determinism first

Les helpers utilisent :

```text
FrozenClock
DeterministicIdFactory
explicit Decimal
explicit timezone
```

---

# 14. TKT-006 — No hidden global mutable state

Le toolkit ne doit pas dépendre d'un registry global modifiable entre tests.

Chaque scenario est :

```text
isolated
instance-scoped
resettable
```

---

# 15. TKT-007 — Consumer-oriented API

La surface doit être compréhensible sans connaître tous les internals du framework.

---

# 16. TKT-008 — Production semantics preserved

Le toolkit ne doit pas rendre possible un comportement interdit en production.

Exemple :

```text
post directly into closed period
```

ne doit pas devenir possible parce qu'on utilise InMemory.

---

# 17. TKT-009 — Testing helpers remain optional

Le package runtime core ne dépend jamais de :

```text
Hypothesis
pytest
testcontainers
freezegun
```

---

# 18. TKT-010 — Testing package is downward-only

Direction :

```text
pyaccountingkit.testing
      ↓
core
domain
application
ports
official adapters
```

Jamais :

```text
core/domain
      ↓
pyaccountingkit.testing
```

---

# 19. Package cible

```text
pyaccountingkit/
└── testing/
    ├── __init__.py
    ├── clocks.py
    ├── ids.py
    ├── builders/
    ├── scenarios/
    ├── assertions/
    ├── fakes/
    ├── strategies/
    ├── contracts/
    ├── golden/
    ├── concurrency/
    └── fixtures/
```

---

# 20. `testing.__init__`

Doit exposer uniquement les helpers stables les plus utiles.

Exemple :

```text
FrozenClock
DeterministicIdFactory
AccountingScenario
JournalEntryBuilder
AccountingPeriodBuilder
CompanyAccountBuilder
assert_balanced
assert_posted
```

---

# 21. Clocks

Le toolkit réexporte :

```text
FrozenClock
```

depuis :

```text
pyaccountingkit.core.clock
```

Pas de duplication.

---

# 22. `AdvancingClock`

Helper test-only possible :

```python
clock = AdvancingClock(start=...)
clock.advance(days=1)
```

Utilité :

```text
aging
cut-off
effective dates
period boundaries
```

---

# 23. `SequenceClock`

Helper possible :

```text
first call -> t1
second call -> t2
third call -> t3
```

utile pour tester des ordres temporels précis.

---

# 24. Clock rules

Toutes les clocks de test doivent produire :

```text
timezone-aware timestamps
```

---

# 25. Deterministic IDs

Le dépôt documente déjà :

```text
DeterministicIdFactory
```

mais ne fournit pas encore une implémentation consolidée.

Le toolkit doit en fournir une.

---

# 26. `DeterministicIdFactory`

Exemple :

```python
ids = DeterministicIdFactory(
    prefix="test",
    start=1,
)
```

Résultats :

```text
test-0001
test-0002
test-0003
```

---

# 27. Typed ID factories

Helpers possibles :

```text
EntryIdFactory
PeriodIdFactory
AccountIdFactory
SettlementIdFactory
EventIdFactory
ManifestIdFactory
```

---

# 28. ID stability

Un même scénario golden doit pouvoir générer les mêmes IDs entre exécutions si ceux-ci participent au checksum attendu.

---

# 29. Builders

Builders initiaux recommandés :

```text
MoneyBuilder
CompanyAccountBuilder
CompanyChartBuilder
JournalBuilder
JournalEntryBuilder
AccountingPeriodBuilder
AccountingPolicySetBuilder
ReferenceSnapshotBuilder
ReceivableBuilder
PayableBuilder
SettlementBuilder
PaymentBuilder
ReconciliationBuilder
ClosingRunBuilder
ReportSnapshotBuilder
AnalysisSnapshotBuilder
```

---

# 30. Builder principle

Exemple :

```python
entry = JournalEntryBuilder().build()
```

doit produire une écriture :

```text
balanced
valid IDs
same entity
same currency
valid period reference
```

---

# 31. `JournalEntryBuilder`

API cible possible :

```python
entry = (
    JournalEntryBuilder()
    .with_id("entry-1")
    .for_period("2026-10")
    .in_journal("SALES")
    .debit("411000", "1200.00", "EUR")
    .credit("707000", "1200.00", "EUR")
    .validated()
    .build()
)
```

---

# 32. Explicit invalid variants

Exemples :

```python
JournalEntryBuilder().unbalanced()
JournalEntryBuilder().cross_currency()
JournalEntryBuilder().with_one_line()
```

Ces méthodes rendent le caractère invalide visible dans le test.

---

# 33. `AccountingPeriodBuilder`

Defaults :

```text
OPEN
timezone-safe dates
entity set
fiscal year set
```

Helpers :

```text
.open()
.review()
.closing()
.closed()
```

---

# 34. `CompanyAccountBuilder`

Defaults :

```text
active
valid account code
entity-scoped
```

---

# 35. `ReceivableBuilder`

Defaults :

```text
positive original amount
zero allocations
OPEN status
valid party
```

---

# 36. `SettlementBuilder`

Defaults :

```text
positive amount
same currency
unallocated
valid accounting reference
```

---

# 37. Builder composition

Les builders doivent pouvoir composer :

```text
Invoice
    ↓
Receivable
    ↓
Settlement
```

sans dupliquer les règles métier.

---

# 38. No builder business logic duplication

Exemple :

```text
JournalEntryBuilder
```

ne doit pas recalculer lui-même la validation de partie double si le domaine fournit déjà :

```text
entry.validate()
```

Il assemble puis appelle le comportement canonique.

---

# 39. Scenario harness

Concept principal :

```text
AccountingScenario
```

---

# 40. `AccountingScenario`

Objectif :

> fournir un environnement minimal complet et isolé pour exécuter des use cases PyAccountingKit.

Structure :

```text
AccountingScenario
|
+-- store
+-- uow_factory
+-- clock
+-- id_factory
+-- reference provider
+-- chart resolver
+-- application services
+-- audit access
+-- outbox access
```

---

# 41. `AccountingScenario.minimal()`

Doit pouvoir créer :

```text
entity
fiscal year
open period
journal
chart
currency
InMemory UoW
FrozenClock
```

---

# 42. Usage

```python
scenario = AccountingScenario.minimal(currency="EUR")
```

puis :

```python
result = scenario.post(entry)
```

---

# 43. `AccountingScenario.for_standard(...)`

Future helper :

```python
scenario = AccountingScenario.for_standard(
    standard="fr-pcg",
    edition="2026",
)
```

si le provider correspondant est disponible.

---

# 44. Scenario state inspection

Le scenario doit permettre de lire :

```text
posted entries
periods
audit events
outbox records
trial balance
```

sans exposer excessivement les internals.

---

# 45. No magic mutation

Le scenario ne doit pas fournir :

```python
scenario.force_post(...)
```

contournant les invariants.

---

# 46. Specialized scenarios

Possibles :

```text
LedgerScenario
SubledgerScenario
ClosingScenario
ReconciliationScenario
ReportingScenario
SemanticScenario
```

mais uniquement si la complexité le justifie.

---

# 47. Golden scenario harness

Le document `27` définit :

```text
GoldenScenarioDefinition
```

Le toolkit doit fournir :

```text
GoldenScenarioRunner
```

---

# 48. `GoldenScenarioRunner`

Responsabilités :

```text
load fixture
build scenario
execute steps
collect result
calculate checksums
compare expected
produce evidence
```

---

# 49. Golden result

Structure :

```text
GoldenScenarioResult
|
+-- scenario_id
+-- version
+-- assertions
+-- expected_checksums
+-- actual_checksums
+-- status
```

---

# 50. Concurrency harness

Le document `27` définit les besoins :

```text
barriers
worker coordination
transaction checkpoints
```

Le toolkit doit fournir les primitives communes.

---

# 51. `RaceCoordinator`

Concept :

```text
RaceCoordinator
|
+-- register_worker
+-- barrier
+-- release
+-- collect_results
```

---

# 52. `WorkerBarrier`

Permet :

```text
Worker A reaches point X
Worker B reaches point Y
then release both
```

sans utiliser :

```text
sleep()
```

---

# 53. `TransactionCheckpoint`

Hook test-only permettant de synchroniser des transactions autour de :

```text
after load
before save
before commit
after lock
```

---

# 54. Test-only instrumentation

Ces hooks doivent rester :

```text
testing-only
adapter-owned
not public runtime behavior
```

---

# 55. Fakes

Les fakes initiaux recommandés :

```text
FakeReferenceProvider
FakeExchangeRateProvider
FakeArtifactStore
FakeSemanticExporter
RecordingAuditSink
RecordingOutboxPublisher
DeterministicSequenceProvider
```

---

# 56. `FakeReferenceProvider`

Doit implémenter le vrai :

```text
ReferenceProviderProtocol
```

avec un dataset minimal configurable.

---

# 57. Fake vs Stub

Le toolkit peut documenter :

```text
Fake
    working lightweight implementation
Stub
    predefined response

Spy / Recording
    records calls/events
```

sans multiplier inutilement les classes.

---

# 58. `RecordingAuditSink`

Doit permettre :

```python
assert audit.events[-1].event_type == ...
```

tout en respectant le vrai port.

---

# 59. `RecordingOutboxPublisher`

Permet de tester :

```text
number of records
event types
idempotency keys
correlation ids
```

---

# 60. Existing InMemory outbox

Le toolkit doit réutiliser autant que possible :

```text
InMemoryOutboxPublisher
```

plutôt que créer un duplicate.

---

# 61. Assertions métier

Package :

```text
pyaccountingkit.testing.assertions
```

---

# 62. Initial assertions

```text
assert_balanced
assert_posted
assert_reversed
assert_period_open
assert_period_closed
assert_trial_balance_balanced
assert_subledger_matches_control_account
assert_settlement_within_outstanding
assert_no_duplicate_effect
assert_audit_contains
assert_outbox_contains
assert_snapshot_checksum
```

---

# 63. `assert_balanced`

Exemple :

```python
assert_balanced(entry)
```

Message d'échec :

```text
Expected debit == credit.
Debit: 1,000.00 EUR
Credit: 900.00 EUR
Difference: 100.00 EUR
```

---

# 64. Assertion quality

Les assertions doivent produire des messages utiles au métier.

Éviter :

```text
AssertionError: False is not true
```

---

# 65. `assert_trial_balance_balanced`

Doit afficher :

```text
total debit
total credit
difference
snapshot variant
```

---

# 66. `assert_no_duplicate_effect`

Peut vérifier :

```text
entry count
audit count
outbox count
```

après un retry/idempotency scenario.

---

# 67. Event assertions

Après `25`, ajouter :

```text
assert_event_emitted
assert_same_correlation
assert_causation_chain
```

---

# 68. Manifest assertions

Après `26` :

```text
assert_manifest_replayable
assert_pinned_version
assert_checksum_matches
```

---

# 69. Golden assertions

Après `27` :

```text
assert_golden_match
assert_only_allowed_race_outcome
```

---

# 70. Hypothesis strategies

Package :

```text
pyaccountingkit.testing.strategies
```

Dépendance optionnelle :

```text
hypothesis
```

---

# 71. Strategy modules

```text
money.py
identifiers.py
journal_entries.py
periods.py
settlements.py
references.py
analysis.py
```

---

# 72. `money_strategy`

Exemple :

```python
money_strategy(
    currency=EUR,
    min_minor=-1_000_000,
    max_minor=1_000_000,
)
```

---

# 73. No float strategies

Toutes les strategies monétaires construisent :

```text
Decimal
Money
```

pas :

```text
float
```

---

# 74. `balanced_entry_strategy`

Doit garantir par construction :

```text
sum debit == sum credit
```

---

# 75. `unbalanced_entry_strategy`

Doit produire intentionnellement :

```text
debit != credit
```

---

# 76. `settlement_strategy`

Doit permettre deux modes :

```text
valid allocations
over-allocation candidates
```

---

# 77. Shrinking

Les strategies doivent être conçues pour produire des contre-exemples lisibles après shrink.

Éviter des graphes d'objets inutilement gigantesques.

---

# 78. Strategy public stability

Les strategies publiques doivent être versionnées comme le reste de l'API de testing.

---

# 79. Pytest fixtures

Le toolkit peut fournir un plugin pytest optionnel.

Exemple :

```text
pyaccountingkit.testing.pytest_plugin
```

---

# 80. Fixtures possibles

```text
accounting_scenario
frozen_clock
in_memory_uow
minimal_entity
open_period
standard_chart
```

---

# 81. Plugin opt-in

L'activation doit être explicite.

Exemple :

```python
pytest_plugins = ["pyaccountingkit.testing.pytest_plugin"]
```

---

# 82. No automatic global pytest plugin

Éviter des side effects à l'import package.

---

# 83. Contract suites

Package :

```text
pyaccountingkit.testing.contracts
```

---

# 84. Repository contract suite

Une API de certification peut permettre :

```python
class TestMyRepository(
    JournalEntryRepositoryContractSuite
):
    def make_repository(self):
        ...
```

---

# 85. UoW contract suite

Tests génériques :

```text
commit
rollback
exception rollback
shared transaction
audit atomicity
outbox atomicity
idempotency
revision conflict
```

---

# 86. Reference provider contract suite

Le repository possède déjà un contract test.

Le toolkit doit extraire le pattern réutilisable sans coupler les consommateurs au dossier `tests/`.

---

# 87. Query contract suite

Doit permettre de qualifier :

```text
JournalQuery
GeneralLedgerQuery
TrialBalanceQuery
```

---

# 88. Adapter certification

Un auteur d'adapter tiers doit pouvoir exécuter :

```text
pyaccountingkit adapter contract suite
```

contre son implémentation.

---

# 89. Adapter certification levels

```text
BASIC
TRANSACTIONAL
PRODUCTION
```

---

# 90. BASIC

```text
repository semantics
queries
serialization
```

---

# 91. TRANSACTIONAL

Ajoute :

```text
rollback
idempotency
outbox
revision conflict
```

---

# 92. PRODUCTION

Ajoute :

```text
real concurrency
migration
fault injection
performance smoke
```

---

# 93. Contract suite version

Les contract suites doivent déclarer :

```text
contract_suite_version
```

pour qu'un adapter puisse savoir contre quelle baseline il a été qualifié.

---

# 94. Consumer test kit

Les applications utilisatrices doivent pouvoir tester leur intégration sans connaissance interne.

Exemple :

```python
scenario = AccountingScenario.with_adapter(my_uow_factory)
```

---

# 95. Consumer smoke suite

Le toolkit peut fournir :

```text
ConsumerSmokeSuite
```

avec :

```text
import public API
create minimal entity
post balanced entry
query trial balance
reverse entry
```

---

# 96. Framework-neutral

La smoke suite ne dépend pas de :

```text
Django request
FastAPI TestClient
```

Les consumers peuvent l'encapsuler.

---

# 97. Django testing adapter

Package optionnel possible :

```text
pyaccountingkit.testing.django
```

avec :

```text
database fixtures
transaction helpers
factory integration
```

mais seulement si un besoin réel émerge.

---

# 98. SQLAlchemy testing adapter

Même principe.

---

# 99. No framework-specific core testing API

La surface principale reste framework-neutral.

---

# 100. Fixture packs

Package ou resources test-only :

```text
testing/fixtures/
```

---

# 101. Initial fixture packs

```text
minimal_ledger
o2c
p2p
settlements
closing
reconciliation
analysis
```

---

# 102. Regulatory fixtures

Les gros datasets réglementaires ne doivent pas nécessairement être embarqués dans le core wheel.

Le toolkit peut utiliser :

```text
small normalized fixtures
```

et laisser les datasets complets aux qualification suites.

---

# 103. CFA FRA fixtures

Restent dans :

```text
tests/golden/cfa_fra
```

ou package test-data dédié.

Ne pas transformer l'oracle legacy en dépendance testing générique obligatoire.

---

# 104. `ScenarioFixture`

Concept :

```text
ScenarioFixture
|
+-- fixture_id
+-- version
+-- input_checksum
+-- data
```

---

# 105. Fixture immutability

Une fixture golden versionnée est immutable.

---

# 106. Fixture factories

Pour les unit tests, on peut préférer des builders à des gros fichiers JSON.

---

# 107. Rule of thumb

```text
Builder
    for local test setup

Structured fixture
    for reusable golden / consumer scenario
```

---

# 108. Test object mother

Le pattern Object Mother peut être utilisé avec prudence.

Exemple :

```text
AccountingExamples.simple_sale()
```

mais ne doit pas devenir un catalogue opaque de 200 objets magiques.

---

# 109. Named examples

Helpers lisibles :

```text
simple_cash_sale()
partial_customer_payment()
balanced_opening_entry()
```

peuvent être utiles pour la documentation.

---

# 110. Documentation examples

Les snippets README doivent pouvoir utiliser le testing toolkit.

Cela réduit :

```text
boilerplate
fragile examples
```

---

# 111. Doctest?

Les doctests ne sont pas recommandés comme mécanisme principal.

Les exemples publics doivent être testés via pytest.

---

# 112. Testing toolkit extras

Proposition packaging :

```toml
[project.optional-dependencies]
testing = [
    "hypothesis>=...",
]
```

Éventuellement :

```text
testing-postgres
```

pour les outils lourds.

---

# 113. Pytest dependency

Le package `pyaccountingkit.testing` runtime n'a pas besoin de dépendre entièrement de pytest.

Séparer :

```text
generic test helpers
```

de :

```text
pytest integration
```

---

# 114. Testcontainers

`testcontainers` doit rester optionnel.

Il peut supporter les suites :

```text
PostgreSQL production qualification
```

---

# 115. Golden helpers

Package :

```text
testing.golden
```

---

# 116. Initial helpers

```text
load_golden_fixture
canonicalize_result
calculate_semantic_checksum
compare_golden
build_golden_evidence
```

---

# 117. Golden update policy

Le toolkit peut fournir :

```text
diff generation
```

mais pas :

```text
silent accept
```

---

# 118. Human-review diff

Un diff golden devrait afficher :

```text
changed financial values
changed statuses
changed event types
changed checksums
```

---

# 119. Reproducibility helpers

Après `26`, le toolkit peut fournir :

```text
ReplayHarness
ManifestBuilder
assert_replay_match
```

---

# 120. `ReplayHarness`

Responsabilités :

```text
resolve pinned inputs
execute computation
compare checksums
produce ReplayEvidence
```

---

# 121. Event testing helpers

Après `25` :

```text
EventRecorder
EventSequenceAssertion
CorrelationAssertion
```

---

# 122. `EventRecorder`

Peut consommer :

```text
OutboxRecord
DomainEvent
AuditEvent
```

mais doit préserver leur distinction.

---

# 123. Audit helpers

```text
assert_audit_actor
assert_audit_object
assert_audit_correlation
```

---

# 124. Fault injection toolkit

Package :

```text
testing.faults
```

possible dans une phase ultérieure.

---

# 125. Fault points

```text
AFTER_SAVE
AFTER_AUDIT
BEFORE_OUTBOX
BEFORE_COMMIT
AFTER_COMMIT_BEFORE_PUBLISH
```

---

# 126. `FaultInjector`

Doit être test-only.

Il ne devient jamais un service runtime.

---

# 127. Failure factory

Exemple :

```python
FaultInjector.raise_at(
    FaultPoint.BEFORE_COMMIT,
    RuntimeError("synthetic failure"),
)
```

---

# 128. Concurrency helpers and DB

Les helpers génériques peuvent coordonner les workers.

L'adapter PostgreSQL fournit la vraie sémantique de lock.

---

# 129. No fake locking claims

InMemory ne doit pas prétendre qualifier :

```text
PostgreSQL row locking
deadlocks
isolation levels
```

---

# 130. Capability-aware tests

Le toolkit doit permettre :

```python
if adapter.capabilities.supports_pessimistic_locking:
    ...
```

sans considérer l'absence comme un échec automatique si l'adapter n'annonce pas cette capability.

---

# 131. Adapter capability fixture

Structure :

```text
AdapterCapabilities
|
+-- transactional
+-- optimistic_revision
+-- pessimistic_locking
+-- transactional_outbox
+-- advisory_locks
```

---

# 132. Snapshot assertions

Helpers :

```text
assert_snapshot_immutable
assert_snapshot_current
assert_snapshot_stale
assert_snapshot_checksum
```

---

# 133. Semantic layer testing

Pour `31` :

```text
SemanticDatasetBuilder
MetricDefinitionBuilder
assert_semantic_value
assert_cross_adapter_semantic_equivalence
```

dans une phase ultérieure.

---

# 134. Testing and architecture fitness

Règles :

```text
AFF-TESTING-001
core/domain MUST NOT import pyaccountingkit.testing

AFF-TESTING-002
testing toolkit MAY import public domain/application contracts

AFF-TESTING-003
testing toolkit MUST NOT become required core dependency

AFF-TESTING-004
Hypothesis/pytest remain optional dependencies
```

---

# 135. Public vs internal testing API

Surface stable :

```text
pyaccountingkit.testing
```

Internals :

```text
pyaccountingkit.testing._internal
```

si nécessaire.

---

# 136. No accidental stabilization

Tous les helpers internes ne doivent pas être réexportés.

---

# 137. SemVer

La public Testing API suit :
```text
package SemVer
```

mais peut avoir une politique de stabilité légèrement moins forte avant 1.0.

---

# 138. Deprecation

Un helper public supprimé doit suivre :

```text
deprecation warning
migration note
removal version
```

---

# 139. Type hints

Tous les helpers publics doivent être typés.

---

# 140. `Protocol` use

Les contract suites utilisent les vrais Protocols du framework.

---

# 141. No Any-heavy public toolkit

Éviter une API de test entièrement basée sur :

```text
dict[str, Any]
```

pour les objets métier critiques.

---

# 142. Assertions return

Les assertions suivent la convention :

```text
raise AssertionError on failure
return None on success
```

---

# 143. Result helpers

Les runners complexes peuvent retourner des objets :

```text
GoldenScenarioResult
ConcurrencyScenarioResult
ReplayEvidence
```

---

# 144. Error diagnostics

Les failures doivent afficher :

```text
business object IDs
expected
actual
difference
scenario context
```

---

# 145. Sensitive data

Les diagnostics de test ne doivent pas encourager l'impression automatique de secrets ou de PII.

---

# 146. Scenario isolation

Chaque `AccountingScenario` crée son propre :

```text
store
clock
id space
```

par défaut.

---

# 147. Explicit shared store

Les tests de concurrence peuvent demander :

```text
shared store
```

explicitement.

---

# 148. Reset

Une API :

```python
scenario.reset()
```

peut être fournie, mais il est préférable de créer un nouveau scenario pour éviter les fuites d'état.

---

# 149. Parallel pytest

Le toolkit doit supporter :

```text
pytest-xdist
```

si les tests utilisent des stores isolés et identifiants déterministes scope-test.

---

# 150. Deterministic ID collision

Le prefix ID doit pouvoir intégrer :

```text
scenario/test namespace
```

pour éviter des collisions lors de tests parallèles.

---

# 151. Consumer extension

Un consumer peut définir ses propres builders en composant ceux du toolkit.

---

# 152. No subclass requirement

La composition doit être préférée à une hiérarchie profonde de builders.

---

# 153. Example custom consumer builder

```python
class RentalInvoiceBuilder:
    def build(self):
        return (
            InvoiceBuilder()
            .for_party(...)
            .with_lines(...)
            .build()
        )
```

---

# 154. Contract suite hooks

Les suites doivent permettre au consumer de fournir :

```text
make_adapter()
cleanup()
capabilities()
```

sans modifier le test contractuel lui-même.

---

# 155. Database lifecycle

Pour PostgreSQL :

```text
one isolated schema/database per test session
transaction cleanup
migration bootstrap
```

selon l'adapter.

---

# 156. Migration testing helpers

Future helpers :

```text
PreviousVersionInstaller
MigrationScenario
SchemaStateAssertion
```

peuvent appartenir aux scripts de qualification plutôt qu'au toolkit core.

---

# 157. Scope boundary

Le toolkit ne doit pas devenir :

```text
CI orchestration framework
container platform
migration manager
performance benchmark framework
```

Il fournit les briques réutilisables.

---

# 158. Relation avec `11_TESTING_AND_QUALITY_STRATEGY`

`11` répond :

> Quels types de tests et gates sont requis ?

`28` répond :

> Quels outils PyAccountingKit fournissons-nous pour écrire et exécuter ces tests facilement ?

---

# 159. Relation avec `27_GOLDEN_ACCOUNTING...`

`27` définit :

```text
what scenarios must exist
```

`28` fournit :

```text
how to implement them consistently
```

---

# 160. Relation avec `24_ARCHITECTURE_FITNESS_FUNCTIONS`

`24` protège :

```text
dependency rules
```

`28` fournit les contract suites et helpers permettant de qualifier certains comportements d'architecture.

---

# 161. Relation avec `25_DOMAIN_EVENTS...`

`28` fournit :

```text
event recorders
causality assertions
```

sans changer le modèle événementiel.

---

# 162. Relation avec `26_REPRODUCIBILITY...`

`28` fournit :

```text
manifest builders
replay harness
checksum assertions
```

---

# 163. Relation avec adapters

Le toolkit doit favoriser :

```text
same test
different adapter
```

---

# 164. Example

```python
@pytest.mark.parametrize(
    "factory",
    [
        in_memory_factory,
        django_postgres_factory,
        sqlalchemy_postgres_factory,
    ],
)
def test_posting_contract(factory):
    scenario = AccountingScenario.with_uow_factory(factory)
    ...
```

---

# 165. Testing Kit public surface v1

Recommandation initiale :

```text
FrozenClock
AdvancingClock
DeterministicIdFactory
AccountingScenario

JournalEntryBuilder
AccountingPeriodBuilder
CompanyAccountBuilder
ReceivableBuilder
SettlementBuilder

assert_balanced
assert_posted
assert_reversed
assert_trial_balance_balanced
assert_no_duplicate_effect

money_strategy
balanced_entry_strategy

RepositoryContractSuite
UnitOfWorkContractSuite
ReferenceProviderContractSuite
```

---

# 166. Surface à différer

Ne pas rendre public immédiatement :

```text
fault injection internals
DB lock instrumentation
semantic builders
migration installers
complex golden update commands
```

---

# 167. MVP architecture

## TKT-00 — Package bootstrap

```text
pyaccountingkit.testing
```

---

# 168. TKT-01 — Deterministic primitives

```text
FrozenClock re-export
AdvancingClock
DeterministicIdFactory
```

---

# 169. TKT-02 — Core builders

```text
JournalEntryBuilder
AccountingPeriodBuilder
CompanyAccountBuilder
```

---

# 170. TKT-03 — AccountingScenario

```text
minimal InMemory scenario
```

---

# 171. TKT-04 — Assertions

```text
balanced
posted
reversed
trial balance
audit
outbox
```

---

# 172. TKT-05 — Hypothesis strategies

```text
Money
balanced entries
periods
settlements
```

---

# 173. TKT-06 — Contract suites

```text
repository
UoW
reference provider
```

---

# 174. TKT-07 — Golden helpers

```text
fixture loader
checksum compare
evidence builder
```

---

# 175. TKT-08 — Concurrency helpers

```text
RaceCoordinator
WorkerBarrier
```

---

# 176. TKT-09 — Replay/event helpers

```text
ReplayHarness
EventRecorder
causality assertions
```

---

# 177. Priorités

| Lot | Priorité |
|---|---:|
| TKT-00 | P0 |
| TKT-01 | P0 |
| TKT-02 | P0 |
| TKT-03 | P0 |
| TKT-04 | P0 |
| TKT-05 | P1 |
| TKT-06 | P0 |
| TKT-07 | P1 |
| TKT-08 | P1 |
| TKT-09 | P2 |

---

# 178. Definition of Done — MVP

```text
[ ] package pyaccountingkit.testing existe
[ ] FrozenClock réexporté sans duplication
[ ] DeterministicIdFactory disponible
[ ] JournalEntryBuilder disponible
[ ] AccountingPeriodBuilder disponible
[ ] CompanyAccountBuilder disponible
[ ] AccountingScenario.minimal disponible
[ ] assertions comptables de base disponibles
[ ] aucune dépendance pytest obligatoire du core testing runtime
[ ] type hints complets
[ ] documentation d'usage disponible
```

---

# 179. Definition of Done — Property Testing

```text
[ ] money_strategy
[ ] balanced_entry_strategy
[ ] unbalanced_entry_strategy
[ ] settlement_strategy
[ ] Hypothesis reste optional dependency
[ ] strategies shrink-friendly
```

---

# 180. Definition of Done — Adapter Authors

```text
[ ] RepositoryContractSuite
[ ] UnitOfWorkContractSuite
[ ] ReferenceProviderContractSuite
[ ] capabilities contract défini
[ ] contract suite version définie
[ ] exemple adapter tiers documenté
```

---

# 181. Definition of Done — Golden & Replay

```text
[ ] GoldenScenarioRunner
[ ] golden fixture loader
[ ] semantic checksum comparison
[ ] human-readable diff
[ ] ReplayHarness
[ ] assert_replay_match
```

---

# 182. Definition of Done — Concurrency

```text
[ ] RaceCoordinator
[ ] WorkerBarrier
[ ] allowed/forbidden outcome assertion
[ ] PostgreSQL usage documented
[ ] no sleep-based synchronization examples
```

---

# 183. ADR proposées

| ADR | Décision |
|---|---|
| ADR-TKT-001 | PyAccountingKit fournit une API `pyaccountingkit.testing` officielle |
| ADR-TKT-002 | Le testing toolkit ne devient jamais une dépendance du domaine |
| ADR-TKT-003 | `FrozenClock` reste défini dans `core` et est réexporté |
| ADR-TKT-004 | Les builders produisent des objets valides par défaut |
| ADR-TKT-005 | Les fixtures invalides sont demandées explicitement |
| ADR-TKT-006 | Les builders réutilisent les comportements métier canoniques |
| ADR-TKT-007 | Les fakes implémentent les vrais ports |
| ADR-TKT-008 | L'InMemory adapter officiel est utilisé plutôt qu'une seconde fake persistence |
| ADR-TKT-009 | `DeterministicIdFactory` devient une primitive de testing officielle |
| ADR-TKT-010 | Les helpers de test n'utilisent jamais float pour Money |
| ADR-TKT-011 | Le toolkit n'utilise aucun état global mutable implicite |
| ADR-TKT-012 | `AccountingScenario` est instance-scoped |
| ADR-TKT-013 | Les assertions produisent des diagnostics métier |
| ADR-TKT-014 | Hypothesis reste une dépendance optionnelle |
| ADR-TKT-015 | Les strategies publiques sont versionnées |
| ADR-TKT-016 | Les contract suites peuvent être réutilisées par des adapters tiers |
| ADR-TKT-017 | Les contract suites déclarent une version |
| ADR-TKT-018 | Les adapters Production passent des suites plus strictes que BASIC |
| ADR-TKT-019 | Les golden helpers ne mettent jamais à jour automatiquement les attentes sans revue |
| ADR-TKT-020 | Les concurrency helpers utilisent des barrières explicites |
| ADR-TKT-021 | Les vraies garanties PostgreSQL ne sont pas simulées par InMemory |
| ADR-TKT-022 | Les helpers événementiels préservent la distinction Domain/Audit/Outbox |
| ADR-TKT-023 | Les replay helpers utilisent les manifests pinés |
| ADR-TKT-024 | Les framework-specific testing integrations restent optionnelles |
| ADR-TKT-025 | Le pytest plugin est opt-in |
| ADR-TKT-026 | Le package testing principal reste framework-neutral |
| ADR-TKT-027 | Les helpers publics sont entièrement typés |
| ADR-TKT-028 | Les internals testing ne sont pas réexportés accidentellement |
| ADR-TKT-029 | Le toolkit privilégie la composition à l'héritage |
| ADR-TKT-030 | Les exemples publics du toolkit sont testés |
| ADR-TKT-031 | Le testing toolkit supporte les tests consommateurs |
| ADR-TKT-032 | Le testing toolkit supporte la qualification cross-adapter |
| ADR-TKT-033 | Les fixtures golden sont versionnées et immuables |
| ADR-TKT-034 | Le toolkit ne devient pas un orchestrateur CI généraliste |
| ADR-TKT-035 | Les primitives de test doivent refléter la sémantique Production |
| ADR-TKT-036 | Toute divergence test/production connue doit être documentée |

---

# 184. Architecture Fitness Functions associées

```text
AFF-TESTING-001
core/domain MUST NOT import pyaccountingkit.testing

AFF-TESTING-002
pyaccountingkit.testing MUST NOT be a mandatory core dependency

AFF-TESTING-003
testing fakes MUST implement canonical ports

AFF-TESTING-004
Hypothesis/pytest/testcontainers remain optional

AFF-TESTING-005
testing package MUST NOT import concrete BI/web frameworks in its core surface
```

---

# 185. Error taxonomy

Erreurs spécifiques possibles :

```text
TestingToolkitError
|
+-- InvalidBuilderConfigurationError
+-- ScenarioSetupError
+-- GoldenMismatchError
+-- UnsupportedAdapterCapabilityError
+-- ReplayAssertionError
+-- RaceOutcomeAssertionError
```

---

# 186. Builder validation

Un builder mal configuré doit produire une erreur claire.

Exemple :

```text
JournalEntryBuilder requires at least one debit and one credit line.
```

---

# 187. Scenario failure

`ScenarioSetupError` doit distinguer :

```text
fixture problem
framework behavior failure
adapter failure
```

---

# 188. Golden mismatch diagnostics

Doit afficher :

```text
expected checksum
actual checksum
semantic diff
scenario id/version
adapter
```

---

# 189. Race diagnostics

Doit afficher :

```text
worker A outcome
worker B outcome
final state
violated invariant
event counts
```

---

# 190. Documentation cible

Ajouter :

```text
docs/testing/
├── QUICKSTART.md
├── BUILDERS.md
├── SCENARIOS.md
├── PROPERTY_TESTING.md
├── ADAPTER_CONTRACTS.md
├── GOLDEN_TESTING.md
└── CONCURRENCY_TESTING.md
```

---

# 191. Quickstart consumer

Exemple cible :

```python
from pyaccountingkit.testing import AccountingScenario

scenario = AccountingScenario.minimal()

scenario.post_balanced(
    debit_account="512000",
    credit_account="101000",
    amount="1000.00",
)

tb = scenario.trial_balance()
assert tb.total_debit == tb.total_credit
```

---

# 192. Quickstart adapter author

Exemple conceptuel :

```python
class TestMyRepository(JournalEntryRepositoryContractSuite):
    def make_repository(self):
        return MyRepository(...)
```

---

# 193. Quickstart property test

```python
@given(balanced_entry_strategy())
def test_posted_entries_remain_balanced(entry):
    ...
```

---

# 194. Packaging proposal

Possible :

```toml
[project.optional-dependencies]
testing = [
    "hypothesis>=...",
]
```

Les helpers ne nécessitant pas Hypothesis restent importables sans cet extra.

---

# 195. Lazy optional imports

`pyaccountingkit.testing.strategies` peut produire une erreur claire si Hypothesis n'est pas installé.

---

# 196. No optional import crash at root

```python
import pyaccountingkit.testing
```

doit fonctionner sans Hypothesis si l'utilisateur n'importe pas `strategies`.

---

# 197. CI qualification du toolkit

Le toolkit doit avoir ses propres tests :

```text
builders
scenario isolation
deterministic IDs
assertion diagnostics
contract suite self-tests
optional dependency isolation
```

---

# 198. Meta-tests

Les contract suites elles-mêmes doivent être testées contre :

```text
known good adapter
known broken adapter
```

pour vérifier qu'elles détectent réellement les violations.

---

# 199. Example known broken adapter

Un test interne peut utiliser un adapter volontairement défectueux :

```text
rollback does not rollback
```

et vérifier que :

```text
UnitOfWorkContractSuite fails
```

---

# 200. Mutation testing du toolkit

Les assertions et contract suites critiques peuvent bénéficier de mutation tests ciblés.

---

# 201. Performance

Le toolkit ne doit pas rendre les unit tests inutilement lents.

Cibles :

```text
AccountingScenario.minimal()
fast enough for hundreds of tests
```

---

# 202. Fixture cache

Un cache immutable peut être envisagé pour :

```text
large reference fixtures
```

mais jamais comme état mutable partagé.

---

# 203. Thread safety

Les helpers utilisés dans les concurrency tests doivent être thread-safe ou clairement documentés comme thread-confined.

---

# 204. Async compatibility

Une future version peut introduire :

```text
AsyncAccountingScenario
AsyncContractSuite
```

uniquement lorsqu'un vrai adapter async apparaît.

Ne pas anticiper inutilement.

---

# 205. Scope non couvert

Le toolkit ne cherche pas à remplacer :

```text
pytest
Hypothesis
Testcontainers
Factory Boy
freezegun
```

Il fournit une couche métier PyAccountingKit au-dessus de ces outils lorsqu'utile.

---

# 206. Positionnement global

```text
                    APPLICATION / CONSUMER TESTS
                               │
                               ▼
                    pyaccountingkit.testing
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
      Builders             Scenarios            Assertions
          │                    │                    │
          └────────────────────┼────────────────────┘
                               ▼
               Canonical Public/Application API
                               │
                               ▼
                             Domain
                               │
                               ▼
                           Real Ports
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
           InMemory        Django/PG       SQLAlchemy/PG
```

---

# 207. Testing stack cible

```text
pytest
    +
Hypothesis
    +
PyAccountingKit Testing Toolkit
    +
Official Adapter Contract Suites
    +
Golden / Replay / Concurrency Harnesses
```

---

# 208. Roadmap synthétique

```text
TKT-00
Testing package
    ↓
TKT-01
Deterministic primitives
    ↓
TKT-02
Builders
    ↓
TKT-03
AccountingScenario
    ↓
TKT-04
Business assertions
    ↓
TKT-05
Hypothesis strategies
    ↓
TKT-06
Adapter contract suites
    ↓
TKT-07
Golden helpers
    ↓
TKT-08
Concurrency harness
    ↓
TKT-09
Replay + event helpers
```

---

# 209. Critères de succès

Le toolkit est réussi si un consumer peut écrire un test de posting réaliste avec :

```text
moins de boilerplate
sans dépendre de Django
sans réimplémenter le domaine
sans mocker chaque repository
```

et si un adapter author peut qualifier son implémentation avec :

```text
the same official contract suite
```

que les adapters du repository principal.

---

# 210. Principe final
Le toolkit doit transformer :

```text
"tester PyAccountingKit nécessite connaître ses internals"
```

en :

```text
"tester une intégration PyAccountingKit utilise une API métier officielle"
```

---

# 211. Conclusion

PyAccountingKit possède déjà les fondations nécessaires :

```text
FrozenClock
InMemory UnitOfWork
contract tests
Hypothesis
golden tests
concurrency tests
```

Le besoin n'est donc pas d'inventer de nouveaux mocks.

Il consiste à organiser ces capacités autour d'une **surface de testing stable et réutilisable**.

La cible est :

```text
Canonical Domain
      ↓
Official Test Builders
      ↓
Official Scenarios
      ↓
Official Assertions
      ↓
Official Contract Suites
      ↓
Golden / Concurrency / Replay
```

Le principe de conception est :

> **Le Testing Toolkit doit rendre le chemin correct plus simple à tester, sans introduire un comportement de test différent du comportement réel du framework.**