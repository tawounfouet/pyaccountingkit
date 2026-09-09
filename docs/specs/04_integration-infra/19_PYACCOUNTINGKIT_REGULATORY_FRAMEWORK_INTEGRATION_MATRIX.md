# 19 - PyAccountingKit - Matrice d'intégration des référentiels comptables et réglementaires

> **Projet** : PyAccountingKit  
> **Document** : `19_PYACCOUNTINGKIT_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX.md`  
> **Statut** : P1.8 - Matrice d'intégration réglementaire  
> **Langue** : Français  
> **Documents parents** :
> - `00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`
> - `01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`
> - `02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`
> - `03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md`
> - `04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md`
> - `05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md`
> - `06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md`
> - `13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md`
> - `17_PYACCOUNTINGKIT_RELEASE_AND_VERSIONING_STRATEGY.md`
> - `18_PYACCOUNTINGKIT_CFA_FRA_EXTRACTION_AND_MIGRATION_MAP.md`
> **Objet** : Définir, par standard et par capacité, ce que PyAccountingKit peut consommer depuis `regulatory-accounting-data-framework`, ce qui est seulement structurel, ce qui nécessite validation humaine, ce qui peut devenir exécutable et ce qui doit explicitement rester interdit à l'inférence automatique.

---

# 1. Résumé exécutif

PyAccountingKit ne doit jamais considérer qu'un référentiel est simplement :

```text
SUPPORTED = true
```

L'intégration réglementaire est multidimensionnelle.

Un standard peut disposer :

```text
d'une structure de comptes complète

mais pas de mapping de reporting exécutable

ou

d'un reporting officiel

mais seulement de suggestions de comptes à validation humaine

ou

d'une relation de famille

sans héritage comptable

ou

d'un crosswalk structurel

sans équivalence sémantique
```

La matrice d'intégration doit donc raisonner en **capacités indépendantes** :

```text
STANDARD IDENTITY

STRUCTURE

EFFECTIVE PLAN

OVERLAYS

RELATIONS

CROSSWALKS

NEUTRAL CONCEPTS

CONCEPT BINDINGS

REPORTING STRUCTURE

REPORTING ACCOUNT MAPPINGS

ACCOUNTING POLICIES

IMPORT CLASSIFICATION

EXPORT / REGULATORY RENDERING

REFERENCE SNAPSHOTS

PRODUCTION QUALIFICATION
```

Principe central :

```text
Dataset present
    !=
Semantics validated
    !=
Executable mapping
    !=
Production-qualified integration
```

---

# 2. Source réglementaire de vérité

Pour PyAccountingKit :

```text
regulatory-accounting-data-framework
    =
versioned regulatory source of truth
```

PyAccountingKit ne duplique pas le corpus réglementaire dans son domaine.

Architecture :

```text
regulatory-accounting-data-framework
               |
               v
       Reference Adapter
               |
               v
AccountingReferenceProvider
               |
               v
       PyAccountingKit
```

---

# 3. Standards couverts par la présente matrice

La matrice formalise explicitement les standards actuellement représentés dans le corpus de travail :

```text
fr-pcg:2026

fr-nonprofit:2026

ohada-syscohada:2017

ohada-ebnl:2023

cemac-pcemf:2010
```

---

# 4. IFRS et autres référentiels

CFA FRA possédait une représentation locale d'un référentiel IFRS.

Cette représentation historique ne constitue pas une source réglementaire de vérité pour PyAccountingKit.

Dans le périmètre de preuves actuellement étudié :

```text
IFRS integration status
    =
NOT_ASSERTED
```

jusqu'à ce qu'un corpus réglementaire versionné, sourcé et qualifié soit disponible dans `regulatory-accounting-data-framework`.

---

# 5. Taxonomie des statuts d'intégration

La matrice utilise les statuts suivants.

| Statut | Signification |
|---|---|
| `ABSENT` | Aucune capacité correspondante dans le corpus étudié |
| `DISCOVERED` | Artefact identifié, sans qualification suffisante |
| `INGESTIBLE` | Format suffisamment structuré pour être chargé |
| `VALIDATED` | Structure / relation validée selon les règles du corpus |
| `CANDIDATE` | Donnée utile comme suggestion, pas comme instruction exécutable |
| `REVIEW_REQUIRED` | Validation humaine obligatoire |
| `EXECUTABLE` | Peut être consommé automatiquement dans le scope explicitement qualifié |
| `PRODUCTION_QUALIFIED` | Exécution + contrats + golden/replay tests qualifiés |
| `NOT_ASSERTED` | Le corpus ne permet pas d'affirmer la capacité |
| `FORBIDDEN_INFERENCE` | Une inférence automatique est explicitement interdite |

---

# 6. Règle de progression

La progression normale est :

```text
DISCOVERED
    ↓
INGESTIBLE
    ↓
VALIDATED
    ↓
EXECUTABLE
    ↓
PRODUCTION_QUALIFIED
```

Mais une donnée peut rester volontairement :

```text
CANDIDATE
    ↓
REVIEW_REQUIRED
```

sans jamais devenir automatiquement exécutable.

---

# 7. Couches de données du regulatory framework

Le repository réglementaire distingue plusieurs familles de datasets :

```text
raw
structured
reporting
relations
crosswalk
concepts
prudential
business
```

Les principaux artefacts étudiés comprennent notamment :

```text
structured/
    syscohada_2017_v1_structure.json
    pcg_2026_v1_structure.json
    nonprofit_2026_v1_effective_plan.json
    nonprofit_2026_v1_account_overlay.json
    ebnl_2023_v1_structure.json

reporting/
    syscohada_2017_v3_reporting.json
    pcg_2026_v3_reporting.json
    nonprofit_2026_v3_reporting.json
    ebnl_2023_v3_reporting.json

relations/
    ohada_accounting_standard_relations.json

crosswalk/
    ebnl_2023_vs_syscohada_2017_structural_delta.json

concepts/
    accounting_core_concepts_v0.json
```

---

# 8. Matrice globale des standards

| Standard | Structure | Effective Plan | Relations | Crosswalk | Reporting structure | Mapping comptes reporting | Concepts/bindings | Snapshot |
|---|---|---|---|---|---|---|---|---|
| `fr-pcg:2026` | `VALIDATED/INGESTIBLE` | N/A | `NOT_ASSERTED` | `NOT_ASSERTED` | artefact inventorié | qualification exécutable à établir | concepts neutres seulement | `SUPPORTED` |
| `fr-nonprofit:2026` | via effective plan | `VALIDATED/INGESTIBLE` | base PCG explicitée | via base/overlay, pas crosswalk générique | `VALIDATED` | `REVIEW_REQUIRED` | concepts neutres, bindings différés | `SUPPORTED` |
| `ohada-syscohada:2017` | `VALIDATED/INGESTIBLE` | N/A | `member_of_family` | scopes structurels possibles | artefact inventorié | qualification exécutable à établir | concepts neutres seulement | `SUPPORTED` |
| `ohada-ebnl:2023` | artefact structuré inventorié | N/A | `specialized_standard_within_family` | structural delta vs SYSCOHADA | artefact inventorié | `NOT_ASSERTED` | concepts neutres seulement | `SUPPORTED` |
| `cemac-pcemf:2010` | `NOT_ASSERTED` dans les preuves actuelles | N/A | `sector_specialization_within_family` | candidate crosswalk vs SYSCOHADA | `NOT_ASSERTED` | `REVIEW_REQUIRED/NOT_ASSERTED` | `NOT_ASSERTED` | possible si provider source disponible |

