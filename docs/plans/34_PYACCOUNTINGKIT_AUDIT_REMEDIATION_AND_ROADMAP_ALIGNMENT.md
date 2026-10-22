# 34_PYACCOUNTINGKIT_AUDIT_REMEDIATION_AND_ROADMAP_ALIGNMENT.md

# PyAccountingKit — Audit, Remediation & Roadmap Alignment

> **Projet** : PyAccountingKit  
> **Document** : `34_PYACCOUNTINGKIT_AUDIT_REMEDIATION_AND_ROADMAP_ALIGNMENT.md`  
> **Statut** : Document de jonction canonique entre audit, remédiation et roadmap stratégique  
> **Date** : 22 octobre 2026  
> **Baseline auditée** : `main` — commit `259e9ad665941cd6a9545deb3b92f979d40eae35`  
> **Version auditée** : `0.7.0rc1`  
> **Sources de vérité** :
> - `AUDIT_APPROFONDI_PYACCOUNTINGKIT_2026-10-22.md`
> - `PLAN_REMEDIATION_PYACCOUNTINGKIT_2026-10-22.md`
> - `docs/ROADMAP.md`
> - `docs/plans/README.md`
> - specs d’architecture `24 → 32`
> **Langue** : Français

---

# 1. Objet

Ce document relie explicitement trois niveaux de pilotage qui ne doivent plus être confondus :

```text
AUDIT
    ↓
WHAT IS WRONG NOW

REMEDIATION
    ↓
WHAT MUST BE FIXED FIRST

STRATEGIC ROADMAP
    ↓
WHAT WE BUILD NEXT
```

Il fournit la matrice de traçabilité canonique :

```text
Finding / Gap
    ↓
REM-* owner
    ↓
Release gate
    ↓
Future LOT-* dependency
    ↓
Spec 24..32
```

---

# 2. Pourquoi ce document est nécessaire

Avant l’audit du 22 octobre 2026, la trajectoire implicite était :

```text
0.7.0rc1
    ↓
0.7.0 stable
    ↓
architecture hardening
```

L’audit modifie cette séquence.

La trajectoire correcte devient :

```text
0.7.0rc1
    ↓
audit findings
    ↓
REM-00..REM-10
    ↓
requalification
    ↓
release decision
    ↓
new RC if required
    ↓
0.7.0 stable
    ↓
LOT-39..LOT-46
```

---

# 3. Positionnement des quatre documents de pilotage

## 3.1 Audit

`AUDIT_APPROFONDI_PYACCOUNTINGKIT_2026-10-22.md`

Rôle :

```text
diagnostic
evidence
risk classification
reproduction
```

Il répond à :

> **quels écarts existent sur la baseline auditée ?**

---

# 4. Plan de remédiation

`PLAN_REMEDIATION_PYACCOUNTINGKIT_2026-10-22.md`

Rôle :

```text
corrective sequencing
ownership
validation strategy
migration impact
release exit criteria
```

Il répond à :

> **dans quel ordre et avec quelles preuves corriger les écarts ?**

---

# 5. Roadmap produit

`docs/ROADMAP.md`

Rôle :

```text
product milestones
release train
LOT-*
architecture gates
future capabilities
```

Il répond à :

> **quels blocs fonctionnels et architecturaux constituent l’évolution du produit ?**

---

# 6. Next Steps Plan

`33_PYACCOUNTINGKIT_NEXT_STEPS_IMPLEMENTATION_PLAN.md`

Rôle :

```text
operational bridge
current execution order
remediation first
strategic roadmap second
```

Il répond à :

> **quelle est la prochaine séquence exécutable ?**

---

# 7. Décision de gouvernance

La hiérarchie de pilotage devient :

```text
current verified repository state
        ↓
audit findings
        ↓
remediation plan
        ↓
release qualification
        ↓
strategic roadmap
```

Une spec future ne peut pas être utilisée pour masquer un défaut présent.

Un défaut présent ne doit pas non plus invalider une bonne cible architecturale future.

---

# 8. Deux horizons explicitement séparés

## Horizon A — Tactical Remediation

```text
REM-00 → REM-10
```

Objectif :

```text
repair
stabilize
prove
```

---

# 9. Horizon B — Strategic Evolution

```text
LOT-39 → LOT-46
```

Objectif :

```text
enforce
generalize
evolve
extend
```

---

