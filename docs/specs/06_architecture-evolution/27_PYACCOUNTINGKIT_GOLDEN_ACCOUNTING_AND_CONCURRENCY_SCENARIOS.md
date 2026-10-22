# 27_PYACCOUNTINGKIT_GOLDEN_ACCOUNTING_AND_CONCURRENCY_SCENARIOS.md

# PyAccountingKit — Golden Accounting & Concurrency Scenarios

> **Projet** : PyAccountingKit  
> **Document** : `27_PYACCOUNTINGKIT_GOLDEN_ACCOUNTING_AND_CONCURRENCY_SCENARIOS.md`  
> **Statut** : Spécification transverse de qualification métier et transactionnelle  
> **Version documentaire** : 1.0  
> **Date** : 22 octobre 2026  
> **Baseline observée** : PyAccountingKit `0.7.0rc1`  
> **Langue** : Français  

---

# 1. Objet du document

Ce document définit la stratégie cible de **Golden Accounting Scenarios** et de **Concurrency Scenarios** de PyAccountingKit.

Il complète :

```text
11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md
10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md
15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md
22_PYACCOUNTINGKIT_RECONCILIATION_ARCHITECTURE.md
26_PYACCOUNTINGKIT_REPRODUCIBILITY_AND_COMPUTATION_MANIFESTS.md
```

L'objectif est de fournir une suite transverse capable de prouver :

```text
correct accounting behavior
+
correct transaction boundaries
+
correct concurrency behavior
+
deterministic replay
+
cross-adapter semantic parity
```

---

# 2. Pourquoi une spécification dédiée

Le dépôt possède déjà :

```text
unit tests
property tests
contract tests
integration tests
concurrency tests
golden tests
replay tests
CFA FRA golden fixtures
```

Cependant ces preuves sont aujourd'hui distribuées entre :

```text
testing strategy
bounded-context specs
release plans
CFA FRA qualification
adapter qualification
```

Ce document introduit une vision commune :

> **un scénario métier critique doit pouvoir être qualifié comme une histoire comptable complète, avec des résultats attendus et des races explicitement interdites.**

---

# 3. Golden scenario

Un Golden Scenario est :

> **un scénario métier versionné, déterministe et explicite dont les inputs et outputs attendus servent de preuve de non-régression.**

Il ne teste pas seulement :

```text
one method
```

mais une chaîne métier telle que :

```text
Invoice
→ Receivable
→ Journal Entry
→ Payment
→ Settlement
→ Reconciliation
→ Closing
→ Reporting
```

---

# 4. Concurrency scenario

Un Concurrency Scenario est :

> **un scénario contrôlé dans lequel plusieurs opérations concurrentes tentent d'affecter le même état métier ou transactionnel.**

Exemple :

```text
Worker A
    posting

Worker B
    closing same period
```

La suite doit démontrer que seules les issues autorisées peuvent exister.

---

# 5. Golden != Snapshot Testing naïf

Un golden test ne consiste pas à accepter automatiquement :

```text
new output
```

parce que le code a changé.

Toute différence doit être :

```text
expected
reviewed
explained
versioned
```

---

# 6. Baseline CFA FRA

PyAccountingKit possède déjà une baseline spécialisée :

```text
CFA FRA Golden Scenario Inventory
```

avec des scénarios notamment pour :

```text
posting
reversal
FEC
ledger
trial balance
statements
analysis
controls
```

Cette baseline reste un oracle comportemental historique.

---

# 7. CFA FRA != Generic Golden Accounting

La cible de ce document est plus générale.

```text
CFA FRA Golden
    = legacy parity / migration oracle

Golden Accounting
    = framework-wide canonical qualification
```

Les scénarios génériques ne doivent pas dépendre du legacy CFA FRA.

---

# 8. Principe de qualification

Un golden scenario doit déclarer :

```text
scenario_id
scenario_version
category
purpose
accounting framework context
inputs
preconditions
commands
expected domain events
expected state
expected snapshots
expected controls
expected checksums
supported adapters
```

---

# 9. `GoldenScenarioDefinition`

Concept cible :

```text
GoldenScenarioDefinition
|
+-- scenario_id
+-- version
+-- title
+-- category
+-- description
+-- accounting_context
+-- fixture_refs
+-- execution_steps
+-- expected_assertions
+-- expected_events
+-- expected_checksums
```

---

# 10. Golden scenario categories

```text
POSTING
REVERSAL
ORDER_TO_CASH
PURCHASE_TO_PAY
SETTLEMENT
AGING
RECONCILIATION
CLOSING
IMPORT
REPORTING
ANALYSIS
CONSOLIDATION
MULTI_CURRENCY
SEMANTIC
```

---

# 11. Golden fixture governance

Chaque fixture doit avoir :

```text
fixture_id
fixture_version
source
input_checksum
expected_output_checksum
```

Tout changement sémantique doit être revu.

---

# 12. Pas d'auto-update aveugle

Interdit :

```text
pytest --update-all-golden
```

sans revue métier.

Toute modification attendue doit documenter :

```text
before
after
reason
migration impact
ADR or issue
```

---

# 13. Intentional divergence

Une divergence peut être acceptée pour :

```text
BUG_FIX
GENERALIZATION
REGULATORY_CORRECTION
PORTABILITY_CHANGE
SAFETY_HARDENING
API_REDESIGN
```

mais doit être enregistrée explicitement.

---

# 14. Golden checksum

Chaque scénario doit pouvoir produire :

```text
semantic checksum
```

des résultats critiques.

Exemples :

```text
trial balance checksum
report snapshot checksum
analysis snapshot checksum
reconciliation snapshot checksum
```

---

# 15. Golden manifest

Chaque exécution peut produire :

```text
GoldenScenarioManifest
```

contenant :

```text
scenario id/version
fixture checksums
framework version
reference context
policy versions
adapter
result checksums
```