---

# 9. Règle d'interprétation de la matrice

Une cellule :

```text
artefact inventorié
```

signifie uniquement :

```text
le repository fourni indique l'existence du dataset
```

Elle ne signifie pas :

```text
mapping réglementaire executable
```

La qualification exécutable nécessite ses propres preuves et tests.

---

# 10. PCG 2026 - identité

```text
standard_id:
    fr-pcg

edition:
    2026

canonical ref:
    fr-pcg:2026
```

---

# 11. PCG 2026 - structure

Le dataset `v1_structure` est hiérarchique.

Exemple de noeud :

```text
account:fr-pcg:2026:512
    label = Banques
    parent = account:fr-pcg:2026:51
    path = 5 / 51 / 512
```

Il expose explicitement :

```text
node_id

node_type

parent_node_id

children_node_ids

path_codes

path_node_ids

depth

is_leaf

attributes

provenance

ref_code

standard_id

edition
```

---

# 12. Décision PCG structure

```text
PyAccountingKit:
    CONSUME

PyAccountingKit:
    DOES NOT REBUILD HIERARCHY FROM PREFIX ALONE
```

---

# 13. Identité réglementaire PCG

Exemple :

```text
account:fr-pcg:2026:512
```

Cette identité est préservée telle quelle comme :

```text
ReferenceAccount.external_id
```

ou équivalent.

Elle n'est jamais remplacée par un UUID PyAccountingKit.

---

# 14. PCG optional/minimum metadata

La structure PCG peut contenir des attributs comme :

```text
is_minimum_plan_account

optional
```

PyAccountingKit peut les exposer comme metadata de référence.

Il ne doit pas transformer automatiquement :

```text
optional=false
```

en :

```text
CompanyAccount must exist
```

sans `CompanyChartGenerationPolicy`.

---

# 15. PCG -> Company Chart

Exemple :

```text
ReferenceAccount
    account:fr-pcg:2026:512
        |
        +--> CompanyAccount 512001
        +--> CompanyAccount 51200001
        +--> CompanyAccount 512-BANK-EUR
```

Le lien sémantique est :

```text
RegulatoryAccountBinding
```

et non l'égalité des codes.

---

# 16. PCG 2026 - reporting

L'inventaire réglementaire fourni contient :

```text
pcg_2026_v3_reporting.json
```

La présence du dataset suffit pour déclarer :

```text
REPORTING DATASET DISCOVERED
```

mais la présente matrice ne transforme pas cette présence seule en :

```text
EXECUTABLE ACCOUNT MAPPING
```

---

# 17. France Non-Profit 2026 - identité

```text
standard_id:
    fr-nonprofit

edition:
    2026

canonical ref:
    fr-nonprofit:2026
```

---

# 18. Nature du référentiel Non-Profit

Le corpus fournit un :

```text
effective plan
```

déjà résolu à partir de :

```text
fr-pcg:2026
+
specific nonprofit extensions
```

---

# 19. Règle de consommation Non-Profit

PyAccountingKit consomme :

```text
nonprofit_2026_v1_effective_plan.json
```

comme plan effectif.

Il ne reconstitue pas arbitrairement le plan à chaque exécution depuis l'overlay.

---

# 20. Effective plan statistics

Le plan effectif fournit :

```text
base_standard:
    fr-pcg:2026

effective_accounts_or_groups:
    901

extension_additions:
    73

extension_overrides:
    43

inherited:
    785
```

---

# 21. Exemple d'override Non-Profit

```text
account:fr-nonprofit:2026:10
    base:
        account:fr-pcg:2026:10

    base label:
        Capital et réserves

    effective label:
        Fonds propres et réserves

    origin:
        extension_override
```

---

# 22. Exemple d'héritage Non-Profit

```text
account:fr-nonprofit:2026:512
    base:
        account:fr-pcg:2026:512

    label:
        Banques

    origin:
        inherited_from_base_standard
```

---

# 23. Décision effective plan

L'objet cible :

```text
EffectiveAccountPlan
```

préserve :

```text
account_id

base_account_id

origin

provenance

extension source reference
```

---

# 24. Overlay Non-Profit

Le corpus fournit aussi :

```text
nonprofit_2026_v1_account_overlay.json
```

avec notamment :

```text
base_standard = fr-pcg:2026

canonical_effect = replace_or_add

overlay_type

regulatory_status = official_extension
```

---

# 25. Règle overlay

L'overlay est utile pour :

```text
provenance

impact analysis

upgrade comparison

explainability
```

Il n'est pas nécessairement le runtime input principal lorsque l'effective plan est déjà fourni.

---

# 26. Non-Profit reporting

Le dataset reporting déclare explicitement :

```text
dataset_layer:
    v3_reporting

mapping_policy:
    account_hints:
        derived_candidate

    account_hints_executable:
        false

    human_validation_required:
        true

    statement_structure:
        official_source
```

---

# 27. Conséquence majeure

Pour `fr-nonprofit:2026` :

```text
Statement structure:
    VALIDATED / usable

Account hints:
    CANDIDATE

Automatic account mapping:
    FORBIDDEN
```

---

# 28. Exemple de hint

Une ligne peut proposer :

```text
account_prefix = 466

mapping_status =
    derived_candidate_from_specific_nomenclature

human_validation_required = true
```

Cette suggestion ne doit jamais devenir silencieusement :

```text
StatementAccountMapping ACTIVE
```

---

# 29. Activation d'un mapping de reporting

Flux correct :

```text
Reference candidate hint
        |
        v
Mapping Candidate
        |
        v
Human / explicit validation
        |
        v
StatementAccountMapping
        |
        v
MappingSet version
```

---

# 30. SYSCOHADA 2017 - identité

```text
standard_id:
    ohada-syscohada

edition:
    2017

canonical ref:
    ohada-syscohada:2017
```

---

# 31. SYSCOHADA - relation de famille

La relation réglementaire indique :

```text
relation_type:
    member_of_family

subject:
    ohada-syscohada:2017

target:
    ohada-accounting
```

---

# 32. Conséquence

```text
SYSCOHADA 2017
    is member of
OHADA accounting family
```

Mais cette relation ne permet aucune inférence vers :

```text
EBNL

PCEMF
```

---

# 33. SYSCOHADA structure

Exemple :

```text
account:ohada-syscohada:2017:7721
    label:
        Revenus des titres de participation

    parent:
        account:ohada-syscohada:2017:772

    path:
        7 / 77 / 772 / 7721
```

---

# 34. Règle hiérarchique SYSCOHADA

Même lorsqu'un loader réglementaire a dérivé la hiérarchie avec une méthode de type :

```text
source group
+
strict prefix
```

PyAccountingKit doit consommer :

```text
parent_node_id

path_node_ids
```

fournis par le dataset.

Il ne recalcule pas ces relations comme vérité métier.

---

# 35. SYSCOHADA reporting

Le repository inventorié contient :

```text
syscohada_2017_v3_reporting.json
```

La qualification des mappings compte -> ligne doit rester distincte de l'existence de la structure officielle.

---

# 36. OHADA EBNL 2023 - identité

```text
canonical ref:
    ohada-ebnl:2023
```

---

# 37. EBNL - relation de famille

Le corpus définit :

```text
relation_type:
    specialized_standard_within_family

subject:
    ohada-ebnl:2023

target:
    ohada-accounting
```

