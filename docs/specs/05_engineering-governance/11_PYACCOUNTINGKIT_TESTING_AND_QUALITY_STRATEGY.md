# 11 - PyAccountingKit - Stratégie de tests et de qualité

> **Projet** : PyAccountingKit  
> **Document** : `11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md`  
> **Documents parents** : `00` à `10` de la spécification PyAccountingKit  
> **Statut** : P0.12 - Stratégie de tests, qualité et qualification de release  
> **Langue** : Français  
> **Objet** : Définir la stratégie complète de validation de PyAccountingKit : tests unitaires, property-based tests, contract tests, intégration, concurrence, golden tests, replay, migrations, compatibilité, qualité statique, qualification des adapters et release gates.

---

# 1. Résumé exécutif

PyAccountingKit est un framework comptable. Sa stratégie de tests doit donc protéger en priorité :

```text
justesse comptable
immutabilité
traçabilité
reproductibilité
cohérence multi-référentiels
sûreté transactionnelle
portabilité des adapters
non-régression des invariants
```

La chaîne de qualification cible est :

```text
UNIT TESTS
    ↓
PROPERTY-BASED TESTS
    ↓
CONTRACT TESTS
    ↓
INTEGRATION TESTS
    ↓
CONCURRENCY / TRANSACTION TESTS
    ↓
GOLDEN / REPLAY TESTS
    ↓
MIGRATION / COMPATIBILITY TESTS
    ↓
RELEASE QUALIFICATION GATES
```

La règle centrale est :

```text
un test qui passe ne prouve pas seulement
que le code fonctionne ;

il doit contribuer à prouver que
le comportement comptable attendu reste vrai.
```

---

# 2. Objectifs

La stratégie doit permettre de :

1. protéger tous les invariants P0 ;
2. tester les policies de manière déterministe ;
3. tester tous les adapters via une même contract suite ;
4. tester les transactions réelles PostgreSQL ;
5. qualifier optimistic et pessimistic locking ;
6. tester double posting, double reversal et posting vs close ;
7. tester l'idempotence et les séquences ;
8. tester journal, grand livre et balances ;
9. tester cut-off, ajustements, clôture, réouverture et à-nouveaux ;
10. tester l'audit, la provenance et le lineage ;
11. tester les snapshots et checksums ;
12. tester les migrations ;
13. tester la compatibilité des releases ;
14. qualifier les référentiels réglementaires ;
15. empêcher toute régression silencieuse de semantics comptables.

---

# 3. Principes directeurs

## Q-001 - Tester le comportement, pas les détails privés

Préférer :

```text
given balanced entry
when validated
then status = VALIDATED
```

à des tests couplés à des appels privés internes.

## Q-002 - Les invariants critiques ont plusieurs couches de preuve

Les règles comme :

```text
ENTRY_BALANCED
POSTED_IMMUTABLE
REVERSAL_PRESERVES_ORIGINAL
SAME_ACCOUNTING_ENTITY
PERIOD_OPEN_FOR_POSTING
```

doivent être couvertes par plusieurs types de tests.

## Q-003 - Les tests réglementaires pinent leur contexte

Tout test réglementaire doit préciser :

```text
standard_id
edition
dataset_version
policy_version
```

## Q-004 - Même sémantique sous tous les adapters

Les mêmes scénarios doivent produire les mêmes résultats métier sous :

```text
InMemory
Django/PostgreSQL
SQLAlchemy/PostgreSQL
```

## Q-005 - Une DB réelle est obligatoire pour qualifier la concurrence

Les mocks et SQLite ne suffisent pas pour prouver :

```text
row locking
transaction isolation
deadlocks
posting vs close race
```

## Q-006 - CFA FRA reste un oracle comportemental

CFA FRA est utilisé pour des golden scenarios de :

```text
posting
reversal
ledger
trial balance
FEC
closing
audit
```

Il ne devient jamais une dépendance runtime.

---

# 4. Taxonomie des tests

```text
UNIT
PROPERTY
CONTRACT
INTEGRATION
CONCURRENCY
TRANSACTION
GOLDEN
REPLAY
MIGRATION
COMPATIBILITY
PERFORMANCE
SECURITY_ADJACENT
RELEASE_GATE
```