---

# 16. Cross-adapter parity

Un Golden Scenario critique doit pouvoir être exécuté sur :

```text
InMemory
Django/PostgreSQL
SQLAlchemy/PostgreSQL
```

lorsque les capabilities correspondantes sont supportées.

---

# 17. Semantic parity

Le test compare :

```text
business meaning
```

pas :

```text
database primary keys
row insertion order
ORM-specific objects
```

---

# 18. Decimal discipline

Les valeurs monétaires golden utilisent :

```text
Decimal strings
```

Jamais :

```text
float
```

---

# 19. Time control

Les golden tests utilisent :

```text
FrozenClock
```

ou un clock déterministe.

---

# 20. ID control

Les golden tests peuvent utiliser :

```text
DeterministicIdFactory
```

lorsque l'identifiant influence un artifact attendu.

---

# 21. Golden Scenario 1 — Minimal Double Entry

## ID

```text
GOLD-GL-001
```

## Input

```text
Dr Cash        1,000
Cr Capital     1,000
```

## Expected

```text
entry validated
entry posted
total debit = 1,000
total credit = 1,000
trial balance balanced
```

---

# 22. Golden Scenario 2 — Unbalanced rejection

## ID

```text
GOLD-GL-002
```

Input :

```text
Dr Cash        1,000
Cr Capital       900
```

Expected :

```text
validation fails
no posting
no ledger movement
no outbox accounting event
```

---

# 23. Golden Scenario 3 — Reversal

## ID

```text
GOLD-GL-003
```

Input :

```text
posted original entry
```

Action :

```text
reverse
```

Expected :

```text
original preserved
original status = REVERSED
new reversal entry = POSTED
debit/credit swapped
net(original + reversal) = 0
```

---

# 24. Golden Scenario 4 — Trial Balance lifecycle

## ID

```text
GOLD-TB-001
```

Fixture :

```text
Opening
Cash        Dr 1,000
Capital     Cr 1,000

Normal
Rent        Dr 200
Cash        Cr 200

Adjustment
Rent        Dr 50
Accrued     Cr 50

Closing
Capital     Dr 250
Rent        Cr 250
```

Expected :

```text
BEFORE_ADJUSTMENTS
ADJUSTED
POST_CLOSING
```

avec balances déterministes.

---

# 25. Golden Scenario 5 — Order to Cash

## ID

```text
GOLD-O2C-001
```

Flow :

```text
Customer
    ↓
Invoice
    ↓
Receivable
    ↓
JournalEntry
    ↓
Payment
    ↓
Settlement
    ↓
Matching
    ↓
Bank Reconciliation
```

---

# 26. O2C expected assertions

```text
invoice issued
receivable recognized
journal entry balanced
customer subledger updated
payment recorded
settlement allocated
outstanding balance = 0
bank line reconciled
subledger = control account
```

---

# 27. O2C accounting evidence

Le scénario doit produire :

```text
journal entry IDs
receivable ID
payment ID
settlement allocation
reconciliation match
trial balance snapshot
```

---

# 28. Golden Scenario 6 — Partial Settlement

## ID

```text
GOLD-SET-001
```

Input :

```text
Receivable = 1,000 EUR
Payment = 600 EUR
```

Expected :

```text
allocated = 600
outstanding = 400
status = PARTIALLY_SETTLED
```

---

# 29. Golden Scenario 7 — Multi-invoice Settlement

## ID

```text
GOLD-SET-002
```

Input :

```text
Payment = 1,000

Invoice A = 600
Invoice B = 300
```

Expected :

```text
A settled = 600
B settled = 300
unallocated = 100
```

---

# 30. Golden Scenario 8 — Purchase to Pay

## ID

```text
GOLD-P2P-001
```

Flow :

```text
Supplier
    ↓
Supplier Invoice
    ↓
Payable
    ↓
Journal Entry
    ↓
Outgoing Payment
    ↓
Settlement
    ↓
Bank Reconciliation
```

Expected :

```text
payable recognized
AP subledger updated
payment executed/recorded
settlement complete
bank reconciliation complete
GL control account matches AP
```

---

# 31. Golden Scenario 9 — Receivable Aging

## ID

```text
GOLD-AGING-001
```

Fixtures :

```text
Invoice A due 10 days ago
Invoice B due 40 days ago
Invoice C due 95 days ago
```

Expected buckets :

```text
0-30
31-60
61-90
90+
```

---

# 32. Aging expected invariant

```text
sum aging buckets
=
total outstanding receivables
```

---

# 33. Golden Scenario 10 — Bank Reconciliation

## ID

```text
GOLD-REC-001
```

Input :

```text
Bank line = 1,000 EUR
Ledger line = 1,000 EUR
same reference
```

Expected :

```text
exact match
residual = 0
control PASS
```

---

# 34. Golden Scenario 11 — Bank Fee

## ID

```text
GOLD-REC-002
```

Input :

```text
Bank fee = -15 EUR
No ledger entry
```

Expected :

```text
unmatched bank item
cause = BANK_FEE
optional JournalEntryProposal
no direct posting by reconciliation
```

---

# 35. Golden Scenario 12 — Reconciliation ambiguity

## ID

```text
GOLD-REC-003
```

Input :

```text
source = 100 ref X

target A = 100 ref X
target B = 100 ref X
```

Expected :

```text
MULTIPLE_EXACT
review required
no auto-match
```

---

# 36. Golden Scenario 13 — Subledger vs GL

## ID

```text
GOLD-SUB-001
```

Input :

```text
AR Subledger = 25,000
GL Control Account = 25,000
```

Expected :

```text
reconciliation PASS
```

---

# 37. Golden Scenario 14 — Subledger mismatch

## ID

```text
GOLD-SUB-002
```

Input :

```text
AR = 25,000
GL = 24,950
```

Expected :

```text
difference = 50
difference visible
drill-down available
```

