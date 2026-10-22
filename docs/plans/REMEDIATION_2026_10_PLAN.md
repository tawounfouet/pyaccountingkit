# PyAccountingKit — Remediation Plan 2026-10

> **Projet** : PyAccountingKit
> **Document** : REMEDIATION_2026_10_PLAN.md
> **Statut** : REM-00 — baseline et plan de remédiation canonique
> **Date** : 22 octobre 2026
> **Version package** : 0.7.0rc1
> **Audit baseline SHA** : 259e9ad665941cd6a9545deb3b92f979d40eae35
> **Remediation start SHA** : 3ba5d84ab575bb4b0c0b41f148632632c01551c7
> **Registre machine-readable** : docs/audits/REMEDIATION_2026_10_STATUS.json
> **Source de gouvernance** : docs/plans/34_PYACCOUNTINGKIT_AUDIT_REMEDIATION_AND_ROADMAP_ALIGNMENT.md

---

# 1. Objet

Ce document est le plan opérationnel canonique de l'overlay de remédiation issu de l'audit approfondi de PyAccountingKit 0.7.0rc1.

Il transforme :

~~~text
F01..F27
+
A01..A03
~~~

en une chaîne vérifiable :

~~~text
finding
    ↓
corrective test
    ↓
implementation fix
    ↓
qualification evidence
    ↓
VERIFIED
~~~

Il ne remplace ni la roadmap produit ni les specs d'architecture. Il constitue le contrat d'exécution de REM-00 → REM-10.

---

# 2. Baseline figée

## 2.1 Audit baseline

~~~text
SHA     259e9ad665941cd6a9545deb3b92f979d40eae35
version 0.7.0rc1
~~~

## 2.2 Remediation start

~~~text
SHA     3ba5d84ab575bb4b0c0b41f148632632c01551c7
version 0.7.0rc1
~~~

## 2.3 Delta entre audit et démarrage REM-00

La comparaison GitHub entre les deux SHA montre :

~~~text
ahead_by     22 commits
code delta   0 fichier src/
test delta   0 fichier tests/
workflow     0 changement observé
changes      documentation uniquement
~~~

Conclusion :

> **La baseline comportementale du code au démarrage de REM-00 est identique à la baseline auditée.**

Les commits documentaires intervenus après l'audit ne ferment donc aucun finding à eux seuls.

---

# 3. Règle exacte de preuve

Aucun finding ne passe directement de OPEN à VERIFIED.

Cycle obligatoire :

~~~text
OPEN
  ↓
IN_PROGRESS
  ↓
FIXED_UNVERIFIED
  ↓
VERIFIED
~~~

États complémentaires :

~~~text
BLOCKED
NOT_IN_RELEASE_SCOPE
~~~

Règles :

- OPEN : défaut confirmé, aucun correctif qualifié.
- IN_PROGRESS : test correctif et/ou correction en cours.
- FIXED_UNVERIFIED : correction présente mais preuve complète manquante.
- VERIFIED : correction + tests + gates applicables + preuve liée au SHA exact.
- BLOCKED : dépendance explicite empêche la fermeture.
- NOT_IN_RELEASE_SCOPE : uniquement par décision documentée de scope ; ne signifie pas corrigé.

---

# 4. Politique de SHA

Toute preuve de qualification doit référencer le SHA candidat exact.

~~~text
test evidence SHA
    =
candidate SHA
~~~

Interdit :

~~~text
evidence from previous SHA
    → reused as current proof
~~~

Un nouveau commit qui touche le comportement concerné invalide la preuve antérieure jusqu'à requalification.

---

# 5. Politique corrective-test-first

Pour chaque finding :

~~~text
1. reproduce defect
2. encode expected behavior
3. confirm test fails on faulty behavior
4. implement minimum coherent fix
5. run focused tests
6. run contract/integration tests
7. run applicable cross-adapter / PostgreSQL tests
8. attach exact-SHA evidence
9. move status to VERIFIED
~~~

Le test final doit vérifier le comportement attendu, et non simplement reproduire l'ancien bug.

---

# 6. Source of truth precedence

En cas de conflit :

~~~text
accounting invariant / approved spec
        ↓
explicit remediation decision
        ↓
corrective test
        ↓
legacy fixture
~~~

Une fixture historique n'est pas une autorité si elle encode le défaut audité.

---

# 7. Transaction boundary rule

Lorsqu'une mutation comptable est concernée, la transaction doit inclure, selon le use case :

~~~text
business writes
state transitions
evidence / durable trace
audit
outbox intent
idempotency completion
~~~

Les éléments qui doivent être atomiques ne peuvent pas être validés après un commit métier déjà irréversible.

---

# 8. Port evolution rule

Toute évolution de port exige l'inventaire puis la migration de :

~~~text
callers
in-memory adapter
Django adapter
SQLAlchemy adapter
contract tests
integration tests
public facade if exposed
manifests / docs if user-visible
~~~