# 10. Principe cardinal

```text
REM-* fixes existing semantics

LOT-* builds future architecture
```

---

# 11. Baseline auditée

```text
branch: main
commit: 259e9ad665941cd6a9545deb3b92f979d40eae35
version: 0.7.0rc1
```

---

# 12. Scope de l’audit

L’audit identifie :

```text
F01 → F27
```

et :

```text
A01 → A03
```

---

# 13. Findings P1/P2 — lecture stratégique

Les findings peuvent être regroupés ainsi :

```text
IDENTITY / ENTITY SCOPE
F01 F02 F03 F04 F13 F18

POSTING / IMMUTABILITY / IDEMPOTENCY
F10 F11 F23 F24

CLOSING / OPENING
F05 F06 F07 F08 F09

EVIDENCE / SNAPSHOT / TRACE
F14 F20 A03

ACCOUNTING FIDELITY
F12 F15 F16 F21

REFERENCE / PUBLICATION
F19 F22

PUBLIC API
F17 A02

CI / RELEASE QUALIFICATION
F25 F26 F27

PERSISTENT SUBLEDGERS
A01
```

---

# 14. Mapping global Audit → Remediation

| Audit | Remediation owner |
|---|---|
| F01 | REM-02 |
| F02 | REM-02 |
| F03 | REM-02 |
| F04 | REM-02 |
| F05 | REM-05 |
| F06 | REM-05 |
| F07 | REM-05 |
| F08 | REM-05 |
| F09 | REM-05 |
| F10 | REM-03 |
| F11 | REM-03 |
| F12 | REM-06 |
| F13 | REM-02 |
| F14 | REM-04 |
| F15 | REM-06 |
| F16 | REM-06 |
| F17 | REM-08 |
| F18 | REM-02 |
| F19 | REM-07 |
| F20 | REM-04 |
| F21 | REM-06 |
| F22 | REM-07 |
| F23 | REM-03 |
| F24 | REM-03 |
| F25 | REM-01 |
| F26 | REM-01 |
| F27 | REM-01 |
| A01 | REM-09 |
| A02 | REM-08 |
| A03 | REM-04 |

---

# 15. Mapping Remediation → Strategic Roadmap

| Remediation | Future capability prepared |
|---|---|
| REM-00 | all future lots |
| REM-01 | LOT-39, LOT-42 |
| REM-02 | LOT-40, LOT-41 |
| REM-03 | LOT-40, LOT-42, LOT-44 |
| REM-04 | LOT-40, LOT-41 |
| REM-05 | LOT-42, LOT-44 |
| REM-06 | LOT-41 |
| REM-07 | LOT-41 |
| REM-08 | `0.9.x` API freeze |
| REM-09 | stable persistent subledger capability |
| REM-10 | authorizes strategic roadmap resumption |

---

# 16. Mapping Strategic Lot → Spec

| Lot | Spec |
|---|---|
| LOT-39 | `24_ARCHITECTURE_FITNESS_FUNCTIONS` |
| LOT-40 | `25_DOMAIN_EVENTS_CAUSALITY_AND_EVENT_ENVELOPE` |
| LOT-41 | `26_REPRODUCIBILITY_AND_COMPUTATION_MANIFESTS` |
| LOT-42 | `27_GOLDEN_ACCOUNTING_AND_CONCURRENCY_SCENARIOS` |
| LOT-43 | `28_TESTING_TOOLKIT_ARCHITECTURE` |
| LOT-44 | `30_UNCERTAINTY_RECOVERY_AND_EXTERNAL_EFFECTS` |
| LOT-45 | `29_DOMAIN_FIRST_PACKAGE_TOPOLOGY_AND_MIGRATION` |
| LOT-46 | `31_FINANCIAL_SEMANTIC_LAYER_ARCHITECTURE` |
| governance | `32_ARCHITECTURE_STYLE_DDD_HEXAGONAL_CLEAN_VS_MVC` |

---

# 17. F01 — AccountId vs AccountCode

## Audit meaning

Le posting utilise une résolution incohérente entre :

```text
AccountId
AccountCode
```

## Remediation

```text
REM-02
```

## Strategic impact

Prépare :

```text
LOT-40
LOT-41
```

Pourquoi :

```text
event identity
manifest identity
replay identity
```

doivent être bâtis sur des identifiants comptables corrects.

---

