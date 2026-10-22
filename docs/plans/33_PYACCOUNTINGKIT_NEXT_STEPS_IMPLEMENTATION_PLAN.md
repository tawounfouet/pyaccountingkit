# 33_PYACCOUNTINGKIT_NEXT_STEPS_IMPLEMENTATION_PLAN.md

# PyAccountingKit — Next Steps Implementation Plan
## Version révisée après audit du 22 octobre 2026

> **Projet** : PyAccountingKit  
> **Document** : `33_PYACCOUNTINGKIT_NEXT_STEPS_IMPLEMENTATION_PLAN.md`  
> **Statut** : Plan d’action exécutable — révisé après audit approfondi  
> **Date** : 22 octobre 2026  
> **Baseline auditée** : `main` — commit `259e9ad665941cd6a9545deb3b92f979d40eae35`  
> **Version auditée** : `0.7.0rc1`  
> **Sources de pilotage** :
> - `AUDIT_APPROFONDI_PYACCOUNTINGKIT_2026-10-22.md`
> - `PLAN_REMEDIATION_PYACCOUNTINGKIT_2026-10-22.md`
> - specs d’architecture `24 → 32`
> **Langue** : Français

---

# 1. Objet

Ce document remplace la séquence initiale :

```text
0.7.0rc1
→ 0.7.0 stable
→ LOT-39...
```

par une trajectoire corrigée tenant compte de l’audit approfondi du 22 octobre 2026.

Le principe devient :

```text
AUDIT
    ↓
REMEDIATION
    ↓
REQUALIFICATION
    ↓
RELEASE DECISION
    ↓
0.7.0 stable si les conditions applicables sont satisfaites
    ↓
STRATEGIC ROADMAP
```

---

# 2. Décision de pilotage

La promotion stable de `0.7.0` est suspendue tant que les défauts P1 applicables au périmètre de release ne sont pas corrigés et qualifiés.

Les contrôles externes G5 restent requis, mais :

```text
G5 green
!=
accounting integrity proven
```

La fermeture des contrôles GitHub ne remplace donc pas la remédiation métier.

---

# 3. Deux plans complémentaires

PyAccountingKit possède désormais deux plans distincts.

## 3.1 Remediation Plan

```text
REM-00 → REM-10
```

Objectif :

```text
réparer
stabiliser
qualifier
l’existant
```

## 3.2 Strategic Roadmap

```text
LOT-39 → LOT-46
```

Objectif :

```text
faire évoluer
l’architecture cible
après stabilisation
```

---

# 4. Relation entre les deux

```text
                    CURRENT
                  PyAccountingKit
                     0.7.0rc1
                         │
                         ▼
               ┌─────────────────┐
               │ AUDIT FINDINGS  │
               │ F01 → F27       │
               │ A01 → A03       │
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │ REMEDIATION     │
               │ REM-00 → REM-10 │
               └────────┬────────┘
                        │
                        ▼
                 RELEASE DECISION
                        │
                        ▼
                   0.7.x stable
                        │
                        ▼
               STRATEGIC ROADMAP
                        │
      ┌─────────────────┼─────────────────┐
      ▼                 ▼                 ▼
    LOT-39            LOT-40            LOT-41...
```

---

# 5. Baseline de l’audit

L’audit porte sur :

```text
branch: main
commit: 259e9ad665941cd6a9545deb3b92f979d40eae35
version: 0.7.0rc1
```

Il identifie :

```text
27 findings
F01 → F27

3 structural gaps
A01 → A03
```

---

# 6. Catégories critiques identifiées

Les principaux risques concernent :

```text
identity / account scope
entity isolation
POSTED immutability
idempotency
closing atomicity
snapshot integrity
checksum fidelity
reporting arithmetic
publication state
CI / qualification reliability
```

---

# 7. Nouvelle macro-roadmap

