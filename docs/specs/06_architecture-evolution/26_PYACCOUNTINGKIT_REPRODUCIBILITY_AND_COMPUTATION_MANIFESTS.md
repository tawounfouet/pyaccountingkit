# 26_PYACCOUNTINGKIT_REPRODUCIBILITY_AND_COMPUTATION_MANIFESTS.md

# PyAccountingKit — Reproducibility & Computation Manifests

> **Projet** : PyAccountingKit  
> **Document** : `26_PYACCOUNTINGKIT_REPRODUCIBILITY_AND_COMPUTATION_MANIFESTS.md`  
> **Statut** : Spécification d'architecture transverse — reproductibilité, provenance et replay  
> **Version documentaire** : 1.0  
> **Date** : 22 octobre 2026  
> **Baseline observée** : PyAccountingKit `0.7.0rc1`  
> **Langue** : Français  

---

# 1. Objet du document

Ce document définit l'architecture cible de **reproductibilité des calculs et publications** de PyAccountingKit.

Il formalise la manière dont le framework doit capturer, pour toute production financière importante :

```text
les données sources
les snapshots utilisés
les versions de référentiels
les versions de policies
les versions de définitions
les mappings
les stratégies
les paramètres
les checksums
la version du framework
le résultat produit
```

afin de pouvoir répondre à :

> **Avec quelles données, quelles règles et quelles versions ce résultat a-t-il exactement été produit ?**

La cible est :

```text
INPUTS
+
VERSIONS
+
POLICIES
+
MAPPINGS
+
PARAMETERS
+
CODE VERSION
        ↓
DETERMINISTIC COMPUTATION
        ↓
OUTPUT
+
MANIFEST
+
CHECKSUM
```

---

# 2. Pourquoi ce document est nécessaire

PyAccountingKit produit ou prépare des résultats tels que :

```text
Trial Balance
Financial Statement
Regulatory Export
Financial Analysis
Closing Result
Reconciliation Snapshot
Consolidation Snapshot
Semantic Snapshot
Import Result
```

Ces résultats peuvent être :

```text
publiés
audités
comparés
rejoués
consommés par des systèmes externes
utilisés comme source downstream
```

Il n'est donc pas suffisant de stocker uniquement :

```text
result = 1 250 000 EUR
```

Il faut pouvoir expliquer :

```text
why
from what
with which version
under which policy
using which mapping
at which point in time
```

---

# 3. Baseline existante

La codebase actuelle possède déjà des mécanismes solides de reproductibilité.

Cette spécification les généralise.

---

# 4. `ReportSnapshot`

`ReportSnapshot` est actuellement immutable et capture notamment :

```text
snapshot_id
accounting_entity_id
report_type
source_period_id
source_checksum
statement_definition_id
statement_definition_version
statement_definition_checksum
mapping_set_id
mapping_set_version
mapping_set_checksum
result_checksum
as_of
created_at
status
lines
checksum
```

Le snapshot est donc déjà capable de répondre à une grande partie de :

```text
source
definition
mapping
result
integrity
```

---

# 5. `ReportSnapshotFreshness`

La baseline distingue :

```text
CURRENT
STALE
```

en comparant le `source_checksum` du snapshot avec la source courante.

Cette propriété devient un principe transverse.

---

# 6. `AnalysisSnapshot`

`AnalysisSnapshot` capture déjà :

```text
snapshot_id
accounting_entity_id
period_id
as_of
source_type
source_ref
source_checksum
source_freshness
definition_set_id
definition_set_version
definition_set_checksum
analysis_result_checksum
indicator_checksums
ratio_checksums
trace_checksums
functional_balance_checksum
working_capital_checksum
trend_checksums
diagnostic_checksums
generated_at
checksum
```

C'est déjà une forme spécialisée de computation manifest.

---

# 7. `RegulatoryExportArtifact`

La baseline capture notamment :

```text
artifact_id
accounting_entity_id
regulatory_report_checksum
profile_id
profile_version
reference_snapshot_id
export_definition_id
export_definition_version
media_type
payload_checksum
generated_at
payload
```

L'intégrité du payload est validée par SHA-256.

---

# 8. `SNAPSHOT_SCHEMA_MANIFEST.json`

Le repository possède déjà :

```text
SNAPSHOT_SCHEMA_MANIFEST.json
```

avec :

```text
schema_version
package version
snapshot types
field names
field types
enum values
immutability metadata
```

Ce manifest protège la structure des snapshots.

Il ne remplace cependant pas un manifest d'exécution.

---

# 9. Trois niveaux à distinguer

Il faut distinguer :

```text
Schema Manifest
Computation Manifest
Result Snapshot
```

---

# 10. Schema Manifest

Il décrit :

```text
la structure du contrat
```

Exemple :

```text
SNAPSHOT_SCHEMA_MANIFEST.json
```

Question répondue :

> Quels champs constituent un `ReportSnapshot` ?

---

# 11. Computation Manifest

Il décrit :

```text
les coordonnées exactes d'une exécution
```

Question répondue :

> Quelles versions et quelles entrées ont produit CE résultat précis ?

---

# 12. Result Snapshot

Il contient :

```text
le résultat métier figé
```

Question répondue :

> Quel résultat a effectivement été publié ?

---

# 13. Principe fondamental

La reproductibilité doit être basée sur :

```text
pinning
+
checksums
+
immutable snapshots
+
deterministic rules
```

et non uniquement sur :

```text
timestamps
database IDs
latest version
current configuration
```

---

# 14. Reproductibility contract

Une computation est considérée reproductible si :

```text
same canonical inputs
+
same input checksums
+
same framework version
+
same definition versions
+
same policies
+
same mappings
+
same strategy versions
+
same explicit parameters
=
same semantic output
```

à l'exception des métadonnées volontairement non sémantiques.

---

# 15. Semantic output

Le terme :

```text
same semantic output
```

signifie :

```text
same financial values
same classifications
same mappings
same statuses
same deterministic traces
```

mais pas nécessairement :

```text
same generated_at
same random UUID
same database row ID
```

---

# 16. Semantic checksum

Chaque résultat important doit pouvoir exposer un checksum ne dépendant que de sa sémantique.

Exemple :

```text
analysis_result_checksum
result_checksum
```

déjà présents dans la baseline.

---

# 17. Artifact checksum