---

# 5. Pyramide de tests

```text
                    /\
                   /  \
                  / E2E \
                 /------\
                /Integration\
               /------------\
              / Contract Tests\
             /----------------\
            / Property-Based   \
           /--------------------\
          /      Unit Tests      \
         /________________________\
```

Répartition indicative :

```text
Unit             40-50 %
Property         10-15 %
Contract         15-20 %
Integration      10-15 %
Concurrency       5-10 %
Golden/Replay     5-10 %
```

---

# 6. Unit tests

Les unit tests ciblent :

```text
Value Objects
Entities
Aggregates
Domain Services
Policies
pure calculations
```

## 6.1 Money

```text
test_money_rejects_float
test_money_uses_decimal
test_currency_mismatch_rejected
test_rounding_policy_explicit
```

## 6.2 JournalEntry

```text
test_draft_entry_can_add_line
test_validated_entry_requires_two_lines
test_entry_requires_debit_equals_credit
test_line_cannot_have_debit_and_credit
test_posted_entry_is_immutable
```

## 6.3 Reversal

```text
test_reversal_swaps_debit_credit
test_reversal_keeps_original
test_reversal_has_new_identity
test_double_reversal_rejected
```

## 6.4 Company Chart

```text
test_account_code_is_string
test_fixed_length_policy
test_variable_length_policy
test_segmented_policy
test_alphanumeric_policy
test_hierarchy_cycle_rejected
```

## 6.5 Policy Resolution

```text
test_entity_specific_policy_wins
test_ambiguous_policy_fails_closed
test_missing_required_policy_fails_closed
test_effective_date_respected
```

## 6.6 Reference Data

```text
test_reference_id_preserved
test_parent_child_preserved
test_effective_plan_consumed
test_code_equality_not_semantic_equivalence
test_non_executable_hint_rejected
```

## 6.7 Closing

```text
test_open_to_review
test_review_to_closing
test_closing_to_closed
test_direct_open_to_closed_rejected
test_reopen_requires_explicit_command
```

## 6.8 Controls

```text
test_severity_independent_of_blocking
test_indeterminate_supported
test_control_result_immutable
test_gate_blocks_on_blocking_fail
```

---

# 7. Property-based tests

Outil recommandé :

```text
Hypothesis
```

## 7.1 Partie double

Pour toute écriture validée :

```text
sum(debit) == sum(credit)
```

## 7.2 Reversal

Pour toute reversal intégrale :

```text
net(original + reversal) == 0
```

## 7.3 Immutabilité

Pour toute écriture `POSTED` :

```text
all accounting mutations fail
```

## 7.4 AccountCodePolicy

Pour tout code généré :

```text
policy.validate(generated_code).valid == true
```

## 7.5 Hierarchy

Pour tout chart valide :

```text
no cycle exists
```

## 7.6 Trial Balance

Pour toute collection d'écritures postées équilibrées :

```text
trial_balance.total_debit
==
trial_balance.total_credit
```

## 7.7 Projection rebuild

```text
rebuild(canonical_lines)
==
projection
```

## 7.8 Policy déterministe

```text
same inputs
+ same policy version
+ same reference snapshot
= same output
```

---

# 8. Contract tests

Les contract tests garantissent qu'une implémentation respecte un port.

## 8.1 Repository Contract

```text
add/get
not-found semantics
revision semantics
unique constraints
append-only semantics
```

## 8.2 UnitOfWork Contract

```text
commit persists
rollback restores
exception rolls back
repositories share same transaction
audit rolls back with critical mutation
```

## 8.3 Query Contract

Doit produire la même sémantique pour :

```text
AccountingJournalQuery
GeneralLedgerQuery
TrialBalanceQuery
AuditQuery
```

## 8.4 Reference Provider Contract

```text
get_standard
get_structure
get_effective_plan
get_reporting_model
get_relations
get_crosswalk
get_concepts
create_snapshot
```

## 8.5 Matrice adapter

| Contract | InMemory | Django/PostgreSQL | SQLAlchemy/PostgreSQL |
|---|---:|---:|---:|
| Repository | oui | oui | oui |
| UnitOfWork | oui | oui | oui |
| Idempotency | oui | oui | oui |
| Outbox | oui | oui | oui |
| Query | oui | oui | oui |
| Audit | oui | oui | oui |
| Concurrency | partiel | complet | complet |

