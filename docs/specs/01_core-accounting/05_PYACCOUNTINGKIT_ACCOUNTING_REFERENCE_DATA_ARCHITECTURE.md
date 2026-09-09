# 05 - PyAccountingKit - Architecture des Accounting Reference Data

> **Projet** : PyAccountingKit  
> **Document** : `05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md`  
> **Documents parents** :
> - `00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`
> - `01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`
> - `02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`
> - `03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md`
> - `04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md`
> **Statut** : P0.6 - Contrat détaillé avec `regulatory-accounting-data-framework`  
> **Langue** : Français  
> **Objet** : Définir le bounded context `Accounting Reference Data`, les contrats de lecture de `regulatory-accounting-data-framework`, les objets de référence exposés à PyAccountingKit, les stratégies de snapshot/versioning, les règles relatives aux effective plans, overlays, relations, crosswalks, concepts et reporting réglementaire.

---

# 1. Résumé exécutif

`regulatory-accounting-data-framework` constitue la **source de vérité réglementaire structurée** de PyAccountingKit.

PyAccountingKit ne doit pas :

```text
recopier les référentiels
reconstruire arbitrairement les hiérarchies
inventer une relation d'héritage
valider automatiquement un crosswalk candidat
déduire une équivalence sémantique d'un code identique
exécuter un account hint déclaré non exécutable
inventer des concept bindings absents
coupler le domaine à un chemin de repository
```

Le contrat cible est :

```text
regulatory-accounting-data-framework
          |
          v
AccountingReferenceProvider
          |
          v
ReferenceCatalog
          |
          +--> ReferenceStandard
          +--> ReferenceStructure
          +--> ReferenceAccount
          +--> EffectiveAccountPlan
          +--> ReferenceRelations
          +--> ReferenceCrosswalks
          +--> ReferenceConceptRegistry
          +--> ReferenceReportingModel
          |
          v
AccountingReferenceSnapshot
          |
          +------------------------+
          |                        |
          v                        v
Accounting Policies        Company Chart of Accounts
& Measurement
```

Le framework réglementaire reste propriétaire des **données de référence**.

PyAccountingKit reste propriétaire :

```text
de leur consommation
de leur snapshot
de leur association à une entité
de leur transformation en plan d'entreprise
de leur utilisation dans les policies
de leur utilisation dans le reporting
```

---

# 2. Sources réglementaires observées

Le contrat est conçu à partir des artefacts actuellement disponibles dans `regulatory-accounting-data-framework`.

## 2.1 Structures v1

Exemples :

```text
datasets/structured/
├── syscohada_2017_v1_structure.json
├── pcg_2026_v1_structure.json
├── nonprofit_2026_v1_effective_plan.json
├── nonprofit_2026_v1_account_overlay.json
└── ebnl_2023_v1_structure.json
```

---

## 2.2 Reporting v3

Exemples :

```text
datasets/reporting/
├── syscohada_2017_v3_reporting.json
├── pcg_2026_v3_reporting.json
├── nonprofit_2026_v3_reporting.json
└── ebnl_2023_v3_reporting.json
```

---

## 2.3 Relations

```text
datasets/relations/
└── ohada_accounting_standard_relations.json
```

---

## 2.4 Crosswalks

```text
datasets/crosswalk/
└── ebnl_2023_vs_syscohada_2017_structural_delta.json
```

---

## 2.5 Concepts

```text
datasets/concepts/
└── accounting_core_concepts_v0.json
```

---

## 2.6 Raw / intermediate sources

Exemples :

```text
datasets/raw/
├── syscohada_2017_v0_raw.json
├── pcg_2026_v0_raw.json
├── nonprofit_2026_art_320_2_specific_accounts.json
└── ebnl_2023_v0_reviewed_structure.json
```

Les couches raw ne sont pas le contrat runtime privilégié de PyAccountingKit.

---

# 3. Principe d'autorité

La responsabilité est séparée ainsi :

```text
regulatory-accounting-data-framework
    = ce que la source réglementaire structurée affirme

PyAccountingKit
    = comment une application comptable consomme cette affirmation
```

Cette séparation doit rester stricte.

---

# 4. Anti-Corruption Layer

PyAccountingKit ne doit pas importer directement les schémas JSON dans son domaine.

Il utilise :

```text
External Regulatory Dataset
       |
       v
Regulatory Adapter
       |
       v
Accounting Reference Port
       |
       v
PyAccountingKit Reference Model
```

L'adapter agit comme Anti-Corruption Layer.

---

# 5. Port principal - `AccountingReferenceProvider`

Contrat cible :

```python
from typing import Protocol

class AccountingReferenceProvider(Protocol):

    def get_standard(
        self,
        standard_id: str,
        edition: str | None = None,
    ) -> "ReferenceStandard":
        ...

    def list_standards(
        self,
    ) -> tuple["ReferenceStandardSummary", ...]:
        ...

    def get_structure(
        self,
        standard_id: str,
        edition: str,
    ) -> "ReferenceStructure":
        ...

    def get_effective_plan(
        self,
        standard_id: str,
        edition: str,
    ) -> "EffectiveAccountPlan":
        ...

    def get_reporting_model(
        self,
        standard_id: str,
        edition: str,
    ) -> "ReferenceReportingModel | None":
        ...

    def get_relations(
        self,
        standard_id: str,
        edition: str,
    ) -> tuple["ReferenceRelation", ...]:
        ...

    def get_crosswalk(
        self,
        source_standard: str,
        source_edition: str,
        target_standard: str,
        target_edition: str,
    ) -> "ReferenceCrosswalk | None":
        ...

    def get_concepts(
        self,
    ) -> "ReferenceConceptRegistry | None":
        ...

    def create_snapshot(
        self,
        request: "ReferenceSnapshotRequest",
    ) -> "AccountingReferenceSnapshot":
        ...
```

---

# 6. Responsabilités du provider

Le provider doit :

```text
charger
valider le format attendu
normaliser vers le modèle PyAccountingKit
conserver les identifiants réglementaires
conserver la provenance
conserver les statuts de validation
conserver les contraintes négatives
conserver les flags human-review / executable
exposer une version stable
permettre un snapshot
```

---

# 7. Ce que le provider ne fait pas

Il ne doit pas :