Un artifact physique peut également posséder :

```text
payload_checksum
```

Exemple :

```text
PDF
CSV
JSON
XBRL
Parquet
```

Il faut distinguer :

```text
semantic result checksum
```

de :

```text
physical artifact checksum
```

---

# 18. Pourquoi cette distinction est importante

Deux exports peuvent représenter le même résultat financier :

```text
JSON
CSV
PDF
```

Leur :

```text
payload checksum
```

sera différent.

Mais leur :

```text
semantic source checksum
```

peut être identique.

---

# 19. `ComputationManifest`

Le modèle cible introduit un concept générique :

```text
ComputationManifest
```

qui porte les coordonnées minimales d'un calcul reproductible.

---

# 20. Structure cible

```text
ComputationManifest
|
+-- manifest_id
+-- manifest_type
+-- manifest_schema_version
+-- pyaccountingkit_version
+-- computation_id
+-- accounting_entity_id?
+-- correlation_id?
+-- source_inputs
+-- reference_context
+-- policy_context
+-- definition_context
+-- mapping_context
+-- strategy_context
+-- parameter_context
+-- runtime_context
+-- generated_at
+-- result_checksum
+-- manifest_checksum
```

---

# 21. `manifest_id`

Identifie le document manifest.

Il n'est pas nécessairement l'identifiant du résultat.

---

# 22. `manifest_type`

Exemples :

```text
CLOSING
STATEMENT_GENERATION
REGULATORY_EXPORT
FINANCIAL_ANALYSIS
IMPORT
RECONCILIATION
CONSOLIDATION
SEMANTIC
```

---

# 23. `manifest_schema_version`

Version du schéma du manifest.

À distinguer de :

```text
package version
result schema version
event schema version
```

---

# 24. `pyaccountingkit_version`

Le manifest doit pinner la version du package ayant exécuté le calcul.

Exemple :

```text
0.7.0rc1
```

---

# 25. Version package != version métier

La version :

```text
0.7.0rc1
```

ne remplace pas :

```text
AccountingPolicySet v3
StatementDefinition v4
MappingSet v7
```

Toutes ces coordonnées doivent être conservées indépendamment.

---

# 26. `source_inputs`

Le manifest doit référencer les inputs canoniques.

Exemple :

```text
TrialBalanceSnapshot
ReferenceSnapshot
SubledgerSnapshot
BankStatementSnapshot
FinancialStatementSnapshot
```

---

# 27. Source input reference

Structure :

```text
SourceInputRef
|
+-- source_type
+-- source_id
+-- source_version?
+-- checksum
+-- freshness?
+-- captured_at?
```

---

# 28. Pas de source `LATEST`

Un manifest publié ne doit jamais contenir uniquement :

```text
reference = latest
```

ou :

```text
mapping = current
```

Il doit pinner une version ou un checksum précis.

---

# 29. Reference context

Structure cible :

```text
ReferenceContext
|
+-- standard_id
+-- edition
+-- reference_version
+-- reference_snapshot_id
+-- reference_checksum
```

---

# 30. Exemples

```text
PCG / 2026
SYSCOHADA / 2017
OHADA EBNL / 2023
```

---

# 31. Policy context

Structure :

```text
PolicyContext
|
+-- policy_set_id
+-- policy_set_version
+-- policy_set_checksum
+-- individual_policy_refs?
```

---

# 32. Definition context

Pour reporting :

```text
StatementDefinition
```

Pour analysis :

```text
FinancialIndicatorDefinitionSet
```

Pour reconciliation :

```text
ReconciliationDefinition
```

Pour semantic layer :

```text
SemanticModelDefinition
```

---

# 33. Mapping context

Exemples :

```text
StatementMappingSet
ReferenceAccountMapping
ConsolidationMapping
SemanticMapping
```

Structure :

```text
MappingRef
    id
    version
    checksum
```

---

# 34. Strategy context

Certaines computations dépendent de stratégies.

Exemples :

```text
matching strategy
currency conversion strategy
depreciation strategy
analysis strategy
consolidation strategy
```

Le manifest doit pinner :

```text
strategy id
strategy version
checksum if declarative
```

---

# 35. Parameter context

Les paramètres métier affectant le résultat doivent être explicites.

Exemples :

```text
as_of
period
materiality
tolerance
currency target
scenario
variant
```

---

# 36. Runtime context

Les éléments runtime pouvant affecter la reproductibilité doivent être capturés si nécessaire.

Exemples :

```text
locale?
timezone?
decimal context?
feature flag?
```

Mais le runtime context ne doit pas devenir un dump complet de l'environnement.

---

# 37. Platform independence

Un résultat métier ne doit pas dépendre silencieusement de :

```text
OS
database engine
Python hash ordering
machine timezone
```

si cela peut être évité.

---

# 38. Deterministic serialization

Les checksums utilisent une sérialisation canonique.

Recommandation :

```text
JSON
sort_keys = true
stable separators
ISO dates
Decimal as string
explicit enums
```

---

# 39. Float interdit pour Money

Les montants financiers doivent rester :

```text
Decimal
```

et être sérialisés sous forme :

```text
"100.00"
```

pas :

```text
100.0
```

---

# 40. Sorting

Toute collection dont l'ordre n'est pas sémantique doit être triée avant checksum.

Exemple :

```text
diagnostic_checksums
trend_checksums
```

La baseline applique déjà ce principe dans plusieurs snapshots.

---

# 41. Order-sensitive data

Une collection dont l'ordre est sémantique ne doit pas être triée artificiellement.

Exemple :

```text
statement line display order
```

---

# 42. Time determinism

Un timestamp de génération ne doit pas contaminer un checksum sémantique sauf si le temps constitue réellement une donnée métier.

---

# 43. `generated_at`

`generated_at` est utile pour :

```text
audit
freshness
publication
operations
```

mais il doit être exclu du checksum sémantique si :

```text
same computation run later
```

doit produire le même résultat sémantique.

---

# 44. `manifest_checksum`

Le manifest lui-même possède un checksum.

Il protège :

```text
input refs
versions
policies
definitions
mappings
parameters
```

---

# 45. `result_checksum`

Le manifest pointe vers le checksum du résultat.

Relation :

```text
Manifest
    ├── input checksums
    └── result checksum
```

---

# 46. Chaîne de preuve