```text
0.7.0rc1
    ↓
REM-00 Baseline / Registry
    ↓
REM-01 Qualification Reliability
    ↓
REM-02 Identity / Scope / Read-Side
    ↓
REM-03 Posting / Repositories
    ↓
REM-04 Immutable Evidence / Traceability
    ↓
REM-06 Calculation / Checksums
    ↓
REM-05 Closing / Opening Atomicity
    ↓
REM-07 Safe References / Publication
    ↓
REM-08 Public Contracts / Application Services
    ↓
REM-09 Persistent Subledgers
    ↓
REM-10 Transverse Qualification
    ↓
Release Decision
    ↓
New RC if required
    ↓
0.7.0 stable
    ↓
LOT-39 → LOT-46
```

---

# 8. Pourquoi REM-06 avant REM-05 dans l’ordre opérationnel

REM-05 peut être conçu avant REM-06.

Cependant sa qualification définitive dépend notamment de :

```text
balance checksum semantics
currency identity
account identity
evidence integrity
```

corrigées dans REM-06.

---

# 9. REM-00 — Baseline et registre de remédiation

## Objectif

Transformer l’audit en chantier vérifiable.

Travaux :

```text
freeze baseline
compare current HEAD
reproduce remaining findings
create remediation registry
convert audit reproductions into corrective tests
map impacted contracts
```

---

# 10. Registry cible

Créer :

```text
docs/audits/REMEDIATION_2026_10_STATUS.json
```

Champs :

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

# 11. Status lifecycle

```text
OPEN
IN_PROGRESS
FIXED_UNVERIFIED
VERIFIED
BLOCKED
```

---

# 12. Règle de clôture

```text
documentation updated
```

ne suffit pas à produire :

```text
VERIFIED
```

Un finding n’est fermé que lorsque :

```text
behavior fixed
+
corrective test
+
applicable adapter evidence
+
candidate SHA
```

sont présents.

---

# 13. REM-01 — Qualification et workflows fiables

Findings :

```text
F25
F26
F27
```

Objectif :

```text
make qualification trustworthy
before using it as evidence
```

---

# 14. REM-01 — Travaux prioritaires

Corriger :

```text
Nightly collection
release repository context
strict PostgreSQL qualification
```

---

# 15. PostgreSQL gate

En mode strict :

```text
missing DB config
→ FAIL

DB unavailable
→ FAIL

required module skipped
→ FAIL

zero tests collected
→ FAIL

only one PostgreSQL adapter executed
→ FAIL

evidence for another SHA
→ FAIL
```

---

# 16. Qualification validante

Seul :

```text
Django/PostgreSQL GREEN
+
SQLAlchemy/PostgreSQL GREEN
+
exact candidate SHA
```

constitue une preuve G3 valide.

---

# 17. REM-02 — Identités, scope et read-side

Findings :

```text
F01
F02
F03
F04
F13
F18
```

Objectif :

```text
restore stable identity semantics
and entity isolation
```

---

# 18. REM-02 — Principes

```text
AccountId
!=
AccountCode
```

```text
entity scope
must be checked
inside transaction
```

```text
currency
must be explicit
```

---

# 19. Correctifs REM-02

```text
posting resolves by AccountId
cross-entity proposal posting rejected
import plan scope enforced
trial balance checks period/entity
general ledger uses stable account identity
chart rejects duplicate AccountId
```

---

# 20. Qualification REM-02

Tester :

```text
same codes across two entities
opaque AccountIds
EUR
USD
XAF
cross-entity posting
cross-entity import
historic chart versions
```

sur :

```text
InMemory
Django/PostgreSQL
SQLAlchemy/PostgreSQL
```

---

# 21. REM-03 — Posting, repositories et idempotence

Findings :

```text
F10
F11
F23
F24
```

Objectif :

```text
make lifecycle and immutability explicit
```

---

# 22. Posting lifecycle attendu

```text
DRAFT
    ↓
VALIDATED
    ↓
POSTED
    ↓
REVERSED
```