```text
générer un plan comptable d'entreprise
choisir une AccountingPolicy
poster une écriture
inventer une correspondance
modifier un référentiel source
corriger silencieusement les données
```

---

# 8. `ReferenceCatalog`

Le `ReferenceCatalog` fournit une vue applicative des référentiels disponibles.

```text
ReferenceCatalog
|
+-- standards
+-- editions
+-- dataset_versions
+-- capabilities
```

---

# 9. `ReferenceStandard`

```text
ReferenceStandard
|
+-- standard_id
+-- edition
+-- label?
+-- family_id?
+-- jurisdiction?
+-- sector?
+-- dataset_version
+-- capabilities
+-- provenance
```

L'existence exacte de certains champs dépend des sources.

Le modèle PyAccountingKit les rend optionnels lorsqu'ils ne sont pas présents.

---

# 10. Identité réglementaire

Le couple minimal est :

```text
standard_id
+
edition
```

Exemples observés :

```text
fr-pcg
2026

ohada-syscohada
2017

fr-nonprofit
2026
```

---

# 11. Identifiants de noeuds

Les identifiants du framework réglementaire doivent être préservés.

Exemples :

```text
class:fr-pcg:2026:1

account:fr-pcg:2026:2718

account:ohada-syscohada:2017:7721
```

PyAccountingKit ne les remplace pas par ses UUID internes.

---

# 12. Trois identités distinctes

```text
ReferenceAccountId
    "account:fr-pcg:2026:512"

CompanyAccountId
    UUID interne

CompanyAccountCode
    "51200001"
```

Ces concepts ne doivent jamais être confondus.

---

# 13. `ReferenceStructure`

```text
ReferenceStructure
|
+-- standard_id
+-- edition
+-- dataset_layer
+-- nodes
+-- provenance
+-- checksum
```

---

# 14. Structure d'un noeud de référence

Les datasets v1 observés utilisent notamment :

```text
standard_id
edition
node_id
node_type
ref_code
label_source
parent_node_id
children_node_ids
path_codes
path_node_ids
depth
is_leaf
attributes
provenance
source_record_id
```

PyAccountingKit doit préserver ce vocabulaire plutôt que le simplifier prématurément.

---

# 15. `ReferenceNode`

```text
ReferenceNode
|
+-- id: ReferenceNodeId
+-- standard_id
+-- edition
+-- node_type
+-- ref_code
+-- label
+-- parent_id?
+-- children_ids
+-- path_codes
+-- path_node_ids
+-- depth
+-- is_leaf
+-- attributes
+-- provenance
```

---

# 16. `ReferenceNodeType`

Valeurs constatées :

```text
class
group
account
```

Le modèle doit accepter de nouvelles catégories futures sans casser l'API.

---

# 17. Hiérarchie explicite

L'arbre doit être consommé via :

```text
parent_node_id
children_node_ids
```

et non reconstruit uniquement par :

```text
longest prefix
```

Même si la source a utilisé une méthode dérivée pour reconstruire certaines relations, PyAccountingKit consomme le résultat structuré.

---

# 18. Exemple de structure

```text
class:ohada-syscohada:2017:7
    |
    +-- account:ohada-syscohada:2017:77
           |
           +-- account:ohada-syscohada:2017:772
                  |
                  +-- account:ohada-syscohada:2017:7721
                  +-- account:ohada-syscohada:2017:7722
```

---

# 19. Provenance

`ReferenceProvenance` doit pouvoir conserver :

```text
type
method
confidence
review_status
source_refs
```

---

# 20. `SourceRef`

```text
SourceRef
|
+-- document_id
+-- page_pdf?
+-- section?
+-- heading_path?
+-- snippet?
+-- source_line_md?
```

Le contrat ne doit pas rendre obligatoires les champs non disponibles dans toutes les sources.

---

# 21. Provenance source vs dérivée

Les datasets observés distinguent notamment :

```text
type = source
type = derived
```

et différents `review_status`.

PyAccountingKit conserve cette différence.

---

# 22. `ReferenceAccount`

```text
ReferenceAccount
|
+-- reference_account_id
+-- standard_id
+-- edition
+-- ref_code
+-- label
+-- parent_id?
+-- children_ids
+-- account_class?
+-- attributes
+-- provenance
```

`ReferenceAccount` est immutable côté PyAccountingKit.

---

# 23. Read-only

Le bounded context `Accounting Reference Data` est **read-only** vis-à-vis des données réglementaires externes.

Interdit :

```text
ReferenceAccount.rename()
ReferenceAccount.change_code()
ReferenceStandard.add_account()
```

Toute transformation métier doit créer un objet du domaine entreprise.

---

# 24. `EffectiveAccountPlan`

Tous les référentiels ne sont pas nécessairement de simples structures autonomes.

Certains peuvent être résolus à partir :

```text
base standard
+
extension
+
overlay
```

Le contrat runtime doit permettre de consommer directement un **effective plan**.

---

# 25. Cas `fr-nonprofit:2026`

Le dataset observé indique un plan effectif construit à partir de :

```text
base_standard = fr-pcg:2026
```

avec :

```text
inherited_from_base_standard
extension_override
extension_addition
```

Le plan effectif possède ses propres `account_id` dans le namespace :

```text
account:fr-nonprofit:2026:...
```

---

# 26. Règle essentielle - consommer l'effective plan

PyAccountingKit doit privilégier :

```text
get_effective_plan(
    standard_id="fr-nonprofit",
    edition="2026"
)
```

plutôt que :

```text
charger PCG
+
rejouer arbitrairement les overlays
```

---

# 27. Pourquoi

Parce que la résolution :

```text
base + overrides + additions
```

est une décision du framework réglementaire.

Elle ne doit pas être dupliquée dans PyAccountingKit.

---

# 28. `EffectiveReferenceAccount`

```text
EffectiveReferenceAccount
|
+-- account_id
+-- ref_code
+-- label
+-- base_account_id?
+-- base_label?
+-- origin
+-- provenance_type
+-- extension_source_ref?
```

---

# 29. `EffectiveAccountOrigin`

Valeurs observées :

```text
inherited_from_base_standard
extension_override
extension_addition
```

Le modèle doit être extensible.

---

# 30. Overlay

Le dataset d'overlay observé contient notamment :