---

# 9. Integration tests

Les integration tests valident :

```text
Application Service
+
Adapter
+
Database / External Provider
```

Exemples :

```text
PostEntry -> UoW -> PostgreSQL -> Audit -> Outbox

ReverseEntry -> original + reversal + audit

ClosePeriod -> controls + closing entries + post-closing + CLOSED

ReferenceProvider -> real dataset -> normalized models -> snapshot
```

---

# 10. Concurrency tests

Ces tests sont obligatoires pour les mutations critiques.

## 10.1 Double Posting

```text
Worker A
Worker B
same VALIDATED entry
```

Attendu :

```text
one POSTED
one conflict
```

## 10.2 Double Reversal

Attendu :

```text
one reversal only
```

## 10.3 Posting vs Close

Résultats autorisés :

```text
posting commits before close
```

ou :

```text
close wins and posting fails
```

Interdit :

```text
posting committed after period closed
```

## 10.4 Double Close

```text
one close revision only
```

## 10.5 Idempotency Race

```text
one side effect only
```

## 10.6 Account Code Race

```text
one account created
one duplicate/collision failure
```

## 10.7 Entry Number Race

```text
entry numbers unique according to scope
```

---

# 11. Tests transactionnels et fault injection

Injecter des erreurs :

```text
after aggregate save
after audit append
before outbox append
before commit
```

Attendu :

```text
no partial state
```

Exemple posting :

```text
entry transition
+
audit
+
outbox
```

Si une étape critique échoue avant commit :

```text
rollback all
```

---

# 12. Golden tests

Les golden tests utilisent des entrées et outputs de référence versionnés.

## 12.1 Golden CFA FRA

Scénarios :

```text
balanced entry
unbalanced entry
posting
reversal
ledger running balance
trial balance variants
closing
FEC validation
```

## 12.2 Golden Ledger

Input :

```text
opening
normal
adjusting
reversal
closing
```

Output attendu :

```text
stable ledger rows
stable balances
stable drill-down
```

## 12.3 Golden Trial Balance

```text
BEFORE_ADJUSTMENTS
ADJUSTED
POST_CLOSING
```

## 12.4 Golden Reference Data

Fixtures :

```text
fr-pcg:2026
fr-nonprofit:2026
ohada-syscohada:2017
ohada-ebnl:2023
```

## 12.5 Golden safety

```text
same code != semantic equivalence
human-review candidate != executable mapping
family relation != inheritance
```

---

# 13. Golden fixture governance

Chaque fixture possède :

```text
fixture_id
fixture_version
source
input_checksum
expected_output_checksum
```

Un changement de golden output doit produire :

```text
before
after
reason
manual review
```

Interdit :

```text
auto-update all snapshots
```

sans revue.

---

# 14. Replay tests

Deux modes :

```text
EXACT
CURRENT_ENGINE_COMPARISON
```

## EXACT

Fige :

```text
runtime version
policy version
reference snapshot
source snapshot
external observations
```

Attendu :

```text
same output checksum
```

## CURRENT_ENGINE_COMPARISON

Rejoue les inputs historiques avec le moteur courant et produit :

```text
ReplayComparison
```

pour :

```text
non-régression
migration
release qualification
```

---

# 15. Migration tests

Deux catégories :

```text
schema migration
business/data migration
```

## 15.1 Schema Migration

```text
install previous schema
load fixtures
upgrade
run controls
```

## 15.2 Data Migration

```text
old representation
-> migration
-> same accounting semantics
```

## 15.3 Historical Preservation

Vérifier :

```text
snapshot IDs unchanged
audit meaning unchanged
posted entries unchanged
reference bindings preserved
```

---

# 16. Compatibility tests

Tester :

```text
public API
serialized artifacts
adapter contracts
snapshot schemas
```

A partir d'une RC :

```text
breaking public API change forbidden
```

sans politique de version appropriée.

---

# 17. Quality Gates

## G0 - Local Developer

```text
format
lint
targeted unit tests
```

## G1 - Pull Request