Une écriture persistée VALIDATED doit pouvoir être postée avec sa vraie révision.

---

# 23. POSTED immutability

Après POSTED, figer :

```text
lines
amounts
accounts
entry date
journal
period
classification
```

Les corrections passent par :

```text
reversal
replacement
```

et non :

```text
rewrite
```

---

# 24. Idempotency

La clé doit être associée à :

```text
entity
operation
canonical command fingerprint
durable result
```

Différencier :

```text
identical replay
payload collision
processing in progress
```

---

# 25. REM-04 — Preuves immuables et traçabilité

Findings :

```text
F14
F20
A03
```

Objectif :

```text
make evidence immutable and durable
```

---

# 26. Deep immutability

Corriger :

```text
AuditEvent payload
OutboxRecord payload
ReferenceNode attributes
ReferenceSnapshot content
```

Une dataclass `frozen=True` contenant un `dict` mutable ne constitue pas une preuve immutable.

---

# 27. Durable proposal trace

La trace :

```text
proposal
source
policy versions
chart/version
snapshot
resolved accounts
journal entry
actor/context
```

doit être enregistrée dans la même frontière transactionnelle que le posting.

---

# 28. REM-06 — Exactitude des calculs et empreintes

Findings :

```text
F12
F15
F16
F21
```

Objectif :

```text
restore accounting semantic fidelity
```

---

# 29. EntryType

Ne plus perdre :

```text
ADJUSTING
DEPRECIATION
...
```

lors de :

```text
Proposal
→ JournalEntry
```

---

# 30. Balance checksum

Le checksum doit inclure les coordonnées significatives :

```text
entity
period
variant
currency
currency exponent
AccountId
amounts
relevant chart/reference coordinates
```

---

# 31. Checksum versioning

Introduire :

```text
checksum_schema_version
```

ou mécanisme équivalent.

Ne jamais réécrire silencieusement les preuves historiques.

---

# 32. Allocation arithmetic

Éviter :

```text
0.01 × 50%
+
0.01 × 50%
=
0.02
```

La stratégie doit conserver le total par une allocation déterministe du reliquat.

---

# 33. Reporting signs

Séparer :

```text
economic value
calculation value
presentation value
```

pour éviter une double application des conventions de signe.

---

# 34. REM-05 — Clôture transactionnelle et à-nouveaux

Findings :

```text
F05
F06
F07
F08
F09
```

Objectif :

```text
make closing fail-closed
atomic
replay-safe
```

---

# 35. Closing gate

Un contrôle obligatoire doit être :

```text
present
PASS
correct period
correct version
correct accounting revision
```

Sinon :

```text
close rejected
```

---

# 36. Closing transaction

La transaction doit inclure :

```text
period state
opening entries
closing evidence
audit
outbox
idempotency
```

---

# 37. Opening entries

Les à-nouveaux doivent passer par :

```text
canonical Posting engine
```

et non être injectés directement en état :

```text
POSTED
```

---

# 38. Closing concurrency

Tester :

```text
posting vs close
double close
retry after lost response
read dependencies
```

avec entrelacements déterministes.

---

# 39. REM-07 — Références sûres et publication validée

Findings :

```text
F19
F22
```

---

# 40. Reference hierarchy

Refuser :

```text
cycles
self cycles
orphans
mixed incompatible editions
```

---

# 41. Report lifecycle

Un résultat calculé devient :

```text
DRAFT
```

par défaut.

Puis :

```text
DRAFT
→ VALIDATED
→ PUBLISHED
```

via des use cases explicites.

---

# 42. Publication conditions

Avant PUBLISHED :

```text
controls PASS
source fresh
definition pinned
mapping pinned
evidence durable
```

---

# 43. REM-08 — Contrats publics et services applicatifs

Findings :

```text
F17
A02
```

Objectif :

```text
make public API real
typed
stable
framework-neutral
```