```text
Source Snapshot
    checksum A
        ↓
Definition
    checksum B
        ↓
Mapping
    checksum C
        ↓
Computation Manifest
    checksum D
        ↓
Result Snapshot
    checksum E
        ↓
Export Artifact
    checksum F
```

---

# 47. Provenance graph

Un résultat doit pouvoir former un DAG de provenance.

Exemple :

```text
ReferenceSnapshot
TrialBalanceSnapshot
StatementDefinition
MappingSet
        │
        └──────┐
               ▼
       StatementGenerationManifest
               │
               ▼
          ReportSnapshot
               │
               ▼
       RegulatoryExportArtifact
```

---

# 48. Manifest specializations

Le modèle générique doit supporter des manifests spécialisés.

Recommandés :

```text
ClosingManifest
StatementGenerationManifest
RegulatoryExportManifest
FinancialAnalysisManifest
ImportManifest
ReconciliationManifest
ConsolidationManifest
SemanticManifest
```

---

# 49. `ClosingManifest`

Objectif :

> rendre une clôture explicable et rejouable.

---

# 50. Closing coordinates

```text
entity
fiscal year
period
pre-close source checksum
AccountingPolicySetclosing definition/version
accrual strategy refs
provision strategy refs
generated adjustment entries
controls
post-close source checksum
framework version
```

---

# 51. Exemple

```text
ClosingManifest
|
+-- entity_id
+-- period_id
+-- source_trial_balance_checksum
+-- policy_set_id/version/checksum
+-- closing_rule_set_version
+-- generated_entry_ids
+-- generated_entry_checksums
+-- controls_checksum
+-- post_close_trial_balance_checksum
+-- result_checksum
```

---

# 52. Closing replay

Un replay historique ne doit jamais réécrire :

```text
published historical close
```

Il produit :

```text
ReplayResult
```

ou une nouvelle révision.

---

# 53. `StatementGenerationManifest`

Il généralise ce que `ReportSnapshot` pinne déjà.

---

# 54. Structure recommandée

```text
StatementGenerationManifest
|
+-- entity_id
+-- period_id
+-- source_snapshot_id
+-- source_checksum
+-- statement_definition_id
+-- statement_definition_version
+-- statement_definition_checksum
+-- mapping_set_id
+-- mapping_set_version
+-- mapping_set_checksum
+-- accounting_framework
+-- reference_snapshot
+-- policy_set
+-- pyaccountingkit_version
+-- result_checksum
```

---

# 55. Baseline compatibility

Le manifest ne remplace pas les champs déjà présents dans `ReportSnapshot`.

Il permet :

```text
normalisation transverse
cross-output tooling
release evidence
```

---

# 56. `RegulatoryExportManifest`

Le `RegulatoryExportArtifact` contient déjà une grande partie des coordonnées nécessaires.

Le manifest cible peut ajouter :

```text
report snapshot id
report snapshot checksum
reference checksum
renderer version
export schema version
profile version
```

---

# 57. Regulatory export chain

```text
ReportSnapshot
        ↓
Regulatory Mapping/Profile
        ↓
Export Definition
        ↓
Renderer
        ↓
RegulatoryExportArtifact
```

---

# 58. `FinancialAnalysisManifest`

L'`AnalysisSnapshot` capture déjà :

```text
source
definition set
indicator checksums
ratio checksums
traces
diagnostics
overall checksum
```

Le manifest spécialisé doit principalement normaliser ce contrat dans la famille de manifests.

---

# 59. Analysis coordinates

```text
source snapshot
source freshness
definition set
definition checksum
trend strategies
diagnostic definitions
working capital definition
functional balance definition
result checksum
```

---

# 60. `ImportManifest`

Il s'agit d'un gap plus important.

L'import doit pouvoir capturer :

```text
source artifact
source checksum
source format
parser version
normalization version
mapping version
reference snapshot
policy version
deduplication strategy
batch id
record counts
result checksums
```

---

# 61. Import reproducibility

Pipeline :

```text
Raw Artifact
      ↓
Parser vN
      ↓
Normalization vN
      ↓
Mapping vN
      ↓
JournalEntry candidates
      ↓
Import result
```

Chaque étape influençant le résultat doit être pinée.

---

# 62. `ImportManifest` structure

```text
ImportManifest
|
+-- import_batch_id
+-- source_system
+-- source_artifact_ref
+-- source_checksum
+-- source_format
+-- parser_id/version
+-- normalization_id/version
+-- mapping_set_id/version/checksum
+-- reference_snapshot_id/checksum
+-- import_policy_id/version
+-- idempotency_key
+-- input_record_count
+-- accepted_record_count
+-- rejected_record_count
+-- output_checksums
```

---

# 63. No mutable raw source

Une importation reproductible doit conserver :

```text
raw source checksum
```

et idéalement une référence artifact-backed vers la source.

---

# 64. `ReconciliationManifest`

La spécification de réconciliation prévoit déjà :

```text
pinned source snapshots
matching policy versions
tolerance policy versions
normalization versions
FX snapshot
```

Le manifest doit formaliser ces coordonnées.

---

# 65. Structure

```text
ReconciliationManifest
|
+-- definition_id/version/checksum
+-- source_A_ref/checksum
+-- source_B_ref/checksum
+-- normalization_policy
+-- matching_policy
+-- tolerance_policy
+-- FX snapshot
+-- strategy versions
+-- result snapshot checksum
```

---

# 66. Reconciliation deterministic replay

À coordonnées identiques :

```text
same deterministic candidates
same accepted deterministic matches
same differences
same snapshot checksum
```

hors décisions humaines explicitement capturées.

---

# 67. Human decisions

Lorsqu'un run inclut une décision humaine :

```text
manual match approval
manual classification
manual override
```

elle doit devenir un input explicite de replay.

---

# 68. `DecisionRef`

Structure possible :

```text
decision_id
decision_type
actor_id
occurred_at
decision_payload_checksum
```

---

# 69. `ConsolidationManifest`

La consolidation nécessite un manifest riche.

Il doit pinner :

```text
scope
ownership
source entity snapshots
mapping
FX
consolidation policies
elimination policies
adjustments
sign-offs
```

---

# 70. Consolidation principle

```text
same entity snapshots
+
same scope
+
same ownership
+
same FX
+
same policies
+
same adjustments
=
same consolidated result
```