```text
format
lint
type check
unit
property
InMemory contracts
changed-code coverage
```

## G2 - Main Branch

```text
G1
PostgreSQL integration
Django contracts
SQLAlchemy contracts
golden tests
migration smoke
```

## G3 - Nightly

```text
G2
full version matrix
concurrency stress
replay
mutation sample
performance smoke
```

## G4 - Release Candidate

```text
G3
package build
clean install
public API manifest
adapter qualification
migration qualification
artifact checksums
qualification manifest
```

## G5 - Stable

```text
G4
0 BLOCKER
0 CRITICAL
0 known flaky critical tests
API frozen
Production adapters green
release notes validated
```

---

# 18. Outils recommandés

## Tests

```text
pytest
Hypothesis
pytest-cov
```

## Format / Lint

```text
ruff
```

## Typage

Choisir un outil principal :

```text
mypy
```

ou :

```text
pyright
```

## Security Adjacent

```text
bandit
pip-audit / equivalent
secret scanning
```

---

# 19. Couverture

La couverture est une métrique, pas une preuve suffisante.

Cibles initiales :

```text
domain/          >= 95 %
application/     >= 90 %
ports/           >= 90 %
adapters/        >= 80 %
overall          >= 85 %
```

Les modules critiques suivent aussi la branch coverage.

---

# 20. Mutation testing

P1 recommandé sur :

```text
posting
reversal
trial balance
policy resolution
closing gates
```

Outil possible :

```text
mutmut
```

Objectif : détecter les tests trop superficiels.

---

# 21. Tests déterministes

Interdit dans les tests métier :

```text
datetime.now()
random global
system timezone
locale-dependent behavior
```

Utiliser :

```text
FrozenClock
DeterministicIdFactory
FakeSequenceProvider
```

---

# 22. Test Data Builders

Builders recommandés :

```text
JournalEntryBuilder
CompanyAccountBuilder
AccountingPeriodBuilder
AccountingPolicySetBuilder
ReferenceSnapshotBuilder
ClosingRunBuilder
```

Par défaut, un builder doit produire un objet valide.

---

# 23. Naming convention

Format recommandé :

```text
test_<behavior>_<condition>_<expected>
```

Exemple :

```text
test_post_entry_when_period_closed_raises_closed_period_error
```

---

# 24. Regulatory dataset qualification

Pour chaque standard supporté :

```text
schema valid
IDs stable
hierarchy valid
effective plan integrity
review flags preserved
reference snapshot generated
reporting capability qualified if advertised
```

---

# 25. Company Chart test matrix

```text
6 digits
8 digits
9 digits
10 digits
variable length
segmented
alphanumeric
```

Le même `ReferenceAccount` doit pouvoir être lié à des codes entreprise différents.

---

# 26. Accounting Policy test matrix

```text
resolution
recognition
initial measurement
subsequent measurement
depreciation
impairment
accrual
provision
policy migration
```

Chaque test doit pinner :

```text
policy_id
policy_version
reference snapshot
```

---

# 27. Closing test matrix

```text
month-end
quarter-end
year-end
reopen
opening balances
```

Scénarios cut-off :

```text
accrued expense
accrued income
prepaid expense
deferred income
```

---

# 28. Control test matrix

Tester chaque statut :

```text
PASS
FAIL
WARNING
INDETERMINATE
ERROR
```

et chaque gate :

```text
blocking
non-blocking
override allowed
override forbidden
```

---

# 29. Audit test matrix

```text
actor
occurred_at
object_ref
correlation_id
append-only
before/after minimization
entity isolation
```

---

# 30. Traceability test matrix

Chaîne cible :

```text
source
-> normalized record
-> JournalEntry
-> JournalLine
-> Trial Balance
-> Statement Line
-> Analysis
```

Les golden scenarios doivent vérifier le drill-down.

---

# 31. Adapter qualification levels

```text
TEST_ONLY
REFERENCE
EXPERIMENTAL
PRODUCTION
```

Un adapter `PRODUCTION` doit passer :

```text
all contract tests
real DB integration
real concurrency suite
rollback fault injection
migration suite
performance smoke
```

---

# 32. Qualification des adapters

## InMemory