```text
base_standard
standard_id
edition
ref_code
overlay_id
overlay_type
canonical_effect
regulatory_status
source_ref
```

---

# 31. `ReferenceOverlay`

PyAccountingKit peut exposer l'overlay à des fins :

```text
audit
diagnostic
migration
explanation
```

mais ne doit pas nécessairement l'utiliser pour construire le plan runtime si l'effective plan existe.

---

# 32. `OverlayType`

Exemples observés :

```text
same_semantics_label
label_or_semantic_override
specific_addition
```

Ces types sont informatifs.

Ils ne doivent pas déclencher de logique universelle en dehors de leur contrat explicite.

---

# 33. `canonical_effect`

Exemple observé :

```text
replace_or_add
```

PyAccountingKit peut conserver ce champ brut dans les metadata.

---

# 34. Relations entre standards

Le dataset de relations OHADA distingue plusieurs types :

```text
member_of_family

specialized_standard_within_family

sector_specialization_within_family

crosswalk
```

---

# 35. `ReferenceRelation`

```text
ReferenceRelation
|
+-- relation_id
+-- relation_type
+-- subject_ref
+-- target_ref
+-- subject_kind
+-- target_kind
+-- evidence
+-- human_review_required
+-- auto_inference_allowed
```

---

# 36. Règle - relation != héritage

Une relation :

```text
member_of_family
```

ou :

```text
specialized_standard_within_family
```

n'implique pas :

```text
inherits
```

---

# 37. Contraintes négatives

Le dataset OHADA contient des `negative_constraints`.

PyAccountingKit doit être capable de les exposer.

```text
ReferenceNegativeConstraint
|
+-- constraint_id
+-- forbidden_relation_type
+-- subject_ref
+-- target_ref
+-- reason
```

---

# 38. Importance des contraintes négatives

Elles permettent de représenter explicitement :

```text
la relation qui NE doit pas être inférée
```

et évitent qu'un moteur générique reconstruise un héritage invalide.

---

# 39. Règle fail-closed sur l'héritage

Interdit :

```python
if standard.family_id == other.family_id:
    inherit_accounts()
```

Correct :

```text
explicit effective plan
or
explicit inheritance relation
```

---

# 40. Crosswalks

Un crosswalk relie potentiellement deux référentiels.

Il doit avoir un statut explicite.

```text
ReferenceCrosswalk
|
+-- source_standard
+-- target_standard
+-- relation_type
+-- rows
+-- policy
+-- provenance
```

---

# 41. Crosswalk structurel != crosswalk sémantique

Le dataset EBNL vs SYSCOHADA observé indique explicitement :

```text
relation_type = structural_code_delta

automatic_crosswalk_approval = false

human_review_required_for_semantics = true

inheritance_asserted = false

semantic_equivalence_from_code_equality = false
```

PyAccountingKit doit respecter ces contraintes.

---

# 42. `CrosswalkRow`

```text
CrosswalkRow
|
+-- source_ref_code?
+-- target_ref_code?
+-- status
+-- semantic_equivalence_asserted
+-- human_review_required
+-- evidence?
```

---

# 43. Etats de mapping

Le modèle PyAccountingKit doit distinguer au minimum :

```text
STRUCTURAL_ONLY
CANDIDATE
VALIDATED
REJECTED
```

si la source fournit suffisamment d'information pour cette projection.

Sinon le statut brut source est conservé.

---

# 44. Invariant - code equality is not semantics

```text
source.ref_code == target.ref_code
```

ne suffit jamais pour :

```text
semantic_equivalence = true
```

---

# 45. Aucun auto-approval implicite

Si la source indique :

```text
human_review_required = true
```

PyAccountingKit ne peut pas transformer le mapping en mapping exécutable sans une validation métier explicite.

---

# 46. Registry de concepts neutres

Le dataset `accounting_core_concepts_v0` fournit un pivot sémantique neutre.

Exemples :

```text
concept:equity_capital
concept:reserves
concept:retained_earnings
concept:period_result
concept:provisions
concept:fixed_assets
concept:inventory
concept:trade_receivables
concept:trade_payables
concept:cash
concept:operating_expense
concept:operating_revenue
```

---

# 47. `ReferenceConceptRegistry`

```text
ReferenceConceptRegistry
|
+-- registry_id
+-- purpose
+-- concepts
+-- bindings
+-- binding_policy
```

---

# 48. `ReferenceConcept`

```text
ReferenceConcept
|
+-- concept_id
+-- label
+-- definition
+-- concept_type
+-- status
```

---

# 49. Concept neutre != règle comptable

Le dataset source affirme :

```text
neutral_concept_is_not_accounting_rule = true
```

PyAccountingKit doit conserver cette séparation.

---

# 50. Bindings conceptuels

Le dataset actuellement observé contient :

```text
bindings = []
```

avec :

```text
bindings_status = deferred_until_complete_structures

human_review_required = true

auto_approval_allowed = false

code_equality_is_semantic_evidence = false
```

---

# 51. Règle - ne pas inventer les concept bindings

Interdit :

```python
concept_cash = every_account_starting_with("5")
```

si le référentiel ne le déclare pas explicitement.

---

# 52. Candidate generation

Les concepts neutres peuvent être utilisés pour :

```text
candidate generation
search
human assistance
semantic navigation
```

mais pas pour créer une règle réglementaire automatique non validée.

---

# 53. Reporting réglementaire

Les datasets `v3_reporting` exposent :

```text
statement structure
statement lines
sections
account hints
mapping policy
```

---

# 54. `ReferenceReportingModel`

```text
ReferenceReportingModel
|
+-- standard_id
+-- edition
+-- dataset_layer
+-- statements
+-- mapping_policy
+-- provenance
```

---

# 55. `ReferenceStatement`

```text
ReferenceStatement
|
+-- statement_id
+-- code?
+-- label?
+-- lines
+-- metadata
```

---

# 56. `ReferenceStatementLine`

```text
ReferenceStatementLine
|
+-- line_id
+-- line_code
+-- label
+-- section
+-- account_hints
+-- metadata
```

---

# 57. Structure officielle vs hints candidats

Le dataset nonprofit 2026 observé distingue :

```text
statement_structure = official_source

account_hints = derived_candidate

account_hints_executable = false

human_validation_required = true
```