---

# 38. Interdiction d'héritage implicite EBNL

Le corpus déclare explicitement :

```text
no inheritance from SYSCOHADA is asserted
```

et contient une contrainte négative :

```text
forbidden:
    ohada-ebnl:2023
        inherits
    ohada-syscohada:2017
```

dans l'état courant du corpus.

---

# 39. Conséquence EBNL

Interdit :

```python
if standard.family == "OHADA":
    inherit_all_syscohada_accounts()
```

---

# 40. EBNL / SYSCOHADA structural delta

Le crosswalk structurel déclare :

```text
automatic_crosswalk_approval:
    false

human_review_required_for_semantics:
    true

inheritance_asserted:
    false

relation_type:
    structural_code_delta

semantic_equivalence_from_code_equality:
    false
```

---

# 41. Règle critique de crosswalk

Même si :

```text
EBNL code == SYSCOHADA code
```

PyAccountingKit ne peut pas conclure automatiquement :

```text
same accounting meaning
```

---

# 42. `same_code_same_normalized_label`

Même un statut structurel :

```text
same_code_same_normalized_label
```

ne constitue pas dans le dataset :

```text
semantic_equivalence_asserted = true
```

---

# 43. Crosswalk executable ?

Par défaut :

```text
NO
```

Le crosswalk est :

```text
comparison evidence
candidate generation
migration assistance
```

pas une règle de conversion comptable automatique.

---

# 44. PCEMF 2010 - identité

```text
canonical ref:
    cemac-pcemf:2010
```

---

# 45. PCEMF - relation OHADA

Le corpus définit :

```text
relation_type:
    sector_specialization_within_family

subject:
    cemac-pcemf:2010

target:
    ohada-accounting
```

---

# 46. PCEMF / SYSCOHADA crosswalk

Une relation existe avec :

```text
relation_type:
    crosswalk

subject:
    cemac-pcemf:2010

target:
    ohada-syscohada:2017

human_review_required:
    true

auto_inference_allowed:
    false
```

---

# 47. Interdiction d'héritage PCEMF

Le corpus contient :

```text
no-pcemf2010-inherits-syscohada2017
```

avec comme justification que PCEMF 2010 précède SYSCOHADA 2017 et que les sources ne supportent qu'un cadrage de famille / sectoriel.

---

# 48. Conséquence PCEMF

Interdit :

```text
PCEMF 2010
    automatically inherits
SYSCOHADA 2017
```

---

# 49. Concepts comptables neutres

Le corpus fournit un registre :

```text
accounting-core-concepts-v0
```

Objectif déclaré :

```text
neutral semantic pivot
for candidate generation

not a regulatory standard
```

---

# 50. Concepts présents

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

# 51. Neutral concepts != accounting rules

Le corpus déclare :

```text
neutral_concept_is_not_accounting_rule:
    true
```

---

# 52. Bindings de concepts

Etat actuel :

```text
bindings:
    []

bindings_status:
    deferred_until_complete_structures

human_review_required:
    true

auto_approval_allowed:
    false

code_equality_is_semantic_evidence:
    false
```

---

# 53. Conséquence

Interdit :

```python
concept_cash = all_accounts_starting_with("5")
```

---

# 54. Usage autorisé des concepts

Les concepts neutres peuvent servir à :

```text
candidate generation

search

human-assisted mapping

analytics concept registry

cross-standard navigation
```

---

# 55. Usage interdit

Ils ne peuvent pas directement :

```text
post an entry

select a recognition rule

activate a measurement policy

map an account to a regulatory statement line
```

sans binding validé.

---

# 56. Matrice des relations OHADA

| Subject | Relation | Target | Auto inference | Inheritance |
|---|---|---|---:|---:|
| `ohada-syscohada:2017` | `member_of_family` | `ohada-accounting` | non | N/A |
| `ohada-ebnl:2023` | `specialized_standard_within_family` | `ohada-accounting` | non | non asserté |
| `cemac-pcemf:2010` | `sector_specialization_within_family` | `ohada-accounting` | non | non |
| `cemac-pcemf:2010` | `crosswalk` | `ohada-syscohada:2017` | non | non |

---

# 57. Matrice des contraintes négatives

| Constraint | Subject | Relation interdite | Target |
|---|---|---|---|
| `no-pcemf2010-inherits-syscohada2017` | `cemac-pcemf:2010` | `inherits` | `ohada-syscohada:2017` |
| `no-ebnl-inherits-syscohada-with-current-corpus` | `ohada-ebnl:2023` | `inherits` | `ohada-syscohada:2017` |

---

# 58. Negative constraints as first-class objects

PyAccountingKit doit charger les contraintes négatives.

Objet :

```text
ReferenceNegativeConstraint
```

et non uniquement ignorer les relations absentes.

---

# 59. Pourquoi les contraintes négatives sont importantes

Différence entre :

```text
relation not known
```

et :

```text
relation explicitly forbidden
```

---

# 60. API Provider

Contrat recommandé :

```python
class AccountingReferenceProvider(Protocol):
    def get_standard(...): ...
    def list_standards(...): ...
    def get_structure(...): ...
    def get_effective_plan(...): ...
    def get_reporting_model(...): ...
    def get_relations(...): ...
    def get_crosswalk(...): ...
    def get_concepts(...): ...
    def create_snapshot(...): ...
```

---

# 61. Capabilities provider

Extension recommandée :

```python
class AccountingReferenceProvider(Protocol):
    def get_capabilities(
        self,
        standard_ref: StandardRef,
    ) -> "ReferenceCapabilitySet":
        ...
```

---

# 62. `ReferenceCapabilitySet`

```text
ReferenceCapabilitySet
|
+-- standard_ref
+-- structure
+-- effective_plan
+-- overlays
+-- relations
+-- crosswalks
+-- concepts
+-- concept_bindings
+-- reporting_structure
+-- reporting_account_mappings
+-- policies
+-- exports
+-- snapshots
```

---

# 63. Capability status object

```text
ReferenceCapability
|
+-- code
+-- status
+-- evidence_refs
+-- executable
+-- human_review_required
+-- auto_inference_allowed
+-- notes
```

---

# 64. Integration Profile

```text
RegulatoryFrameworkIntegrationProfile
|
+-- id
+-- standard_ref
+-- provider_id
+-- dataset_release
+-- capabilities
+-- tested_framework_version
+-- qualification_status
+-- evidence
+-- created_at
```

---

# 65. Runtime support must be explicit

Ne pas faire :

```python
if provider.get_standard(...) is not None:
    supports_everything = True
```

---

# 66. `RegulatorySupportLevel`

```text
DISCOVERED

STRUCTURE_SUPPORTED

REFERENCE_VALIDATED

REPORTING_CANDIDATE

EXECUTABLE

PRODUCTION_QUALIFIED
```

---

# 67. Support level is derived

Il est calculé à partir de capacités.

Par exemple :

```text
structure supported
+
reporting structure supported
+
mapping review required

=>
not EXECUTABLE regulatory reporting
```

---

# 68. Regulatory account binding

Mapping :

```text
CompanyAccount
    ->
ReferenceAccount
```

Objet :

```text
RegulatoryAccountBinding
```

---

# 69. Multiplicité

Valide :

```text
many CompanyAccounts
    ->
one ReferenceAccount
```

Exemple :

```text
512001
512002
512003
    ->
account:fr-pcg:2026:512
```

---