# 18. F02 / F03 / F04 — Entity Scope Integrity

Ces findings expriment le même risque systémique :

```text
cross-entity mutation
cross-entity import
cross-entity read relabeling
```

## Remediation owner

```text
REM-02
```

## Future influence

```text
LOT-40 event entity scope
LOT-41 manifest entity scope
LOT-42 golden multi-entity scenarios
```

---

# 19. F10 — POSTED immutability

## Remediation

```text
REM-03
```

## Strategic dependency

LOT-40 ne doit pas produire de nouveaux DomainEvents sur un modèle dont l’historique POSTED peut encore être réécrit.

LOT-42 doit ensuite transformer cette correction en :

```text
golden immutability scenarios
repository contract tests
```

---

# 20. F11 — Idempotency payload conflict

## Remediation

```text
REM-03
```

## Future dependency

C’est un prérequis direct de :

```text
LOT-44
```

car le modèle :

```text
UNCERTAIN
retry
reconciliation
```

ne peut pas être fiable si l’idempotence actuelle accepte :

```text
same key
different command
```

---

# 21. F14 — Audit/Outbox deep immutability

## Remediation

```text
REM-04
```

## Future dependency

Prépare :

```text
LOT-40 Event Envelope
LOT-41 Computation Manifests
```

Une preuve mutable invalide :

```text
causality
auditability
reproducibility
```

---

# 22. F15 — Balance checksum incomplet

## Remediation

```text
REM-06
```

## Strategic consequence

LOT-41 doit attendre :

```text
currency identity
account identity
checksum versioning
```

avant de généraliser les manifests.

---

# 23. F20 — Snapshot mutable après scellement

## Remediation

```text
REM-04
```

## Strategic consequence

Les principes de `26_REPRODUCIBILITY` sont corrects.

Mais ils ne doivent pas être implémentés sur :

```text
snapshot replay without integrity verification
```

---

# 24. F05/F06/F07/F08/F09 — Closing cluster

Ces findings constituent un cluster transactionnel cohérent.

```text
control presence
balance freshness
canonical opening posting
proof atomicity
read dependency concurrency
```

## Remediation

```text
REM-05
```

## Future mapping

```text
LOT-42
    closing golden/race

LOT-44
    retry / uncertain closing semantics
```

---

# 25. F12/F16/F21 — Accounting fidelity

Ces findings concernent la fidélité sémantique et numérique :

```text
entry type
allocation conservation
sign presentation
```

## Remediation

```text
REM-06
```

Ils doivent être corrigés avant que leurs résultats soient utilisés comme :

```text
golden oracle
manifest output
semantic-layer metric
```

---

# 26. F19/F22 — Reference & Publication Safety

## Remediation

```text
REM-07
```

Ils préparent :

```text
LOT-41
```

car un manifest reproductible doit pointer vers :

```text
valid reference graph
valid publication state
```

---

# 27. F17/A02 — Public API

## Remediation

```text
REM-08
```

Ce lot doit fermer les gaps :

```text
typed requests
typed responses
public error translation
ORM neutrality
configured operation semantics
```

---

# 28. Relation avec `0.9.x`

REM-08 prépare directement :

```text
0.9.x API / Schema Freeze
```

Le freeze ne doit pas figer :

```text
object
**parameters
implicit service contracts
```

comme API stable par défaut.

---

# 29. A01 — Persistent Subledgers

A01 est différent des autres points.

Il ne décrit pas uniquement un bug.

Il décrit une capacité structurelle incomplète :

```text
domain services exist
but full persistent application chain is missing
```

---

# 30. Decision point for A01

Deux options doivent être explicitement supportées.

## Option A — A01 in 0.7 scope

Alors :

```text
REM-09 required before stable
```

## Option B — A01 deferred

Alors :

```text
0.7 release scope explicitly excludes
full production persistent subledger capability
```

A01 reste :

```text
OPEN
```

sans bloquer un périmètre 0.7 explicitement plus étroit.

---

# 31. No false closure

A01 ne peut pas être déclaré résolu par :

```text
documentation
stub
in-memory service
domain dataclass
```

Il exige une chaîne :

```text
application
+
ports
+
persistence
+
transaction
+
real DB qualification
```

---

# 32. F25/F26/F27 — Qualification Trust

Ces findings sont prioritaires très tôt.

Pourquoi :

```text
we cannot prove fixes
with an unreliable qualification pipeline
```