Cette distinction doit être conservée intégralement.

---

# 58. `ReferenceAccountHint`

```text
ReferenceAccountHint
|
+-- account_prefix?
+-- account_id?
+-- mapping_status
+-- human_validation_required
+-- executable
+-- provenance?
```

---

# 59. Invariant reporting

Un `ReferenceAccountHint` avec :

```text
executable = false
```

ne peut pas devenir automatiquement un `StatementAccountMapping` exécutable.

---

# 60. Transformation correcte

```text
ReferenceAccountHint
        |
        v
MappingSuggestion
        |
        v
Human / Rule Validation
        |
        v
StatementAccountMapping
```

---

# 61. Distinction des trois mappings

PyAccountingKit distingue :

```text
1. RegulatoryAccountBinding
   CompanyAccount -> ReferenceAccount

2. StatementAccountMapping
   CompanyAccount -> StatementLine

3. ReferenceCrosswalk
   ReferenceAccount A -> ReferenceAccount B
```

Ces trois relations ne sont pas interchangeables.

---

# 62. `RegulatoryAccountBinding`

```text
RegulatoryAccountBinding
|
+-- company_account_id
+-- reference_account_id
+-- reference_snapshot
+-- binding_type
+-- status
+-- confidence?
+-- validated_by?
+-- validated_at?
+-- provenance
```

---

# 63. Binding type

Proposition :

```text
MANUAL
RULE
IMPORTED
VALIDATED_CANDIDATE
```

Une suggestion non validée n'est pas un binding actif.

---

# 64. Statut d'un binding

```text
CANDIDATE
VALIDATED
REJECTED
SUPERSEDED
```

---

# 65. `ReferenceSnapshotRequest`

```text
ReferenceSnapshotRequest
|
+-- standards
+-- structures
+-- effective_plans
+-- reporting_models
+-- relations
+-- crosswalks
+-- concepts
```

---

# 66. `AccountingReferenceSnapshot`

Objet central :

```text
AccountingReferenceSnapshot
|
+-- snapshot_id
+-- created_at
+-- provider_id
+-- provider_version?
+-- dataset_release
+-- artifacts
+-- checksums
+-- standard_snapshots
+-- metadata
```

---

# 67. `StandardReferenceSnapshot`

```text
StandardReferenceSnapshot
|
+-- standard_id
+-- edition
+-- dataset_version
+-- structure_checksum?
+-- effective_plan_checksum?
+-- reporting_checksum?
+-- relations_checksum?
+-- loaded_at
```

---

# 68. Pourquoi un snapshot

Un plan d'entreprise créé aujourd'hui doit pouvoir répondre plus tard :

```text
Quel référentiel exact a été utilisé ?
Quelle édition ?
Quel dataset ?
Quel checksum ?
Quel reporting model ?
```

---

# 69. Snapshot et reproductibilité

Le snapshot soutient :

```text
company chart generation
policy execution
report generation
audit
migration
golden tests
```

---

# 70. Immutabilité du snapshot

Un `AccountingReferenceSnapshot` finalisé est immutable.

Un nouveau release du dataset crée :

```text
new snapshot
```

et non une mutation silencieuse.

---

# 71. Dimensions de version

PyAccountingKit doit distinguer :

```text
PyAccountingKitVersion

RegulatoryDatasetRelease

StandardEdition

ReferenceSnapshotId

CompanyChartVersion

AccountingPolicySetVersion

StatementMappingVersion

ReportSnapshotVersion
```

---

# 72. Dataset release vs standard edition

Exemple :

```text
standard edition:
    PCG 2026

dataset release:
    une version technique du corpus structuré
```

Ces deux informations ne doivent pas être fusionnées.

---

# 73. Checksum

Chaque artefact chargé peut avoir :

```text
sha256
```

ou un checksum équivalent.

Le provider doit pouvoir produire un checksum lorsqu'il n'est pas fourni par la source externe.

---

# 74. `ReferenceArtifactDescriptor`

```text
ReferenceArtifactDescriptor
|
+-- artifact_type
+-- logical_id
+-- standard_id?
+-- edition?
+-- dataset_layer
+-- version
+-- checksum
+-- source_location?
```

---

# 75. Capabilities

Tous les standards ne possèdent pas nécessairement tous les layers.

```text
ReferenceCapabilities
|
+-- has_structure
+-- has_effective_plan
+-- has_reporting
+-- has_relations
+-- has_crosswalks
+-- has_concepts
```

---

# 76. Résolution d'une structure

Règle cible :

```text
if effective plan exists:
    use effective plan for company chart generation

else:
    use standalone structure
```

---

# 77. Structure vs effective plan

```text
ReferenceStructure
    = hiérarchie réglementaire structurée

EffectiveAccountPlan
    = plan réglementaire résolu et applicable
```

Les deux peuvent coexister.

---

# 78. `ReferenceCatalogService`

```python
class ReferenceCatalogService:

    def resolve_account_plan(
        self,
        standard_id: str,
        edition: str,
    ) -> "ReferenceAccountPlan":
        ...
```

Il choisit le layer approprié sans reconstruire les règles d'extension.

---

# 79. Read model de recherche

Le provider peut proposer des queries :

```text
find account by id
find account by exact code
search accounts by label
list children
list descendants
list ancestors
```

---

# 80. Lookup par code

Signature :

```python
def get_account_by_code(
    *,
    standard_id: str,
    edition: str,
    ref_code: str,
) -> ReferenceAccount | None:
    ...
```

Le code n'est unique qu'à l'intérieur du scope :

```text
standard + edition
```

---

# 81. Lookup par ID

Préféré lorsque possible :

```python
def get_account(
    reference_account_id: ReferenceAccountId,
) -> ReferenceAccount:
    ...
```

---

# 82. Recherche textuelle

Une recherche par libellé :

```text
"Banques"
```

ne produit jamais automatiquement un mapping.

Elle renvoie :

```text
ReferenceSearchResult
```

---

# 83. `ReferenceSearchResult`

```text
ReferenceSearchResult
|
+-- reference_node_id
+-- label
+-- score?
+-- matched_fields
+-- provenance
```

---

# 84. Provider Local Filesystem

Adapter initial recommandé :