---

# 44. Public contracts

Remplacer progressivement :

```text
**parameters: object
→ object
```

par :

```text
typed request
typed response
stable public errors
```

---

# 45. Framework neutrality

Adopter une liste positive de :

```text
DTO
Value Objects
serializable primitives
```

et rejeter :

```text
ORM
Session
QuerySet
arbitrary iterator
unknown object graph
```

---

# 46. REM-09 — Auxiliaires persistants

Structural gap :

```text
A01
```

Objets déjà présents :

```text
Receivable
Payable
Settlement
DueItem
Allocation
Matching
Aging
```

Gap :

```text
no complete persistent application chain
```

---

# 47. REM-09 — Travaux

Créer :

```text
repositories
ports
use cases
persistence
migrations
transaction boundaries
public operations
```

pour :

```text
receivables/payables
settlements
allocations
matching
aging
reversal evidence
```

---

# 48. Scope decision for A01

Deux options sont possibles.

## Option A — fermer A01 avant stable

Alors :

```text
0.7.0 stable
```

représente une qualification plus large.

## Option B — différer A01

Possible uniquement si :

```text
release scope explicitly excludes
full persistent subledger production capability
```

Dans ce cas :

```textA01 remains OPEN
```

et la remédiation globale reste incomplète.

---

# 49. REM-10 — Qualification transverse

REM-10 décide si une release peut être promue.

---

# 50. Matrice minimale

| Famille | InMemory | Django/PostgreSQL | SQLAlchemy/PostgreSQL |
|---|---|---|---|
| Scope / identities | Required | Required | Required |
| Persistence lifecycle | Required | Required | Required |
| Idempotency | Required | Required | Required |
| Atomic failure | Required | Required | Required |
| Closing concurrency | Deterministic | Real DB | Real DB |
| Subledgers | Required if in scope | Required | Required |
| Replay / evidence | Required | Required | Required |

---

# 51. REM-10 — Exit criteria

```text
[ ] F01..F27 fixed and verified on candidate SHA
[ ] applicable A01..A03 resolved or explicitly scoped
[ ] 0 open P1 in release scope
[ ] 0 unjustified mandatory skip
[ ] InMemory/DjangoPG/SQLAlchemyPG parity
[ ] migrations qualified
[ ] replay qualified
[ ] manifests aligned
[ ] README / CHANGELOG aligned
[ ] G5 externally verified
[ ] no fake CFA FRA live evidence
```

---

# 52. Release decision after REM-10

Après REM-10 :

```text
compatible fixes
    ↓
new 0.7 RC
    ↓
final qualification
    ↓
0.7.0 stable
```

Si les corrections imposent des changements structurels incompatibles :

```text
do not force 0.7.0
```

Choisir le milestone approprié après analyse SemVer.

---

# 53. Nouvelle relation avec `LOT-39 → LOT-46`

Après la remédiation :

```text
LOT-39 Architecture Fitness
LOT-40 Domain Events
LOT-41 Reproducibility
LOT-42 Golden / Concurrency
LOT-43 Testing Toolkit
LOT-44 Recovery / External Effects
LOT-45 Domain-First Foundations
LOT-46 Financial Semantic Layer
```

reprennent comme roadmap stratégique.

---

# 54. Mapping REM → future LOT

| Remediation | Future capability préparée |
|---|---|
| REM-01 | LOT-39 / LOT-42 |
| REM-02 | LOT-40 / LOT-41 |
| REM-03 | LOT-40 / LOT-42 / LOT-44 |
| REM-04 | LOT-40 / LOT-41 |
| REM-05 | LOT-42 / LOT-44 |
| REM-06 | LOT-41 |
| REM-07 | LOT-41 |
| REM-08 | API Freeze 0.9 |
| REM-09 | Stable Subledger capability |
| REM-10 | autorise reprise roadmap |

---

# 55. LOT-39 — après remédiation