---

# 33. REM-01 before large remediation

REM-01 doit démarrer immédiatement après REM-00.

Objectif :

```text
make proof infrastructure trustworthy
```

---

# 34. Exact SHA rule

Toute preuve de release doit être reliée à :

```text
exact candidate SHA
```

Interdit :

```text
latest green run
on another revision
```

---

# 35. PostgreSQL rule

En qualification stricte :

```text
skipped required module
=
failure
```

---

# 36. Golden evolution strategy

Les reproductions de l’audit ne sont pas fusionnées telles quelles comme tests définitifs.

Elles servent à créer :

```text
corrective expected-behavior tests
```

Puis ces tests peuvent être promus vers :

```text
contract
golden
race
property
replay
```

selon leur nature.

---

# 37. Audit test lifecycle

```text
BUG REPRODUCTION
    ↓
EXPECTED BEHAVIOR TEST
    ↓
FIX
    ↓
CONTRACT / GOLDEN / RACE
    ↓
PERMANENT QUALIFICATION
```

---

# 38. Mapping findings → future test classes

| Findings | Future test family |
|---|---|
| F01/F02/F03/F04/F18 | entity / identity contracts |
| F05/F06/F07/F08/F09 | closing golden + races |
| F10/F23/F24 | repository lifecycle contracts |
| F11 | idempotency contracts |
| F12/F16/F21 | property + golden |
| F13 | read-side contract |
| F14/F20 | evidence / replay |
| F15 | checksum property / replay |
| F17 | public API contract |
| F19 | reference graph property |
| F22 | publication state-machine |
| F25/F26/F27 | release tooling tests |

---

# 39. Relationship with LOT-39

LOT-39 is not the first remediation task.

But some of its mechanisms may be used during remediation.

Example :

```text
architecture check
CI rule
AST guard
```

can be introduced tactically if needed.

However:

```text
REM-01
!=
full LOT-39
```

---

# 40. Relationship with LOT-43

Likewise :

```text
builders
assertions
deterministic fixtures
```

can be extracted during remediation.

But stabilizing a complete public:

```text
pyaccountingkit.testing
```

surface is not a prerequisite for closing a P1.

---

# 41. Relationship with LOT-40

LOT-40 should start only after the event source semantics are trustworthy.

Minimum prerequisites :

```text
REM-03
REM-04
LOT-39 / testing foundations as applicable
```

---

# 42. Relationship with LOT-41

LOT-41 should start only after :

```text
snapshot integrity
checksum correctness
publication safety
```

are established.

Minimum remediation dependencies :

```text
REM-04
REM-06
REM-07
```

---

# 43. Relationship with LOT-42

LOT-42 is the most naturally incremental future lot.

It may absorb remediation outputs progressively.

Examples :

```text
F09
→ RACE close vs post

F10
→ GOLD immutable posted entry

F11
→ idempotency collision scenario

F22
→ publication lifecycle scenario
```

---

# 44. Relationship with LOT-44

LOT-44 should not generalize recovery semantics until existing idempotence and closing behavior are corrected.

Minimum dependencies :

```text
REM-03
REM-05
LOT-40
LOT-41
LOT-42
```

---

# 45. Relationship with LOT-45

Domain-First migration must remain structurally conservative during remediation.

Rule :

```text
fix semantics first
move packages second
```

---

# 46. Allowed LOT-45 work before 1.0
Only foundations :

```text
inventory
context ownership
minimal shared kernel rules
migration map
fitness constraints
```

---

# 47. Forbidden migration behavior during remediation

Avoid mixing :

```text
bug fix
+
package move
+
public API redesign
+
persistence migration
```

in one PR.

---

# 48. Relationship with LOT-46

The Financial Semantic Layer depends on trusted upstream semantics.

It should not consume:

```text
incorrect allocations
mutable snapshots
unsafe publications
ambiguous account identity
```

---

# 49. Minimum upstream trust for LOT-46

```text
REM-02 closed
REM-04 closed
REM-06 closed
REM-07 closed
LOT-41 available
Reporting/Analysis stable
```

---

# 50. Release decision model

After REM-10 :

```text
candidate
    ↓
evaluate unresolved items
```

Possible outcomes :

```text
PROMOTE TO NEW RC
BLOCK
REDUCE SCOPE
MOVE TO NEW MILESTONE
```