```text
LocalFilesystemAccountingReferenceProvider
```

Configuration :

```text
dataset_root
manifest
validation strategy
cache strategy
```

---

# 85. Provider Package

Adapter possible :

```text
PackageAccountingReferenceProvider
```

pour un distribution bundle packagé.

---

# 86. Provider HTTP

Adapter futur :

```text
HttpAccountingReferenceProvider
```

Il doit préserver le même contrat.

---

# 87. Provider Object Storage

Adapter futur :

```text
ObjectStorageAccountingReferenceProvider
```

Exemples d'infrastructure :

```text
S3-compatible
Azure Blob
GCS
```

Le domaine ne dépend pas du fournisseur.

---

# 88. Provider InMemory

```text
InMemoryAccountingReferenceProvider
```

pour :

```text
unit tests
fixtures
golden tests
```

---

# 89. Configuration par injection

Correct :

```python
engine = AccountingEngine(
    reference_provider=provider,
)
```

Incorrect :

```python
Path("../regulatory-accounting-data-framework/datasets")
```

dans le domaine.

---

# 90. Pas de dépendance repository path

PyAccountingKit ne doit jamais supposer :

```text
regulatory-accounting-data-framework
est checkouté à côté du repo
```

Le provider encapsule la localisation.

---

# 91. Cache

Le provider peut cacher :

```text
structures
effective plans
reporting
relations
```

par clé :

```text
standard_id
edition
dataset_version
checksum
```

---

# 92. Cache immutable

Si le checksum change :

```text
cache miss
```

Le cache ne doit pas écraser silencieusement un snapshot déjà utilisé.

---

# 93. Validation du dataset

L'adapter doit distinguer :

```text
schema validity
semantic status
human review status
```

Un JSON syntaxiquement valide n'est pas nécessairement exécutable.

---

# 94. `ReferenceLoadResult`

```text
ReferenceLoadResult
|
+-- artifact
+-- schema_valid
+-- warnings
+-- review_status
+-- executable_capabilities
```

---

# 95. Fail-closed

Cas bloquants :

```text
standard absent
edition absente
checksum invalide
schema non supporté
effective plan requis mais absent
relation ambiguë utilisée comme héritage
mapping non exécutable utilisé comme mapping actif
```

---

# 96. Warnings non bloquants

Exemples :

```text
missing optional provenance field
candidate mapping available but not validated
concept bindings deferred
crosswalk requires review
```

---

# 97. Exceptions

```text
AccountingReferenceError
|
+-- ReferenceStandardNotFoundError
+-- ReferenceEditionNotFoundError
+-- ReferenceArtifactNotFoundError
+-- UnsupportedReferenceSchemaError
+-- InvalidReferenceArtifactError
+-- ReferenceChecksumMismatchError
+-- EffectivePlanResolutionError
+-- ForbiddenReferenceInferenceError
+-- NonExecutableReferenceMappingError
+-- ReferenceHumanReviewRequiredError
```

---

# 98. Relation avec `Accounting Policies & Measurement`

Le bounded context Policies peut demander :

```text
standard
edition
concepts
reference snapshot
```

mais il ne doit pas lire directement les JSON.

```text
Policies
    |
    v
AccountingReferenceProvider
```

---

# 99. `PolicyReferenceContext`

```text
PolicyReferenceContext
|
+-- snapshot_id
+-- standard_id
+-- edition
+-- reference_account_ids
+-- concept_ids
```

---

# 100. Relation avec Company Chart

Pipeline :

```text
ReferenceAccountPlan
    |
    v
CompanyChartGenerationPolicy
    |
    v
CompanyChartOfAccounts
```

---

# 101. Règle - ne pas cloner le référentiel

Le plan d'entreprise ne doit pas être une copie aveugle.

Il doit garder :

```text
company account identity
+
reference binding
```

---

# 102. Exemple

```text
CompanyAccount
    code = "51200101"
    label = "BNP - Compte courant"

RegulatoryAccountBinding
    reference_account_id =
        account:fr-pcg:2026:512
```

---

# 103. Relation avec Reporting

Pipeline :

```text
ReferenceReportingModel
    |
    v
Statement Mapping Configuration
    |
    v
Financial Statement Engine
```

Les `account_hints` candidats ne deviennent pas des mappings actifs sans validation.

---

# 104. Relation avec Crosswalk

Crosswalk peut assister :

```text
migration
group chart mapping
multi-standard reporting
consolidation
```

mais reste soumis à son statut.

---

# 105. Relation avec Concepts

Les concepts neutres peuvent assister :

```text
semantic candidate generation
search
analytics mapping
policy applicability
```

uniquement lorsque leurs bindings sont validés.

---

# 106. Relation avec Consolidation

Le futur bounded context `Consolidation` pourra consommer :

```text
ReferenceCrosswalk
ReferenceConceptRegistry
Group Chart mappings
```

sans transformer un crosswalk structurel en équivalence réglementaire.

---

# 107. Import du corpus

Un adapter LocalFilesystem peut scanner :

```text
manifest
or
known dataset catalog
```

Il ne doit pas inférer les types uniquement depuis le filename si le contenu expose déjà `dataset_layer`.

---

# 108. Registry des loaders

```text
ReferenceArtifactLoaderRegistry
|
+-- v1_structure
+-- v1_effective_plan
+-- v1_overlay
+-- v3_reporting
+-- relations
+-- crosswalk
+-- concepts
```

---

# 109. Support des versions de schema

Chaque loader déclare :

```text
supported_schema_versions
```

et échoue explicitement si le format n'est pas compatible.

---

# 110. DTO externe vs domaine

Exemple :

```text
PcgV1JsonNodeDTO
        |
        v
ReferenceNode
```

Le domaine ne doit pas importer la classe DTO JSON.

---

# 111. Mapper

```python
class ReferenceStructureMapper:

    def map_node(
        self,
        dto: ExternalNodeDTO,
    ) -> ReferenceNode:
        ...
```

---

# 112. Conservation des metadata inconnues

Pour éviter de perdre une information source lors de l'évolution du corpus :

```text
ReferenceNode.metadata
```

peut conserver des attributs non normalisés.

Cela ne doit pas remplacer les champs métier connus.

---

# 113. Immutable collections

Le modèle de référence privilégie :