---

# 38. Golden Scenario 15 — FEC Import

## ID

```text
GOLD-IMP-001
```

Flow :

```text
Raw FEC
    ↓
Parse
    ↓
Normalize
    ↓
Map
    ↓
Validate
    ↓
Import Plan
    ↓
Post
```

Expected :

```text
raw preserved
source checksum stable
all source records accounted for
debit=credit
lineage preserved
```

---

# 39. Golden Scenario 16 — Duplicate Import

## ID

```text
GOLD-IMP-002
```

Input :

```text
same source checksum
same entity
same scope
```

Expected :

```text
second import detected
no duplicate economic effect
```

---

# 40. Golden Scenario 17 — Period Close

## ID

```text
GOLD-CLOSE-001
```

Flow :

```text
OPEN
    ↓
REVIEW
    ↓
CLOSING
    ↓
controls
    ↓
closing adjustments
    ↓
post-closing trial balance
    ↓
CLOSED
```

Expected :

```text
no blocker
closing entries posted once
period CLOSED
post-closing TB balanced
```

---

# 41. Golden Scenario 18 — Close blocked

## ID

```text
GOLD-CLOSE-002
```

Input :

```text
blocking control failure
```

Expected :

```text
period remains non-CLOSED
no final close
blocking evidence retained
```

---

# 42. Golden Scenario 19 — Reopen

## ID

```text
GOLD-CLOSE-003
```

Expected :

```text
reopen explicit
audit event
new revision
historical close evidence preserved```

---

# 43. Golden Scenario 20 — Financial Statements

## ID

```text
GOLD-STMT-001
```

Expected equations :

```text
Assets
=
Liabilities + Equity
```

```text
Revenue - Expenses
=
Net Income
```

---

# 44. Golden Scenario 21 — Financial Analysis

## ID

```text
GOLD-ANA-001
```

Expected metrics :

```text
EBITDA
Working Capital
BFR
Current Ratio
Net Margin
ROA
ROE
```

avec checksums déterministes.

---

# 45. Golden Scenario 22 — Regulatory Export

## ID

```text
GOLD-REG-001
```

Flow :

```text
ReportSnapshot
    ↓
Regulatory Profile
    ↓
Export Definition
    ↓
Renderer
```

Expected :

```text
payload valid
payload SHA-256 stable
source report checksum linked
```

---

# 46. Golden Scenario 23 — Multi-currency

## ID

```text
GOLD-FX-001
```

Input :

```text
transaction currency = USD
functional currency = EUR
pinned FX observation
```

Expected :

```text
explicit converted amount
source rate preserved
conversion reproducible
no silent currency mixing
```

---

# 47. Golden Scenario 24 — Consolidation

## ID

```text
GOLD-CONS-001
```

Inputs :

```text
Entity A
Entity B
intercompany positions
scope
ownership
FX
```

Expected :

```text
source entity ledgers unchanged
group adjustments isolated
eliminations deterministic
consolidated snapshot balanced
```

---

# 48. Golden Scenario 25 — Semantic Layer

## ID

```text
GOLD-SEM-001
```

Flow :

```text
ReportSnapshot
AnalysisSnapshot
    ↓
Semantic Model
    ↓
Revenue / EBITDA / NetIncome
```

Expected :

```text
same metric values across
DataFrame
SQL
BI adapter
```

---

# 49. Golden full accounting cycle

Scenario maître :

```text
GOLD-E2E-001
```

Flow :

```text
Entity setup
    ↓
Chart / Reference binding
    ↓
Opening balances
    ↓
Sales invoice
    ↓
Receivable
    ↓
Customer payment
    ↓
Settlement
    ↓
Bank reconciliation
    ↓
Supplier invoice
    ↓
Payable
    ↓
Supplier payment
    ↓
Adjustment
    ↓
Period close
    ↓
Trial Balance
    ↓
Financial Statements
    ↓
Financial Analysis
    ↓
Semantic Snapshot
```

---

# 50. Full-cycle assertions

```text
all journal entries balanced
subledger controls pass
all settlements within outstanding amounts
bank reconciliation balanced
period closes once
trial balance balanced
balance sheet equation true
analysis checksums stable
semantic output matches source snapshots
```

---

# 51. Concurrency principles

Concurrency tests must prove:

```text
correctness under race
```

not simply:

```text
no exception
```

---

# 52. Real database requirement

Critical races require :

```text
real PostgreSQL
multiple connections
explicit barriers
controlled lock points
```

SQLite or mocks are insufficient.

---

# 53. No sleep-based synchronization

Avoid :

```python
sleep(1)
```

Use :

```text
thread barriers
events
locks
explicit transaction checkpoints
```

---

# 54. Allowed outcomes

Every race test must specify:

```text
allowed outcomes
forbidden outcomes
```

---

# 55. Race 1 — Double Posting

## ID

```text
RACE-POST-001
```

Initial :

```text
Entry = VALIDATED
```

Concurrent :

```text
Worker A → post
Worker B → post
```

Allowed :

```text
one POSTED
one conflict/idempotent duplicate response
```

Forbidden :

```text
two postings
two ledger effects
two outbox business events
```

---

# 56. Race 2 — Double Reversal

## ID

```text
RACE-REV-001
```

Allowed :

```text
one reversal entry
one rejected/conflicting attempt
```

Forbidden :

```text
two reversal entries
```

---

# 57. Race 3 — Posting vs Period Close

## ID

```text
RACE-CLOSE-001
```

Concurrent :

```text
Worker A → post entry
Worker B → close period
```

Allowed outcome A :

```text
posting commits first
close sees posted entry
close succeeds
```

Allowed outcome B :

```text
close wins
posting fails
```

Forbidden :

```text
entry commits after period is CLOSED
```

---

# 58. Race 4 — Double Close

## ID

```text
RACE-CLOSE-002
```

Allowed :