---

# 71. Structure

```text
ConsolidationManifest
|
+-- group_id
+-- period
+-- scope_version
+-- ownership_version
+-- source_snapshot_refs
+-- mapping_set
+-- FX_snapshot
+-- consolidation_policy_set
+-- adjustment_refs
+-- elimination_strategy_versions
+-- result_checksum
```

---

# 72. `SemanticManifest`

Le document `31_PYACCOUNTINGKIT_FINANCIAL_SEMANTIC_LAYER_ARCHITECTURE.md` définit déjà un `SemanticManifest`.

Ce manifest appartient naturellement à cette architecture transverse.

---

# 73. Semantic coordinates

```text
pyaccountingkit_version
semantic_model_version
dataset_definition_version
metric_definition_set_version
reference_standard
reference_edition
mapping_versions
source_snapshot_ids
source_snapshot_checksums
currency_policy_version
generated_at
output_checksum
```

---

# 74. Manifest family

La cible peut être représentée ainsi :

```text
ComputationManifest
|
+-- ClosingManifest
+-- StatementGenerationManifest
+-- RegulatoryExportManifest
+-- FinancialAnalysisManifest
+-- ImportManifest
+-- ReconciliationManifest
+-- ConsolidationManifest
+-- SemanticManifest
```

---

# 75. Héritage technique ?

Cette hiérarchie est conceptuelle.

L'implémentation Python peut utiliser :

```text
composition
Protocol
base dataclass
discriminated union
```

Le choix technique ne doit pas rigidifier inutilement le domaine.

---

# 76. Manifest immutability

Tout manifest lié à un résultat publié est immutable.

Correction :

```text
new manifest
+
new result revision
```

Pas :

```text
edit historical manifest
```

---

# 77. Manifest status

Si nécessaire :

```text
DRAFT
SEALED
PUBLISHED
SUPERSEDED
```

Mais un `PUBLISHED` reste immutable.

---

# 78. Freshness

Le manifest doit permettre de déterminer si le résultat est :

```text
CURRENT
STALE
```

---

# 79. Staleness

Un résultat devient stale lorsqu'une dépendance pinée possède désormais une version ou un checksum plus récent pertinent.

Exemples :

```text
source journal changed
period reopened
mapping changed
policy changed
reference upgraded
FX source revised
definition changed
```

---

# 80. Stale != invalid

Un snapshot historique stale peut rester :

```text
valid historical evidence
```

tout en n'étant plus le résultat courant.

---

# 81. No historical rewrite

Principe :

```text
staleness
does not mutate history
```

La nouvelle vérité courante est représentée par :

```text
new run
new snapshot
new manifest
```

---

# 82. Replay

Le framework doit distinguer :

```text
REPLAY
RECOMPUTE
RERUN
REBUILD
```

---

# 83. Replay

Reproduire une computation historique avec les coordonnées pinées.

---

# 84. Recompute

Calculer à nouveau avec les versions actuelles.

---

# 85. Rerun

Nouvelle exécution dans le même contexte logique mais pouvant avoir de nouveaux IDs et timestamps.

---

# 86. Rebuild

Reconstruire un artifact physique à partir d'un résultat sémantique figé.

---

# 87. Replay target

Un replay doit produire :

```text
ReplayEvidence
```

contenant :

```text
expected_checksum
actual_checksum
match_status
differences
```

---

# 88. Replay statuses

```text
MATCH
SEMANTIC_MISMATCH
INPUT_MISSING
VERSION_UNAVAILABLE
UNSUPPORTED
```

---

# 89. Replay fail-closed

Si une dépendance pinée est absente :

```text
do not silently use current version
```

Retour :

```text
VERSION_UNAVAILABLE
```

---

# 90. Replay evidence

Structure :

```text
ReplayEvidence
|
+-- source_manifest_id
+-- replay_run_id
+-- expected_result_checksum
+-- actual_result_checksum
+-- status
+-- differences
+-- executed_at
```

---

# 91. Version availability

Pour reproduire historiquement un calcul, PyAccountingKit doit pouvoir retrouver :

```text
definition version
mapping version
policy version
reference snapshot
```

Le manifest seul ne suffit pas si les versions historiques sont détruites.

---

# 92. Retention requirement

Tout objet piné par un manifest publié doit suivre une policy de rétention compatible avec le besoin de replay.

---

# 93. Content-addressed artifacts

Une stratégie utile est :

```text
artifact by checksum
```

Exemple :

```text
sha256/<checksum>
```

pour les sources brutes ou certains artifacts.

---

# 94. Object storage

Le stockage physique peut être :

```text
filesystem
S3-compatible object storage
Azure Blob
database
```

via ports/adapters.

Le manifest contient une référence abstraite.

---

# 95. `ArtifactRef`

Structure :

```text
artifact_id
content_type
checksum
size?
storage_ref?
```

---

# 96. Artifact location not semantic

Le chemin physique ou URL ne doit pas participer au checksum sémantique.

---

# 97. Canonical hashing algorithm

La baseline utilise SHA-256.

Recommandation :

```text
SHA-256
```

comme algorithme canonique initial pour :

```text
snapshots
definitions
manifests
artifacts
```

---

# 98. Algorithm agility

Le contrat doit toutefois identifier :

```text
checksum_algorithm
```

ou considérer SHA-256 comme une convention versionnée.

---

# 99. Example checksum ref

```text
sha256:6f5902ac...
```

---

# 100. No Python hash()

Interdit pour une preuve durable :

```python
hash(obj)
```

car non stable entre environnements/processus.

---

# 101. Source code identity

La version package constitue la référence principale.

Pour qualification avancée, le manifest peut également capturer :

```text
source_revision
```

exemple :

```text
git commit SHA
```

si disponible.

---

# 102. Package artifact checksum

Une release qualifiée peut pinner :

```text
wheel SHA-256
```

dans les manifests de preuve.

Cela n'est pas obligatoire pour chaque computation runtime.

---

# 103. Environment pinning

La reproductibilité financière ne doit pas dépendre de l'ensemble du lockfile Python si les dépendances externes ne modifient pas la sémantique.

Mais les éléments susceptibles d'affecter le calcul doivent être connus.

---

# 104. Decimal context

Si une computation dépend :

```text
precision
rounding mode
```

ces paramètres doivent être explicitement pinés.