Aucune signature de port ne doit être changée isolément.

---

# 9. PostgreSQL qualification rule

Pour les sujets persistance/concurrence :

~~~text
real PostgreSQL required
~~~

Un skip obligatoire est un échec de qualification, pas un succès partiel.

Doivent être distingués :

~~~text
test not applicable
test intentionally excluded
test required but unavailable
~~~

Le dernier cas bloque la gate.

---

# 10. Registre des findings

Le registre machine-readable est :

~~~text
docs/audits/REMEDIATION_2026_10_STATUS.json
~~~

Il porte pour chaque finding :

~~~text
id
type
severity
title
primary_remediation_lot
release_scope
status
audit_baseline_sha
remediation_start_sha
fix_sha
corrective_tests
qualification_evidence
affected_components
notes
~~~

Le JSON est la source de vérité opérationnelle pour le statut ; ce plan décrit les règles.

---

# 11. Ordre de remédiation

~~~text
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
~~~

L'ordre REM-06 → REM-05 est volontaire : les preuves de clôture doivent s'appuyer sur des calculs/checksums fiables.

---

# 12. REM-00 — Baseline & Remediation Registry

## Scope

- figer les SHA ;
- distinguer audit baseline et remediation start ;
- créer le registre des 30 écarts ;
- définir les statuts ;
- définir la politique de preuve ;
- définir les conventions de tests correctifs ;
- indexer les artifacts ;
- confirmer que les commits post-audit n'ont pas modifié le code.

## Findings

~~~text
F01..F27
A01..A03
~~~

## DoD

~~~text
[ ] audit baseline SHA enregistré
[ ] remediation start SHA enregistré
[ ] delta audit→start qualifié
[ ] plan de remédiation présent
[ ] registre JSON valide présent
[ ] 30 findings présents
[ ] chaque finding possède un lot primaire
[ ] chaque finding possède un statut explicite
[ ] politique exact-SHA documentée
[ ] convention corrective-test-first documentée
[ ] plans README indexe les artifacts
~~~

---

# 13. REM-01 — Qualification Reliability

## Findings

- F25 — Nightly collection broken.
- F26 — release verification lacks repository context.
- F27 — RC qualification passes while required PostgreSQL modules are skipped.

## Objectif

Avant de corriger les invariants comptables, rendre la machine de qualification fiable.

## Exit criteria

~~~text
Nightly collects expected suite
required PG unavailable => FAIL
required PG module skipped => FAIL
candidate SHA explicitly captured
repository context available to verification
Django + SQLAlchemy production adapter evidence required where applicable
~~~

---

# 14. REM-02 — Identity / Scope / Read-Side

## Findings

~~~text
F01 F02 F03 F04 F13 F18
~~~

## Objectif

Rétablir la séparation :

~~~text
AccountId != AccountCode
Entity A != Entity B
requested scope == persisted/read scope
~~~

## Required regression themes

- AccountId vs AccountCode ;
- posting cross-entity ;
- ImportPlan entity boundary ;
- balance entity relabeling ;
- ledger account identity and currency fidelity ;
- duplicate AccountId in company chart.

---

# 15. REM-03 — Posting / Repositories / Idempotency

## Findings

~~~text
F10 F11 F23 F24
~~~

## Objectif

Garantir le lifecycle des écritures et les contrats repository/idempotency.

## Required regression themes

- POSTED economics cannot be rewritten ;
- same idempotency key cannot replay different semantic payload/scope ;
- PeriodRepository transition contract consistent across adapters ;
- persisted VALIDATED entry can be posted through the supported path.

---

# 16. REM-04 — Immutable Evidence / Durable Traceability

## Findings

~~~text
F14 F20 A03
~~~

## Objectif

Rendre les preuves et traces historiques réellement immuables et atomiques.

## Required regression themes

- deep immutability of AuditEvent / OutboxRecord payloads ;
- sealed regulatory snapshot cannot be silently mutated ;
- proposal→entry trace persisted atomically with execution outcome.

---

# 17. REM-06 — Calculation / Checksums / Fidelity

## Findings

~~~text
F12 F15 F16 F21
~~~

## Objectif

Éliminer les pertes sémantiques et erreurs de calcul/fingerprint.

## Required regression themes

- proposal→entry preserves EntryType ;
- trial-balance checksum includes semantic account/currency identity ;
- allocation preserves cents without premature rounding ;
- sign convention applied exactly once.

---

# 18. REM-05 — Closing / Opening Atomicity

## Findings

~~~text
F05 F06 F07 F08 F09
~~~

## Objectif

Rendre clôture et à-nouveaux fail-closed, scope-safe et atomiques.

## Required regression themes

- ERROR/missing controls block closing ;
- foreign/stale balance rejected ;
- opening path cannot bypass posting/target scope ;
- closing proof committed atomically with accounting transition ;
- read-only resources still participate in conflict detection when required.