# 70. Same company code across entities

Possible :

```text
Entity A / 512001

Entity B / 512001
```

Le binding reste entity/chart-scoped.

---

# 71. Regulatory binding != reporting mapping

Toujours distinguer :

```text
CompanyAccount
    -> ReferenceAccount
```

de :

```text
CompanyAccount
    -> StatementLine
```

---

# 72. Regulatory binding != crosswalk

Toujours distinguer :

```text
CompanyAccount -> ReferenceAccount
```

de :

```text
ReferenceAccount A -> ReferenceAccount B
```

---

# 73. Trois graphes distincts

```text
COMPANY GRAPH

    CompanyAccount
        ->
    ReferenceAccount


PRESENTATION GRAPH

    CompanyAccount
        ->
    StatementLine


CROSS-STANDARD GRAPH

    ReferenceAccount A
        ->
    ReferenceAccount B
```

---

# 74. Never merge those graphs

Sinon le framework risque de transformer :

```text
structural correspondence
```

en :

```text
posting or presentation rule
```

---

# 75. Reference snapshots

Un plan entreprise actif doit pinner :

```text
AccountingReferenceSnapshot
```

---

# 76. Snapshot dimensions

Minimum :

```text
standard_id

edition

dataset_version

checksum
```

---

# 77. Multiple snapshot standards

Une entité peut éventuellement avoir :

```text
primary statutory snapshot

group/reporting snapshot

management reference snapshot
```

si explicitement configuré.

---

# 78. `BindingPurpose`

```text
STATUTORY

REPORTING

GROUP

TAX

MANAGEMENT

OTHER
```

---

# 79. Pas de multi-standard implicite

Une entité ne devient pas automatiquement :

```text
PCG + IFRS + SYSCOHADA
```

parce que plusieurs standards existent dans le provider.

---

# 80. Reference upgrade

Flux :

```text
ReferenceSnapshot R1
        |
        v
New Dataset R2
        |
        v
Impact Analysis
        |
        v
Migration Plan
        |
        v
Review
        |
        v
New Company Chart / Binding Set
        |
        v
Activation
```

---

# 81. No live regulatory lookup in historical replay

Un replay historique utilise :

```text
pinned snapshot
```

pas :

```text
provider latest
```

---

# 82. Reference Upgrade Impact

```text
ReferenceUpgradeImpact
|
+-- added_nodes
+-- removed_nodes
+-- changed_labels
+-- changed_hierarchy
+-- changed_relations
+-- changed_reporting_lines
+-- changed_hints
+-- affected_company_bindings
+-- affected_statement_mappings
+-- human_review_requirements
```

---

# 83. Non-Profit upgrade

Un changement d'overlay doit être analysé contre :

```text
effective plan vN
```

et non appliquer des mutations directes aux CompanyAccounts historiques.

---

# 84. Reporting qualification

Une structure de reporting peut être :

```text
official
```

sans mapping automatique.

---

# 85. `ReportingIntegrationStatus`

```text
STRUCTURE_ONLY

CANDIDATE_MAPPING

VALIDATED_MAPPING

EXECUTABLE_MAPPING

PRODUCTION_QUALIFIED
```

---

# 86. Non-Profit status initial

D'après la policy explicite du dataset :

```text
STRUCTURE_ONLY
+
CANDIDATE_MAPPING
+
HUMAN_REVIEW_REQUIRED
```

---

# 87. Mapping validation object

```text
ReferenceReportingMappingValidation
|
+-- candidate_ref
+-- statement_line_id
+-- company_account_id?
+-- reference_account_id?
+-- decision
+-- reviewer
+-- reviewed_at
+-- evidence
```

---

# 88. Mapping decision

```text
ACCEPT

REJECT

REPLACE

DEFER
```

---

# 89. Candidate hints and prefix

Un `account_prefix` de reporting est :

```text
search/mapping candidate hint
```

et non :

```text
semantic classifier
```

---

# 90. Company Chart Generation

Les datasets réglementaires peuvent alimenter :

```text
CompanyChartGenerationPolicy
```

mais la policy doit déterminer :

```text
which nodes are materialized

which nodes are postable

how company codes are generated

which labels are overridden
```

---

# 91. Structure type `group`

Un noeud réglementaire :

```text
node_type = group
```

ne signifie pas nécessairement :

```text
non-postable CompanyAccount
```

sans policy de génération.

---

# 92. Structure leaf

Même règle pour :

```text
is_leaf
```

Le leaf réglementaire aide la génération mais ne remplace pas la politique entreprise.

---

# 93. Accounting policies integration

Les policies de reconnaissance / mesure doivent pouvoir être liées à :

```text
standard

reference snapshot

concept binding

entity context
```

---

# 94. No policy from code

Interdit :

```python
if reference_code.startswith("2"):
    measurement = HISTORICAL_COST
```

dans le core.

---

# 95. Policy Binding

```text
AccountingPolicy
    |
    v
PolicyBinding
    |
    +--> standard_ref
    +--> reference_account_ref?
    +--> concept_ref?
    +--> applicability
```

---

# 96. Concept binding requirement

Si `concept_ref` est utilisé :

```text
binding must be validated
```

Le registre actuel, avec `bindings=[]`, ne permet pas d'auto-résoudre ces policies.

---

# 97. FEC / Import integration

Un import peut identifier :

```text
source account code
```

puis mapper vers :

```text
CompanyAccount
```

et seulement ensuite vers :

```text
ReferenceAccount
```

---

# 98. Import must not post against ReferenceAccount

Interdit :

```text
FEC line
    ->
ReferenceAccount
    ->
Posting
```

Le posting s'effectue sur :

```text
CompanyAccount
```

---

# 99. Reporting integration flow

```text
Reference Reporting Model
        |
        v
Statement Definition
        |
        +
Validated Company Mapping
        |
        v
Financial Statement Engine
        |
        v
ReportSnapshot
```

---

# 100. Financial Analysis integration

Les neutral concepts peuvent aider l'analyse seulement si :

```text
validated binding exists
```

Sinon l'analyse utilise :

```text
explicit statement lines

explicit analytical mappings
```

---

# 101. Cross-standard reporting

Un reporting dans un second standard exige :

```text
explicit mapping/profile
```

et non :

```text
family relation
```

---

# 102. PCEMF to SYSCOHADA

La relation crosswalk peut être utilisée pour :

```text
candidate generation

gap analysis

migration review
```

Pas pour :

```text
automatic statutory conversion
```

---

# 103. EBNL to SYSCOHADA

Même règle.

Le structural delta est utile pour :

```text
difference inventory
```

mais n'est pas :

```text
semantic mapping
```

---

# 104. Crosswalk model

```text
ReferenceCrosswalk
|
+-- source_standard
+-- target_standard
+-- relation_type
+-- rows
+-- semantic_status
+-- auto_approval_allowed
+-- human_review_required
+-- provenance
```

---

# 105. Crosswalk row

```text
ReferenceCrosswalkRow
|
+-- source_ref?
+-- target_ref?
+-- source_code?
+-- target_code?
+-- structural_status
+-- semantic_equivalence_asserted
+-- human_review_required
+-- evidence
```

---

# 106. No semantic equivalence from code equality

Global invariant :

```text
same code
    !=
same meaning
```

---

# 107. No inheritance from family membership

Global invariant :

```text
member_of_family
    !=
inherits
```

---

# 108. No specialization as inheritance

Global invariant :