```text
REFERENCE / TEST_ONLY
```

## Django/PostgreSQL

Cible :

```text
PRODUCTION
```

## SQLAlchemy/PostgreSQL

Cible :

```text
PRODUCTION
```

---

# 33. Matrice CI

La matrice exacte sera figée dans la release strategy, mais doit couvrir :

```text
supported Python versions
supported Django versions
supported SQLAlchemy versions
supported PostgreSQL versions
```

---

# 34. Fast CI vs Full CI

## Fast CI

```text
one Python version
InMemory
unit
property
contract
```

## Full CI

```text
all supported versions
PostgreSQL
Django
SQLAlchemy
concurrency
migration
golden
replay
```

---

# 35. Test markers

```text
unit
property
contract
integration
postgres
django
sqlalchemy
concurrency
golden
replay
migration
slow
performance
```

---

# 36. PostgreSQL qualification

Un adapter SQL de production doit être testé sur une vraie instance PostgreSQL.

Approches :

```text
Testcontainers
Docker Compose
CI native service container
```

SQLite peut servir à des tests rapides, mais ne valide pas :

```text
select_for_update
real transaction isolation
PostgreSQL locking
real deadlocks
```

---

# 37. Concurrency harness

Eviter les tests synchronisés par :

```text
sleep(1)
```

Utiliser :

```text
thread barriers
explicit events
two DB connections
controlled lock points
```

---

# 38. Performance smoke tests

Hot paths :

```text
post 10 lines
post 100 lines
ledger 100k lines
trial balance 100k lines
bulk import
```

Le P0 vise surtout la détection de régression grossière.

---

# 39. N+1 query tests

Exemple :

```text
validate 100-line entry
```

ne doit pas provoquer :

```text
100 individual account queries
```

---

# 40. Security-adjacent tests

Vérifier :

```text
no secrets in audit
no credentials in metadata
artifact refs validated
entity isolation
optional dependencies isolated
```

---

# 41. Serialization tests

```text
Decimal serialized canonically
dates ISO 8601
timezones explicit
enums stable
schema_version present
```

Jamais de conversion d'un montant comptable vers `float`.

---

# 42. Optional dependency tests

Le core doit fonctionner sans Django ni SQLAlchemy.

Tester :

```text
pip install pyaccountingkit
```

puis :

```text
import pyaccountingkit
```

sans adapter ORM installé.

---

# 43. Package install tests

Tester :

```text
core only
[django]
[sqlalchemy]
all extras
```

Construire et installer :

```text
wheel
sdist
```

dans un environnement propre.

---

# 44. Public API manifest

A partir RC, générer :

```text
PUBLIC_API_MANIFEST.json
```

pour surveiller les symboles publics.

---

# 45. Adapter Contract Manifest

```text
PORT_CONTRACT_MANIFEST.json
```

peut pinner :

```text
contract_version
required protocols
capabilities
```

---

# 46. Qualification Manifest

Artifact recommandé :

```text
TEST_QUALIFICATION_MANIFEST.json
```

contenant :

```text
package version
commit/build id
Python version
test suite version
adapter qualification
golden checksums
supported standards
release gate status
```

---

# 47. Flaky tests

Politique stable :

```text
0 known flaky critical tests
```

Un test critique ne peut pas être simplement ignoré pour publier une stable.

---

# 48. Regression policy

Tout bug critique corrigé doit ajouter un test de régression.

Catégories critiques :

```text
wrong accounting result
double posting
lost reversal
wrong period
wrong reference mapping
lost audit
non-reproducible result
```

---

# 49. Structure cible du dossier tests

```text
tests/
|
+-- unit/
|   +-- domain/
|   +-- application/
|
+-- property/
|
+-- contract/
|   +-- repositories/
|   +-- uow/
|   +-- queries/
|   +-- providers/
|
+-- integration/
|   +-- django/
|   +-- sqlalchemy/
|   +-- reference/
|
+-- concurrency/
|
+-- golden/
|
+-- replay/
|
+-- migration/
|
+-- performance/
|
+-- support/
|
+-- fixtures/
    +-- accounting/
    +-- reference/
    +-- cfa_fra/
```

---

# 50. Premier golden scenario recommandé