---

# 51. Stable decision is not automatic

REM-10 does not mean :

```text
always publish 0.7.0
```

It means :

```text
we now have enough evidence
to make the release decision
```

---

# 52. SemVer decision

If fixes remain compatible with the intended 0.7 surface :

```text
new 0.7 RC
→ stable
```

If fixes materially alter public contracts :

```text
select appropriate milestone
```

Do not force the stable number.

---

# 53. G5 relation

G5 remains necessary.

But :

```text
G5
+
open accounting P1
=
NO STABLE
```

---

# 54. G3 relation

G3 is now strict.

```text
required PostgreSQL suites skipped
=
NO QUALIFICATION
```

---

# 55. Evidence classes

For each remediation finding, retain:

```text
baseline evidence
corrective test
candidate evidence
adapter evidence
migration evidence
release evidence
```

---

# 56. Evidence chain

```text
Finding
    ↓
Corrective Test
    ↓
Fix Commit
    ↓
PR
    ↓
CI
    ↓
Adapter Qualification
    ↓
REM Status
    ↓
Release Candidate
```

---

# 57. Remediation status model

Canonical statuses :

```text
OPEN
IN_PROGRESS
FIXED_UNVERIFIED
VERIFIED
BLOCKED
```

---

# 58. VERIFIED semantics

A finding becomes VERIFIED only if :

```text
correct behavior proven
+
required adapters proven
+
candidate SHA known
+
migration/replay handled when applicable
```

---

# 59. Proposed remediation registry

Target artifact :

```text
docs/audits/REMEDIATION_2026_10_STATUS.json
```

Recommended fields :

```text
finding_id
remediation_lot
baseline_sha
candidate_sha
status
owner
validator
corrective_test
adapter_evidence
migration_evidence
commit
PR
CI
residual_risk
```

---

# 60. Proposed remediation implementation plan

Target canonical path :

```text
docs/plans/REMEDIATION_2026_10_PLAN.md
```

This document can be generated from the current remediation plan without changing its semantics.

---

# 61. Canonical reading order

After these files are integrated into GitHub :

```text
docs/ROADMAP.md
    ↓
docs/audits/AUDIT_APPROFONDI_PYACCOUNTINGKIT_2026-10-22.md
    ↓
docs/plans/REMEDIATION_2026_10_PLAN.md
    ↓
docs/audits/REMEDIATION_2026_10_STATUS.json
    ↓
docs/plans/README.md
    ↓
33_NEXT_STEPS
    ↓
34_ALIGNMENT
```

---

# 62. Immediate execution sequence

```text
STEP 1
REM-00

STEP 2
REM-01

STEP 3
REM-02 first slice
```

---

# 63. REM-00 immediate tasks

```text
compare HEAD vs audit baseline
reproduce remaining findings
create status registry
convert reproductions into corrective tests
map impacted contracts
```

---

# 64. REM-01 immediate tasks

```text
fix Nightly test collection
fix gh release repository context
make strict PostgreSQL execution mandatory
bind qualification to exact candidate SHA
```

---

# 65. First REM-02 slice

Start with :

```text
AccountId != AccountCode
```

Then :

```text
cross-entity posting
cross-entity import
trial balance entity verification
ledger account identity / currency
duplicate AccountId protection
```

---

# 66. Why this order

Because :

```text
correctness evidence
must become trustworthy
before scaling the correction campaign
```

---

# 67. PR strategy

Recommended :

```text
PR-REM-00.1
registry + corrective test scaffolding

PR-REM-01.1
Nightly collection

PR-REM-01.2
strict PostgreSQL qualification

PR-REM-02.1
AccountId vs AccountCode

PR-REM-02.2
entity scope
```

---

# 68. PR rule

Each PR should contain :

```text
findings addressed
bug trigger
expected behavior
contract impact
migration impact
tests
remaining risk
```

---

# 69. No mass remediation PR

Avoid :

```text
fix all audit issues
```

in one change.

---

# 70. Migration rule

If a remediation changes :

```text
checksum
idempotency schema
snapshot schema
port signature
database schema
public response
```

then :

```text
migration / compatibility decision
```

is mandatory.

---

# 71. Historical evidence rule

Missing historical evidence must not be fabricated.

If reconstructed later :

```text
new timestamp
new provenance
new status
```

must be explicit.

---

# 72. Accounting repair rule