```text
tuple
frozen dataclass
immutable mapping
```

lorsque pertinent.

---

# 114. Exemple de dataclass

```python
from dataclasses import dataclass
from typing import Mapping

@dataclass(frozen=True)
class ReferenceAccount:
    reference_account_id: str
    standard_id: str
    edition: str
    ref_code: str
    label: str
    parent_id: str | None
    children_ids: tuple[str, ...]
    attributes: Mapping[str, object]
    provenance: "ReferenceProvenance"
```

---

# 115. Manifest de snapshot

Proposition :

```json
{
  "snapshot_id": "ref-snapshot-...",
  "created_at": "...",
  "artifacts": [
    {
      "type": "structure",
      "standard_id": "fr-pcg",
      "edition": "2026",
      "checksum": "..."
    }
  ]
}
```

---

# 116. Serialization

`AccountingReferenceSnapshot` doit pouvoir être sérialisé dans :

```text
JSON
```

pour :

```text
audit
report snapshot
policy trace
migration log
```

---

# 117. Snapshot léger vs complet

Deux modes possibles :

```text
REFERENCE_POINTER_SNAPSHOT
    IDs + versions + checksums

EMBEDDED_REFERENCE_SNAPSHOT
    metadata + selected normalized data
```

Le mode P0 recommandé est :

```text
REFERENCE_POINTER_SNAPSHOT
```

avec possibilité d'archivage externe du corpus.

---

# 118. Disponibilité historique

Un snapshot ne suffit que si l'artefact référencé reste récupérable.

L'exploitation production doit donc garantir :

```text
retention des releases réglementaires utilisées
```

---

# 119. `ReferenceReleaseRepository`

Port optionnel :

```text
ReferenceReleaseRepository
```

capable de récupérer une release historique par checksum/version.

---

# 120. Mise à jour réglementaire

Pipeline :

```text
new regulatory dataset release
        |
        v
load + validate
        |
        v
new ReferenceSnapshot candidate
        |
        v
impact analysis
        |
        +--> charts
        +--> policies
        +--> mappings
        +--> reporting
        |
        v
explicit migration decision
```

---

# 121. Aucune mutation automatique des plans existants

Un nouveau référentiel ne doit pas réécrire automatiquement :

```text
CompanyChartOfAccounts v1
```

Il déclenche :

```text
CompanyChartMigrationPlan
```

---

# 122. Impact analysis

Objet futur :

```text
ReferenceUpgradeImpact
|
+-- accounts_added
+-- accounts_removed
+-- labels_changed
+-- hierarchy_changed
+-- reporting_changed
+-- relations_changed
+-- crosswalk_changed
+-- policy_impacts
```

---

# 123. Structure diff

Les différences doivent comparer :

```text
ReferenceAccountId
ref_code
label
parent
attributes
```

sans supposer que tout changement de label est un changement sémantique.

---

# 124. Migration de standard

Passer :

```text
standard A
->
standard B
```

est distinct de :

```text
edition A1
->
edition A2
```

---

# 125. Cross-standard migration

Elle nécessite potentiellement :

```text
crosswalk
human validation
company account mappings
policy migration
reporting mapping migration
```

---

# 126. Monitoring

Métriques techniques utiles :

```text
reference_load_duration
reference_cache_hit
reference_artifact_count
reference_validation_errors
human_review_candidates
non_executable_mapping_attempts
```

---

# 127. Logging

Les logs doivent exposer :

```text
standard_id
edition
artifact_type
dataset_version
checksum
snapshot_id
```

sans reproduire inutilement tout le corpus.

---

# 128. Sécurité

Les fichiers réglementaires sont normalement read-only.

L'adapter doit empêcher :

```text
write through
silent local patch
runtime modification
```

---

# 129. Integrity

Lors du démarrage ou chargement :

```text
manifest / expected checksum
        vs
actual checksum
```

peut être vérifié.

---

# 130. Tests unitaires du mapper

```text
test_preserves_reference_node_id
test_preserves_parent_child_relationship
test_preserves_ref_code_as_string
test_preserves_provenance
test_preserves_unknown_attributes
test_maps_class_group_account_types
```

---

# 131. Tests Effective Plan

```text
test_effective_plan_preserves_namespace
test_inherited_account_keeps_base_account_id
test_extension_override_keeps_source_ref
test_extension_addition_has_no_base_account
test_company_chart_generator_uses_effective_plan
```

---

# 132. Tests Relations

```text
test_family_membership_does_not_imply_inheritance
test_negative_constraint_blocks_forbidden_inference
test_crosswalk_relation_preserves_human_review_flag
```

---

# 133. Tests Crosswalk

```text
test_equal_code_does_not_imply_semantic_equivalence
test_structural_delta_is_not_executable_mapping
test_human_review_required_is_preserved
```

---

# 134. Tests Concepts

```text
test_concept_registry_is_neutral
test_empty_bindings_are_not_filled_automatically
test_concept_is_not_accounting_rule
```

---

# 135. Tests Reporting

```text
test_official_statement_structure_is_preserved

test_non_executable_account_hint_cannot_become_active_mapping

test_human_validation_required_is_preserved

test_statement_line_id_is_stable
```

---

# 136. Contract tests Provider

Tous les adapters doivent passer la même suite :

```text
AccountingReferenceProviderContractTests
```

---

# 137. Contract test - get standard

```text
given known standard + edition
returns ReferenceStandard
```

---

# 138. Contract test - missing standard

```text
unknown standard
    ->
ReferenceStandardNotFoundError
```

---

# 139. Contract test - immutability

```text
returned reference model
cannot be mutated
```

---

# 140. Contract test - deterministic snapshot

A même ensemble d'artefacts :

```text
same snapshot logical content
same checksums
```

hors champs temporels explicitement exclus du digest.

---

# 141. Golden dataset PCG

Fixtures P0 recommandées :

```text
class:fr-pcg:2026:1

account:fr-pcg:2026:10

account:fr-pcg:2026:2718
```

pour valider :

```text
class
group
account
parent / children
attributes
provenance
```

---

# 142. Golden dataset SYSCOHADA

Fixture recommandée :

```text
account:ohada-syscohada:2017:7721
```

pour vérifier :