---

# 105. Rounding policy

En comptabilité, le rounding doit relever de :

```text
RoundingPolicy
```

plutôt que d'un paramètre Python global implicite.

---

# 106. Timezone

Les timestamps sont timezone-aware.

La timezone ne doit pas modifier un résultat comptable basé sur une date métier si ce n'est pas prévu.

---

# 107. Locale

La locale ne doit affecter que :

```text
presentation
```

et non :

```text
calculation
```

---

# 108. Randomness

Les computations comptables canoniques doivent être déterministes.

Aucune randomness implicite.

---

# 109. Future probabilistic analysis

Si un futur module probabiliste utilise un seed :

```text
seed
```

devra être piné dans son manifest.

Ce n'est pas un besoin core actuel.

---

# 110. External observations

Toute donnée externe influençant un résultat doit être snapshotée ou pinée.

Exemples :

```text
FX rate
index
market reference used for accounting measurement
external confirmation
```

---

# 111. No live external lookup during replay

Un replay historique ne doit pas appeler :

```text
current FX API
current regulatory API
latest mapping service
```

Il utilise les observations pinées.

---

# 112. Reproducibility boundary

Les effets externes non déterministes doivent être convertis en :

```text
immutable input snapshots
```

avant computation.

---

# 113. Manifest repository

Un port possible :

```text
ComputationManifestRepositoryProtocol
```

---

# 114. Responsibilities

```text
save sealed manifest
get by id
find by result snapshot
find by correlation
```

---

# 115. Manifest store

Peut être implémenté via :

```text
database
object storage
artifact store
```

sans modifier le domaine.

---

# 116. Public API

Surface possible :

```text
accounting.reproducibility
```

---

# 117. API examples

```python
manifest = accounting.reproducibility.get_manifest(
    manifest_id
)
```

```python
evidence = accounting.reproducibility.replay(
    manifest_id
)
```

```python
lineage = accounting.reproducibility.explain(
    result_snapshot_id
)
```

---

# 118. No raw repository exposure

L'utilisateur ne manipule pas directement le repository de manifests dans l'usage normal.

---

# 119. Provenance API

Résultat possible :

```text
ComputationLineage
```
avec :

```text
sources
definitions
mappings
policies
result
exports
```

---

# 120. Relationship with Domain Events

Le computation manifest peut référencer :

```text
correlation_id
```

et éventuellement :

```text
trigger_event_id
```

---

# 121. Event != manifest

Un DomainEvent décrit :

```text
what happened
```

Un ComputationManifest décrit :

```text
under which coordinates the result was computed
```

---

# 122. Relationship with Audit

Audit répond :

```text
who did what
```

Manifest répond :

```text
with what inputs and versions
```

Les deux se complètent.

---

# 123. Relationship with Evidence Bundles

Un manifest peut faire partie d'un :

```text
EvidenceBundle
```

contenant :

```text
manifest
snapshot
controls
audit refs
artifact checksums
qualification report
```

---

# 124. Release evidence

Les release gates peuvent produire :

```text
manifest schema checksum
snapshot schema manifest
public API manifest
adapter contract manifest
architecture contract manifest
domain event manifest
```

---

# 125. `COMPUTATION_MANIFEST_SCHEMA.json`

Artifact recommandé :

```text
COMPUTATION_MANIFEST_SCHEMA.json
```

Il décrit la structure des différents manifests.

---

# 126. `COMPUTATION_MANIFEST_REGISTRY.json`

Option possible :

```text
COMPUTATION_MANIFEST_REGISTRY.json
```

listant :

```text
manifest type
schema version
owner context
serializer
status
```

---

# 127. Contract versioning

Chaque manifest spécialisé possède :

```text
schema_version
```

---

# 128. Breaking manifest change

Exemples :

```text
remove required version coordinate
change checksum semantics
change source identity semantics
```

=> nouvelle version.

---

# 129. Manifest backward compatibility

Les old manifests publiés doivent rester lisibles selon la policy annoncée.

---

# 130. Upcasters

Un manifest historique peut être :

```text
upcast to canonical in-memory representation
```

sans réécrire l'original.

---

# 131. Historical preservation

Le JSON original ou l'artifact original doit rester conservé si requis par l'audit.

---

# 132. Manifest canonical serialization

Le manifest doit être sérialisable de manière déterministe.

Exemple :

```text
JSON canonical-like representation
```

---

# 133. Manifest content rules

Inclure :

```text
all semantic inputs
all versioned rules
all relevant parameters
result checksum
```

Éviter :

```text
debug logs
temporary cache keys
database connection details
secret values
```

---

# 134. Secrets

Aucun manifest ne contient :

```text
password
API token
database credentials
private key
```

---

# 135. Sensitive references

Utiliser :

```text
opaque artifact reference
```

plutôt que contenu sensible lorsque cela suffit.

---

# 136. Multi-tenant

Chaque manifest doit être scoped lorsqu'approprié par :

```text
tenant/accounting_entity
```

---

# 137. Cross-tenant replay

Interdit par défaut.

Le replay ne doit pas pouvoir charger une source appartenant à un autre tenant.

---

# 138. Access control

Les manifests peuvent exposer des métadonnées sensibles sur :

```text
financial periods
entities
sources
```

Ils doivent suivre les contrôles d'accès de l'application consommatrice.

---

# 139. Observability

Métriques possibles :

```text
computation_manifest_created_total
computation_replay_total
computation_replay_mismatch_total
stale_snapshot_total
missing_pinned_dependency_total
```

---

# 140. Logs

Les logs de replay peuvent inclure :

```text
manifest_id
manifest_type
result_checksum
correlation_id
```

mais pas nécessairement le contenu financier complet.

---

# 141. Error taxonomy

```text
ReproducibilityError
|
+-- ManifestNotFoundError
+-- ManifestIntegrityError
+-- ManifestVersionUnsupportedError
+-- PinnedDependencyMissingError
+-- SourceChecksumMismatchError
+-- DefinitionChecksumMismatchError
+-- MappingChecksumMismatchError
+-- PolicyChecksumMismatchError
+-- ReplayMismatchError
+-- ArtifactIntegrityError
+-- NonDeterministicComputationError
```

---

# 142. Fail-closed conditions

Le replay doit échouer si :