POSTED historical accounting must not be edited silently.

Corrections use :

```text
reversal
adjustment
replacement
```

according to the applicable rule.

---

# 73. Stop-the-line conditions during remediation

Any of the following blocks progression :

```text
cross-entity accounting effect
posted mutation
closing without valid evidence
checksum mismatch ignored
snapshot corruption accepted
required PG suite skipped
idempotency collision accepted
publication without controls
```

---

# 74. Roadmap resume gate

Strategic work resumes only when :

```text
REM-10 completed for chosen release scope
```

and the release decision is documented.

---

# 75. Full remediation vs scoped release

Two distinct statements must never be confused.

```text
0.7 release scope qualified
```

does not necessarily mean :

```text
all A01..A03 globally closed
```

if some structural capability is explicitly deferred.

---

# 76. Scope transparency rule

Any deferred gap must be:

```text
named
documented
kept OPEN
excluded from claimed capability
```

---

# 77. Example — A01 deferred

Valid wording :

```text
0.7.0 qualifies regulatory production capabilities.
Persistent subledger end-to-end production capability remains outside this release scope.
A01 remains OPEN.
```

Invalid wording :

```text
all PyAccountingKit production capabilities qualified
```

---

# 78. Relationship with public claims

README, CHANGELOG, compatibility matrix and release notes must describe only :

```text
qualified delivered capability
```

not aspirational architecture.

---

# 79. Documentation synchronization

At each major remediation closure, update as applicable :

```text
docs/ROADMAP.md
docs/plans/README.md
remediation registry
CHANGELOG
public manifests
release qualification report
```

---

# 80. Final alignment matrix

| Layer | Current role | Next action |
|---|---|---|
| Audit | factual baseline diagnosis | preserve evidence |
| Remediation | tactical correction plan | execute REM-00..10 |
| Roadmap | strategic product evolution | paused behind remediation gate |
| Specs 24..32 | future architecture target | retain unchanged unless implementation reveals contradiction |
| LOT-39..46 | strategic implementation | resume after remediation |
| Release 0.7 | regulatory qualification | requalify before stable |

---

# 81. Canonical flow

```text
AUDIT
  │
  ▼
FINDINGS
  │
  ▼
REM LOT
  │
  ▼
CORRECTIVE TEST
  │
  ▼
FIX
  │
  ▼
CROSS-ADAPTER PROOF
  │
  ▼
REM-10
  │
  ▼
RELEASE DECISION
  │
  ├── BLOCK
  ├── REDUCE SCOPE
  ├── NEW RC
  └── STABLE
          │
          ▼
STRATEGIC LOTS
```

---

# 82. Strategic flow after remediation

```text
LOT-39 Architecture Fitness
    ↓
LOT-43 Testing Toolkit
    ↓
LOT-40 Domain Events
    ↓
LOT-41 Reproducibility
    ↓
LOT-42 Golden / Concurrency
    ↓
LOT-44 Recovery
    ↓
0.8.x
    ↓
0.9.x API / Schema Freeze
    ↓
1.0.0
    ↓
LOT-45 Domain-First Migration
LOT-46 Financial Semantic Layer
```

---

# 83. Definition of Done — alignment itself

This alignment is complete when :

```text
[ ] audit exists in repository
[ ] remediation plan exists in repository
[ ] remediation registry exists
[ ] ROADMAP references REM overlay
[ ] plans README references REM overlay
[ ] specs 24..32 are indexed
[ ] LOT-39..46 are indexed
[ ] current active lot is REM-00
[ ] no document still claims immediate 0.7 stable promotion
```

---

# 84. Decision summary

The project now has a clean separation :

```text
AUDIT
=
truth about current baseline

REMEDIATION
=
required correction work

ROADMAP
=
future product evolution
```

---

# 85. Final conclusion

The audit does not invalidate the new architecture roadmap.

It changes its execution order.

The canonical rule is now :

```text
FIX WHAT EXISTS
        ↓
PROVE IT
        ↓
RELEASE IT
        ↓
EVOLVE IT
```

The immediate next work remains :

```text
REM-00
    ↓
REM-01
    ↓
REM-02 first slice
```

Only after the remediation gate is satisfied does the strategic roadmap resume with :

```text
LOT-39 → LOT-46
```

This document is therefore the permanent bridge between:

```text
finding
remediation
release
architecture evolution
```