```text
edition = 2017
node_type = account
parent = account:ohada-syscohada:2017:772
path hierarchy
provenance
```

---

# 143. Golden dataset Nonprofit Effective Plan

Fixture :

```text
account:fr-nonprofit:2026:512
```

doit conserver :

```text
base_account_id = account:fr-pcg:2026:512

origin = inherited_from_base_standard
```

---

# 144. Golden dataset Nonprofit Override

Fixture :

```text
account:fr-nonprofit:2026:10
```

doit conserver :

```text
base_account_id = account:fr-pcg:2026:10

origin = extension_override

label = Fonds propres et réserves
```

---

# 145. Golden relation OHADA

Le provider doit représenter :

```text
ohada-ebnl:2023
    specialized_standard_within_family
ohada-accounting
```

sans en créer :

```text
ohada-ebnl:2023 inherits ohada-syscohada:2017
```

---

# 146. Golden crosswalk

`ebnl_2023_vs_syscohada_2017_structural_delta` doit conserver :

```text
automatic_crosswalk_approval = false
human_review_required_for_semantics = true
inheritance_asserted = false
semantic_equivalence_from_code_equality = false
```

---

# 147. Golden concept registry

Le provider doit conserver :

```text
bindings = []
```

et la policy :

```text
human_review_required = true
auto_approval_allowed = false
```

sans générer de bindings.

---

# 148. Golden reporting

Pour `fr-nonprofit:2026` :

```text
statement_structure = official_source

account_hints = derived_candidate

account_hints_executable = false

human_validation_required = true
```

doit être préservé.

---

# 149. Package cible

```text
src/pyaccountingkit/
|
+-- domain/
|   +-- references/
|       +-- standard.py
|       +-- structure.py
|       +-- account.py
|       +-- effective_plan.py
|       +-- overlay.py
|       +-- relation.py
|       +-- crosswalk.py
|       +-- concepts.py
|       +-- reporting.py
|       +-- snapshot.py
|       +-- provenance.py
|
+-- ports/
|   +-- references.py
|
+-- application/
|   +-- references/
|       +-- catalog.py
|       +-- snapshot.py
|       +-- search.py
|       +-- impact.py
|
+-- adapters/
    +-- regulatory/
        +-- filesystem/
        +-- package/
        +-- http/
        +-- object_storage/
```

---

# 150. Adapter filesystem

```text
adapters/regulatory/filesystem/
|
+-- provider.py
+-- catalog.py
+-- loaders/
|   +-- structure_v1.py
|   +-- effective_plan_v1.py
|   +-- overlay_v1.py
|   +-- reporting_v3.py
|   +-- relations.py
|   +-- crosswalk.py
|   +-- concepts.py
|
+-- mappers/
|   +-- structure.py
|   +-- reporting.py
|   +-- relations.py
|
+-- validation/
```

---

# 151. Pas de packages par standard

A éviter :

```text
pyaccountingkit-reference-pcg
pyaccountingkit-reference-syscohada
pyaccountingkit-reference-ebnl
```

si ces packages ne font que recopier les datasets.

---

# 152. Adapter optionnel autorisé

Un package technique séparé pourrait exister si nécessaire :

```text
pyaccountingkit-regulatory-adapter
```

mais uniquement s'il existe une raison de cycle de release ou de dépendances.

Dans le premier repo, un module interne est suffisant.

---

# 153. API publique P0

Exemple :

```python
catalog = accounting.references

pcg = catalog.get_standard(
    standard_id="fr-pcg",
    edition="2026",
)

plan = catalog.get_account_plan(
    standard_id="fr-pcg",
    edition="2026",
)

account = catalog.get_account(
    "account:fr-pcg:2026:512"
)
```

---

# 154. API Effective Plan

```python
plan = catalog.get_account_plan(
    standard_id="fr-nonprofit",
    edition="2026",
)
```

doit retourner le plan effectif déjà résolu.

---

# 155. API reporting

```python
reporting = catalog.get_reporting_model(
    standard_id="fr-nonprofit",
    edition="2026",
)
```

---

# 156. API relation

```python
relations = catalog.get_relations(
    standard_id="ohada-ebnl",
    edition="2023",
)
```

---

# 157. API concepts

```python
concepts = catalog.get_concept_registry()
```

L'appel ne doit pas laisser entendre que les bindings sont validés lorsqu'ils sont absents.

---

# 158. API snapshot

```python
snapshot = catalog.create_snapshot(
    ReferenceSnapshotRequest(
        standards=(
            StandardRef("fr-pcg", "2026"),
        ),
        include_structure=True,
        include_reporting=True,
    )
)
```

---

# 159. Domain Events

Le bounded context Reference peut émettre des événements applicatifs :

```text
ReferenceSnapshotCreated
ReferenceReleaseLoaded
ReferenceValidationFailed
ReferenceUpgradeDetected
```

Les objets externes ne deviennent pas des aggregates mutables.

---

# 160. ADRs

| ID | Décision |
|---|---|
| ADR-REF-001 | `regulatory-accounting-data-framework` est la source de vérité réglementaire structurée |
| ADR-REF-002 | PyAccountingKit consomme les données via `AccountingReferenceProvider` |
| ADR-REF-003 | Le domaine ne connaît aucun chemin de repository |
| ADR-REF-004 | Les identifiants réglementaires externes sont préservés |
| ADR-REF-005 | `ReferenceAccount` est immutable |
| ADR-REF-006 | Parent/enfants structurés sont consommés tels quels |
| ADR-REF-007 | Un effective plan fourni par la source est consommé directement |
| ADR-REF-008 | PyAccountingKit ne rejoue pas arbitrairement les overlays si un effective plan existe |
| ADR-REF-009 | Relation de famille et héritage sont distincts |
| ADR-REF-010 | Les negative constraints sont préservées |
| ADR-REF-011 | L'égalité de code ne prouve pas l'équivalence sémantique |
| ADR-REF-012 | Les crosswalks candidats restent non exécutables jusqu'à validation |
| ADR-REF-013 | Les concepts neutres ne sont pas des règles comptables |
| ADR-REF-014 | Les concept bindings absents ne sont jamais inventés |
| ADR-REF-015 | Structure de reporting officielle et account hints candidats sont séparés |
| ADR-REF-016 | `account_hints_executable=false` est fail-closed |
| ADR-REF-017 | Les versions de dataset et éditions de standard sont distinctes |
| ADR-REF-018 | Les références utilisées en production sont figées dans `AccountingReferenceSnapshot` |
| ADR-REF-019 | Une mise à jour réglementaire ne mute pas automatiquement les charts existants |
| ADR-REF-020 | Tous les adapters passent une contract suite commune |