Une partie des Architecture Fitness Functions peut être utilisée dès REM-01.

Mais l’implémentation complète de LOT-39 intervient après la remise à niveau.

Cible :

```text
import-linter
AST rules
context rules
exception registry
blocking CI gate
```

---

# 56. LOT-43 — Testing Toolkit

Les helpers nécessaires à la remédiation peuvent être extraits progressivement.

Mais la stabilisation de :

```text
pyaccountingkit.testing
```

comme surface publique ne doit pas ralentir les corrections P1.

---

# 57. LOT-40 — Domain Events

Ne pas refondre l’Event Envelope avant d’avoir sécurisé :

```text
F10 immutability
F11 idempotency
F14 payload immutability
A03 durable trace
```

---

# 58. LOT-41 — Reproducibility

Ne pas construire les manifests sur des preuves incorrectes.

Prérequis :

```text
F15 checksum corrected
F20 snapshots immutable
F22 publication lifecycle corrected
F06 closing freshness corrected
```

---

# 59. LOT-42 — Golden / Concurrency

Celui-ci peut démarrer progressivement pendant la remédiation.

Les corrective tests des Fxx doivent devenir les futurs :

```text
golden
race
regression
contract
```

scenarios.

---

# 60. LOT-44 — Recovery

Les remédiations sur :

```text
idempotency
closing retry
atomic outbox
```

préparent directement :

```text
UNCERTAIN
RecoveryDisposition
ExternalEffect
```

mais la state machine complète reste post-remédiation.

---

# 61. LOT-45 — Domain-First Migration

Gel presque complet pendant la remédiation.

Règle :

```text
correct behavior first
move packages later
```

Avant 1.0, limiter à :

```text
inventory
ownership map
minimal shared kernel policy
```

---

# 62. LOT-46 — Financial Semantic Layer

Ne pas implémenter avant que :

```text
ReportSnapshot
AnalysisSnapshot
checksums
publication
reproducibility
```

soient fiables.

---

# 63. Revised release sequence

## Current

```text
0.7.0rc1
```

## Next

```text
0.7.x RC remediation candidate
```

après corrections suffisantes.

Puis :

```text
0.7.0 stable
```

si le périmètre qualifié le permet.

---

# 64. Après `0.7.0`

Proposition conservée :

```text
0.8.x
Reliability & Architecture Hardening
```

avec :

```text
Architecture Fitness
Testing Toolkit
Domain Events
Computation Manifests
Golden / Concurrency
Recovery
```

---

# 65. `0.9.x`

Objectif :

```text
API / Schema Freeze
```

Inclure :

```text
Public API
Public Errors
Event Schemas
Snapshot Schemas
Manifest Schemas
Adapter Contracts
```

---

# 66. `1.0.0`

Objectif :

```text
Stable Public Core
```

Critères :

```text
0 BLOCKER
0 CRITICAL
stable contracts
cross-adapter qualification
golden green
concurrency green
replay green
package qualification green
```

---

# 67. Post-1.0

Deux grands chantiers :

```text
Domain-First Package Migration
+
Financial Semantic Layer
```

---

# 68. Immediate execution queue

La nouvelle file d’exécution est :

```text
NOW
│
├── REM-00
│   ├── compare HEAD with audit baseline
│   ├── remediation registry
│   └── corrective tests
│
├── REM-01
│   ├── Nightly
│   ├── release verification
│   └── strict PostgreSQL proof
│
├── REM-02
│   └── identity / entity scope
│
├── REM-03
│   └── posting / immutability / idempotency
│
├── REM-04
│   └── evidence / durable trace
│
├── REM-06
│   └── checksum / calculation fidelity
│
├── REM-05
│   └── closing / openings
│
├── REM-07
│   └── publication / references
│
├── REM-08
│   └── public contracts
│
├── REM-09
│   └── persistent subledgers
│
└── REM-10
    └── release decision
```

---

# 69. First implementation increment