```text
source checksum differs
definition version unavailable
mapping checksum mismatches
policy unavailable
manifest checksum invalid
artifact checksum invalid
```

---

# 143. No implicit fallback

Interdit :

```text
v3 unavailable
→ use latest v5
```

dans un replay historique.

---

# 144. Warnings

Les cas non critiques peuvent produire :

```text
environment metadata differs
package patch differs but declared semantically compatible
artifact rebuilt with different physical format
```

selon policy explicite.

---

# 145. Deterministic computation test

Pattern :

```text
run A
same inputs
same versions
same parameters

run B
same inputs
same versions
same parameters

assert:
semantic_checksum(A) == semantic_checksum(B)
```

---

# 146. Golden tests

Créer des golden manifests.

---

# 147. Golden — Statement

```text
TrialBalance S1
StatementDefinition D1
MappingSet M1
Reference R1

Expected:
ReportSnapshot checksum = X
```

---

# 148. Golden — Analysis

```text
ReportSnapshot S2
DefinitionSet A3

Expected:
AnalysisSnapshot checksum = Y
```

---

# 149. Golden — Import

```text
Raw FEC artifact checksum F1
Parser P1
Mapping M2

Expected:
Normalized output checksums = (...)
```

---

# 150. Golden — Reconciliation

```text
Source A
Source B
MatchingPolicy M4
Tolerance T2

Expected:
ReconciliationSnapshot checksum = R
```

---

# 151. Golden — Consolidation

```text
Entity snapshots
scope
ownership
FX
policies
eliminations

Expected:
ConsolidationSnapshot checksum = C
```

---

# 152. Golden — Semantic

```text
Financial snapshots
SemanticModel V1
MetricDefinitionSet V3

Expected:
SemanticSnapshot checksum = S
```

---

# 153. Property-based tests

Exemples :

```text
serialization order does not change checksum
```

```text
metadata excluded from semantic checksum does not alter result checksum
```

```text
same Decimal values produce same checksum
```

---

# 154. Mutation test

Une modification d'un input piné doit changer :

```text
manifest checksum
```

et généralement :

```text
result checksum
```

si la modification est sémantiquement pertinente.

---

# 155. Freshness tests

```text
source unchanged
→ CURRENT
```

```text
source checksum changed
→ STALE
```

---

# 156. Replay qualification

Tests :

```text
exact replay
missing dependency
checksum mismatch
unsupported manifest schema
historical version
```

---

# 157. Cross-adapter replay

La même computation avec :

```text
InMemory source adapter
SQL source adapter
```

doit produire le même résultat sémantique si les inputs canoniques sont identiques.

---

# 158. Database independence

Les IDs de lignes SQL ne doivent pas participer au checksum si leur identité n'est pas métier.

---

# 159. Order independence

Le résultat ne doit pas dépendre de l'ordre arbitraire retourné par une base.

---

# 160. Architecture Fitness Functions

Règles proposées :

```text
AFF-REPRO-001
published computations must expose a manifest or equivalent pinned coordinates

AFF-REPRO-002
manifest core must not depend on adapters

AFF-REPRO-003
semantic checksums must not use Python hash()

AFF-REPRO-004
published manifests are immutable

AFF-REPRO-005
historical replay must not resolve "latest" dependencies

AFF-REPRO-006
Money serialization must remain Decimal-safe
```

---

# 161. Package topology

Dans la topologie actuelle :

```text
pyaccountingkit/
├── core/
│   └── checksums.py
├── domain/
│   └── reproducibility/
├── application/
│   └── reproducibility/
├── ports/
│   └── manifests.py
└── adapters/
    └── manifests/
```

---

# 162. Future domain-first topology

```text
reproducibility/
├── domain/
├── application/
├── ports/
└── adapters/
```

ou bien une capability transverse minimale.

Le choix doit éviter un nouveau god-context.

---

# 163. Reproducibility as cross-cutting capability

Recommandation :

```text
manifest primitives
```

peuvent être partagées,

mais chaque bounded context reste propriétaire de son manifest spécialisé.

Exemple :

```text
reporting
    owns StatementGenerationManifest

analysis
    owns FinancialAnalysisManifest

reconciliation
    owns ReconciliationManifest
```

---

# 164. No central business knowledge

Le package générique de reproducibility ne doit pas connaître la formule d'EBITDA ou la structure d'un rapprochement.

Il fournit :

```text
hashing
canonical references
manifest primitives
replay contracts
```

---

# 165. Public manifests

Tous les manifests ne sont pas nécessairement publics.

Visibilité :

```text
INTERNAL
AUDIT
PUBLIC_INTEGRATION
```

---

# 166. Manifest privacy

Un manifest public ne doit pas exposer inutilement :

```text
internal storage paths
PII
infrastructure identifiers
```

---

# 167. Audit export

Une API peut générer :

```text
ManifestSummary
```

sans exposer toutes les métadonnées internes.

---

# 168. Human-readable explanation

Une computation doit pouvoir produire une explication :

```text
Generated with:
- PyAccountingKit 0.7.0rc1
- PCG 2026 snapshot ...
- Statement Definition v4
- Mapping Set v8
- Trial Balance checksum ...
```

---

# 169. Machine-readable + human-readable

Les deux sont nécessaires.

```text
JSON manifest
+
formatted explanation
```

---

# 170. Integration with semantic layer

La semantic layer peut utiliser les manifests pour afficher :

```text
metric lineage
dataset provenance
freshness
```

---

# 171. Integration with events

Lorsqu'une computation publiée émet un DomainEvent :

```text
manifest_id
```

peut être référencé dans l'événement ou son metadata.

---

# 172. Example

```text
FinancialStatementPublished
    report_snapshot_id
    manifest_id
    result_checksum
```

---

# 173. Integration with outbox

L'outbox transporte une référence au résultat publié, pas nécessairement tout le manifest.

---

# 174. Integration with closing

Un `AccountingPeriodClosed` event peut référencer :

```text
ClosingManifestId
```

---

# 175. Integration with audit

Audit peut référencer :

```text
manifest_id
```

pour expliquer la computation ayant produit un artifact.

---

# 176. Evidence bundle chain

```text
Audit Event
     │
     ├── ComputationManifest
     │       ├── Inputs
     │       ├── Policies
     │       ├── Mappings
     │       └── Result checksum
     │
     └── Published Artifact
             └── payload checksum
```