```text
Opening:
    Dr Cash 1,000
    Cr Capital 1,000

Normal:
    Dr Expense 200
    Cr Cash 200

Adjustment:
    Dr Expense 50
    Cr Accrued 50

Reversal:
    inverse a selected posted entry

Closing:
    close temporary account according to policy
```

Outputs vérifiés :

```text
journal order
ledger balances
trial balance before adjustments
adjusted balance
post-closing balance
reversal links
audit events
control results
```

---

# 51. Risk-based testing

Priorité maximale :

```text
Money
Posting
Reversal
Periods
Reference Mapping
Policy Resolution
Ledger
Closing
Audit
Reproducibility
Concurrency
```

| Risque | Impact | Priorité |
|---|---:|---:|
| Mauvais équilibre | Critique | maximale |
| Double posting | Critique | maximale |
| Mauvais mapping réglementaire | Critique | maximale |
| Posting après close | Critique | maximale |
| Reversal incorrecte | Critique | maximale |
| Perte d'audit | Critique | maximale |
| Ledger incorrect | Critique | maximale |
| Mauvaise policy | Critique | maximale |
| Code de compte invalide | Majeur | haute |
| Régression performance | Majeur | moyenne/haute |

---

# 52. Definition of Done - Domain Feature

```text
spec updated
unit tests
property tests where meaningful
error taxonomy updated
public API documented
no uncovered invariant
```

---

# 53. Definition of Done - Adapter Feature

```text
contract tests
real DB integration
rollback tests
concurrency tests
exception translation
performance smoke
```

---

# 54. Definition of Done - Regulatory Feature

```text
reference fixture
snapshot version
golden test
human-review flags respected
provenance preserved
```

---

# 55. Definition of Done - Closing Feature

```text
normal flow
blocking flow
reopen flow
audit
idempotence
concurrency
```

---

# 56. Test smells interdits

```text
assert True
sleep-based concurrency tests
real datetime dependency
float money
mock every repository method
golden update without review
test depending on execution order
shared mutable fixture
catch Exception and ignore
```

---

# 57. ADRs

| ID | Décision |
|---|---|
| ADR-TEST-001 | Les invariants critiques sont couverts par unit + property + integration |
| ADR-TEST-002 | Hypothesis est recommandé pour les property-based tests |
| ADR-TEST-003 | Les adapters partagent une contract suite commune |
| ADR-TEST-004 | Les races critiques sont testées contre PostgreSQL réel |
| ADR-TEST-005 | SQLite seul ne qualifie pas un adapter Production |
| ADR-TEST-006 | CFA FRA est un golden oracle, pas une dépendance runtime |
| ADR-TEST-007 | Les golden fixtures sont versionnées et immutables |
| ADR-TEST-008 | Toute modification golden nécessite une revue explicite |
| ADR-TEST-009 | Les tests réglementaires pinent standard/edition/dataset |
| ADR-TEST-010 | Les policy tests pinent leur version |
| ADR-TEST-011 | Les replay tests pinent runtime/reference/policy/source snapshots |
| ADR-TEST-012 | Les migrations exécutent des controls post-migration |
| ADR-TEST-013 | Coverage n'est pas une preuve suffisante |
| ADR-TEST-014 | La cible de couverture du domain est >= 95 % |
| ADR-TEST-015 | Tout bug comptable critique corrigé ajoute un regression test |
| ADR-TEST-016 | Les exemples publics sont testés |
| ADR-TEST-017 | Les dépendances optionnelles sont testées séparément |
| ADR-TEST-018 | Les RC exécutent la full concurrency suite |
| ADR-TEST-019 | Un adapter Production doit passer rollback + concurrency + migration |
| ADR-TEST-020 | Les flakes critiques sont interdits en stable |
| ADR-TEST-021 | Les tests temporels utilisent un Clock injecté |
| ADR-TEST-022 | Decimal est obligatoire dans les tests monétaires |
| ADR-TEST-023 | Les ouvrages doctrinaux ne remplacent pas la réglementation courante |
| ADR-TEST-024 | Chaque release génère un qualification manifest |
| ADR-TEST-025 | Toute divergence de golden output doit être expliquée |
| ADR-TEST-026 | Les query semantics doivent être identiques entre adapters |
| ADR-TEST-027 | La fault injection fait partie de la qualification Production |
| ADR-TEST-028 | L'API publique est surveillée par manifest à partir de RC |
| ADR-TEST-029 | Les snapshots historiques ne sont pas recalculés silencieusement en migration |
| ADR-TEST-030 | La stratégie de tests fait partie du contrat produit de PyAccountingKit |