```text
specialized_standard_within_family
    !=
inherits
```

---

# 109. No sector specialization as inheritance

Global invariant :

```text
sector_specialization_within_family
    !=
inherits
```

---

# 110. No reporting hint as mapping

Global invariant :

```text
account_hint
    !=
StatementAccountMapping
```

---

# 111. No concept as rule

Global invariant :

```text
ReferenceConcept
    !=
AccountingPolicy
```

---

# 112. Fail-closed matrix

| Situation | Résultat |
|---|---|
| relation absente | `UNRESOLVED` |
| relation explicitement interdite | `FORBIDDEN` |
| crosswalk structural | `CANDIDATE_ONLY` |
| semantic equivalence non assertée | `REVIEW_REQUIRED` |
| concept binding absent | `UNRESOLVED` |
| reporting hint non exécutable | `CANDIDATE_ONLY` |
| provider snapshot incompatible | `ERROR` |
| standard edition inconnue | `ERROR` |

---

# 113. Runtime errors

Taxonomie :

```text
RegulatoryIntegrationError
|
+-- ReferenceStandardNotFoundError
+-- ReferenceEditionNotFoundError
+-- ReferenceCapabilityUnavailableError
+-- ReferenceSnapshotMismatchError
+-- ReferenceRelationForbiddenError
+-- ReferenceRelationUnresolvedError
+-- CrosswalkNotExecutableError
+-- SemanticEquivalenceNotValidatedError
+-- ConceptBindingUnavailableError
+-- ReportingMappingRequiresReviewError
+-- RegulatoryDatasetCompatibilityError
```

---

# 114. Application service - inspect capabilities

```python
profile = accounting.references.integration_profile(
    standard_id="fr-nonprofit",
    edition="2026",
)
```

---

# 115. Result example

```text
structure:
    EFFECTIVE_PLAN

reporting_structure:
    VALIDATED

account_hints:
    CANDIDATE

account_mapping:
    REVIEW_REQUIRED

snapshot:
    SUPPORTED
```

---

# 116. Application service - validate mapping

```python
accounting.reporting.validate_mapping_candidate(
    candidate_id=...,
    decision="ACCEPT",
    context=review_context,
)
```

---

# 117. Application service - impact analysis

```python
impact = accounting.references.plan_upgrade(
    current_snapshot=current,
    target_snapshot=target,
)
```

---

# 118. Provider adapters

Cibles :

```text
LocalFilesystemReferenceAdapter

PackageReferenceAdapter

HttpReferenceAdapter

ObjectStorageReferenceAdapter

InMemoryReferenceAdapter
```

---

# 119. Provider adapter invariant

Tous les adapters doivent produire le même :

```text
Reference domain model
```

pour le même dataset.

---

# 120. No repository path in domain

Interdit :

```text
domain.get("/datasets/structured/pcg_2026_v1_structure.json")
```

---

# 121. Adapter chooses storage

Le domaine connaît :

```text
standard_id

edition

dataset release

artifact identity
```

pas le chemin filesystem.

---

# 122. Regulatory dataset manifest

Recommandation :

```text
RegulatoryDatasetManifest
|
+-- dataset_release
+-- artifacts
+-- checksums
+-- standards
+-- capabilities
+-- generated_at
```

---

# 123. Artifact descriptor

```text
ReferenceArtifactDescriptor
|
+-- artifact_id
+-- layer
+-- standard_ref
+-- media_type
+-- checksum
+-- size?
+-- provenance?
```

---

# 124. Snapshot creation

```text
Provider artifacts
        |
        v
checksum validation
        |
        v
ReferenceSnapshot
```

---

# 125. Snapshot completeness

Un snapshot doit capturer uniquement les capacités réellement utilisées.

Exemple :

```text
Company Chart snapshot:
    structure

Reporting snapshot:
    structure + reporting model

Cross-standard analysis:
    structures + crosswalk
```

---

# 126. Minimal snapshot

Ne pas forcer le téléchargement de :

```text
all standards
all reporting
all crosswalks
```

si une entité utilise seulement PCG structure.

---

# 127. Reference snapshot reproducibility

Replay :

```text
same dataset release
+
same artifact checksums
+
same mapping/policy versions
=
same reference semantics
```

---

# 128. Production qualification

Un standard n'est pas `PRODUCTION_QUALIFIED` globalement.

Qualification par capacité :

```text
STRUCTURE

CHART_GENERATION

REPORTING_STRUCTURE

REPORTING_MAPPING

POLICY_BINDING

CROSSWALK

EXPORT
```

---

# 129. Exemple

Possible :

```text
fr-nonprofit:2026
    structure:
        PRODUCTION_QUALIFIED

    reporting_structure:
        PRODUCTION_QUALIFIED

    automatic_reporting_mapping:
        NOT_QUALIFIED
```

---

# 130. Qualification evidence

```text
RegulatoryCapabilityQualification
|
+-- standard_ref
+-- capability_code
+-- provider_version
+-- dataset_release
+-- framework_version
+-- status
+-- test_suite
+-- golden_refs
+-- reviewer
+-- qualified_at
```

---

# 131. Tests structure - PCG

Golden minimum :

```text
load standard fr-pcg:2026

find account:fr-pcg:2026:512

verify:
    label Banques
    parent 51
    path 5/51/512
    children 5121 / 5124
```

---

# 132. Tests structure - SYSCOHADA

Golden :

```text
load account:ohada-syscohada:2017:7721

verify:
    label
    parent 772
    path 7/77/772/7721
    provenance retained
```

---

# 133. Tests effective plan - Non-Profit

Golden :

```text
10:
    override

11:
    inherited

512:
    inherited from fr-pcg:2026:512
```

---

# 134. Non-Profit statistics golden

Verify :

```text
901 effective nodes

73 additions

43 overrides

785 inherited
```

---

# 135. Reporting safety golden

For Non-Profit :

```text
account_hints_executable == false

human_validation_required == true

statement_structure == official_source
```

---

# 136. Crosswalk safety golden

For EBNL/SYSCOHADA :

```text
automatic_crosswalk_approval == false

inheritance_asserted == false

semantic_equivalence_from_code_equality == false
```

---

# 137. OHADA relation golden

Verify :

```text
SYSCOHADA:
    member_of_family

EBNL:
    specialized_standard_within_family

PCEMF:
    sector_specialization_within_family
```

---

# 138. Negative relation golden

Verify impossible :

```text
PCEMF 2010 inherits SYSCOHADA 2017
```

and :

```text
EBNL 2023 inherits SYSCOHADA 2017
```

under current corpus.

---

# 139. Concept safety golden

Verify :

```text
bindings == []

auto_approval_allowed == false

neutral_concept_is_not_accounting_rule == true
```

---

# 140. Contract tests - provider

Every provider must pass :

```text
get_standard

get_structure

get_effective_plan where available

get_reporting_model where available

get_relations where available

get_crosswalk where available

get_concepts where available

create_snapshot
```

---

# 141. Contract test - missing capability

If PCEMF structure is unavailable :

```text
get_structure(cemac-pcemf:2010)
```

must return/raise :

```text
ReferenceCapabilityUnavailable
```

not fabricate data from SYSCOHADA.

---

# 142. Contract test - relation inference

Provider cannot implement :

```python
if same_family:
    relation = "inherits"
```

---

# 143. Contract test - reporting hint

Provider preserves :

```text
account_hints_executable=false
```

through all DTO conversions.

---

# 144. Contract test - external IDs