```text
one close revision
```

Forbidden :

```text
duplicate closing effects
duplicate opening generation
```

---

# 59. Race 5 — Reopen vs Posting

## ID

```text
RACE-CLOSE-003
```

Objectif :

```text
posting eligibility
must reflect committed period state
```

---

# 60. Race 6 — Double Settlement

## ID

```text
RACE-SET-001
```

Initial :

```text
Receivable outstanding = 100
```

Concurrent :

```text
Worker A allocate 80
Worker B allocate 70
```

Allowed :

```text
one allocation succeeds
other receives remaining-based rejection or retries safely
```

Invariant final :

```text
allocated_total <= 100
```

Forbidden :

```text
allocated_total = 150
```

---

# 61. Race 7 — Settlement vs Reversal

## ID

```text
RACE-SET-002
```

Concurrent :

```text
Worker A allocate payment
Worker B reverse payment
```

Expected :

```text
one serializable outcome
no settlement referencing invalid reversed economic state
```

---

# 62. Race 8 — Two Settlements Same Invoice

## ID

```text
RACE-SET-003
```

Expected :

```text
outstanding never negative
```

---

# 63. Race 9 — Match Acceptance Race

## ID

```text
RACE-REC-001
```

Two reviewers attempt to accept competing match candidates for the same residual.

Expected :

```text
only one allocation consumes residual
```

---

# 64. Race 10 — Match vs Reverse Match

## ID

```text
RACE-REC-002
```

Expected :

```text
reconciliation state remains internally consistent
```

---

# 65. Race 11 — Reconciliation Publish vs Source Refresh

## ID

```text
RACE-REC-003
```

Concurrent :

```text
publish reconciliation snapshot
source snapshot changes
```

Allowed :

```text
published snapshot pins old source and becomes stale
```

Forbidden :

```text
snapshot silently mixes source versions
```

---

# 66. Race 12 — Reconciliation vs Entry Reversal

## ID

```text
RACE-REC-004
```

Expected :

```text
published reconciliation points to explicit source revision
new reversal produces new reconciliation requirement/staleness
```

---

# 67. Race 13 — Duplicate Import

## ID

```text
RACE-IMP-001
```

Concurrent :

```text
Worker A imports artifact H
Worker B imports same artifact H
```

Expected :

```text
one economic effect
duplicate detected
```

---

# 68. Race 14 — Same Source Entry in Two Batches

## ID

```text
RACE-IMP-002
```

Expected :

```text
source-entry identity prevents duplicate posting
```

---

# 69. Race 15 — Import vs Period Close

## ID

```text
RACE-IMP-003
```

Allowed :

```text
import posts before close
```

or :

```text
close wins and import fails for protected period
```

Forbidden :

```text
historical entry appears after close without reopen flow
```

---

# 70. Race 16 — Import Plan vs Mapping Change

## ID

```text
RACE-IMP-004
```

Initial :

```text
plan checksum P1
mapping M1
```

Concurrent :

```text
mapping changes to M2
execute P1
```

Expected :

```text
stale plan rejected
```

---

# 71. Race 17 — Reference Version Switch vs Posting

## ID

```text
RACE-REF-001
```

Concurrent :

```text
Worker A resolves reference under V1
Worker B activates V2
```

Expected :

```text
posting uses one explicit reference context
no mixed V1/V2 evaluation
```

---

# 72. Race 18 — Policy Set Activation vs Posting

## ID

```text
RACE-POL-001
```

Expected :

```text
posting pins one policy set version
```

Forbidden :

```text
half evaluation with old policy
half with new policy
```

---

# 73. Race 19 — Entry Number Allocation

## ID

```text
RACE-NUM-001
```

Concurrent :

```text
two postings request next number
```

Expected :

```text
unique numbers within configured scope
```

---

# 74. Race 20 — Account Creation

## ID

```text
RACE-ACC-001
```

Concurrent :

```text
two workers create same account code
```

Expected :

```text
one account
one duplicate/conflict
```

---

# 75. Race 21 — Idempotency Claim

## ID

```text
RACE-IDEM-001
```

Concurrent :

```text
same command idempotency key
```

Expected :

```text
one side effect
```

---

# 76. Race 22 — Outbox Commit

## ID

```text
RACE-OUT-001
```

Fault points :

```text
after aggregate save
after audit append
before outbox append
before commit
```

Expected :

```text
rollback all
```

---

# 77. Race 23 — Outbox Duplicate Delivery

## ID

```text
RACE-OUT-002
```

Expected :

```text
consumer deduplicates EventId
no duplicate downstream economic effect
```

---

# 78. Race 24 — Report Publish vs Source Mutation

## ID

```text
RACE-RPT-001
```

Expected :

```text
published report pins source checksum
later mutation marks report stale
```

---

# 79. Race 25 — Analysis vs Report Supersession

## ID

```text
RACE-ANA-001
```

Expected :

```text
analysis snapshot explicitly references source report revision
```

---

# 80. Race 26 — Consolidation Publish vs Entity Restatement

## ID

```text
RACE-CONS-001
```

Expected :

```text
published consolidation pins entity snapshots
new restatement produces stale status/new run
```

---

# 81. Race 27 — Semantic Snapshot vs Metric Definition Change

## ID

```text
RACE-SEM-001
```

Expected :

```text
snapshot pins metric definition version
new definition does not rewrite historical snapshot
```

---

# 82. Concurrency outcome model

Concept :

```text
ConcurrencyScenarioResult
|
+-- scenario_id
+-- worker_results
+-- final_state
+-- invariant_results
+-- event_counts
+-- audit_counts
+-- outbox_counts
+-- checksum
```

---

# 83. Worker result

```text
SUCCESS
CONFLICT
IDEMPOTENT_REPLAY
REJECTED
RETRYABLE
FAILED
```

---

# 84. Conflict != failure

Une race correctement protégée peut produire :