---

# 161. Critères d'acceptation P0.6

```text
[ ] AccountingReferenceProvider est spécifié

[ ] ReferenceCatalog est spécifié

[ ] ReferenceStandard est spécifié

[ ] ReferenceStructure est spécifié

[ ] ReferenceNode est spécifié

[ ] ReferenceAccount est spécifié

[ ] les IDs réglementaires sont préservés

[ ] parent / children / path sont préservés

[ ] provenance est préservée

[ ] EffectiveAccountPlan est spécifié

[ ] fr-nonprofit peut consommer un effective plan déjà résolu

[ ] overlays sont auditables

[ ] ReferenceRelation est spécifié

[ ] negative constraints sont préservées

[ ] family membership n'implique pas inheritance

[ ] ReferenceCrosswalk est spécifié

[ ] code equality n'implique pas semantic equivalence

[ ] human-review flags sont préservés

[ ] ReferenceConceptRegistry est spécifié

[ ] bindings absents ne sont pas inventés

[ ] ReferenceReportingModel est spécifié

[ ] account_hints_executable=false est respecté

[ ] AccountingReferenceSnapshot est spécifié

[ ] standard edition != dataset release

[ ] filesystem paths sont confinés à l'adapter

[ ] InMemory provider peut servir aux tests

[ ] contract test suite est définie
```

---

# 162. Ordre d'implémentation recommandé

## REF-00 - Primitives

```text
ReferenceStandardId
ReferenceEdition
ReferenceNodeId
ReferenceAccountId
ReferenceProvenance
SourceRef
```

---

## REF-01 - Modèle structurel

```text
ReferenceStandard
ReferenceStructure
ReferenceNode
ReferenceAccount
```

---

## REF-02 - Provider Port

```text
AccountingReferenceProvider
ReferenceCatalogService
```

---

## REF-03 - Filesystem Adapter

```text
v1 structure loader
mapper
validation
```

---

## REF-04 - Effective Plans

```text
EffectiveAccountPlan
EffectiveReferenceAccount
overlay metadata
```

---

## REF-05 - Snapshot

```text
AccountingReferenceSnapshot
checksums
serialization
```

---

## REF-06 - Relations / Crosswalk

```text
ReferenceRelation
NegativeConstraint
ReferenceCrosswalk
human-review status
```

---

## REF-07 - Concepts

```text
ReferenceConceptRegistry
no automatic bindings
```

---

## REF-08 - Reporting

```text
ReferenceReportingModel
ReferenceStatement
ReferenceStatementLine
ReferenceAccountHint
```

---

# 163. Démonstrateur P0.6

Scénario recommandé :

```text
1. Instantiate LocalFilesystemAccountingReferenceProvider

2. Load:
      fr-pcg / 2026

3. Read:
      class:fr-pcg:2026:1

4. Read:
      account:fr-pcg:2026:2718

5. Verify:
      hierarchy
      provenance
      attributes

6. Load:
      fr-nonprofit / 2026 effective plan

7. Verify:
      account:fr-nonprofit:2026:512
      base_account_id = account:fr-pcg:2026:512

8. Verify extension override:
      account:fr-nonprofit:2026:10

9. Load OHADA relations

10. Assert:
      EBNL membership != SYSCOHADA inheritance

11. Load EBNL/SYSCOHADA structural delta

12. Assert:
      semantic equivalence is not inferred

13. Load concept registry

14. Assert:
      no bindings are generated

15. Load nonprofit reporting

16. Assert:
      account hints are not executable

17. Create AccountingReferenceSnapshot

18. Serialize snapshot
```

---

# 164. Impact sur le prochain document

Le prochain document est :

```text
06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md
```

Il utilisera les contrats de ce document pour transformer :

```text
ReferenceAccountPlan
        |
        v
CompanyChartGenerationPolicy
        |
        v
CompanyChartOfAccounts
        |
        v
CompanyAccount
        |
        v
RegulatoryAccountBinding
```

sans supposer :

```text
une longueur fixe de code
un référentiel unique
une relation 1:1 obligatoire
un clonage intégral du plan réglementaire
```

---

# 165. Conclusion

Le bounded context `Accounting Reference Data` constitue la frontière qui protège PyAccountingKit d'un couplage réglementaire direct.

L'architecture cible est :

```text
regulatory-accounting-data-framework
        |
        v
AccountingReferenceProvider
        |
        v
Reference Catalog / Models
        |
        v
AccountingReferenceSnapshot
        |
        +------------------+
        |                  |
        v                  v
Accounting Policies   Company Chart
        |                  |
        +---------+--------+
                  |
                  v
            Accounting Core
```

Les règles fondamentales sont :

```text
External reference IDs are preserved

Reference data is read-only

Effective plans are consumed as effective plans

Family relation != inheritance

Structural crosswalk != semantic equivalence

Code equality != semantic evidence

Neutral concept != accounting rule

Candidate mapping != executable mapping

Official statement structure != candidate account hints

Dataset release != standard edition

Every production use is reproducible through a snapshot
```

Cette architecture permet d'ajouter de nouveaux référentiels sans modifier le coeur comptable et sans recopier leurs données dans PyAccountingKit.

---

**Prochain document recommandé :**

```text
06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md
```


---

## Sources et références documentaires du projet

- 📕 [Comptabilité Générale — Système français et normes IFRS](../../books/Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md)
- 📂 [Référentiels réglementaires — Datasets](../../referentiels/datasets/)
- 📐 [Référentiels réglementaires — Schémas](../../referentiels/schemas/)
- 📦 [regulatory-accounting-data-framework](../../../resources/regulatory-accounting-data-framework/)

---

## Plans d'implémentation principaux

Ce document est couvert par les plans suivants :

- [PLAN-02 — References, Charts & Policies (0.2.0)](../../plans/PLAN-02_REFERENCES_CHARTS_POLICIES_0.2.0.md)