Le premier incrément recommandé est :

```text
REM-00
+
REM-01
+
first REM-02 slice
```

---

# 70. First concrete tasks

```text
1. Compare current HEAD with audit SHA
2. Build remediation status registry
3. Convert audit reproductions into expected-behavior tests
4. Fix Nightly collection
5. Fix release repository context
6. Make PostgreSQL mandatory in strict qualification
7. Add opaque AccountId regression tests
8. Add cross-entity scope regression tests
9. Fix AccountId vs AccountCode resolution
10. Re-run InMemory + both PostgreSQL adapters
```

---

# 71. PR strategy

Ne pas créer une seule PR :

```text
"fix audit"
```

Préférer des slices.

---

# 72. Suggested PR sequence

```text
PR-REM-00.1
Remediation registry + tests scaffold
```

```text
PR-REM-01.1
Nightly collection
```

```text
PR-REM-01.2
Strict PostgreSQL qualification
```

```text
PR-REM-02.1
AccountId vs AccountCode
```

```text
PR-REM-02.2
Entity scope
```

Puis poursuivre par capability.

---

# 73. Rule for corrective tests

Les assertions d’audit :

```text
prove the bug exists
```

ne doivent pas être copiées comme tests définitifs.

Les nouveaux tests doivent exprimer :

```text
expected correct behavior
```

---

# 74. Rule for historical evidence

Ne jamais reconstruire une preuve manquante comme si elle avait existé historiquement.

Toute réparation a posteriori possède :

```text
its own date
provenance
status
evidence
```

---

# 75. Rule for accounting corrections

Une anomalie réelle dans une écriture POSTED est corrigée par :

```text
reversal
adjustment
replacement
```

pas par :

```text
silent edit
```

---

# 76. Rule for compatibility

Les évolutions de :

```text
idempotency
checksum
snapshots
ports
UoW
publication status
```

doivent inclure une stratégie explicite de migration/replay.

---

# 77. Rule for release evidence

Une preuve qualifiante doit toujours être attachée à :

```text
exact candidate SHA
```

---

# 78. Rule for PostgreSQL

Les garanties de production ne peuvent pas être déclarées uniquement depuis :

```text
InMemory
```

---

# 79. Revised success path

```text
AUDIT
    ↓
FINDINGS
    ↓
CORRECTIVE TESTS
    ↓
FIXES
    ↓
CROSS-ADAPTER QUALIFICATION
    ↓
REPLAY / MIGRATION
    ↓
RELEASE EVIDENCE
    ↓
STABLE
```

---

# 80. Final decision

Le prochain chantier n’est plus :

```text
LOT-39
```

Le prochain chantier est :

```text
REM-00
```

suivi immédiatement de :

```text
REM-01
```

et des premiers correctifs :

```text
REM-02
```

Les `LOT-39 → LOT-46` restent valides mais sont désormais :

```text
POST-REMEDIATION STRATEGIC ROADMAP
```

---

# 81. Next Step

```text
NEXT
=
REM-00 — Baseline & Remediation Registry
```

Livrables immédiats :

```text
docs/plans/REMEDIATION_2026_10_PLAN.md
docs/audits/REMEDIATION_2026_10_STATUS.json
corrective regression tests
HEAD-vs-baseline comparison
```

Puis :

```text
REM-01
Qualification & Workflow Reliability
```

---

# 82. Conclusion

La nouvelle roadmap n’est pas abandonnée.

Elle est désormais précédée d’une couche obligatoire :

```text
REM-00 → REM-10
```

Le modèle de pilotage devient :

```text
FIX WHAT EXISTS
        ↓
PROVE IT
        ↓
RELEASE IT
        ↓
EVOLVE IT
```

Autrement dit :

> **les specs `24 → 32` définissent où PyAccountingKit doit aller ; l’audit et `REM-00 → REM-10` définissent ce qu’il faut corriger avant d’y aller.**