```text
one SUCCESS
one CONFLICT
```

et être considérée :

```text
PASS
```

---

# 85. Invariant-based assertion

Les tests de concurrence doivent surtout vérifier :

```text
final business invariants
```

Exemples :

```text
outstanding >= 0
one close only
one reversal only
one economic import effect
```

---

# 86. Event-count assertions

Exemple double posting :

```text
journal_entry.posted event count = 1
```

---

# 87. Audit-count assertions

Exemple double settlement :

```text
successful allocation audit count=
successful allocation count
```

---

# 88. Outbox-count assertions

L'outbox doit refléter :

```text
committed business events only
```

---

# 89. Transaction rollback scenarios

Fault injection matrix :

```text
after entity mutation
after repository save
after audit record
after idempotency claim
after outbox stage
before commit
```

---

# 90. Transactional expected property

Avant commit failure :

```text
no partial durable state
```

---

# 91. Deadlock scenarios

Des tests peuvent provoquer des deadlocks contrôlés.

Expected :

```text
deterministic retry policy
or explicit conflict
```

sans double effet.

---

# 92. Retry policy

Un retry technique ne doit pas :

```text
re-run irreversible economic effect blindly
```

Il s'appuie sur :

```text
idempotency
transaction result
reconciliation
```

---

# 93. Uncertain commit outcome

Scénario :

```text
database commit sent
connection lost before acknowledgement
```

L'état est :

```text
UNCERTAIN
```

pas automatiquement :

```text
FAILED
```

Ce scénario sera détaillé dans `30`.

---

# 94. Golden + concurrency composition

Certains Golden Scenarios doivent posséder une variante race.

Exemple :

```text
GOLD-SET-001
    +
RACE-SET-001
```

---

# 95. Scenario matrix

| Golden | Race companion |
|---|---|
| Posting | Double Posting |
| Reversal | Double Reversal |
| Settlement | Double Settlement |
| Closing | Posting vs Close |
| Import | Duplicate Import |
| Reconciliation | Match Acceptance Race |
| Reporting | Publish vs Source Mutation |
| Consolidation | Publish vs Restatement |
| Semantic | Snapshot vs Definition Change |

---

# 96. Adapter qualification

## InMemory

Peut qualifier :

```text
business semantics
idempotency model
deterministic golden outputs
```

mais pas toutes les garanties SQL de locking.

---

# 97. PostgreSQL adapters

Django/PostgreSQL et SQLAlchemy/PostgreSQL doivent qualifier :

```text
real transaction isolation
row locking
optimistic conflicts
unique constraints
rollback
deadlock behavior
```

---

# 98. Adapter capability matrix

```text
supports_real_row_locking
supports_transactional_outbox
supports_optimistic_revision
supports_advisory_locking
```

Les scénarios exécutés dépendent des capabilities déclarées.

---

# 99. Cross-adapter Golden parity

La suite doit vérifier :

```text
same canonical input
→ same semantic output
```

sur tous les adapters compatibles.

---

# 100. Cross-adapter concurrency parity

L'issue technique peut varier :

```text
optimistic conflict
unique violation
pessimistic lock wait
```

mais le résultat métier final doit rester équivalent.

---

# 101. Golden replay

Chaque golden scenario critique doit pouvoir être rejoué avec :

```text
ComputationManifest
```

lorsqu'il produit un snapshot.

---

# 102. Replay assertion

```text
expected semantic checksum
==
actual semantic checksum
```

---

# 103. Current-engine comparison

Deux modes :

```text
EXACT_REPLAY
CURRENT_ENGINE_COMPARISON
```

---

# 104. EXACT_REPLAY

Pine :

```text
framework version
policy version
reference snapshots
definitions
mappings
external observations
```

---

# 105. CURRENT_ENGINE_COMPARISON

Utilise les mêmes inputs historiques avec le moteur courant.

Objectif :

```text
detect semantic regressions
```

---

# 106. Golden scenario manifest

Artifact possible :

```text
GOLDEN_ACCOUNTING_SCENARIO_MANIFEST.json
```

---

# 107. Manifest structure

```json
{
  "scenario_id": "GOLD-O2C-001",
  "scenario_version": "1",
  "fixture_checksums": [],
  "reference_context": {},
  "expected_checksums": {},
  "supported_adapters": []
}
```

---

# 108. Concurrency scenario manifest

Artifact :

```text
CONCURRENCY_SCENARIO_MANIFEST.json
```

avec :

```text
scenario id
workers
barriers
allowed outcomes
forbidden outcomes
required capabilities
```

---

# 109. Scenario evidence

Chaque exécution de qualification peut produire :

```text
ScenarioEvidence
```

---

# 110. Evidence fields

```text
scenario_id
scenario_version
adapter
database version
package version
result
expected checksums
actual checksums
worker outcomes
duration
executed_at
```

---

# 111. CI layers

## Pull Request

```text
golden smoke
InMemory deterministic scenarios
```

---

# 112. Main branch

```text
full generic golden suite
PostgreSQL integration
selected concurrency suite
```

---

# 113. Nightly

```text
full concurrency suite
stress repetition
deadlock/fault injection
cross-adapter parity
```

---

# 114. Release Candidate

```text
all critical goldens
all critical races
replay
adapter qualification
evidence bundle
```

---

# 115. Stable release gate

```text
0 critical golden mismatch
0 unexplained race invariant failure
0 flaky critical concurrency test
```

---

# 116. Flakiness policy

Un test race critique flaky est un blocker.

Interdit :

```text
rerun until green
```

comme stratégie permanente.

---

# 117. Repeat count

Les concurrency scenarios doivent pouvoir être exécutés plusieurs fois.

Exemple :

```text
100 iterations
```

pour certaines races rapides.

---

# 118. Stress vs deterministic race

Deux types :

```text
DETERMINISTIC_BARRIER_RACE
STRESS_RACE
```