Provider preserves :

```text
account:fr-pcg:2026:512

account:ohada-syscohada:2017:7721
```

exactly.

---

# 145. Contract test - provenance

Source provenance must survive :

```text
JSON
    ->
adapter DTO
    ->
domain ReferenceNode
```

---

# 146. Matrix serialization

La matrice peut être rendue en JSON :

```json
{
  "standard_ref": "fr-nonprofit:2026",
  "capabilities": {
    "effective_plan": {
      "status": "VALIDATED",
      "executable": true
    },
    "reporting_structure": {
      "status": "VALIDATED",
      "executable": true
    },
    "reporting_account_mappings": {
      "status": "REVIEW_REQUIRED",
      "executable": false
    }
  }
}
```

---

# 147. Configuration utilisateur

L'application peut définir :

```text
RegulatoryIntegrationPolicy
```

---

# 148. `RegulatoryIntegrationPolicy`

```text
RegulatoryIntegrationPolicy
|
+-- require_snapshot
+-- allow_candidate_suggestions
+-- require_human_review
+-- reject_unqualified_capabilities
+-- accepted_provider_ids
+-- minimum_qualification
```

---

# 149. Production recommendation

```text
require_snapshot = true

reject_unqualified_capabilities = true

require_human_review = true
    when source marks review required
```

---

# 150. Preview mode

Preview peut autoriser :

```text
candidate suggestions
```

mais doit les étiqueter clairement.

---

# 151. `ReferenceCandidate`

```text
ReferenceCandidate
|
+-- candidate_type
+-- source
+-- target
+-- confidence?
+-- rationale
+-- human_review_required
+-- executable
```

---

# 152. Confidence

Un score de confiance n'outrepasse jamais :

```text
human_review_required = true
```

---

# 153. Regulatory confidence vs provenance confidence

Distinguer :

```text
extraction confidence

semantic validation

execution authorization
```

---

# 154. Example

Un noeud structure peut avoir :

```text
provenance.confidence = 1.0
```

sans que cela rende :

```text
cross-standard mapping executable
```

---

# 155. Regulatory officiality

L'architecture doit distinguer :

```text
official source structure

derived structure

candidate mapping

validated executable mapping
```

---

# 156. `ReferenceEvidenceStatus`

```text
OFFICIAL_SOURCE

SOURCE_SUPPORTED

DERIVED

STRUCTURAL

CANDIDATE

HUMAN_VALIDATED
```

---

# 157. `ReferenceExecutionStatus`

```text
NON_EXECUTABLE

EXECUTABLE

REVIEW_REQUIRED
```

---

# 158. Pourquoi séparer Evidence et Execution

Car :

```text
official statement line
```

peut être officiel,

tandis que :

```text
account hint for that line
```

reste non exécutable.

---

# 159. Matrix per capability, not per file

Un fichier reporting peut contenir :

```text
official structure

and

candidate hints
```

Le fichier ne reçoit donc pas un unique statut d'exécution.

---

# 160. Security / safety property

Le danger principal n'est pas seulement :

```text
invalid JSON
```

mais :

```text
valid JSON interpreted with too much authority
```

---

# 161. Fail-closed regulatory interpretation

Principle :

```text
if authority is ambiguous:
    do not execute
```

---

# 162. Audit trail

Événements :

```text
REFERENCE_SNAPSHOT_CREATED

REFERENCE_CAPABILITY_INSPECTED

REGULATORY_BINDING_CREATED

REGULATORY_BINDING_REVIEWED

REPORTING_MAPPING_CANDIDATE_CREATED

REPORTING_MAPPING_VALIDATED

REFERENCE_UPGRADE_PLANNED

REFERENCE_UPGRADE_ACTIVATED

CROSSWALK_REVIEWED
```

---

# 163. Audit metadata

```text
standard_ref

dataset_release

artifact checksum

candidate/evidence refs

review decision
```

---

# 164. Upgrade audit

Ne jamais seulement enregistrer :

```text
"updated PCG"
```

mais :

```text
from snapshot R1
to snapshot R2
impact plan P
review decision
```

---

# 165. Observability

Metrics :

```text
reference_snapshot_created_total

reference_capability_unavailable_total

regulatory_mapping_review_required_total

crosswalk_candidate_total

crosswalk_rejected_total

reference_upgrade_total

reference_replay_mismatch_total
```

---

# 166. No sensitive financial data

Les métriques réglementaires n'ont pas besoin d'exposer les montants comptables.

---

# 167. Package cible

```text
src/pyaccountingkit/
|
+-- domain/references/
|   +-- standards.py
|   +-- nodes.py
|   +-- effective_plan.py
|   +-- relations.py
|   +-- crosswalks.py
|   +-- concepts.py
|   +-- reporting.py
|   +-- capabilities.py
|   +-- qualification.py
|
+-- application/references/
|   +-- inspect_capabilities.py
|   +-- create_snapshot.py
|   +-- compare_snapshots.py
|   +-- plan_upgrade.py
|   +-- validate_candidate.py
|
+-- ports/
|   +-- references.py
|
+-- adapters/regulatory/
    +-- filesystem.py
    +-- package.py
    +-- http.py
    +-- object_storage.py
    +-- in_memory.py
```

---

# 168. No per-standard duplicated packages

Éviter :

```text
pyaccountingkit-reference-pcg

pyaccountingkit-reference-syscohada
```

si ces packages recopient les datasets.

---

# 169. Acceptable standard-specific adapter logic

Autorisé si nécessaire :

```text
loader/parser strategy
```

mais l'artefact réglementaire reste dans :

```text
regulatory-accounting-data-framework
```

---

# 170. Matrice de responsabilités

| Responsabilité | regulatory framework | PyAccountingKit | Application |
|---|---:|---:|---:|
| Source réglementaire | **oui** | non | non |
| Structuration source | **oui** | consomme | non |
| Provenance | **oui** | préserve | affiche |
| Company Chart | non | **oui** | configure |
| Company coding | non | **oui** | configure |
| Candidate review | metadata | orchestre | **décide/autorise** |
| Posting | non | **oui** | déclenche |
| Reporting engine | modèle source | **oui** | configure |
| Analysis | concepts candidats | **oui** | utilise |
| Regulatory dataset release | **oui** | pinne | sélectionne |

---

# 171. Matrice de sécurité sémantique

| Donnée | Peut suggérer | Peut exécuter directement |
|---|---:|---:|
| Explicit structure node | oui | oui pour navigation/reference |
| Effective plan account | oui | oui comme reference |
| Family relation | oui | non pour inheritance |
| Structural crosswalk | oui | non |
| Neutral concept | oui | non |
| Empty/deferred concept binding | non | non |
| Official statement structure | oui | oui comme structure |
| Candidate account hint | oui | non |
| Validated StatementAccountMapping | oui | oui |
| Negative constraint | oui | oui comme interdiction |

---

# 172. Standards summary

## `fr-pcg:2026`

```text
Primary strength:
    structured account hierarchy

Integration:
    reference structure / company chart seed

Safety:
    company semantics remain explicitly bound
```

---

# 173. `fr-nonprofit:2026`

```text
Primary strength:
    resolved effective plan
    official reporting structure

Safety:
    candidate reporting hints remain non-executable
```

---

# 174. `ohada-syscohada:2017`

```text
Primary strength:
    structured OHADA chart
    family membership

Safety:
    membership gives no inheritance into special standards
```

---