---

# 58. Critères d'acceptation P0.12

```text
[ ] taxonomie des tests définie
[ ] pyramide de tests définie
[ ] unit tests obligatoires pour invariants
[ ] property-based tests définis
[ ] Hypothesis recommandé
[ ] contract tests définis
[ ] Repository Contract défini
[ ] UnitOfWork Contract défini
[ ] Query Contract défini
[ ] Reference Provider Contract défini
[ ] integration tests définis
[ ] concurrency tests définis
[ ] PostgreSQL réel obligatoire pour les races
[ ] double posting testé
[ ] double reversal testé
[ ] posting vs close testé
[ ] idempotency race testée
[ ] fault injection définie
[ ] golden tests définis
[ ] CFA FRA utilisé comme oracle comportemental
[ ] replay tests définis
[ ] migration tests définis
[ ] compatibility tests définis
[ ] PR / Main / RC / Stable gates définis
[ ] coverage targets définis
[ ] domain coverage target >= 95 %
[ ] static typing gate défini
[ ] security scanning défini
[ ] deterministic clock/ids définis
[ ] golden fixtures versionnées
[ ] golden updates nécessitent revue
[ ] adapter qualification levels définis
[ ] Production adapter qualification définie
[ ] package install matrix définie
[ ] optional dependency tests définis
[ ] public API manifest prévu
[ ] aucun flaky test critique en stable
[ ] qualification manifest prévu
```

---

# 59. Ordre d'implémentation recommandé

## TEST-00 - Core Primitives

```text
Money
IDs
Dates
AccountCode
Revision
```

## TEST-01 - Accounting Invariants

```text
JournalEntry
JournalEntryLine
partie double
immutabilité
```

## TEST-02 - Posting / Reversal

```text
state machine
posting
reversal
idempotence
```

## TEST-03 - Reference Data

```text
provider contracts
datasets
snapshots
```

## TEST-04 - Policies

```text
resolution
recognition
measurement
trace
```

## TEST-05 - Company Chart

```text
6/8/9/N
segmentation
bindings
```

## TEST-06 - Ledger

```text
journal
general ledger
trial balance
```

## TEST-07 - Closing

```text
cut-off
adjustments
close
reopen
opening
```

## TEST-08 - Controls / Audit

```text
control runs
gates
audit trail
lineage
```

## TEST-09 - Persistence Contracts

```text
repositories
UoW
idempotency
outbox
```

## TEST-10 - Django Adapter

```text
PostgreSQL integration
concurrency
```

## TEST-11 - SQLAlchemy Adapter

```text
PostgreSQL integration
concurrency
```

## TEST-12 - Golden CFA FRA

```text
behavior parity
```

## TEST-13 - Migration / Replay

```text
schema upgrade
snapshot preservation
reproducibility
```

---

# 60. Conclusion

La stratégie qualité de PyAccountingKit repose sur une idée simple :

```text
les règles comptables critiques
ne doivent jamais dépendre
d'un seul niveau de test.
```

La chaîne cible est :

```text
Unit
    ↓
Property
    ↓
Contract
    ↓
Integration
    ↓
Concurrency
    ↓
Golden
    ↓
Replay
    ↓
Migration
    ↓
Release Gates
```

Les protections prioritaires concernent :

```text
partie double
immutabilité
reversal
périodes
policies
mapping réglementaire
ledger
closing
audit
reproductibilité
transactions
concurrence
```

PyAccountingKit ne devra être déclaré stable que lorsque :

```text
InMemory
Django/PostgreSQL
SQLAlchemy/PostgreSQL
```

produisent les mêmes semantics comptables sur la contract suite et les golden scenarios, et lorsque les races critiques ont été qualifiées sur une base transactionnelle réelle.

---

**Prochain document recommandé :**

```text
12_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md
```