---

# 119. Deterministic barrier race

Forcer l'interleaving avec :

```text
barriers
locks
events
```

pour reproduire exactement la fenêtre critique.

---

# 120. Stress race

Multiplier les workers et runs pour détecter des erreurs résiduelles.

---

# 121. Concurrency harness

Composants possibles :

```text
WorkerBarrier
TransactionCheckpoint
RaceCoordinator
WorkerResult
InvariantProbe
```

---

# 122. No application sleeps

La coordination ne doit pas dépendre de timing aléatoire.

---

# 123. Lock observability

Les adapters de test peuvent exposer des hooks uniquement dédiés à la qualification.

Ces hooks ne doivent pas contaminer la public API runtime.

---

# 124. Test-only instrumentation

Autorisé :

```text
test synchronization hooks
```

si clairement isolé dans :

```text
testing
```

---

# 125. Golden test directory target

```text
tests/golden/
├── ledger/
├── o2c/
├── p2p/
├── settlements/
├── reconciliation/
├── closing/
├── imports/
├── reporting/
├── analysis/
├── consolidation/
├── semantic/
└── cfa_fra/
```

---

# 126. Concurrency test directory target

```text
tests/concurrency/
├── posting/
├── reversal/
├── closing/
├── settlements/
├── reconciliation/
├── imports/
├── references/
├── reporting/
└── support/
```

---

# 127. Golden fixture naming

```text
<scenario_id>__v<version>.json
```

Exemple :

```text
GOLD-O2C-001__v1.json
```

---

# 128. Expected artifact naming

```text
GOLD-O2C-001__v1.expected.json
```

---

# 129. Scenario code naming

```python
def test_gold_o2c_001_full_settlement_cycle():
    ...
```

---

# 130. Race code naming

```python
def test_race_set_001_double_allocation_never_overallocates():
    ...
```

---

# 131. Property-based companion

Les goldens doivent être complétés par property tests.

Golden :

```text
known representative case
```

Property :

```text
general invariant space
```

---

# 132. Example property — Settlement

Pour toute combinaison :

```text
allocated <= outstanding
```

---

# 133. Example property — Ledger

```text
sum debit == sum credit
```

---

# 134. Example property — Reversal

```text
net original + reversal = 0
```

---

# 135. Example property — Aging

```text
sum buckets = outstanding total
```

---

# 136. Example property — Reconciliation

```text
matched + unmatched = source totals
```

---

# 137. Architecture fitness integration

Règles possibles :

```text
AFF-GOLD-001
critical bounded contexts must expose at least one golden scenario

AFF-GOLD-002
golden fixtures must be versioned

AFF-GOLD-003
golden output changes require explicit review metadata

AFF-RACE-001
production adapters must run critical concurrency suite

AFF-RACE-002
critical race tests must use real PostgreSQL
```

---

# 138. Public API non-coupling

Les golden tests doivent privilégier :

```text
public/application APIs
```

plutôt que des internals fragiles.

---

# 139. Domain-level direct tests

Les invariants purs peuvent être testés directement sur le domaine.

---

# 140. Integration golden

Un golden E2E doit passer via :

```text
AccountingApplication
```

ou la façade publique équivalente.

---

# 141. Golden scenario versioning

Une évolution sémantique volontaire crée :

```text
scenario v2
```

si v1 reste pertinent historiquement.

---

# 142. Scenario retirement

Cycle :

```text
ACTIVE
DEPRECATED
RETIRED
```

---

# 143. No historical deletion

Les golden scenarios utilisés comme release evidence ne doivent pas disparaître sans justification.

---

# 144. Framework context pinning

Chaque golden réglementaire doit pinner :

```text
standard_id
edition
dataset_version
policy_version
```

---

# 145. Generic scenarios

Les goldens génériques évitent de dépendre d'un référentiel spécifique lorsque la règle est universelle.

Exemple :

```text
double-entry balance
```

---

# 146. Regulatory-specific scenario

Un scénario réglementaire peut pinner :

```text
SYSCOHADA 2017
```

si son objectif porte explicitement sur ce référentiel.

---

# 147. Golden safety scenarios

Inclure des tests négatifs :

```text
same account code != semantic equivalence
candidate mapping != executable mapping
family relation != inheritance
unknown relation fails closed
```

---

# 148. Golden error scenarios

Les erreurs publiques importantes peuvent avoir des goldens :

```text
error code
state unchanged
audit behavior
```

---

# 149. Error golden example

```text
post to closed period
```

Expected :

```text
error code = PERIOD_CLOSED
entry remains VALIDATED
no ledger movement
```

---

# 150. Concurrency error semantics

Les conflits doivent produire :

```text
stable error category
```

même si l'exception DB interne varie selon adapter.

---

# 151. Persistence abstraction

Adapter A peut produire :

```text
OptimisticRevisionConflict
```

Adapter B :

```text
UniqueConstraintConflict
```

La public/application API doit normaliser si nécessaire.

---

# 152. Fault injection

Scénarios recommandés :

```text
audit failure
outbox failure
repository save failure
commit failure
dispatcher failure
```

---

# 153. Dispatcher failure

Si le commit a réussi mais la publication échoue :

```text
business state remains committed
outbox remains pending
retry publication
```

---

# 154. Outbox retry golden

Un scénario doit vérifier :

```text
same EventId
multiple delivery attempts
one consumer effect
```

---

# 155. Replay + events

Le replay d'un snapshot ne doit pas republier automatiquement les DomainEvents historiques comme nouveaux effets externes.

---

# 156. Golden performance boundaries

Les goldens fonctionnels ne doivent pas devenir des benchmarks rigides.

Performance est une suite distincte.

---

# 157. Performance smoke companions

Scénarios :

```text
10-line posting
100-line posting
100k ledger
100k trial balance source
large import
```

---

# 158. Data volume not semantics