---

# 177. Release qualification

Le framework doit qualifier :

```text
manifest schema stability
snapshot schema stability
canonical checksum stability
golden replay stability
```

---

# 178. Schema manifest integration

`SNAPSHOT_SCHEMA_MANIFEST.json` reste la référence structurelle des snapshots.

Ajouter éventuellement :

```text
COMPUTATION_MANIFEST_SCHEMA.json
```

---

# 179. Stable checksum policy

Les règles de checksum elles-mêmes constituent un contrat.

Un changement de :

```text
included fields
normalization
sorting
decimal formatting
```

peut modifier tous les checksums.

Il doit donc être versionné.

---

# 180. `checksum_schema_version`

Option recommandée :

```text
checksum_schema_version
```

ou une convention équivalente.

---

# 181. Checksum migration

Une nouvelle version de checksum ne doit pas invalider silencieusement les historiques.

Conserver :

```text
algorithm
schema version
checksum
```

---

# 182. Manifest example

```json
{
  "manifest_id": "manifest:statement:2026:001",
  "manifest_type": "STATEMENT_GENERATION",
  "manifest_schema_version": "1",
  "pyaccountingkit_version": "0.7.0rc1",
  "accounting_entity_id": "entity:42",
  "source_inputs": [
    {
      "source_type": "TRIAL_BALANCE",
      "source_id": "tb:2026-10",
      "checksum": "sha256:..."
    }
  ],
  "definitions": [
    {
      "id": "balance-sheet",
      "version": "4",
      "checksum": "sha256:..."
    }
  ],
  "mappings": [
    {
      "id": "statement-map",
      "version": "8",
      "checksum": "sha256:..."
    }
  ],
  "result_checksum": "sha256:...",
  "manifest_checksum": "sha256:..."
}
```

---

# 183. Example closing chain

```text
TrialBalance BEFORE_ADJUSTMENTS
        ↓
ClosingManifest
        ├── PolicySet
        ├── ClosingRules
        ├── GeneratedEntries
        └── Controls
        ↓
TrialBalance POST_CLOSING
        ↓
AccountingPeriodClosed
```

---

# 184. Example analysis chain

```text
FinancialStatementSnapshot
        ↓
FinancialAnalysisManifest
        ├── DefinitionSet
        ├── Trend definitions
        └── Diagnostic definitions
        ↓
AnalysisSnapshot
```

---

# 185. Example semantic chain

```text
ReportSnapshot
AnalysisSnapshot
        ↓
SemanticManifest
        ├── SemanticModel
        ├── Metric definitions
        └── Currency policy
        ↓
SemanticSnapshot
```

---

# 186. Initial roadmap

## REP-00 — Checksum primitives

```text
canonical serialization
SHA-256 helpers
checksum refs
```

---

## REP-01 — Generic manifest primitives

```text
ManifestId
ManifestType
SourceInputRef
VersionedRef
ComputationManifest
```

---

## REP-02 — Reporting manifest

```text
StatementGenerationManifest
```

aligné avec `ReportSnapshot`.

---

## REP-03 — Analysis manifest
```text
FinancialAnalysisManifest
```

aligné avec `AnalysisSnapshot`.

---

## REP-04 — Regulatory export manifest

Alignement avec :

```text
RegulatoryExportArtifact
```

---

## REP-05 — Import manifest

```text
ImportManifest
```

---

## REP-06 — Replay API

```text
ReplayEvidence
ReplayStatus
```

---

## REP-07 — Reconciliation / Consolidation manifests

---

## REP-08 — Semantic manifest integration

---

## REP-09 — Manifest schema / release gates

```text
COMPUTATION_MANIFEST_SCHEMA.json
golden replay qualification
```

---

# 187. Priorités

| Lot | Priorité |
|---|---:|
| REP-00 | P0 |
| REP-01 | P0 |
| REP-02 | P0 |
| REP-03 | P0 |
| REP-04 | P1 |
| REP-05 | P1 |
| REP-06 | P1 |
| REP-07 | P2 |
| REP-08 | P2 |
| REP-09 | P1 |

---

# 188. ADR proposées

| ADR | Décision |
|---|---|
| ADR-REP-001 | Toute computation publiée doit être reproductible ou déclarer explicitement ses limites |
| ADR-REP-002 | Les inputs de replay sont pinés par version et checksum |
| ADR-REP-003 | `LATEST` n'est jamais une coordonnée acceptable dans un manifest publié |
| ADR-REP-004 | Schema Manifest, Computation Manifest et Result Snapshot sont distincts |
| ADR-REP-005 | `ComputationManifest` est le contrat transverse de provenance d'exécution |
| ADR-REP-006 | Les manifests publiés sont immuables |
| ADR-REP-007 | Un changement de source rend un résultat stale sans réécrire l'historique |
| ADR-REP-008 | Stale ne signifie pas historiquement invalide |
| ADR-REP-009 | Les checksums canoniques utilisent SHA-256 initialement |
| ADR-REP-010 | Python `hash()` est interdit pour les preuves durables |
| ADR-REP-011 | Les montants sont sérialisés en Decimal string |
| ADR-REP-012 | Les collections non ordonnées sont canonicalisées avant checksum |
| ADR-REP-013 | Les timestamps opérationnels n'entrent pas dans un checksum sémantique sauf besoin métier |
| ADR-REP-014 | Package version et versions métier restent distinctes |
| ADR-REP-015 | Les policies applicables sont pinées explicitement |
| ADR-REP-016 | Les mappings applicables sont pinés explicitement |
| ADR-REP-017 | Les données réglementaires sont pinées via ReferenceSnapshot |
| ADR-REP-018 | Les observations externes influençant le calcul sont snapshotées |
| ADR-REP-019 | Un replay historique ne consulte pas les données externes courantes |
| ADR-REP-020 | Un replay n'utilise jamais silencieusement une version de remplacement |
| ADR-REP-021 | Missing pinned dependency est une erreur fail-closed |
| ADR-REP-022 | Replay et recompute sont deux opérations distinctes |
| ADR-REP-023 | Replay ne modifie jamais le snapshot historique |
| ADR-REP-024 | Les versions historiques nécessaires au replay suivent une policy de rétention |
| ADR-REP-025 | Semantic checksum et artifact checksum restent distincts |
| ADR-REP-026 | Les manifests ne contiennent aucun secret |
| ADR-REP-027 | Les storage locations ne font pas partie de la sémantique |
| ADR-REP-028 | Le manifest peut référencer CorrelationId sans devenir un DomainEvent |
| ADR-REP-029 | AuditEvent et ComputationManifest restent distincts |
| ADR-REP-030 | EvidenceBundle peut agréger manifests, snapshots, audit et artifacts |
| ADR-REP-031 | Chaque bounded context possède son manifest spécialisé |
| ADR-REP-032 | Le core de reproducibility ne contient pas de règles métier spécialisées |
| ADR-REP-033 | Les manifest schemas sont versionnés |
| ADR-REP-034 | Les checksum semantics sont versionnées |
| ADR-REP-035 | Les golden replay tests participent aux release gates |
| ADR-REP-036 | Cross-adapter equivalence est testée sur les résultats sémantiques |
| ADR-REP-037 | Les IDs techniques de base de données n'entrent pas dans les checksums métier |
| ADR-REP-038 | La locale ne doit pas modifier les calculs |
| ADR-REP-039 | Les règles de rounding sont explicites et versionnées |
| ADR-REP-040 | La reproductibilité devient une capacité de première classe de PyAccountingKit |