---

# 19. REM-07 — Safe References / Publication

## Findings

~~~text
F19 F22
~~~

## Objectif

Empêcher l'exécution/publication de structures invalides.

## Required regression themes

- hierarchy cycle/mixed edition fail-closed ;
- FAIL result cannot become PUBLISHED ;
- legal publication transition is VALIDATED → PUBLISHED.

---

# 20. REM-08 — Public Contracts / Application Services

## Findings

~~~text
F17 A02
~~~

## Objectif

Éliminer les fuites ORM et stabiliser les contrats opérationnels typés.

## Required regression themes

- neutrality guard catches wrapped ORM leakage ;
- public facade translates internal failures ;
- operational public contracts remain typed and adapter-neutral.

---

# 21. REM-09 — Persistent Subledgers

## Finding

~~~text
A01
~~~

## Scope decision

A01 est CONDITIONAL pour la release 0.7.

Deux issues seulement sont valides :

~~~text
1. capability declared in 0.7 scope
   => implement + qualify persistent chain

2. capability explicitly excluded from 0.7 scope
   => NOT_IN_RELEASE_SCOPE
      + public/release claims must exclude it
~~~

Aucune fermeture artificielle n'est autorisée.

---

# 22. REM-10 — Transverse Qualification

## Scope

Tous les findings applicables.

## Required evidence

~~~text
unit
property
contract
integration
real PostgreSQL
Django adapter
SQLAlchemy adapter
concurrency
golden
replay
migration where affected
package build
public import smoke
exact candidate SHA
~~~

## Stable decision

~~~text
applicable P1 OPEN
    => BLOCK

required PG skipped
    => BLOCK

evidence SHA mismatch
    => BLOCK

semantic cross-adapter divergence
    => BLOCK
~~~

---

# 23. Finding-to-lot matrix

| Finding | Priority | Primary lot |
|---|---:|---|
| F01 | P1 | REM-02 |
| F02 | P1 | REM-02 |
| F03 | P1 | REM-02 |
| F04 | P1 | REM-02 |
| F05 | P1 | REM-05 |
| F06 | P1 | REM-05 |
| F07 | P1 | REM-05 |
| F08 | P1 | REM-05 |
| F09 | P1 | REM-05 |
| F10 | P1 | REM-03 |
| F11 | P1 | REM-03 |
| F12 | P1 | REM-06 |
| F13 | P1 | REM-02 |
| F14 | P1 | REM-04 |
| F15 | P1 | REM-06 |
| F16 | P1 | REM-06 |
| F17 | P2 | REM-08 |
| F18 | P2 | REM-02 |
| F19 | P2 | REM-07 |
| F20 | P1 | REM-04 |
| F21 | P1 | REM-06 |
| F22 | P1 | REM-07 |
| F23 | P1 | REM-03 |
| F24 | P1 | REM-03 |
| F25 | P2 | REM-01 |
| F26 | P2 | REM-01 |
| F27 | P1 | REM-01 |
| A01 | architecture gap | REM-09 |
| A02 | architecture gap | REM-08 |
| A03 | architecture gap | REM-04 |

---

# 24. Pull request / commit discipline

Éviter une PR massive de remédiation.

Préférence :

~~~text
one coherent remediation slice
+
focused corrective tests
+
focused evidence
~~~

Chaque slice doit référencer les finding IDs concernés.

---

# 25. Stop-the-line conditions

Suspendre la progression d'un lot si :

- le correctif modifie un invariant sans spec/ADR claire ;
- une migration de port laisse un adapter non migré ;
- un test production obligatoire est skipped ;
- une preuve provient d'un autre SHA ;
- un fix transforme un défaut en silence plutôt qu'en rejet explicite ;
- l'historique comptable est réécrit pour satisfaire un test ;
- une fixture est modifiée uniquement pour masquer une régression ;
- une correction crée une divergence InMemory / Django / SQLAlchemy.

---

# 26. REM-00 completion evidence

REM-00 est considéré documentairement initialisé lorsque :

~~~text
docs/plans/REMEDIATION_2026_10_PLAN.md
+
docs/audits/REMEDIATION_2026_10_STATUS.json
+
docs/plans/README.md links
~~~

sont présents sur main.

Il ne ferme aucun finding métier.

Il autorise le passage à :

~~~text
REM-01
Qualification Reliability
~~~

---

# 27. Prochaine action après REM-00

~~~text
F25
Nightly collection
    ↓
F26
repository-aware verification
    ↓
F27
PostgreSQL fail-closed RC qualification
~~~

Puis :

~~~text
REM-02
Identity / Scope first slice
~~~

---

# 28. Principe final

~~~text
DO NOT CLAIM FIXED
UNTIL
THE EXPECTED BEHAVIOR
IS PROVEN
ON
THE EXACT CANDIDATE SHA
~~~