Un golden métier doit rester petit, lisible et auditable.

---

# 159. Golden documentation

Chaque scénario critique doit disposer de :

```text
purpose
business story
inputs
steps
expected state
expected financial result
expected events
expected controls
```

---

# 160. Human readability

Un expert comptable doit pouvoir comprendre le scénario sans lire le code.

---

# 161. Machine readability

Le même scénario doit posséder une représentation structurée exploitable par les tests.

---

# 162. Scenario registry

Artifact possible :

```text
GOLDEN_SCENARIO_REGISTRY.json
```

---

# 163. Registry fields

```text
scenario_id
version
category
status
owner
test_path
fixture_path
criticality
```

---

# 164. Concurrency registry

```text
CONCURRENCY_SCENARIO_REGISTRY.json
```

---

# 165. Criticality

Valeurs :

```text
CRITICAL
HIGH
MEDIUM
LOW
```

---

# 166. Critical goldens

Minimum :

```text
posting
reversal
O2C
P2P
closing
import
trial balance
financial statements
```

---

# 167. Critical races

Minimum :

```text
double posting
double reversal
posting vs close
double settlement
duplicate import
idempotency claim
```

---

# 168. High-priority races
```text
settlement vs reversal
match acceptance race
import vs close
reference switch vs posting
report publish vs source change
```

---

# 169. Release evidence bundle

Une release peut inclure :

```text
golden scenario manifest
concurrency scenario manifest
golden results
concurrency results
replay results
adapter matrix
```

---

# 170. Qualification summary

Exemple :

```text
Golden:
25/25 PASS

Concurrency:
18/18 PASS

Replay:
12/12 MATCH

Adapters:
InMemory PASS
Django/PostgreSQL PASS
SQLAlchemy/PostgreSQL PASS
```

---

# 171. Non-regression policy

Toute correction d'un bug critique doit ajouter :

```text
regression golden
or
regression concurrency scenario
```

selon la nature du bug.

---

# 172. Bug examples requiring concurrency regression

```text
double posting
negative outstanding
duplicate import
late posting after close
duplicate reversal
```

---

# 173. Bug examples requiring golden regression

```text
wrong balance
wrong financial ratio
wrong mapping
wrong aging bucket
wrong regulatory export
```

---

# 174. Definition of Done — Golden framework

```text
[ ] GoldenScenarioDefinition defined
[ ] scenario registry defined
[ ] fixture governance defined
[ ] semantic checksum discipline defined
[ ] cross-adapter parity defined
[ ] full accounting cycle defined
[ ] critical golden catalog defined
[ ] intentional divergence protocol defined
```

---

# 175. Definition of Done — Concurrency framework

```text
[ ] ConcurrencyScenarioDefinition defined
[ ] allowed outcomes explicit
[ ] forbidden outcomes explicit
[ ] PostgreSQL harness defined
[ ] deterministic barriers defined
[ ] final invariant checks defined
[ ] worker result taxonomy defined
[ ] critical races catalog defined
```

---

# 176. Definition of Done — Release qualification

```text
[ ] all CRITICAL goldens green
[ ] all CRITICAL races green
[ ] no flaky critical race
[ ] cross-adapter golden parity green
[ ] replay checksums green
[ ] evidence bundle generated
```

---

# 177. `ConcurrencyScenarioDefinition`

Concept cible :

```text
ConcurrencyScenarioDefinition
|
+-- scenario_id
+-- version
+-- initial_state
+-- workers
+-- barriers
+-- allowed_outcomes
+-- forbidden_outcomes
+-- final_invariants
+-- required_capabilities
```

---

# 178. Example definition

```text
RACE-SET-001

Initial:
    Receivable outstanding = 100

Worker A:
    Allocate 80

Worker B:
    Allocate 70

Invariant:
    final allocated <= 100

Forbidden:
    150 allocated
```

---

# 179. Golden-to-race traceability

Chaque race doit référencer la capability qu'elle protège.

Exemple :

```text
RACE-SET-001
protects:
    GOLD-SET-001
    Settlement invariant INV-...
```

---

# 180. Scenario-to-spec traceability

Chaque scénario critique référence :

```text
spec
ADR
invariant
public error
```

---

# 181. Scenario ownership

Exemples :

```text
Ledger owns posting/reversal goldens
Subledgers own settlement goldens
Reconciliation owns matching goldens
Closing owns closing goldens
```

La suite transverse agrège les preuves.

---

# 182. No central god-test module

Les tests restent proches de leurs contexts.

Le registry transverse les référence.

---

# 183. Architecture target

```text
                 DOMAIN SPECS
                      │
                      ▼
            GOLDEN SCENARIOS
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
     InMemory     Django/PG     SQLAlchemy/PG
        │             │             │
        └─────────────┼─────────────┘
                      ▼
             SEMANTIC PARITY
                      │
                      ▼
              CONCURRENCY SUITE
                      │
                      ▼
                  REPLAY
                      │
                      ▼
              RELEASE EVIDENCE
```

---

# 184. Initial implementation roadmap

## GOLD-00 — Scenario model & registry

```text
GoldenScenarioDefinition
registry
fixture metadata
```

## GOLD-01 — Ledger core

```text
posting
reversal
trial balance
```

## GOLD-02 — O2C / P2P

```text
receivable
payable
settlement
```

## GOLD-03 — Import

```text
FEC + generic import
```

## GOLD-04 — Closing

```text
close
block
reopen
```

## GOLD-05 — Reconciliation

```text
bank
subledger/GL
ambiguity
```

## GOLD-06 — Reporting / Analysis

```text
statements
ratios
regulatory export
```

## GOLD-07 — Consolidation / Semantic

---

# 185. Concurrency roadmap

## RACE-00 — Harness

```text
barriers
worker coordinator
PostgreSQL fixtures
```

## RACE-01 — Ledger