---

# 189. Architecture Fitness Functions associées

```text
AFF-REPRO-001
published result must expose replay coordinates

AFF-REPRO-002
manifest primitives must not depend on adapters

AFF-REPRO-003
durable checksum must not use Python hash()

AFF-REPRO-004
published manifest must be immutable

AFF-REPRO-005
historical replay must not resolve current/latest dependencies

AFF-REPRO-006
Money checksum serialization must be Decimal-safe
```

---

# 190. Definition of Done — primitives

```text
[ ] ManifestId défini
[ ] ManifestType défini
[ ] VersionedRef défini
[ ] SourceInputRef défini
[ ] checksum convention documentée
[ ] canonical serialization documentée
[ ] manifest checksum défini
[ ] result checksum distinction définie
```

---

# 191. Definition of Done — reporting & analysis

```text
[ ] StatementGenerationManifest défini
[ ] alignement ReportSnapshot documenté
[ ] FinancialAnalysisManifest défini
[ ] alignement AnalysisSnapshot documenté
[ ] regulatory export manifest défini
[ ] artifact checksum vs semantic checksum testé
```

---

# 192. Definition of Done — replay

```text
[ ] ReplayStatus défini
[ ] ReplayEvidence défini
[ ] missing dependency fail-closed
[ ] stale source détectée
[ ] checksum mismatch détecté
[ ] exact replay test vert
[ ] historical version test vert
[ ] no latest fallback test vert
```

---

# 193. Definition of Done — release

```text
[ ] COMPUTATION_MANIFEST_SCHEMA.json généré
[ ] schema compatibility gate vert
[ ] checksum semantics versionnées
[ ] golden manifests versionnés
[ ] replay mismatch report généré
[ ] architecture fitness rules vertes
```

---

# 194. Matrice des manifests

| Manifest | Sources principales | Definitions / Policies | Résultat |
|---|---|---|---|
| ClosingManifest | TrialBalance / Ledger | Closing + PolicySet | Closed Period / TB |
| StatementGenerationManifest | TrialBalance | StatementDefinition + MappingSet | ReportSnapshot |
| RegulatoryExportManifest | ReportSnapshot | Profile + ExportDefinition | ExportArtifact |
| FinancialAnalysisManifest | Report/Analysis Source | DefinitionSet | AnalysisSnapshot |
| ImportManifest | Raw Artifact | Parser + Mapping + Policy | Imported entries |
| ReconciliationManifest | Source snapshots | Matching/Tolerance policies | ReconciliationSnapshot |
| ConsolidationManifest | Entity snapshots | Scope/FX/Policies | ConsolidationSnapshot |
| SemanticManifest | Financial snapshots | SemanticModel + Metrics | SemanticSnapshot |

---

# 195. Risques

## Risque 1 — Manifest trop volumineux

Mitigation :

```text
reference by checksum/id
not full embedded content
```

---

## Risque 2 — Duplication avec snapshots

Mitigation :

```text
snapshot = result
manifest = execution coordinates
```

---

## Risque 3 — Faux replay

Un replay qui utilise les dernières policies n'est pas un replay.

Mitigation :

```text
strict pinned dependency resolution
```

---

## Risque 4 — Checksum instable

Mitigation :

```text
canonical serialization
versioned checksum rules
golden tests
```

---

## Risque 5 — Historique impossible à rejouer

Mitigation :

```text
retention of pinned definitions and snapshots
```

---

# 196. Positionnement global

```text
                    VERSIONED INPUTS
                         │
        ┌────────────────┼─────────────────┐
        │                │                 │
   Snapshots         Policies         Definitions
        │                │                 │
        └────────────────┼─────────────────┘
                         │
                    Mappings
                         │
                         ▼
               ComputationManifest
                         │
                         ▼
                  Computation
                         │
                         ▼
                  ResultSnapshot
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
         Domain Event          Export Artifact
              │                     │
              └──────────┬──────────┘
                         ▼
                    EvidenceBundle
```

---

# 197. Principe final

Une production financière importante doit être capable de répondre :

```text
WHAT was produced?
FROM WHICH inputs?
WITH WHICH versions?
UNDER WHICH policies?
USING WHICH mappings?
WITH WHICH framework version?
WITH WHICH checksum?
CAN IT BE replayed?
```

---

# 198. Conclusion

PyAccountingKit possède déjà plusieurs mécanismes de reproductibilité de haut niveau :

```text
immutable snapshots
source checksums
definition versions
mapping versions
analysis checksums
artifact checksums
snapshot schema manifest
```

La prochaine étape consiste à les harmoniser.

La cible devient :

```text
ONE COMPUTATION
      ↓
ONE SEALED MANIFEST
      ↓
PINNED INPUTS
      ↓
PINNED RULES
      ↓
DETERMINISTIC OUTPUT
      ↓
VERIFIABLE CHECKSUM
      ↓
REPLAYABLE EVIDENCE
```

Le principe de conception est :

> **Un résultat financier publié ne doit pas seulement être correct aujourd'hui ; il doit rester explicable et, lorsque les dépendances historiques sont disponibles, reproductible demain.**