# 175. `ohada-ebnl:2023`

```text
Primary strength:
    specialized OHADA reference
    structural comparison data

Safety:
    no automatic inheritance / semantic equivalence
```

---

# 176. `cemac-pcemf:2010`

```text
Primary strength:
    explicit sector-specialization relation
    crosswalk scope

Safety:
    no inheritance from SYSCOHADA 2017
    individual mappings require review
```

---

# 177. Release compatibility matrix integration

`17_RELEASE_AND_VERSIONING_STRATEGY` doit publier pour chaque release :

```text
REGULATORY_COMPATIBILITY_MATRIX.json
```

---

# 178. Example release entry

```json
{
  "standard_ref": "fr-nonprofit:2026",
  "dataset_release": "pinned-release-id",
  "capabilities": {
    "effective_plan": "PRODUCTION_QUALIFIED",
    "reporting_structure": "PRODUCTION_QUALIFIED",
    "automatic_account_mapping": "NOT_SUPPORTED"
  }
}
```

---

# 179. Compatibility != bundling

PyAccountingKit peut être compatible avec un dataset sans le livrer dans le wheel.

---

# 180. Dataset delivery

Possible :

```text
filesystem
package
HTTP
object storage
```

---

# 181. Offline deployment

`PackageReferenceAdapter` ou `LocalFilesystemReferenceAdapter`.

---

# 182. Connected deployment

`HttpReferenceAdapter` / object storage.

---

# 183. Dataset checksum required

Pour production :

```text
artifact checksum
```

doit être validé au snapshot.

---

# 184. Source update while application runs

Ne modifie pas le snapshot actif.

---

# 185. New snapshot only

Une mise à jour provider devient effective uniquement via :

```text
new AccountingReferenceSnapshot
```

et activation explicite.

---

# 186. ADRs

| ID | Décision |
|---|---|
| ADR-RFM-001 | L'intégration réglementaire est capability-based, pas un booléen global |
| ADR-RFM-002 | `regulatory-accounting-data-framework` reste la source réglementaire |
| ADR-RFM-003 | Les IDs réglementaires externes sont préservés |
| ADR-RFM-004 | Les hiérarchies explicites sont consommées sans reconstruction dans le domain |
| ADR-RFM-005 | `fr-nonprofit:2026` consomme un effective plan déjà résolu |
| ADR-RFM-006 | Les overlays Non-Profit servent à provenance/impact, pas à re-résolution arbitraire |
| ADR-RFM-007 | `member_of_family` n'implique pas `inherits` |
| ADR-RFM-008 | `specialized_standard_within_family` n'implique pas `inherits` |
| ADR-RFM-009 | `sector_specialization_within_family` n'implique pas `inherits` |
| ADR-RFM-010 | Les negative constraints sont first-class |
| ADR-RFM-011 | EBNL n'hérite pas automatiquement de SYSCOHADA dans le corpus courant |
| ADR-RFM-012 | PCEMF 2010 n'hérite pas de SYSCOHADA 2017 |
| ADR-RFM-013 | Un crosswalk structurel n'est pas une équivalence sémantique |
| ADR-RFM-014 | L'égalité de code n'est jamais une preuve sémantique |
| ADR-RFM-015 | Les concepts neutres ne sont pas des règles comptables |
| ADR-RFM-016 | Les concept bindings absents/différés ne sont pas inventés |
| ADR-RFM-017 | La structure officielle de reporting est distincte de ses account hints |
| ADR-RFM-018 | Un account hint marqué non exécutable reste un candidat |
| ADR-RFM-019 | Une confidence élevée ne contourne jamais `human_review_required` |
| ADR-RFM-020 | RegulatoryAccountBinding, StatementAccountMapping et ReferenceCrosswalk restent trois graphes distincts |
| ADR-RFM-021 | Le posting utilise CompanyAccount, jamais ReferenceAccount directement |
| ADR-RFM-022 | Les active charts/reporting profiles pinnent un ReferenceSnapshot |
| ADR-RFM-023 | Les upgrades réglementaires sont explicitement planifiés |
| ADR-RFM-024 | Le latest provider dataset n'est jamais utilisé implicitement en replay |
| ADR-RFM-025 | Les qualifications réglementaires sont par capacité |
| ADR-RFM-026 | Présence d'un dataset ne signifie pas exécution qualifiée |
| ADR-RFM-027 | Les adapters de stockage produisent un domain model identique |
| ADR-RFM-028 | Aucun chemin du repository réglementaire n'entre dans le domain |
| ADR-RFM-029 | IFRS reste `NOT_ASSERTED` sans source réglementaire versionnée qualifiée |
| ADR-RFM-030 | Les packages par standard ne dupliquent pas les datasets réglementaires |
| ADR-RFM-031 | Les candidate mappings peuvent être utilisés en preview, jamais comme mappings actifs sans validation |
| ADR-RFM-032 | Les official statement structures peuvent être exécutées comme structure sans rendre leurs hints exécutables |
| ADR-RFM-033 | Le snapshot capture les capacités réellement utilisées |
| ADR-RFM-034 | Le provider expose idéalement un `ReferenceCapabilitySet` |
| ADR-RFM-035 | Les erreurs d'ambiguïté réglementaire sont fail-closed |
| ADR-RFM-036 | Les cross-standard analyses exigent des mappings/crosswalks explicitement qualifiés |
| ADR-RFM-037 | Les concepts neutres servent à la navigation/candidate generation tant que leurs bindings sont différés |
| ADR-RFM-038 | Les tests golden incluent les contraintes négatives et non seulement les cas positifs |
| ADR-RFM-039 | `REGULATORY_COMPATIBILITY_MATRIX` est un artefact de release |
| ADR-RFM-040 | La qualification Production ne s'applique jamais automatiquement à toutes les capacités d'un standard |

---

# 187. Critères d'acceptation P1.8

```text
[ ] taxonomy de statuts définie

[ ] matrice par standard définie

[ ] PCG 2026 structure intégrée

[ ] IDs PCG réglementaires préservés

[ ] Non-Profit effective plan défini

[ ] base fr-pcg:2026 explicite

[ ] override / inherited origins préservés

[ ] statistiques effective plan documentées

[ ] overlay boundary définie

[ ] Non-Profit reporting structure distinguée des hints

[ ] account_hints_executable=false respecté

[ ] human_validation_required respecté

[ ] SYSCOHADA member_of_family défini

[ ] EBNL specialized_standard_within_family défini

[ ] PCEMF sector_specialization_within_family défini

[ ] negative constraints intégrées

[ ] EBNL -> SYSCOHADA inheritance interdit

[ ] PCEMF -> SYSCOHADA inheritance interdit

[ ] structural crosswalk non exécutable défini

[ ] semantic code equality interdite

[ ] neutral concepts définis

[ ] bindings vides/différés respectés

[ ] neutral concept != accounting rule explicite

[ ] RegulatoryAccountBinding séparé

[ ] StatementAccountMapping séparé

[ ] ReferenceCrosswalk séparé

[ ] ReferenceCapabilitySet défini

[ ] IntegrationProfile défini

[ ] RegulatorySupportLevel défini

[ ] snapshot pinning défini

[ ] upgrade impact analysis défini

[ ] production qualification par capability définie

[ ] provider contract tests définis

[ ] regulatory golden tests définis

[ ] IFRS non asserté sans source qualifiée

[ ] fail-closed errors définies
```

---

# 188. Ordre d'implémentation recommandé