```text
double posting
double reversal
posting vs close
```

## RACE-02 — Settlement

```text
double settlement
settlement vs reversal
```

## RACE-03 — Import

```text
duplicate import
import vs close
stale plan
```

## RACE-04 — Reconciliation

```text
competing matches
publish vs source refresh
```

## RACE-05 — References / Policies

```text
version switch vs posting
```

## RACE-06 — Downstream snapshots

```text
report
analysis
consolidation
semantic
```

---

# 186. Priorités

| Lot | Priorité |
|---|---:|
| GOLD-00 | P0 |
| GOLD-01 | P0 |
| GOLD-02 | P0 |
| GOLD-03 | P0 |
| GOLD-04 | P0 |
| GOLD-05 | P1 |
| GOLD-06 | P1 |
| GOLD-07 | P2 |
| RACE-00 | P0 |
| RACE-01 | P0 |
| RACE-02 | P0 |
| RACE-03 | P0 |
| RACE-04 | P1 |
| RACE-05 | P1 |
| RACE-06 | P2 |

---

# 187. ADR proposées

| ADR | Décision |
|---|---|
| ADR-GOLD-001 | Les golden scenarios sont des preuves métier versionnées |
| ADR-GOLD-002 | CFA FRA Golden reste un oracle spécialisé, pas le golden framework générique |
| ADR-GOLD-003 | Les goldens comparent la sémantique, pas les détails ORM |
| ADR-GOLD-004 | Les fixtures monétaires n'utilisent jamais float |
| ADR-GOLD-005 | Tout golden output change nécessite une revue explicite |
| ADR-GOLD-006 | Les divergences intentionnelles sont enregistrées |
| ADR-GOLD-007 | Les critical goldens sont exécutés sur les production adapters compatibles |
| ADR-GOLD-008 | Les goldens réglementaires pinent standard, édition et version |
| ADR-GOLD-009 | Les goldens utilisent Clock/ID déterministes |
| ADR-GOLD-010 | Le full accounting cycle devient une preuve E2E canonique |
| ADR-GOLD-011 | Golden et property tests sont complémentaires |
| ADR-GOLD-012 | Les snapshots produits par un golden participent au replay |
| ADR-RACE-001 | Les races critiques sont qualifiées sur PostgreSQL réel |
| ADR-RACE-002 | Les races utilisent des barrières déterministes, pas des sleeps |
| ADR-RACE-003 | Chaque race définit allowed et forbidden outcomes |
| ADR-RACE-004 | Un conflict contrôlé peut constituer un PASS |
| ADR-RACE-005 | Double posting ne produit qu'un effet métier |
| ADR-RACE-006 | Double reversal ne produit qu'une reversal |
| ADR-RACE-007 | Posting vs Close interdit tout posting postérieur au close commit |
| ADR-RACE-008 | Settlement ne peut jamais sur-allouer un outstanding |
| ADR-RACE-009 | Duplicate import ne produit jamais de double effet économique |
| ADR-RACE-010 | Competing reconciliation matches protègent les residuals |
| ADR-RACE-011 | Reference/Policy activation est pinée par opération |
| ADR-RACE-012 | Outbox rollback reste atomique avec business state |
| ADR-RACE-013 | Duplicate event delivery doit être idempotente |
| ADR-RACE-014 | Published snapshots pinent explicitement leur source |
| ADR-RACE-015 | Flaky critical concurrency test bloque une stable |
| ADR-RACE-016 | Cross-adapter concurrency peut varier techniquement mais pas sémantiquement |
| ADR-RACE-017 | Toute correction de race critique ajoute un regression scenario |
| ADR-RACE-018 | Stress tests complètent mais ne remplacent pas les races déterministes |
| ADR-RACE-019 | Concurrency evidence participe aux release gates |
| ADR-RACE-020 | Golden + concurrency + replay forment une chaîne unique de qualification |

---

# 188. Architecture Fitness Functions associées

```text
AFF-GOLD-001
critical bounded contexts expose golden scenarios

AFF-GOLD-002
golden fixtures are versioned

AFF-GOLD-003
golden output changes require explicit review

AFF-RACE-001
production database adapters execute critical races

AFF-RACE-002
critical concurrency tests use a real database

AFF-RACE-003
critical race failures block release qualification
```

---

# 189. Qualification chain

La chaîne cible devient :

```text
UNIT
    ↓
PROPERTY
    ↓
CONTRACT
    ↓
INTEGRATION
    ↓
GOLDEN
    ↓
CONCURRENCY
    ↓
REPLAY
    ↓
RELEASE EVIDENCE
```

---

# 190. Full qualification principle

Pour une capability financière critique, la preuve idéale couvre :

```text
correct in isolation
+
correct on known business scenario
+
correct under race
+
correct across adapters
+
replayable
```

---

# 191. Conclusion

PyAccountingKit possède déjà une stratégie de tests robuste et une baseline CFA FRA utile.

La prochaine étape est de transformer les scénarios les plus importants en un **catalogue transverse de preuves métier et transactionnelles**.

La cible est :

```text
KNOWN ACCOUNTING STORY
        ↓
GOLDEN INPUT
        ↓
DETERMINISTIC EXECUTION
        ↓
EXPECTED FINANCIAL RESULT
        ↓
CONCURRENCY CHALLENGE
        ↓
INVARIANTS STILL HOLD
        ↓
REPLAY MATCHES
        ↓
RELEASE EVIDENCE
```

Les propriétés à protéger sont simples :

```text
one posting
one reversal
no over-allocation
no duplicate import
no late posting after close
no hidden reconciliation mutation
no mixed reference versions
no silent stale snapshot rewrite
```

Le principe final est :

> **Un framework comptable fiable ne doit pas seulement produire le bon résultat dans le happy path ; il doit aussi conserver ce résultat lorsque plusieurs opérations concurrentes tentent de modifier le même état.**