## RFM-00 - Capability primitives

```text
ReferenceCapabilityCode
ReferenceCapabilityStatus
ReferenceExecutionStatus
ReferenceEvidenceStatus
```

---

## RFM-01 - Capability inspection

```text
ReferenceCapabilitySet

provider.get_capabilities()
```

---

## RFM-02 - PCG 2026

```text
structure loader

node identity

hierarchy

snapshot golden
```

---

## RFM-03 - SYSCOHADA 2017

```text
structure loader

OHADA family relation

snapshot golden
```

---

## RFM-04 - Non-Profit 2026

```text
effective plan

overlay metadata

base relationship

snapshot
```

---

## RFM-05 - Non-Profit reporting safety

```text
official statement structure

candidate hints

human review

non-executable mapping gate
```

---

## RFM-06 - OHADA relations

```text
family relations

negative constraints
```

---

## RFM-07 - Crosswalks

```text
EBNL/SYSCOHADA structural delta

PCEMF/SYSCOHADA candidate scope
```

---

## RFM-08 - Neutral concepts

```text
concept registry

deferred bindings

candidate generation only
```

---

## RFM-09 - Qualification model

```text
RegulatoryCapabilityQualification

golden evidence

framework/dataset version pinning
```

---

## RFM-10 - Release matrix

```text
REGULATORY_COMPATIBILITY_MATRIX.json
```

---

# 189. Démonstrateur - PCG

```text
1. Load fr-pcg:2026
2. Get structure
3. Resolve account:fr-pcg:2026:512
4. Verify hierarchy
5. Create snapshot
6. Generate company account candidate
7. Bind explicit CompanyAccount
```

---

# 190. Démonstrateur - Non-Profit

```text
1. Load fr-nonprofit:2026 effective plan
2. Verify base fr-pcg:2026
3. Verify account 10 override
4. Verify account 512 inheritance
5. Load reporting model
6. Read official statement structure
7. Generate account-hint candidates
8. Prevent execution before validation
```

---

# 191. Démonstrateur - EBNL crosswalk safety

```text
1. Load EBNL/SYSCOHADA structural delta
2. Find same code/same normalized label
3. Verify semantic_equivalence_asserted == false
4. Attempt automatic crosswalk activation
5. Expected:
      CrosswalkNotExecutableError
```

---

# 192. Démonstrateur - PCEMF inheritance safety

```text
Attempt:
    PCEMF 2010 inherits SYSCOHADA 2017

Expected:
    ReferenceRelationForbiddenError
```

---

# 193. Démonstrateur - concepts

```text
1. Load concept:cash
2. Inspect bindings
3. bindings = []
4. Attempt resolve CompanyAccount automatically
5. Expected:
      ConceptBindingUnavailable
```

---

# 194. Démonstrateur - reporting hint safety

```text
Hint:
    prefix 466

human_validation_required:
    true

Expected:
    MappingCandidate

Not:
    Active StatementAccountMapping
```

---

# 195. Démonstrateur - upgrade

```text
Current:
    ReferenceSnapshot R1

Provider:
    dataset R2 available

Expected:
    current chart still uses R1

Then:
    compare R1/R2
    create migration plan
    review
    activate new snapshot explicitly
```

---

# 196. Source-evidence registry

Les décisions critiques de ce document ont été construites à partir des artefacts suivants :

```text
pcg_2026_v1_structure(1).json

syscohada_2017_v1_structure(1).json

nonprofit_2026_v1_effective_plan(1).json

nonprofit_2026_v1_account_overlay(1).json

nonprofit_2026_v3_reporting(1).json

ohada_accounting_standard_relations(1).json

ebnl_2023_vs_syscohada_2017_structural_delta(1).json

accounting_core_concepts_v0(1).json
```

---

# 197. Faits explicitement prouvés par le corpus étudié

```text
PCG 2026 exposes explicit structured hierarchy

SYSCOHADA 2017 exposes explicit structured hierarchy

Non-Profit 2026 is an effective plan based on fr-pcg:2026

Non-Profit distinguishes inherited accounts and extension overrides

Non-Profit reporting structure is official-source

Non-Profit account hints are derived candidates

Non-Profit account hints are non-executable

Non-Profit reporting requires human validation

SYSCOHADA is an OHADA family member

EBNL is a specialized standard within the OHADA family

PCEMF is a sector specialization within the OHADA family

EBNL -> SYSCOHADA inheritance is not asserted

PCEMF 2010 -> SYSCOHADA 2017 inheritance is forbidden

EBNL/SYSCOHADA code equality is not semantic equivalence

neutral accounting concepts are not accounting rules

concept bindings are currently deferred and empty
```

---

# 198. Faits volontairement non affirmés

Le présent document ne prétend pas, faute de preuve suffisante dans les sources actuellement étudiées, que :

```text
all PCG reporting account mappings are executable

all SYSCOHADA reporting account mappings are executable

EBNL reporting mappings are production-qualified

PCEMF structure/reporting datasets are fully integrated

IFRS is a qualified regulatory standard in the current provider

any cross-standard code equality proves accounting equivalence
```

---

# 199. Frontière avec le prochain document

Le prochain jalon de la roadmap est :

```text
20_PYACCOUNTINGKIT_ADR_REGISTER.md
```

Il devra consolider dans un registre unique les ADR issus de :

```text
RULE
POL
REF
COA
LEDGER
CLOSING
AUDIT
PERSISTENCE
TESTING
IMPORT
REPORTING
ANALYSIS
SUBLEDGER
API
RELEASE
CFA MIGRATION
REGULATORY FRAMEWORK MATRIX
```

---

# 200. Conclusion

La matrice d'intégration réglementaire impose une règle fondamentale :

```text
PyAccountingKit consumes regulatory evidence
without granting it more authority
than the source explicitly provides.
```

La chaîne cible est :

```text
Regulatory Dataset
        |
        v
Capability Inspection
        |
        +--> Structure
        +--> Effective Plan
        +--> Relations
        +--> Crosswalk
        +--> Concepts
        +--> Reporting
        |
        v
Reference Snapshot
        |
        v
Explicit Company Bindings / Validated Mappings
        |
        v
Accounting / Reporting / Analysis
```

Les garanties finales sont :

```text
Explicit IDs are preserved

Explicit hierarchies are consumed

Effective plans are not arbitrarily re-resolved

Family membership does not imply inheritance

Specialization does not imply inheritance

Code equality does not imply semantic equivalence

Neutral concepts do not imply accounting rules

Candidate hints do not imply executable mappings

Human-review flags are binding safety constraints

Negative constraints are first-class

Historical snapshots never use provider latest implicitly

Qualification is per capability, not per standard name

When regulatory authority is ambiguous, PyAccountingKit fails closed
```

---

**Prochain document recommandé :**

```text
20_PYACCOUNTINGKIT_ADR_REGISTER.md
```


---

## Sources et références documentaires du projet

- 📂 [Référentiels réglementaires — Datasets](../../referentiels/datasets/)
- 📐 [Référentiels réglementaires — Schémas](../../referentiels/schemas/)
- 📦 [regulatory-accounting-data-framework](../../../resources/regulatory-accounting-data-framework/)

---

## Plans d'implémentation principaux

Ce document est couvert par les plans suivants :

- [PLAN-02 — References, Charts & Policies (0.2.0)](../../plans/PLAN-02_REFERENCES_CHARTS_POLICIES_0.2.0.md)
